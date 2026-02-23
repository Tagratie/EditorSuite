"""
tools/downloader.py
Tool 8  — Profile / Batch Video Downloader (yt-dlp)
Tool 12 — TikTok / YouTube Downloader (single video, no watermark)
"""
import os
import subprocess

from ui import theme as _T
from utils.helpers import ok, info, err, warn, divider, prompt, back_to_menu
from utils import dirs as _dirs


def _ytdlp_available() -> bool:
    import shutil
    return bool(shutil.which("yt-dlp"))


# ── Tool 12: TikTok / YouTube Downloader ─────────────────────────────────────

def tool_dlvideo():
    divider("TIKTOK / YOUTUBE DOWNLOADER")
    print(f"  {_T.DIM}Download any single TikTok or YouTube video.{_T.R}")
    print(f"  {_T.DIM}TikTok: best available quality  ·  YouTube: up to 1080p MP4{_T.R}\n")

    if not _ytdlp_available():
        err("yt-dlp not installed. Run: pip install yt-dlp")
        back_to_menu(); return

    url = prompt("Paste TikTok or YouTube URL").strip()
    if not url:
        back_to_menu(); return

    is_youtube = any(x in url for x in ("youtube.com", "youtu.be"))

    out_dir  = os.path.join(_dirs.DIR_DOWNLOADS, "single")
    os.makedirs(out_dir, exist_ok=True)
    out_tmpl = os.path.join(out_dir, "%(uploader)s_%(title)s.%(ext)s")

    if is_youtube:
        quality = prompt("Max quality [1080/720/480/best]", "1080").strip()
        height  = quality if quality.isdigit() else "1080"
        cmd = [
            "yt-dlp", url,
            "-o", out_tmpl,
            "--format", f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "--add-metadata",
            "--progress",
        ]
        info(f"Downloading YouTube video at up to {height}p...")
    else:
        # TikTok — strip watermark
        cmd = [
            "yt-dlp", url,
            "-o", out_tmpl,
            "--merge-output-format", "mp4",
            "--no-warnings", "--progress",
        ]
        info("Downloading TikTok video...")

    print()
    ret = subprocess.run(cmd)
    if ret.returncode == 0:
        print(); ok(f"Saved to: {out_dir}")
    else:
        err("Download failed — check that the URL is a valid public video.")
    back_to_menu()


# ── Tool 8: Profile / Batch Downloader ───────────────────────────────────────

def tool_downloader():
    divider("VIDEO DOWNLOADER")
    print(f"  {_T.CYAN}1{_T.R}  Download all videos from a TikTok / YouTube profile")
    print(f"  {_T.CYAN}2{_T.R}  Batch download from a list of URLs (any yt-dlp supported site)")
    print()

    if not _ytdlp_available():
        err("yt-dlp not installed. Run: pip install yt-dlp"); back_to_menu(); return

    mode = prompt("Mode [1/2]", "1").strip()

    if mode == "1":
        _download_profile()
    elif mode == "2":
        _download_batch()
    else:
        err("Invalid mode.")
        back_to_menu()


def _download_profile():
    username = prompt("TikTok or YouTube username / handle").strip().lstrip("@")
    if not username:
        back_to_menu(); return

    quality = prompt("Quality [best/1080/720/480]", "best").strip()
    fmt_map = {"best": "bestvideo+bestaudio/best",
               "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
               "720":  "bestvideo[height<=720]+bestaudio/best[height<=720]",
               "480":  "bestvideo[height<=480]+bestaudio/best[height<=480]"}
    fmt = fmt_map.get(quality, "bestvideo+bestaudio/best")

    dl_path = os.path.join(_dirs.DIR_DOWNLOADS, username)
    os.makedirs(dl_path, exist_ok=True)
    out_tmpl = os.path.join(dl_path, "%(upload_date)s_%(title)s.%(ext)s")

    # Try TikTok first, fall back to plain username for YouTube
    urls = [f"https://www.tiktok.com/@{username}", username]
    print()
    info(f"Downloading @{username} → {dl_path}")
    for url in urls:
        ret = subprocess.run([
            "yt-dlp", url,
            "-f", fmt, "-o", out_tmpl,
            "--merge-output-format", "mp4",
            "--no-warnings", "--progress",
        ])
        if ret.returncode == 0:
            break
    ok(f"Done — saved to {dl_path}")
    back_to_menu()


def _download_batch():
    print(f"\n  {_T.DIM}Enter one URL per line. Empty line when done.{_T.R}\n")
    urls = []
    while True:
        line = input(f"  {_T.CYAN}>{_T.R} URL (blank to finish): ").strip()
        if not line:
            break
        urls.append(line)
    if not urls:
        warn("No URLs entered."); back_to_menu(); return

    quality = prompt("Quality [best/1080/720/480]", "best").strip()
    fmt_map = {"best": "bestvideo+bestaudio/best",
               "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
               "720":  "bestvideo[height<=720]+bestaudio/best[height<=720]",
               "480":  "bestvideo[height<=480]+bestaudio/best[height<=480]"}
    fmt = fmt_map.get(quality, "bestvideo+bestaudio/best")

    dl_path = os.path.join(_dirs.DIR_DOWNLOADS, "batch")
    os.makedirs(dl_path, exist_ok=True)
    out_tmpl = os.path.join(dl_path, "%(uploader)s_%(title)s.%(ext)s")

    print()
    ok(f"Downloading {len(urls)} URLs → {dl_path}")
    for i, url in enumerate(urls, 1):
        info(f"[{i}/{len(urls)}] {url[:70]}")
        subprocess.run([
            "yt-dlp", url,
            "-f", fmt, "-o", out_tmpl,
            "--merge-output-format", "mp4",
            "--no-warnings", "--progress",
        ])
    ok("Batch download complete.")
    back_to_menu()
