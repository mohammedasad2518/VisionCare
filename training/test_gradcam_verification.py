"""
VisionCare Phase 8: Comprehensive Grad-CAM Verification Suite
Tests:
1. Direct Grad-CAM service calculation across all 4 categories:
   - Cataract
   - Diabetic Retinopathy
   - Glaucoma
   - Normal
2. Finite pixel values and non-blank overlay assertions.
3. Live HTTP endpoint testing with Uvicorn server (POST /api/predict vs POST /api/gradcam).
4. Error cases (empty file, invalid MIME, corrupted image, out-of-range class index).
"""

import sys
import io
import time
import base64
import subprocess
from pathlib import Path
from PIL import Image
import numpy as np
import requests

workspace_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(workspace_root))

from backend.app.services.gradcam_service import gradcam_service
from backend.app.services.model_service import model_service

PORT = 8009
BASE_URL = f"http://127.0.0.1:{PORT}"

TEST_CASES = [
    {
        "category": "Cataract",
        "path": workspace_root / "training" / "data_splits" / "test" / "Cataract" / "103_left.jpg",
    },
    {
        "category": "Diabetic Retinopathy",
        "path": workspace_root / "training" / "data_splits" / "test" / "Diabetic Retinopathy" / "10003_left.jpeg",
    },
    {
        "category": "Glaucoma",
        "path": workspace_root / "training" / "data_splits" / "test" / "Glaucoma" / "1212_left.jpg",
    },
    {
        "category": "Normal",
        "path": workspace_root / "training" / "data_splits" / "test" / "Normal" / "2335_right.jpg",
    },
]


def test_gradcam_direct():
    print("=" * 65, flush=True)
    print("1. DIRECT GRAD-CAM SERVICE VERIFICATION (ALL 4 CATEGORIES)", flush=True)
    print("=" * 65, flush=True)
    assert model_service.is_available, "ModelService must be loaded and available"

    for case in TEST_CASES:
        category = case["category"]
        file_path = case["path"]
        print(f"\n[Direct] Evaluating: {category} ({file_path.name})", flush=True)

        assert file_path.exists(), f"Image file not found: {file_path}"
        img = Image.open(file_path)
        orig_w, orig_h = img.size

        # Run Grad-CAM service
        result = gradcam_service.generate_gradcam(img)

        # 1. Structure validation
        assert result["status"] == "success"
        assert result["target_layer"] == "block5_conv4"
        assert result["original_dimensions"] == (orig_w, orig_h)
        assert 0.0 <= result["confidence"] <= 1.0
        assert len(result["scores"]) == 4

        # 2. Base64 format validation
        assert result["heatmap_data_url"].startswith("data:image/png;base64,")
        assert result["overlay_data_url"].startswith("data:image/png;base64,")

        # 3. Decode overlay to verify finite values and non-blank image
        overlay_b64 = result["overlay_data_url"].split(",")[1]
        overlay_bytes = base64.b64decode(overlay_b64)
        overlay_pil = Image.open(io.BytesIO(overlay_bytes))
        overlay_np = np.array(overlay_pil)

        assert overlay_pil.size == (orig_w, orig_h), f"Dimension mismatch: expected {(orig_w, orig_h)}, got {overlay_pil.size}"
        assert not np.isnan(overlay_np).any(), "NaN values found in overlay"
        assert np.isfinite(overlay_np).all(), "Non-finite values found in overlay"
        assert overlay_np.max() > overlay_np.min(), "Overlay is completely blank"

        # 4. Decode heatmap to verify finite values
        heatmap_b64 = result["heatmap_data_url"].split(",")[1]
        heatmap_bytes = base64.b64decode(heatmap_b64)
        heatmap_pil = Image.open(io.BytesIO(heatmap_bytes))
        heatmap_np = np.array(heatmap_pil)

        assert heatmap_pil.size == (orig_w, orig_h), f"Dimension mismatch: expected {(orig_w, orig_h)}, got {heatmap_pil.size}"
        assert not np.isnan(heatmap_np).any(), "NaN values found in heatmap"
        assert np.isfinite(heatmap_np).all(), "Non-finite values found in heatmap"

        print(f"  --> PASS: Pred='{result['prediction']}' (Score={result['confidence']:.4f}) | Dim={overlay_pil.size} | Overlay range=[{overlay_np.min()}, {overlay_np.max()}]", flush=True)


def test_gradcam_http():
    print("\n" + "=" * 65, flush=True)
    print("2. LIVE HTTP ENDPOINT VERIFICATION (POST /api/predict & /api/gradcam)", flush=True)
    print("=" * 65, flush=True)

    # Start live Uvicorn server
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(PORT),
        "--log-level",
        "warning"
    ]
    print(f"Starting temporary Uvicorn server on port {PORT}...", flush=True)
    log_file = open("gradcam_uvicorn.log", "w", encoding="utf-8")
    server_proc = subprocess.Popen(
        cmd,
        cwd=str(workspace_root),
        stdout=log_file,
        stderr=log_file,
        text=True
    )

    try:
        # Wait for startup
        started = False
        for attempt in range(25):
            time.sleep(1.5)
            try:
                resp = requests.get(f"{BASE_URL}/api/health", timeout=3)
                if resp.status_code == 200:
                    started = True
                    print(f"Server is ready after ~{(attempt + 1) * 1.5:.1f}s!", flush=True)
                    break
            except Exception:
                pass

        assert started, "Server failed to respond within 35 seconds."

        # Test each class through actual HTTP requests
        for case in TEST_CASES:
            category = case["category"]
            file_path = case["path"]
            filename = file_path.name
            content_type = "image/jpeg" if file_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"

            print(f"\n[HTTP] Testing: {category} ({filename})", flush=True)

            with open(file_path, "rb") as f:
                img_data = f.read()

            # 1. POST /api/predict
            pred_resp = requests.post(
                f"{BASE_URL}/api/predict",
                files={"file": (filename, io.BytesIO(img_data), content_type)},
                timeout=15
            )
            assert pred_resp.status_code == 200, f"/api/predict failed: {pred_resp.text}"
            pred_data = pred_resp.json()

            # 2. POST /api/gradcam
            grad_resp = requests.post(
                f"{BASE_URL}/api/gradcam",
                files={"file": (filename, io.BytesIO(img_data), content_type)},
                timeout=15
            )
            assert grad_resp.status_code == 200, f"/api/gradcam failed: {grad_resp.text}"
            grad_data = grad_resp.json()

            # 3. Assert predictions and confidences match
            assert pred_data["prediction"] == grad_data["prediction"], (
                f"Prediction mismatch: predict='{pred_data['prediction']}', gradcam='{grad_data['prediction']}'"
            )
            assert abs(pred_data["confidence"] - grad_data["confidence"]) < 1e-4, (
                f"Confidence mismatch: predict={pred_data['confidence']}, gradcam={grad_data['confidence']}"
            )
            assert grad_data["target_layer"] == "block5_conv4"
            assert grad_data["heatmap_data_url"].startswith("data:image/png;base64,")
            assert grad_data["overlay_data_url"].startswith("data:image/png;base64,")

            print(f"  --> PASS: HTTP Predict='{pred_data['prediction']}' matches GradCAM='{grad_data['prediction']}' (Score={grad_data['confidence']:.4f})", flush=True)

        # 4. Error Cases
        print("\n" + "=" * 65, flush=True)
        print("3. HTTP 4XX ERROR HANDLING CHECKS", flush=True)
        print("=" * 65, flush=True)

        # A. Corrupted image
        print("\nTest A: Corrupted image stream...", flush=True)
        corrupt_resp = requests.post(
            f"{BASE_URL}/api/gradcam",
            files={"file": ("corrupt.jpg", io.BytesIO(b"NOT_A_REAL_JPEG_IMAGE_HEADER_DATA_12345"), "image/jpeg")},
            timeout=5
        )
        assert corrupt_resp.status_code == 400, f"Expected 400, got {corrupt_resp.status_code}"
        print(f"  --> PASS: Rejected corrupted image with HTTP 400: '{corrupt_resp.json().get('detail')}'", flush=True)

        # B. Non-image file format (.txt)
        print("\nTest B: Non-image format (text/plain)...", flush=True)
        txt_resp = requests.post(
            f"{BASE_URL}/api/gradcam",
            files={"file": ("document.txt", io.BytesIO(b"Sample plain text file"), "text/plain")},
            timeout=5
        )
        assert txt_resp.status_code == 400, f"Expected 400, got {txt_resp.status_code}"
        print(f"  --> PASS: Rejected unsupported format with HTTP 400: '{txt_resp.json().get('detail')}'", flush=True)

        # C. Empty file (0 bytes)
        print("\nTest C: Empty file (0 bytes)...", flush=True)
        empty_resp = requests.post(
            f"{BASE_URL}/api/gradcam",
            files={"file": ("empty.png", io.BytesIO(b""), "image/png")},
            timeout=5
        )
        assert empty_resp.status_code == 400, f"Expected 400, got {empty_resp.status_code}"
        print(f"  --> PASS: Rejected empty file with HTTP 400: '{empty_resp.json().get('detail')}'", flush=True)

        # D. Invalid class index
        print("\nTest D: Out-of-bounds class_index (99)...", flush=True)
        first_img_path = TEST_CASES[0]["path"]
        with open(first_img_path, "rb") as f:
            valid_bytes = f.read()
        idx_resp = requests.post(
            f"{BASE_URL}/api/gradcam?class_index=99",
            files={"file": (first_img_path.name, io.BytesIO(valid_bytes), "image/jpeg")},
            timeout=5
        )
        assert idx_resp.status_code == 400, f"Expected 400, got {idx_resp.status_code}"
        print(f"  --> PASS: Rejected out-of-bounds class index with HTTP 400: '{idx_resp.json().get('detail')}'", flush=True)

    finally:
        print("\nShutting down Uvicorn test server...", flush=True)
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
            print("Server terminated cleanly.", flush=True)
        except subprocess.TimeoutExpired:
            server_proc.kill()
            server_proc.wait()
            print("Server process killed after timeout.", flush=True)
        try:
            log_file.close()
        except Exception:
            pass


if __name__ == "__main__":
    test_gradcam_direct()
    test_gradcam_http()
    print("\n" + "=" * 65, flush=True)
    print("ALL PHASE 8 GRAD-CAM VERIFICATION TESTS PASSED SUCCESSFULLY!", flush=True)
    print("=" * 65, flush=True)
