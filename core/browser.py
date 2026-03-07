"""
core/browser.py
Shared Playwright browser setup used by all scraper tools.
"""
import os
import threading

# ── Safety net: force PLAYWRIGHT_BROWSERS_PATH before any Playwright import ──
def _ensure_playwright_path():
    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        return
    base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
    if os.path.isdir(base):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = base

_ensure_playwright_path()


_BARGS = [
    "--disable-blink-features=AutomationControlled",
    "--window-position=-32000,-32000",
    "--window-size=1280,900",
    # Extra stealth flags
    "--disable-web-security",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
]
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Persistent profile dir — keeps cookies/localStorage so TikTok sees a
# returning user, not a fresh bot fingerprint on every launch.
def _profile_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    p = os.path.join(base, "EditorSuite", "browser_profile")
    os.makedirs(p, exist_ok=True)
    return p


def _find_chromium_exe() -> str | None:
    base = os.environ.get(
        "PLAYWRIGHT_BROWSERS_PATH",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright"),
    )
    if not os.path.isdir(base):
        return None
    try:
        for entry in sorted(os.listdir(base), reverse=True):
            if not entry.lower().startswith("chromium"):
                continue
            for rel in (
                "chrome-win64/chrome.exe",
                "chrome-linux/chrome",
                "chrome-mac/Chromium.app/Contents/MacOS/Chromium",
            ):
                exe = os.path.join(base, entry, rel)
                if os.path.isfile(exe):
                    return exe
    except Exception:
        pass
    return None


# JS injected into every page to mask Playwright automation signals
_STEALTH_JS = """
() => {
    // Remove webdriver flag
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    // Fake plugins list (empty = bot giveaway)
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
    });
    // Fake languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
    });
    // Chrome runtime object (missing in headless)
    window.chrome = { runtime: {} };
    // Permissions API — bots return 'denied' for notifications
    const origQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (params) =>
        params.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : origQuery(params);
}
"""


def _hide_scraper_windows():
    """Hide off-screen Playwright windows from the taskbar."""
    try:
        import win32gui, win32con, time
        time.sleep(2)
        def _cb(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd): return
            if win32gui.GetClassName(hwnd) != "Chrome_WidgetWin_1": return
            if "EditorSuite" in win32gui.GetWindowText(hwnd): return
            try:
                x, y, _, _ = win32gui.GetWindowRect(hwnd)
                if x < -1000:
                    ex  = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                    ex |=  win32con.WS_EX_TOOLWINDOW
                    ex &= ~win32con.WS_EX_APPWINDOW
                    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex)
            except Exception:
                pass
        win32gui.EnumWindows(_cb, None)
    except Exception:
        pass


async def new_browser(pw, mute: bool = False):
    """
    Launch a persistent-context Chromium browser.
    Returns (None, ctx) — ctx IS the browser context; there is no separate
    browser object when using launch_persistent_context.

    Callers that do `browser, ctx = await new_browser(pw)` and then call
    `await browser.close()` need to call `await ctx.close()` instead.
    We return a _CtxWrapper as the first element so existing close() calls
    still work without any changes to callers.
    """
    args = (['--mute-audio'] if mute else []) + _BARGS
    exe  = _find_chromium_exe()
    kwargs = dict(
        user_data_dir   = _profile_dir(),
        headless        = False,
        args            = args,
        viewport        = {"width": 1280, "height": 900},
        user_agent      = _UA,
        locale          = "en-US",
    )
    if exe:
        kwargs["executable_path"] = exe

    ctx = await pw.chromium.launch_persistent_context(**kwargs)

    # Inject stealth JS into every new page before any scripts run
    await ctx.add_init_script(_STEALTH_JS)

    threading.Thread(target=_hide_scraper_windows, daemon=True).start()

    # Wrap ctx so callers can do `browser.close()` or `await browser.close()`
    class _CtxWrapper:
        async def close(self): await ctx.close()
        def __await__(self): return ctx.__await__()

    return _CtxWrapper(), ctx


async def new_page(ctx):
    """Return the existing blank tab if one is open, otherwise open a new one.
    launch_persistent_context always starts with one blank tab — reusing it
    prevents a visible second tab from appearing."""
    pages = ctx.pages
    if pages:
        return pages[0]
    return await ctx.new_page()
