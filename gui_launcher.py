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
        print("  EditorSuite already running.")
        sys.exit(0)

    # ── Auto-install pip packages ─────────────────────────────────────────────
    # Determine if running as frozen exe — suppress console output if so
    _frozen = getattr(sys, "frozen", False)
    _devnull = subprocess.DEVNULL if _frozen else None

    for pkg, imp in [("flask", "flask"), ("pywin32", "win32gui"), ("playwright", "playwright")]:
        try:
            __import__(imp)
        except ImportError:
            if not _frozen:
                print(f"  Installing {pkg} (one-time)...")
            subprocess.run([sys.executable, "-m", "pip", "install", pkg, "--quiet"],
                           stdout=_devnull, stderr=_devnull)

    # ── Playwright: check install location from dry-run, install if missing ───
    def _chromium_missing() -> bool:
        try:
            r = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"],
                capture_output=True, text=True, timeout=20
            )
            # Parse "Install location: /some/path/chromium-XXXX"
            m = re.search(r"Install location:\s+(.+)", r.stdout)
            if not m:
                return False  # can't parse — assume ok, don't block startup
            install_path = pathlib.Path(m.group(1).strip())
            return not install_path.exists()
        except Exception:
            return False  # on any error, don't block startup

    if _chromium_missing():
        if not _frozen:
            print("  Installing Playwright Chromium (one-time, ~150 MB)...")
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            stdout=_devnull, stderr=_devnull
        )
        if not _frozen:
            print("  [✓] Done.")

    _sock.close()

    # ── Point Playwright to system-installed browsers (critical when frozen as .exe) ──
    # PyInstaller extracts to a temp dir; without this Playwright looks there for
    # chromium and fails. PLAYWRIGHT_BROWSERS_PATH redirects it to the real install.
    ms_playwright = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
    if os.path.isdir(ms_playwright):
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", ms_playwright)
    else:
        # First run or non-standard install — run install now to populate it
        print("  Playwright browsers not found — installing now...")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
        if os.path.isdir(ms_playwright):
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = ms_playwright

    # ── Load and start Flask server ───────────────────────────────────────────
    import importlib.util
    spec = importlib.util.spec_from_file_location("server", os.path.join(ROOT, "gui", "server.py"))
    srv  = importlib.util.module_from_spec(spec)
    sys.modules["gui.server"] = srv
    spec.loader.exec_module(srv)
    srv.start()
