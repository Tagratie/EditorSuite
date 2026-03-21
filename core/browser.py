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
    # Suppress translate bar and first-run UI
    "--disable-features=Translate,TranslateUI",
    "--lang=en-US",
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


def _ensure_chromium_installed():
    """
    Install Chromium if missing. Tries multiple methods, never raises.
    Called at module load AND inside new_browser() as a safety net.
    """
    import subprocess as _sp

    if _find_chromium_exe():
        return  # already installed — fast path

    browsers_path = os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "ms-playwright"
    )
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = browsers_path
    _no_window = {"creationflags": 0x08000000} if os.name == "nt" else {}

    print("[EditorSuite] Chromium not found — installing…")

    # ── Method 1: playwright's bundled Node driver (works inside frozen exe) ──
    try:
        from playwright._impl._driver import compute_driver_executable
        drv_exe, drv_cli = compute_driver_executable()
        drv_exe = str(drv_exe)
        drv_cli = str(drv_cli)
        if os.path.isfile(drv_exe):
            _sp.run(
                [drv_exe, drv_cli, "install", "chromium"],
                env=env, timeout=300,
                stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
                **_no_window,
            )
    except Exception as _e:
        print(f"[EditorSuite] Method 1 failed: {_e}")

    if _find_chromium_exe():
        print("[EditorSuite] Chromium installed ✓ (method 1)")
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browsers_path
        return

    # ── Method 2: playwright CLI on PATH or in Scripts folders ────────────────
    try:
        import shutil
        pw_cli = shutil.which("playwright")
        if not pw_cli:
            lapp = os.environ.get("LOCALAPPDATA", "")
            for base in (
                os.path.join(lapp, "Programs", "Python"),
                os.path.expanduser(r"~\AppData\Local\Programs\Python"),
                r"C:\Python312", r"C:\Python311", r"C:\Python310",
            ):
                for root, _dirs, files in os.walk(base):
                    if "playwright.exe" in files:
                        pw_cli = os.path.join(root, "playwright.exe")
                        break
                if pw_cli:
                    break
        if pw_cli and os.path.isfile(pw_cli):
            _sp.run(
                [pw_cli, "install", "chromium"],
                env=env, timeout=300,
                stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
                **_no_window,
            )
    except Exception as _e:
        print(f"[EditorSuite] Method 2 failed: {_e}")

    if _find_chromium_exe():
        print("[EditorSuite] Chromium installed ✓ (method 2)")
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browsers_path
        return

    # ── Method 3: python -m playwright install ────────────────────────────────
    try:
        import sys
        py = sys.executable
        if getattr(sys, "frozen", False):
            import shutil
            py = shutil.which("python") or shutil.which("python3") or ""
        if py and os.path.isfile(py):
            _sp.run(
                [py, "-m", "playwright", "install", "chromium"],
                env=env, timeout=300,
                stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
                **_no_window,
            )
    except Exception as _e:
        print(f"[EditorSuite] Method 3 failed: {_e}")

    if _find_chromium_exe():
        print("[EditorSuite] Chromium installed ✓ (method 3)")
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browsers_path
    else:
        print("[EditorSuite] WARNING: could not install Chromium automatically.")


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
    # Ensure Chromium exists before we even try to build kwargs
    _ensure_chromium_installed()

    exe  = _find_chromium_exe()
    args = (['--mute-audio'] if mute else []) + _BARGS
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


async def new_login_browser(pw, title: str = "EditorSuite — Login"):
    """
    Launch a VISIBLE, centered browser window specifically for login/OAuth flows.
    Does NOT use --window-position=-32000,-32000. Returns (wrapper, ctx).
    """
    _ensure_chromium_installed()
    exe = _find_chromium_exe()

    # Position the login window centered on the EditorSuite app window
    wx, wy = 200, 100
    try:
        import ctypes, win32gui
        es_rect = [None]
        def _find_es(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and "EditorSuite" in win32gui.GetWindowText(hwnd):
                if win32gui.GetClassName(hwnd) == "Chrome_WidgetWin_1":
                    es_rect[0] = win32gui.GetWindowRect(hwnd)
        win32gui.EnumWindows(_find_es, None)
        if es_rect[0]:
            ex, ey, ew, eh = es_rect[0]
            # Center a 900x720 window over the ES window
            wx = ex + (ew - ex - 900) // 2
            wy = ey + (eh - ey - 720) // 2
            wx = max(0, wx); wy = max(0, wy)
        else:
            # Fallback: screen center
            sw = ctypes.windll.user32.GetSystemMetrics(0)
            sh = ctypes.windll.user32.GetSystemMetrics(1)
            wx, wy = max(0, (sw - 900) // 2), max(0, (sh - 720) // 2)
    except Exception:
        pass

    login_args = [
        "--disable-blink-features=AutomationControlled",
        f"--window-position={wx},{wy}",
        "--window-size=900,720",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-features=Translate,TranslateUI",
        "--lang=en-US",
    ]

    kwargs = dict(
        user_data_dir = _profile_dir(),   # share session so login persists
        headless      = False,
        args          = login_args,
        viewport      = {"width": 900, "height": 720},
        user_agent    = _UA,
        locale        = "en-US",
    )
    if exe:
        kwargs["executable_path"] = exe

    ctx = await pw.chromium.launch_persistent_context(**kwargs)
    await ctx.add_init_script(_STEALTH_JS)

    # Bring the NEW login window to foreground (not ES itself)
    try:
        import win32gui, win32process, time as _t
        _t.sleep(1.0)
        # Find chromium windows that are NOT the ES window
        es_pid = None
        try:
            import psutil
            es_pid = os.getpid()
        except Exception:
            pass
        def _focus_new(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd): return
            if win32gui.GetClassName(hwnd) != "Chrome_WidgetWin_1": return
            if "EditorSuite" in win32gui.GetWindowText(hwnd): return
            try:
                import ctypes
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
        win32gui.EnumWindows(_focus_new, None)
    except Exception:
        pass

    class _CtxWrapper:
        async def close(self): await ctx.close()
        def __await__(self): return ctx.__await__()

    return _CtxWrapper(), ctx



    """Return the existing blank tab if one is open, otherwise open a new one.
    launch_persistent_context always starts with one blank tab — reusing it
    prevents a visible second tab from appearing."""
    pages = ctx.pages
    if pages:
        return pages[0]
    return await ctx.new_page()
