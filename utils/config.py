"""
utils/config.py
Pure config I/O — no UI or color dependencies.
"""
import os
import json

SCRIPT_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # editorsuite/
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")

DEFAULTS = {
    "my_username":           "",
    "theme":                 "default",
    "logo_style":            "big",
    "root_dir":              os.path.join(SCRIPT_DIR, "EditorSuite_Output"),
    # Per-category dir overrides (empty = use default subfolder)
    "dir_sounds":            "",
    "dir_hashtags":          "",
    "dir_viral":             "",
    "dir_compete":           "",
    "dir_analysis":          "",
    "dir_downloads":         "",
    "dir_audio":             "",
    "dir_compress":          "",
    "dir_images":            "",
    "dir_logs":              "",
    # Scraping defaults
    "default_videos":        "500",
    "default_top_n":         "50",
    "default_quality":       "best",
    "default_hb_preset":     "Best",
    "scroll_delay":          "2.0",
    "stale_limit":           "8",
    # Behaviour
    "auto_open_folder":      False,
    "compact_menu":          False,
    "show_file_size":        True,
    "confirm_on_exit":       False,
    # Services
    "spotify_client_id":     "",
    "spotify_client_secret": "",
}


def load_config() -> dict:
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, encoding="utf-8") as f:
                data = json.load(f)
            return {**DEFAULTS, **data}
    except Exception:
        pass
    return dict(DEFAULTS)


def save_config(data: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_my_username() -> str:
    return load_config().get("my_username", "")


def set_my_username(username: str) -> str:
    username = username.lstrip("@").strip()
    cfg = load_config()
    cfg["my_username"] = username
    save_config(cfg)
    return username
