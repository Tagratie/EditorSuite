"""
main.py — EditorSuite entry point
Run with:  python main.py

Navigation:
  Main screen  →  1-4 to pick category  |  S = Settings  |  Esc = quit
  Submenu      →  1-N to pick tool       |  Esc = back to Home
  After tool   →  Enter = stay in category  |  b/Esc = Home  |  q = quit
"""

import sys
import os
import subprocess
import traceback
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ── Bootstrap ─────────────────────────────────────────────────────────────────
try:
    from utils.config import load_config, save_config, get_my_username, set_my_username
    from utils.dirs   import _init_dirs
    from ui.theme     import _apply_theme, CYAN, BOLD, DIM, YELLOW, RED, GREEN, R

    _boot_cfg = load_config()
    _apply_theme(_boot_cfg.get("theme", "default"))
    _init_dirs()
except Exception as e:
    print(f"\n  [ERROR] Startup failed:\n  {e}\n")
    traceback.print_exc()
    input("\n  Press Enter to exit...")
    sys.exit(1)

# ── Background updater (silent, once per day) ─────────────────────────────────
try:
    from utils.updater import check_and_update
    check_and_update()
except Exception:
    pass

# ── First-run: install Playwright Chromium if missing ─────────────────────────
def _ensure_playwright() -> None:
    cfg = load_config()
    if cfg.get("playwright_ready"):
        return
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            b.close()
        cfg["playwright_ready"] = True
        save_config(cfg)
        return
    except Exception:
        pass
    os.system("cls" if os.name == "nt" else "clear")
    print(f"\n  {CYAN}{BOLD}First-time setup{R}")
    print(f"  {DIM}Installing Chromium (~170 MB) — only happens once.{R}\n")
    ret = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
    if ret.returncode == 0:
        print(f"\n  {GREEN}[+]{R} Chromium ready.\n")
        cfg["playwright_ready"] = True
        save_config(cfg)
        time.sleep(1)
    else:
        print(f"\n  {YELLOW}[!]{R} Chromium install failed — scraper tools won't work.\n")
        time.sleep(3)

_ensure_playwright()

# ── Tool imports ──────────────────────────────────────────────────────────────
try:
    from tools.audio_scraper     import tool_scraper
    from tools.hashtag_analyzer  import tool_caption, tool_hpa
    from tools.competitor        import tool_ct
    from tools.best_posting_time import tool_bptf
    from tools.spotify           import tool_ets
    from tools.compressor        import tool_compress, tool_bulkcompress
    from tools.downloader        import tool_dlvideo, tool_profile_playlist
    from tools.cross_hashtag     import tool_crosshash
    from tools.viral_finder      import tool_viral
    from tools.calendar          import tool_calendar
    from tools.audio_tools       import tool_audioextract
    from tools.engagement        import tool_engagerate
    from tools.niche_report      import tool_nichereport
    from tools.bg_remover        import tool_bgremove
    from tools.growth_tracker    import tool_growthtrack
    from tools.music_downloader  import tool_music_dl
    from tools.trending          import tool_trending
    from ui.settings             import tool_settings
except Exception as e:
    print(f"\n  [ERROR] Failed to import a tool:\n  {e}\n")
    traceback.print_exc()
    input("\n  Press Enter to exit...")
    sys.exit(1)

from utils.helpers import show_banner, BackToCategory, BackToMain, Quit, clear_screen
from ui.menu       import build_menu, build_category, CATEGORIES

_ESC = "__esc__"   # sentinel returned by _input() when Escape is pressed

# ── Tool registry ─────────────────────────────────────────────────────────────
TOOLS = {
    # 1 — SCRAPERS (6)
    (1, 1): tool_scraper,
    (1, 2): tool_caption,       # Hashtag Frequency
    (1, 3): tool_crosshash,
    (1, 4): tool_viral,
    (1, 5): tool_trending,
    (1, 6): tool_ets,

    # 2 — ANALYTICS (6)
    (2, 1): tool_hpa,
    (2, 2): tool_ct,
    (2, 3): tool_bptf,
    (2, 4): tool_engagerate,
    (2, 5): tool_nichereport,
    (2, 6): tool_growthtrack,

    # 3 — DOWNLOADERS (4)
    (3, 1): tool_dlvideo,
    (3, 2): tool_profile_playlist,
    (3, 3): tool_music_dl,
    (3, 4): tool_audioextract,

    # 4 — STUDIO (4)
    (4, 1): tool_compress,
    (4, 2): tool_bulkcompress,
    (4, 3): tool_bgremove,
    (4, 4): tool_calendar,
}

_N_CATS = len(CATEGORIES)   # 4


# ── Input — Escape-aware ──────────────────────────────────────────────────────
def _input(prompt_str: str = "  > ") -> str:
    """
    Returns the stripped lowercase input, or __esc__ if Escape was pressed.
    Uses prompt_toolkit when available for Escape detection.
    Falls back to plain input() — Escape won't be caught but app still works.
    """
    try:
        from prompt_toolkit import prompt as pt_prompt
        from prompt_toolkit.keys import Keys
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.styles import Style

        kb = KeyBindings()
        _escaped = [False]

        @kb.add(Keys.Escape)
        def _esc(event):
            _escaped[0] = True
            event.app.current_buffer.text = _ESC
            event.app.exit(result=_ESC)

        style = Style.from_dict({"": "#ffffff"})
        result = pt_prompt(prompt_str, key_bindings=kb, style=style)
        if _escaped[0] or result == _ESC:
            return _ESC
        return result.strip().lower()
    except Exception:
        return input(prompt_str).strip().lower()


def _show_submenu(cat_idx: int) -> None:
    clear_screen()
    print()
    print(build_category(cat_idx))
    print()


def _run_tool(cat_idx: int, tool_idx: int) -> None:
    fn = TOOLS.get((cat_idx, tool_idx))
    if not fn:
        return
    try:
        fn()
    except (BackToCategory, BackToMain, Quit):
        raise
    except KeyboardInterrupt:
        print(f"\n\n  {YELLOW}Interrupted.{R}")
        from utils.helpers import back_to_menu
        back_to_menu()
    except Exception:
        print()
        traceback.print_exc()
        from utils.helpers import back_to_menu
        back_to_menu()


# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    # First-run username setup
    if not get_my_username():
        show_banner()
        print(f"  {CYAN}{BOLD}Welcome to EditorSuite!{R}")
        print(f"  {DIM}Enter your TikTok username once — saved for all tools.{R}\n")
        u = input(f"  {CYAN}>{R} TikTok username (no @): ").strip().lstrip("@")
        if u:
            set_my_username(u)
            print(f"\n  {GREEN}[+]{R} Saved as @{u}")
            time.sleep(0.8)

    while True:
        # ── Main screen ───────────────────────────────────────────────────────
        show_banner()
        print(build_menu())
        cat_raw = _input()
        print()

        if cat_raw == _ESC:
            # Esc on home screen = quit
            if load_config().get("confirm_on_exit"):
                if input(f"  Quit? [y/N]: ").strip().lower() != "y":
                    continue
            print(f"  {DIM}Goodbye.{R}\n")
            break

        if cat_raw in ("q", "quit", "exit"):
            print(f"  {DIM}Goodbye.{R}\n")
            break

        if cat_raw == "s":
            try:
                tool_settings()
            except (BackToCategory, BackToMain, Quit):
                pass
            except KeyboardInterrupt:
                pass
            continue

        if not (cat_raw.isdigit() and 1 <= int(cat_raw) <= _N_CATS):
            print(f"  {RED}Pick 1-{_N_CATS}, S for Settings, or Esc to quit.{R}")
            time.sleep(1.2)
            continue

        cat_idx = int(cat_raw)

        # ── Submenu ───────────────────────────────────────────────────────────
        while True:
            _show_submenu(cat_idx)
            tool_raw = _input()
            print()

            if tool_raw == _ESC:
                break   # Esc = back to home

            if tool_raw in ("b", "back"):
                break

            if tool_raw in ("q", "quit", "exit"):
                print(f"  {DIM}Goodbye.{R}\n")
                return

            cat_size = len(CATEGORIES[cat_idx - 1][1])
            if not (tool_raw.isdigit() and 1 <= int(tool_raw) <= cat_size):
                print(f"  {RED}Pick 1-{cat_size}, or Esc for Home.{R}")
                time.sleep(1.0)
                continue

            tool_idx = int(tool_raw)
            try:
                _run_tool(cat_idx, tool_idx)
            except BackToCategory:
                pass
            except BackToMain:
                break
            except Quit:
                print(f"  {DIM}Goodbye.{R}\n")
                return


if __name__ == "__main__":
    main()
