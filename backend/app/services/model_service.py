import logging
from pathlib import Path
from typing import Optional, Dict, Any
from ..core.config import settings

logger = logging.getLogger(__name__)

# Check TensorFlow availability without crashing if missing
try:
    import tensorflow as tf
    from tensorflow.keras.models import load_model
    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False
    logger.warning("TensorFlow is not installed in the current environment. Running in lightweight mode.")

class ModelService:
    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or settings.MODEL_PATH
        self.model = None
        self._is_loaded = False
        self._load_error: Optional[str] = None
        self.categories = settings.CATEGORIES
        self.initialize_model()

    def initialize_model(self) -> None:
        """
        Attempts to locate and safely load the trained VGG19 model.
        Reports availability accurately without fabricating mock predictions.
        """
        if not HAS_TENSORFLOW:
            self._is_loaded = False
            self._load_error = "TensorFlow dependency is not installed."
            logger.info("ModelService: TensorFlow unavailable. Model disabled.")
            return

        if not self.model_path.exists():
            self._is_loaded = False
            self._load_error = f"Model artifact not found at '{self.model_path}'."
            logger.info(f"ModelService: Artifact not found at '{self.model_path}'.")
            return

        try:
            logger.info(f"Loading Keras classification model from '{self.model_path}'...")
            self.model = load_model(str(self.model_path))
            self._is_loaded = True
            self._load_error = None
            logger.info("Model loaded successfully!")
        except Exception as e:
            self.model = None
            self._is_loaded = False
            self._load_error = f"Error loading model: {str(e)}"
            logger.error(f"Failed to load model from '{self.model_path}': {e}")

    @property
    def is_available(self) -> bool:
        """Returns True only if a real, trained model is loaded and ready for inference."""
        return self._is_loaded and self.model is not None

    def get_status(self) -> Dict[str, Any]:
        """Provides status metadata for the health endpoint."""
        # Sanitize model path to relative identifier to avoid leaking local filesystem structure
        sanitized_path = f"models/{self.model_path.name}" if self.model_path else "Not configured"
        return {
            "available": self.is_available,
            "model_path": sanitized_path,
            "file_exists": self.model_path.exists() if self.model_path else False,
            "tensorflow_installed": HAS_TENSORFLOW,
            "architecture": "VGG19 (Transfer Learning)" if self.is_available else "Not configured",
            "categories": self.categories,
            "error": self._load_error,
        }

    def predict(self, image) -> Dict[str, Any]:
        """
        Executes real inference on preprocessed fundus image.
        Raises RuntimeError if model is unavailable.
        """
        if not self.is_available:
            raise RuntimeError(
                "Screening service is temporarily unavailable because the classification model has not been configured."
            )

        import numpy as np
        from tensorflow.keras.applications.vgg19 import preprocess_input

        # Ensure image is in RGB format and sized to model input dimensions
        if image.mode != "RGB":
            image = image.convert("RGB")
        if image.size != settings.IMAGE_SIZE:
            image = image.resize(settings.IMAGE_SIZE)

        img_array = np.array(image, dtype=np.float32)
        batch_input = np.expand_dims(img_array, axis=0)
        preprocessed = preprocess_input(batch_input)

        raw_preds = self.model.predict(preprocessed, verbose=0)[0]
        pred_idx = int(np.argmax(raw_preds))
        confidence = float(raw_preds[pred_idx])
        pred_class = self.categories[pred_idx]

        probabilities = {
            self.categories[i]: round(float(raw_preds[i]), 4)
            for i in range(len(self.categories))
        }

        return {
            "prediction": pred_class,
            "confidence": round(confidence, 4),
            "probabilities": probabilities
        }

model_service = ModelService()

