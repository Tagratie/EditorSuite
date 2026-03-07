import multiprocessing
multiprocessing.freeze_support()  # MUST be line 2 — stops Windows spawn loop

import sys, os, subprocess, pathlib, socket, re

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# ── When frozen as .exe, sys.executable IS the exe.
# Any subprocess.run([sys.executable, "-m", ...]) would re-launch the entire
# exe into memory (RAM spike), get killed by the socket lock only AFTER all
# frozen modules have already loaded.  We detect this early and use the real
# system Python instead, or skip installs entirely (everything is bundled).
_frozen = getattr(sys, "frozen", False)

def _find_system_python():
    """Return a real python.exe on the system, never the frozen exe."""
    if not _frozen:
        return sys.executable          # dev mode — fine to use directly
    # Try py launcher first (most Windows installs have it)
    for candidate in ["py", "python3", "python"]:
        try:
            r = subprocess.run([candidate, "--version"], capture_output=True, timeout=5)
            if r.returncode == 0:
                # Resolve to full path so we can be sure it is not our own exe
                import shutil
                full = shutil.which(candidate)
                if full and os.path.abspath(full).lower() != os.path.abspath(sys.executable).lower():
                    return full
        except Exception:
            continue
    return None          # no system Python found — skip installs silently


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
    _devnull = subprocess.DEVNULL
    _nownd   = {"creationflags": 0x08000000} if os.name == "nt" else {}  # CREATE_NO_WINDOW

    # ── Auto-install pip packages (skipped when frozen — everything is bundled) ──
    if not _frozen:
        for pkg, imp in [("flask", "flask"), ("pywin32", "win32gui"), ("playwright", "playwright")]:
            try:
                __import__(imp)
            except ImportError:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", pkg, "--quiet"],
                    stdout=_devnull, stderr=_devnull, **_nownd)
    # When frozen: deps are bundled by PyInstaller — no subprocess needed.
    # If playwright somehow isn't bundled we handle it below via system Python.

    # ── Playwright: check install location, install Chromium if missing ───────
    def _chromium_missing() -> bool:
        """Check if Chromium browser files are present — without spawning the exe."""
        # Fast path: just check the known ms-playwright directory directly
        ms_playwright = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
        if not os.path.isdir(ms_playwright):
            return True
        # Look for any chromium subfolder
        try:
            for entry in os.listdir(ms_playwright):
                if entry.lower().startswith("chromium"):
                    full = os.path.join(ms_playwright, entry)
                    if os.path.isdir(full):
                        return False
        except Exception:
            pass
        return True

    if _chromium_missing():
        syspy = _find_system_python()
        if syspy:
            subprocess.run(
                [syspy, "-m", "playwright", "install", "chromium"],
                stdout=_devnull, stderr=_devnull, **_nownd
            )
        # If no system Python, user will need to install Chromium separately;
        # server.py will surface a clear error when a scraper tool tries to run.

    _sock.close()

    # ── Point Playwright to system-installed browsers (critical for .exe) ─────
    ms_playwright = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
    if os.path.isdir(ms_playwright):
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", ms_playwright)
    else:
        syspy = _find_system_python()
        if syspy:
            subprocess.run(
                [syspy, "-m", "playwright", "install", "chromium"],
                stdout=_devnull, stderr=_devnull, **_nownd
            )
        if os.path.isdir(ms_playwright):
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = ms_playwright

    # ── Load and start Flask server ───────────────────────────────────────────
    import importlib.util
    spec = importlib.util.spec_from_file_location("server", os.path.join(ROOT, "gui", "server.py"))
    srv  = importlib.util.module_from_spec(spec)
    sys.modules["gui.server"] = srv
    spec.loader.exec_module(srv)
    srv.start()
