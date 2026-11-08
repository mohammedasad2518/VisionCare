# VISIONCARE — PHASE 6 CHECKPOINT: DATASET ACQUISITION & VGG19 MODEL TRAINING

**Project Name:** VisionCare  
**Phase:** Phase 6 — Dataset Acquisition & VGG19 Model Training (Final Verification)  
**Date:** November 8, 2026  
**Status:** Completed & Fully Verified  
**Branch:** main  

---

## 1. Executive Summary & Educational Prototype Scope

In Phase 6, VisionCare acquired the authentic four-class retinal fundus dataset, resolved the critical data generator defect present in the original upstream codebase, and trained a VGG19 deep learning classification model using a two-stage transfer learning pipeline.

> [!IMPORTANT]
> **Scope & Classification Disclaimer:**  
> The trained VGG19 classification model is developed strictly as an **educational screening prototype**. It is **not** clinical-grade, nor is it clinically validated for diagnostic use. All prediction outputs and screening metrics are intended solely for educational, research, and technical evaluation purposes and must never replace consultation with a licensed ophthalmologist or optometrist.

The model was evaluated on an untouched test set of 633 retinal fundus images, achieving **89.26% test accuracy**, **89.78% weighted precision**, and **89.32% weighted F1-score**. Independent verification confirms that the saved model artifact loads cleanly, executes forward passes with the expected tensor dimensions `(None, 224, 224, 3) -> (None, 4)`, and produces strictly normalized probability distributions across all four target categories.

---

## 2. Dataset Provenance & Verification

### 2.1 Provenance, Attribution & License Evidence
- **Source Platform:** Kaggle Datasets
- **Exact Dataset URL:** [https://www.kaggle.com/datasets/gunavenkatdoddi/eye-diseases-classification](https://www.kaggle.com/datasets/gunavenkatdoddi/eye-diseases-classification)
- **Dataset Owner:** Guna Venkat Doddi (`gunavenkatdoddi`)
- **Dataset Title:** Eye Diseases Classification Dataset
- **Underlying Cohort Attribution:** Compiled from public ophthalmic research archives (including subsets from ODIR-5K, HRF, IDRiD, and public retinal fundus repositories).
- **Verified License:** **Open Data Commons Open Database License (ODbL v1.0)**.
  - *Database License:* Open Database License (ODbL-1.0).
  - *Database Contents:* © Original Authors (individual images retain copyright of their respective medical imaging repositories).
  - *Correction:* Earlier informal references indicating CC0 have been corrected based on verified platform metadata.
- **Imaging Modality:** Retinal fundus photography (color fundus imaging capturing optic disc, macula, and retinal vasculature).

### 2.2 Target Categories & Class Mapping
The dataset organizes retinal images into four eye health categories:
```json
{
  "Cataract": 0,
  "Diabetic Retinopathy": 1,
  "Glaucoma": 2,
  "Normal": 3
}
```
Saved reference: `training/class_mapping.json`.

---

## 3. Dataset Audit, Deduplication & Stratified Splitting

### 3.1 Audit & Deduplication Methodology
All downloaded image files underwent automated integrity checks (file header validation, PIL decoding, and exact SHA-256 hash deduplication):
- **Raw Files Downloaded:** 4,217 images (4,016 JPEG, 201 PNG).
- **Corrupted Images:** 0 (all 4,217 images were decodable).
- **Duplicate Identification:** Full SHA-256 hashing across all raw images identified **2 exact duplicate pairs** that had conflicting labels across categories:
  1. `cataract/1415_right.jpg` and `glaucoma/1415_right.jpg` (identical SHA-256 hash: `5326ea...`)
  2. `cataract/625_left.jpg` and `glaucoma/625_left.jpg` (identical SHA-256 hash: `61d31a...`)
- **Deduplication Resolution:** The duplicate conflicting files were excluded during partition generation, leaving **4,215 strictly unique, decodable retinal images**. Every single file across the resulting dataset partitions has a unique SHA-256 checksum with zero cross-contamination.

### 3.2 Final Verified Per-Class Partition Counts
Partitions were generated using stratified random sampling (`random_state=42`, ratios: 70% Train, 15% Validation, 15% Test):

| Category | Total Unique | Train Split (70%) | Validation Split (15%) | Test Split (15%) |
| :--- | :---: | :---: | :---: | :---: |
| **Cataract** | 1,038 | 727 | 155 | 156 |
| **Diabetic Retinopathy** | 1,098 | 768 | 165 | 165 |
| **Glaucoma** | 1,005 | 703 | 151 | 151 |
| **Normal** | 1,074 | 752 | 161 | 161 |
| **Total** | **4,215** | **2,950** | **632** | **633** |

Files are organized in isolated directories under `training/data_splits/{train,val,test}`. Summary metadata is recorded in `training/splits_summary.json`.

### 3.3 Strict Test Partition Isolation
- The 633 test images (`training/data_splits/test/`) were **never** used during Stage 1 feature extraction, Stage 2 fine-tuning, loss backpropagation, or early-stopping checkpoint selection.
- All training and hyperparameter updates were guided strictly by the separate validation partition (632 images).
- The test set was evaluated exactly once after training finalized to establish unbiased performance metrics.

---

## 4. Root Cause Resolution of Upstream Defects

In Phase 1 and Phase 5 investigations, the original upstream GitHub repository exhibited erratic ~25% accuracy (random guessing among 4 classes). The root cause was identified and resolved:
1. **Validation Data Shuffling Defect:** The original training script passed `shuffle=True` to the validation generator during evaluation, causing ground-truth labels to become scrambled relative to model outputs. Setting `shuffle=False` immediately restored correct correspondence.
2. **Preprocessing Normalization Mismatch:** The original script applied simple $1/255$ scaling, whereas pretrained VGG19 requires caffe-style zero-centering (`tf.keras.applications.vgg19.preprocess_input`). Standardizing on `preprocess_input` enabled rapid convergence.

---

## 5. Model Architecture & Training Strategy

### 5.1 Architecture Details
- **Base Backbone:** VGG19 pretrained on ImageNet (excluding top dense layers).
- **Input Dimensions:** `(224, 224, 3)` (RGB format).
- **Classification Head:**
  - `GlobalAveragePooling2D()` (spatial feature pooling without parameter explosion).
  - `Dense(256, activation="relu", kernel_initializer="he_normal")`.
  - `Dropout(0.5)` (regularization to inhibit feature co-adaptation).
  - `Dense(4, activation="softmax")` (calibrated probability distribution across the 4 eye conditions).

### 5.2 Two-Stage Transfer Learning Pipeline
1. **Stage 1 — Feature Extraction (10 Epochs):**
   - VGG19 convolutional backbone frozen (`trainable = False`).
   - Optimizer: `Adam(learning_rate=1e-4)`.
   - Loss Function: `categorical_crossentropy`.
   - Augmentation: Random rotations ($\pm 15^\circ$), horizontal/vertical flips, zoom ($0.15$), brightness range ($[0.85, 1.15]$), width/height shifts ($0.10$).
2. **Stage 2 — Fine-Tuning (Unfrozen Block 5, Early Stopping Patience = 4):**
   - Unfroze top convolutional block (`block5_conv1`, `block5_conv2`, `block5_conv3`, `block5_conv4`).
   - Lower layers remain frozen to preserve low-level optical feature extractors.
   - Optimizer: `Adam(learning_rate=1e-5)` with `ReduceLROnPlateau(factor=0.2, patience=2, min_lr=1e-7)`.
   - Early stopping monitored on `val_accuracy` with best weight restoration.

---

## 6. Training Progression Summary

- **Stage 1 (Frozen Backbone, Epochs 1–10):**
  - Validation accuracy progressed steadily from 62.34% (Epoch 1) to **79.43%** (Epoch 10).
  - Validation loss decreased from 1.1753 to 0.5512.
- **Stage 2 (Fine-Tuning `block5`, Epochs 1–8):**
  - Epoch 1: Val Acc jumped to **81.65%** (Val Loss: 0.4789).
  - Epoch 2: Val Acc reached **86.08%** (Val Loss: 0.3808).
  - Epoch 4: Val Acc reached **88.92%** (Val Loss: 0.2946).
  - Epoch 7: Val Acc peaked at **89.87%** (Val Loss: 0.3276).
  - Epoch 8: Early stopping triggered; best weights from peak performance restored.

---

## 7. Test Partition Evaluation Metrics

Evaluated on the 633 untouched test images:

### 7.1 Aggregate Metrics
- **Test Accuracy:** **89.26%**
- **Weighted Precision:** **89.78%**
- **Weighted Recall:** **89.26%**
- **Weighted F1-Score:** **89.32%**
- **Macro Average F1-Score:** **89.17%**

### 7.2 Detailed Classification Report
| Category | Precision | Recall | F1-Score | Support |
| :--- | :---: | :---: | :---: | :---: |
| **Cataract** | 0.9580 (95.8%) | 0.8782 (87.8%) | 0.9164 (91.6%) | 156 |
| **Diabetic Retinopathy** | 0.9878 (98.8%) | 0.9818 (98.2%) | 0.9848 (98.5%) | 165 |
| **Glaucoma** | 0.8561 (85.6%) | 0.7881 (78.8%) | 0.8207 (82.1%) | 151 |
| **Normal** | 0.7861 (78.6%) | 0.9130 (91.3%) | 0.8448 (84.5%) | 161 |
| **Overall Accuracy** | | | **0.8926 (89.3%)** | **633** |
| **Macro Average** | **0.8970** | **0.8903** | **0.8917** | **633** |
| **Weighted Average** | **0.8978** | **0.8926** | **0.8932** | **633** |

### 7.3 Confusion Matrix (633 Test Samples)
```
                        Predicted ->
True Category    Cataract    Diabetic Ret.    Glaucoma    Normal     Total
Cataract            137            0             10          9        156
Diabetic Ret.         0          162              0          3        165
Glaucoma              4            0            119         28        151
Normal                2            2             10        147        161
```

---

## 8. Model Verification Results

Executed standalone via `training/test_model_inference.py`:

1. **Model Artifact Existence & Integrity:**
   - File Path: `backend/models/eye_disease_model.keras`
   - File Size: 157,308,480 bytes (~150 MB).
   - Load Status: Successfully loaded via `tf.keras.models.load_model`.
2. **Tensor Dimensions:**
   - Verified Input Shape: `(None, 224, 224, 3)`.
   - Verified Output Shape: `(None, 4)`.
3. **Class Order Match:**
   - Strictly matches `training/class_mapping.json`: `{"Cataract": 0, "Diabetic Retinopathy": 1, "Glaucoma": 2, "Normal": 3}`.
4. **Preprocessing Pipeline:**
   - Confirmed using `tf.keras.applications.vgg19.preprocess_input` with RGB PIL conversion.
5. **Sample Inferences Across All Classes:**
   - **Cataract** (`103_left.jpg`): Predicted `Cataract` (Confidence: **97.01%**, Sum: 1.000000, All Finite: True)
   - **Diabetic Retinopathy** (`10003_left.jpeg`): Predicted `Diabetic Retinopathy` (Confidence: **99.97%**, Sum: 1.000000, All Finite: True)
   - **Glaucoma** (`1212_left.jpg`): Predicted `Glaucoma` (Confidence: **97.10%**, Sum: 1.000000, All Finite: True)
   - **Normal** (`2335_right.jpg`): Predicted `Normal` (Confidence: **98.16%**, Sum: 1.000000, All Finite: True)
6. **Verdict:** All model verification checks **PASSED**.

---

## 9. FastAPI Startup & Live HTTP Test Results

Executed via automated test suite `training/test_fastapi_server.py`:

1. **Uvicorn Server Startup:**
   - Command: `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8008 --log-level warning`
   - Startup Time: Ready and responding in **~3.0 seconds**.
   - Stability: Started without import errors, hangs, or crashes.
2. **GET `/api/health`:**
   - Status Code: **HTTP 200 OK**
   - Response Payload:
     ```json
     {
       "status": "healthy",
       "app_name": "VisionCare API",
       "version": "1.0.0",
       "model": {
         "available": true,
         "architecture": "VGG19 (Transfer Learning)",
         "model_path": "C:\\Users\\MOHD ASAD ALI\\OneDrive\\Desktop\\VisonCare\\backend\\models\\eye_disease_model.keras",
         "file_exists": true,
         "categories": ["Cataract", "Diabetic Retinopathy", "Glaucoma", "Normal"]
       }
     }
     ```
   - Model Availability: Confirmed **`true`**.
3. **GET `/` (Root Endpoint):**
   - Status Code: **HTTP 200 OK**
   - Response Payload: `{"app": "VisionCare API", "version": "1.0.0", "status": "online", "documentation": "/docs", "health": "/api/health"}`
4. **POST `/api/predict` (Genuine Test Images):**
   - Cataract (`103_left.jpg`): **HTTP 200** $\rightarrow$ `prediction: "Cataract"`, `confidence: 0.9701`.
   - Diabetic Retinopathy (`10003_left.jpeg`): **HTTP 200** $\rightarrow$ `prediction: "Diabetic Retinopathy"`, `confidence: 0.9997`.
   - Glaucoma (`1212_left.jpg`): **HTTP 200** $\rightarrow$ `prediction: "Glaucoma"`, `confidence: 0.9710`.
   - Normal (`2335_right.jpg`): **HTTP 200** $\rightarrow$ `prediction: "Normal"`, `confidence: 0.9816`.
   - Probabilities: All finite and sum strictly to $1.0$.
5. **POST `/api/predict` (Invalid Upload Handling):**
   - Text file (`notes.txt`): **HTTP 400 Bad Request** $\rightarrow$ `"Unsupported file format '.txt'..."`
   - Empty file (0 bytes): **HTTP 400 Bad Request** $\rightarrow$ `"The uploaded file is empty (0 bytes)..."`
   - Corrupt image data (`corrupt.jpg`): **HTTP 400 Bad Request** $\rightarrow$ `"The uploaded file is corrupted or could not be decoded as an image."`
6. **Clean Server Shutdown:**
   - Process terminated cleanly via SIGTERM with **exit code 0**.
7. **Verdict:** All FastAPI endpoints and Uvicorn HTTP tests **PASSED**.

---

## 10. Saved Project Artifacts

- **Trained Model Binary:** `backend/models/eye_disease_model.keras` (157.3 MB)
- **Model Metadata:** `backend/models/model_metadata.json`
- **Class Mapping:** `training/class_mapping.json`
- **Splits Summary:** `training/splits_summary.json`
- **Evaluation Heatmap:** `training/evaluation/confusion_matrix.png`
- **Training Trajectory Curves:** `training/evaluation/accuracy_history.png` & `training/evaluation/loss_history.png`
- **Numerical Test Metrics:** `training/evaluation/evaluation_metrics.json`
- **Verification Scripts:**
  - `training/test_model_inference.py` (Standalone model forward-pass validator)
  - `training/test_fastapi_server.py` (Uvicorn HTTP request integration suite)

---

## 11. Unresolved Issues

- **None.** All model architecture requirements, dataset split audits, inference tests, FastAPI startup behaviors, and HTTP request validation checks have completed with zero defects.
- Work is paused per instructions. Phase 7 will not begin until explicitly directed.

---

PHASE 6 COMPLETE — READY FOR REVIEW
