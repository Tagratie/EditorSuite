"""
tools/compressor.py
Tool 6  — Single Video Compressor (HandBrake CLI)
Tool 20 — Bulk Video Compressor (entire folder)
"""
import json
import os

from ui import theme as _T
from utils.helpers import ok, info, err, warn, divider, prompt, back_to_menu
from utils import dirs as _dirs


# ── HandBrake helpers ─────────────────────────────────────────────────────────

def _find_handbrake() -> str | None:
    import shutil
    hb = shutil.which("HandBrakeCLI") or shutil.which("handbrake-cli")
    if hb:
        return hb
    candidates = [
        r"C:\Program Files\HandBrake\HandBrakeCLI.exe",
        r"C:\Program Files (x86)\HandBrake\HandBrakeCLI.exe",
        "/usr/bin/HandBrakeCLI",
        "/usr/local/bin/HandBrakeCLI",
    ]
    return next((c for c in candidates if os.path.exists(c)), None)


def _load_saved_presets() -> list[tuple]:
    """Return [(display_name, path, all_names_list), ...] from PRESETS_DIR."""
    if not os.path.exists(_dirs.PRESETS_DIR):
        return []
    files  = [f for f in os.listdir(_dirs.PRESETS_DIR) if f.lower().endswith(".json")]
    result = []
    for fname in sorted(files):
        path = os.path.join(_dirs.PRESETS_DIR, fname)
        try:
            data = json.load(open(path, encoding="utf-8"))
            pl   = data.get("PresetList") or []
            names = []
            for entry in pl:
                names.append(entry.get("PresetName") or entry.get("name") or fname)
                for child in entry.get("ChildrenArray", []):
                    names.append(child.get("PresetName") or child.get("name") or "")
            names = [n for n in names if n]
            result.append((names[0] if names else fname, path, names))
        except Exception:
            result.append((fname, path, [fname]))
    return result


def _pick_preset(saved: list[tuple], default_name: str = "Best") -> tuple[str | None, str]:
    """Interactive preset picker. Returns (preset_file_path_or_None, preset_name)."""
    if not saved:
        return None, prompt("Preset name", default_name)

    print(f"\n  {_T.BOLD}Saved presets:{_T.R}")
    for i, (name, path, names) in enumerate(saved, 1):
        label = ", ".join(names) if len(names) > 1 else name
        print(f"    {_T.CYAN}{i}{_T.R}. {_T.BOLD}{label}{_T.R}  {_T.DIM}({os.path.basename(path)}){_T.R}")
    print(f"    {_T.DIM}0. Use a built-in preset name instead{_T.R}\n")

    choice = prompt(f"Pick preset [1-{len(saved)}] or 0 for built-in", "1")
    if choice.isdigit() and 1 <= int(choice) <= len(saved):
        idx = int(choice) - 1
        return saved[idx][1], (saved[idx][2][0] if saved[idx][2] else saved[idx][0])
    return None, prompt("Preset name", default_name)


# ── Tool 6: Single Video Compressor ──────────────────────────────────────────

def tool_compress():
    import subprocess
    divider("VIDEO COMPRESSOR")
    hb = _find_handbrake()
    if not hb:
        err("HandBrakeCLI not found.")
        info("Download from: https://handbrake.fr/downloads2.php")
        back_to_menu(); return

    os.makedirs(_dirs.PRESETS_DIR, exist_ok=True)
    raw = prompt("Drag a video or a .json preset file here").strip().strip('"\'')
    if not raw:
        back_to_menu(); return

    # If a .json preset was dropped — install it
    if raw.lower().endswith(".json") and os.path.exists(raw):
        import shutil as _sh
        dest = os.path.join(_dirs.PRESETS_DIR, os.path.basename(raw))
        _sh.copy2(raw, dest)
        try:
            data  = json.load(open(dest, encoding="utf-8"))
            names = [e.get("PresetName") or "" for e in (data.get("PresetList") or [])]
            names = [n for n in names if n]
        except Exception:
            names = []
        print()
        ok(f"Preset saved: {dest}")
        if names:
            ok(f"Preset names: {', '.join(names)}")
        info("You can now select this preset when compressing.")
        back_to_menu(); return

    if not os.path.exists(raw):
        err(f"File not found: {raw}"); back_to_menu(); return

    base, _ = os.path.splitext(raw)
    out      = base + "_compressed.mp4"
    saved    = _load_saved_presets()
    preset_file, preset_name = _pick_preset(saved)

    info(f"Input : {os.path.basename(raw)}")
    info(f"Output: {os.path.basename(out)}")
    info(f"Preset: {preset_name}\n")

    cmd = [hb, "-i", raw, "-o", out, "--preset", preset_name, "--optimize"]
    if preset_file:
        cmd += ["--preset-import-file", preset_file]

    ret = subprocess.run(cmd)
    if ret.returncode != 0 or not os.path.exists(out):
        warn("Preset failed — retrying with built-in x265 HQ settings...")
        subprocess.run([
            hb, "-i", raw, "-o", out,
            "--encoder", "x265", "--quality", "18",
            "--aencoder", "av_aac", "--ab", "192",
            "--optimize", "--format", "av_mp4",
        ])

    if os.path.exists(out):
        orig = os.path.getsize(raw) / 1024 / 1024
        comp = os.path.getsize(out) / 1024 / 1024
        pct  = (1 - comp / orig) * 100 if orig else 0
        print()
        ok(f"{orig:.1f} MB  →  {comp:.1f} MB  ({pct:.0f}% smaller)")
        ok(f"Saved: {out}")
    else:
        err("Compression failed.")
    back_to_menu()


# ── Tool 20: Bulk Video Compressor ────────────────────────────────────────────

def tool_bulkcompress():
    import subprocess
    divider("BULK VIDEO COMPRESSOR")
    print(f"  {_T.DIM}Compress every video in a folder with HandBrake.{_T.R}\n")
    hb = _find_handbrake()
    if not hb:
        err("HandBrakeCLI not found.")
        info("Download from: https://handbrake.fr/downloads2.php")
        back_to_menu(); return

    folder = prompt("Drag a folder here").strip().strip('"\'')
    if not folder or not os.path.isdir(folder):
        err("Folder not found."); back_to_menu(); return

    VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv"}
    videos = [f for f in os.listdir(folder)
              if os.path.splitext(f)[1].lower() in VIDEO_EXTS and "_compressed" not in f]
    if not videos:
        warn("No video files found in that folder."); back_to_menu(); return

    saved = _load_saved_presets()
    preset_file, preset_name = _pick_preset(saved, default_name="Fast 1080p30")

    out_dir = os.path.join(folder, "compressed")
    os.makedirs(out_dir, exist_ok=True)
    ok(f"Found {len(videos)} videos | Output → {out_dir}\n")

    failed = []
    for i, fname in enumerate(videos, 1):
        src = os.path.join(folder, fname)
        dst = os.path.join(out_dir, os.path.splitext(fname)[0] + "_compressed.mp4")
        print(f"  {_T.CYAN}[{i}/{len(videos)}]{_T.R} {fname[:60]}", end="... ", flush=True)
        cmd = [hb, "-i", src, "-o", dst, "--preset", preset_name, "--optimize"]
        if preset_file:
            cmd += ["--preset-import-file", preset_file]
        ret = subprocess.run(cmd, capture_output=True)
        if os.path.exists(dst) and os.path.getsize(dst) > 1000:
            orig = os.path.getsize(src) / 1024 / 1024
            comp = os.path.getsize(dst) / 1024 / 1024
            pct  = (1 - comp / orig) * 100 if orig else 0
            print(f"{_T.GREEN}✓{_T.R} {orig:.0f} MB → {comp:.0f} MB ({pct:.0f}% smaller)")
        else:
            print(f"{_T.YELLOW}failed{_T.R}")
            failed.append(fname)

    print()
    ok(f"Done! {len(videos)-len(failed)}/{len(videos)} compressed.")
    if failed:
        warn(f"Failed: {', '.join(failed[:5])}")
    back_to_menu()
