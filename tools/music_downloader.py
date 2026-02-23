"""
tools/music_downloader.py
Tool 23 — Spotify / SoundCloud Downloader
  - Spotify  → spotdl  (auto-installed if missing, matches via YouTube Music)
  - SoundCloud → yt-dlp
Tool 24 — YouTube Playlist Downloader  (yt-dlp)
"""
import os
import sys
import subprocess
import shutil

from ui import theme as _T
from utils.helpers import ok, info, err, warn, divider, prompt, back_to_menu
from utils import dirs as _dirs


def _check_ytdlp() -> str | None:
    """Return yt-dlp path or None, printing an install hint if missing."""
    path = shutil.which("yt-dlp")
    if not path:
        err("yt-dlp not found.")
        info("Install with:  pip install yt-dlp")
    return path


def _ensure_spotdl() -> bool:
    """
    Ensure spotdl + setuptools are installed.
    Always invoked via  python -m spotdl  (avoids broken .exe issues on Windows).
    Returns True if ready, False on failure.
    """
    # 1. setuptools ships pkg_resources — spotdl needs it on Python 3.12+
    warn("Checking dependencies...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "setuptools", "--quiet", "--upgrade"],
        capture_output=True,
    )

    # 2. Install spotdl itself if not importable
    try:
        import spotdl  # noqa: F401
    except ImportError:
        warn("spotdl not found — installing now (one-time setup)...")
        print()
        ret = subprocess.run(
            [sys.executable, "-m", "pip", "install", "spotdl", "--quiet"],
        )
        if ret.returncode != 0:
            err("pip install spotdl failed.")
            info("Try manually:  pip install spotdl setuptools")
            return False
        ok("spotdl installed successfully.")

    return True


def _run_spotdl(args: list) -> int:
    """Always run spotdl as  python -m spotdl  — bypasses broken .exe files."""
    return subprocess.run([sys.executable, "-m", "spotdl"] + args).returncode


# ── Tool 23: Spotify / SoundCloud Downloader ─────────────────────────────────

def tool_music_dl():
    divider("SPOTIFY / SOUNDCLOUD DOWNLOADER")
    print(f"  {_T.DIM}Download any Spotify track, album, or playlist as MP3.{_T.R}")
    print(f"  {_T.DIM}Also supports SoundCloud URLs via yt-dlp.{_T.R}\n")

    url = prompt("Paste Spotify or SoundCloud URL").strip()
    if not url:
        back_to_menu(); return

    is_spotify    = "spotify.com"    in url
    is_soundcloud = "soundcloud.com" in url

    os.makedirs(_dirs.DIR_AUDIO, exist_ok=True)

    # ── Spotify → spotdl ──────────────────────────────────────────────────────
    if is_spotify:
        if not _ensure_spotdl():
            back_to_menu(); return

        quality = prompt("Audio quality kbps [320/256/192/128]", "320")
        print()
        info("Starting Spotify download via spotdl...")
        info(f"Saving to: {_dirs.DIR_AUDIO}\n")

        ret = _run_spotdl([
            "download", url,
            "--output",       _dirs.DIR_AUDIO,
            "--bitrate",      f"{quality}k",
            "--format",       "mp3",
            "--print-errors",
        ])

        print()
        if ret == 0:
            ok(f"Download complete → {_dirs.DIR_AUDIO}")
        else:
            err("spotdl encountered errors (some tracks may still have downloaded).")
            info("If a track is unavailable on YouTube Music, spotdl will skip it.")

    # ── SoundCloud → yt-dlp ──────────────────────────────────────────────────
    elif is_soundcloud:
        ytdlp = _check_ytdlp()
        if not ytdlp:
            back_to_menu(); return

        quality = prompt("Audio quality kbps [320/256/192/128]", "320")
        out_tpl = os.path.join(_dirs.DIR_AUDIO, "%(uploader)s - %(title)s.%(ext)s")
        print()
        info("Starting SoundCloud download via yt-dlp...")

        ret = subprocess.run([
            ytdlp, url,
            "--extract-audio",
            "--audio-format",  "mp3",
            "--audio-quality", f"{quality}k",
            "--output",        out_tpl,
            "--progress",
            "--ignore-errors",
        ]).returncode

        print()
        if ret == 0:
            ok(f"Download complete → {_dirs.DIR_AUDIO}")
        else:
            err("Download failed or partially completed.")

    else:
        err("Unrecognised URL. Paste a Spotify or SoundCloud link.")

    back_to_menu()


# ── Tool 24: YouTube Playlist Downloader ─────────────────────────────────────

def tool_playlist_dl():
    divider("YOUTUBE PLAYLIST DOWNLOADER")
    print(f"  {_T.DIM}Download an entire YouTube playlist or channel — video or audio.{_T.R}\n")

    ytdlp = _check_ytdlp()
    if not ytdlp:
        back_to_menu(); return

    url = prompt("Paste YouTube playlist / channel URL").strip()
    if not url:
        back_to_menu(); return

    print(f"\n  {_T.CYAN}1{_T.R}  Video (MP4)")
    print(f"  {_T.CYAN}2{_T.R}  Audio only (MP3)\n")
    mode = prompt("Mode [1/2]", "1").strip()

    if mode == "2":
        out_dir = _dirs.DIR_AUDIO
        fmt_args = [
            "--extract-audio",
            "--audio-format",  "mp3",
            "--audio-quality", "0",
        ]
    else:
        out_dir = _dirs.DIR_DOWNLOADS
        # Best quality MP4 with height cap at 1080p
        fmt_args = [
            "--format", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
        ]

    # Optional: limit number of videos (useful for huge channels)
    limit = prompt("Max videos to download (blank = all)", "").strip()

    os.makedirs(out_dir, exist_ok=True)
    playlist_name = "%(playlist_title)s" if "playlist" in url.lower() else "%(uploader)s"
    out_tpl = os.path.join(out_dir, playlist_name, "%(playlist_index)s - %(title)s.%(ext)s")

    cmd = [
        ytdlp, url,
        "--output",       out_tpl,
        "--yes-playlist",
        "--progress",
        "--ignore-errors",
        "--no-warnings",
        "--add-metadata",
    ] + fmt_args

    if limit.isdigit():
        cmd += ["--playlist-end", limit]

    print()
    info(f"Downloading playlist → {out_dir}")
    info("Press Ctrl+C at any time to stop.\n")

    try:
        subprocess.run(cmd)
        print()
        ok(f"Playlist download complete → {out_dir}")
    except KeyboardInterrupt:
        print()
        warn("Stopped by user. Already-downloaded files are kept.")

    back_to_menu()
