"""
main.py — EditorSuite entry point
Run with:  python main.py

Navigation:  Main → category (1-6) → tool (1-5)
             Enter = stay in category  |  b = Home  |  q = quit
"""

import sys
import os
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
    from utils.config import load_config, get_my_username, set_my_username
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
    pass   # updater errors never crash the app

# ── Tool imports ──────────────────────────────────────────────────────────────
try:
    from tools.audio_scraper     import tool_scraper
    from tools.hashtag_analyzer  import tool_caption, tool_hpa
    from tools.competitor        import tool_ct
    from tools.best_posting_time import tool_bptf
    from tools.spotify           import tool_ets
    from tools.compressor        import tool_compress, tool_bulkcompress
    from tools.downloader        import tool_dlvideo, tool_downloader
    from tools.cross_hashtag     import tool_crosshash
    from tools.viral_finder      import tool_viral
    from tools.calendar          import tool_calendar
    from tools.audio_tools       import tool_audioextract, tool_speed
    from tools.hashtag_suggester import tool_hashsugg
    from tools.engagement        import tool_engagerate
    from tools.niche_report      import tool_nichereport
    from tools.bg_remover        import tool_bgremove
    from tools.growth_tracker    import tool_growthtrack
    from tools.content_planner   import tool_caption_writer, tool_content_ideas
    from tools.music_downloader  import tool_music_dl, tool_playlist_dl
    from tools.video_trimmer     import tool_trimmer
    from tools.captions          import tool_captions
    from tools.creator_tools     import tool_merge, tool_thumbnail, tool_bulkrename
    from tools.trending          import tool_trending
    from ui.settings             import tool_settings
except Exception as e:
    print(f"\n  [ERROR] Failed to import a tool:\n  {e}\n")
    traceback.print_exc()
    input("\n  Press Enter to exit...")
    sys.exit(1)

from utils.helpers import show_banner, BackToCategory, BackToMain, Quit, clear_screen
from ui.menu       import build_menu, build_category, CATEGORIES

# ── Tool registry ─────────────────────────────────────────────────────────────
TOOLS = {
    # 1 — SCRAPERS
    (1, 1): tool_scraper,
    (1, 2): tool_caption,       # Hashtag Frequency
    (1, 3): tool_crosshash,
    (1, 4): tool_viral,
    (1, 5): tool_hashsugg,

    # 2 — ANALYZERS
    (2, 1): tool_hpa,
    (2, 2): tool_ct,
    (2, 3): tool_bptf,
    (2, 4): tool_engagerate,
    (2, 5): tool_nichereport,

    # 3 — PLANNERS
    (3, 1): tool_ets,
    (3, 2): tool_calendar,
    (3, 3): tool_growthtrack,
    (3, 4): tool_caption_writer,
    (3, 5): tool_content_ideas,

    # 4 — DOWNLOADERS
    (4, 1): tool_dlvideo,
    (4, 2): tool_downloader,
    (4, 3): tool_playlist_dl,
    (4, 4): tool_music_dl,
    (4, 5): tool_audioextract,

    # 5 — VIDEO TOOLS
    (5, 1): tool_compress,
    (5, 2): tool_speed,
    (5, 3): tool_bgremove,
    (5, 4): tool_bulkcompress,
    (5, 5): tool_trimmer,

    # 6 — CREATOR TOOLS
    (6, 1): tool_captions,
    (6, 2): tool_merge,
    (6, 3): tool_thumbnail,
    (6, 4): tool_bulkrename,
    (6, 5): tool_trending,
}

_N_CATS = len(CATEGORIES)   # 6


# ── Input ─────────────────────────────────────────────────────────────────────
def _input(prompt_str: str = "  > ") -> str:
    try:
        from prompt_toolkit import prompt as pt_prompt
        from prompt_toolkit.styles import Style
        style = Style.from_dict({"": "#ffffff"})
        return pt_prompt(prompt_str, style=style).strip().lower()
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
            print(f"\n  {GREEN}[v]{R} Saved as @{u}")
            time.sleep(0.8)

    while True:
        # ── Step 1: pick a category ───────────────────────────────────────────
        show_banner()
        print(build_menu())
        cat_raw = _input()
        print()

        if cat_raw in ("q", "quit", "exit"):
            if load_config().get("confirm_on_exit"):
                if input(f"  Quit? [y/N]: ").strip().lower() != "y":
                    continue
            print(f"  {DIM}Goodbye.{R}\n")
            break

        if cat_raw == "s":
            try:
                tool_settings()
            except (BackToCategory, BackToMain):
                pass
            except Quit:
                break
            except KeyboardInterrupt:
                pass
            continue

        if not (cat_raw.isdigit() and 1 <= int(cat_raw) <= _N_CATS):
            print(f"  {RED}Pick a category 1-{_N_CATS}, S for Settings, or q to quit.{R}")
            time.sleep(1.2)
            continue

        cat_idx = int(cat_raw)

        # ── Step 2: pick a tool ───────────────────────────────────────────────
        while True:
            _show_submenu(cat_idx)
            tool_raw = _input()
            print()

            if tool_raw in ("b", "back"):
                break

            if tool_raw in ("q", "quit", "exit"):
                print(f"  {DIM}Goodbye.{R}\n")
                return

            if not (tool_raw.isdigit() and 1 <= int(tool_raw) <= 5):
                print(f"  {RED}Pick 1-5, or b for Home.{R}")
                time.sleep(1.0)
                continue

            tool_idx = int(tool_raw)
            try:
                _run_tool(cat_idx, tool_idx)
            except BackToCategory:
                pass        # redraw submenu
            except BackToMain:
                break       # back to category screen
            except Quit:
                print(f"  {DIM}Goodbye.{R}\n")
                return


if __name__ == "__main__":
    main()
