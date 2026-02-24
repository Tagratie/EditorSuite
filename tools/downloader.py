"""
tools/downloader.py
Single video DL  — TikTok / YouTube
Profile + Playlist DL  — merged: handles profiles, playlists, channels
"""
import os
import subprocess
import shutil

from ui import theme as _T
from utils.helpers import ok, info, err, warn, divider, prompt, back_to_menu
from utils import dirs as _dirs


def _need_ytdlp() -> bool:
    if shutil.which("yt-dlp"):
        return True
    err("yt-dlp not installed.  Run: pip install yt-dlp")
    return False

_FMT = {
    "best": "bestvideo+bestaudio/best",
    "1080": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "720":  "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "480":  "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
}


# ── Single Video ──────────────────────────────────────────────────────────────

def tool_dlvideo():
    divider("TIKTOK / YOUTUBE DOWNLOADER")
    print(f"  {_T.DIM}Download any single TikTok or YouTube video.{_T.R}")
    print(f"  {_T.DIM}TikTok: best available quality  ·  YouTube: up to 1080p MP4{_T.R}\n")

    if not _need_ytdlp():
        back_to_menu(); return

    url = prompt("Paste TikTok or YouTube URL").strip()
    if not url:
        back_to_menu(); return

    is_youtube = any(x in url for x in ("youtube.com", "youtu.be"))
    out_dir    = os.path.join(_dirs.DIR_DOWNLOADS, "single")
    os.makedirs(out_dir, exist_ok=True)
    out_tmpl   = os.path.join(out_dir, "%(uploader)s_%(title)s.%(ext)s")

    if is_youtube:
        quality = prompt("Max quality [1080/720/480/best]", "1080").strip()
        fmt     = _FMT.get(quality, _FMT["1080"])
        cmd     = ["yt-dlp", url, "-o", out_tmpl, "--format", fmt,
                   "--merge-output-format", "mp4", "--add-metadata", "--progress"]
        info(f"Downloading YouTube video ({quality}p)...")
    else:
        cmd = ["yt-dlp", url, "-o", out_tmpl,
               "--merge-output-format", "mp4", "--no-warnings", "--progress"]
        info("Downloading TikTok video...")

    print()
    ret = subprocess.run(cmd)
    print()
    if ret.returncode == 0:
        ok(f"Saved to: {out_dir}")
    else:
        err("Download failed — check the URL is a valid public video.")
    back_to_menu()


# ── Profile + Playlist (merged) ───────────────────────────────────────────────

def tool_profile_playlist():
    divider("TIKTOK / YOUTUBE PROFILE & PLAYLIST DOWNLOADER")
    print(f"  {_T.DIM}Download entire profiles, playlists, or channels — TikTok & YouTube.{_T.R}\n")

    if not _need_ytdlp():
        back_to_menu(); return

    print(f"  {_T.CYAN}1{_T.R}  TikTok profile      @username — all their videos")
    print(f"  {_T.CYAN}2{_T.R}  YouTube channel     full channel or any /videos page")
    print(f"  {_T.CYAN}3{_T.R}  YouTube playlist    any playlist URL")
    print(f"  {_T.CYAN}4{_T.R}  Paste any URL       auto-detect (playlist, channel, profile)\n")
    mode = prompt("Mode [1/2/3/4]", "1").strip()

    if mode == "1":
        raw = prompt("TikTok username (no @)").strip().lstrip("@")
        if not raw:
            back_to_menu(); return
        url   = f"https://www.tiktok.com/@{raw}"
        label = f"@{raw}"
        subdir = raw
    elif mode in ("2", "3", "4"):
        url = prompt("Paste URL").strip()
        if not url:
            back_to_menu(); return
        label  = url[:60]
        subdir = "download"
        # Try to pull a clean folder name from the URL
        import re
        m = re.search(r"@([\w.]+)|/c/([\w.]+)|/channel/([\w]+)|list=([\w_-]+)", url)
        if m:
            subdir = next(g for g in m.groups() if g)
    else:
        err("Invalid mode."); back_to_menu(); return

    # Quality
    print(f"\n  {_T.CYAN}1{_T.R}  Video (MP4)")
    print(f"  {_T.CYAN}2{_T.R}  Audio only (MP3)\n")
    media = prompt("Media type [1/2]", "1").strip()

    quality = prompt("Quality [best/1080/720/480]", "best").strip()
    limit   = prompt("Max videos (blank = all)", "").strip()

    out_dir  = os.path.join(_dirs.DIR_DOWNLOADS, subdir)
    os.makedirs(out_dir, exist_ok=True)
    out_tmpl = os.path.join(out_dir, "%(upload_date)s_%(title)s.%(ext)s")

    if media == "2":
        cmd = ["yt-dlp", url, "-o", out_tmpl,
               "--extract-audio", "--audio-format", "mp3", "--audio-quality", "0",
               "--yes-playlist", "--progress", "--ignore-errors", "--no-warnings"]
    else:
        fmt = _FMT.get(quality, _FMT["best"])
        cmd = ["yt-dlp", url, "-o", out_tmpl, "--format", fmt,
               "--merge-output-format", "mp4",
               "--yes-playlist", "--progress", "--ignore-errors", "--no-warnings",
               "--add-metadata"]

    if limit.isdigit():
        cmd += ["--playlist-end", limit]

    print()
    info(f"Downloading {label}")
    info(f"Saving to: {out_dir}")
    info("Press Ctrl+C to stop early — already downloaded files are kept.\n")

    try:
        subprocess.run(cmd)
        print(); ok(f"Done → {out_dir}")
    except KeyboardInterrupt:
        print(); warn("Stopped. Downloaded files are kept.")

    back_to_menu()
