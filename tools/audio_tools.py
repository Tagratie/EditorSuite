"""
tools/audio_tools.py
Audio Extractor — rips audio from a local video file OR downloads audio
directly from a TikTok / YouTube URL.
Uses ffmpeg for local files, yt-dlp for URLs.
"""
import os
import shutil
import subprocess

from ui import theme as _T
from utils.helpers import ok, info, err, warn, divider, prompt, back_to_menu
from utils import dirs as _dirs


def _is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def tool_audioextract():
    divider("AUDIO EXTRACTOR")
    print(f"  {_T.DIM}Rip audio to MP3 from a local video file{_T.R}")
    print(f"  {_T.DIM}or download audio directly from a TikTok / YouTube URL.{_T.R}\n")

    raw = prompt("Drag a video file here  OR  paste a TikTok / YouTube URL").strip().strip('"\'')
    if not raw:
        back_to_menu(); return

    bitrate = prompt("Bitrate kbps [320/256/192/128]", "320").strip()
    os.makedirs(_dirs.DIR_AUDIO, exist_ok=True)

    if _is_url(raw):
        # ── URL mode: yt-dlp ──────────────────────────────────────────────────
        if not shutil.which("yt-dlp"):
            err("yt-dlp not installed.  Run: pip install yt-dlp")
            back_to_menu(); return

        out_tmpl = os.path.join(_dirs.DIR_AUDIO, "%(uploader)s - %(title)s.%(ext)s")
        print()
        info("Downloading and extracting audio via yt-dlp...")
        ret = subprocess.run([
            "yt-dlp", raw,
            "--extract-audio",
            "--audio-format",  "mp3",
            "--audio-quality", f"{bitrate}k",
            "--output",        out_tmpl,
            "--progress",
            "--no-warnings",
        ])
        print()
        if ret.returncode == 0:
            ok(f"Saved to: {_dirs.DIR_AUDIO}")
        else:
            err("Download failed — check the URL is a valid public video.")

    else:
        # ── Local file mode: ffmpeg ───────────────────────────────────────────
        if not os.path.exists(raw):
            err(f"File not found: {raw}")
            back_to_menu(); return

        if not shutil.which("ffmpeg"):
            err("ffmpeg not found.  Install from https://ffmpeg.org")
            back_to_menu(); return

        stem = os.path.splitext(os.path.basename(raw))[0]
        out  = os.path.join(_dirs.DIR_AUDIO, stem + "_audio.mp3")
        print()
        info(f"Extracting audio → {os.path.basename(out)}...")
        ret = subprocess.run([
            "ffmpeg", "-y", "-i", raw,
            "-vn", "-acodec", "libmp3lame", "-ab", f"{bitrate}k",
            out,
        ], capture_output=True)

        if os.path.exists(out) and os.path.getsize(out) > 1000:
            sz = os.path.getsize(out) / 1024 / 1024
            print(); ok(f"Saved: {out}  ({sz:.1f} MB)")
        else:
            err("Extraction failed.")
            print(ret.stderr.decode(errors="replace")[-400:])

    back_to_menu()
