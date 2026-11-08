import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
os.environ["MPLCONFIGDIR"] = str(BASE_DIR / ".matplotlib")
(BASE_DIR / ".matplotlib").mkdir(parents=True, exist_ok=True)

import json
import logging
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support

import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import VGG19
from tensorflow.keras.applications.vgg19 import preprocess_input
from tensorflow.keras.layers import Dense, Dropout, GlobalAveragePooling2D, Input
from tensorflow.keras.models import Model
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from tensorflow.keras.optimizers import Adam

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("VGG19_Trainer")

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
SPLITS_DIR = Path(__file__).resolve().parent / "data_splits"
EVAL_DIR = Path(__file__).resolve().parent / "evaluation"
EVAL_DIR.mkdir(parents=True, exist_ok=True)

BACKEND_MODELS_DIR = BASE_DIR / "backend" / "models"
BACKEND_MODELS_DIR.mkdir(parents=True, exist_ok=True)
MODEL_SAVE_PATH = BACKEND_MODELS_DIR / "eye_disease_model.keras"
METADATA_SAVE_PATH = BACKEND_MODELS_DIR / "model_metadata.json"

# Fixed Class Mapping & Order
CLASSES = ["Cataract", "Diabetic Retinopathy", "Glaucoma", "Normal"]
CLASS_INDICES = {cls: idx for idx, cls in enumerate(CLASSES)}

# Hyperparameters
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
STAGE1_EPOCHS = 10
STAGE2_EPOCHS = 20
STAGE1_LR = 0.0001
STAGE2_LR = 0.00001

def create_generators():
    logger.info("Initializing ImageDataGenerators with VGG19 preprocess_input...")

    train_dir = SPLITS_DIR / "train"
    val_dir = SPLITS_DIR / "val"
    test_dir = SPLITS_DIR / "test"

    # Moderate training-only augmentation
    train_datagen = ImageDataGenerator(
        preprocessing_function=preprocess_input,
        horizontal_flip=True,
        rotation_range=15,
        zoom_range=0.1,
        brightness_range=[0.9, 1.1],
        fill_mode='nearest'
    )

    # Validation and test have NO augmentation, only preprocessing
    val_datagen = ImageDataGenerator(preprocessing_function=preprocess_input)
    test_datagen = ImageDataGenerator(preprocessing_function=preprocess_input)

    train_gen = train_datagen.flow_from_directory(
        directory=str(train_dir),
        target_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        classes=CLASSES,
        class_mode='categorical',
        shuffle=True,
        seed=42
    )

    val_gen = val_datagen.flow_from_directory(
        directory=str(val_dir),
        target_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        classes=CLASSES,
        class_mode='categorical',
        shuffle=False
    )

    test_gen = test_datagen.flow_from_directory(
        directory=str(test_dir),
        target_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        classes=CLASSES,
        class_mode='categorical',
        shuffle=False
    )

    return train_gen, val_gen, test_gen

def build_model():
    logger.info("Constructing VGG19 Transfer Learning Architecture...")
    
    # Input
    inputs = Input(shape=(224, 224, 3))

    # Base VGG19 pretrained on ImageNet
    base_model = VGG19(weights="imagenet", include_top=False, input_tensor=inputs)

    # Initial freeze of entire convolutional backbone
    base_model.trainable = False

    # Classification Head
    x = base_model.output
    x = GlobalAveragePooling2D(name="gap")(x)
    x = Dense(256, activation='relu', name="dense_256")(x)
    x = Dropout(0.5, name="dropout_0.5")(x)
    outputs = Dense(len(CLASSES), activation='softmax', name="predictions")(x)

    model = Model(inputs=inputs, outputs=outputs, name="VisionCare_VGG19")
    return model, base_model

def train():
    logger.info("=== STARTING VISIONCARE VGG19 MODEL TRAINING PIPELINE ===")
    
    train_gen, val_gen, test_gen = create_generators()
    model, base_model = build_model()

    # Callbacks
    early_stop_stage1 = EarlyStopping(monitor='val_loss', patience=3, restore_best_weights=True, verbose=1)
    reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience=2, min_lr=1e-7, verbose=1)
    checkpoint = ModelCheckpoint(
        filepath=str(MODEL_SAVE_PATH),
        monitor='val_accuracy',
        save_best_only=True,
        verbose=1
    )

    # STAGE 1: Feature Extraction (Frozen Backbone)
    logger.info("\n--- STAGE 1: FEATURE EXTRACTION (FROZEN BACKBONE) ---")
    model.compile(
        optimizer=Adam(learning_rate=STAGE1_LR),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    history1 = model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=STAGE1_EPOCHS,
        callbacks=[early_stop_stage1, reduce_lr, checkpoint]
    )

    # STAGE 2: Fine-Tuning (Unfreeze block5)
    logger.info("\n--- STAGE 2: FINE-TUNING (UNFREEZING BLOCK5 CONVOLUTIONAL LAYERS) ---")
    base_model.trainable = True

    # Freeze all layers except block5 conv layers
    unfreeze_layers = {"block5_conv1", "block5_conv2", "block5_conv3", "block5_conv4"}
    for layer in base_model.layers:
        if layer.name in unfreeze_layers:
            layer.trainable = True
        else:
            layer.trainable = False

    trainable_count = sum(len(layer.weights) for layer in model.layers if layer.trainable)
    logger.info(f"Unfrozen block5 conv layers for fine-tuning. Trainable layers count: {trainable_count}")

    model.compile(
        optimizer=Adam(learning_rate=STAGE2_LR),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    early_stop_stage2 = EarlyStopping(monitor='val_loss', patience=4, restore_best_weights=True, verbose=1)

    history2 = model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=STAGE2_EPOCHS,
        callbacks=[early_stop_stage2, reduce_lr, checkpoint]
    )

    # Combine History
    stage1_epochs_run = len(history1.history['accuracy'])
    acc = history1.history['accuracy'] + history2.history['accuracy']
    val_acc = history1.history['val_accuracy'] + history2.history['val_accuracy']
    loss = history1.history['loss'] + history2.history['loss']
    val_loss = history1.history['val_loss'] + history2.history['val_loss']

    # Plot Accuracy and Loss Curves
    plot_training_curves(acc, val_acc, loss, val_loss, stage1_epochs_run)

    # EVALUATION ON UNTOUCHED TEST SET USING BEST SAVED CHECKPOINT
    logger.info("\n--- EVALUATION ON UNTOUCHED TEST SET ---")
    logger.info(f"Loading best saved checkpoint from: {MODEL_SAVE_PATH}")
    best_model = tf.keras.models.load_model(str(MODEL_SAVE_PATH))
    evaluate_on_test_set(best_model, test_gen)

def plot_training_curves(acc, val_acc, loss, val_loss, stage1_epochs_run):
    epochs_range = range(1, len(acc) + 1)

    # Accuracy Plot
    plt.figure(figsize=(8, 5))
    plt.plot(epochs_range, acc, label='Training Accuracy', color='#059669', lw=2)
    plt.plot(epochs_range, val_acc, label='Validation Accuracy', color='#0284c7', lw=2)
    plt.axvline(x=stage1_epochs_run + 0.5, color='#94a3b8', linestyle='--', label='Fine-Tuning Start')
    plt.title('VGG19 Training and Validation Accuracy', fontsize=12, fontweight='bold')
    plt.xlabel('Epochs')
    plt.ylabel('Accuracy')
    plt.legend(loc='lower right')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(EVAL_DIR / "accuracy_history.png"), dpi=300)
    plt.close()

    # Loss Plot
    plt.figure(figsize=(8, 5))
    plt.plot(epochs_range, loss, label='Training Loss', color='#e11d48', lw=2)
    plt.plot(epochs_range, val_loss, label='Validation Loss', color='#d97706', lw=2)
    plt.axvline(x=stage1_epochs_run + 0.5, color='#94a3b8', linestyle='--', label='Fine-Tuning Start')
    plt.title('VGG19 Training and Validation Loss', fontsize=12, fontweight='bold')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(EVAL_DIR / "loss_history.png"), dpi=300)
    plt.close()

    logger.info(f"Training history plots saved to {EVAL_DIR}")

def evaluate_on_test_set(model, test_gen):
    test_gen.reset()
    y_true = test_gen.classes
    test_preds = model.predict(test_gen, verbose=1)
    y_pred = np.argmax(test_preds, axis=1)

    # Test Accuracy
    test_acc = float(np.mean(y_pred == y_true))
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='weighted')

    # Classification Report
    cls_report_dict = classification_report(y_true, y_pred, target_names=CLASSES, output_dict=True)
    cls_report_text = classification_report(y_true, y_pred, target_names=CLASSES)

    logger.info(f"\nTest Accuracy: {test_acc:.4f}")
    logger.info(f"Weighted Precision: {precision:.4f}")
    logger.info(f"Weighted Recall: {recall:.4f}")
    logger.info(f"Weighted F1-Score: {f1:.4f}")
    logger.info(f"\nClassification Report:\n{cls_report_text}")

    # Confusion Matrix
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(7, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=CLASSES, yticklabels=CLASSES)
    plt.title('VGG19 Test Set Confusion Matrix', fontsize=12, fontweight='bold')
    plt.xlabel('Predicted Class')
    plt.ylabel('True Class')
    plt.tight_layout()
    plt.savefig(str(EVAL_DIR / "confusion_matrix.png"), dpi=300)
    plt.close()

    # Save Evaluation Artifacts
    eval_summary = {
        "test_accuracy": round(test_acc, 4),
        "weighted_precision": round(float(precision), 4),
        "weighted_recall": round(float(recall), 4),
        "weighted_f1": round(float(f1), 4),
        "classification_report": cls_report_dict,
        "confusion_matrix": cm.tolist()
    }

    with open(EVAL_DIR / "evaluation_metrics.json", "w") as f:
        json.dump(eval_summary, f, indent=2)

    # Save Model Metadata
    metadata = {
        "model_architecture": "VGG19 with Custom Classification Head (GlobalAveragePooling2D + Dense(256) + Dropout(0.5) + Dense(4))",
        "input_dimensions": [224, 224, 3],
        "class_mapping": CLASS_INDICES,
        "preprocessing_method": "tf.keras.applications.vgg19.preprocess_input",
        "dataset": "Kaggle Eye Diseases Classification Dataset (gunavenkatdoddi/eye-diseases-classification)",
        "dataset_total_images": 4215,
        "training_date": datetime.utcnow().isoformat() + "Z",
        "test_metrics": {
            "accuracy": round(test_acc, 4),
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1_score": round(float(f1), 4)
        },
        "model_version": "1.0.0"
    }

    with open(METADATA_SAVE_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Model saved to: {MODEL_SAVE_PATH}")
    logger.info(f"Model metadata saved to: {METADATA_SAVE_PATH}")
    logger.info(f"Evaluation report saved to: {EVAL_DIR / 'evaluation_metrics.json'}")

if __name__ == "__main__":
    train()
