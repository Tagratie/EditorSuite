"""
utils/helpers.py — fixed version, no ui.theme dependency
"""
import sys, os

try:
    from ui import theme as _T
except ModuleNotFoundError:
    class _T:  # noqa
        BOLD=DIM=R=GREEN=YELLOW=RED=CYAN=MAGENTA=WHITE=BLUE=""

def ok(msg):      print(f"  ✓ {msg}")
def info(msg):    print(f"  · {msg}")
def err(msg):     print(f"  ✗ {msg}", file=sys.stderr)
def warn(msg):    print(f"  ⚠ {msg}")
def divider(c="-", n=60): print(c * n)
def prompt(msg):  return input(f"  > {msg}: ").strip()
def save(data, path):
    import json
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
def saved_in(path): ok(f"Saved → {path}")
def back_to_menu(): pass
def clear_line():   print("\r\033[K", end="", flush=True)
