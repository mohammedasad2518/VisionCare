import io
import sys
from pathlib import Path
from PIL import Image

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def create_test_image(format="JPEG", size=(300, 300), color="blue") -> bytes:
    """Creates a real in-memory image for testing."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()

def run_tests():
    print("\n" + "=" * 60)
    print("VISIONCARE FASTAPI BACKEND TEST SUITE")
    print("=" * 60 + "\n")

    # 1. Test Root Endpoint
    print("[1/10] Testing Root endpoint (GET /)...")
    res = client.get("/")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data["app"] == "VisionCare API"
    assert data["status"] == "online"
    print(f"  PASS: {data}")

    # 2. Test Health Endpoint
    print("\n[2/10] Testing Health endpoint (GET /api/health)...")
    res = client.get("/api/health")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "VisionCare API"
    assert data["model"]["available"] is False
    assert data["model"]["file_exists"] is False
    print(f"  PASS: Model accurately reported as available={data['model']['available']}")

    # 3. Test Swagger Documentation
    print("\n[3/10] Testing Swagger documentation (GET /docs)...")
    res = client.get("/docs")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "swagger-ui" in res.text.lower() or "html" in res.headers.get("content-type", "")
    print("  PASS: Swagger UI available at /docs")

    # 4. Test Valid JPG Upload (Model Unavailable -> HTTP 503)
    print("\n[4/10] Testing Valid JPG Upload (POST /api/predict)...")
    jpg_bytes = create_test_image(format="JPEG", size=(250, 250), color="red")
    files = {"file": ("retina_test.jpg", jpg_bytes, "image/jpeg")}
    res = client.post("/api/predict", files=files)
    assert res.status_code == 503, f"Expected 503 Service Unavailable, got {res.status_code}"
    assert "temporarily unavailable" in res.json()["detail"]
    print(f"  PASS: Validated JPG successfully and cleanly returned 503 notice: {res.json()['detail']}")

    # 5. Test Valid PNG Upload (Model Unavailable -> HTTP 503)
    print("\n[5/10] Testing Valid PNG Upload (POST /api/predict)...")
    png_bytes = create_test_image(format="PNG", size=(400, 400), color="green")
    files = {"file": ("fundus_scan.png", png_bytes, "image/png")}
    res = client.post("/api/predict", files=files)
    assert res.status_code == 503, f"Expected 503 Service Unavailable, got {res.status_code}"
    assert "temporarily unavailable" in res.json()["detail"]
    print("  PASS: Validated PNG successfully and cleanly returned 503 notice")

    # 6. Test Invalid File Extension / Format
    print("\n[6/10] Testing Invalid File Format (.txt)...")
    files = {"file": ("document.txt", b"This is a text document not a fundus image.", "text/plain")}
    res = client.post("/api/predict", files=files)
    assert res.status_code == 400, f"Expected 400, got {res.status_code}"
    assert "Unsupported file format" in res.json()["detail"]
    print(f"  PASS: Rejected .txt file: {res.json()['detail']}")

    # 7. Test Oversized File (> 10 MB)
    print("\n[7/10] Testing Oversized File (> 10 MB)...")
    oversized_bytes = b"0" * (10 * 1024 * 1024 + 1024)  # 10 MB + 1 KB
    files = {"file": ("oversized.jpg", oversized_bytes, "image/jpeg")}
    res = client.post("/api/predict", files=files)
    assert res.status_code == 400, f"Expected 400, got {res.status_code}"
    assert "exceeds maximum allowed limit" in res.json()["detail"]
    print(f"  PASS: Rejected oversized file: {res.json()['detail']}")

    # 8. Test Corrupted Image Stream
    print("\n[8/10] Testing Corrupted Image Upload...")
    corrupt_bytes = b"Corrupted arbitrary binary header that cannot be parsed by Pillow"
    files = {"file": ("corrupt.jpg", corrupt_bytes, "image/jpeg")}
    res = client.post("/api/predict", files=files)
    assert res.status_code == 400, f"Expected 400, got {res.status_code}"
    assert "corrupted or could not be decoded" in res.json()["detail"]
    print(f"  PASS: Detected corrupted file: {res.json()['detail']}")

    # 9. Test Empty File (0 Bytes)
    print("\n[9/10] Testing Empty File (0 Bytes)...")
    files = {"file": ("empty.jpg", b"", "image/jpeg")}
    res = client.post("/api/predict", files=files)
    assert res.status_code == 400, f"Expected 400, got {res.status_code}"
    assert "empty (0 bytes)" in res.json()["detail"]
    print(f"  PASS: Detected empty file: {res.json()['detail']}")

    # 10. Test Proper HTTP Error Responses
    print("\n[10/10] Testing Validation Error for Missing File Payload...")
    res = client.post("/api/predict")
    assert res.status_code == 422, f"Expected 422 for missing payload, got {res.status_code}"
    data = res.json()
    assert data["status"] == "error"
    assert data["type"] == "validation_error"
    print("  PASS: Custom 422 validation handler functioning as expected")

    print("\n" + "=" * 60)
    print("ALL 10 TEST CASES PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    run_tests()

