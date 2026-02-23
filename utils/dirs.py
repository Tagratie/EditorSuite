"""
utils/dirs.py
All output-directory globals in one place.
Call _init_dirs() on startup and after any settings change.
"""
import os
from utils.config import load_config, DEFAULTS

# ── Globals (module-level, mutated by _init_dirs) ─────────────────────────────
OUTPUT_DIR   = DEFAULTS["root_dir"]
PRESETS_DIR  = ""
DIR_SOUNDS   = ""
DIR_HASHTAGS = ""
DIR_VIRAL    = ""
DIR_COMPETE  = ""
DIR_ANALYSIS = ""
DIR_DOWNLOADS= ""
DIR_AUDIO    = ""
DIR_COMPRESS = ""
DIR_IMAGES   = ""
DIR_LOGS     = ""


def _init_dirs() -> None:
    """Resolve all directory paths from config and update module globals."""
    global OUTPUT_DIR, PRESETS_DIR
    global DIR_SOUNDS, DIR_HASHTAGS, DIR_VIRAL, DIR_COMPETE
    global DIR_ANALYSIS, DIR_DOWNLOADS, DIR_AUDIO, DIR_COMPRESS
    global DIR_IMAGES, DIR_LOGS

    cfg = load_config()
    OUTPUT_DIR  = cfg["root_dir"]
    PRESETS_DIR = os.path.join(OUTPUT_DIR, "handbrake_presets")

    def _d(key: str, *sub: str) -> str:
        override = cfg.get(key, "")
        return override if override else os.path.join(OUTPUT_DIR, *sub)

    DIR_SOUNDS    = _d("dir_sounds",    "reports", "sounds")
    DIR_HASHTAGS  = _d("dir_hashtags",  "reports", "hashtags")
    DIR_VIRAL     = _d("dir_viral",     "reports", "viral")
    DIR_COMPETE   = _d("dir_compete",   "reports", "competitors")
    DIR_ANALYSIS  = _d("dir_analysis",  "reports", "analysis")
    DIR_DOWNLOADS = _d("dir_downloads", "downloads")
    DIR_AUDIO     = _d("dir_audio",     "downloads", "audio")
    DIR_COMPRESS  = _d("dir_compress",  "compressed")
    DIR_IMAGES    = _d("dir_images",    "images")
    DIR_LOGS      = _d("dir_logs",      "logs")
