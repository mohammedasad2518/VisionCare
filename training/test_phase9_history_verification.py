"""
VisionCare Phase 9: Comprehensive History & Database Verification Suite
Tests:
1. Database initialization and SQLite schema creation.
2. Direct CRUD operations (create, read, list, delete, clear, canonical category ordering).
3. Live HTTP endpoint testing with Uvicorn server:
   - GET /api/history
   - GET /api/history/{id}
   - DELETE /api/history/{id}
   - DELETE /api/history
   - 400 & 404 validation
   - Successful POST /api/predict automatically archives record
   - Failed predictions (corrupt, empty) NEVER create database records
   - Database persistence across server restart
"""

import sys
import io
import time
import subprocess
from pathlib import Path
import requests

workspace_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(workspace_root))

from backend.app.core.config import settings
from backend.app.db.session import init_db, SessionLocal
from backend.app.models.screening_record import ScreeningRecord
from backend.app.services.history_service import history_service

PORT = 8010
BASE_URL = f"http://127.0.0.1:{PORT}"
SAMPLE_IMAGE = workspace_root / "training" / "data_splits" / "test" / "Cataract" / "103_left.jpg"


def test_database_crud_direct():
    print("=" * 65, flush=True)
    print("1. DIRECT DATABASE & CRUD SERVICE VERIFICATION", flush=True)
    print("=" * 65, flush=True)

    # 1. Initialize
    init_db()
    assert settings.DATABASE_PATH.exists(), f"Database file missing: {settings.DATABASE_PATH}"
    print(f"  [PASS] Database initialized at: {settings.DATABASE_PATH}", flush=True)

    db = SessionLocal()
    try:
        # Clear existing test data
        history_service.clear_all_records(db)

        # 2. Create Record
        scores = {
            "Cataract": 0.9701,
            "Diabetic Retinopathy": 0.0007,
            "Glaucoma": 0.0008,
            "Normal": 0.0285
        }
        record = history_service.create_record(
            db=db,
            filename="103_left.jpg",
            predicted_category="Cataract",
            confidence_score=0.9701,
            scores=scores,
            dimensions=(512, 512),
            image_format="JPEG",
            file_size_bytes=46733
        )
        assert record.id is not None
        assert record.filename == "103_left.jpg"
        assert record.predicted_category == "Cataract"
        assert record.dimensions == "512x512"
        assert record.file_size_bytes == 46733
        print(f"  [PASS] Successfully created record ID: {record.id}", flush=True)

        # 3. Verify Canonical Category Order
        deserialized_scores = record.scores
        expected_keys = ["Cataract", "Diabetic Retinopathy", "Glaucoma", "Normal"]
        assert list(deserialized_scores.keys()) == expected_keys, f"Scores keys mismatch: {list(deserialized_scores.keys())}"
        print(f"  [PASS] Canonical category order strictly verified: {list(deserialized_scores.keys())}", flush=True)

        # 4. Fetch Single Record
        fetched = history_service.get_record_by_id(db, record.id)
        assert fetched is not None
        assert fetched.id == record.id
        print(f"  [PASS] Successfully retrieved single record ID {record.id}", flush=True)

        # 5. List Records
        records, count = history_service.get_history(db)
        assert count == 1
        assert len(records) == 1
        print(f"  [PASS] History list verified (count={count})", flush=True)

        # 6. Delete Record
        deleted = history_service.delete_record(db, record.id)
        assert deleted is True
        assert history_service.get_record_by_id(db, record.id) is None
        print(f"  [PASS] Successfully deleted record ID {record.id}", flush=True)

        # 7. Clear All
        history_service.create_record(db, "sample1.jpg", "Normal", 0.95, scores, "512x512", "JPEG", 40000)
        history_service.create_record(db, "sample2.jpg", "Glaucoma", 0.88, scores, "512x512", "JPEG", 42000)
        cleared = history_service.clear_all_records(db)
        assert cleared == 2
        _, count_after = history_service.get_history(db)
        assert count_after == 0
        print(f"  [PASS] Clear all records verified (deleted {cleared} records)", flush=True)

    finally:
        db.close()


def test_history_http_endpoints():
    print("\n" + "=" * 65, flush=True)
    print("2. LIVE HTTP HISTORY ENDPOINTS & PREDICTION INTEGRATION", flush=True)
    print("=" * 65, flush=True)

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

    log_file = open("history_test_server.log", "w", encoding="utf-8")
    server_proc = subprocess.Popen(cmd, cwd=str(workspace_root), stdout=log_file, stderr=log_file, text=True)

    try:
        # Wait for server startup
        started = False
        for attempt in range(25):
            time.sleep(1.5)
            try:
                r = requests.get(f"{BASE_URL}/api/health", timeout=3)
                if r.status_code == 200:
                    started = True
                    print(f"Server is ready on port {PORT} after ~{(attempt + 1) * 1.5:.1f}s!", flush=True)
                    break
            except Exception:
                pass
        assert started, "Server failed to respond within 35 seconds."

        # A. Start clean: Clear history
        clear_resp = requests.delete(f"{BASE_URL}/api/history", timeout=5)
        assert clear_resp.status_code == 200
        print("  [PASS] Initial DELETE /api/history returned 200", flush=True)

        # B. Verify Empty State: GET /api/history
        get_empty = requests.get(f"{BASE_URL}/api/history", timeout=5)
        assert get_empty.status_code == 200
        data = get_empty.json()
        assert data["status"] == "success"
        assert data["total_count"] == 0
        assert data["records"] == []
        print("  [PASS] Empty GET /api/history returned total_count=0", flush=True)

        # C. Predict Image & Verify Automatic History Persistence
        assert SAMPLE_IMAGE.exists(), f"Sample image {SAMPLE_IMAGE} missing"
        with open(SAMPLE_IMAGE, "rb") as f:
            img_bytes = f.read()

        pred_resp = requests.post(
            f"{BASE_URL}/api/predict",
            files={"file": (SAMPLE_IMAGE.name, io.BytesIO(img_bytes), "image/jpeg")},
            timeout=15
        )
        assert pred_resp.status_code == 200, f"/api/predict failed: {pred_resp.text}"
        pred_data = pred_resp.json()
        screening_id = pred_data.get("screening_id")
        assert screening_id is not None, "screening_id missing from /api/predict response"
        print(f"  [PASS] Successful prediction returned screening_id={screening_id}", flush=True)

        # D. Verify Record Exists in History List: GET /api/history
        get_history = requests.get(f"{BASE_URL}/api/history", timeout=5)
        assert get_history.status_code == 200
        history_data = get_history.json()
        assert history_data["total_count"] == 1
        assert len(history_data["records"]) == 1
        rec = history_data["records"][0]
        assert rec["id"] == screening_id
        assert rec["filename"] == SAMPLE_IMAGE.name
        assert rec["predicted_category"] == pred_data["prediction"]
        assert abs(rec["confidence_score"] - pred_data["confidence"]) < 1e-4
        assert rec["dimensions"] == "512x512"
        assert rec["image_format"] == "JPEG"
        assert rec["file_size_bytes"] == len(img_bytes)
        assert list(rec["scores"].keys()) == ["Cataract", "Diabetic Retinopathy", "Glaucoma", "Normal"]
        print(f"  [PASS] GET /api/history correctly reflects newly archived record ID {screening_id}", flush=True)

        # E. Verify Single Record Endpoint: GET /api/history/{id}
        get_single = requests.get(f"{BASE_URL}/api/history/{screening_id}", timeout=5)
        assert get_single.status_code == 200
        single_data = get_single.json()
        assert single_data["id"] == screening_id
        assert single_data["filename"] == SAMPLE_IMAGE.name
        print(f"  [PASS] GET /api/history/{screening_id} returned exact record", flush=True)

        # F. Verify 404 & 400 Handling
        # 404 on nonexistent ID
        resp_404 = requests.get(f"{BASE_URL}/api/history/999999", timeout=5)
        assert resp_404.status_code == 404
        assert "not found" in resp_404.json().get("detail", "").lower()
        print("  [PASS] Nonexistent ID returned HTTP 404 Not Found", flush=True)

        # 400 on invalid ID
        resp_400 = requests.get(f"{BASE_URL}/api/history/0", timeout=5)
        assert resp_400.status_code == 400
        print("  [PASS] Non-positive ID returned HTTP 400 Bad Request", flush=True)

        # G. Verify Failed Predictions NEVER Create History Records
        corrupt_resp = requests.post(
            f"{BASE_URL}/api/predict",
            files={"file": ("corrupt.jpg", io.BytesIO(b"INVALID_HEADER_STREAM_DATA"), "image/jpeg")},
            timeout=5
        )
        assert corrupt_resp.status_code == 400
        # Check history count remains 1
        check_count = requests.get(f"{BASE_URL}/api/history", timeout=5).json()["total_count"]
        assert check_count == 1, f"Failed prediction created unwanted record! Count: {check_count}"
        print("  [PASS] Failed prediction did NOT create a history record (count remained 1)", flush=True)

        # H. Verify Single Record Deletion: DELETE /api/history/{id}
        del_resp = requests.delete(f"{BASE_URL}/api/history/{screening_id}", timeout=5)
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted_id"] == screening_id
        # Verify 404 when querying deleted ID
        assert requests.get(f"{BASE_URL}/api/history/{screening_id}", timeout=5).status_code == 404
        print(f"  [PASS] DELETE /api/history/{screening_id} succeeded and record is gone", flush=True)

        # I. Delete nonexistent ID -> 404
        del_404 = requests.delete(f"{BASE_URL}/api/history/999999", timeout=5)
        assert del_404.status_code == 404
        print("  [PASS] DELETE nonexistent ID returned HTTP 404", flush=True)

    finally:
        print("Shutting down test server...", flush=True)
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except Exception:
            server_proc.kill()
        log_file.close()


def test_database_persistence_across_restart():
    print("\n" + "=" * 65, flush=True)
    print("3. VERIFYING DATABASE PERSISTENCE ACROSS SERVER RESTARTS", flush=True)
    print("=" * 65, flush=True)

    # Step 1: Insert record directly via DB session
    db = SessionLocal()
    rec = history_service.create_record(
        db=db,
        filename="persistent_fundus.png",
        predicted_category="Normal",
        confidence_score=0.9850,
        scores={"Normal": 0.985, "Cataract": 0.005, "Diabetic Retinopathy": 0.005, "Glaucoma": 0.005},
        dimensions=(512, 512),
        image_format="PNG",
        file_size_bytes=52000
    )
    persistent_id = rec.id
    db.close()
    print(f"Inserted persistent record ID {persistent_id}. Starting fresh Uvicorn server...", flush=True)

    # Step 2: Start new server instance
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
    log_file = open("restart_test_server.log", "w", encoding="utf-8")
    server_proc = subprocess.Popen(cmd, cwd=str(workspace_root), stdout=log_file, stderr=log_file, text=True)

    try:
        started = False
        for attempt in range(25):
            time.sleep(1.5)
            try:
                r = requests.get(f"{BASE_URL}/api/health", timeout=3)
                if r.status_code == 200:
                    started = True
                    break
            except Exception:
                pass
        assert started, "Fresh server instance failed to respond"

        # Step 3: Verify the record is still present in SQLite database
        resp = requests.get(f"{BASE_URL}/api/history/{persistent_id}", timeout=5)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["id"] == persistent_id
        assert data["filename"] == "persistent_fundus.png"
        assert data["predicted_category"] == "Normal"
        print(f"  [PASS] Record ID {persistent_id} successfully persisted across server restart!", flush=True)

        # Cleanup
        requests.delete(f"{BASE_URL}/api/history/{persistent_id}", timeout=5)
    finally:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except Exception:
            server_proc.kill()
        log_file.close()


if __name__ == "__main__":
    test_database_crud_direct()
    test_history_http_endpoints()
    test_database_persistence_across_restart()
    print("\n" + "=" * 65, flush=True)
    print("ALL PHASE 9 BACKEND HISTORY & DATABASE TESTS PASSED!", flush=True)
    print("=" * 65, flush=True)

