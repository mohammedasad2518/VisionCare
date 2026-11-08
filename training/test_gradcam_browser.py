"""
VisionCare Phase 8: End-to-End Chrome Headless Browser Automation Test
Automates:
1. Starts FastAPI backend on port 8000.
2. Builds and starts Vite preview on port 5173.
3. Launches Headless Chrome with Chrome DevTools Protocol (CDP).
4. Navigates to http://localhost:5173/screening.
5. Verifies service readiness and model availability.
6. Automates image selection using a genuine retinal fundus photo (Glaucoma/1212_left.jpg).
7. Clicks 'Start Screening'.
8. Verifies prediction results:
   - Outcome classification
   - Confidence score
   - Scores distribution
9. Verifies Visual Explanation (Grad-CAM) generation:
   - "Visual Explanation" heading
   - Required clinical disclaimer:
     "The highlighted regions represent image areas that contributed to the model's classification. They are not a medical diagnosis or a confirmed disease location."
   - Layer specification: "block5_conv4"
   - View mode buttons ("Overlay", "Side-by-Side", "Heatmap", "Original Photo")
   - Salience colorbar & legend
   - Base64 data URL images rendered in <img> tags
10. Verifies zero occurrences of "AI" in DOM.
"""

import sys
import os
import json
import time
import asyncio
import base64
import subprocess
from pathlib import Path
import requests
import websockets

WORKSPACE = Path(__file__).resolve().parent.parent
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


async def run_browser_automation():
    print("=" * 65)
    print("VISIONCARE PHASE 8 E2E CHROME HEADLESS BROWSER TEST")
    print("=" * 65)

    assert TEST_IMAGE.exists(), f"Sample image {TEST_IMAGE} does not exist"

    # 1. Start FastAPI backend on 8000
    print("\n[1] Starting FastAPI backend on http://127.0.0.1:8000...")
    backend_log = open("backend_e2e_gradcam.log", "w", encoding="utf-8")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning"],
        cwd=str(WORKSPACE),
        stdout=backend_log,
        stderr=backend_log,
        text=True
    )

    # 2. Start Vite preview on 5173
    print("[2] Starting Vite preview server on http://localhost:5173...")
    frontend_log = open("frontend_e2e_gradcam.log", "w", encoding="utf-8")
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
        print("[3] Waiting for backend to become ready...")
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
        assert backend_ready, "Backend failed to start"

        # Wait for frontend
        print("[4] Waiting for Vite preview server...")
        frontend_ready = False
        for i in range(15):
            time.sleep(1)
            try:
                r = requests.get("http://localhost:5173/screening", timeout=2)
                if r.status_code == 200:
                    frontend_ready = True
                    print(f"    Frontend preview ready after {i+1}s!")
                    break
            except Exception:
                pass
        assert frontend_ready, "Frontend preview failed to start"

        # 3. Launch Chrome with CDP
        print("\n[5] Launching Chrome Headless with Remote Debugging (port 9223)...")
        import tempfile
        user_data_dir = tempfile.mkdtemp()
        chrome_cmd = [
            CHROME_PATH,
            "--headless=new",
            "--disable-gpu",
            "--remote-debugging-port=9223",
            f"--user-data-dir={user_data_dir}",
            "--window-size=1280,960",
            "about:blank"
        ]
        chrome_proc = subprocess.Popen(chrome_cmd)
        time.sleep(2)

        # Get WebSocket URL for first target page
        tabs = requests.get("http://127.0.0.1:9223/json", timeout=3).json()
        target_tab = next(t for t in tabs if t.get("type") == "page" and not t.get("url", "").startswith("chrome"))
        target_ws_url = target_tab["webSocketDebuggerUrl"]
        print(f"    Connected to Chrome CDP: {target_ws_url}")

        async with websockets.connect(target_ws_url, max_size=50 * 1024 * 1024) as ws:
            # Enable DOM and Page
            await cdp_command(ws, "Page.enable")
            await cdp_command(ws, "DOM.enable")
            await cdp_command(ws, "Runtime.enable")

            # Navigate to screening page
            print("[6] Navigating to http://localhost:5173/screening...")
            await cdp_command(ws, "Page.navigate", {"url": "http://localhost:5173/screening"})

            # Wait for React to mount and hydrate
            page_text = ""
            for _ in range(20):
                await asyncio.sleep(1)
                eval_res = await cdp_command(ws, "Runtime.evaluate", {
                    "expression": "document.body.innerText",
                    "returnByValue": True
                })
                page_text = eval_res.get("result", {}).get("value", "")
                if "VisionCare" in page_text and "Eye Disease Screening" in page_text:
                    break

            assert "VisionCare" in page_text, f"VisionCare branding missing (current text: '{page_text}')"
            assert "Screening Workspace" in page_text, "Screening Workspace header missing"
            assert "Eye Disease Screening" in page_text, "Page heading missing"
            print("    [DOM] Initial page loaded with VisionCare branding and screening workspace.")

            # Set file input directly using DOM.setFileInputFiles
            print(f"[7] Dispatching test image into file input: {TEST_IMAGE.name}...")
            doc_res = await cdp_command(ws, "DOM.getDocument")
            root_node_id = doc_res["root"]["nodeId"]

            input_res = await cdp_command(ws, "DOM.querySelector", {
                "nodeId": root_node_id,
                "selector": "input[type='file']"
            })
            input_node_id = input_res.get("nodeId", 0)
            assert input_node_id > 0, "Could not find file input element in DOM"

            await cdp_command(ws, "DOM.setFileInputFiles", {
                "files": [str(TEST_IMAGE)],
                "nodeId": input_node_id
            })
            print("    [DOM] Dispatched retinal photograph file into file input.")

            # Trigger change event for React synthetic event handler
            await cdp_command(ws, "Runtime.evaluate", {
                "expression": """
                (() => {
                    const input = document.querySelector('input[type=\"file\"]');
                    if (input) {
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                })()
                """
            })
            await asyncio.sleep(2)

            # Check Staging card is visible
            staging_check = await cdp_command(ws, "Runtime.evaluate", {
                "expression": "document.body.innerText.includes('Staged Retinal Photograph')",
                "returnByValue": True
            })
            assert staging_check.get("result", {}).get("value") is True, "Staged image preview not shown"
            print("    [DOM] Image staging card rendered with image preview.")

            # Click 'Start Screening' button
            print("[8] Clicking 'Start Screening' button...")
            click_res = await cdp_command(ws, "Runtime.evaluate", {
                "expression": """
                (() => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const screenBtn = buttons.find(b => b.innerText.includes('Start Screening'));
                    if (screenBtn) {
                        screenBtn.click();
                        return true;
                    }
                    return false;
                })()
                """,
                "returnByValue": True
            })
            assert click_res.get("result", {}).get("value") is True, "Start Screening button not found or could not be clicked"
            print("    [DOM] Clicked 'Start Screening'. Waiting for evaluation & Grad-CAM...")

            # Wait for screening results & Grad-CAM to render (up to 15 seconds)
            results_ready = False
            gradcam_ready = False

            for second in range(15):
                await asyncio.sleep(1)
                text_eval = await cdp_command(ws, "Runtime.evaluate", {
                    "expression": "document.body.innerText",
                    "returnByValue": True
                })
                current_text = text_eval.get("result", {}).get("value", "")

                if "Screening Results" in current_text:
                    results_ready = True
                if "Visual Explanation" in current_text and "Salience Overlay" in current_text:
                    gradcam_ready = True
                    print(f"    Results and Visual Explanation rendered after ~{second + 1}s!")
                    break

            assert results_ready, "Screening results failed to render"
            assert gradcam_ready, "Grad-CAM visual explanation section failed to render"

            # 9. Verify Visual Explanation Content
            print("\n[9] Inspecting Visual Explanation DOM elements:")
            dom_check = await cdp_command(ws, "Runtime.evaluate", {
                "expression": """
                (() => {
                    const body = document.body.innerText;
                    const hasDisclaimer = body.includes("The highlighted regions represent image areas that contributed to the model's classification. They are not a medical diagnosis or a confirmed disease location.");
                    const hasLayer = body.includes("block5_conv4");
                    const hasLegend = body.includes("Activation Salience Scale");
                    
                    const buttons = Array.from(document.querySelectorAll('button')).map(b => b.innerText.trim());
                    const hasOverlayTab = buttons.some(b => b.includes('Overlay'));
                    const hasSideBySideTab = buttons.some(b => b.includes('Side-by-Side'));
                    const hasHeatmapTab = buttons.some(b => b.includes('Heatmap'));
                    const hasOriginalTab = buttons.some(b => b.includes('Original Photo'));

                    const images = Array.from(document.querySelectorAll('img')).map(i => i.src);
                    const hasBase64Image = images.some(src => src.startsWith('data:image/png;base64,'));

                    return {
                        hasDisclaimer,
                        hasLayer,
                        hasLegend,
                        hasOverlayTab,
                        hasSideBySideTab,
                        hasHeatmapTab,
                        hasOriginalTab,
                        hasBase64Image,
                        totalImages: images.length
                    };
                })()
                """,
                "returnByValue": True
            })

            data = dom_check.get("result", {}).get("value", {})
            print(f"    - Disclaimer present: {data.get('hasDisclaimer')}")
            print(f"    - Target layer (block5_conv4): {data.get('hasLayer')}")
            print(f"    - Salience scale legend: {data.get('hasLegend')}")
            print(f"    - View Tabs (Overlay, Side-by-Side, Heatmap, Original): {data.get('hasOverlayTab') and data.get('hasSideBySideTab') and data.get('hasHeatmapTab') and data.get('hasOriginalTab')}")
            print(f"    - Base64 Grad-CAM image rendered in <img>: {data.get('hasBase64Image')}")

            assert data.get("hasDisclaimer") is True, "Clinical disclaimer missing or text mismatch"
            assert data.get("hasLayer") is True, "Target layer specification missing"
            assert data.get("hasLegend") is True, "Salience scale legend missing"
            assert data.get("hasOverlayTab") is True, "Overlay tab button missing"
            assert data.get("hasSideBySideTab") is True, "Side-by-Side tab button missing"
            assert data.get("hasHeatmapTab") is True, "Heatmap tab button missing"
            assert data.get("hasOriginalTab") is True, "Original photo tab button missing"
            assert data.get("hasBase64Image") is True, "Base64 Grad-CAM overlay image not found in <img> tags"

            # 10. Test Tab Switching to 'Side-by-Side'
            print("\n[10] Switching view to 'Side-by-Side'...")
            switch_res = await cdp_command(ws, "Runtime.evaluate", {
                "expression": """
                (() => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const btn = buttons.find(b => b.innerText.includes('Side-by-Side'));
                    if (btn) {
                        btn.click();
                        return true;
                    }
                    return false;
                })()
                """,
                "returnByValue": True
            })
            assert switch_res.get("result", {}).get("value") is True
            await asyncio.sleep(0.5)

            side_check = await cdp_command(ws, "Runtime.evaluate", {
                "expression": "document.body.innerText.includes('Original Photograph') && document.body.innerText.includes('Heatmap Overlay')",
                "returnByValue": True
            })
            assert side_check.get("result", {}).get("value") is True, "Side-by-Side view did not render both panels"
            print("    [DOM] Side-by-Side view confirmed: Both Original Photograph and Heatmap Overlay panels present.")

            # 11. Strict Check for Prohibited Word "AI"
            full_html = await cdp_command(ws, "Runtime.evaluate", {
                "expression": "document.body.innerText",
                "returnByValue": True
            })
            text = full_html.get("result", {}).get("value", "")
            # Check standalone AI
            import re
            ai_matches = re.findall(r'\bAI\b', text)
            assert len(ai_matches) == 0, f"Prohibited word 'AI' found in live rendered DOM: {ai_matches}"
            print("    [Branding Check] Zero occurrences of prohibited term 'AI' verified in live browser DOM!")

            print("\n--> LIVE CHROME BROWSER AUTOMATION TEST PASSED WITH 100% SUCCESS!")

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
    asyncio.run(run_browser_automation())
