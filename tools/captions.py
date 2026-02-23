"""
tools/captions.py
Tool 6.1 — Caption / Subtitle Generator
Uses OpenAI Whisper (runs 100% locally, no API key) to transcribe any video
or audio file and export SRT / TXT / VTT subtitles.
Auto-installs openai-whisper if missing.
"""
import os
import sys
import subprocess
import shutil
from datetime import datetime

from ui import theme as _T
from utils.helpers import ok, info, err, warn, divider, prompt, back_to_menu
from utils import dirs as _dirs


_MODELS = {
    "1": ("tiny",   "~39 MB   — fastest,  English-only, lower accuracy"),
    "2": ("base",   "~74 MB   — fast,     good for clear audio"),
    "3": ("small",  "~244 MB  — balanced, recommended for most uses"),
    "4": ("medium", "~769 MB  — accurate, slower"),
    "5": ("large",  "~1.5 GB  — best quality, slowest"),
}

_FORMATS = {
    "1": "srt",   # SubRip — works in Premiere, DaVinci, CapCut, VLC, YouTube
    "2": "vtt",   # WebVTT — web / browsers
    "3": "txt",   # plain transcript
    "4": "all",   # all three
}


def _ensure_whisper() -> bool:
    """Install openai-whisper and ffmpeg-python if missing. Returns True if ready."""
    try:
        import whisper  # noqa: F401
        return True
    except ImportError:
        warn("openai-whisper not found — installing (one-time, ~150 MB)...")
        print()
        ret = subprocess.run(
            [sys.executable, "-m", "pip", "install",
             "openai-whisper", "setuptools", "--quiet"],
        )
        if ret.returncode != 0:
            err("Installation failed.")
            info("Try manually:  pip install openai-whisper")
            return False
        try:
            import whisper  # noqa: F401
            ok("openai-whisper installed.")
            return True
        except ImportError:
            err("Install succeeded but whisper still not importable.")
            return False


def tool_captions():
    divider("CAPTION / SUBTITLE GENERATOR")
    print(f"  {_T.DIM}Transcribes any video or audio to SRT / TXT / VTT using local AI.{_T.R}")
    print(f"  {_T.DIM}Runs 100% offline — no API key, no upload.{_T.R}\n")

    if not _ensure_whisper():
        back_to_menu(); return

    if not shutil.which("ffmpeg"):
        err("ffmpeg not found — required by Whisper.")
        info("Install from https://ffmpeg.org  or:  winget install ffmpeg")
        back_to_menu(); return

    # File input
    raw = prompt("Drag a video or audio file here").strip().strip('"').strip("'")
    if not raw or not os.path.exists(raw):
        err("File not found."); back_to_menu(); return

    # Model selection
    print(f"\n  {_T.BOLD}Whisper model:{_T.R}")
    for k, (name, desc) in _MODELS.items():
        print(f"  {_T.CYAN}{k}{_T.R}  {name:<8}  {_T.DIM}{desc}{_T.R}")
    model_key = prompt("\nModel", "3")
    model_name = _MODELS.get(model_key, _MODELS["3"])[0]

    # Output format
    print(f"\n  {_T.BOLD}Output format:{_T.R}")
    for k, fmt in _FORMATS.items():
        print(f"  {_T.CYAN}{k}{_T.R}  {fmt}")
    fmt_key = prompt("\nFormat", "1")
    out_fmt = _FORMATS.get(fmt_key, "srt")

    # Language
    lang = prompt("\nLanguage code (e.g. en, de, fr — blank = auto-detect)", "").strip() or None

    print()
    info(f"Loading model '{model_name}'...")
    info("Transcribing — this may take a moment for longer files...\n")

    try:
        import whisper
        model  = whisper.load_model(model_name)
        result = model.transcribe(raw, language=lang, verbose=False)
    except Exception as e:
        err(f"Transcription failed: {e}")
        back_to_menu(); return

    base      = os.path.splitext(os.path.basename(raw))[0]
    out_dir   = _dirs.DIR_AUDIO
    os.makedirs(out_dir, exist_ok=True)
    saved     = []
    fmts_out  = ["srt", "vtt", "txt"] if out_fmt == "all" else [out_fmt]

    for fmt in fmts_out:
        path = os.path.join(out_dir, f"{base}.{fmt}")
        if fmt == "txt":
            with open(path, "w", encoding="utf-8") as f:
                f.write(result["text"].strip())
        elif fmt == "srt":
            with open(path, "w", encoding="utf-8") as f:
                f.write(_to_srt(result["segments"]))
        elif fmt == "vtt":
            with open(path, "w", encoding="utf-8") as f:
                f.write(_to_vtt(result["segments"]))
        saved.append(path)
        ok(f"Saved {fmt.upper()}: {path}")

    # Print transcript preview
    preview = result["text"].strip()[:300]
    print(f"\n  {_T.DIM}Preview:{_T.R}")
    for line in preview.split("\n")[:6]:
        print(f"  {line}")
    if len(result["text"]) > 300:
        print(f"  {_T.DIM}... ({len(result['text'])} chars total){_T.R}")

    detected = result.get("language", "unknown")
    print()
    ok(f"Language detected: {detected}")
    ok(f"Duration: {result['segments'][-1]['end']:.1f}s  |  {len(result['segments'])} segments")

    back_to_menu()


# ── Subtitle format converters ─────────────────────────────────────────────────

def _fmt_time_srt(t: float) -> str:
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def _fmt_time_vtt(t: float) -> str:
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def _to_srt(segments) -> str:
    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{_fmt_time_srt(seg['start'])} --> {_fmt_time_srt(seg['end'])}")
        lines.append(seg["text"].strip())
        lines.append("")
    return "\n".join(lines)


def _to_vtt(segments) -> str:
    lines = ["WEBVTT", ""]
    for seg in segments:
        lines.append(f"{_fmt_time_vtt(seg['start'])} --> {_fmt_time_vtt(seg['end'])}")
        lines.append(seg["text"].strip())
        lines.append("")
    return "\n".join(lines)
