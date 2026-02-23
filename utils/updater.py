"""
utils/updater.py
Silent background updater — runs once per day on startup.
Updates yt-dlp (via yt-dlp --update) and spotdl (via pip).
State tracked in DIR_LOGS/last_update.json.
"""
import json
import os
import subprocess
import sys
import threading
from datetime import date


_UPDATE_FILE = None   # resolved lazily after dirs init


def _update_file() -> str:
    from utils import dirs as _dirs
    return os.path.join(_dirs.DIR_LOGS, "last_update.json")


def _last_update() -> str:
    try:
        with open(_update_file(), encoding="utf-8") as f:
            return json.load(f).get("date", "")
    except Exception:
        return ""


def _save_update() -> None:
    try:
        os.makedirs(os.path.dirname(_update_file()), exist_ok=True)
        with open(_update_file(), "w", encoding="utf-8") as f:
            json.dump({"date": str(date.today())}, f)
    except Exception:
        pass


def _do_update() -> None:
    """Runs in a daemon thread — completely silent, never blocks startup."""
    try:
        # yt-dlp self-update
        subprocess.run(
            ["yt-dlp", "--update"],
            capture_output=True,
            timeout=30,
        )
    except Exception:
        pass

    try:
        # spotdl via pip (handles pkg_resources issues too)
        subprocess.run(
            [sys.executable, "-m", "pip", "install",
             "--upgrade", "spotdl", "setuptools", "--quiet"],
            capture_output=True,
            timeout=60,
        )
    except Exception:
        pass

    _save_update()


def check_and_update() -> None:
    """
    Call once at startup.  If today's date differs from last update,
    spin up a daemon thread to update tools in the background.
    The user never waits — they're already looking at the main menu.
    """
    if _last_update() == str(date.today()):
        return   # already updated today

    t = threading.Thread(target=_do_update, daemon=True, name="EditorSuite-Updater")
    t.start()
