"""
tools/audio_tools.py
Tool 13 — Audio Extractor  (video → MP3 via ffmpeg)
Tool 14 — Video Speed Changer  (slow-mo / speed-up via ffmpeg)
"""
import os
import subprocess

from ui import theme as _T
from utils.helpers import ok, info, err, divider, prompt, back_to_menu
from utils import dirs as _dirs


def _ffmpeg_available() -> bool:
    import shutil
    return bool(shutil.which("ffmpeg"))


# ── Tool 13: Audio Extractor ──────────────────────────────────────────────────

def tool_audioextract():
    divider("AUDIO EXTRACTOR")
    print(f"  {_T.DIM}Rips audio from any video file to MP3.{_T.R}\n")
    if not _ffmpeg_available():
        err("ffmpeg not found. Install from https://ffmpeg.org"); back_to_menu(); return

    raw = prompt("Drag a video file here").strip().strip('"\'')
    if not raw or not os.path.exists(raw):
        err("File not found."); back_to_menu(); return

    os.makedirs(_dirs.DIR_AUDIO, exist_ok=True)
    stem = os.path.splitext(os.path.basename(raw))[0]
    out  = os.path.join(_dirs.DIR_AUDIO, stem + "_audio.mp3")

    bitrate = prompt("Bitrate (kbps)", "320")
    print()
    info(f"Extracting audio → {os.path.basename(out)}...")
    ret = subprocess.run([
        "ffmpeg", "-y", "-i", raw,
        "-vn", "-acodec", "libmp3lame", "-ab", f"{bitrate}k",
        out,
    ], capture_output=True)

    if os.path.exists(out):
        size = os.path.getsize(out) / 1024 / 1024
        ok(f"Done → {out}  ({size:.1f} MB)")
    else:
        err("Extraction failed.")
        print(ret.stderr.decode(errors="replace")[-400:])
    back_to_menu()


# ── Tool 14: Video Speed Changer ──────────────────────────────────────────────

def tool_speed():
    divider("VIDEO SPEED CHANGER")
    if not _ffmpeg_available():
        err("ffmpeg not found. Install from https://ffmpeg.org"); back_to_menu(); return

    raw = prompt("Drag a video file here").strip().strip('"\'')
    if not raw or not os.path.exists(raw):
        err("File not found."); back_to_menu(); return

    print(f"\n  {_T.DIM}Examples: 0.5 = half speed (slow-mo)  |  2.0 = double speed{_T.R}")
    factor_str = prompt("Speed factor", "0.5")
    try:
        factor = float(factor_str)
    except Exception:
        factor = 0.5

    base, _ = os.path.splitext(raw)
    out      = f"{base}_{factor}x.mp4"
    vf       = f"setpts={1/factor:.4f}*PTS"

    # atempo only accepts 0.5–2.0; chain multiple filters for extreme values
    af_val = factor
    atempo: list[str] = []
    while af_val > 2.0:
        atempo.append("atempo=2.0"); af_val /= 2.0
    while af_val < 0.5:
        atempo.append("atempo=0.5"); af_val *= 2.0
    atempo.append(f"atempo={af_val:.4f}")
    af = ",".join(atempo)

    print()
    info(f"Processing at {factor}x speed...")
    ret = subprocess.run([
        "ffmpeg", "-y", "-i", raw,
        "-vf", vf, "-af", af,
        "-c:v", "libx264", "-c:a", "aac",
        out,
    ], capture_output=True)

    if os.path.exists(out):
        ok(f"Done → {out}")
    else:
        err("Failed.")
        print(ret.stderr.decode(errors="replace")[-400:])
    back_to_menu()
