"""
tools/bg_remover.py
Tool 18 — Background Remover
Uses rembg (local AI) to remove backgrounds from images.
No upload, no API key needed.
"""
import os
import subprocess

from ui import theme as _T
from utils.helpers import ok, info, err, warn, divider, prompt, back_to_menu
from utils import dirs as _dirs


def _ensure_rembg():
    """Import or auto-install rembg + Pillow. Returns (remove_fn, ok_bool)."""
    try:
        from rembg import remove as _remove
        from PIL import Image  # noqa: F401
        return _remove, True
    except ImportError:
        warn("rembg not installed. Installing now (this may take a minute)...")
        ret = subprocess.run(
            ["pip", "install", "rembg[gpu]", "Pillow", "--break-system-packages", "-q"]
        )
        if ret.returncode != 0:
            subprocess.run(
                ["pip", "install", "rembg", "Pillow", "--break-system-packages", "-q"]
            )
        try:
            from rembg import remove as _remove
            ok("rembg installed successfully.")
            return _remove, True
        except ImportError:
            err("Could not install rembg. Try: pip install rembg Pillow")
            return None, False


def tool_bgremove():
    divider("BACKGROUND REMOVER")
    print(f"  {_T.DIM}Removes background from images. Supports JPG, PNG, WEBP.{_T.R}")
    print(f"  {_T.DIM}Uses rembg (local AI — no upload, no API key needed).{_T.R}\n")

    rembg_remove, rembg_ok = _ensure_rembg()
    if not rembg_ok:
        back_to_menu()
        return

    print(f"  {_T.CYAN}1{_T.R}  Remove background from a single image")
    print(f"  {_T.CYAN}2{_T.R}  Batch process an entire folder")
    print()
    mode = prompt("Mode [1/2]", "1").strip()

    if mode == "1":
        raw = prompt("Drag an image here").strip().strip('"').strip("'")
        if not raw or not os.path.exists(raw):
            err("File not found.")
            back_to_menu()
            return
        files   = [raw]
        out_dir = _dirs.DIR_IMAGES
        os.makedirs(out_dir, exist_ok=True)
    else:
        folder = prompt("Drag a folder here").strip().strip('"').strip("'")
        if not folder or not os.path.isdir(folder):
            err("Folder not found.")
            back_to_menu()
            return
        exts  = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        files = [
            os.path.join(folder, f) for f in os.listdir(folder)
            if os.path.splitext(f)[1].lower() in exts and "_nobg" not in f
        ]
        out_dir = os.path.join(folder, "no_bg")
        os.makedirs(out_dir, exist_ok=True)
        if not files:
            warn("No images found in that folder.")
            back_to_menu()
            return
        ok(f"Found {len(files)} images → {out_dir}\n")

    ok_count = 0
    for i, path in enumerate(files, 1):
        fname = os.path.basename(path)
        base  = os.path.splitext(fname)[0]
        dest  = os.path.join(out_dir, base + "_nobg.png")

        if mode == "1":
            print(); info(f"Processing: {fname}")
        else:
            print(f"  {_T.CYAN}[{i}/{len(files)}]{_T.R} {fname[:55]}", end="... ", flush=True)

        try:
            with open(path, "rb") as f:
                in_data = f.read()
            out_data = rembg_remove(in_data)
            with open(dest, "wb") as f:
                f.write(out_data)
            size = os.path.getsize(dest) / 1024
            if mode == "1":
                ok(f"Saved: {dest}  ({size:.0f} KB)")
            else:
                print(f"{_T.GREEN}✓{_T.R}  ({size:.0f} KB)")
            ok_count += 1
        except Exception as e:
            if mode == "1":
                err(f"Failed: {e}")
            else:
                print(f"{_T.YELLOW}✗ {e}{_T.R}")

    if mode == "2":
        print()
        ok(f"Done — {ok_count}/{len(files)} processed.")
        ok(f"Saved to: {out_dir}")

    back_to_menu()
