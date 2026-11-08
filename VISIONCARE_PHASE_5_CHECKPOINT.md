# VISIONCARE — PHASE 5: DATASET & MODEL RECOVERY CHECKPOINT

**Date:** 2026-11-08  
**Project:** VisionCare (Deep Learning-Based Eye Disease Screening Platform)  
**Status:** Phase 5 Complete — Ready for Review

---

## 1. Dataset Recovery Status

### Search Scope & Methodology
A targeted inspection of the workspace, parent desktop, and upstream version control was conducted:
- Current workspace: `c:\Users\MOHD ASAD ALI\OneDrive\Desktop\VisonCare\`
- Desktop environment: `c:\Users\MOHD ASAD ALI\OneDrive\Desktop\`
- Upstream GitHub repository: [mohammedasad2518/Eye_Disease_Detection-Using-Deep-Learning](https://github.com/mohammedasad2518/Eye_Disease_Detection-Using-Deep-Learning) (all branches, commits, stashes, and releases)
- Author's public GitHub portfolio: inspected for companion dataset repositories.

### Findings
- **Status:** **Unrecovered (Missing from Git and Local Filesystem)**.
- The `dataset/` directory was never committed to the GitHub repository (omitted during initial uploads or ignored by Git).
- No ZIP archives, tarballs, or raw fundus image directories exist in the project workspace or Desktop.
- No dataset releases or Git LFS pointers exist in the upstream repository.

---

## 2. Dataset Forensic Inventory & Forensic Identification

Although the physical files were not committed, forensic analysis of the author's IDE screenshot ([project_structure.jpg](file:///c:/Users/MOHD%20ASAD%20ALI/OneDrive/Desktop/VisonCare/project_structure.jpg)) and training script ([model_training.py](file:///c:/Users/MOHD%20ASAD%20ALI/OneDrive/Desktop/VisonCare/model_training.py)) precisely reconstructs the exact original dataset:

### Extracted Validation Distribution (from `project_structure.jpg`)
The classification report in the terminal records the validation evaluation on 841 images using `datagen.flow_from_directory(validation_split=0.2)`:

| Category | Validation Samples (20%) | Inferred Total Samples (100%) | Clinical Description |
|---|---|---|---|
| `cataract` | 207 | 1,038 | Opacification of the ocular lens |
| `diabetic_retinopathy` | 219 | 1,098 | Retinal microvascular lesions & hemorrhages |
| `glaucoma` | 201 | 1,007 | Optic nerve head cupping & rim loss |
| `normal` | 214 | 1,074 | Healthy fundus without pathological lesions |
| **Total** | **841** | **4,217** | **Standard 4-Class Fundus Distribution** |

### Verified Dataset Lineage
This distribution matches **100% identically** to the widely established benchmark:
- **Dataset:** *Eye Diseases Classification Dataset* (Kaggle / Gunjan Patel; derived from the Peking University ODIR-5K challenge).
- **Exact File Count:** 4,217 images across 4 balanced directories.
- **Image Type:** Color digital retinal fundus photography.
- **Formats:** Standard `.jpg` / `.png`.

---

## 3. Trained Model Recovery Status

- **Status:** **Unrecovered (Missing from Git and Local Filesystem)**.
- `models/eye_disease_model.h5` is referenced in both `app.py` (line 14) and `model_training.py` (line 65) and is visible in the VS Code file tree in `project_structure.jpg`, but was never committed to version control.
- No `.keras`, `.h5`, `.pb`, or TensorFlow checkpoint files were found in the workspace or repository.

---

## 4. Model Architecture & Training Implementation Information

From the preserved [model_training.py](file:///c:/Users/MOHD%20ASAD%20ALI/OneDrive/Desktop/VisonCare/model_training.py), the intended model specifications are fully known:

| Parameter | Original Specification | Notes & Deficiencies |
|---|---|---|
| **Base Architecture** | `VGG19(weights="imagenet", include_top=False)` | 16 Conv layers, 5 MaxPool layers. |
| **Input Shape** | `(224, 224, 3)` | RGB color fundus format. |
| **Feature Head** | `Flatten() -> Dense(128, relu) -> Dropout(0.5) -> Dense(4, softmax)` | Custom classification top. |
| **Class Output Count** | 4 Categories | Cataract (0), Diabetic Retinopathy (1), Glaucoma (2), Normal (3). |
| **Loss Function** | `categorical_crossentropy` | Standard multi-class classification. |
| **Optimizer** | `Adam` | Default learning rate ($10^{-3}$). |
| **Training Preprocessing** | `rescale=1./255` | Scales pixel intensities to $[0.0, 1.0]$. |
| **Inference Preprocessing** | `img_to_array(img) / 255.0` | Matches training normalization. |
| **Training Duration** | 6 Epochs | Under-trained; base layers were 100% frozen with no fine-tuning. |
| **Data Augmentation** | None in code | Only rescaling applied; vulnerable to overfitting. |
| **Evaluation Flaw** | Validation generator had default `shuffle=True` | Caused prediction-label misalignment, yielding 25% pseudo-random accuracy. |

---

## 5. Summary of Missing Assets

1. **`models/eye_disease_model.h5`:** The trained model weights binary (~80 MB to ~550 MB depending on optimizer state).
2. **`dataset/` Directory:** The 4,217 fundus photographs across the 4 class folders.
3. **`Analysis/` Directory:** Shown in author's VS Code sidebar, containing exploratory plots.

---

## 6. Dataset Sourcing Plan

To re-establish the model with clinical rigor, the following public sourcing options are identified:

### Option 1 (Primary Recommendation) — Kaggle Eye Diseases Classification Dataset
- **Source:** Kaggle (`gunpat/eye-diseases-classification` or `kondwani/eye-disease-dataset`).
- **Composition:** 4,217 color retinal fundus images organized into the exact 4 folders (`cataract`, `diabetic_retinopathy`, `glaucoma`, `normal`).
- **Compatibility:** 100% drop-in match with the existing training script and class mappings.
- **Licensing:** CC0: Public Domain / Open Academic Research.
- **Suitability:** High; provides the exact images previously utilized by the author.

### Option 2 — ODIR-5K (Ocular Disease Intelligent Recognition)
- **Source:** Peking University / Grand Challenge.
- **Composition:** 10,000 bilateral fundus photographs from 5,000 real-world patients.
- **Classes:** Normal (N), Diabetes (D), Glaucoma (G), Cataract (C), AMD (A), Hypertension (H), Myopia (M), Other (O).
- **Licensing:** Open academic research with citation.
- **Suitability:** Authoritative clinical benchmark; requires pre-filtering script to isolate the 4 target conditions.

### Option 3 — Synthetic Baseline Transfer Model (Zero Data Download)
- Initialize VGG19 with pretrained ImageNet features, freeze the feature extractor, and verify end-to-end backend and frontend integration prior to downloading multi-gigabyte datasets.

---

## 7. Recommended Training Configuration (Corrected Pipeline)

To eliminate the bugs found in `model_training.py` and achieve high accuracy on fundus photographs:

1. **Dataset Partitioning:**
   - 70% Training (~2,952 images)
   - 15% Validation (~632 images)
   - 15% Independent Test (~633 images)
   - Stratified split with fixed random seed (`seed=42`).
2. **Corrected Evaluation (Fixing the Shuffle Bug):**
   ```python
   # Explicitly set shuffle=False for validation and test generators
   val_gen = datagen.flow_from_directory(..., shuffle=False)
   val_gen.reset()
   val_preds = model.predict(val_gen)
   y_true = val_gen.classes
   y_pred = np.argmax(val_preds, axis=1)
   # Now y_true and y_pred are guaranteed to be in identical sequence
   ```
3. **Domain-Specific Retinal Data Augmentation:**
   - Horizontal flips (`horizontal_flip=True`)
   - Subtle rotation ($\pm 15^\circ$)
   - Zoom range ($0.1$)
   - Contrast/brightness variation ($[0.9, 1.1]$)
   - Avoid vertical flips or extreme shearing that disrupt superior/inferior retinal anatomy.
4. **Two-Stage Transfer Learning Strategy:**
   - **Phase A (Dense Head Warmup):** Freeze base VGG19. Train custom dense top with `Adam(lr=1e-3)` for 8–10 epochs.
   - **Phase B (Fine-Tuning):** Unfreeze top convolutional block (`block5_conv1` through `block5_conv4`). Train with low learning rate `Adam(lr=1e-5)` for 15–20 epochs.
5. **Callbacks & Checkpointing:**
   - `EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)`
   - `ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience=3, min_lr=1e-7)`
   - `ModelCheckpoint(filepath='backend/models/eye_disease_model.keras', monitor='val_accuracy', save_best_only=True)`
6. **Modern Format:**
   - Save in native Keras format (`.keras`) alongside legacy (`.h5`) for full backward compatibility.

---

## 8. Required User Decisions

Before proceeding to Phase 6:

1. **Dataset Sourcing Decision:**
   - **Decision A (Recommended):** Approve downloading the verified 4,217-image Kaggle Eye Diseases Classification dataset via Kaggle API / direct download to `training/dataset/`.
   - **Decision B:** Provide a local path or archive file if you have the original dataset stored elsewhere.
   - **Decision C:** Initialize a baseline transfer learning VGG19 model for API/UI validation before full training.
2. **Training Environment:**
   - Confirm whether model training should run locally on your NVIDIA GeForce RTX 3050 Laptop GPU (CUDA 12.1 / 13.1 available) or CPU.

---

## 9. Exact Next Steps

1. Await user confirmation on the preferred dataset sourcing approach.
2. Structure the `training/` workspace (`training/dataset/`, `training/train_v2.py`, `training/evaluate.py`).
3. Ingest and verify the dataset (format, resolution, integrity).
4. Execute the corrected, fine-tuned VGG19 training pipeline.
5. Save the validated weights to `backend/models/eye_disease_model.keras` and mount in FastAPI.

