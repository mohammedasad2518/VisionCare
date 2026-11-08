"""
VisionCare Phase 9: End-to-End Chrome Headless Browser Automation Test
Tests:
1. Navigates to /history: verifies initial empty state ("No Screening Records in Archive").
2. Navigates to /screening: uploads sample image (Glaucoma/1212_left.jpg) and executes screening.
3. Navigates back to /history: verifies newly persisted record appears in the history table!
4. Inspects record: verifies modal opens with canonical 4-category distribution.
5. Deletes record: verifies individual deletion and return to empty state.
6. Verifies zero occurrences of "AI" in live DOM.
"""

import sys
import os
import json
import time
import asyncio
import tempfile
import subprocess
from pathlib import Path
import requests
import websockets

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))
FRONTEND_DIR = WORKSPACE / "frontend"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TEST_IMAGE = WORKSPACE / "training" / "data_splits" / "test" / "Glaucoma" / "1212_left.jpg"


async def cdp_command(ws, method, params=None, msg_id=[1]):
    curr_id = msg_id[0]
    msg_id[0] += 1
    payload = {"id": curr_id, "method": method}
    if params:
        payload["params"] = params
    await ws.send(json.dumps(payload))
    while True:
        resp = await ws.recv()
        data = json.loads(resp)
        if data.get("id") == curr_id:
            return data.get("result", {})


async def run_history_browser_automation():
    print("=" * 65, flush=True)
    print("VISIONCARE PHASE 9 E2E CHROME HEADLESS BROWSER TEST", flush=True)
    print("=" * 65, flush=True)

    assert TEST_IMAGE.exists(), f"Sample image {TEST_IMAGE} does not exist"

    # Clean DB history before browser test via fast sqlite3 connection (avoid importing TF in test runner)
    import sqlite3
    db_path = WORKSPACE / "backend" / "data" / "visioncare.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    # Ensure table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS screening_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename VARCHAR(255) NOT NULL,
            predicted_category VARCHAR(64) NOT NULL,
            confidence_score FLOAT NOT NULL,
            scores_json TEXT NOT NULL,
            dimensions VARCHAR(32) NOT NULL,
            image_format VARCHAR(16) NOT NULL,
            file_size_bytes INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.execute("DELETE FROM screening_records;")
    conn.commit()
    conn.close()
    print("    [Database] screening_records table reset cleanly.", flush=True)

    # 1. Start FastAPI backend on 8000
    print("\n[1] Starting FastAPI backend on http://127.0.0.1:8000...", flush=True)
    backend_log = open("backend_e2e_history.log", "w", encoding="utf-8")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "info"],
        cwd=str(WORKSPACE),
        stdout=backend_log,
        stderr=backend_log,
        text=True
    )

    # 2. Start Vite preview on 5173
    print("[2] Starting Vite preview server on http://localhost:5173...", flush=True)
    frontend_log = open("frontend_e2e_history.log", "w", encoding="utf-8")
    frontend_proc = subprocess.Popen(
        ["cmd.exe", "/c", "npm", "run", "preview", "--", "--port", "5173"],
        cwd=str(FRONTEND_DIR),
        stdout=frontend_log,
        stderr=frontend_log,
        text=True
    )

    chrome_proc = None
    try:
        # Wait for backend
        print("[3] Waiting for backend to become ready...", flush=True)
        backend_ready = False
        for i in range(40):
            time.sleep(1)
            try:
                r = requests.get("http://127.0.0.1:8000/api/health", timeout=2)
                if r.status_code == 200 and r.json().get("model", {}).get("available"):
                    backend_ready = True
                    print(f"    Backend ready after {i+1}s!", flush=True)
                    break
            except Exception:
                pass
        assert backend_ready, "Backend failed to start"

        # Wait for frontend
        print("[4] Waiting for Vite preview server...", flush=True)
        frontend_ready = False
        for i in range(20):
            time.sleep(1)
            try:
                r = requests.get("http://localhost:5173/history", timeout=2)
                if r.status_code == 200:
                    frontend_ready = True
                    print(f"    Frontend preview ready after {i+1}s!", flush=True)
                    break
            except Exception:
                pass
        assert frontend_ready, "Frontend preview failed to start"

        # 3. Launch Chrome with CDP
        user_data_dir = tempfile.mkdtemp()
        print(f"\n[5] Launching Chrome Headless with Remote Debugging (port 9224)...", flush=True)
        chrome_cmd = [
            CHROME_PATH,
            "--headless=new",
            "--disable-gpu",
            "--remote-debugging-port=9224",
            f"--user-data-dir={user_data_dir}",
            "--window-size=1280,960",
            "about:blank"
        ]
        chrome_proc = subprocess.Popen(chrome_cmd)
        time.sleep(2)

        # Get WebSocket URL for first target page
        tabs = requests.get("http://127.0.0.1:9224/json", timeout=3).json()
        target_tab = next(t for t in tabs if t.get("type") == "page" and not t.get("url", "").startswith("chrome"))
        target_ws_url = target_tab["webSocketDebuggerUrl"]
        print(f"    Connected to Chrome CDP: {target_ws_url}", flush=True)

        async with websockets.connect(target_ws_url, max_size=50 * 1024 * 1024) as ws:
            await cdp_command(ws, "Page.enable")
            await cdp_command(ws, "DOM.enable")
            await cdp_command(ws, "Runtime.enable")

            # Step A: Navigate to /history to check initial empty state
            print("\n[6] Navigating to http://localhost:5173/history...", flush=True)
            await cdp_command(ws, "Page.navigate", {"url": "http://localhost:5173/history"})

            # Wait for React to render History page
            history_text = ""
            for attempt in range(15):
                await asyncio.sleep(1)
                eval_res = await cdp_command(ws, "Runtime.evaluate", {
                    "expression": "document.body.innerText",
                    "returnByValue": True
                })
                history_text = eval_res.get("result", {}).get("value", "")
                if "Screening History" in history_text:
                    print(f"    [DOM] History page rendered after {attempt+1}s.", flush=True)
                    break
                else:
                    print(f"    Waiting for History heading (attempt {attempt+1}): length={len(history_text)}", flush=True)

            assert "Screening History" in history_text, f"History page heading missing. Body text was: {history_text[:200]}"
            assert "No Screening Records in Archive" in history_text, "Empty state missing from initial history page"
            print("    [DOM] History page rendered with confirmed empty state.", flush=True)

            # Step B: Navigate to /screening and perform an actual screening
            print("\n[7] Navigating to http://localhost:5173/screening...", flush=True)
            await cdp_command(ws, "Page.navigate", {"url": "http://localhost:5173/screening"})

            for _ in range(15):
                await asyncio.sleep(1)
                eval_res = await cdp_command(ws, "Runtime.evaluate", {
                    "expression": "document.body.innerText",
                    "returnByValue": True
                })
                t = eval_res.get("result", {}).get("value", "")
                if "Eye Disease Screening" in t:
                    break

            # Dispatch image
            doc_res = await cdp_command(ws, "DOM.getDocument")
            root_node_id = doc_res["root"]["nodeId"]
            input_res = await cdp_command(ws, "DOM.querySelector", {
                "nodeId": root_node_id,
                "selector": "input[type='file']"
            })
            input_node_id = input_res.get("nodeId", 0)
            await cdp_command(ws, "DOM.setFileInputFiles", {
                "files": [str(TEST_IMAGE)],
                "nodeId": input_node_id
            })
            await cdp_command(ws, "Runtime.evaluate", {
                "expression": "document.querySelector('input[type=\"file\"]').dispatchEvent(new Event('change', { bubbles: true }));"
            })
            await asyncio.sleep(2)

            # Click Start Screening
            await cdp_command(ws, "Runtime.evaluate", {
                "expression": """
                (() => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const btn = buttons.find(b => b.innerText.includes('Start Screening'));
                    if (btn) btn.click();
                })()
                """
            })
            print("    [DOM] Screening submitted. Waiting for outcome...", flush=True)

            # Wait for screening results
            for _ in range(15):
                await asyncio.sleep(1)
                eval_res = await cdp_command(ws, "Runtime.evaluate", {
                    "expression": "document.body.innerText",
                    "returnByValue": True
                })
                t = eval_res.get("result", {}).get("value", "")
                if "Screening Results" in t:
                    print("    [DOM] Screening complete! Primary condition classified.", flush=True)
                    break

            # Step C: Navigate back to /history and verify the record is now displayed
            print("\n[8] Navigating back to http://localhost:5173/history to verify persistence...", flush=True)
            await cdp_command(ws, "Page.navigate", {"url": "http://localhost:5173/history"})

            history_rendered = False
            for _ in range(15):
                await asyncio.sleep(1)
                eval_res = await cdp_command(ws, "Runtime.evaluate", {
                    "expression": "document.body.innerText",
                    "returnByValue": True
                })
                t = eval_res.get("result", {}).get("value", "")
                if "1212_left.jpg" in t and "Glaucoma" in t:
                    history_rendered = True
                    print("    [DOM] Archived record confirmed in History table!", flush=True)
                    break

            assert history_rendered, "New record did not appear in history table after screening!"

            # Inspect DOM table values
            check_record = await cdp_command(ws, "Runtime.evaluate", {
                "expression": """
                (() => {
                    const text = document.body.innerText;
                    return {
                        hasFilename: text.includes('1212_left.jpg'),
                        hasGlaucoma: text.includes('Glaucoma'),
                        hasTotalArchived: text.toUpperCase().includes('TOTAL ARCHIVED')
                    };
                })()
                """,
                "returnByValue": True
            })
            vals = check_record.get("result", {}).get("value", {})
            assert vals.get("hasFilename") is True
            assert vals.get("hasGlaucoma") is True
            assert vals.get("hasTotalArchived") is True
            print("    [DOM Check] Record details (filename, condition, metrics) verified.", flush=True)

            # Step D: Test Record Inspection Modal
            print("\n[9] Clicking to inspect record details modal...", flush=True)
            await cdp_command(ws, "Runtime.evaluate", {
                "expression": """
                (() => {
                    const row = document.querySelector('tbody tr');
                    if (row) row.click();
                })()
                """
            })
            await asyncio.sleep(1)

            modal_check = await cdp_command(ws, "Runtime.evaluate", {
                "expression": "document.body.innerText.includes('Four-Category Feature Score Distribution')",
                "returnByValue": True
            })
            assert modal_check.get("result", {}).get("value") is True, "Inspection modal did not open"
            print("    [DOM Check] Inspection modal opened with Four-Category Score Distribution!", flush=True)

            # Close modal
            await cdp_command(ws, "Runtime.evaluate", {
                "expression": """
                (() => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const closeBtn = buttons.find(b => b.innerText.includes('Close'));
                    if (closeBtn) closeBtn.click();
                })()
                """
            })
            await asyncio.sleep(0.5)

            # Step E: Delete the record
            print("\n[10] Deleting individual record...", flush=True)
            await cdp_command(ws, "Runtime.evaluate", {
                "expression": """
                (() => {
                    const deleteBtn = document.querySelector('button[title=\"Delete Record\"]');
                    if (deleteBtn) deleteBtn.click();
                })()
                """
            })
            await asyncio.sleep(1.5)

            after_delete = await cdp_command(ws, "Runtime.evaluate", {
                "expression": "document.body.innerText",
                "returnByValue": True
            })
            del_text = after_delete.get("result", {}).get("value", "")
            assert "No Screening Records in Archive" in del_text, "Empty state did not return after deleting record"
            print("    [DOM Check] Record deleted. History page returned to empty state.", flush=True)

            # Step F: Verify 0 occurrences of prohibited word "AI"
            full_text = del_text
            import re
            ai_matches = re.findall(r'\bAI\b', full_text)
            assert len(ai_matches) == 0, f"Prohibited word 'AI' found in live DOM: {ai_matches}"
            print("    [Branding Check] Zero occurrences of 'AI' confirmed in live browser DOM!", flush=True)

            print("\n--> LIVE CHROME BROWSER E2E TEST PASSED WITH 100% SUCCESS!", flush=True)

    finally:
        print("\n[11] Terminating test processes...")
        if chrome_proc:
            chrome_proc.terminate()
            try:
                chrome_proc.wait(timeout=3)
            except Exception:
                chrome_proc.kill()
        backend_proc.terminate()
        try:
            backend_proc.wait(timeout=3)
        except Exception:
            backend_proc.kill()
        frontend_proc.terminate()
        try:
            frontend_proc.wait(timeout=3)
        except Exception:
            frontend_proc.kill()
        backend_log.close()
        frontend_log.close()
        print("    All processes shut down cleanly.")


if __name__ == "__main__":
    asyncio.run(run_history_browser_automation())
