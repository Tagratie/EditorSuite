"""
gui/runner.py
All 21 EditorSuite tools fully wired — no CLI fallback.
"""
import os, sys, re, queue, threading, subprocess, asyncio, shutil
from pathlib import Path

ROOT = str(Path(__file__).parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.config import load_config
from utils.dirs   import _init_dirs
from ui.theme     import _apply_theme

load_config(); _apply_theme("default"); _init_dirs()
from utils import dirs as _dirs


def _strip(s): return re.sub(r'\033\[[0-9;]*m', '', str(s))


# ── Binary resolver — finds yt-dlp/ffmpeg inside frozen exe or on PATH ───────
def _find_bin(name: str) -> str:
    """
    Return the full path to a binary.
    Search order:
      1. PyInstaller _MEIPASS (frozen exe — binaries bundled here)
      2. Same folder as this script (dev — local copy)
      3. shutil.which (system PATH)
      4. Common Windows install locations
    Falls back to bare name so the OS error message stays meaningful.
    """
    candidates = []

    # 1. Frozen bundle
    mei = getattr(sys, "_MEIPASS", None)
    if mei:
        candidates += [
            os.path.join(mei, name + ".exe"),
            os.path.join(mei, name),
        ]

    # 2. Script directory (dev)
    here = os.path.dirname(os.path.abspath(__file__))
    candidates += [
        os.path.join(here, name + ".exe"),
        os.path.join(here, name),
    ]

    # 3. PATH
    found = shutil.which(name)
    if found:
        candidates.append(found)

    # 4. Common install locations (Windows)
    lapp = os.environ.get("LOCALAPPDATA", "")
    pf   = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    candidates += [
        os.path.join(lapp, "Programs", name, name + ".exe"),
        os.path.join(pf,   "yt-dlp",   name + ".exe"),
        os.path.join(pf,   "ffmpeg", "bin", name + ".exe"),
        os.path.join(lapp, "Microsoft", "WinGet", "Packages",
                     name + ".exe"),
    ]

    for c in candidates:
        if c and os.path.isfile(c):
            return c

    return name  # last resort — let subprocess raise a clear error


# ── Entry points ──────────────────────────────────────────────────────────────

def run_task(detected: dict, options: dict, q: queue.Queue):
    """Home paste-anything panel."""
    _run(detected.get("type",""), detected.get("value",""), options, q)

def run_named_tool(tool_id: str, options: dict, q: queue.Queue):
    """Sidebar tool buttons."""
    _run(tool_id, None, options, q)

def _run(kind, value, opts, q):
    _init_dirs()   # re-read config so folder settings always take effect
    log   = lambda m:   q.put({"type":"log",      "text":_strip(m)})
    prog  = lambda v,t: q.put({"type":"progress", "value":v,"total":t})
    res   = lambda d:   q.put({"type":"result",   "data":d})
    def done(m="", path=""): q.put({"type":"done", "text":str(m), "path":str(path)})
    error = lambda m:   q.put({"type":"error",    "text":str(m)})
    try:
        _dispatch(kind, value, opts, log, prog, res, done, error)
    except Exception as e:
        import traceback
        error(f"Error: {e}")
        log(traceback.format_exc())
    finally:
        q.put(None)


# ── Dispatcher ────────────────────────────────────────────────────────────────

def _dispatch(kind, value, opts, log, prog, res, done, error):
    # paste-anything shortcuts
    if kind == "hashtag":
        return _scraper(value or opts.get("hashtag",""), opts, log, prog, res, done, error)
    if kind in ("tiktok_video","youtube_video"):
        return _dl_video(value or opts.get("url",""), opts, log, done, error)
    if kind == "tiktok_profile":
        return _dl_profile(value or opts.get("url",""), opts, log, done, error)
    if kind == "youtube_playlist":
        return _dl_playlist(value or opts.get("url",""), opts, log, done, error)
    if kind in ("spotify_track","spotify_album","spotify_playlist"):
        return _spotify(value or opts.get("url",""), opts, log, prog, done, error)
    if kind == "soundcloud":
        return _soundcloud(value or opts.get("url",""), opts, log, done, error)

    # --- SCRAPERS ---
    if kind == "scraper":
        h = (opts.get("hashtag","") or "").lstrip("#").strip()
        return (error("Enter a hashtag.") if not h else
                _scraper(h, opts, log, prog, res, done, error))

    if kind == "crosshash":
        tags = [t.strip().lstrip("#") for t in opts.get("hashtags","").split(",") if t.strip()]
        return (error("Enter at least one hashtag.") if not tags else
                _cross_hashtag(tags, opts, log, prog, res, done, error))

    if kind == "sp_exp":
        h = (opts.get("hashtag","") or "").lstrip("#").strip()
        return (error("Enter a hashtag.") if not h else
                _export_spotify(h, opts, log, prog, done, error))

    # --- ANALYTICS ---
    if kind == "hanalyze":
        tags = [t.strip().lstrip("#") for t in opts.get("hashtags","").split(",") if t.strip()]
        return (error("Enter at least one hashtag.") if not tags else
                _hashtag_analyze(tags, opts, log, prog, res, done, error))

    if kind == "competitor":
        u1 = opts.get("user1","").lstrip("@").strip()
        u2 = opts.get("user2","").lstrip("@").strip()
        return (error("Enter both usernames.") if not u1 or not u2 else
                _competitor(u1, u2, opts, log, res, done, error))





    # --- DOWNLOADERS ---
    if kind == "dl_vid":
        url = opts.get("url","").strip()
        return (error("Enter a URL.") if not url else
                _dl_video(url, opts, log, done, error))

    if kind == "dl_prof":
        url = opts.get("url","").strip()
        if url.startswith("@"):
            url = f"https://www.tiktok.com/{url}"
        return (error("Enter a URL or @username.") if not url else
                (_dl_profile(re.sub(r"https?://[^/]+/@?","",url).rstrip("/"), opts, log, done, error)
                 if "tiktok.com/@" in url else _dl_playlist(url, opts, log, done, error)))

    if kind == "dl_spotify":
        url = opts.get("url","").strip()
        if not url: return error("Enter a URL.")
        if "soundcloud" in url: return _soundcloud(url, opts, log, done, error)
        opts.setdefault("audio_quality", opts.get("quality","320"))
        return _spotify(url, opts, log, prog, done, error)

    if kind == "dl_song":
        title  = opts.get("title","").strip()
        artist = opts.get("artist","").strip()
        if not title:
            return error("Enter a song title.")
        return _dl_song(title, artist, opts, log, prog, done, error)

    if kind == "dl_audio":
        inp = opts.get("input","").strip()
        return (error("Enter a file path or URL.") if not inp else
                _audio_extract(inp, opts, log, done, error))

    # --- STUDIO ---
    if kind == "compress":
        inp = opts.get("input","").strip()
        if not inp: return error("Enter a video file or folder path.")
        if os.path.isdir(inp):
            opts["folder"] = inp
            return _bulk_compress(inp, opts, log, prog, done, error)
        return _compress(inp, opts, log, done, error)


    if kind == "bg_rem":
        inp = opts.get("input","").strip()
        return (error("Enter a file or folder path.") if not inp else
                _bg_remove(inp, opts, log, prog, done, error))

    error(f"Unknown tool: {kind}")


# =============================================================================
# SCRAPERS
# =============================================================================

RECENT_DAYS = 30

def _scraper(hashtag, opts, log, prog, res, done, error):
    from tools.audio_scraper import scrape_sounds
    limit = int(opts.get("limit","300") or "300")
    log(f"Scraping #{hashtag} — targeting {limit} videos...")
    pcb = lambda seen, total: prog(seen, total)
    try:
        scanned, sounds = asyncio.run(scrape_sounds(
            hashtag, limit, progress_cb=pcb, recent_days=RECENT_DAYS))
    except Exception as e:
        return error(f"Scrape failed: {e}")

    kept    = sorted([v for v in sounds.values() if not v["reason"]],
                     key=lambda x: x["count"], reverse=True)
    by_views = sorted(kept, key=lambda x: x.get("avg_views") or x.get("views", 0), reverse=True)
    removed = [v for v in sounds.values() if v["reason"]]
    log(f"Scanned {scanned} videos · {len(kept)} sounds · {len(removed)} filtered")

    from utils.html_report import save_sounds_report
    os.makedirs(_dirs.DIR_SOUNDS, exist_ok=True)
    html_path = save_sounds_report(hashtag, scanned, kept, removed, _dirs.DIR_SOUNDS)

    res({"type":"sounds","hashtag":hashtag,"scanned":scanned,
         "kept":len(kept),"removed":len(removed),
         "top":kept[:15],"top_by_count":kept[:15],"top_by_views":by_views[:15],
         "html_path":html_path})
    done(f"{len(kept)} trending sounds found")


def _cross_hashtag(tags, opts, log, prog, res, done, error):
    from tools.cross_hashtag import _scrape_tag_sounds
    from playwright.async_api import async_playwright
    target = int(opts.get("limit","300") or "300")
    log(f"Scraping {len(tags)} hashtag(s), {target} videos each...")

    all_sounds = {}

    async def _run():
        from core.browser import new_browser
        async with async_playwright() as pw:
            browser, ctx = await new_browser(pw, mute=True)
            try:
                for i, tag in enumerate(tags, 1):
                    log(f"  [{i}/{len(tags)}] Scraping #{tag}...")
                    pcb = lambda seen, total, _i=i, _n=len(tags): prog(
                        int(((_i-1) + seen/max(total,1)) * 100), _n * 100)
                    sounds, _ = await _scrape_tag_sounds(ctx, tag, target, progress_cb=pcb)
                    for sid, s in sounds.items():
                        if sid in all_sounds:
                            all_sounds[sid]["count"] += s["count"]
                            all_sounds[sid]["tags"].add(tag)
                            if s.get("post_url") and not all_sounds[sid].get("post_url"):
                                all_sounds[sid]["post_url"] = s.get("post_url")
                        else:
                            all_sounds[sid] = {**s, "tags": {tag}}
            finally:
                await browser.close()

    try:
        asyncio.run(_run())
    except Exception as e:
        return error(f"Scrape failed: {e}")

    cross = sorted(
        [dict(s, tags=list(s["tags"])) for s in all_sounds.values()
         if len(s.get("tags", set())) > 1],
        key=lambda x: x["count"], reverse=True
    )[:20]
    log(f"Found {len(cross)} sounds trending across multiple hashtags")
    res({"type":"cross_sounds","tags":tags,"sounds":cross})
    done(f"{len(cross)} cross-hashtag sounds found")


def _export_spotify(hashtag, opts, log, prog, done, error):
    from tools.audio_scraper import scrape_sounds
    cfg = load_config()
    cid = cfg.get("spotify_client_id","")
    sec = cfg.get("spotify_client_secret","")
    if not cid or not sec:
        return error("Spotify credentials missing. Add spotify_client_id and spotify_client_secret to config.json.")
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
    except ImportError:
        return error("spotipy not installed. Run: pip install spotipy")

    limit = int(opts.get("limit","500") or "500")
    top_n = int(opts.get("top_n","20") or "20")
    log(f"Scraping #{hashtag}...")
    pcb = lambda seen, total: prog(seen, total)
    try:
        scanned, sounds = asyncio.run(scrape_sounds(hashtag, limit, progress_cb=pcb))
    except Exception as e:
        return error(f"Scrape failed: {e}")

    kept = sorted([v for v in sounds.values() if not v["reason"]],
                  key=lambda x: x["count"], reverse=True)[:top_n]
    log(f"Found {len(kept)} sounds — searching Spotify...")
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=cid, client_secret=sec,
            redirect_uri="http://localhost:8888/callback",
            scope="playlist-modify-public"))
        uid = sp.current_user()["id"]
        pl  = sp.user_playlist_create(uid, f"TikTok #{hashtag} Trending", public=True)
        uris = []
        for s in kept:
            r = sp.search(q=f"{s['title']} {s.get('author','')}", type="track", limit=1)
            items = r["tracks"]["items"]
            if items:
                uris.append(items[0]["uri"])
                log(f"  ✓ {s['title']}")
            else:
                log(f"  ✗ {s['title']} — not on Spotify")
        if uris:
            sp.playlist_add_items(pl["id"], uris)
        done(f"Playlist created with {len(uris)} tracks: {pl['external_urls']['spotify']}")
    except Exception as e:
        error(f"Spotify error: {e}")


# =============================================================================
# ANALYTICS
# =============================================================================

def _hashtag_analyze(tags, opts, log, prog, res, done, error):
    from tools.hashtag_analyzer import _analyze_hashtags
    log(f"Analysing {len(tags)} hashtag(s)...")
    try:
        results = asyncio.run(_analyze_hashtags(tags))
    except Exception as e:
        return error(f"Analysis failed: {e}")

    rows = sorted([
        {"tag":f"#{tag}",
         "posts":     d.get("post_count",0),
         "avg_views": d.get("avg_views",0),
         "avg_likes": d.get("avg_likes",0),
         "difficulty":d.get("difficulty","—")}
        for tag,d in results.items()
    ], key=lambda r: r["avg_views"], reverse=True)

    res({"type":"hashtag_analyze","rows":rows})
    done(f"Analysis complete for {len(rows)} hashtags")


def _competitor(u1, u2, opts, log, res, done, error):
    from tools.competitor import _scrape_profile, _analyze_posts
    from playwright.async_api import async_playwright
    log(f"Scraping @{u1} and @{u2}...")

    async def _run():
        from core.browser import new_browser
        async with async_playwright() as pw:
            browser, ctx = await new_browser(pw, mute=True)
            try:
                _, posts1 = await _scrape_profile(ctx, u1)
                _, posts2 = await _scrape_profile(ctx, u2)
            finally:
                await browser.close()
            return posts1, posts2

    try:
        posts1, posts2 = asyncio.run(_run())
    except Exception as e:
        return error(f"Scrape failed: {e}")

    s1 = _analyze_posts(posts1)
    s2 = _analyze_posts(posts2)
    log(f"@{u1}: {len(posts1)} posts  |  @{u2}: {len(posts2)} posts")
    res({"type":"competitor","user1":u1,"user2":u2,
         "stats1":s1,"stats2":s2,
         "posts1":posts1[:5],"posts2":posts2[:5]})
    done(f"Comparison complete: @{u1} vs @{u2}")


def _dl_video(url, opts, log, done, error):
    quality = str(opts.get("quality","1080")).replace("p","")
    out_dir = os.path.join(_dirs.DIR_DOWNLOADS, "single")
    os.makedirs(out_dir, exist_ok=True)
    is_yt = any(x in url for x in ("youtube.com","youtu.be"))
    log(f"Downloading {'YouTube' if is_yt else 'TikTok'} video...")
    if is_yt:
        # Prefer mp4 video + m4a (AAC) audio so the result plays everywhere.
        # If no m4a stream available, take best audio and remux/convert to aac.
        fmt = (
            f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={quality}]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={quality}]+bestaudio/best[ext=mp4]/best"
        )
        cmd = [_find_bin("yt-dlp"), url,
               "-o", os.path.join(out_dir, "%(uploader)s_%(title)s.%(ext)s"),
               "--format", fmt,
               "--merge-output-format", "mp4",
               "--audio-format", "aac",        # convert audio to AAC if not already
               "--postprocessor-args", "ffmpeg:-c:a aac -b:a 192k",
               "--add-metadata", "--progress"]
    else:
        cmd = [_find_bin("yt-dlp"), url, "-o", os.path.join(out_dir,"%(uploader)s_%(title)s.%(ext)s"),
               "--merge-output-format","mp4","--no-warnings","--progress"]
    _stream_cmd(cmd, log)
    # Find the actual downloaded file to return its path
    import glob as _glob
    _files = []
    for _ext in ("*.mp4","*.mkv","*.mov","*.webm","*.avi"):
        _files += _glob.glob(os.path.join(out_dir, _ext))
    _file_path = sorted(_files, key=os.path.getmtime)[-1] if _files else out_dir
    done(f"Saved to: {out_dir}", path=_file_path)


def _dl_profile(username, opts, log, done, error):
    url     = f"https://www.tiktok.com/@{username.lstrip('@')}"
    out_dir = os.path.join(_dirs.DIR_DOWNLOADS, username)
    os.makedirs(out_dir, exist_ok=True)
    lim = opts.get("limit","")
    cmd = [_find_bin("yt-dlp"), url, "-o",
           os.path.join(out_dir,"%(upload_date)s_%(title)s.%(ext)s"),
           "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
           "--merge-output-format","mp4",
           "--audio-format","aac",
           "--postprocessor-args","ffmpeg:-c:a aac -b:a 192k",
           "--yes-playlist","--ignore-errors","--no-warnings","--progress"]
    if str(lim).isdigit(): cmd += ["--playlist-end", str(lim)]
    log(f"Downloading @{username}'s videos...")
    _stream_cmd(cmd, log)
    done(f"Saved to: {out_dir}", path=out_dir)


def _dl_playlist(url, opts, log, done, error):
    out_dir = os.path.join(_dirs.DIR_DOWNLOADS, "playlists")
    os.makedirs(out_dir, exist_ok=True)
    cmd = [_find_bin("yt-dlp"), url, "-o",
           os.path.join(out_dir,"%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s"),
           "--format", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best",
           "--merge-output-format","mp4",
           "--audio-format","aac",
           "--postprocessor-args","ffmpeg:-c:a aac -b:a 192k",
           "--yes-playlist","--ignore-errors","--no-warnings","--progress"]
    log("Downloading playlist / channel...")
    _stream_cmd(cmd, log)
    done(f"Saved to: {out_dir}", path=out_dir)


def _spotify(url, opts, log, prog, done, error):
    from tools.music_downloader import _get_tracks
    url = re.sub(r"\?.*$","",url.strip())
    log("Reading Spotify track info...")
    tracks = _get_tracks(url)
    if not tracks:
        return error("Could not read track info. Make sure the URL is public.")

    quality = opts.get("audio_quality", opts.get("quality","320"))
    os.makedirs(_dirs.DIR_AUDIO, exist_ok=True)
    out_tpl = os.path.join(_dirs.DIR_AUDIO, "%(artist)s - %(title)s.%(ext)s")
    log(f"Found {len(tracks)} track(s) — downloading from YouTube Music...")

    ok_n = fail_n = 0
    for i,t in enumerate(tracks, 1):
        title, artist = t.get("title",""), t.get("artist","")
        if not title: fail_n += 1; continue
        log(f"[{i}/{len(tracks)}] {title}" + (f" — {artist}" if artist else ""))
        prog(i, len(tracks))
        success = False
        _cflags = {"creationflags": 0x08000000} if os.name == "nt" else {}
        for q2 in [f"ytmsearch1:{title} {artist}".strip(),
                   f"ytsearch1:{title} {artist}".strip()]:
            r = subprocess.run([_find_bin("yt-dlp"), q2,
                "--extract-audio","--audio-format","mp3",
                "--audio-quality",f"{quality}k","--output",out_tpl,
                "--no-playlist","--quiet","--no-warnings",
                "--embed-thumbnail","--add-metadata"],
                capture_output=True, **_cflags)
            if r.returncode == 0: success = True; break
        if success: ok_n += 1
        else: fail_n += 1; log(f"  ✗ not found")

    done(f"{ok_n}/{len(tracks)} tracks downloaded → {_dirs.DIR_AUDIO}", path=_dirs.DIR_AUDIO)


def _dl_song(title, artist, opts, log, prog, done, error):
    """
    Download a single song using the same YouTube Music search flow as the
    Spotify downloader, but without needing a Spotify URL.
    """
    try:
        from tools.music_downloader import _dl_tracks
    except Exception as e:
        return error(f"Music downloader not available: {e}")

    quality = opts.get("audio_quality", opts.get("quality","320"))
    os.makedirs(_dirs.DIR_AUDIO, exist_ok=True)

    desc = f"{title}" + (f" — {artist}" if artist else "")
    log(f"Downloading song: {desc}")
    prog(0, 1)

    ok_n, fail_n = _dl_tracks([{"title": title, "artist": artist}], quality, _dirs.DIR_AUDIO)
    if ok_n:
        prog(1, 1)
        done(f"1/1 tracks downloaded → {_dirs.DIR_AUDIO}", path=_dirs.DIR_AUDIO)
    else:
        error("Song could not be downloaded from YouTube Music.")


def _soundcloud(url, opts, log, done, error):
    q = opts.get("quality", opts.get("audio_quality","320"))
    os.makedirs(_dirs.DIR_AUDIO, exist_ok=True)
    cmd = [_find_bin("yt-dlp"), url,"--extract-audio","--audio-format","mp3",
           "--audio-quality",f"{q}k",
           "--output",os.path.join(_dirs.DIR_AUDIO,"%(uploader)s - %(title)s.%(ext)s"),
           "--progress","--ignore-errors"]
    log("Downloading from SoundCloud...")
    _stream_cmd(cmd, log)
    done(f"Saved to: {_dirs.DIR_AUDIO}", path=_dirs.DIR_AUDIO)


def _audio_extract(inp, opts, log, done, error):
    bitrate = opts.get("bitrate","320")
    os.makedirs(_dirs.DIR_AUDIO, exist_ok=True)
    if inp.startswith("http"):
        cmd = [_find_bin("yt-dlp"), inp,"--extract-audio","--audio-format","mp3",
               "--audio-quality",f"{bitrate}k",
               "--output",os.path.join(_dirs.DIR_AUDIO,"%(title)s.%(ext)s"),
               "--progress"]
        log("Extracting audio from URL...")
        _stream_cmd(cmd, log)
        done(f"Saved to: {_dirs.DIR_AUDIO}", path=_dirs.DIR_AUDIO)
    else:
        if not os.path.exists(inp):
            return error(f"File not found: {inp}")
        out = os.path.join(_dirs.DIR_AUDIO, Path(inp).stem+"_audio.mp3")
        log(f"Extracting audio from: {Path(inp).name}")
        cmd = [_find_bin("ffmpeg"),"-y","-i",inp,"-vn","-acodec","libmp3lame",
               "-ab",f"{bitrate}k",out,"-hide_banner","-stats"]
        _stream_cmd(cmd, log)
        done(f"Saved: {out}", path=out)


# =============================================================================
# STUDIO
# =============================================================================

def _compress(inp, opts, log, done, error):
    """Route to the GUI compressor — handles preset cards, output folder, custom HB presets."""
    import queue as _q, threading as _th
    from tools.compressor import run_gui_compress
    ql = _q.Queue()
    _th.Thread(target=run_gui_compress, args=(opts, ql), daemon=True).start()
    while True:
        item = ql.get()
        if item is None: break
        t = item.get("type","")
        if   t == "log":   log(item.get("text",""))
        elif t == "done":  done(item.get("text",""), item.get("path",""))
        elif t == "error": error(item.get("text",""))


def _bulk_compress(folder, opts, log, prog, done, error):
    """Route to the GUI bulk compressor — handles preset cards and output folder."""
    import queue as _q, threading as _th
    from tools.compressor import run_gui_bulk_compress
    ql = _q.Queue()
    _th.Thread(target=run_gui_bulk_compress, args=(opts, ql), daemon=True).start()
    while True:
        item = ql.get()
        if item is None: break
        t = item.get("type","")
        if   t == "log":      log(item.get("text",""))
        elif t == "progress": prog(item.get("value",0), item.get("total",1))
        elif t == "done":     done(item.get("text",""), item.get("path",""))
        elif t == "error":    error(item.get("text",""))


def _bg_remove(inp, opts, log, prog, done, error):
    try:
        from rembg import remove
        from PIL import Image
    except ImportError:
        return error("rembg not installed. Run: pip install rembg pillow")

    exts = {".png",".jpg",".jpeg",".webp",".bmp"}
    if os.path.isdir(inp):
        files = [f for f in Path(inp).iterdir() if f.suffix.lower() in exts]
        if not files: return error("No images found in folder.")
        out_dir = os.path.join(inp, "no_bg")
        os.makedirs(out_dir, exist_ok=True)
        log(f"Processing {len(files)} image(s)...")
        for i,f in enumerate(files, 1):
            prog(i, len(files))
            log(f"[{i}/{len(files)}] {f.name}")
            try:
                out_img = remove(Image.open(str(f)))
                out_img.save(os.path.join(out_dir, f.stem+"_no_bg.png"))
            except Exception as e:
                log(f"  ✗ {e}")
        done(f"{len(files)} images → {out_dir}", path=out_dir)
    else:
        if not os.path.exists(inp): return error(f"File not found: {inp}")
        log(f"Removing background: {Path(inp).name}")
        try:
            out_path = os.path.join(Path(inp).parent, Path(inp).stem+"_no_bg.png")
            remove(Image.open(inp)).save(out_path)
            done(f"Saved: {out_path}", path=out_path)
        except Exception as e:
            error(f"Failed: {e}")


# =============================================================================
# HELPERS
# =============================================================================

def _stream_cmd(cmd, log_fn):
    try:
        kwargs = dict(
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace")
        if os.name == "nt":               # hide console window on Windows
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        proc = subprocess.Popen(cmd, **kwargs)
        for line in proc.stdout:
            line = _strip(line).strip()
            if line: log_fn(line)
        proc.wait()
        return proc.returncode
    except (FileNotFoundError, OSError) as _exc:
        log_fn(f"Command not found: {cmd[0]}  ({_exc})")
        return 1


