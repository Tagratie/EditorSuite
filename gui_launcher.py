import sys, os, subprocess, threading

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# Auto-install dependencies
for pkg, imp in [("flask", "flask"), ("pywin32", "win32gui")]:
    try:
        __import__(imp)
    except ImportError:
        print(f"Installing {pkg} (one-time)...")
        subprocess.run([sys.executable, "-m", "pip", "install", pkg, "--quiet"])

import importlib.util
spec = importlib.util.spec_from_file_location("server", os.path.join(ROOT, "gui", "server.py"))
srv = importlib.util.module_from_spec(spec)
sys.modules["gui.server"] = srv
spec.loader.exec_module(srv)

srv.start()
