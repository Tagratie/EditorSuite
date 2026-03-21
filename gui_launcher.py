import multiprocessing
multiprocessing.freeze_support()  # MUST be line 2 — stops Windows spawn loop

import sys, os, subprocess, pathlib, socket, re

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

if __name__ == "__main__":

    # ── Single-instance lock ──────────────────────────────────────────────────
    PORT = 7331
    _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    try:
        _sock.bind(("127.0.0.1", PORT))
        _sock.setblocking(False)
    except OSError:
        sys.exit(0)

    # ── Subprocess flags — hide any CMD windows on Windows ───────────────────
    _frozen  = getattr(sys, "frozen", False)
    _devnull = subprocess.DEVNULL
    _nownd   = {"creationflags": 0x08000000} if os.name == "nt" else {}  # CREATE_NO_WINDOW

    def _find_system_python() -> str | None:
        """Find a real python.exe — never returns the frozen .exe itself."""
        import shutil
        for candidate in ("py", "python3", "python"):
            found = shutil.which(candidate)
            if found and os.path.abspath(found) != os.path.abspath(sys.executable):
                return found
        # Fallback: walk common install locations
        for base in (
            os.path.expanduser(r"~\AppData\Local\Programs\Python"),
            r"C:\Python312", r"C:\Python311", r"C:\Python310",
            os.path.expanduser(r"~\AppData\Local\Python"),
        ):
            for root, dirs, files in os.walk(base):
                if "python.exe" in files:
                    return os.path.join(root, "python.exe")
        return None

    # ── When frozen, all subprocess calls must use real Python, not the .exe ──
    _py = _find_system_python() if _frozen else sys.executable

    # ── Auto-install pip packages (dev/unfrozen only) ─────────────────────────
    if not _frozen:
        for pkg, imp in [("flask", "flask"), ("pywin32", "win32gui"), ("playwright", "playwright")]:
            try:
                __import__(imp)
            except ImportError:
                subprocess.run(
                    [_py, "-m", "pip", "install", pkg, "--quiet"],
                    stdout=_devnull, stderr=_devnull, **_nownd)

    # ── Playwright: ensure Chromium is installed via real Python ──────────────
    ms_playwright = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")

    def _chromium_installed() -> bool:
        """Check ms-playwright folder directly — no subprocess needed."""
        if not os.path.isdir(ms_playwright):
            return False
        for entry in os.listdir(ms_playwright):
            if entry.lower().startswith("chromium"):
                exe = os.path.join(ms_playwright, entry, "chrome-win64", "chrome.exe")
                if os.path.isfile(exe):
                    return True
        return False

    def _install_chromium():
        """
        Try every possible way to run `playwright install chromium`.
        Order of attempts:
          1. Real python.exe -m playwright install chromium
          2. playwright.exe CLI (installed by pip into Scripts/)
          3. The frozen exe's bundled playwright driver (last resort)
        """
        import shutil

        # Attempt 1 — real Python
        if _py:
            r = subprocess.run(
                [_py, "-m", "playwright", "install", "chromium"],
                capture_output=True, **_nownd
            )
            if _chromium_installed():
                return

        # Attempt 2 — playwright.exe CLI in PATH or Scripts folders
        pw_cli = shutil.which("playwright")
        if not pw_cli:
            # Search common Scripts locations
            for base in (
                os.path.join(os.environ.get("LOCALAPPDATA",""), "Programs", "Python"),
                os.path.expanduser(r"~\AppData\Local\Programs\Python"),
                r"C:\Python312", r"C:\Python311", r"C:\Python310",
            ):
                for root, dirs, files in os.walk(base):
                    if "playwright.exe" in files:
                        pw_cli = os.path.join(root, "playwright.exe")
                        break
                if pw_cli:
                    break
        if pw_cli:
            subprocess.run(
                [pw_cli, "install", "chromium"],
                capture_output=True, **_nownd
            )
            if _chromium_installed():
                return

        # Attempt 3 — bundled playwright driver inside the frozen exe
        # PyInstaller extracts it to _MEIPASS; its node-based CLI can install
        mei = getattr(sys, "_MEIPASS", None)
        if mei:
            driver = os.path.join(mei, "playwright", "driver", "playwright.cmd")
            if not os.path.isfile(driver):
                driver = os.path.join(mei, "playwright", "driver", "playwright")
            if os.path.isfile(driver):
                subprocess.run(
                    [driver, "install", "chromium"],
                    capture_output=True, **_nownd
                )

    if not _chromium_installed():
        _install_chromium()

    _sock.close()

    # ── Always hard-set PLAYWRIGHT_BROWSERS_PATH ──────────────────────────────
    if os.path.isdir(ms_playwright):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = ms_playwright
    else:
        # Still not installed — try one more time now that sock is closed
        _install_chromium()
        if os.path.isdir(ms_playwright):
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = ms_playwright

    # ── Inject bundled binaries (yt-dlp, ffmpeg) into PATH ──────────────────
    # Bundled in the exe via build_exe.py — extracted to _MEIPASS at runtime.
    # Prepending _MEIPASS means every subprocess call everywhere finds them
    # without requiring anything installed on the user's system.
    _mei = getattr(sys, "_MEIPASS", None)
    if _mei and os.path.isdir(_mei):
        os.environ["PATH"] = _mei + os.pathsep + os.environ.get("PATH", "")

    # ── Load and start Flask server ───────────────────────────────────────────
    import importlib.util
    spec = importlib.util.spec_from_file_location("server", os.path.join(ROOT, "gui", "server.py"))
    srv  = importlib.util.module_from_spec(spec)
    sys.modules["gui.server"] = srv
    spec.loader.exec_module(srv)
    srv.start()
