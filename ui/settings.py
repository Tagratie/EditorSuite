"""
ui/settings.py
Settings menu — launched by pressing S from the main menu.
All 20 options: appearance, directories, defaults, behaviour, account, files, reset.
"""
import os
import sys
import time
from datetime import datetime

from ui import theme as _T
from utils.config import load_config, save_config, DEFAULTS, SCRIPT_DIR
from utils.dirs import _init_dirs
from utils import dirs as _dirs
from utils.helpers import ok, err, warn, clear_screen, back_to_menu


def tool_settings():
    while True:
        cfg   = load_config()
        t     = _T.THEMES.get(cfg.get("theme", "default"), _T.THEMES["default"])
        bc    = t["banner"]; rs = t["reset"]
        C, B, r, D, W = _T.CYAN, _T.BOLD, _T.R, _T.DIM, _T.WHITE

        clear_screen()
        print(f"\n{bc}{B}  EDITOR SUITE — SETTINGS{rs}\n")

        ao  = cfg.get("auto_open_folder", False)
        cm  = cfg.get("compact_menu",     False)
        sfs = cfg.get("show_file_size",   True)
        ce  = cfg.get("confirm_on_exit",  False)
        cid = cfg.get("spotify_client_id", "")
        un  = cfg.get("my_username", "") or "not set"

        def flag(v): return f"{_T.GREEN}ON{r}" if v else f"{D}OFF{r}"

        print(f"  {B}APPEARANCE{r}")
        print(f"    {C}1{r}  Theme         [{B}{cfg.get('theme','default')}{r}]"
              f"  {D}default / neon / minimal / sunset / matrix / ocean{r}")
        print(f"    {C}2{r}  Logo style    [{B}{cfg.get('logo_style','big')}{r}]"
              f"  {D}big / compact / text / none{r}")

        print(f"\n  {B}DIRECTORIES{r}")
        print(f"    {C}3{r}  Root output folder")
        print(f"         {D}{cfg.get('root_dir','')}{r}")
        print(f"    {C}4{r}  Per-category folder overrides  "
              f"{D}(sounds, hashtags, viral, downloads…){r}")

        print(f"\n  {B}SCRAPING DEFAULTS{r}")
        print(f"    {C}5{r}  Videos to scan      [{D}{cfg.get('default_videos','500')}{r}]")
        print(f"    {C}6{r}  Top N results        [{D}{cfg.get('default_top_n','50')}{r}]")
        print(f"    {C}7{r}  Download quality     [{D}{cfg.get('default_quality','best')}{r}]")
        print(f"    {C}8{r}  Scroll delay (s)     [{D}{cfg.get('scroll_delay','2.0')}{r}]")
        print(f"    {C}9{r}  Stale scroll limit   [{D}{cfg.get('stale_limit','8')}{r}]")
        print(f"    {C}10{r} HandBrake preset     [{D}{cfg.get('default_hb_preset','Best')}{r}]")

        print(f"\n  {B}BEHAVIOUR{r}")
        print(f"    {C}11{r} Auto-open folder after save  [{flag(ao)}]")
        print(f"    {C}12{r} Compact menu (hide 12–20)    [{flag(cm)}]")
        print(f"    {C}13{r} Show file size after save    [{flag(sfs)}]")
        print(f"    {C}14{r} Confirm before quit          [{flag(ce)}]")

        print(f"\n  {B}ACCOUNT & SERVICES{r}")
        print(f"    {C}15{r} TikTok username    {D}[@{un}]{r}")
        print(f"    {C}16{r} Spotify credentials {D}[{'set' if cid else 'not set'}]{r}")
        print(f"    {C}17{r} Clear Spotify cache and credentials")

        print(f"\n  {B}FILE BROWSER{r}")
        print(f"    {C}18{r} Open root output folder in Explorer/Finder")
        print(f"    {C}19{r} Browse all saved files by category")

        print(f"\n  {B}MAINTENANCE{r}")
        print(f"    {C}20{r} Reset ALL settings to defaults")

        print(f"\n  {D}Enter a number to change, or q to go back.{r}\n")
        choice = input(f"  {C}>{r} ").strip().lower()

        if choice in ("q", ""):
            _apply_theme_and_dirs(cfg)
            break

        elif choice == "1":
            _opt_theme(cfg)
        elif choice == "2":
            _opt_logo(cfg)
        elif choice == "3":
            _opt_root_dir(cfg)
        elif choice == "4":
            _opt_subfolders(cfg)
        elif choice == "5":
            _opt_str(cfg, "default_videos",    "Videos to scan",    is_int=True)
        elif choice == "6":
            _opt_str(cfg, "default_top_n",     "Top N results",     is_int=True)
        elif choice == "7":
            _opt_quality(cfg)
        elif choice == "8":
            _opt_float(cfg, "scroll_delay",    "Scroll delay (seconds)")
        elif choice == "9":
            _opt_str(cfg, "stale_limit",       "Stale scroll limit", is_int=True)
        elif choice == "10":
            _opt_str(cfg, "default_hb_preset", "HandBrake preset name")
        elif choice == "11":
            _opt_toggle(cfg, "auto_open_folder", "Auto-open folder")
        elif choice == "12":
            _opt_toggle(cfg, "compact_menu",     "Compact menu")
        elif choice == "13":
            _opt_toggle(cfg, "show_file_size",   "Show file size")
        elif choice == "14":
            _opt_toggle(cfg, "confirm_on_exit",  "Confirm on exit")
        elif choice == "15":
            _opt_username(cfg)
        elif choice == "16":
            _opt_spotify(cfg)
        elif choice == "17":
            _opt_clear_spotify(cfg)
        elif choice == "18":
            _opt_open_folder(cfg)
        elif choice == "19":
            _opt_browse_files()
        elif choice == "20":
            _opt_reset()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _apply_theme_and_dirs(cfg):
    _T._apply_theme(cfg.get("theme", "default"))
    _init_dirs()


def _opt_theme(cfg):
    options = " / ".join(_T.THEMES.keys())
    print(f"\n  Available: {_T.CYAN}{options}{_T.R}\n")
    for name, th in _T.THEMES.items():
        print(f"    {th['banner']}{th['bold']}{name:<10}{th['reset']}  "
              f"{th['good']}good{th['reset']}  {th['warn']}warn{th['reset']}  "
              f"{th['accent']}accent{th['reset']}")
    cur = cfg.get("theme", "default")
    v   = input(f"\n  {_T.CYAN}>{_T.R} Theme name [{cur}]: ").strip() or cur
    if v in _T.THEMES:
        cfg["theme"] = v
        save_config(cfg)
        _T._apply_theme(v)
        ok(f"Theme set to '{v}'")
    else:
        err(f"Unknown theme. Options: {options}")
    time.sleep(1)


def _opt_logo(cfg):
    print(f"\n  Styles: {_T.CYAN}big / compact / text / none{_T.R}")
    cur = cfg.get("logo_style", "big")
    v   = input(f"  {_T.CYAN}>{_T.R} Logo style [{cur}]: ").strip() or cur
    if v in _T.LOGOS:
        cfg["logo_style"] = v
        save_config(cfg)
        ok(f"Logo set to '{v}'")
    else:
        err("Unknown style.")
    time.sleep(1)


def _opt_root_dir(cfg):
    print(f"\n  {_T.DIM}Current: {cfg.get('root_dir', '')}{_T.R}")
    print(f"  {_T.DIM}Drag a folder here or type a full path.{_T.R}")
    v = input(f"  {_T.CYAN}>{_T.R} New root folder: ").strip().strip('"').strip("'")
    if v:
        cfg["root_dir"] = v
        save_config(cfg)
        _init_dirs()
        ok(f"Root folder: {v}")
    time.sleep(1.2)


def _opt_subfolders(cfg):
    subfolders = [
        ("dir_sounds",    "Trending sounds reports   "),
        ("dir_hashtags",  "Hashtag frequency reports "),
        ("dir_viral",     "Viral video reports       "),
        ("dir_compete",   "Competitor reports        "),
        ("dir_analysis",  "Analysis (BPTF, calendar) "),
        ("dir_downloads", "Video downloads           "),
        ("dir_audio",     "Extracted audio           "),
        ("dir_compress",  "Compressed videos         "),
        ("dir_images",    "Background-removed images "),
        ("dir_logs",      "Logs & tracking data      "),
    ]
    clear_screen()
    print(f"\n  {_T.BOLD}PER-CATEGORY FOLDER OVERRIDES{_T.R}")
    print(f"  {_T.DIM}Leave blank to keep default subfolder inside root.{_T.R}\n")
    for key, label in subfolders:
        cur = cfg.get(key, "")
        print(f"  {_T.CYAN}{label}{_T.R}  {_T.DIM}current: {cur if cur else '(auto)'}{_T.R}")
        v = input(f"  {_T.CYAN}>{_T.R} New path (blank = keep): ").strip().strip('"').strip("'")
        if v:
            cfg[key] = v
        elif not v and cfg.get(key):
            if input(f"  {_T.DIM}Clear override? [y/N]: {_T.R}").strip().lower() == "y":
                cfg[key] = ""
    save_config(cfg)
    _init_dirs()
    ok("Folder overrides saved.")
    time.sleep(1.2)


def _opt_str(cfg, key, label, is_int=False):
    cur = cfg.get(key, DEFAULTS.get(key, ""))
    v   = input(f"  {_T.CYAN}>{_T.R} {label} [{cur}]: ").strip() or cur
    if is_int and not v.isdigit():
        err("Must be a whole number.")
    else:
        cfg[key] = v
        save_config(cfg)
        ok("Saved.")
    time.sleep(0.7)


def _opt_float(cfg, key, label):
    cur = cfg.get(key, DEFAULTS.get(key, ""))
    v   = input(f"  {_T.CYAN}>{_T.R} {label} [{cur}]: ").strip() or cur
    try:
        float(v)
        cfg[key] = v
        save_config(cfg)
        ok("Saved.")
    except ValueError:
        err("Must be a number (e.g. 2.0).")
    time.sleep(0.7)


def _opt_quality(cfg):
    print(f"  {_T.DIM}Options: best / 1080 / 720 / 480{_T.R}")
    cur = cfg.get("default_quality", "best")
    v   = input(f"  {_T.CYAN}>{_T.R} Default quality [{cur}]: ").strip() or cur
    cfg["default_quality"] = v
    save_config(cfg)
    ok("Saved.")
    time.sleep(0.7)


def _opt_toggle(cfg, key, label):
    cfg[key] = not cfg.get(key, DEFAULTS.get(key, False))
    save_config(cfg)
    ok(f"{label}: {'ON' if cfg[key] else 'OFF'}")
    time.sleep(0.7)


def _opt_username(cfg):
    cur = cfg.get("my_username", "") or "not set"
    v   = input(f"  {_T.CYAN}>{_T.R} TikTok username (no @) [{cur}]: ").strip().lstrip("@") or cur
    if v and v != "not set":
        cfg["my_username"] = v
        save_config(cfg)
        ok(f"Username set to @{v}")
    time.sleep(0.7)


def _opt_spotify(cfg):
    cid = cfg.get("spotify_client_id", "")
    print(f"\n  {_T.DIM}Get these from https://developer.spotify.com/dashboard{_T.R}")
    new_cid  = input(f"  {_T.CYAN}>{_T.R} Client ID [{'set' if cid else 'not set'}]: ").strip() or cid
    new_csec = input(f"  {_T.CYAN}>{_T.R} Client Secret: ").strip() or cfg.get("spotify_client_secret", "")
    cfg["spotify_client_id"]     = new_cid
    cfg["spotify_client_secret"] = new_csec
    os.makedirs(_dirs.DIR_LOGS, exist_ok=True)
    creds_path = os.path.join(_dirs.DIR_LOGS, "spotify_creds.txt")
    with open(creds_path, "w", encoding="utf-8") as f:
        f.write(new_cid + "\n" + new_csec + "\n")
    save_config(cfg)
    ok("Spotify credentials saved.")
    time.sleep(1)


def _opt_clear_spotify(cfg):
    for p in [
        os.path.join(SCRIPT_DIR, ".spotify_cache"),
        os.path.join(_dirs.DIR_LOGS, "spotify_creds.txt"),
        os.path.join(_dirs.OUTPUT_DIR, "spotify_creds.txt"),
    ]:
        if os.path.exists(p):
            os.remove(p)
            ok(f"Deleted: {p}")
    cfg["spotify_client_id"] = ""
    cfg["spotify_client_secret"] = ""
    save_config(cfg)
    ok("Spotify data cleared.")
    time.sleep(1.2)


def _opt_open_folder(cfg):
    import subprocess
    folder = cfg.get("root_dir", _dirs.OUTPUT_DIR)
    try:
        if os.name == "nt":
            subprocess.Popen(f'explorer "{folder}"', shell=True)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
    except Exception as e:
        err(str(e))
    time.sleep(0.5)


def _opt_browse_files():
    clear_screen()
    cats = [
        ("Trending Sounds",    _dirs.DIR_SOUNDS),
        ("Hashtag Reports",    _dirs.DIR_HASHTAGS),
        ("Viral Videos",       _dirs.DIR_VIRAL),
        ("Competitor Reports", _dirs.DIR_COMPETE),
        ("Analysis",           _dirs.DIR_ANALYSIS),
        ("Downloads",          _dirs.DIR_DOWNLOADS),
        ("Audio",              _dirs.DIR_AUDIO),
        ("Compressed",         _dirs.DIR_COMPRESS),
        ("Images",             _dirs.DIR_IMAGES),
        ("Logs & Tracking",    _dirs.DIR_LOGS),
    ]
    print(f"\n  {_T.BOLD}ALL SAVED FILES{_T.R}\n")
    grand_total = grand_size = 0

    for label, path in cats:
        if not os.path.isdir(path):
            continue
        files = []
        for root, dirs, fnames in os.walk(path):
            for fn in fnames:
                fp = os.path.join(root, fn)
                sz = os.path.getsize(fp)
                mt = os.path.getmtime(fp)
                files.append((mt, fn, fp, sz))
        if not files:
            continue
        files.sort(reverse=True)
        cat_size     = sum(f[3] for f in files)
        grand_total += len(files)
        grand_size  += cat_size
        sz_str = f"{cat_size/1024:.0f} KB" if cat_size < 1024*1024 else f"{cat_size/1024/1024:.1f} MB"
        print(f"  {_T.CYAN}{_T.BOLD}{label}{_T.R}  {_T.DIM}{len(files)} files, {sz_str}{_T.R}")
        for mt, fn, fp, sz in files[:6]:
            fsz  = f"{sz/1024:.0f}KB" if sz < 1024*1024 else f"{sz/1024/1024:.1f}MB"
            mstr = datetime.fromtimestamp(mt).strftime("%Y-%m-%d %H:%M")
            print(f"    {_T.DIM}{mstr}{_T.R}  {fn[:52]:<52}  {_T.DIM}{fsz:>7}{_T.R}")
        if len(files) > 6:
            print(f"    {_T.DIM}... and {len(files)-6} more{_T.R}")
        print()

    gs_str = f"{grand_size/1024/1024:.1f} MB" if grand_size > 1024*1024 else f"{grand_size/1024:.0f} KB"
    print(f"  {_T.DIM}Total: {grand_total} files, {gs_str}{_T.R}")
    input(f"\n  {_T.DIM}Press Enter to go back...{_T.R}")


def _opt_reset():
    v = input(f"  {_T.YELLOW}Reset ALL settings to defaults? [yes/no]: {_T.R}").strip().lower()
    if v == "yes":
        save_config(dict(DEFAULTS))
        _T._apply_theme("default")
        _init_dirs()
        ok("Settings reset to defaults.")
    time.sleep(1)
