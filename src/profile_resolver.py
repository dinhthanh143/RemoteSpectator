import os
import json
import sys
from typing import Optional, Dict, Tuple

CHROME_USER_DATA = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
BRAVE_USER_DATA = os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data")
BRAVE_EXE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def list_profiles(browser: str = "chrome") -> Dict[str, Dict]:
    """
    Scans Local State to find profiles, names, and associated emails.
    Returns a dict mapping profile folder name -> profile info.
    """
    user_data_dir = BRAVE_USER_DATA if browser.lower() == "brave" else CHROME_USER_DATA
    local_state_file = os.path.join(user_data_dir, "Local State")
    results = {}
    
    if not os.path.exists(local_state_file):
        return results
        
    try:
        with open(local_state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            info_cache = data.get("profile", {}).get("info_cache", {})
            for folder, pinfo in info_cache.items():
                results[folder] = {
                    "name": pinfo.get("name", ""),
                    "email": pinfo.get("user_name", ""),
                    "path": os.path.join(user_data_dir, folder)
                }
    except Exception as e:
        print(f"Error reading {browser} Local State: {e}", file=sys.stderr)
        
    return results

def resolve_profile(target_query: Optional[str], browser: str = "chrome") -> Tuple[str, Optional[str]]:
    """
    Resolves an email (e.g. 'neonlime123@gmail.com') or profile name ('Default', 'Profile 35')
    to (user_data_dir, profile_folder_name).
    """
    user_data_dir = BRAVE_USER_DATA if browser.lower() == "brave" else CHROME_USER_DATA
    if not target_query:
        return user_data_dir, None
        
    query = target_query.strip().lower()
    profiles = list_profiles(browser)
    
    # 1. Exact match on email
    for folder, info in profiles.items():
        if info.get("email", "").lower() == query:
            return user_data_dir, folder
            
    # 2. Substring match on email or name
    for folder, info in profiles.items():
        if query in info.get("email", "").lower() or query in info.get("name", "").lower():
            return user_data_dir, folder
            
    # 3. Direct match on folder name
    for folder in profiles.keys():
        if folder.lower() == query:
            return user_data_dir, folder
            
    return user_data_dir, None

def get_browser_executable(browser: str = "chrome") -> Optional[str]:
    b = browser.lower()
    if b == "brave" and os.path.exists(BRAVE_EXE):
        return BRAVE_EXE
    elif b == "chrome" and os.path.exists(CHROME_EXE):
        return CHROME_EXE
    return None

if __name__ == "__main__":
    print("Chrome Profiles:")
    for f, d in list_profiles("chrome").items():
        print(f"  {f}: email={d.get('email')}, name={d.get('name')}")
