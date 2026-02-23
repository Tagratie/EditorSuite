"""
ui/theme.py
Color themes, global ANSI color vars, and banner renderer.
_apply_theme() mutates module-level vars — all other modules
read colors via  `from ui import theme as _T; _T.CYAN`
so they always see the live value after a theme change.
"""

# ── Theme palette definitions ─────────────────────────────────────────────────
THEMES = {
    "default": dict(accent="\033[96m", good="\033[92m", warn="\033[93m",
                    err="\033[91m",  special="\033[95m", white="\033[97m",
                    banner="\033[96m", dim="\033[2m", bold="\033[1m", reset="\033[0m"),
    "neon":    dict(accent="\033[95m", good="\033[92m", warn="\033[96m",
                    err="\033[91m",  special="\033[93m", white="\033[97m",
                    banner="\033[95m", dim="\033[2m", bold="\033[1m", reset="\033[0m"),
    "minimal": dict(accent="\033[97m", good="\033[97m", warn="\033[90m",
                    err="\033[97m",  special="\033[97m", white="\033[97m",
                    banner="\033[97m", dim="\033[2m", bold="\033[1m", reset="\033[0m"),
    "sunset":  dict(accent="\033[91m", good="\033[93m", warn="\033[91m",
                    err="\033[31m",  special="\033[33m", white="\033[97m",
                    banner="\033[91m", dim="\033[2m", bold="\033[1m", reset="\033[0m"),
    "matrix":  dict(accent="\033[32m", good="\033[92m", warn="\033[32m",
                    err="\033[92m",  special="\033[32m", white="\033[92m",
                    banner="\033[92m", dim="\033[2m", bold="\033[1m", reset="\033[0m"),
    "ocean":   dict(accent="\033[34m", good="\033[36m", warn="\033[94m",
                    err="\033[91m",  special="\033[96m", white="\033[97m",
                    banner="\033[94m", dim="\033[2m", bold="\033[1m", reset="\033[0m"),
}

# ── Live color globals (reassigned by _apply_theme) ───────────────────────────
R       = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
MAGENTA = "\033[95m"
WHITE   = "\033[97m"


def _apply_theme(name: str) -> None:
    """Update module-level color vars to match the chosen theme."""
    global R, BOLD, DIM, CYAN, GREEN, YELLOW, RED, MAGENTA, WHITE
    t       = THEMES.get(name, THEMES["default"])
    R       = t["reset"]
    BOLD    = t["bold"]
    DIM     = t["dim"]
    CYAN    = t["accent"]
    GREEN   = t["good"]
    YELLOW  = t["warn"]
    RED     = t["err"]
    MAGENTA = t["special"]
    WHITE   = t["white"]


# ── Logo styles ───────────────────────────────────────────────────────────────
LOGOS = {
    "big": (
        "  \033[1m███████╗██████╗ ██╗████████╗ ██████╗ ██████╗"
        "     ███████╗██╗   ██╗██╗████████╗███████╗\033[0m\n"
        "  \033[1m██╔════╝██╔══██╗██║╚══██╔══╝██╔═══██╗██╔══██╗"
        "    ██╔════╝██║   ██║██║╚══██╔══╝██╔════╝\033[0m\n"
        "  \033[1m█████╗  ██║  ██║██║   ██║   ██║   ██║██████╔╝"
        "    ███████╗██║   ██║██║   ██║   █████╗  \033[0m\n"
        "  \033[1m██╔══╝  ██║  ██║██║   ██║   ██║   ██║██╔══██╗"
        "    ╚════██║██║   ██║██║   ██║   ██╔══╝  \033[0m\n"
        "  \033[1m███████╗██████╔╝██║   ██║   ╚██████╔╝██║  ██║"
        "    ███████║╚██████╔╝██║   ██║   ███████╗\033[0m\n"
        "  \033[1m╚══════╝╚═════╝ ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝"
        "    ╚══════╝ ╚═════╝ ╚═╝   ╚═╝   ╚══════╝\033[0m"
    ),
    "compact": (
        "  \033[1m┌────────────────────────────────────────────┐\033[0m\n"
        "  \033[1m│   EDITOR SUITE  //  TikTok Research Kit   │\033[0m\n"
        "  \033[1m└────────────────────────────────────────────┘\033[0m"
    ),
    "text": "  \033[1mEDITOR SUITE  —  TikTok Research Kit\033[0m",
    "none": "",
}


def build_banner() -> str:
    """Return the full banner string using the current theme + logo setting."""
    from utils.config import load_config
    cfg  = load_config()
    logo = LOGOS.get(cfg.get("logo_style", "big"), LOGOS["big"])
    t    = THEMES.get(cfg.get("theme", "default"), THEMES["default"])
    bc, rs = t["banner"], t["reset"]
    return ("\n" + bc + logo + rs + "\n") if logo else "\n"
