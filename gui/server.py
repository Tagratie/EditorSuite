"""
gui/server.py — Flask backend for EditorSuite GUI
"""
import os, sys, json, queue, threading, webbrowser
from pathlib import Path

ROOT = str(Path(__file__).parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from flask import Flask, Response, request, jsonify, send_from_directory
from gui.detector import detect
from gui.runner   import run_task

app = Flask(__name__, static_folder=str(Path(__file__).parent / "static"))

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

def start(port: int = 7331, open_browser: bool = True):
    if open_browser:
        threading.Timer(1.4, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    print(f"\n  EditorSuite GUI  →  http://127.0.0.1:{port}")
    print(f"  Press Ctrl+C to stop.\n")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
