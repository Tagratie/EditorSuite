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

    # ── Auto-install pip packages ─────────────────────────────────────────────
    for pkg, imp in [("flask", "flask"), ("pywin32", "win32gui"), ("playwright", "playwright")]:
        try:
            __import__(imp)
        except ImportError:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg, "--quiet"],
                stdout=_devnull, stderr=_devnull, **_nownd)

    # ── Playwright: check install location, install Chromium if missing ───────
    def _chromium_missing() -> bool:
        try:
            r = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"],
                capture_output=True, text=True, timeout=20, **_nownd
            )
            m = re.search(r"Install location:\s+(.+)", r.stdout)
            if not m:
                return False
            return not pathlib.Path(m.group(1).strip()).exists()
        except Exception:
            return False

    if _chromium_missing():
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            stdout=_devnull, stderr=_devnull, **_nownd
        )

    _sock.close()

    # ── Point Playwright to system-installed browsers (critical for .exe) ─────
    ms_playwright = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
    if os.path.isdir(ms_playwright):
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", ms_playwright)
    else:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
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
