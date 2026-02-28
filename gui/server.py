"""
gui/server.py — Flask backend for EditorSuite GUI
"""
import os, sys, json, queue, threading, webbrowser, time, signal
from pathlib import Path

ROOT = str(Path(__file__).parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from flask import Flask, Response, request, jsonify, send_from_directory, send_file
from gui.detector import detect
from gui.runner   import run_task

app = Flask(__name__, static_folder=str(Path(__file__).parent / "static"))

# ── Heartbeat watchdog — kills process when browser tab is closed ──────────────
_last_ping = time.time()
_PING_TIMEOUT = 15   # seconds of silence before shutdown

def _watchdog():
    time.sleep(20)   # grace period at startup
    while True:
        time.sleep(5)
        if time.time() - _last_ping > _PING_TIMEOUT:
            print("\n  [EditorSuite] Browser disconnected — shutting down.")
            os.kill(os.getpid(), signal.SIGTERM)

threading.Thread(target=_watchdog, daemon=True).start()


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/detect", methods=["POST"])
def api_detect():
    text = (request.json or {}).get("text", "")
    return jsonify(detect(text))

@app.route("/api/run", methods=["POST"])
def api_run():
    data     = request.json or {}
    detected = data.get("detected", {})
    options  = data.get("options",  {})
    q        = queue.Queue()
    threading.Thread(target=run_task, args=(detected, options, q), daemon=True).start()

    def generate():
        while True:
            try:
                item = q.get(timeout=120)
            except queue.Empty:
                yield "data: " + json.dumps({"type":"error","text":"Timed out"}) + "\n\n"
                break
            if item is None:
                yield "data: " + json.dumps({"type":"close"}) + "\n\n"
                break
            yield "data: " + json.dumps(item) + "\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@app.route("/api/open", methods=["POST"])
def api_open():
    path = (request.json or {}).get("path", "")
    if path and os.path.exists(path):
        if os.name == "nt":          os.startfile(path)
        elif sys.platform == "darwin":
            import subprocess; subprocess.Popen(["open", path])
        else:
            import subprocess; subprocess.Popen(["xdg-open", path])
    return jsonify({"ok": True})

@app.route("/api/tool", methods=["POST"])
def api_tool():
    """Run a named tool (from the sidebar menu) via SSE stream."""
    data    = request.json or {}
    tool_id = data.get("tool_id", "")
    options = data.get("options", {})
    q       = queue.Queue()

    from gui.runner import run_named_tool
    threading.Thread(target=run_named_tool, args=(tool_id, options, q), daemon=True).start()

    def generate():
        while True:
            try:
                item = q.get(timeout=120)
            except queue.Empty:
                yield "data: " + json.dumps({"type":"error","text":"Timed out"}) + "\n\n"
                break
            if item is None:
                yield "data: " + json.dumps({"type":"close"}) + "\n\n"
                break
            yield "data: " + json.dumps(item) + "\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@app.route("/api/download-file", methods=["GET"])
def api_download_file():
    """Serve a local file as a native browser download (GET so the browser handles it)."""
    path = request.args.get("path", "")
    if not path or not os.path.isfile(path):
        return "File not found", 404
    return send_file(
        os.path.abspath(path),
        as_attachment=True,
        download_name=os.path.basename(path)
    )

@app.route("/api/open-folder", methods=["POST"])
def api_open_folder():
    """Open a folder in the OS file explorer, forced to foreground."""
    path = (request.json or {}).get("path", "")
    folder = os.path.dirname(os.path.abspath(path)) if os.path.isfile(path) else os.path.abspath(path)
    if not folder or not os.path.isdir(folder):
        return jsonify({"ok": False, "error": "Folder not found"})
    try:
        if os.name == "nt":
            import subprocess, ctypes
            # Open explorer then forcibly bring it to foreground
            subprocess.Popen(["explorer", os.path.normpath(folder)])
            # Give explorer a moment to open, then steal focus via keybd_event trick
            def _bring_to_front():
                import time; time.sleep(0.5)
                try:
                    # ALT keypress releases foreground lock so SetForegroundWindow works
                    ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
                    # Find the explorer window and raise it
                    hwnd = ctypes.windll.user32.FindWindowW("CabinetWClass", None)
                    if hwnd:
                        ctypes.windll.user32.ShowWindow(hwnd, 9)   # SW_RESTORE
                        ctypes.windll.user32.SetForegroundWindow(hwnd)
                except Exception:
                    pass
            threading.Thread(target=_bring_to_front, daemon=True).start()
        elif sys.platform == "darwin":
            import subprocess; subprocess.Popen(["open", folder])
        else:
            import subprocess; subprocess.Popen(["xdg-open", folder])
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})
    return jsonify({"ok": True})


@app.route("/api/config", methods=["GET"])
def api_config_get():
    from utils.config import load_config
    return jsonify(load_config())

@app.route("/api/config", methods=["POST"])
def api_config_post():
    from utils.config import load_config, save_config
    updates = request.json or {}
    cfg = load_config()
    cfg.update(updates)
    save_config(cfg)
    return jsonify({"ok": True})


@app.route("/api/ping", methods=["POST"])
def api_ping():
    global _last_ping
    _last_ping = time.time()
    return jsonify({"ok": True})

@app.route("/api/shutdown", methods=["POST"])
def api_shutdown():
    """Called by beforeunload — graceful shutdown."""
    def _kill():
        time.sleep(0.3)
        os.kill(os.getpid(), signal.SIGTERM)
    threading.Thread(target=_kill, daemon=True).start()
    return jsonify({"ok": True})


def _focus_browser():
    """After opening the browser, bring it to the foreground (Windows)."""
    import time; time.sleep(2.5)
    if os.name == "nt":
        try:
            import ctypes
            # Release foreground lock then find Chrome/Edge/Firefox window
            ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
            for cls in ["Chrome_WidgetWin_1", "MozillaWindowClass", "Edge_WidgetWin_1"]:
                hwnd = ctypes.windll.user32.FindWindowW(cls, None)
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 9)
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    break
        except Exception:
            pass


def start(port: int = 7331, open_browser: bool = True):
    if open_browser:
        def _open():
            import time; time.sleep(1.4)
            webbrowser.open(f"http://127.0.0.1:{port}")
            _focus_browser()
        threading.Thread(target=_open, daemon=True).start()
    print(f"\n  EditorSuite GUI  →  http://127.0.0.1:{port}")
    print(f"  Press Ctrl+C to stop.\n")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
