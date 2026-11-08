"""
VisionCare Phase 10: Final Screening Workflow & Model Validation Suite
Tests against the live VisionCare API on http://127.0.0.1:8000:
1. Model invariants and health verification.
2. Image upload validation (JPG/JPEG/PNG, empty 0B, corrupted, non-image, arbitrary dimensions, large image).
3. 4-Category screening pipeline with VGG19 preprocessing across all 4 classes.
4. Numerical fidelity: finite scores, non-negative, sum to 1.0, canonical ordering.
5. Grad-CAM visual explanation (block5_conv4, bicubic upsampling, non-empty, no NaN/inf).
6. Screening history auto-archiving (1-to-1 success mapping, 0-on-failure, deletion).
7. Zero occurrences of prohibited term 'AI'.
"""

import sys
import os
import io
import json
import base64
import requests
import numpy as np
from pathlib import Path
from PIL import Image

WORKSPACE = Path(__file__).resolve().parent.parent
BASE_URL = "http://127.0.0.1:8000"

TEST_DATA_DIR = WORKSPACE / "training" / "data_splits" / "test"
TEST_IMAGES = {
    "Cataract": TEST_DATA_DIR / "Cataract" / "103_left.jpg",
    "Diabetic Retinopathy": TEST_DATA_DIR / "Diabetic Retinopathy" / "10003_left.jpeg",
    "Glaucoma": TEST_DATA_DIR / "Glaucoma" / "1212_left.jpg",
    "Normal": TEST_DATA_DIR / "Normal" / "2335_right.jpg",
}

CANONICAL_CATEGORIES = ["Cataract", "Diabetic Retinopathy", "Glaucoma", "Normal"]


def run_phase10_validation():
    print("=" * 70, flush=True)
    print("VISIONCARE PHASE 10: FINAL SCREENING WORKFLOW & MODEL VALIDATION", flush=True)
    print("=" * 70, flush=True)

    # ---------------------------------------------------------
    # 1. Health & Model Status Invariant Verification
    # ---------------------------------------------------------
    print("\n[1] Verifying Service Health & Model Invariants...", flush=True)
    health_resp = requests.get(f"{BASE_URL}/api/health", timeout=5)
    assert health_resp.status_code == 200, f"Health check failed: {health_resp.status_code}"
    hdata = health_resp.json()

    assert hdata["status"] == "healthy"
    assert hdata["app_name"] == "VisionCare API"
    model_info = hdata["model"]
    assert model_info["available"] is True
    assert model_info["file_exists"] is True
    assert model_info["tensorflow_installed"] is True
    assert model_info["categories"] == CANONICAL_CATEGORIES
    print(f"    Service Name:       {hdata['app_name']}")
    print(f"    Architecture:       {model_info['architecture']}")
    print(f"    Canonical Classes:  {model_info['categories']}")
    print("    --> Health and model invariants verified successfully.")

    # ---------------------------------------------------------
    # 2. Image Upload Validation Suite
    # ---------------------------------------------------------
    print("\n[2] Testing Image Upload Validation...", flush=True)

    # Case 2a: Empty file (0 bytes)
    resp_empty = requests.post(f"{BASE_URL}/api/predict", files={"file": ("empty.jpg", b"", "image/jpeg")}, timeout=5)
    assert resp_empty.status_code == 400, f"Expected 400 for empty file, got {resp_empty.status_code}"
    print("    [2a] Empty file (0B) rejected with HTTP 400: PASS")

    # Case 2b: Non-image text file
    resp_txt = requests.post(f"{BASE_URL}/api/predict", files={"file": ("notes.txt", b"Hello non image file", "text/plain")}, timeout=5)
    assert resp_txt.status_code == 400, f"Expected 400 for txt file, got {resp_txt.status_code}"
    print("    [2b] Non-image file (.txt) rejected with HTTP 400: PASS")

    # Case 2c: Non-image PDF file
    resp_pdf = requests.post(f"{BASE_URL}/api/predict", files={"file": ("scan.pdf", b"%PDF-1.4 header text", "application/pdf")}, timeout=5)
    assert resp_pdf.status_code == 400, f"Expected 400 for PDF file, got {resp_pdf.status_code}"
    print("    [2c] Non-image file (.pdf) rejected with HTTP 400: PASS")

    # Case 2d: Corrupted image stream (JPEG extension with garbage bytes)
    corrupted_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 20 + b"INVALID_GARBAGE_BYTES_CORRUPTED"
    resp_corrupt = requests.post(f"{BASE_URL}/api/predict", files={"file": ("corrupt.jpg", corrupted_bytes, "image/jpeg")}, timeout=5)
    assert resp_corrupt.status_code == 400, f"Expected 400 for corrupted image, got {resp_corrupt.status_code}"
    print("    [2d] Corrupted image bytes rejected with HTTP 400: PASS")

    # Case 2e: Arbitrary valid dimensions (PNG & JPEG)
    for dims in [(300, 300), (800, 600), (1024, 768)]:
        img = Image.new("RGB", dims, color=(120, 80, 50))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        resp_dims = requests.post(f"{BASE_URL}/api/predict", files={"file": (f"test_{dims[0]}x{dims[1]}.png", buf.getvalue(), "image/png")}, timeout=10)
        assert resp_dims.status_code == 200, f"Failed on dimensions {dims}: {resp_dims.status_code}"
        data = resp_dims.json()
        assert data["status"] == "success"
        print(f"    [2e] Arbitrary dimensions {dims[0]}x{dims[1]} processed smoothly: PASS")

    # Case 2f: Large image within limit (~4.5 MB)
    large_img = Image.new("RGB", (2000, 2000), color=(50, 100, 150))
    large_buf = io.BytesIO()
    large_img.save(large_buf, format="JPEG", quality=95)
    large_bytes = large_buf.getvalue()
    print(f"    Large image size: {len(large_bytes) / (1024*1024):.2f} MB")
    resp_large = requests.post(f"{BASE_URL}/api/predict", files={"file": ("large_fundus.jpg", large_bytes, "image/jpeg")}, timeout=15)
    assert resp_large.status_code == 200, f"Failed on large image: {resp_large.status_code}"
    print("    [2f] Large image (2000x2000, ~4.5MB) within limit processed: PASS")

    # ---------------------------------------------------------
    # 3. Four-Category Screening Pipeline & Numerical Verification
    # ---------------------------------------------------------
    print("\n[3] Testing Prediction Pipeline Across All 4 Categories...", flush=True)

    # Clear history to accurately test auto-archiving counts
    requests.delete(f"{BASE_URL}/api/history", timeout=5)

    prediction_records = {}

    for category, path in TEST_IMAGES.items():
        with open(path, "rb") as f:
            file_bytes = f.read()

        content_type = "image/jpeg" if path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
        resp = requests.post(f"{BASE_URL}/api/predict", files={"file": (path.name, file_bytes, content_type)}, timeout=10)
        assert resp.status_code == 200, f"Screening failed for {category}: {resp.status_code} - {resp.text}"

        data = resp.json()
        assert data["status"] == "success"
        assert "screening_id" in data and data["screening_id"] is not None

        pred = data["prediction"]
        conf = data["confidence"]
        scores = data["scores"]

        prediction_records[category] = data

        print(f"    Testing [{category}]:")
        print(f"      Filename:           {path.name}")
        print(f"      Predicted Category: {pred}")
        print(f"      Model Score:        {conf * 100:.2f}%")
        print(f"      Assigned Archive ID: #{data['screening_id']}")

        # Primary prediction assertion: must match ground truth test sample
        assert pred == category, f"Expected prediction '{category}', but got '{pred}'"

        # Four categories present and canonical
        score_keys = list(scores.keys())
        assert score_keys == CANONICAL_CATEGORIES, f"Keys mismatch canonical order: {score_keys}"

        # Finite, non-negative, and sum to 1.0
        score_values = [scores[c] for c in CANONICAL_CATEGORIES]
        assert all(isinstance(v, (int, float)) and np.isfinite(v) and v >= 0.0 for v in score_values), f"Invalid score values: {scores}"
        total_sum = sum(score_values)
        assert abs(total_sum - 1.0) < 1e-4, f"Scores do not sum to 1.0: {total_sum}"

        # Top category in scores matches prediction
        max_class = max(scores, key=scores.get)
        assert max_class == pred, f"Top class '{max_class}' does not match prediction '{pred}'"
        assert abs(scores[pred] - conf) < 1e-5, f"Top score {scores[pred]} does not match confidence {conf}"
        print(f"      Probability Sum:    {total_sum:.6f} (Finite & Normalized: PASS)")

    print("    --> All 4 categories classified with 100% agreement and strict numerical normalization.")

    # ---------------------------------------------------------
    # 4. Grad-CAM Visual Explanation Suite
    # ---------------------------------------------------------
    print("\n[4] Testing Grad-CAM Visual Explanations...", flush=True)

    for category, path in TEST_IMAGES.items():
        with open(path, "rb") as f:
            file_bytes = f.read()

        content_type = "image/jpeg" if path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
        resp = requests.post(f"{BASE_URL}/api/gradcam", files={"file": (path.name, file_bytes, content_type)}, timeout=10)
        assert resp.status_code == 200, f"Grad-CAM failed for {category}: {resp.status_code} - {resp.text}"

        gdata = resp.json()
        assert gdata["status"] == "success"
        assert gdata["target_layer"] == "block5_conv4"
        assert gdata["prediction"] == category

        # Data URLs
        heatmap_url = gdata["heatmap_data_url"]
        overlay_url = gdata["overlay_data_url"]
        assert heatmap_url.startswith("data:image/png;base64,"), "Heatmap must be a valid PNG Base64 data URL"
        assert overlay_url.startswith("data:image/png;base64,"), "Overlay must be a valid PNG Base64 data URL"

        # Decode overlay to verify valid PNG image and dimensions
        overlay_bytes = base64.b64decode(overlay_url.replace("data:image/png;base64,", ""))
        overlay_img = Image.open(io.BytesIO(overlay_bytes))
        dims = gdata["original_dimensions"]
        assert overlay_img.size == (dims[0], dims[1]), f"Overlay size {overlay_img.size} does not match {dims}"

        # Verify pixels are non-blank and non-trivial
        arr = np.array(overlay_img)
        assert arr.max() > arr.min(), "Overlay image cannot be flat/blank"
        assert np.isfinite(arr).all(), "Overlay image contains NaN or infinite pixel values"

        print(f"    Grad-CAM [{category}]: Layer {gdata['target_layer']} -> Dimensions {dims} (Valid PNG Overlay: PASS)")

    # Test error handling on Grad-CAM (out-of-range class index)
    with open(TEST_IMAGES["Normal"], "rb") as f:
        file_bytes = f.read()
    resp_bad_idx = requests.post(f"{BASE_URL}/api/gradcam?class_index=42", files={"file": ("normal.jpg", file_bytes, "image/jpeg")}, timeout=5)
    assert resp_bad_idx.status_code == 400, f"Expected 400 for class_index=42, got {resp_bad_idx.status_code}"
    print("    Grad-CAM invalid class_index=42 rejected with HTTP 400: PASS")

    # ---------------------------------------------------------
    # 5. Screening History Integration Suite
    # ---------------------------------------------------------
    print("\n[5] Testing Screening History Integration...", flush=True)

    # We cleared history before section 3, and ran 4 successful screenings (one per class)
    h_resp = requests.get(f"{BASE_URL}/api/history?limit=100", timeout=5)
    assert h_resp.status_code == 200
    h_data = h_resp.json()
    records = h_data["records"]
    total = h_data["total_count"]
    print(f"    Total Persisted History Records: {total}")
    assert total == 4, f"Expected exactly 4 history records, got {total}"

    # Verify latest record is first in order (descending by created_at)
    timestamps = [r["created_at"] for r in records]
    assert timestamps == sorted(timestamps, reverse=True), "Records not sorted descending by created_at"
    print("    [5a] Latest screening first (descending sort): PASS")

    # Verify field fidelity on first record
    first_rec = records[0]
    assert "id" in first_rec and first_rec["id"] > 0
    assert "filename" in first_rec and len(first_rec["filename"]) > 0
    assert "predicted_category" in first_rec and first_rec["predicted_category"] in CANONICAL_CATEGORIES
    assert "confidence_score" in first_rec and 0.0 <= first_rec["confidence_score"] <= 1.0
    assert "scores" in first_rec and list(first_rec["scores"].keys()) == CANONICAL_CATEGORIES
    assert "dimensions" in first_rec
    assert "image_format" in first_rec
    assert "file_size_bytes" in first_rec and first_rec["file_size_bytes"] > 0
    print(f"    [5b] Full record fidelity (id=#{first_rec['id']}, {first_rec['filename']}, {first_rec['predicted_category']}): PASS")

    # Test single record lookup
    rec_id = first_rec["id"]
    detail_resp = requests.get(f"{BASE_URL}/api/history/{rec_id}", timeout=5)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == rec_id
    assert detail["predicted_category"] == first_rec["predicted_category"]
    print(f"    [5c] Single record retrieval GET /api/history/{rec_id}: PASS")

    # Negative test on history: non-existent ID
    resp_404 = requests.get(f"{BASE_URL}/api/history/999999", timeout=5)
    assert resp_404.status_code == 404
    print("    [5d] Non-existent ID returns HTTP 404: PASS")

    # Test individual deletion
    del_resp = requests.delete(f"{BASE_URL}/api/history/{rec_id}", timeout=5)
    assert del_resp.status_code == 200
    del_check = requests.get(f"{BASE_URL}/api/history/{rec_id}", timeout=5)
    assert del_check.status_code == 404
    print(f"    [5e] Individual record deletion DELETE /api/history/{rec_id}: PASS")

    # Verify that failed predictions NEVER create history records
    count_before = requests.get(f"{BASE_URL}/api/history", timeout=5).json()["total_count"]
    # Send empty file, text file, corrupt file
    requests.post(f"{BASE_URL}/api/predict", files={"file": ("empty.jpg", b"", "image/jpeg")}, timeout=5)
    requests.post(f"{BASE_URL}/api/predict", files={"file": ("text.txt", b"plain text", "text/plain")}, timeout=5)
    requests.post(f"{BASE_URL}/api/predict", files={"file": ("corrupt.jpg", b"\x00\x01\x02", "image/jpeg")}, timeout=5)
    count_after = requests.get(f"{BASE_URL}/api/history", timeout=5).json()["total_count"]
    assert count_before == count_after, f"Failed prediction created ghost record! Before: {count_before}, After: {count_after}"
    print(f"    [5f] Failed uploads strictly never create history records ({count_before} == {count_after}): PASS")

    # ---------------------------------------------------------
    # 6. Prohibited Word 'AI' Audit
    # ---------------------------------------------------------
    print("\n[6] Auditing Prohibited Word 'AI'...", flush=True)
    import re
    # Check all responses
    for data in [hdata, detail, first_rec]:
        raw_text = json.dumps(data)
        matches = re.findall(r'\bAI\b', raw_text)
        assert len(matches) == 0, f"Found 'AI' in API payload: {matches}"
    print("    Zero occurrences of 'AI' confirmed in all tested backend payloads: PASS")

    print("\n" + "=" * 70, flush=True)
    print("PHASE 10 FINAL VALIDATION SUITE PASSED WITH 100% SUCCESS!", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    run_phase10_validation()
