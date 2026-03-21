"""
utils/helpers.py
Shared display / IO helpers.

Navigation is handled via three lightweight exceptions:
    BackToCategory  — raised by back_to_menu() when user presses Enter
    BackToMain      — raised when user presses 'b'
    Quit            — raised when user presses 'q'

main.py catches these in the tool loop.  Every tool just calls
back_to_menu() at the end — no return values, no extra logic needed.
"""
import os
import re
import sys
from datetime import datetime
from ui import theme as _T


# ---------- Data parsing helpers ----------
def _coerce_int(val) -> int:
    """Best-effort parse of numeric strings like '1,234', '5.6K', '1.2M'."""
    if val is None:
        return 0
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).strip()
    if not s:
        return 0
    s = s.replace(",", "").replace("views", "").replace("view", "").strip()
    m = re.match(r"^([0-9]*\.?[0-9]+)\s*([kmb])$", s, re.IGNORECASE)
    if m:
        num = float(m.group(1))
        mult = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}[m.group(2).lower()]
        return int(num * mult)
    digits = re.findall(r"\d+", s)
    return int("".join(digits)) if digits else 0


def get_stat(item: dict, *keys: str) -> int:
    """
    Pull a stat from common TikTok response shapes.
    Checks stats/statistics/statsV2 plus direct keys, with coercion.
    """
    if not isinstance(item, dict):
        return 0
    containers = []
    for k in ("stats", "statistics", "statsV2", "stats_v2", "statistic", "statsInfo", "stats_info"):
        c = item.get(k)
        if isinstance(c, dict):
            containers.append(c)
    def _pick(d: dict, key: str):
        if key in d:
            return d.get(key)
        lk = key.lower()
        for k in d.keys():
            if isinstance(k, str) and k.lower() == lk:
                return d.get(k)
        return None

    variants = []
    for key in keys:
        variants.extend([key, f"{key}Text", f"{key}Str"])

    zero_seen = False

    def _consider(v):
        nonlocal zero_seen
        if v in (None, ""):
            return None
        val = _coerce_int(v)
        if val != 0:
            return val
        zero_seen = True
        return None

    for c in containers:
        for key in variants:
            v = _pick(c, key)
            found = _consider(v)
            if found is not None:
                return found
    for key in variants:
        v = _pick(item, key)
        found = _consider(v)
        if found is not None:
            return found

    def _search(obj, depth: int):
        if depth < 0:
            return None
        if isinstance(obj, dict):
            for key in variants:
                v = _pick(obj, key)
                if v not in (None, ""):
                    return v
            for v in obj.values():
                found = _search(v, depth - 1)
                if found not in (None, ""):
                    return found
        elif isinstance(obj, list):
            for v in obj:
                found = _search(v, depth - 1)
                if found not in (None, ""):
                    return found
        return None

    v = _search(item, 4)
    found = _consider(v)
    if found is not None:
        return found
    return 0 if zero_seen else 0


def unwrap_item(item):
    """Normalize TikTok item wrappers to the actual item struct."""
    if not isinstance(item, dict):
        return item
    if isinstance(item.get("itemStruct"), dict):
        return item.get("itemStruct")
    info = item.get("itemInfo")
    if isinstance(info, dict) and isinstance(info.get("itemStruct"), dict):
        return info.get("itemStruct")
    if isinstance(item.get("item"), dict):
        return item.get("item")
    return item


# ── Navigation signals ─────────────────────────────────────────────────────────
class BackToCategory(Exception): pass   # stay in current category submenu
class BackToMain(Exception):     pass   # return to category selection screen
class Quit(Exception):           pass   # exit the app


# ── Screen ─────────────────────────────────────────────────────────────────────
def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def clear_line() -> None:
    print(" " * 84, end="\r", flush=True)


# ── Status printers ────────────────────────────────────────────────────────────
def ok(msg: str)   -> None: print(f"  {_T.GREEN}[v]{_T.R} {msg}", flush=True)
def info(msg: str) -> None: print(f"  {_T.CYAN}[i]{_T.R} {msg}", flush=True)
def err(msg: str)  -> None: print(f"  {_T.RED}[x]{_T.R} {msg}", flush=True)
def warn(msg: str) -> None: print(f"  {_T.YELLOW}[!]{_T.R} {msg}", flush=True)


# ── Layout helpers ─────────────────────────────────────────────────────────────
def divider(label: str = "") -> None:
    if label:
        pad = max(2, (88 - len(label) - 4) // 2)
        print(f"\n  {_T.DIM}{'-'*pad}  {_T.R}{_T.BOLD}{label}{_T.R}  {_T.DIM}{'-'*pad}{_T.R}\n")
    else:
        print(f"  {_T.DIM}{'-'*88}{_T.R}")


def pbar(done: int, total: int, label: str = "", width: int = 28, col=None) -> None:
    c = col or _T.CYAN
    filled = int(width * done / total) if total else 0
    bar    = f"{c}{'#'*filled}{_T.DIM}{'.'*(width-filled)}{_T.R}"
    pct    = int(100 * done / total) if total else 0
    print(f"  [{bar}] {pct:>3}%  {label}", end="\r", flush=True)


# ── Input ──────────────────────────────────────────────────────────────────────
def prompt(label: str, default: str = "") -> str:
    """Show a styled prompt. Substitutes config defaults for common labels."""
    from utils.config import load_config
    cfg = load_config()
    if default == "500" and "Videos to scan" in label:
        default = cfg.get("default_videos", "500")
    elif default == "50" and "Top N" in label:
        default = cfg.get("default_top_n", "50")
    elif default == "best" and "Quality" in label:
        default = cfg.get("default_quality", "best")
    elif default == "Best" and "preset" in label.lower():
        default = cfg.get("default_hb_preset", "Best")
    suffix = f" [{default}]" if default else ""
    val = input(f"  {_T.CYAN}>{_T.R} {label}{suffix}: ").strip()
    return val or default


def back_to_menu() -> None:
    """
    Show a 3-option footer at the end of every tool.
    Raises a navigation exception — caught by main.py's tool loop.

      Enter  → back to current category  (BackToCategory)
      b      → all categories            (BackToMain)
      q      → quit                      (Quit)
    """
    C, B, r, D, G = _T.CYAN, _T.BOLD, _T.R, _T.DIM, _T.GREEN
    print()
    print(f"  {D}{'─' * 52}{r}")
    print(f"  {G}Enter{r}  {D}→{r}  back to category    "
          f"{C}Esc{r}  {D}→{r}  Home    "
          f"{C}q{r}  {D}→{r}  quit")
    print()
    try:
        choice = input("  > ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        raise Quit()

    if choice == "q":
        raise Quit()
    elif choice in ("b", "back", "esc", "escape", "\x1b"):
        raise BackToMain()
    else:
        raise BackToCategory()


# ── File I/O ──────────────────────────────────────────────────────────────────
def save(folder: str, filename: str, lines: list) -> str:
    """Write lines to folder/filename, creating folder if needed. Returns path."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(str(l) for l in lines))
    return path


def saved_in(folder: str) -> None:
    """Print a 'saved to' confirmation with optional file size + folder open."""
    from utils.config import load_config
    cfg = load_config()
    if cfg.get("show_file_size", True):
        try:
            files = [os.path.join(folder, f) for f in os.listdir(folder)
                     if os.path.isfile(os.path.join(folder, f))]
            if files:
                latest = max(files, key=os.path.getmtime)
                sz     = os.path.getsize(latest)
                sz_str = f"{sz/1024:.0f} KB" if sz < 1024*1024 else f"{sz/1024/1024:.1f} MB"
                ok(f"Saved to: {folder}  ({sz_str})")
                if cfg.get("auto_open_folder", False):
                    _open_folder(folder)
                return
        except Exception:
            pass
    ok(f"Saved to: {folder}")
    if cfg.get("auto_open_folder", False):
        _open_folder(folder)


def _open_folder(folder: str) -> None:
    import subprocess
    try:
        if os.name == "nt":
            subprocess.Popen(f'explorer "{folder}"', shell=True)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
    except Exception:
        pass


# ── Menu display ───────────────────────────────────────────────────────────────
def show_banner() -> None:
    from ui.theme import build_banner
    clear_screen()
    print(build_banner())


def show_menu() -> None:
    from ui.menu import build_menu
    print(build_menu())
