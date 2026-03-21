"""
gui/server.py — Flask backend for EditorSuite GUI
"""
import os, sys, json, queue, threading, webbrowser, time, signal, subprocess
from datetime import date, datetime
from pathlib import Path

ROOT = str(Path(__file__).parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from flask import Flask, Response, request, jsonify, send_from_directory, send_file
from gui.detector import detect
from gui.runner   import run_task

app = Flask(__name__, static_folder=str(Path(__file__).parent / "static"))


def _json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, Path):
        return str(o)
    if isinstance(o, set):
        return list(o)
    return str(o)

# ── TikTok API helper ─────────────────────────────────────────────────────────
def _tt_api(endpoint: str, params: dict = None, method: str = "GET",
             body: dict = None) -> dict:
    """
    Make a TikTok Content API request using the stored access token.
    endpoint: e.g. "/v2/video/list/"
    Returns parsed JSON dict, or raises on error.
    """
    import urllib.request, urllib.parse
    from utils.config import load_config
    cfg   = load_config()
    token = cfg.get("tiktok_access_token","").strip()
    if not token:
        raise ValueError("Not connected to TikTok — sign in first.")
    base  = "https://open.tiktokapis.com"
    url   = base + endpoint
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data  = json.dumps(body or {}).encode() if body is not None else None
    req   = urllib.request.Request(
        url, data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


# Single-run lock to prevent overlapping tool executions (results crossing streams).
_RUN_LOCK = threading.Lock()
_RUNNING = False


def _try_start_run() -> bool:
    global _RUNNING
    with _RUN_LOCK:
        if _RUNNING:
            return False
        _RUNNING = True
        return True


def _finish_run() -> None:
    global _RUNNING
    with _RUN_LOCK:
        _RUNNING = False

# ── Heartbeat watchdog — was killing process on idle tab ───────────────────────
# We now keep the server alive until it is explicitly shut down via /api/shutdown
# (triggered when the app window/tab actually closes).
_last_ping = time.time()
_PING_TIMEOUT = None   # no auto-shutdown on idle; browser close still calls /api/shutdown

def _watchdog():
    # Preserved for future use; currently disabled by _PING_TIMEOUT=None.
    if not _PING_TIMEOUT:
        return
    time.sleep(12)   # grace period at startup
    while True:
        time.sleep(5)
        if time.time() - _last_ping > _PING_TIMEOUT:
            print("\n  [EditorSuite] Browser disconnected — shutting down.")
            os.kill(os.getpid(), signal.SIGTERM)

if _PING_TIMEOUT:
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
    if not _try_start_run():
        return jsonify({"error": "busy", "message": "A tool is already running."}), 409
    data     = request.json or {}
    detected = data.get("detected", {})
    options  = data.get("options",  {})
    q        = queue.Queue()
    threading.Thread(target=run_task, args=(detected, options, q), daemon=True).start()

    def generate():
        try:
            while True:
                try:
                    item = q.get(timeout=120)
                except queue.Empty:
                    yield "data: " + json.dumps({"type":"error","text":"Timed out"}, default=_json_default) + "\n\n"
                    break
                if item is None:
                    yield "data: " + json.dumps({"type":"close"}, default=_json_default) + "\n\n"
                    break
                yield "data: " + json.dumps(item, default=_json_default) + "\n\n"
        finally:
            _finish_run()

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
    if not _try_start_run():
        return jsonify({"error": "busy", "message": "A tool is already running."}), 409
    data    = request.json or {}
    tool_id = data.get("tool_id", "")
    options = data.get("options", {})
    q       = queue.Queue()

    from gui.runner import run_named_tool
    threading.Thread(target=run_named_tool, args=(tool_id, options, q), daemon=True).start()

    def generate():
        try:
            while True:
                try:
                    item = q.get(timeout=120)
                except queue.Empty:
                    yield "data: " + json.dumps({"type":"error","text":"Timed out"}, default=_json_default) + "\n\n"
                    break
                if item is None:
                    yield "data: " + json.dumps({"type":"close"}, default=_json_default) + "\n\n"
                    break
                yield "data: " + json.dumps(item, default=_json_default) + "\n\n"
        finally:
            _finish_run()

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
    import os, sys
    from utils.config import load_config
    cfg = load_config()

    # ── Sanitize root_dir ──────────────────────────────────────────────────
    # If root_dir is empty, relative, or somehow inside _MEIPASS / Temp,
    # replace it with the proper default (user's Videos folder).
    _bad_dirs = (
        getattr(sys, "_MEIPASS", None),
        os.environ.get("TEMP"), os.environ.get("TMP"),
        os.path.join(os.environ.get("LOCALAPPDATA",""), "EditorSuite", "runtime"),
    )
    _root = cfg.get("root_dir", "")
    _is_bad = (
        not _root
        or not os.path.isabs(_root)
        or any(b and _root.startswith(b) for b in _bad_dirs if b)
    )
    if _is_bad:
        _root = os.path.join(os.path.expanduser("~"), "Videos", "EditorSuite")
        cfg["root_dir"] = _root
        # Persist the fix so it doesn't re-default on next load
        try:
            from utils.config import save_config
            _persisted = load_config()
            if not _persisted.get("root_dir") or not os.path.isabs(_persisted.get("root_dir","")):
                _persisted["root_dir"] = _root
                save_config(_persisted)
        except Exception:
            pass

    cfg["default_output"] = os.path.join(os.path.expanduser("~"), "Videos", "EditorSuite")
    return jsonify(cfg)

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

@app.route("/api/browse-file", methods=["POST"])
def api_browse_file():
    """Open a native file picker dialog (IFileOpenDialog)."""
    try:
        import ctypes, ctypes.wintypes, uuid
        from ctypes import HRESULT
        filters_raw = (request.json or {}).get("filters", [])
        CLSID_FileOpenDialog = "{DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7}"
        IID_IFileOpenDialog  = "{D57C7288-D4AD-4768-BE02-9D969532D960}"
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
        clsid = _guid(CLSID_FileOpenDialog); iid = _guid(IID_IFileOpenDialog)
        ptr = ctypes.c_void_p()
        hr = ole32.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(ptr))
        if hr != 0: raise OSError(f"CoCreateInstance failed: {hr:#010x}")
        vt = ctypes.cast(ctypes.cast(ptr, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(ctypes.c_void_p))
        Show = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.wintypes.HWND)(vt[3])
        import win32gui
        app_hwnd = 0
        def _find(h, _):
            nonlocal app_hwnd
            if win32gui.IsWindowVisible(h) and "EditorSuite" in win32gui.GetWindowText(h):
                if win32gui.GetClassName(h) == "Chrome_WidgetWin_1": app_hwnd = h
        win32gui.EnumWindows(_find, None)
        hr = Show(ptr, app_hwnd)
        path = ""
        if hr == 0:
            si = ctypes.c_void_p()
            GetResult = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))(vt[20])
            if GetResult(ptr, ctypes.byref(si)) == 0 and si:
                si_vt = ctypes.cast(ctypes.cast(si, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(ctypes.c_void_p))
                GetDisplayName = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_wchar_p))(si_vt[5])
                name = ctypes.c_wchar_p()
                GetDisplayName(si, 0x80058000, ctypes.byref(name))
                if name.value: path = name.value; ole32.CoTaskMemFree(name)
        ole32.CoUninitialize()
        return jsonify({"path": path})
    except Exception as e:
        return jsonify({"path": "", "error": str(e)})


@app.route("/api/3d-search", methods=["GET"])
def api_3d_search():
    """Proxy Sketchfab search — avoids CORS in the browser app."""
    import urllib.request, urllib.parse
    q   = request.args.get("q", "").strip()
    cat = request.args.get("cat", "all").strip()
    free = request.args.get("free", "0") == "1"
    if not q:
        return jsonify({"results": [], "source": "Sketchfab"})
    # Build search query — append category keyword if set
    search_q = q if cat == "all" else f"{q} {cat}"
    params = {
        "q": search_q,
        "count": "16",
        "sort_by": "-likeCount",
        "type": "models",
    }
    if free:
        params["downloadable"] = "true"
    url = "https://api.sketchfab.com/v3/models?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EditorSuite/2.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
        results = data.get("results", [])
        # Trim to essential fields to keep response small
        slim = []
        for m in results:
            slim.append({
                "uid":          m.get("uid", ""),
                "name":         m.get("name", ""),
                "viewerUrl":    m.get("viewerUrl", f"https://sketchfab.com/models/{m.get('uid','')}"),
                "thumbnails":   m.get("thumbnails", {}),
                "user":         {"username": (m.get("user") or {}).get("username", "")},
                "faceCount":    m.get("faceCount", 0),
                "likeCount":    m.get("likeCount", 0),
                "isDownloadable": m.get("isDownloadable", False),
            })
        return jsonify({"results": slim, "source": "Sketchfab"})
    except Exception as e:
        return jsonify({"results": [], "source": "Sketchfab", "error": str(e)})


@app.route("/api/creator-latest", methods=["GET"])
def api_creator_latest():
    """
    Return the latest non-pinned post for a watched creator.
    If the creator is the authenticated user → TikTok API.
    Otherwise → yt-dlp RSS (no Playwright, no scraping).
    """
    import subprocess, urllib.request
    handle = request.args.get("handle","").strip().lstrip("@")
    if not handle:
        return jsonify({"error":"no handle"}), 400

    from utils.config import load_config
    from gui.runner import _find_bin
    cfg   = load_config()
    token = cfg.get("tiktok_access_token","").strip()
    my_user = cfg.get("tiktok_username","").strip().lower()

    # If the watched creator is our own account, use the Content API
    if token and handle.lower() == my_user:
        try:
            fields = "id,create_time,share_url,video_description"
            data   = _tt_api(
                "/v2/video/list/",
                params={"fields": fields},
                method="POST",
                body={"max_count": 5},
            )
            videos = data.get("data",{}).get("videos") or []
            for v in videos:
                if v.get("id"):
                    from datetime import datetime
                    ts = v.get("create_time",0)
                    return jsonify({
                        "latest_id":   str(v["id"]),
                        "latest_url":  v.get("share_url",""),
                        "latest_time": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "",
                    })
            return jsonify({"latest_id":"","latest_url":"","latest_time":""})
        except Exception as e:
            pass  # fall through to yt-dlp

    # For any creator → yt-dlp: scrape RSS feed (fast, no browser)
    try:
        _no_win = {"creationflags": 0x08000000} if os.name == "nt" else {}
        r = subprocess.run(
            [_find_bin("yt-dlp"),
             f"https://www.tiktok.com/@{handle}",
             "--dump-json", "--playlist-end", "8",
             "--no-warnings", "--quiet", "--flat-playlist"],
            capture_output=True, text=True, timeout=25,
            encoding="utf-8", errors="replace", **_no_win
        )
        candidates = []  # (create_time, id, url)
        for line in r.stdout.strip().splitlines():
            try:
                item = json.loads(line)
                vid_id = str(item.get("id") or "")
                if not vid_id: continue
                ts  = item.get("timestamp") or item.get("upload_date") or 0
                # Skip if title hints at pinned (yt-dlp doesn't expose isTop)
                title = (item.get("title") or "").lower()
                url   = item.get("url") or item.get("webpage_url") or f"https://www.tiktok.com/@{handle}/video/{vid_id}"
                candidates.append((ts, vid_id, url, title))
            except Exception:
                pass
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            _, vid_id, url, _ = candidates[0]
            from datetime import datetime
            ts_val = candidates[0][0]
            try:
                ts_str = datetime.fromtimestamp(int(ts_val)).strftime("%Y-%m-%d %H:%M") if ts_val else ""
            except Exception:
                ts_str = str(ts_val)
            return jsonify({"latest_id": vid_id, "latest_url": url, "latest_time": ts_str})
        return jsonify({"latest_id":"","latest_url":"","latest_time":""})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/connect-tiktok", methods=["POST"])
def api_connect_tiktok():
    """
    Open TikTok login in a centered visible browser window (Playwright).
    User just logs into their normal TikTok account — no developer setup needed.
    Auto-detects login by watching TikTok API responses.
    """
    import threading, asyncio, time
    result     = {}
    done_event = threading.Event()

    async def _do_login():
        from playwright.async_api import async_playwright
        from core.browser import new_login_browser
        try:
            async with async_playwright() as pw:
                browser, ctx = await new_login_browser(pw)
                try:
                    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
                    found = {}

                    # ── Response listener — catches API calls post-login ──
                    async def on_resp(response):
                        if found: return
                        url = response.url
                        # Broad set of endpoints TikTok calls when a user is authenticated
                        triggers = (
                            "/api/user/detail",
                            "/api/recommend/",
                            "/passport/web/account",
                            "/api/post/item_list",
                            "/api/homepage/",
                            "/aweme/v1/feed",
                            "/tiktok/v1/feed",
                            "/web/user/info",
                            "/creator-micro/user/",
                            "/api/creator/",
                        )
                        if not any(t in url for t in triggers): return
                        try:
                            body = await response.json()
                            # Walk common response shapes
                            for shape in (
                                body.get("userInfo") or {},
                                body.get("UserInfo") or {},
                                {"user": body.get("user")} if body.get("user") else {},
                            ):
                                user = shape.get("user") or shape.get("User") or {}
                                uid  = user.get("uniqueId") or user.get("unique_id","")
                                if uid:
                                    stats = (shape.get("stats") or shape.get("Stats") or
                                             body.get("stats") or {})
                                    found["username"]  = uid
                                    found["nickname"]  = user.get("nickname", uid)
                                    found["followers"] = stats.get("followerCount", 0)
                                    return
                        except Exception:
                            pass

                    page.on("response", on_resp)

                    # Go to foryou first — if already logged in this loads immediately
                    # and triggers user API calls; if not, TikTok redirects to /login
                    try:
                        await page.goto("https://www.tiktok.com/foryou",
                                        wait_until="domcontentloaded", timeout=25000)
                    except Exception:
                        await page.goto("https://www.tiktok.com/login",
                                        wait_until="domcontentloaded", timeout=25000)

                    for i in range(180):
                        await asyncio.sleep(1)
                        if found.get("username"): break

                        # Every 5s: try JS extraction from TikTok's global state
                        if i % 5 == 4:
                            try:
                                uid = await page.evaluate("""() => {
                                    try {
                                        // TikTok stores user in several places
                                        const d = window.__NEXT_DATA__;
                                        const u = (d && d.props &&
                                            (d.props.pageProps?.userInfo?.user ||
                                             d.props.initialProps?.userInfo?.user));
                                        if (u && u.uniqueId) return u.uniqueId;
                                        // Redux store
                                        const s = window.__redux_store__ ||
                                                  window.store;
                                        if (s) {
                                            const st = s.getState();
                                            const uid = st?.user?.loginUser?.uniqueId ||
                                                        st?.commonProps?.loginUser?.uniqueId;
                                            if (uid) return uid;
                                        }
                                    } catch(e) {}
                                    return null;
                                }""")
                                if uid:
                                    found["username"] = uid
                                    found["nickname"] = uid
                                    found["followers"] = 0
                            except Exception:
                                pass

                        # At 20s if still not found and on login page, stay there
                        # At 30s navigate to foryou to force API calls
                        if i == 30 and not found:
                            try:
                                cur = page.url
                                if "login" not in cur:
                                    # Already past login — navigate to profile to force API
                                    await page.goto("https://www.tiktok.com/profile",
                                                    wait_until="domcontentloaded", timeout=15000)
                                else:
                                    # Still on login — user hasn't logged in yet, keep waiting
                                    pass
                            except Exception:
                                pass

                    if found.get("username"):
                        result.update(found)
                        result["status"] = "ok"
                        # ── Scrape analytics page for real stats ──────────
                        try:
                            analytics = {}
                            await page.goto(
                                "https://www.tiktok.com/tiktokstudio/content",
                                wait_until="domcontentloaded", timeout=20000
                            )
                            await asyncio.sleep(3)

                            async def on_analytics(response):
                                analytics_urls = (
                                    "/api/creator/analytics/",
                                    "/api/statistics/",
                                    "/creator-micro/analytics/",
                                    "/tiktok/web/analytics/",
                                    "/api/data/analytics/",
                                )
                                if not any(u in response.url for u in analytics_urls):
                                    return
                                try:
                                    body = await response.json()
                                    # Flatten any analytics data we find
                                    for k, v in body.items():
                                        if isinstance(v, (int, float, str)):
                                            analytics[k] = v
                                        elif isinstance(v, dict):
                                            analytics.update(v)
                                except Exception:
                                    pass

                            page.on("response", on_analytics)

                            # Navigate analytics tabs to trigger API calls
                            for tab_url in (
                                "https://www.tiktok.com/tiktokstudio/analytics/overview",
                                "https://www.tiktok.com/creator#/profile-manage?from=studio",
                            ):
                                try:
                                    await page.goto(tab_url, wait_until="domcontentloaded", timeout=15000)
                                    await asyncio.sleep(3)
                                except Exception:
                                    pass

                            result["analytics"] = analytics
                        except Exception as ae:
                            result["analytics"] = {}
                    else:
                        result["status"] = "timeout"
                finally:
                    await browser.close()
        except Exception as e:
            result["status"] = "error"; result["error"] = str(e)
        finally:
            done_event.set()

    threading.Thread(target=lambda: asyncio.run(_do_login()), daemon=True).start()

    def generate():
        yield "data: " + json.dumps({"type":"status","text":"Opening TikTok login window…"}) + "\n\n"
        start_t = time.time()
        while not done_event.is_set() and time.time() - start_t < 190:
            time.sleep(3)
            elapsed = int(time.time() - start_t)
            if not done_event.is_set():
                yield "data: " + json.dumps({
                    "type":"status",
                    "text":f"Sign in to TikTok in the window that just opened… ({elapsed}s)"
                }) + "\n\n"
        done_event.wait(timeout=5)
        if result.get("status") == "ok":
            from utils.config import load_config, save_config
            cfg = load_config()
            cfg["tiktok_connected"] = True
            cfg["tiktok_username"]  = result["username"]
            cfg.setdefault("my_username", result["username"])
            save_config(cfg)
            yield "data: " + json.dumps({
                "type":      "connected",
                "username":  result["username"],
                "nickname":  result.get("nickname",""),
                "followers": result.get("followers",0),
                "analytics": result.get("analytics",{}),
            }) + "\n\n"
        else:
            yield "data: " + json.dumps({
                "type":"error",
                "text": result.get("error","Login timed out — please try again.")
            }) + "\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@app.route("/api/my-stats", methods=["GET"])
def api_my_stats():
    """Fetch private stats using stored OAuth tokens."""
    platform = request.args.get("platform","tiktok")

    if platform == "tiktok":
        import urllib.request
        from utils.config import load_config
        cfg          = load_config()
        access_token = cfg.get("tiktok_access_token","").strip()
        if not access_token:
            return jsonify({"error":"Not connected to TikTok. Sign in via My Account."}), 401

        try:
            # ── Fetch video list ─────────────────────────────────────────────
            fields = "id,title,cover_image_url,share_url,video_description,duration,height,width,title,embed_html,embed_link,like_count,comment_count,share_count,view_count,create_time"
            vids_req = urllib.request.Request(
                "https://open.tiktokapis.com/v2/video/list/?fields=" + fields,
                data=json.dumps({"max_count":20}).encode(),
                headers={"Authorization":f"Bearer {access_token}","Content-Type":"application/json"}
            )
            vids_req.get_method = lambda: "POST"
            with urllib.request.urlopen(vids_req, timeout=15) as r:
                vids_data = json.loads(r.read().decode())

            videos_raw = vids_data.get("data",{}).get("videos",[]) or []

            # ── Fetch user info ──────────────────────────────────────────────
            ui_req = urllib.request.Request(
                "https://open.tiktokapis.com/v2/user/info/?fields=open_id,display_name,follower_count,following_count,likes_count,video_count,username",
                headers={"Authorization":f"Bearer {access_token}"}
            )
            with urllib.request.urlopen(ui_req, timeout=10) as r:
                ui_data = json.loads(r.read().decode())
            user = ui_data.get("data",{}).get("user",{})

            # Build analysis object matching rTikTokStats expectations
            from collections import Counter, defaultdict
            from datetime import datetime, timezone

            posts = [{
                "id":       v.get("id",""),
                "views":    v.get("view_count",0),
                "likes":    v.get("like_count",0),
                "comments": v.get("comment_count",0),
                "shares":   v.get("share_count",0),
                "desc":     v.get("video_description","")[:120],
                "ts":       v.get("create_time",0),
                "dt":       datetime.fromtimestamp(v.get("create_time",0),tz=timezone.utc) if v.get("create_time") else None,
                "url":      v.get("share_url",""),
                "date":     datetime.fromtimestamp(v.get("create_time",0)).strftime("%Y-%m-%d") if v.get("create_time") else "",
            } for v in videos_raw]

            n = len(posts)
            if n:
                avg_views  = sum(p["views"] for p in posts) // n
                avg_er_num = sum(
                    (p["likes"]+p["comments"]+p["shares"])/p["views"]*100
                    for p in posts if p["views"] > 0
                )
                avg_er = avg_er_num / max(sum(1 for p in posts if p["views"]>0), 1)
                top5   = sorted(posts, key=lambda p:p["views"], reverse=True)[:5]
            else:
                avg_views = avg_er = 0; top5 = []

            profile = {
                "followers":  user.get("follower_count",0),
                "following":  user.get("following_count",0),
                "likes":      user.get("likes_count",0),
                "videos":     user.get("video_count",0),
                "nickname":   user.get("display_name",""),
            }

            # Best slots from timestamps
            slot_views = defaultdict(list)
            for p in posts:
                if p.get("dt"):
                    slot_views[(p["dt"].weekday(), p["dt"].hour)].append(p["views"])
            best_slots = sorted(
                [[[d,h], sum(v)/len(v)] for (d,h),v in slot_views.items() if len(v)>=1],
                key=lambda x: x[1], reverse=True
            )[:5]

            analysis = {
                "n":          n,
                "avg_views":  avg_views,
                "avg_30":     avg_views,
                "avg_31_60":  0,
                "avg_er":     round(avg_er,2),
                "freq_week":  0,
                "trend":      0,
                "top5":       top5,
                "sounds":     [],
                "best_slots": best_slots,
                "posts":      posts,
            }

            return jsonify({"profile":profile,"analysis":analysis}, default=_json_default)

        except Exception as e:
            return jsonify({"error":str(e)}), 500

    if platform == "youtube":
        import urllib.request
        from utils.config import load_config
        cfg          = load_config()
        access_token = cfg.get("youtube_access_token","").strip()

        if not access_token:
            # Fall back to yt-dlp public scrape
            url = request.args.get("url","").strip()
            if not url: return jsonify({"error":"No token and no URL"}), 401
            try:
                from gui.runner import _find_bin
                import subprocess as _sp
                _no_win = {"creationflags":0x08000000} if os.name=="nt" else {}
                r = _sp.run([_find_bin("yt-dlp"),"--dump-json","--flat-playlist",
                             "--playlist-end","15","--no-warnings",url],
                            capture_output=True,text=True,timeout=60,**_no_win)
                videos=[]; channel_name=""; total_views=0
                for line in r.stdout.strip().splitlines():
                    try:
                        item=json.loads(line)
                        if item.get("_type")=="url" or item.get("id"):
                            v={"title":item.get("title",""),"views":item.get("view_count") or 0,
                               "likes":item.get("like_count",0) or 0,"upload_date":item.get("upload_date",""),
                               "url":item.get("url") or item.get("webpage_url","")}
                            videos.append(v); total_views+=v["views"]
                            if not channel_name: channel_name=item.get("channel") or item.get("uploader","")
                    except Exception: pass
                avg=total_views//max(len(videos),1)
                return jsonify({"channel_name":channel_name,"channel":{"subscribers":0,"total_views":total_views,"video_count":len(videos)},"videos":videos,"avg_views":avg})
            except Exception as e:
                return jsonify({"error":str(e)}), 500

        try:
            # ── YouTube Data API — channel stats ─────────────────────────────
            ch_req = urllib.request.Request(
                "https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true",
                headers={"Authorization":f"Bearer {access_token}"}
            )
            with urllib.request.urlopen(ch_req, timeout=10) as r:
                ch_data = json.loads(r.read().decode())
            items = ch_data.get("items",[])
            ch = items[0] if items else {}
            snippet = ch.get("snippet",{})
            stats   = ch.get("statistics",{})

            channel_name = snippet.get("title","YouTube Channel")
            channel_id   = ch.get("id","")

            # ── Videos list ──────────────────────────────────────────────────
            search_req = urllib.request.Request(
                f"https://www.googleapis.com/youtube/v3/search?part=snippet&forMine=true&type=video&maxResults=20&order=date",
                headers={"Authorization":f"Bearer {access_token}"}
            )
            with urllib.request.urlopen(search_req, timeout=10) as r:
                search_data = json.loads(r.read().decode())

            vid_ids = [i["id"]["videoId"] for i in search_data.get("items",[]) if i.get("id",{}).get("videoId")]

            videos = []
            if vid_ids:
                stats_req = urllib.request.Request(
                    "https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id=" + ",".join(vid_ids),
                    headers={"Authorization":f"Bearer {access_token}"}
                )
                with urllib.request.urlopen(stats_req, timeout=10) as r:
                    vids_data = json.loads(r.read().decode())
                for v in vids_data.get("items",[]):
                    vs = v.get("statistics",{})
                    sn = v.get("snippet",{})
                    videos.append({
                        "title":       sn.get("title",""),
                        "views":       int(vs.get("viewCount",0) or 0),
                        "likes":       int(vs.get("likeCount",0) or 0),
                        "comments":    int(vs.get("commentCount",0) or 0),
                        "upload_date": sn.get("publishedAt","")[:10],
                        "url":         f"https://www.youtube.com/watch?v={v.get('id','')}",
                        "thumbnail":   (sn.get("thumbnails",{}).get("medium",{}) or {}).get("url",""),
                    })

            total_views = int(stats.get("viewCount",0) or 0)
            avg_views   = total_views // max(len(videos),1) if videos else 0

            # ── Analytics API — 28-day metrics ───────────────────────────────
            analytics = {}
            try:
                from datetime import date, timedelta
                end_date   = date.today().isoformat()
                start_date = (date.today() - timedelta(days=28)).isoformat()
                ana_url = (
                    "https://youtubeanalytics.googleapis.com/v2/reports"
                    f"?ids=channel%3D%3DMINE&startDate={start_date}&endDate={end_date}"
                    "&metrics=views,estimatedMinutesWatched,averageViewDuration,likes,subscribersGained,subscribersLost"
                    "&dimensions=day&sort=day"
                )
                ana_req = urllib.request.Request(ana_url, headers={"Authorization":f"Bearer {access_token}"})
                with urllib.request.urlopen(ana_req, timeout=10) as r:
                    ana_data = json.loads(r.read().decode())
                rows = ana_data.get("rows",[])
                if rows:
                    analytics["views_28d"]    = sum(r[1] for r in rows)
                    analytics["watch_time_28d"]= sum(r[2] for r in rows)
                    analytics["avg_view_dur"]  = int(sum(r[3] for r in rows)/len(rows))
                    analytics["subs_gained"]   = sum(r[5] for r in rows)
                    analytics["subs_lost"]     = sum(r[6] for r in rows)
            except Exception:
                pass

            return jsonify({
                "channel_name": channel_name,
                "channel": {
                    "subscribers":  int(stats.get("subscriberCount",0) or 0),
                    "total_views":  total_views,
                    "video_count":  int(stats.get("videoCount",0) or 0),
                },
                "videos":    videos,
                "avg_views": avg_views,
                "analytics": analytics,
            })

        except Exception as e:
            return jsonify({"error":str(e)}), 500

    return jsonify({"error":"unknown platform"}), 400

@app.route("/api/my-following", methods=["GET"])
def api_my_following():
    """
    Return following list via TikTok Content API (no Playwright).
    Falls back to yt-dlp if no token.
    """
    import urllib.request, urllib.parse, subprocess, time
    from utils.config import load_config
    from gui.runner import _find_bin

    handle = request.args.get("handle","").strip().lstrip("@")
    q      = request.args.get("q","").lower().strip()
    if not handle:
        return jsonify({"users":[], "error":"not connected"})

    cfg   = load_config()
    token = cfg.get("tiktok_access_token","").strip()

    # Module-level cache {handle: (ts, users)}
    cache = getattr(api_my_following, "_cache", {})
    api_my_following._cache = cache
    cached_at, cached_users = cache.get(handle, (0, []))
    if time.time() - cached_at < 600 and cached_users:
        users = cached_users
    else:
        users = []

        if token:
            # TikTok Content API: get following list
            # Note: requires user.following.list scope (may need re-auth if not granted)
            try:
                cursor = 0
                while len(users) < 200:
                    params = "fields=display_name,follower_count,username"
                    body   = json.dumps({"max_count": 50, "cursor": cursor}).encode()
                    req    = urllib.request.Request(
                        f"https://open.tiktokapis.com/v2/user/following/list/?{params}",
                        data=body,
                        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=12) as r:
                        data  = json.loads(r.read().decode())
                    follows = data.get("data",{}).get("following") or []
                    for u in follows:
                        uid = u.get("username") or u.get("display_name","")
                        if uid:
                            users.append({"handle": uid, "name": u.get("display_name", uid)})
                    has_more = data.get("data",{}).get("has_more", False)
                    cursor   = data.get("data",{}).get("cursor", 0)
                    if not has_more or not follows:
                        break
            except Exception as e:
                # Token might not have following scope — fall through to yt-dlp
                pass

        if not users:
            # yt-dlp fallback: scrape following page (no headless browser needed,
            # yt-dlp uses its own HTTP client)
            try:
                _no_win = {"creationflags": 0x08000000} if os.name == "nt" else {}
                r = subprocess.run(
                    [_find_bin("yt-dlp"),
                     f"https://www.tiktok.com/@{handle}/following",
                     "--dump-json", "--flat-playlist", "--playlist-end", "60",
                     "--no-warnings", "--quiet"],
                    capture_output=True, text=True, timeout=30,
                    encoding="utf-8", errors="replace", **_no_win
                )
                seen = set()
                for line in r.stdout.strip().splitlines():
                    try:
                        item = json.loads(line)
                        uid  = item.get("channel") or item.get("uploader") or ""
                        if uid and uid.lower() not in seen:
                            seen.add(uid.lower())
                            users.append({"handle": uid, "name": uid})
                    except Exception:
                        pass
            except Exception:
                pass

        cache[handle] = (time.time(), users)

    if q:
        users = [u for u in users if q in u["handle"].lower() or q in u["name"].lower()]
    return jsonify({"users": users[:60]})


@app.route("/api/footage-search", methods=["GET"])
def api_footage_search():
    """Search YouTube via yt-dlp — works without any API key."""
    import subprocess
    q    = request.args.get("q","").strip()
    mode = request.args.get("mode","general")
    if not q:
        return jsonify({"results":[],"source":"YouTube"})

    if mode == "cars":
        search_query = f"ytsearch12:{q} cinematic footage 4K"
    else:
        search_query = f"ytsearch12:{q} stock footage free HD"

    try:
        from gui.runner import _find_bin
        _no_win = {"creationflags": 0x08000000} if os.name == "nt" else {}
        r = subprocess.run(
            [_find_bin("yt-dlp"), search_query,
             "--dump-json", "--flat-playlist",
             "--no-playlist", "--no-warnings", "--quiet"],
            capture_output=True, text=True, timeout=25,
            encoding="utf-8", errors="replace", **_no_win
        )
        results = []
        for line in r.stdout.strip().splitlines():
            try:
                item = json.loads(line)
                vid_id = item.get("id","")
                # best thumbnail
                thumbs = item.get("thumbnails") or []
                thumb  = next(
                    (t["url"] for t in reversed(thumbs) if t.get("url")),
                    item.get("thumbnail","")
                )
                if not thumb and vid_id:
                    thumb = f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"
                results.append({
                    "id":       vid_id,
                    "title":    item.get("title",""),
                    "url":      item.get("url") or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else ""),
                    "thumbnail": thumb,
                    "duration": item.get("duration") or 0,
                    "views":    item.get("view_count") or 0,
                    "channel":  item.get("channel") or item.get("uploader",""),
                    "upload_date": item.get("upload_date",""),
                })
            except Exception:
                pass
        return jsonify({"results": results, "source": "YouTube"})
    except subprocess.TimeoutExpired:
        return jsonify({"results":[], "error":"Search timed out — try again"})
    except Exception as e:
        return jsonify({"results":[], "error": str(e)})


@app.route("/api/connect-youtube-oauth", methods=["POST"])
def api_connect_youtube_oauth():
    """
    Start Google OAuth flow for YouTube Data API.
    Requires google_client_id + google_client_secret in config.json.
    Opens browser → user approves → callback at localhost:8889 → tokens stored.
    """
    import threading, time, webbrowser, urllib.parse, http.server, urllib.request
    from utils.config import load_config, save_config

    cfg      = load_config()
    client_id     = cfg.get("google_client_id","").strip()
    client_secret = cfg.get("google_client_secret","").strip()

    result     = {}
    done_event = threading.Event()

    REDIRECT_URI = "http://localhost:8889/oauth-callback"
    SCOPES = " ".join([
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/yt-analytics.readonly",
        "https://www.googleapis.com/auth/userinfo.profile",
    ])

    def start_callback_server():
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_GET(self):
                qs = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(qs)
                code = (params.get("code",[""])[0])
                self.send_response(200)
                self.send_header("Content-type","text/html")
                self.end_headers()
                self.wfile.write(b"<html><body style='background:#080b14;color:#dde4f5;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0'><div style='text-align:center'><div style='font-size:3rem;margin-bottom:16px'>&#10003;</div><div style='font-size:1.1rem;font-weight:600'>Connected! You can close this window.</div></div></body></html>")
                if code:
                    result["code"] = code
                    done_event.set()
                    # shutdown server in thread
                    threading.Thread(target=self.server.shutdown,daemon=True).start()
        try:
            srv = http.server.HTTPServer(("localhost",8889), Handler)
            srv.serve_forever()
        except Exception:
            done_event.set()

    threading.Thread(target=start_callback_server, daemon=True).start()

    def generate():
        if not client_id or not client_secret:
            yield "data: " + json.dumps({"type":"error","text":"Add google_client_id and google_client_secret to Settings first. See docs."}) + "\n\n"
            return

        auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            + urllib.parse.urlencode({
                "client_id":     client_id,
                "redirect_uri":  REDIRECT_URI,
                "response_type": "code",
                "scope":         SCOPES,
                "access_type":   "offline",
                "prompt":        "consent",
            })
        )
        yield "data: " + json.dumps({"type":"status","text":"Opening Google sign-in window…"}) + "\n\n"
        time.sleep(0.3)
        webbrowser.open(auth_url)
        yield "data: " + json.dumps({"type":"status","text":"Waiting for Google authorization…"}) + "\n\n"

        done_event.wait(timeout=180)

        if not result.get("code"):
            yield "data: " + json.dumps({"type":"error","text":"Authorization timed out or was cancelled."}) + "\n\n"
            return

        # Exchange code for tokens
        try:
            token_data = urllib.parse.urlencode({
                "code":          result["code"],
                "client_id":     client_id,
                "client_secret": client_secret,
                "redirect_uri":  REDIRECT_URI,
                "grant_type":    "authorization_code",
            }).encode()
            req = urllib.request.Request(
                "https://oauth2.googleapis.com/token",
                data=token_data,
                headers={"Content-Type":"application/x-www-form-urlencoded"}
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                tokens = json.loads(r.read().decode())

            access_token  = tokens.get("access_token","")
            refresh_token = tokens.get("refresh_token","")

            # Get channel info
            ch_req = urllib.request.Request(
                "https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            with urllib.request.urlopen(ch_req, timeout=10) as r:
                ch_data = json.loads(r.read().decode())

            items = ch_data.get("items",[])
            ch = items[0] if items else {}
            snippet = ch.get("snippet",{})
            channel_name = snippet.get("title","YouTube Channel")
            channel_url  = f"https://www.youtube.com/channel/{ch.get('id','')}"

            # Save tokens
            cfg2 = load_config()
            cfg2["youtube_access_token"]  = access_token
            cfg2["youtube_refresh_token"] = refresh_token
            cfg2["youtube_channel_id"]    = ch.get("id","")
            save_config(cfg2)

            yield "data: " + json.dumps({
                "type":"connected",
                "channel_name": channel_name,
                "channel_url":  channel_url,
                "access_token": access_token,
            }) + "\n\n"

        except Exception as e:
            yield "data: " + json.dumps({"type":"error","text":str(e)}) + "\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})


@app.route("/api/artist-search", methods=["GET"])
def api_artist_search():
    """
    Search for artists.
    platform=yt  → YouTube Music via yt-dlp ytmsearch (fast, reliable)
    platform=sp  → Spotify Web API (requires spotify_client_id/secret in config)
    """
    import subprocess, urllib.request, urllib.parse, base64
    q        = request.args.get("q","").strip()
    platform = request.args.get("platform","yt").strip()
    if not q:
        return jsonify({"artists":[]})

    from gui.runner import _find_bin
    _no_win = {"creationflags":0x08000000} if os.name=="nt" else {}
    results = []

    if platform == "sp":
        # ── Spotify Web API ────────────────────────────────────────────────
        from utils.config import load_config
        cfg    = load_config()
        cid    = cfg.get("spotify_client_id","").strip()
        sec    = cfg.get("spotify_client_secret","").strip()

        if not cid or not sec:
            return jsonify({"artists":[], "error":"no_credentials",
                "message":"Add Spotify credentials in Settings → Spotify API."})

        # Client-credentials token (read-only search, no user login needed)
        try:
            creds = base64.b64encode(f"{cid}:{sec}".encode()).decode()
            tok_req = urllib.request.Request(
                "https://accounts.spotify.com/api/token",
                data=b"grant_type=client_credentials",
                headers={"Authorization":f"Basic {creds}",
                         "Content-Type":"application/x-www-form-urlencoded"},
                method="POST",
            )
            with urllib.request.urlopen(tok_req, timeout=10) as r:
                tok = json.loads(r.read().decode())
            token = tok.get("access_token","")
        except Exception as e:
            return jsonify({"artists":[], "error":str(e)})

        try:
            params = urllib.parse.urlencode({"q":q,"type":"artist","limit":"8"})
            search_req = urllib.request.Request(
                f"https://api.spotify.com/v1/search?{params}",
                headers={"Authorization":f"Bearer {token}"},
            )
            with urllib.request.urlopen(search_req, timeout=10) as r:
                data = json.loads(r.read().decode())

            for a in data.get("artists",{}).get("items",[]):
                imgs = a.get("images",[])
                img  = imgs[0]["url"] if imgs else ""
                results.append({
                    "id":                  a["id"],
                    "name":                a.get("name",""),
                    "platform":            "spotify",
                    "image":               img,
                    "genres":              ", ".join(a.get("genres",[])[:2]),
                    "followers":           a.get("followers",{}).get("total",0),
                    "latest_release_id":   "",
                    "latest_release_title":"",
                    "url":                 a.get("external_urls",{}).get("spotify",""),
                })
        except Exception as e:
            return jsonify({"artists":[], "error":str(e)})

    else:
        # ── YouTube Music via yt-dlp ytmsearch ────────────────────────────
        try:
            r = subprocess.run(
                [_find_bin("yt-dlp"),
                 f"ytmsearch10:{q}",
                 "--dump-json","--flat-playlist","--no-warnings","--quiet"],
                capture_output=True, text=True, timeout=20,
                encoding="utf-8", errors="replace", **_no_win)
            seen = set()
            for line in r.stdout.strip().splitlines():
                try:
                    item = json.loads(line)
                    channel = item.get("channel") or item.get("uploader") or ""
                    if not channel or channel.lower() in seen:
                        continue
                    # Only keep if channel name looks like an artist (not "Official Audio" etc.)
                    if any(w in channel.lower() for w in ["official","vevo","records","music"]) and q.lower() not in channel.lower():
                        continue
                    seen.add(channel.lower())
                    ch_url = item.get("channel_url") or item.get("uploader_url") or ""
                    thumbs = item.get("thumbnails") or []
                    img    = next((t["url"] for t in reversed(thumbs) if t.get("url")),
                                  item.get("thumbnail",""))
                    results.append({
                        "id":                  ch_url or channel,
                        "name":                channel,
                        "platform":            "youtube",
                        "image":               img,
                        "genres":              "",
                        "followers":           0,
                        "latest_release_id":   str(item.get("id") or ""),
                        "latest_release_title": item.get("title",""),
                        "url":                 ch_url,
                    })
                except Exception:
                    pass
        except Exception as e:
            return jsonify({"artists":[], "error":str(e)})

    return jsonify({"artists": results[:10]})


@app.route("/api/artist-tracks", methods=["GET"])
def api_artist_tracks():
    """Get tracks for a YouTube channel or Spotify artist via yt-dlp."""
    import subprocess
    artist_id = request.args.get("id","").strip()
    platform  = request.args.get("platform","youtube").strip()
    name      = request.args.get("name","").strip()
    from gui.runner import _find_bin
    _no_win = {"creationflags":0x08000000} if os.name=="nt" else {}

    if platform == "youtube" and artist_id.startswith("http"):
        # Scrape channel videos
        try:
            r = subprocess.run(
                [_find_bin("yt-dlp"), artist_id,
                 "--dump-json","--flat-playlist","--playlist-end","30",
                 "--no-warnings","--quiet"],
                capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace", **_no_win)
            tracks = []
            for line in r.stdout.strip().splitlines():
                try:
                    item = json.loads(line)
                    if item.get("_type")=="url" or item.get("id"):
                        dur_s = item.get("duration") or 0
                        dur_str = f"{int(dur_s)//60}:{str(int(dur_s)%60).zfill(2)}" if dur_s else ""
                        thumbs = item.get("thumbnails") or []
                        thumb  = next((t["url"] for t in reversed(thumbs) if t.get("url")), item.get("thumbnail",""))
                        tracks.append({
                            "id":      item.get("id",""),
                            "title":   item.get("title",""),
                            "album":   item.get("album") or item.get("channel",""),
                            "duration":dur_str,
                            "image":   thumb,
                            "url":     item.get("url") or (f"https://youtube.com/watch?v={item.get('id','')}"),
                        })
                except Exception: pass
            return jsonify({"tracks": tracks, "image":"", "genres":"", "followers":0})
        except Exception as e:
            return jsonify({"tracks":[], "error":str(e)})

    # Spotify / generic: search for artist top songs via yt-dlp ytmsearch
    try:
        search_q = f"ytmsearch20:{name} songs"
        r = subprocess.run(
            [_find_bin("yt-dlp"), search_q,
             "--dump-json","--flat-playlist","--no-warnings","--quiet"],
            capture_output=True, text=True, timeout=25,
            encoding="utf-8", errors="replace", **_no_win)
        tracks = []
        for line in r.stdout.strip().splitlines():
            try:
                item = json.loads(line)
                a = item.get("artist") or item.get("uploader") or item.get("channel") or ""
                if name and a and name.lower() not in a.lower() and a.lower() not in name.lower():
                    continue  # filter to this artist only
                dur_ms = (item.get("duration") or 0) * 1000
                thumbs = item.get("thumbnails") or []
                thumb  = next((t["url"] for t in reversed(thumbs) if t.get("url")), item.get("thumbnail",""))
                tracks.append({
                    "id":          item.get("id",""),
                    "title":       item.get("title",""),
                    "album":       item.get("album",""),
                    "duration_ms": int(dur_ms),
                    "image":       thumb,
                    "url":         item.get("webpage_url") or item.get("url",""),
                })
            except Exception: pass
        return jsonify({"tracks": tracks[:30], "image":"", "genres":"", "followers":0})
    except Exception as e:
        return jsonify({"tracks":[], "error":str(e)})


@app.route("/api/artist-latest", methods=["GET"])
def api_artist_latest():
    """Get the latest release for a watched artist."""
    import subprocess
    artist_id = request.args.get("id","").strip()
    platform  = request.args.get("platform","youtube").strip()
    name      = request.args.get("name","").strip()
    from gui.runner import _find_bin
    _no_win = {"creationflags":0x08000000} if os.name=="nt" else {}

    try:
        if platform=="youtube" and artist_id.startswith("http"):
            r = subprocess.run(
                [_find_bin("yt-dlp"), artist_id, "--dump-json","--flat-playlist",
                 "--playlist-end","1","--no-warnings","--quiet"],
                capture_output=True, text=True, timeout=20,
                encoding="utf-8", errors="replace", **_no_win)
        else:
            r = subprocess.run(
                [_find_bin("yt-dlp"), f"ytmsearch1:{name} new song",
                 "--dump-json","--flat-playlist","--no-warnings","--quiet"],
                capture_output=True, text=True, timeout=20,
                encoding="utf-8", errors="replace", **_no_win)
        for line in r.stdout.strip().splitlines():
            try:
                item = json.loads(line)
                vid_id = str(item.get("id") or "")
                if vid_id:
                    return jsonify({
                        "latest_id":    vid_id,
                        "latest_title": item.get("title",""),
                        "latest_date":  str(item.get("upload_date","") or ""),
                        "latest_url":   item.get("webpage_url") or item.get("url") or f"https://youtube.com/watch?v={vid_id}",
                    })
            except Exception: pass
        return jsonify({"latest_id":"","latest_title":"","latest_date":"","latest_url":""})
    except Exception as e:
        return jsonify({"error":str(e)})


# ── AUTH ENDPOINTS (proxy to Supabase) ────────────────────────────────────────
def _get_auth_cfg():
    from utils.config import load_config
    cfg = load_config()
    return cfg.get("auth_url","").rstrip("/"), cfg.get("auth_key","")

def _supabase(path, method="POST", body=None, token=None):
    """Forward a request to Supabase and return (status, json_dict)."""
    import urllib.request, urllib.error
    url, key = _get_auth_cfg()
    if not url or not key:
        return 503, {"error": "No auth server configured. Run setup_server.py first."}
    req = urllib.request.Request(
        url + path,
        data=json.dumps(body).encode() if body else None,
        method=method
    )
    req.add_header("Content-Type",  "application/json")
    req.add_header("apikey",         key)
    req.add_header("Authorization", f"Bearer {token or key}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:   body = json.loads(e.read().decode())
        except Exception: body = {"error": str(e)}
        return e.code, body
    except Exception as e:
        return 0, {"error": str(e)}


@app.route("/api/auth/register", methods=["POST"])
def api_auth_register():
    """Create a new account via Supabase Auth."""
    data = request.json or {}
    status, resp = _supabase(
        "/auth/v1/signup", "POST",
        body={"email": data.get("email",""), "password": data.get("password","")}
    )
    return jsonify(resp), status


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    """Log in with email+password via Supabase Auth."""
    data = request.json or {}
    status, resp = _supabase(
        "/auth/v1/token?grant_type=password", "POST",
        body={"email": data.get("email",""), "password": data.get("password","")}
    )
    if status == 200:
        # Return a clean response the frontend expects
        return jsonify({
            "token":   resp.get("access_token",""),
            "refresh": resp.get("refresh_token",""),
            "email":   resp.get("user",{}).get("email",""),
            "user_id": resp.get("user",{}).get("id",""),
        })
    return jsonify(resp), status


@app.route("/api/auth/refresh", methods=["POST"])
def api_auth_refresh():
    """Refresh an expired access token."""
    data = request.json or {}
    status, resp = _supabase(
        "/auth/v1/token?grant_type=refresh_token", "POST",
        body={"refresh_token": data.get("refresh","")}
    )
    if status == 200:
        return jsonify({
            "token":   resp.get("access_token",""),
            "refresh": resp.get("refresh_token",""),
        })
    return jsonify(resp), status


@app.route("/api/userdata/get", methods=["POST"])
def api_userdata_get():
    """Fetch a data key for the logged-in user from Supabase."""
    data  = request.json or {}
    token = data.get("token","")
    key   = data.get("key","")
    if not token or not key:
        return jsonify({"error": "Missing token or key"}), 400
    _, key_cfg = _get_auth_cfg()
    url_base, _ = _get_auth_cfg()
    import urllib.request
    req = urllib.request.Request(
        f"{url_base}/rest/v1/user_data?key=eq.{urllib.parse.quote(key)}&select=value&limit=1",
        method="GET"
    )
    req.add_header("apikey",        key_cfg)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept",        "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read().decode())
            return jsonify({"value": rows[0]["value"] if rows else None})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/userdata/set", methods=["POST"])
def api_userdata_set():
    """Upsert a data key for the logged-in user in Supabase."""
    import urllib.request
    data  = request.json or {}
    token = data.get("token","")
    key   = data.get("key","")
    value = data.get("value")
    if not token or not key:
        return jsonify({"error": "Missing token or key"}), 400
    url_base, key_cfg = _get_auth_cfg()

    # We need the user_id from the JWT to do the upsert
    # Decode it (no signature verification needed — Supabase validates on its side)
    import base64
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        user_id = json.loads(base64.b64decode(payload_b64)).get("sub","")
    except Exception:
        return jsonify({"error": "Invalid token"}), 401

    body = json.dumps({
        "user_id":    user_id,
        "key":        key,
        "value":      value,
        "updated_at": "now()",
    }).encode()

    req = urllib.request.Request(
        f"{url_base}/rest/v1/user_data",
        data=body, method="POST"
    )
    req.add_header("Content-Type",  "application/json")
    req.add_header("apikey",         key_cfg)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Prefer",        "resolution=merge-duplicates")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return jsonify({"ok": True})
    except urllib.error.HTTPError as e:
        return jsonify({"error": str(e)}), e.code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/auth/role", methods=["POST"])
def api_auth_role():
    """Fetch the current user's role from Supabase."""
    data  = request.json or {}
    token = data.get("token","")
    if not token:
        return jsonify({"role":"user"})

    url_base, key_cfg = _get_auth_cfg()
    if not url_base:
        return jsonify({"role":"user"})

    # Decode user_id from JWT (no signature check needed — Supabase validates)
    import base64
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        user_id = json.loads(base64.b64decode(payload_b64)).get("sub","")
    except Exception:
        return jsonify({"role":"user"})

    import urllib.request as _ur
    req = _ur.Request(
        f"{url_base}/rest/v1/roles?user_id=eq.{user_id}&select=role&limit=1",
        method="GET"
    )
    req.add_header("apikey",        key_cfg)
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with _ur.urlopen(req, timeout=8) as r:
            rows = json.loads(r.read().decode())
            role = rows[0]["role"] if rows else "user"
            return jsonify({"role": role})
    except Exception:
        return jsonify({"role": "user"})


@app.route("/auth/callback")
def auth_callback():
    """Handle Google OAuth redirect from Supabase."""
    return """<!DOCTYPE html>
<html><head><title>EditorSuite — Signing in…</title>
<style>body{background:#080b14;color:#dde4f5;font-family:monospace;
display:flex;align-items:center;justify-content:center;height:100vh;margin:0;font-size:.95rem}
div{text-align:center;padding:40px}</style></head><body>
<div id="m">Completing sign in…</div>
<script>
const p=new URLSearchParams(window.location.hash.slice(1));
const t=p.get("access_token"),r=p.get("refresh_token");
if(t){
  localStorage.setItem("es_token",t);
  localStorage.setItem("es_refresh",r||"");
  if(window.opener){window.opener.postMessage({type:"oauth_token",token:t,refresh:r||""},"*");document.getElementById("m").textContent="✓ Signed in! Closing…";setTimeout(()=>window.close(),700);}
  else{document.getElementById("m").textContent="✓ Signed in! Returning to app…";setTimeout(()=>{window.location.href="/";},700);}
}else{document.getElementById("m").textContent="Sign-in failed — no token. Close this and try again.";}
</script></body></html>"""


@app.route("/api/extract-thumb", methods=["POST"])
def api_extract_thumb():
    """Use ffmpeg to extract a thumbnail from a local video file."""
    data = request.json or {}
    path = data.get("path","").strip()
    if not path or not os.path.isfile(path):
        return jsonify({"thumb":""})
    # Save thumb next to video file
    thumb_path = os.path.splitext(path)[0] + "_thumb.jpg"
    if not os.path.exists(thumb_path):
        import subprocess as _sp
        try:
            _sp.run([
                _find_bin("ffmpeg"), "-y", "-i", path,
                "-ss","00:00:01", "-vframes","1",
                "-vf","scale=320:-1",
                thumb_path
            ], capture_output=True, timeout=15)
        except Exception:
            return jsonify({"thumb":""})
    if os.path.exists(thumb_path):
        return jsonify({"thumb": thumb_path})
    return jsonify({"thumb":""})


@app.route("/api/serve-thumb")
def api_serve_thumb():
    """Serve a local thumbnail image file."""
    from flask import send_file, abort
    path = request.args.get("path","").strip()
    if not path: abort(400)
    path = os.path.abspath(path)
    home = os.path.expanduser("~")
    if not path.startswith(home): abort(403)
    if not os.path.isfile(path): abort(404)
    return send_file(path, mimetype="image/jpeg")


@app.route("/api/serve-video")
def api_serve_video():
    """Stream a local video file to the browser for in-app playback."""
    import mimetypes
    from flask import send_file, abort
    path = request.args.get("path", "").strip()
    if not path:
        abort(400)
    path = os.path.abspath(path)
    # Security: must be under the user's home dir or Videos folder
    home = os.path.expanduser("~")
    if not path.startswith(home):
        abort(403)
    if not os.path.isfile(path):
        # path might be a folder — find first video file in it
        import glob
        for ext in ("*.mp4","*.mkv","*.mov","*.avi","*.webm"):
            found = glob.glob(os.path.join(path, "**", ext), recursive=True)
            if found:
                path = sorted(found)[0]
                break
        else:
            abort(404)
    mime, _ = mimetypes.guess_type(path)
    mime = mime or "video/mp4"
    return send_file(path, mimetype=mime, conditional=True)


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
        # Chrome first — never pick Edge (it has intrusive translate/sidebar)
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\opera.exe"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\launcher.exe"),  # Opera GX
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\opera.exe"),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\launcher.exe"),
        # Edge only as last resort
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"),
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
        os.path.join(lappdata, "Programs","Opera","launcher.exe"),
        os.path.join(lappdata, "Programs","Opera GX","launcher.exe"),
        os.path.join(pf,       "Opera","launcher.exe"),
        os.path.join(lappdata, "Chromium","Application","chrome.exe"),
        # Edge last — has intrusive translate bar and sidebar even with flags
        os.path.join(pf86,     "Microsoft","Edge","Application","msedge.exe"),
        os.path.join(pf,       "Microsoft","Edge","Application","msedge.exe"),
    ]
    for exe in candidates:
        if exe and os.path.isfile(exe):
            return exe
    return ""


def _strip_titlebar(pid: int):
    """Style window with dark rounded DWM frame and set custom icon."""
    try:
        import win32gui, win32con, win32process
    except ImportError:
        return

    import time, ctypes

    CHROMIUM_CLASSES = {"Chrome_WidgetWin_1", "OperaWindowClass", "BrowserWindowClass"}

    hwnd = None
    for _ in range(80):          # up to 16 s — page may be slow on first load
        time.sleep(0.2)
        found = []
        def _cb(h, _):
            if not win32gui.IsWindowVisible(h): return
            if win32gui.GetClassName(h) not in CHROMIUM_CLASSES: return
            try:
                _, wpid = win32process.GetWindowThreadProcessId(h)
                if wpid == pid:
                    found.append(h)
            except Exception:
                pass
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


def _show_ready_notification():
    """Show a Windows balloon tip via win32gui (no PowerShell needed)."""
    try:
        import win32gui, win32con
        import ctypes, struct, time

        # NIM_ADD = 0, NIM_MODIFY = 1, NIM_DELETE = 2, NIM_SETVERSION = 4
        # NIF_MESSAGE=1, NIF_ICON=2, NIF_TIP=4, NIF_INFO=0x10
        NIM_ADD      = 0
        NIM_MODIFY   = 1
        NIM_DELETE   = 2
        NIF_MESSAGE  = 0x01
        NIF_ICON     = 0x02
        NIF_TIP      = 0x04
        NIF_INFO     = 0x10
        NIIF_NOSOUND = 0x10

        # Create a hidden message-only window to receive tray callbacks
        wc = win32gui.WNDCLASS()
        wc.hInstance   = win32gui.GetModuleHandle(None)
        wc.lpszClassName = "ESNotify"
        wc.lpfnWndProc   = lambda h,m,w,l: win32gui.DefWindowProc(h,m,w,l)
        try:
            win32gui.RegisterClass(wc)
        except Exception:
            pass
        hwnd = win32gui.CreateWindow(
            "ESNotify", "", 0, 0, 0, 0, 0,
            win32con.HWND_MESSAGE, None, wc.hInstance, None
        )

        hicon = win32gui.LoadIcon(None, win32con.IDI_APPLICATION)

        # NOTIFYICONDATA structure
        # https://learn.microsoft.com/en-us/windows/win32/api/shellapi/ns-shellapi-notifyicondataw
        NID_FMT = "IIIIII256sIIII64s256sI"
        nid = struct.pack(
            NID_FMT,
            struct.calcsize(NID_FMT),  # cbSize
            hwnd,                       # hWnd
            1,                          # uID
            NIF_MESSAGE | NIF_ICON | NIF_TIP | NIF_INFO,  # uFlags
            0,                          # uCallbackMessage
            hicon,                      # hIcon
            "EditorSuite".encode("utf-16-le").ljust(512, b"\x00")[:512],  # szTip (256 wchars)
            5000,                       # uTimeout (ms)
            0,                          # dwState
            0,                          # dwStateMask
            NIIF_NOSOUND,              # dwInfoFlags
            "Ready! Outputs saved to Videos folder.".encode("utf-16-le").ljust(128, b"\x00")[:128],  # szInfo (64 wchars)
            "EditorSuite".encode("utf-16-le").ljust(512, b"\x00")[:512],  # szInfoTitle (256 wchars)
            0,                          # uVersion
        )
        ctypes.windll.shell32.Shell_NotifyIconW(NIM_ADD, ctypes.c_char_p(nid))
        time.sleep(6)
        ctypes.windll.shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.c_char_p(nid))
        try:
            win32gui.DestroyWindow(hwnd)
        except Exception:
            pass
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
            [exe,
             f"--app={url}",
             "--window-size=1300,840",
             "--window-position=60,30",
             "--disable-features=Translate,TranslateUI,AutoTranslate,"
             "msEdgeTranslate,EdgeTranslate,msEdgeSideBar,msEdgeShopping,"
             "msEdgeNTP,msEdgeAsyncHubLaunch",
             "--disable-translate",
             "--lang=en-US",
             "--accept-lang=en-US",
             "--no-first-run",
             "--no-default-browser-check",
             "--disable-sync",
             "--disable-extensions",      # kills Edge sidebar/translate extension
             "--disable-background-networking",
            ],
            creationflags=0x08000000
        )
        threading.Thread(target=_strip_titlebar, args=(proc.pid,), daemon=True).start()
        threading.Thread(target=_show_ready_notification, daemon=True).start()
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
