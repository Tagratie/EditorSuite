"""
core/browser.py
Shared Playwright browser setup used by all scraper tools.
"""
import threading

_BARGS = [
    "--disable-blink-features=AutomationControlled",
    "--window-position=-32000,-32000",
    "--window-size=1280,900",
]
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def _hide_scraper_windows():
    """Hide Playwright Chromium windows from taskbar using Win32.
    Runs in background thread — only affects windows positioned off-screen."""
    try:
        import win32gui, win32con
        import time
        time.sleep(2)
        def _cb(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            cls = win32gui.GetClassName(hwnd)
            if cls != "Chrome_WidgetWin_1":
                return
            title = win32gui.GetWindowText(hwnd)
            # Skip our main app window
            if "EditorSuite" in title:
                return
            # Get window rect — off-screen means x < -1000
            try:
                x, y, _, _ = win32gui.GetWindowRect(hwnd)
                if x < -1000:  # Playwright's off-screen window
                    ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                    # WS_EX_TOOLWINDOW hides from taskbar, WS_EX_APPWINDOW shows
                    ex |=  win32con.WS_EX_TOOLWINDOW
                    ex &= ~win32con.WS_EX_APPWINDOW
                    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex)
            except Exception:
                pass
        win32gui.EnumWindows(_cb, None)
    except Exception:
        pass


async def new_browser(pw, mute: bool = False):
    """Launch a headless-off Chromium browser context. Returns (browser, ctx)."""
    args = (["--mute-audio"] if mute else []) + _BARGS
    browser = await pw.chromium.launch(headless=False, args=args)
    ctx = await browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent=_UA,
        locale="en-US",
    )
    # Hide from taskbar in background
    threading.Thread(target=_hide_scraper_windows, daemon=True).start()
    return browser, ctx
