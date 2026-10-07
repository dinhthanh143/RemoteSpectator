import asyncio
import os
import sys
import json
import shutil
import tempfile
import threading
from datetime import datetime
from typing import Optional, List, Dict
from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright
import urllib.request
import urllib.error
from PIL import Image, ImageDraw

mcp = FastMCP("remote-spectator")

VIEWPORTS = {
    "desktop": {"width": 1280, "height": 800},
    "mobile": {"width": 390, "height": 844, "is_mobile": True, "has_touch": True},
    "tablet": {"width": 820, "height": 1180, "is_mobile": True, "has_touch": True}
}

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CAPTURES_DIR = os.path.join(BASE_DIR, ".spectator", "captures")
SESSIONS_DIR = os.path.join(BASE_DIR, ".spectator", "sessions")

CHROME_USER_DATA = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
BRAVE_USER_DATA = os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data")
CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BRAVE_EXE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

os.makedirs(CAPTURES_DIR, exist_ok=True)
os.makedirs(SESSIONS_DIR, exist_ok=True)

import difflib

def resolve_profile(target_query: Optional[str], browser_name: str = "chrome") -> Optional[str]:
    """Finds the profile folder name (e.g. 'Profile 35') by exact, substring, or fuzzy similarity."""
    if not target_query:
        return None
    user_data = BRAVE_USER_DATA if browser_name.lower() == "brave" else CHROME_USER_DATA
    local_state_file = os.path.join(user_data, "Local State")
    if not os.path.exists(local_state_file):
        return None
    try:
        with open(local_state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            info = data.get("profile", {}).get("info_cache", {})
            raw_q = target_query.strip().lower()
            # Strip noise words like 'google', 'chrome', 'brave', 'profile', 'as', 'my'
            q = raw_q
            for noise in ["google", "chrome", "brave", "profile", "as", "my", "account"]:
                q = q.replace(noise, "")
            q = q.strip()
            if not q:
                q = raw_q

            # 1. Exact match on email, name, or folder
            for folder, pinfo in info.items():
                u_email = pinfo.get("user_name", "").lower()
                u_name = pinfo.get("name", "").lower()
                if u_email == q or u_name == q or folder.lower() == q:
                    return folder

            # 2. Substring match
            for folder, pinfo in info.items():
                u_email = pinfo.get("user_name", "").lower()
                u_name = pinfo.get("name", "").lower()
                if (q in u_email) or (q in u_name) or (q in folder.lower()):
                    return folder

            # 3. Fuzzy similarity matching across emails and display names
            candidates = {}
            for folder, pinfo in info.items():
                u_email = pinfo.get("user_name", "").lower()
                u_name = pinfo.get("name", "").lower()
                if u_email:
                    candidates[u_email] = folder
                    # Also include username portion before '@'
                    prefix = u_email.split("@")[0]
                    candidates[prefix] = folder
                if u_name:
                    candidates[u_name] = folder

            best_matches = difflib.get_close_matches(q, candidates.keys(), n=1, cutoff=0.35)
            if best_matches:
                return candidates[best_matches[0]]

    except Exception:
        pass
    return None


def _get_session_file(session_id: str) -> str:
    clean_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_")).strip() or "default"
    return os.path.join(SESSIONS_DIR, f"{clean_id}.json")

def _load_session(session_id: str) -> Dict:
    filepath = _get_session_file(session_id)
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"session_id": session_id, "created_at": datetime.now().isoformat(), "variants": []}

def _save_session(session_data: Dict):
    filepath = _get_session_file(session_data["session_id"])
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=2)

def _create_composite_grid(variants: List[Dict], output_filepath: str):
    images = []
    labels = []
    for v in variants:
        if os.path.exists(v["image_path"]):
            images.append(Image.open(v["image_path"]))
            labels.append(v.get("label", "Variant"))
            
    if not images:
        return
        
    num_items = len(images)
    header_height = 40
    target_width = 640
    scaled_images = []
    for img in images:
        aspect = img.height / img.width
        target_height = int(target_width * aspect)
        scaled_images.append(img.resize((target_width, target_height), Image.Resampling.LANCZOS))
        
    col_width = target_width
    row_height = max(img.height for img in scaled_images) + header_height
    padding = 20
    
    total_width = (col_width * num_items) + (padding * (num_items + 1))
    total_height = row_height + (padding * 2)
    
    canvas = Image.new("RGB", (total_width, total_height), color=(24, 24, 27))
    draw = ImageDraw.Draw(canvas)
    
    for idx, (img, label) in enumerate(zip(scaled_images, labels)):
        x = padding + idx * (col_width + padding)
        y = padding
        draw.rectangle([x, y, x + col_width, y + 32], fill=(39, 39, 42))
        text = f"[{idx+1}] {label}"
        draw.text((x + 12, y + 8), text, fill=(244, 244, 245))
        canvas.paste(img, (x, y + header_height))
        
    canvas.save(output_filepath, "PNG")

@mcp.tool()
async def spectator_ping(url: str, timeout_seconds: int = 3) -> str:
    """Checks if a target web URL / dev server port is responsive and alive."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RemoteSpectator"}
        )
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            return f"SUCCESS: Endpoint {url} responded with HTTP status {response.status}."
    except urllib.error.HTTPError as e:
        return f"ALIVE_WITH_ERROR: Endpoint {url} responded with HTTP {e.code}."
    except Exception as e:
        return f"UNREACHABLE: Failed to reach {url}. Error: {str(e)}"

async def _playwright_snap(
    url: str,
    filepath: str,
    viewport: str = "desktop",
    full_page: bool = False,
    wait_selector: Optional[str] = None,
    browser_name: str = "chromium",
    profile: Optional[str] = None
) -> str:
    clean_viewport = viewport.lower() if viewport.lower() in VIEWPORTS else "desktop"
    vp_config = VIEWPORTS[clean_viewport]
    b_name = browser_name.lower().strip()

    # Determine executable and user data directory
    executable_path = None
    if b_name == "chrome" and os.path.exists(CHROME_EXE):
        executable_path = CHROME_EXE
    elif b_name == "brave" and os.path.exists(BRAVE_EXE):
        executable_path = BRAVE_EXE

    matched_profile_folder = resolve_profile(profile, b_name) if profile else None
    
    async with async_playwright() as p:
        # If user specified a real profile or browser executable
        if matched_profile_folder or b_name in ("chrome", "brave"):
            source_user_data = BRAVE_USER_DATA if b_name == "brave" else CHROME_USER_DATA
            target_profile_dir = matched_profile_folder or "Default"
            
            # Use isolated shadow user-data copy to avoid Windows process lock conflicts
            temp_profile_dir = tempfile.mkdtemp(prefix="spectator_profile_")
            src_p = os.path.join(source_user_data, target_profile_dir)
            dst_p = os.path.join(temp_profile_dir, "Default")
            
            # Copy essential session files (Cookies, Network, Local Storage)
            def safe_copy(src, dst):
                try:
                    if os.path.isfile(src):
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
                    elif os.path.isdir(src):
                        os.makedirs(dst, exist_ok=True)
                        for entry in os.scandir(src):
                            s = os.path.join(src, entry.name)
                            d = os.path.join(dst, entry.name)
                            safe_copy(s, d)
                except Exception:
                    pass

            if os.path.exists(src_p):
                for item in ["Cookies", "Network", "Local Storage", "Session Storage"]:
                    src_item = os.path.join(src_p, item)
                    dst_item = os.path.join(dst_p, item)
                    safe_copy(src_item, dst_item)

            context = await p.chromium.launch_persistent_context(
                user_data_dir=temp_profile_dir,
                executable_path=executable_path,
                headless=True,
                viewport={"width": vp_config["width"], "height": vp_config["height"]},
                is_mobile=vp_config.get("is_mobile", False),
                has_touch=vp_config.get("has_touch", False),
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = context.pages[0] if context.pages else await context.new_page()
        else:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": vp_config["width"], "height": vp_config["height"]},
                is_mobile=vp_config.get("is_mobile", False),
                has_touch=vp_config.get("has_touch", False)
            )
            page = await context.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=15000)
        except Exception:
            await page.goto(url, wait_until="load", timeout=15000)
            
        if wait_selector:
            try:
                await page.wait_for_selector(wait_selector, timeout=5000)
            except Exception as e:
                print(f"Selector timeout: {e}", file=sys.stderr)

        await page.screenshot(path=filepath, full_page=full_page)
        title = await page.title()
        await context.close()
        
        # Cleanup temporary shadow profile if created
        if matched_profile_folder or b_name in ("chrome", "brave"):
            shutil.rmtree(temp_profile_dir, ignore_errors=True)
            
        return title

@mcp.tool()
async def spectator_capture(
    url: str,
    viewport: str = "desktop",
    full_page: bool = False,
    wait_selector: Optional[str] = None,
    browser: str = "chromium",
    profile: Optional[str] = None,
    output_filename: Optional[str] = None
) -> str:
    """
    Captures a visual snapshot of the specified URL.
    - browser: 'chromium' (default clean), 'chrome', or 'brave'
    - profile: email or profile name (e.g. 'neonlime123@gmail.com') to use authenticated session/cookies
    - viewport: 'desktop', 'mobile', or 'tablet'
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_viewport = viewport.lower() if viewport.lower() in VIEWPORTS else "desktop"
    
    if output_filename:
        filename = output_filename if output_filename.endswith(".png") else f"{output_filename}.png"
    else:
        prefix = f"{profile[:10]}_" if profile else ""
        filename = f"capture_{prefix}{clean_viewport}_{timestamp}.png"
        
    target_filepath = os.path.join(CAPTURES_DIR, filename)
    title = await _playwright_snap(
        url=url,
        filepath=target_filepath,
        viewport=clean_viewport,
        full_page=full_page,
        wait_selector=wait_selector,
        browser_name=browser,
        profile=profile
    )
    normalized_path = target_filepath.replace("\\", "/")
    return f"CAPTURED_SUCCESS: Saved visual snapshot of '{title}' ({url})\nBrowser: {browser} (Profile: {profile or 'Clean/None'})\nPath: {normalized_path}\nAsset Manager UI: http://localhost:49152"

@mcp.tool()
async def spectator_compare(
    url: str,
    label: str,
    session_id: str = "default",
    viewport: str = "desktop",
    browser: str = "chromium",
    profile: Optional[str] = None,
    reset_session: bool = False,
    wait_selector: Optional[str] = None
) -> str:
    """Captures a variant and appends it to a multi-stage comparison timeline with browser/profile support."""
    clean_session_id = session_id.strip() or "default"
    if reset_session:
        session = {"session_id": clean_session_id, "created_at": datetime.now().isoformat(), "variants": []}
    else:
        session = _load_session(clean_session_id)
        
    step_num = len(session["variants"]) + 1
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"cmp_{clean_session_id}_step{step_num}_{timestamp}.png"
    filepath = os.path.join(CAPTURES_DIR, filename)
    
    title = await _playwright_snap(
        url=url,
        filepath=filepath,
        viewport=viewport,
        wait_selector=wait_selector,
        browser_name=browser,
        profile=profile
    )
    
    variant_info = {
        "step": step_num,
        "label": label,
        "url": url,
        "timestamp": timestamp,
        "image_path": filepath,
        "page_title": title,
        "browser": browser,
        "profile": profile
    }
    session["variants"].append(variant_info)
    
    composite_filename = f"composite_{clean_session_id}.png"
    composite_path = os.path.join(CAPTURES_DIR, composite_filename)
    _create_composite_grid(session["variants"], composite_path)
    session["latest_composite"] = composite_path
    
    _save_session(session)
    
    normalized_img = filepath.replace("\\", "/")
    normalized_composite = composite_path.replace("\\", "/")
    
    msg = [
        f"COMPARE_STEP_RECORDED (Session: '{clean_session_id}', Step {step_num}):",
        f"- Label: {label}",
        f"- Capture: {normalized_img}",
        f"- Browser: {browser} | Profile: {profile or 'Clean'}"
    ]
    if len(session["variants"]) >= 2:
        msg.append(f"- Composite Image: {normalized_composite}")
        
    msg.append(f"- Asset Manager UI: http://localhost:49152")
    return "\n".join(msg)

def _ensure_ui_server():
    try:
        from src.ui_server import start_ui_server
        t = threading.Thread(target=start_ui_server, daemon=True)
        t.start()
    except Exception as e:
        print(f"Warning: Failed to launch UI server: {e}", file=sys.stderr)

if __name__ == "__main__":
    _ensure_ui_server()
    mcp.run()

