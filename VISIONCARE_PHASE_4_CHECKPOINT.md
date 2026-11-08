# VISIONCARE — PHASE 4: FASTAPI BACKEND FOUNDATION CHECKPOINT

**Date:** 2026-11-08  
**Project:** VisionCare (Deep Learning-Based Eye Disease Screening Platform)  
**Status:** Phase 4 Complete — Ready for Review

---

## 1. Executive Summary

Phase 4 established the clean, modular, and maintainable **FastAPI backend** for **VisionCare** located in `backend/`. 

Key architectural accomplishments:
- **Lightweight & Resilient:** Designed to boot and run reliably using the existing Python 3.10 environment without crashing or requiring TensorFlow to be pre-installed.
- **Medical Integrity First:** Accurately reports the model as unavailable rather than generating synthetic confidence scores, random predictions, or dummy classifications.
- **Robust Image Processing:** Implemented comprehensive in-memory Pillow image validation (MIME, file extension, max 10 MB, corruption checks, 0-byte checks, and RGB conversion).
- **Interactive Documentation:** Automatic OpenAPI and Swagger UI documentation available at `http://localhost:8000/docs`.
- **Full Test Coverage:** 10 automated test scenarios verifying root, health, documentation, image validation, oversized/corrupted files, and HTTP 503 error handling.
- **Strict Compliance:** Zero occurrences of the word "AI" across backend configurations, logs, routes, and schemas. All original files and frontend modules were preserved without modification.

---

## 2. Backend Structure

```
backend/
├── .env.example                         # Environment configuration template
├── requirements.txt                     # Lightweight backend dependencies
├── test_api.py                          # Automated 10-point test suite
└── app/
    ├── __init__.py                      # Package descriptor
    ├── main.py                          # FastAPI instance, CORS, error handlers, root endpoint
    ├── core/
    │   ├── __init__.py
    │   └── config.py                    # Settings, CORS origins, paths, target categories
    ├── routes/
    │   ├── __init__.py
    │   ├── health.py                    # GET /api/health endpoint
    │   └── prediction.py                # POST /api/predict endpoint
    ├── services/
    │   ├── __init__.py
    │   ├── image_service.py             # Pillow-based validation, dimension & corruption checks
    │   └── model_service.py             # VGG19 model loader & availability interface
    └── schemas/
        ├── __init__.py
        └── prediction.py                # Pydantic v2 schemas for health, image & prediction responses
```

---

## 3. API Endpoints

| Method | Path | Summary | Description & Behavior |
|---|---|---|---|
| `GET` | `/` | API Root | Returns service identity, online status, and links to `/docs` and `/api/health`. |
| `GET` | `/api/health` | System Health | Returns operational status (`"healthy"`), version (`"1.0.0"`), and model metadata (`available: false`, `architecture: "Not configured"`, target categories). |
| `POST` | `/api/predict` | Screen Retinal Image | Accepts a fundus photograph via `multipart/form-data`. Validates image integrity and format. Since the model weights are not configured, returns `HTTP 503 Service Unavailable` with message: *"Screening service is temporarily unavailable because the classification model has not been configured."* |
| `GET` | `/docs` | Swagger UI | Interactive API explorer and testing interface. |
| `GET` | `/redoc` | ReDoc UI | Alternative OpenAPI documentation interface. |

---

## 4. Dependencies

The backend was purposefully built to operate on the pre-installed standard Python 3.10 packages without forcing heavy or incompatible installs:

### Core Dependencies (`backend/requirements.txt`)
- `fastapi` (`>=0.110.0`): Asynchronous REST API framework.
- `uvicorn[standard]` (`>=0.28.0`): High-performance ASGI web server.
- `pydantic` (`>=2.0.0`): Request and response data validation.
- `sqlalchemy` (`>=2.0.0`): Database abstraction layer for SQLite history.
- `pillow` (`>=10.0.0`): Image decoding, dimension verification, and color conversion.
- `python-multipart` (`>=0.0.9`): Form-data and file upload streaming.

---

## 5. Image Validation Functionality (`image_service.py`)

The `ImageService` processes images purely in-memory (no permanent disk writes) and applies the following clinical validation pipeline:

1. **Extension Verification:** Rejects any file whose extension is not in `{jpg, jpeg, png}`.
2. **Stream Length & Empty File Check:** Catches 0-byte uploads (`HTTP 400`).
3. **Size Ceiling:** Enforces the `10 MB` maximum limit (`HTTP 400`).
4. **Data Integrity & Decoding:** Uses Pillow's `img.load()` to force a raster decode. Catches truncated files, corrupted byte streams, and syntax errors (`HTTP 400`).
5. **Format Validation:** Confirms Pillow detects true `"JPEG"` or `"PNG"` encoding.
6. **Color Space Standardization:** Automatically converts Grayscale, CMYK, or RGBA images to pure 3-channel `"RGB"`.
7. **Metadata Extraction:** Returns natural dimensions (`width × height px`), size in bytes, and detected format.

---

## 6. Model Availability Handling (`model_service.py`)

- **Soft Dependency on TensorFlow:** Checks `import tensorflow` inside a `try/except` block. If TensorFlow is absent, logs an informative notice and runs in lightweight mode without crashing.
- **Honest Availability Reporting:** Checks if `models/eye_disease_model.h5` exists. Since upstream repository lacked model weights, `is_available` returns `False`.
- **Protection Against Fake Predictions:** The `predict()` method refuses to generate synthetic random outputs, ensuring clinical integrity.
- **Seamless Upgrade Path:** Once trained weights are supplied, `ModelService.initialize_model()` will load the Keras model with zero architectural refactoring required in the route handlers.

---

## 7. Test Results

The test suite (`backend/test_api.py`) executed 10 automated test cases with **100% pass rate**:

```
============================================================
VISIONCARE FASTAPI BACKEND TEST SUITE
============================================================

[1/10] Testing Root endpoint (GET /)...
  PASS: {'app': 'VisionCare API', 'version': '1.0.0', 'status': 'online', 'documentation': '/docs', 'health': '/api/health'}

[2/10] Testing Health endpoint (GET /api/health)...
  PASS: Model accurately reported as available=False

[3/10] Testing Swagger documentation (GET /docs)...
  PASS: Swagger UI available at /docs

[4/10] Testing Valid JPG Upload (POST /api/predict)...
  PASS: Validated JPG successfully and cleanly returned 503 notice: Screening service is temporarily unavailable because the classification model has not been configured.

[5/10] Testing Valid PNG Upload (POST /api/predict)...
  PASS: Validated PNG successfully and cleanly returned 503 notice

[6/10] Testing Invalid File Format (.txt)...
  PASS: Rejected .txt file: Unsupported file format '.txt'. Only JPG, JPEG, and PNG retinal photographs are accepted.

[7/10] Testing Oversized File (> 10 MB)...
  PASS: Rejected oversized file: File size (10.00 MB) exceeds maximum allowed limit of 10 MB.

[8/10] Testing Corrupted Image Upload...
  PASS: Detected corrupted file: The uploaded file is corrupted or could not be decoded as an image.

[9/10] Testing Empty File (0 Bytes)...
  PASS: Detected empty file: The uploaded file is empty (0 bytes). Please provide a valid retinal photograph.

[10/10] Testing Validation Error for Missing File Payload...
  PASS: Custom 422 validation handler functioning as expected

============================================================
ALL 10 TEST CASES PASSED SUCCESSFULLY!
============================================================
```

---

## 8. Server Status

- **Host & Port:** `http://127.0.0.1:8000`
- **Root Status:** `200 OK`
- **Health Status:** `200 OK` (`model.available: false`)
- **Documentation:** Interactive Swagger UI active at `http://127.0.0.1:8000/docs`
- **CORS Configured:** Allows cross-origin requests from frontend instances on ports `5173`, `5174`, and `3000`.

---

## 9. Known Limitations

- **Model Execution:** Real VGG19 inference is awaiting model weights (`models/eye_disease_model.h5`).
- **Grad-CAM & PDF Generation:** Services will be wired into the prediction and report routes once model weights are mounted in subsequent phases.

---

## 10. Instructions for Running the Backend

From the repository root:

```bash
# 1. Navigate to backend directory
cd backend

# 2. Start Uvicorn development server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 3. Open API documentation in browser
http://127.0.0.1:8000/docs

# 4. Run test suite
python test_api.py
```

