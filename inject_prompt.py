import sys
import time
import ctypes
import pyperclip
import pyautogui

user32 = ctypes.windll.user32

def send_prompt_to_antigravity(prompt_text: str):
    hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
    target_hwnd = None

    def enum_proc(hwnd, lParam):
        nonlocal target_hwnd
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == 14748 and user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                if buff.value:
                    target_hwnd = hwnd
                    return False
        return True

    DESKENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumDesktopWindows(hdesk, DESKENUMPROC(enum_proc), 0)

    if not target_hwnd:
        print("Error: Could not locate Antigravity window.")
        return False

    print(f"Located Antigravity HWND: {target_hwnd:08X}")

    pyautogui.FAILSAFE = False

    # Bring to foreground
    user32.ShowWindow(target_hwnd, 9) # SW_RESTORE
    user32.SetForegroundWindow(target_hwnd)
    time.sleep(0.3)

    # Copy prompt to clipboard
    pyperclip.copy(prompt_text)

    # Paste and submit via keybd_event (reliable, no mouse fail-safe)
    VK_CONTROL = 0x11
    VK_V = 0x56
    VK_RETURN = 0x0D
    KEYEVENTF_KEYUP = 0x0002

    # Ctrl + V
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_V, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

    time.sleep(0.15)

    # Enter
    user32.keybd_event(VK_RETURN, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)

    print("Injected prompt successfully.")
    return True

if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else "Hello from Discord injector!"
    send_prompt_to_antigravity(text)
