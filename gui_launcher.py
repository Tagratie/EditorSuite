import sys, os, subprocess

# Force project root onto path BEFORE any other imports
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# Auto-install flask
try:
    import flask
except ImportError:
    print("Installing Flask (one-time)...")
    subprocess.run([sys.executable, "-m", "pip", "install", "flask", "--quiet"])
    import flask

# Import server directly by file path — avoids any package resolution issues
import importlib.util
spec = importlib.util.spec_from_file_location(
    "server", os.path.join(ROOT, "gui", "server.py")
)
server = importlib.util.module_from_spec(spec)
sys.modules["gui.server"] = server
spec.loader.exec_module(server)

server.start()
