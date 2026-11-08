import os
import io
import base64
import logging
import tempfile
from typing import Optional, Dict, Any, Tuple
from PIL import Image
import numpy as np

# Ensure matplotlib cache directory is writable in all environments
if "MPLCONFIGDIR" not in os.environ:
    os.environ["MPLCONFIGDIR"] = tempfile.gettempdir()

import matplotlib
import matplotlib.cm as cm

from .model_service import model_service
from ..core.config import settings

logger = logging.getLogger(__name__)

# Check TensorFlow availability
try:
    import tensorflow as tf
    from tensorflow.keras.applications.vgg19 import preprocess_input
    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False
    logger.warning("TensorFlow is not available. GradCAMService will be inactive.")


class GradCAMService:
    """
    Grad-CAM (Gradient-weighted Class Activation Mapping) visualization service
    for the trained VGG19 retinal disease classification model.

    Generates visual heatmaps identifying salient image regions that contributed
    most significantly to the model's classification score.
    """

    def __init__(self, target_layer_name: str = "block5_conv4"):
        self.target_layer_name = target_layer_name
        self._grad_model = None
        self._initialized_for_model_id = None
        self.colormap = matplotlib.colormaps["jet"]

    def _get_grad_model(self):
        """
        Retrieves or constructs the cached multi-output gradient sub-model.
        Reuses the existing in-memory model loaded by ModelService.
        """
        if not model_service.is_available:
            raise RuntimeError(
                "Classification model is not available for visual explanation generation."
            )

        current_model = model_service.model
        current_id = id(current_model)

        # Check if already constructed for the currently active model
        if self._grad_model is not None and self._initialized_for_model_id == current_id:
            return self._grad_model

        try:
            target_layer = current_model.get_layer(self.target_layer_name)
        except ValueError:
            raise RuntimeError(
                f"Target convolutional layer '{self.target_layer_name}' not found in the loaded model."
            )

        # Construct gradient model outputting target feature map and final predictions
        self._grad_model = tf.keras.models.Model(
            inputs=current_model.inputs,
            outputs=[target_layer.output, current_model.output]
        )
        self._initialized_for_model_id = current_id
        logger.info(
            f"GradCAMService: Initialized gradient sub-model using layer '{self.target_layer_name}'."
        )
        return self._grad_model

    @staticmethod
    def _to_png_data_url(pil_image: Image.Image) -> str:
        """Encodes a PIL image as a base64 PNG data URL."""
        buffer = io.BytesIO()
        pil_image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"

    def generate_gradcam(
        self,
        image: Image.Image,
        class_index: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generates genuine Grad-CAM heatmaps and overlays for a given retinal photograph.

        Parameters:
        - image: PIL Image of the retinal photograph.
        - class_index: Optional target category index (0-3). If None, uses top predicted class.

        Returns:
        - Dictionary containing:
            - status: "success"
            - prediction: str
            - class_index: int
            - confidence: float
            - target_layer: str
            - heatmap_data_url: str (Base64 PNG data URL)
            - overlay_data_url: str (Base64 PNG data URL)
            - original_dimensions: Tuple[int, int] (width, height)
            - scores: Dict[str, float]
        """
        if not HAS_TENSORFLOW:
            raise RuntimeError("TensorFlow is not installed in the environment.")

        if not model_service.is_available:
            raise RuntimeError(
                "Screening service is temporarily unavailable because the classification model has not been configured."
            )

        grad_model = self._get_grad_model()

        # 1. Preserve original dimensions and ensure RGB mode
        if image.mode != "RGB":
            image = image.convert("RGB")
        orig_w, orig_h = image.size

        # 2. Preprocess image identical to VGG19 screening pipeline
        resized_image = image.resize(settings.IMAGE_SIZE)
        img_array = np.array(resized_image, dtype=np.float32)
        batch_input = np.expand_dims(img_array, axis=0)
        preprocessed = preprocess_input(batch_input)

        # 3. Compute gradients via GradientTape
        with tf.GradientTape() as tape:
            conv_outputs, predictions = grad_model([preprocessed])
            raw_scores = predictions[0]

            # Determine target class index
            if class_index is None:
                target_idx = int(tf.argmax(raw_scores))
            else:
                if not (0 <= class_index < len(settings.CATEGORIES)):
                    raise ValueError(
                        f"Class index {class_index} is out of range [0, {len(settings.CATEGORIES) - 1}]."
                    )
                target_idx = int(class_index)

            # Target score for gradient backpropagation
            target_score = predictions[:, target_idx]

        # 4. Extract gradients of target score w.r.t. convolutional feature maps
        grads = tape.gradient(target_score, conv_outputs)

        if grads is None:
            logger.warning("GradCAMService: Gradients returned None; using uniform activation.")
            pooled_grads = tf.zeros((conv_outputs.shape[-1],), dtype=tf.float32)
        else:
            # Global average pooling of gradients across spatial dimensions (height and width)
            pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

        # 5. Weight feature maps by pooled gradients
        # conv_outputs[0] shape: (14, 14, 512), pooled_grads shape: (512, 1)
        heatmap = conv_outputs[0] @ pooled_grads[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)

        # 6. Apply ReLU: only positive contributions to target class are retained
        heatmap = tf.maximum(heatmap, 0.0)

        # 7. Safe normalization to range [0.0, 1.0]
        max_activation = tf.math.reduce_max(heatmap)
        if max_activation > 1e-10:
            heatmap = heatmap / max_activation
        else:
            # In cases where all activations are zero/negative
            heatmap = tf.zeros_like(heatmap)

        heatmap_np = heatmap.numpy()

        # 8. Resize heatmap to original image dimensions with bicubic interpolation
        # Using PIL for bicubic interpolation ensures crisp, artifact-free resolution matching original fundus photograph
        heatmap_uint8 = np.uint8(np.clip(255.0 * heatmap_np, 0, 255))
        heatmap_pil_coarse = Image.fromarray(heatmap_uint8, mode="L")
        heatmap_resized_pil = heatmap_pil_coarse.resize(
            (orig_w, orig_h),
            resample=Image.Resampling.BICUBIC
        )
        heatmap_resized_normalized = np.array(heatmap_resized_pil, dtype=np.float32) / 255.0

        # 9. Apply colormap (jet) to convert single-channel intensity to RGB
        colored_heatmap_float = self.colormap(heatmap_resized_normalized)[:, :, :3]
        colored_heatmap_uint8 = np.uint8(np.clip(255.0 * colored_heatmap_float, 0, 255))
        heatmap_rgb_image = Image.fromarray(colored_heatmap_uint8, mode="RGB")

        # 10. Blend overlay with original fundus photograph
        # 40% heatmap emphasis + 60% anatomical fundus structure
        orig_array = np.array(image, dtype=np.float32)
        overlay_array = 0.4 * (colored_heatmap_float * 255.0) + 0.6 * orig_array
        overlay_uint8 = np.uint8(np.clip(overlay_array, 0, 255))
        overlay_image = Image.fromarray(overlay_uint8, mode="RGB")

        # 11. Encode results into clean base64 PNG data URLs
        heatmap_data_url = self._to_png_data_url(heatmap_rgb_image)
        overlay_data_url = self._to_png_data_url(overlay_image)

        # 12. Compile category distribution scores
        scores = {
            settings.CATEGORIES[i]: round(float(raw_scores[i]), 4)
            for i in range(len(settings.CATEGORIES))
        }

        predicted_class_name = settings.CATEGORIES[target_idx]
        confidence = float(raw_scores[target_idx])

        return {
            "status": "success",
            "message": "Grad-CAM visual explanation generated successfully.",
            "prediction": predicted_class_name,
            "class_index": target_idx,
            "confidence": round(confidence, 4),
            "target_layer": self.target_layer_name,
            "heatmap_data_url": heatmap_data_url,
            "overlay_data_url": overlay_data_url,
            "original_dimensions": (orig_w, orig_h),
            "scores": scores
        }


gradcam_service = GradCAMService()

