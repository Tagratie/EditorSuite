"""
gui/runner.py
Runs EditorSuite tools in a background thread, yields progress lines
that the SSE endpoint streams to the browser.
"""
import os
import sys
import re
import queue
import threading
import subprocess
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import load_config
from utils.dirs   import _init_dirs
from ui.theme     import _apply_theme

load_config(); _apply_theme("default"); _init_dirs()
from utils import dirs as _dirs


def _strip_ansi(s: str) -> str:
    return re.sub(r'\033\[[0-9;]*m', '', s)


class StreamCapture:
    """Redirect stdout/stderr into a queue so we can stream it."""
    def __init__(self, q: queue.Queue):
        self.q = q
        self._orig_out = sys.stdout
        self._orig_err = sys.stderr

    def __enter__(self):
        sys.stdout = self
        sys.stderr = self
        return self

    def __exit__(self, *_):
        sys.stdout = self._orig_out
        sys.stderr = self._orig_err

    def write(self, s: str):
        if s and s.strip():
            self.q.put({"type": "log", "text": _strip_ansi(s).rstrip()})
        self._orig_out.write(s)

    def flush(self):
        self._orig_out.flush()


def run_task(detected: dict, options: dict, q: queue.Queue) -> None:
    """
    Entry point called in a background thread.
    Puts {"type": "log"|"progress"|"result"|"done"|"error", ...} dicts into q.
    """
    kind  = detected["type"]
    value = detected["value"]

    def log(msg):    q.put({"type": "log",      "text": msg})
    def prog(n, t):  q.put({"type": "progress", "value": n, "total": t})
    def result(d):   q.put({"type": "result",   "data": d})
    def done(msg=""):q.put({"type": "done",     "text": msg})
    def error(msg):  q.put({"type": "error",    "text": msg})

    try:
        if kind == "hashtag":
            _run_hashtag_scrape(value, options, log, prog, result, done, error)
        elif kind in ("tiktok_video", "youtube_video"):
            _run_video_dl(value, options, log, done, error)
        elif kind == "tiktok_profile":
            _run_profile_dl(value, options, log, done, error)
        elif kind == "youtube_playlist":
            _run_playlist_dl(value, options, log, done, error)
        elif kind in ("spotify_track", "spotify_album", "spotify_playlist"):
            _run_spotify(value, options, log, prog, done, error)
        elif kind == "soundcloud":
            _run_soundcloud(value, options, log, done, error)
        else:
            error(f"Don't know how to handle: {kind}")
    except Exception as e:
        import traceback
        error(f"Unexpected error: {e}")
        log(traceback.format_exc())
    finally:
        q.put(None)   # sentinel — stream closed


# ── Hashtag scrape ────────────────────────────────────────────────────────────

def _run_hashtag_scrape(hashtag, opts, log, prog, result, done, error):
    import asyncio
    from tools.audio_scraper import scrape_sounds
    from core.filters import check_garbage, is_funk

    target = int(opts.get("limit", 300))
    log(f"Scraping #{hashtag} — targeting {target} videos...")

    try:
        scanned, sounds = asyncio.run(scrape_sounds(hashtag, target))
    except Exception as e:
        error(f"Scrape failed: {e}"); return

    kept = sorted(
        [v for v in sounds.values() if not v["reason"]],
        key=lambda x: x["count"], reverse=True
    )
    removed = [v for v in sounds.values() if v["reason"]]

    log(f"Scanned {scanned} videos · {len(kept)} sounds found · {len(removed)} filtered")

    # Save HTML report
    from utils.html_report import save_sounds_report
    os.makedirs(_dirs.DIR_SOUNDS, exist_ok=True)
    html_path = save_sounds_report(hashtag, scanned, kept, removed, _dirs.DIR_SOUNDS)

    result({
        "type":        "sounds",
        "hashtag":     hashtag,
        "scanned":     scanned,
        "kept":        len(kept),
        "removed":     len(removed),
        "top":         kept[:10],
        "html_path":   html_path,
    })
    done(f"Done — {len(kept)} trending sounds found")


# ── Video download ─────────────────────────────────────────────────────────────

def _run_video_dl(url, opts, log, done, error):
    quality = opts.get("quality", "1080")
    out_dir = os.path.join(_dirs.DIR_DOWNLOADS, "single")
    os.makedirs(out_dir, exist_ok=True)
    out_tpl = os.path.join(out_dir, "%(uploader)s_%(title)s.%(ext)s")
    is_yt   = any(x in url for x in ("youtube.com", "youtu.be"))

    if is_yt:
        cmd = ["yt-dlp", url, "-o", out_tpl,
               "--format", f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
               "--merge-output-format", "mp4", "--add-metadata", "--progress"]
    else:
        cmd = ["yt-dlp", url, "-o", out_tpl, "--merge-output-format", "mp4",
               "--no-warnings", "--progress"]

    log(f"Downloading {'YouTube' if is_yt else 'TikTok'} video...")
    _stream_subprocess(cmd, log)
    done(f"Saved to: {out_dir}")


# ── Profile download ───────────────────────────────────────────────────────────

def _run_profile_dl(username, opts, log, done, error):
    url     = f"https://www.tiktok.com/@{username.lstrip('@')}"
    out_dir = os.path.join(_dirs.DIR_DOWNLOADS, username)
    os.makedirs(out_dir, exist_ok=True)
    out_tpl = os.path.join(out_dir, "%(upload_date)s_%(title)s.%(ext)s")
    limit   = opts.get("limit", "")
    cmd     = ["yt-dlp", url, "-o", out_tpl,
               "--format", "bestvideo+bestaudio/best",
               "--merge-output-format", "mp4",
               "--yes-playlist", "--ignore-errors", "--no-warnings", "--progress"]
    if str(limit).isdigit():
        cmd += ["--playlist-end", str(limit)]
    log(f"Downloading @{username}'s videos...")
    _stream_subprocess(cmd, log)
    done(f"Saved to: {out_dir}")


# ── Playlist download ─────────────────────────────────────────────────────────

def _run_playlist_dl(url, opts, log, done, error):
    out_dir = os.path.join(_dirs.DIR_DOWNLOADS, "playlists")
    os.makedirs(out_dir, exist_ok=True)
    out_tpl = os.path.join(out_dir, "%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s")
    cmd     = ["yt-dlp", url, "-o", out_tpl,
               "--format", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
               "--merge-output-format", "mp4", "--yes-playlist",
               "--ignore-errors", "--no-warnings", "--progress"]
    log("Downloading playlist / channel...")
    _stream_subprocess(cmd, log)
    done(f"Saved to: {out_dir}")


# ── Spotify ───────────────────────────────────────────────────────────────────

def _run_spotify(url, opts, log, prog, done, error):
    from tools.music_downloader import _fetch_spotify_tracks
    import json, urllib.request, re as _re

    log("Reading Spotify track info...")
    tracks = _fetch_spotify_tracks(url)
    if not tracks:
        error("Could not read track info from Spotify page."); return

    log(f"Found {len(tracks)} track(s) — searching YouTube Music...")
    quality = opts.get("quality", "320")
    os.makedirs(_dirs.DIR_AUDIO, exist_ok=True)
    out_tpl = os.path.join(_dirs.DIR_AUDIO, "%(artist)s - %(title)s.%(ext)s")

    ok_n = fail_n = 0
    for i, t in enumerate(tracks, 1):
        title, artist = t.get("title",""), t.get("artist","")
        if not title: fail_n += 1; continue
        log(f"[{i}/{len(tracks)}] {title}" + (f" — {artist}" if artist else ""))
        prog(i, len(tracks))
        success = False
        for q in [f"ytmsearch1:{title} {artist}".strip(),
                  f"ytsearch1:{title} {artist}".strip()]:
            r = subprocess.run(["yt-dlp", q, "--extract-audio", "--audio-format", "mp3",
                                "--audio-quality", f"{quality}k", "--output", out_tpl,
                                "--no-playlist", "--quiet", "--no-warnings",
                                "--embed-thumbnail", "--add-metadata"],
                               capture_output=True)
            if r.returncode == 0:
                success = True; break
        if success: ok_n += 1
        else: fail_n += 1; log(f"  ✗ not found on YouTube Music")

    done(f"{ok_n}/{len(tracks)} tracks downloaded → {_dirs.DIR_AUDIO}")


# ── SoundCloud ────────────────────────────────────────────────────────────────

def _run_soundcloud(url, opts, log, done, error):
    quality = opts.get("quality", "320")
    out_tpl = os.path.join(_dirs.DIR_AUDIO, "%(uploader)s - %(title)s.%(ext)s")
    os.makedirs(_dirs.DIR_AUDIO, exist_ok=True)
    log("Downloading from SoundCloud...")
    cmd = ["yt-dlp", url, "--extract-audio", "--audio-format", "mp3",
           "--audio-quality", f"{quality}k", "--output", out_tpl,
           "--progress", "--ignore-errors"]
    _stream_subprocess(cmd, log)
    done(f"Saved to: {_dirs.DIR_AUDIO}")


# ── Subprocess streaming helper ───────────────────────────────────────────────

def _stream_subprocess(cmd: list, log_fn) -> int:
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace")
        for line in proc.stdout:
            line = _strip_ansi(line).strip()
            if line:
                log_fn(line)
        proc.wait()
        return proc.returncode
    except FileNotFoundError:
        log_fn(f"Command not found: {cmd[0]}")
        return 1


# ── Named tool runner (sidebar tools) ────────────────────────────────────────

def run_named_tool(tool_id: str, options: dict, q: queue.Queue) -> None:
    """
    Runs a tool by its sidebar ID.
    Wraps the existing CLI tool functions, capturing their stdout.
    """
    def log(msg):    q.put({"type": "log",  "text": msg})
    def done(msg=""): q.put({"type": "done", "text": msg})
    def error(msg):  q.put({"type": "error","text": msg})

    try:
        _dispatch_named(tool_id, options, log, done, error, q)
    except Exception as e:
        import traceback
        error(f"Error: {e}")
        log(traceback.format_exc())
    finally:
        q.put(None)


def _dispatch_named(tool_id, opts, log, done, error, q):
    """Map sidebar tool IDs to runner logic."""

    # ── SCRAPERS ──────────────────────────────────────────────────────────────
    if tool_id == "scraper":
        hashtag = opts.get("hashtag","").lstrip("#")
        if not hashtag: error("Enter a hashtag."); return
        _run_hashtag_scrape(hashtag, opts, log,
                            lambda v,t: q.put({"type":"progress","value":v,"total":t}),
                            lambda d: q.put({"type":"result","data":d}),
                            done, error)

    elif tool_id in ("hfreq","hanalyze"):
        hashtags = [h.strip().lstrip("#") for h in opts.get("hashtags","").split(",") if h.strip()]
        if not hashtags: hashtags = [opts.get("hashtag","").lstrip("#")]
        if not any(hashtags): error("Enter at least one hashtag."); return
        log(f"Analysing {len(hashtags)} hashtag(s)...")
        _run_cli_tool("tool_hpa" if tool_id=="hanalyze" else "tool_caption", opts, log, done, error)

    elif tool_id == "crosshash":
        _run_cli_tool("tool_crosshash", opts, log, done, error)

    elif tool_id == "viral":
        hashtag = opts.get("hashtag","").lstrip("#")
        if not hashtag: error("Enter a hashtag."); return
        _run_hashtag_viral(hashtag, opts, log,
                           lambda d: q.put({"type":"result","data":d}),
                           done, error)

    elif tool_id == "trending":
        _run_cli_tool("tool_trending", opts, log, done, error)

    elif tool_id == "sp_exp":
        _run_cli_tool("tool_ets", opts, log, done, error)

    # ── ANALYTICS ─────────────────────────────────────────────────────────────
    elif tool_id == "competitor":
        _run_cli_tool("tool_ct", opts, log, done, error)

    elif tool_id == "besttime":
        _run_cli_tool("tool_bptf", opts, log, done, error)

    elif tool_id == "engagement":
        _run_cli_tool("tool_engagerate", opts, log, done, error)

    elif tool_id == "niche":
        _run_cli_tool("tool_nichereport", opts, log, done, error)

    elif tool_id == "growth":
        _run_cli_tool("tool_growthtrack", opts, log, done, error)

    elif tool_id == "health":
        username = opts.get("username","").lstrip("@")
        if not username: error("Enter a TikTok username."); return
        opts["username"] = username
        _run_cli_tool("tool_account_health", opts, log, done, error)

    # ── DOWNLOADERS ───────────────────────────────────────────────────────────
    elif tool_id == "dl_vid":
        url = opts.get("url","")
        if not url: error("Enter a URL."); return
        _run_video_dl(url, opts, log, done, error)

    elif tool_id == "dl_prof":
        url = opts.get("url","").strip()
        if url.startswith("@"): url = f"https://www.tiktok.com/{url}"
        if not url: error("Enter a URL or @username."); return
        if "tiktok.com/@" in url:
            username = re.sub(r"https?://[^/]+/@?","", url).rstrip("/")
            _run_profile_dl(username, opts, log, done, error)
        else:
            _run_playlist_dl(url, opts, log, done, error)

    elif tool_id == "dl_spotify":
        url = opts.get("url","")
        if not url: error("Enter a Spotify or SoundCloud URL."); return
        if "soundcloud" in url:
            _run_soundcloud(url, opts, log, done, error)
        else:
            opts["audio_quality"] = opts.get("quality","320")
            _run_spotify(url, opts, log,
                         lambda v,t: q.put({"type":"progress","value":v,"total":t}),
                         done, error)

    elif tool_id == "dl_audio":
        inp = opts.get("input","")
        if not inp: error("Enter a file path or URL."); return
        if inp.startswith("http"):
            _run_soundcloud(inp, opts, log, done, error)  # yt-dlp handles TikTok/YT too
        else:
            _run_audio_extract(inp, opts, log, done, error)

    # ── STUDIO ────────────────────────────────────────────────────────────────
    elif tool_id in ("compress","bulk_comp","bg_rem","calendar"):
        _run_cli_tool({
            "compress":  "tool_compress",
            "bulk_comp": "tool_bulkcompress",
            "bg_rem":    "tool_bgremove",
            "calendar":  "tool_calendar",
        }[tool_id], opts, log, done, error)

    else:
        error(f"Unknown tool: {tool_id}")


def _run_audio_extract(inp: str, opts: dict, log, done, error):
    bitrate = opts.get("bitrate","320")
    out_dir = _dirs.DIR_AUDIO
    os.makedirs(out_dir, exist_ok=True)
    fname   = os.path.splitext(os.path.basename(inp))[0] + "_audio.mp3"
    out     = os.path.join(out_dir, fname)
    log(f"Extracting audio from: {inp}")
    cmd = ["ffmpeg","-y","-i",inp,"-vn","-acodec","libmp3lame",
           "-ab",f"{bitrate}k",out,"-hide_banner"]
    ret = _stream_subprocess(cmd, log)
    if ret == 0: done(f"Saved: {out}")
    else: error("ffmpeg extraction failed.")


def _run_hashtag_viral(hashtag, opts, result_fn, done, error):
    import asyncio
    from tools.viral_finder import _scrape_viral
    try:
        videos = asyncio.run(_scrape_viral(hashtag, int(opts.get("limit",100))))
    except Exception as e:
        error(f"Scrape failed: {e}"); return
    if not videos: error("No videos found."); return
    result_fn({"type":"viral","hashtag":hashtag,"videos":videos[:10]})
    done(f"{len(videos)} videos found")


def _run_cli_tool(fn_name: str, opts: dict, log, done, error):
    """
    Last-resort runner: calls the CLI tool function directly,
    capturing its stdout into the log stream.
    Interactive prompts won't work but most tools just need
    the options pre-filled.
    """
    log(f"Running {fn_name}...")
    log("(This tool requires interactive input — please use the CLI version for full functionality)")
    done(f"Open the terminal app and run: main.py → select the tool")
