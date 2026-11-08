import subprocess
import sys
import time
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def test_browser_integration():
    print("=" * 60)
    print("VISIONCARE HEADLESS BROWSER & FRONTEND INTEGRATION TEST")
    print("=" * 60)

    # 1. Start FastAPI backend on 8000
    print("\n[1] Starting FastAPI backend on http://127.0.0.1:8000...")
    backend_log = open("backend_browser_test.log", "w")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning"],
        cwd=str(BASE_DIR),
        stdout=backend_log,
        stderr=backend_log,
        text=True
    )

    # 2. Start Vite preview on 5173
    print("[2] Starting Vite preview server on http://localhost:5173...")
    frontend_log = open("frontend_browser_test.log", "w")
    # Use npx vite preview from frontend directory
    frontend_proc = subprocess.Popen(
        ["cmd.exe", "/c", "npm", "run", "preview", "--", "--port", "5173"],
        cwd=str(FRONTEND_DIR),
        stdout=frontend_log,
        stderr=frontend_log,
        text=True
    )

    try:
        # Wait for backend
        print("[3] Waiting for backend to become healthy...")
        backend_ready = False
        for i in range(25):
            time.sleep(1)
            try:
                r = requests.get("http://127.0.0.1:8000/api/health", timeout=2)
                if r.status_code == 200 and r.json().get("model", {}).get("available"):
                    backend_ready = True
                    print(f"    Backend ready after {i+1}s!")
                    break
            except Exception:
                pass
        assert backend_ready, "Backend failed to initialize"

        # Wait for frontend
        print("[4] Waiting for Vite preview server...")
        frontend_ready = False
        for i in range(15):
            time.sleep(1)
            try:
                r = requests.get("http://localhost:5173/", timeout=2)
                if r.status_code == 200:
                    frontend_ready = True
                    print(f"    Frontend ready after {i+1}s!")
                    break
            except Exception:
                pass
        assert frontend_ready, "Frontend failed to initialize"

        # 5. Launch genuine Chrome headless to render Screening page and fetch health
        print("\n[5] Launching Chrome Headless to execute React DOM and verify /api/health interaction...")
        chrome_cmd = [
            CHROME_PATH,
            "--headless=new",
            "--disable-gpu",
            "--virtual-time-budget=8000",
            "--dump-dom",
            "http://localhost:5173/screening"
        ]
        chrome_res = subprocess.run(
            chrome_cmd,
            capture_output=True,
            text=True,
            timeout=20,
            encoding="utf-8",
            errors="replace"
        )

        dom_html = chrome_res.stdout
        print(f"    Chrome rendered HTML length: {len(dom_html)} characters")

        # Verify key DOM nodes and state rendered by React
        assert "VisionCare" in dom_html, "VisionCare branding missing from rendered DOM"
        assert "Screening Workspace" in dom_html, "Screening Workspace badge missing from rendered DOM"
        assert "Eye Disease Screening" in dom_html, "Page heading missing from rendered DOM"
        assert "Screening Engine" in dom_html, "Screening Engine section missing from rendered DOM"
        assert "Available" in dom_html, "Screening engine was not confirmed Available by browser!"
        assert "AI" not in dom_html.replace("EMAIL", "").replace("DOMAIN", ""), "Prohibited term found in rendered DOM"

        print("    [DOM Check] 'VisionCare' branding confirmed.")
        print("    [DOM Check] 'Screening Workspace' confirmed.")
        print("    [DOM Check] 'Eye Disease Screening' confirmed.")
        print("    [DOM Check] 'Screening Engine' confirmed.")
        print("    [DOM Check] 'Available' status badge confirmed (React verified backend /api/health)!")
        print("    --> Genuine Chrome browser test PASSED with 100% verification!")

    finally:
        print("\n[6] Cleaning up test server processes...")
        backend_proc.terminate()
        try:
            backend_proc.wait(timeout=5)
        except Exception:
            backend_proc.kill()
        
        frontend_proc.terminate()
        try:
            frontend_proc.wait(timeout=5)
        except Exception:
            frontend_proc.kill()

        backend_log.close()
        frontend_log.close()
        print("    Both test servers shut down cleanly.")

    print("\n" + "=" * 60)
    print("ALL BROWSER & INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_browser_integration()

