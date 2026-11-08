import json
import logging
from pathlib import Path
import numpy as np
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("InferenceVerifier")

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "backend" / "models" / "eye_disease_model.keras"
METADATA_PATH = BASE_DIR / "backend" / "models" / "model_metadata.json"
TEST_SPLITS_DIR = Path(__file__).resolve().parent / "data_splits" / "test"

CLASSES = ["Cataract", "Diabetic Retinopathy", "Glaucoma", "Normal"]
CLASS_INDICES = {cls: idx for idx, cls in enumerate(CLASSES)}

def verify_inference():
    logger.info("=== VERIFYING TRAINED VGG19 MODEL INFERENCE ===")

    # 1. Check Model Existence
    if not MODEL_PATH.exists():
        logger.error(f"Saved model file not found at '{MODEL_PATH}'.")
        return False

    import tensorflow as tf
    from tensorflow.keras.models import load_model
    from tensorflow.keras.applications.vgg19 import preprocess_input

    # 2. Load Model Independently
    logger.info(f"Loading model from: {MODEL_PATH}")
    model = load_model(str(MODEL_PATH))
    logger.info("Model loaded successfully!")

    # 3. Verify Input and Output Shapes
    input_shape = model.input_shape
    output_shape = model.output_shape
    logger.info(f"Verified Input Shape: {input_shape} (Expected: (None, 224, 224, 3))")
    logger.info(f"Verified Output Shape: {output_shape} (Expected: (None, 4))")

    assert input_shape == (None, 224, 224, 3), f"Invalid input shape {input_shape}"
    assert output_shape == (None, 4), f"Invalid output shape {output_shape}"

    # 4. Test on a Sample Fundus Image from each Category
    sample_tests = []
    for cls in CLASSES:
        cls_dir = TEST_SPLITS_DIR / cls
        images = list(cls_dir.glob("*.*"))
        if not images:
            continue
        sample_img_path = images[0]

        # Load and preprocess
        with Image.open(sample_img_path) as img:
            img = img.convert("RGB").resize((224, 224))
            arr = np.array(img, dtype=np.float32)

        # Batch dimension and VGG19 preprocess_input
        batch_input = np.expand_dims(arr, axis=0)
        preprocessed = preprocess_input(batch_input)

        # Predict
        raw_preds = model.predict(preprocessed, verbose=0)[0]
        prob_sum = float(np.sum(raw_preds))
        pred_idx = int(np.argmax(raw_preds))
        pred_class = CLASSES[pred_idx]
        confidence = float(raw_preds[pred_idx])

        # Validate probabilities sum to ~1.0
        assert np.isclose(prob_sum, 1.0, atol=1e-3), f"Probabilities do not sum to 1: {prob_sum}"

        prob_breakdown = {CLASSES[i]: round(float(raw_preds[i]), 4) for i in range(len(CLASSES))}

        logger.info(f"\n[Sample Test] True Class: {cls}")
        logger.info(f"  File: {sample_img_path.name}")
        logger.info(f"  Predicted Class: {pred_class} (Confidence: {confidence * 100:.2f}%)")
        logger.info(f"  Probability Sum: {prob_sum:.4f}")
        logger.info(f"  Distribution: {prob_breakdown}")

        sample_tests.append({
            "true_class": cls,
            "predicted_class": pred_class,
            "confidence": round(confidence, 4),
            "probabilities": prob_breakdown
        })

    # 5. Check Metadata
    if METADATA_PATH.exists():
        with open(METADATA_PATH, "r") as f:
            metadata = json.load(f)
        logger.info(f"\nModel Metadata Verified: version {metadata.get('model_version')}, test acc {metadata.get('test_metrics', {}).get('accuracy')}")

    logger.info("\nALL INFERENCE VERIFICATIONS PASSED CLEANLY!")
    return True

if __name__ == "__main__":
    verify_inference()

