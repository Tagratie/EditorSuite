"""
gui/server.py — Flask backend for EditorSuite GUI
"""
import os, sys, json, queue, threading, webbrowser, time, signal, subprocess
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
_PING_TIMEOUT = 4    # seconds before watchdog kills if no ping

def _watchdog():
    time.sleep(12)   # grace period at startup
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

@app.route("/api/browse-folder", methods=["POST"])
def api_browse_folder():
    """Open the modern IFileOpenDialog (Vista+ Explorer style, respects dark mode)."""
    try:
        import ctypes, ctypes.wintypes, uuid
        from ctypes import HRESULT

        CLSID_FileOpenDialog = "{DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7}"
        IID_IFileOpenDialog  = "{D57C7288-D4AD-4768-BE02-9D969532D960}"
        FOS_PICKFOLDERS      = 0x00000020
        FOS_FORCEFILESYSTEM  = 0x00000040

        ole32 = ctypes.windll.ole32

        class _GUID(ctypes.Structure):
            _fields_ = [("Data1",ctypes.c_ulong),("Data2",ctypes.c_ushort),
                        ("Data3",ctypes.c_ushort),("Data4",ctypes.c_ubyte*8)]

        def _guid(s):
            u = uuid.UUID(s); b = u.bytes_le; g = _GUID()
            g.Data1 = int.from_bytes(b[0:4],"little")
            g.Data2 = int.from_bytes(b[4:6],"little")
            g.Data3 = int.from_bytes(b[6:8],"little")
            g.Data4 = (ctypes.c_ubyte*8)(*b[8:]); return g

        ole32.CoInitialize(None)
        clsid = _guid(CLSID_FileOpenDialog)
        iid   = _guid(IID_IFileOpenDialog)
        ptr   = ctypes.c_void_p()
        hr = ole32.CoCreateInstance(ctypes.byref(clsid), None, 1,
                                    ctypes.byref(iid), ctypes.byref(ptr))
        if hr != 0: raise OSError(f"CoCreateInstance failed: {hr:#010x}")

        vt = ctypes.cast(
            ctypes.cast(ptr, ctypes.POINTER(ctypes.c_void_p))[0],
            ctypes.POINTER(ctypes.c_void_p))

        GetOptions = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint))(vt[10])
        SetOptions = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.c_uint)(vt[9])
        opts = ctypes.c_uint(0)
        GetOptions(ptr, ctypes.byref(opts))
        SetOptions(ptr, opts.value | FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM)

        # Find the app window HWND so the dialog is parented/focused correctly
        import win32gui
        app_hwnd = 0
        def _find_app(h, _):
            nonlocal app_hwnd
            if win32gui.IsWindowVisible(h) and "EditorSuite" in win32gui.GetWindowText(h):
                if win32gui.GetClassName(h) == "Chrome_WidgetWin_1":
                    app_hwnd = h
        win32gui.EnumWindows(_find_app, None)

        Show = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.wintypes.HWND)(vt[3])
        hr   = Show(ptr, app_hwnd)

        path = ""
        if hr == 0:
            si = ctypes.c_void_p()
            GetResult = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p,
                                           ctypes.POINTER(ctypes.c_void_p))(vt[20])
            if GetResult(ptr, ctypes.byref(si)) == 0 and si:
                si_vt = ctypes.cast(
                    ctypes.cast(si, ctypes.POINTER(ctypes.c_void_p))[0],
                    ctypes.POINTER(ctypes.c_void_p))
                GetDisplayName = ctypes.WINFUNCTYPE(
                    HRESULT, ctypes.c_void_p, ctypes.c_uint,
                    ctypes.POINTER(ctypes.c_wchar_p))(si_vt[5])
                name = ctypes.c_wchar_p()
                GetDisplayName(si, 0x80058000, ctypes.byref(name))
                if name.value:
                    path = name.value
                    ole32.CoTaskMemFree(name)

        ole32.CoUninitialize()
        return jsonify({"path": path})

    except Exception as e:
        return jsonify({"path": "", "error": str(e)})

@app.route("/api/shutdown", methods=["POST"])
def api_shutdown():
    def _kill():
        time.sleep(0.15)
        os._exit(0)  # instant — no cleanup chain
    threading.Thread(target=_kill, daemon=True).start()
    return jsonify({"ok": True})


def _find_chromium_exe() -> str:
    """Find any Chromium-based browser on Windows via registry + known paths."""
    if os.name != "nt":
        return ""
    import winreg

    # Registry keys where browsers register their exe path
    reg_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\opera.exe"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\launcher.exe"),  # Opera GX
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\opera.exe"),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\launcher.exe"),
    ]
    for hive, path in reg_paths:
        try:
            with winreg.OpenKey(hive, path) as k:
                exe = winreg.QueryValue(k, None)
                if exe and os.path.isfile(exe):
                    return exe
        except OSError:
            continue

    # Fallback: hardcoded common paths
    lappdata = os.environ.get("LOCALAPPDATA", "")
    pf       = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    pf86     = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    candidates = [
        os.path.join(lappdata, "Google","Chrome","Application","chrome.exe"),
        os.path.join(pf,       "Google","Chrome","Application","chrome.exe"),
        os.path.join(pf86,     "Google","Chrome","Application","chrome.exe"),
        os.path.join(pf86,     "Microsoft","Edge","Application","msedge.exe"),
        os.path.join(pf,       "Microsoft","Edge","Application","msedge.exe"),
        os.path.join(lappdata, "Programs","Opera","launcher.exe"),
        os.path.join(lappdata, "Programs","Opera GX","launcher.exe"),
        os.path.join(pf,       "Opera","launcher.exe"),
        os.path.join(lappdata, "Chromium","Application","chrome.exe"),
    ]
    for exe in candidates:
        if exe and os.path.isfile(exe):
            return exe
    return ""


def _strip_titlebar(pid: int):
    """Style window with dark rounded DWM frame and set custom icon."""
    try:
        import win32gui, win32con
    except ImportError:
        return

    import time, ctypes

    CHROMIUM_CLASSES = {"Chrome_WidgetWin_1", "OperaWindowClass", "BrowserWindowClass"}

    hwnd = None
    for _ in range(60):
        time.sleep(0.2)
        found = []
        def _cb(h, _):
            if not win32gui.IsWindowVisible(h): return
            if win32gui.GetClassName(h) not in CHROMIUM_CLASSES: return
            if "EditorSuite" in win32gui.GetWindowText(h):
                found.append(h)
        win32gui.EnumWindows(_cb, None)
        if found:
            hwnd = found[0]
            break

    if not hwnd:
        return

    # ── DWM: dark mode + rounded corners + matching border/caption color ──────
    try:
        dwm = ctypes.windll.dwmapi
        # Dark titlebar
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)
        # Rounded corners (Win11) — DWMWCP_ROUND = 2
        dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(ctypes.c_int(2)), 4)
        # Border color matches app bg (#14141a → BGR: 0x001a1414)
        dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(ctypes.c_int(0x001a1414)), 4)
        # Caption (titlebar) color — slightly lighter dark
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(ctypes.c_int(0x00100d0d)), 4)
        # Caption text color — off-white
        dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(ctypes.c_int(0x00f0f0f4)), 4)
    except Exception:
        pass

    # Keep normal resizable frame so Windows snapping / drag-to-top fullscreen work
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

    # ── Custom icon ───────────────────────────────────────────────────────────
    try:
        import win32con as wc
        ico = os.path.join(os.path.dirname(__file__), "static", "favicon.ico")
        if os.path.isfile(ico):
            big   = win32gui.LoadImage(None, ico, 1, 32, 32, 0x0010)
            small = win32gui.LoadImage(None, ico, 1, 16, 16, 0x0010)
            win32gui.SendMessage(hwnd, wc.WM_SETICON, 1, big)
            win32gui.SendMessage(hwnd, wc.WM_SETICON, 0, small)
    except Exception:
        pass


def _launch_app_window(url: str):
    """Open EditorSuite as app window — NEVER opens a normal browser tab."""
    import time
    time.sleep(1.4)

    if os.name == "nt":
        exe = _find_chromium_exe()
        if not exe:
            print("  [!] No Chrome/Edge/Opera found — open http://127.0.0.1:7331 manually.")
            return
        # Resolve launcher.exe (Opera wrapper) to actual opera.exe
        if "launcher.exe" in exe.lower():
            import glob
            folder = os.path.dirname(exe)
            opera_real = next(
                (f for f in glob.glob(os.path.join(folder, "*.exe"))
                 if os.path.basename(f).lower() == "opera.exe"), None)
            if not opera_real:
                for sub in os.listdir(folder):
                    candidate = os.path.join(folder, sub, "opera.exe")
                    if os.path.isfile(candidate):
                        opera_real = candidate; break
            if opera_real:
                exe = opera_real
        proc = subprocess.Popen(
            [exe, f"--app={url}", "--window-size=1300,840", "--window-position=60,30"],
            creationflags=0x08000000
        )
        threading.Thread(target=_strip_titlebar, args=(proc.pid,), daemon=True).start()
    elif sys.platform == "darwin":
        for chrome in [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]:
            if os.path.isfile(chrome):
                subprocess.Popen([chrome, f"--app={url}"])
                return
        print("  [!] No Chrome/Edge found — open http://127.0.0.1:7331 manually.")
    else:
        for b in ("google-chrome", "chromium-browser", "chromium", "microsoft-edge"):
            try:
                subprocess.Popen([b, f"--app={url}"]); return
            except FileNotFoundError:
                continue
        print("  [!] No Chromium browser found — open http://127.0.0.1:7331 manually.")


def start(port: int = 7331, open_browser: bool = True):
    if open_browser:
        url = f"http://127.0.0.1:{port}"
        threading.Thread(target=_launch_app_window, args=(url,), daemon=True).start()
    print(f"\n  EditorSuite GUI  →  http://127.0.0.1:{port}")
    print(f"  Press Ctrl+C to stop.\n")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True, use_reloader=False)
