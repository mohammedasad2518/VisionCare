# 👁️ Eye Disease Detection Using Deep Learning

## 📌 Overview

This project focuses on detecting and classifying eye diseases using deep learning techniques. It uses Convolutional Neural Networks (CNNs) to analyze retinal (fundus) images and predict different eye conditions.

Early detection of eye diseases like glaucoma, cataract, and diabetic retinopathy can help prevent vision loss and improve treatment outcomes.

---

## 🎯 Objectives

* Build a deep learning model for eye disease classification
* Improve accuracy using image preprocessing and CNNs
* Enable early diagnosis through automated prediction
* Create a scalable healthcare support solution

---

## 🧠 Technologies Used

* Python
* TensorFlow / Keras
* NumPy
* Pandas
* Matplotlib / Seaborn
* React + Vite + Tailwind CSS
* FastAPI + Uvicorn
* SQLAlchemy + SQLite (Screening History Archive)

---

## 📂 Dataset

The model is trained on retinal images containing different eye conditions.

### Classes:

* Cataract
* Diabetic Retinopathy
* Glaucoma
* Normal

---

## ⚙️ Methodology

1. Data Collection
2. Data Preprocessing (resizing, normalization, augmentation)
3. Model Building (CNN architecture with VGG19 transfer learning)
4. Model Training
5. Model Evaluation (accuracy, precision, recall)
6. Model Interpretability with Grad-CAM

---

## 🧩 Project Structure

```
Eye_Disease_Detection-Using-Deep-Learning/
│
├── backend/                  # FastAPI web service
│   ├── app/
│   │   ├── core/            # Configuration and settings
│   │   ├── db/              # SQLAlchemy session and database initialization
│   │   ├── models/          # SQLAlchemy ORM models (ScreeningRecord)
│   │   ├── routes/          # API endpoints (/api/health, /api/predict, /api/gradcam, /api/history)
│   │   ├── schemas/         # Pydantic request and response schemas
│   │   └── services/        # ImageService, ModelService, GradCAMService, HistoryService
│   ├── data/                # Persistent SQLite database storage (visioncare.db)
│   ├── models/              # Trained VGG19 weights (eye_disease_model.keras)
│   └── requirements.txt
│
├── frontend/                 # React + Vite application
│   ├── src/
│   │   ├── components/      # UI components (Button, Card, Badge, Header, Footer)
│   │   ├── pages/           # Home, Screening, History, NotFound
│   │   └── services/        # Centralized API service (api.js)
│   └── package.json
│
├── training/                 # Model training and verification scripts
│   ├── data_splits/         # Train, validation, and test dataset splits
│   ├── test_gradcam_verification.py
│   ├── test_phase9_history_verification.py
│   ├── test_phase9_browser.py
│   └── test_phase10_final_validation.py
│
└── README.md
```

---

## 🚀 Installation & Setup

```bash
# Clone the repository
git clone https://github.com/mohammedasad2518/Eye_Disease_Detection-Using-Deep-Learning.git

# Navigate to project folder
cd Eye_Disease_Detection-Using-Deep-Learning

# Install backend dependencies
pip install -r backend/requirements.txt

# Run FastAPI backend
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

In a separate terminal, start the React frontend:
```bash
cd frontend
npm install
npm run dev
```

---

## 📊 Results

* The model classifies multiple eye conditions from retinal fundus photographs.
* Evaluates 4 distinct categories: Cataract, Diabetic Retinopathy, Glaucoma, and Normal.
* Deep convolutional transfer learning enables fine-grained ophthalmic feature extraction.

---

## 💡 Features

* Automated disease screening
* Four-class classification
* Interactive Grad-CAM visual explanation
* Real-time model health monitoring

---

## 👨‍💻 Author

Mohammed Asad

---

## 🌐 VisionCare Web Application

VisionCare has been upgraded with a modern full-stack application architecture connecting a React frontend to a FastAPI backend powered by the trained VGG19 screening model.

### 1. How to Start the FastAPI Backend
Ensure backend dependencies are installed, then run the Uvicorn server:
```bash
# From the repository root
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Base URL: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`
- Health Endpoint: `http://127.0.0.1:8000/api/health`

### 2. How to Start the React Frontend
In a separate terminal, install Node dependencies and launch Vite:
```bash
cd frontend
npm install
npm run dev
```
- Frontend Application URL: `http://localhost:5173`
- Direct access to Screening Workspace: `http://localhost:5173/screening`

### 3. Configuring `VITE_API_BASE_URL`
The frontend communicates with the backend via the centralized service in `frontend/src/services/api.js`. Create or edit `frontend/.env`:
```env
VITE_API_BASE_URL=http://localhost:8000
```
If unset, the frontend defaults to `http://localhost:8000` with automated proxy routing configured in `frontend/vite.config.js`.

---

## 🔬 Grad-CAM Visual Explanation (Phase 8)

VisionCare incorporates **Grad-CAM (Gradient-weighted Class Activation Mapping)** to provide visual explanations of the model's classifications.

### 1. What is Grad-CAM?
Grad-CAM is an interpretability technique for convolutional neural networks. It visualizes the spatial regions of an input image that most strongly influenced the network's classification score for a particular category.

### 2. How the Grad-CAM Calculation Works
1. **Target Layer Identification:** The VGG19 architecture consists of 5 convolutional blocks. Layer `block5_conv4` (the final convolutional layer, producing 512 feature maps of spatial dimension $14 \times 14$) is selected because it captures high-level semantic and anatomical features.
2. **Gradient Computation:** When a retinal photograph is processed, `tf.GradientTape` computes the gradients of the target class score ($y^c$) with respect to each feature map activation ($A^k$) in `block5_conv4`:
   $$\frac{\partial y^c}{\partial A^k_{i,j}}$$
3. **Global Average Pooling:** Gradients are spatially pooled across the width and height to obtain neuron importance weights ($\alpha_k^c$):
   $$\alpha_k^c = \frac{1}{Z} \sum_{i} \sum_{j} \frac{\partial y^c}{\partial A^k_{i,j}}$$
4. **Weighted Combination & Rectification:** The 512 feature maps are linearly combined with their corresponding weights and passed through a Rectified Linear Unit (ReLU) to isolate features with a positive influence on the target category:
   $$L^c_{\text{Grad-CAM}} = \text{ReLU}\left( \sum_k \alpha_k^c A^k \right)$$
5. **Normalization & Resampling:** The resulting heatmap is normalized to $[0.0, 1.0]$ and upsampled to the original image dimensions using bicubic interpolation.
6. **Colormap Blending:** The normalized intensity array is mapped to an RGB heatmap using the `jet` colormap and superimposed onto the original photograph ($0.4 \times \text{Heatmap} + 0.6 \times \text{Original}$). Both images are encoded as Base64 PNG data URLs.

### 3. Grad-CAM API Endpoint (`POST /api/gradcam`)
- **Request:** Multipart form upload (`file: UploadFile`, optional `class_index: int`).
- **Response Structure:**
  ```json
  {
    "status": "success",
    "message": "Grad-CAM visual explanation generated successfully.",
    "prediction": "Glaucoma",
    "class_index": 2,
    "confidence": 0.971,
    "target_layer": "block5_conv4",
    "heatmap_data_url": "data:image/png;base64,...",
    "overlay_data_url": "data:image/png;base64,...",
    "original_dimensions": [512, 512],
    "scores": {
      "Cataract": 0.0003,
      "Diabetic Retinopathy": 0.0001,
      "Glaucoma": 0.971,
      "Normal": 0.0286
    }
  }
  ```

### 4. Frontend Visual Explanation Interface
The Screening results view features an interactive **Visual Explanation** workspace:
- **Comparison Modes:** Toggle between "Overlay", "Side-by-Side", "Heatmap", and "Original Photo".
- **Opacity Slider:** Adjust the overlay blend opacity dynamically from 20% to 100%.
- **Salience Legend:** Visual spectrum bar from deep blue (minimal contribution) to deep red (peak focus).
- **Clinical Notice:** *"The highlighted regions represent image areas that contributed to the model's classification. They are not a medical diagnosis or a confirmed disease location."*
- **Fault-Tolerant Execution:** The primary screening classification is preserved even if visualization generation encounters an issue.

---

## 📜 Screening History & Database Integration (Phase 9)

VisionCare incorporates persistent screening record management using an integrated SQLite database managed via SQLAlchemy.

### 1. Architectural Highlights & Privacy Guarantees
- **Zero Raw Image Persistence:** In strict adherence to healthcare privacy best practices, patient retinal images are never saved to disk or serialized into database BLOBs. Only evaluation metadata, timestamps, and model output probability distributions are archived.
- **Automated Lifecycle Integration:** Successful evaluations submitted through `POST /api/predict` automatically create a persisted database record and return the generated `screening_id`. Failed validations or unprocessable files never create database entries.
- **Canonical Ordering Enforcement:** All record distributions strictly preserve the canonical 4-category order: `Cataract`, `Diabetic Retinopathy`, `Glaucoma`, and `Normal`.
- **Database Engine:** SQLite at `backend/data/visioncare.db`, managed via SQLAlchemy ORM with thread-safe connection pooling and automatic schema initialization.

### 2. Database Schema (`ScreeningRecord`)
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Unique screening identifier. |
| `filename` | `VARCHAR(255)` | Original filename of uploaded fundus image. |
| `predicted_category` | `VARCHAR(64)` | Primary classified condition. |
| `confidence_score` | `FLOAT` | Confidence score in $[0.0, 1.0]$. |
| `scores_json` | `TEXT` | JSON dictionary mapping all 4 classes to probabilities. |
| `dimensions` | `VARCHAR(32)` | Image dimensions (`WIDTHxHEIGHT`). |
| `image_format` | `VARCHAR(16)` | Image format (`JPEG`, `PNG`, etc.). |
| `file_size_bytes` | `INTEGER` | Upload byte size. |
| `created_at` | `TIMESTAMP` | UTC creation timestamp. |

### 3. History API Endpoints
- **`GET /api/history`**: Retrieve screening records with pagination (`limit`, `skip`) and category filtering (`category`).
- **`GET /api/history/{id}`**: Retrieve detailed examination record by ID including the full 4-class probability distribution.
- **`DELETE /api/history/{id}`**: Permanently remove a specific screening record.
- **`DELETE /api/history`**: Clear all screening records with confirmation.

### 4. Interactive History Dashboard
The frontend `History` workspace (`http://localhost:5173/history`) provides:
- **Summary Analytics:** Real-time metrics tracking Total Archived examinations, Screening Negative count, Pathology Flags, and Latest Activity.
- **Search & Filter:** Instant filename search and category filter pills (`All`, `Cataract`, `Diabetic Retinopathy`, `Glaucoma`, `Normal`).
- **Records Table:** Clean tabular layout presenting timestamps, image attributes, categorized outcome badges, and quick actions.
- **Inspection Modal:** Modal displaying comprehensive evaluation metadata and a full horizontal bar chart showing confidence across all four categories.
- **Data Management:** Individual record deletion with live list updating and bulk archive purge with confirmation dialog.
- **States:** Graceful handling of loading spinners, empty archive states, network errors, and clinical disclaimers.

---

## 🎯 Final Screening Workflow & Model Validation (Phase 10)

Phase 10 solidifies and validates the end-to-end retinal image screening workflow, verifying rigorous data validation, classification fidelity, Grad-CAM explainability, and database history integration.

### 1. Final Screening Workflow
1. **User Upload:** Digital retinal fundus photograph (JPG, JPEG, or PNG up to 10 MB) via drag-and-drop or file browser.
2. **Multi-Stage Validation:**
   - Empty files (0 bytes) rejected with HTTP 400.
   - Non-image files (.txt, .pdf, binaries) rejected with HTTP 400.
   - Corrupted image streams caught via PIL bitmap rasterization with HTTP 400.
   - Arbitrary dimensions safely normalized and resized to $224 \times 224 \times 3$ RGB.
   - Object URLs revoked upon replace, remove, and component unmount to prevent browser memory leaks.
3. **Deep Feature Inference:** Evaluated through the trained VGG19 transfer learning backbone using standard Caffe zero-centered preprocessing.
4. **Result Presentation:**
   - Primary Classified Condition.
   - Model Score (unambiguously presented as raw model output score rather than calibrated clinical probability).
   - Four-Category Score Distribution in canonical order (`Cataract`, `Diabetic Retinopathy`, `Glaucoma`, `Normal`).
   - Image Filename & Screening Timestamp display.
   - Prominent educational and medical governance disclaimer.
5. **Grad-CAM Visual Explanation:**
   - Backpropagates class scores to final convolutional layer `block5_conv4`.
   - Bicubic upsampling to native image resolution.
   - Interactive viewer tabs (Overlay, Side-by-Side, Heatmap, Original Photo) with opacity slider and salience scale.
   - Fault-tolerant fallback: visualization issues never disturb or invalidate the primary screening outcome.
6. **Automatic Record Archiving:** Successful evaluations automatically create a persistent database record in `backend/data/visioncare.db`, while failed requests never create ghost records.

### 2. Model Evaluation Audit (Phase 6 Test Set)
Evaluated on 633 untouched test images (`training/data_splits/test/`):
- **Test Accuracy:** 89.26%
- **Weighted Precision:** 89.78%
- **Weighted Recall:** 89.26%
- **Weighted F1-Score:** 89.32%
- **Macro Average F1-Score:** 89.17%

#### Per-Class Breakdown:
| Category | Precision | Recall | F1-Score | Support | Key Clinical & Technical Insights |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Cataract** | 95.80% | 87.82% | 91.64% | 156 | High precision; mild media opacities can occasionally be confounded with normal illumination variations. |
| **Diabetic Retinopathy** | 98.78% | 98.18% | 98.48% | 165 | Outstanding sensitivity and specificity driven by distinct microaneurysms and exudate patterns. |
| **Glaucoma** | 85.61% | 78.81% | 82.07% | 151 | Lowest recall; 28 subtle early-stage optic cup enlargements were classified as normal due to lack of 3D stereoscopic depth. |
| **Normal** | 78.61% | 91.30% | 84.48% | 161 | High recall ensures healthy retinas are flagged negative; lower precision reflects conservative triage. |

### 3. Verification Suite
All automated tests pass with 100% success:
- `python -u training/test_phase10_final_validation.py`: Complete screening workflow, upload validation, 4-class inference, Grad-CAM, and history integration.
- `python training/test_phase9_history_verification.py`: Full CRUD, restart persistence, and negative tests.
- `python training/test_gradcam_verification.py`: Direct and HTTP Grad-CAM verification.
- `python -u training/test_phase9_browser.py`: End-to-end Chrome Headless browser automation.
- `npm run lint` & `npm run build`: Zero errors, zero warnings.

---

*Note: VisionCare is an educational screening prototype and is not clinical-grade or a substitute for professional medical examination.*
