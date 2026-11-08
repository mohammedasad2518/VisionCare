import subprocess
import sys
import time
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
TEST_DIR = BASE_DIR / "training" / "data_splits" / "test"
PORT = 8008
BASE_URL = f"http://127.0.0.1:{PORT}"

def run_server_tests():
    print("=" * 60)
    print("VISIONCARE FASTAPI & UVICORN HTTP VERIFICATION TEST")
    print("=" * 60)

    # 1. Start Uvicorn Subprocess
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
    print(f"\n[1] Starting Uvicorn server: {' '.join(cmd)}")
    log_file = open("uvicorn_server.log", "w")
    server_process = subprocess.Popen(
        cmd,
        cwd=str(BASE_DIR),
        stdout=log_file,
        stderr=log_file,
        text=True
    )

    try:
        # 2. Wait for Server Startup
        print("[2] Waiting for server to initialize and load model into memory...")
        started = False
        health_data = None
        for attempt in range(25):
            time.sleep(1.5)
            # Check if process crashed prematurely
            if server_process.poll() is not None:
                stdout, stderr = server_process.communicate()
                print(f"ERROR: Server process terminated unexpectedly with code {server_process.returncode}")
                print(f"STDOUT:\n{stdout}")
                print(f"STDERR:\n{stderr}")
                sys.exit(1)
            
            try:
                resp = requests.get(f"{BASE_URL}/api/health", timeout=3)
                if resp.status_code == 200:
                    health_data = resp.json()
                    started = True
                    print(f"    Server is ready after ~{(attempt+1)*1.5:.1f}s!")
                    break
            except requests.exceptions.RequestException:
                pass

        assert started, "Server failed to start within 35 seconds."

        # 3. Verify Health Endpoint
        print("\n[3] Verifying GET /api/health:")
        print(f"    HTTP Status Code: 200 (Expected: 200)")
        print(f"    App Name: {health_data.get('app_name')}")
        print(f"    API Status: {health_data.get('status')}")
        model_info = health_data.get("model", {})
        print(f"    Model Available: {model_info.get('available')}")
        print(f"    Model Architecture: {model_info.get('architecture')}")
        print(f"    Model Weights Path: {model_info.get('model_path')}")
        print(f"    File Exists on Disk: {model_info.get('file_exists')}")
        print(f"    Categories: {model_info.get('categories')}")

        assert health_data.get("status") == "healthy", f"Status unhealthy: {health_data}"
        assert model_info.get("available") is True, "Model is not marked available!"
        assert model_info.get("file_exists") is True, "Model file not found!"
        assert model_info.get("architecture") == "VGG19 (Transfer Learning)"
        assert not str(model_info.get("model_path", "")).startswith("C:"), "Sensitive absolute path leaked in model_path!"
        print("    --> Health check PASSED with model available and path sanitized!")

        # 4. Verify Root Endpoint
        print("\n[4] Verifying GET /:")
        root_resp = requests.get(f"{BASE_URL}/", timeout=3)
        print(f"    HTTP Status Code: {root_resp.status_code}")
        print(f"    Response JSON: {root_resp.json()}")
        assert root_resp.status_code == 200
        assert root_resp.json().get("status") == "online"
        print("    --> Root endpoint PASSED!")

        # 5. Verify POST /api/predict with genuine test images
        print("\n[5] Verifying POST /api/predict with valid test images across all 4 categories:")
        test_samples = [
            ("Cataract", TEST_DIR / "Cataract" / "103_left.jpg"),
            ("Diabetic Retinopathy", TEST_DIR / "Diabetic Retinopathy" / "10003_left.jpeg"),
            ("Glaucoma", TEST_DIR / "Glaucoma" / "1212_left.jpg"),
            ("Normal", TEST_DIR / "Normal" / "2335_right.jpg"),
        ]

        for expected_class, img_path in test_samples:
            assert img_path.exists(), f"Sample image {img_path} does not exist"
            with open(img_path, "rb") as f:
                files = {"file": (img_path.name, f, "image/jpeg" if img_path.suffix in [".jpg", ".jpeg"] else "image/png")}
                pred_resp = requests.post(f"{BASE_URL}/api/predict", files=files, timeout=10)

            print(f"\n    Testing: {expected_class} ({img_path.name})")
            print(f"    HTTP Status: {pred_resp.status_code}")
            assert pred_resp.status_code == 200, f"Expected 200, got {pred_resp.status_code}: {pred_resp.text}"
            
            result = pred_resp.json()
            print(f"    Prediction: {result['prediction']}")
            print(f"    Confidence: {result['confidence'] * 100:.2f}%")
            print(f"    Probabilities: {result['probabilities']}")
            print(f"    Image Metadata: {result['image']}")

            assert result["status"] == "success"
            assert result["prediction"] == expected_class, f"Expected {expected_class}, got {result['prediction']}"
            assert result["confidence"] > 0.80, f"Confidence too low: {result['confidence']}"
            assert "scores" in result, "Missing 'scores' field"
            assert "probabilities" in result, "Missing 'probabilities' field"
            prob_sum = sum(result["probabilities"].values())
            assert abs(prob_sum - 1.0) < 0.01, f"Probabilities do not sum to 1.0: {prob_sum}"

        print("\n    --> All 4 genuine prediction tests PASSED with high confidence!")

        # 6. Verify 4xx Responses for Invalid Uploads
        print("\n[6] Verifying 4xx error handling on invalid files:")

        # Test A: Text file with invalid extension
        print("    [A] Uploading text file (.txt)...")
        files = {"file": ("notes.txt", b"Invalid text file content", "text/plain")}
        err_resp_a = requests.post(f"{BASE_URL}/api/predict", files=files, timeout=5)
        print(f"        HTTP Status: {err_resp_a.status_code} (Expected: 400)")
        print(f"        Detail: {err_resp_a.json().get('detail')}")
        assert err_resp_a.status_code == 400
        assert "Unsupported file format" in err_resp_a.json().get("detail", "")

        # Test B: Empty file (0 bytes)
        print("    [B] Uploading empty file (0 bytes)...")
        files = {"file": ("empty.jpg", b"", "image/jpeg")}
        err_resp_b = requests.post(f"{BASE_URL}/api/predict", files=files, timeout=5)
        print(f"        HTTP Status: {err_resp_b.status_code} (Expected: 400)")
        print(f"        Detail: {err_resp_b.json().get('detail')}")
        assert err_resp_b.status_code == 400
        assert "empty" in err_resp_b.json().get("detail", "").lower()

        # Test C: Corrupted image file (disguised as jpg)
        print("    [C] Uploading corrupted image data disguised as .jpg...")
        files = {"file": ("corrupt.jpg", b"NOT_A_REAL_JPEG_IMAGE_HEADER_DATA_12345", "image/jpeg")}
        err_resp_c = requests.post(f"{BASE_URL}/api/predict", files=files, timeout=5)
        print(f"        HTTP Status: {err_resp_c.status_code} (Expected: 400)")
        print(f"        Detail: {err_resp_c.json().get('detail')}")
        assert err_resp_c.status_code == 400
        assert "corrupted" in err_resp_c.json().get("detail", "").lower()

        print("    --> All 4xx validation tests PASSED cleanly!")

    finally:
        # 7. Clean Shutdown of Server
        print("\n[7] Shutting down Uvicorn test server cleanly...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
            print("    Server process terminated cleanly (exit code: 0).")
        except subprocess.TimeoutExpired:
            server_process.kill()
            server_process.wait()
            print("    Server process killed after timeout.")
        try:
            log_file.close()
        except Exception:
            pass

    print("\n" + "=" * 60)
    print("ALL FASTAPI & UVICORN SERVER VERIFICATIONS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    run_server_tests()

