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


# ── Preset card ID → HandBrake settings ──────────────────────────────────────
# Maps the frontend preset card IDs to (preset_name, fallback_encoder_args)
# fallback_encoder_args are used when no preset file is supplied so HandBrake
# always gets explicit quality settings as a safety net.

_PRESET_MAP = {
    "tiktok": {
        "name":    "Fast 720p30",
        "encoder": "x264",
        "quality": "26",
        "res":     "--maxWidth 1280 --maxHeight 720",
        "audio":   "av_aac", "ab": "128",
    },
    "instagram": {
        "name":    "HQ 1080p30 Surround",
        "encoder": "x264",
        "quality": "22",
        "res":     "--maxWidth 1920 --maxHeight 1080",
        "audio":   "av_aac", "ab": "192",
    },
    "discord": {
        "name":    "Fast 720p30",
        "encoder": "x264",
        "quality": "28",
        "res":     "--maxWidth 1280 --maxHeight 720",
        "audio":   "av_aac", "ab": "128",
        "extra":   ["--vb", "0", "--ab", "128"],   # keeps under 25 MB for typical clips
    },
    "web": {
        "name":    "Fast 720p30",
        "encoder": "x264",
        "quality": "23",
        "res":     "--maxWidth 1280 --maxHeight 720",
        "audio":   "av_aac", "ab": "128",
    },
    "hq": {
        "name":    "HQ 1080p30 Surround",
        "encoder": "x265",
        "quality": "18",
        "res":     "--maxWidth 1920 --maxHeight 1080",
        "audio":   "av_aac", "ab": "192",
    },
    "ultra": {
        "name":    "Very Fast 480p30",
        "encoder": "x264",
        "quality": "30",
        "res":     "--maxWidth 854 --maxHeight 480",
        "audio":   "av_aac", "ab": "96",
    },
}


def _fallback_cmd(hb, src, dst, preset_id):
    """Build a HandBrake command using explicit encoder flags (no preset file needed)."""
    p = _PRESET_MAP.get(preset_id, _PRESET_MAP["web"])
    cmd = [
        hb, "-i", src, "-o", dst,
        "--encoder",  p["encoder"],
        "--quality",  p["quality"],
        "--aencoder", p["audio"],
        "--ab",       p["ab"],
        "--optimize", "--format", "av_mp4",
    ]
    # Resolution flags are space-separated strings — split them in
    for flag in p["res"].split():
        cmd.append(flag)
    return cmd


def _preset_cmd(hb, src, dst, preset_id, preset_file=None):
    """Build a HandBrake command using a named preset (+ optional import file)."""
    p    = _PRESET_MAP.get(preset_id, _PRESET_MAP["web"])
    name = p["name"]
    cmd  = [hb, "-i", src, "-o", dst, "--preset", name, "--optimize"]
    if preset_file and os.path.isfile(preset_file):
        cmd += ["--preset-import-file", preset_file]
    return cmd


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


# ── GUI runner helpers ────────────────────────────────────────────────────────

def _is_custom_preset_path(preset_id: str) -> bool:
    """True when the frontend sent a file path instead of a built-in preset ID."""
    return preset_id and preset_id not in _PRESET_MAP and (
        preset_id.lower().endswith(".json") or os.sep in preset_id or "/" in preset_id
    )


def _run_compress_single(src, dst, preset_id, hb, q):
    """Compress one file, push log/done/error events to queue q."""
    import subprocess

    def log(msg):  q.put({"type": "log",  "text": msg})
    def done(msg, path=""): q.put({"type": "done", "text": msg, "path": path})
    def error(msg): q.put({"type": "error","text": msg})

    log(f"Input:  {os.path.basename(src)}")
    log(f"Output: {os.path.basename(dst)}")
    log(f"Preset: {preset_id}")

    # Custom .json preset file path supplied directly
    if _is_custom_preset_path(preset_id):
        preset_file = preset_id
        # Try to read the first preset name from the file
        try:
            data = json.load(open(preset_file, encoding="utf-8"))
            pl   = data.get("PresetList") or []
            name = (pl[0].get("PresetName") or pl[0].get("name") or "Custom") if pl else "Custom"
        except Exception:
            name = "Custom"
        cmd = [hb, "-i", src, "-o", dst,
               "--preset", name, "--preset-import-file", preset_file, "--optimize"]
        log(f"Using custom preset file: {os.path.basename(preset_file)} ({name})")
    else:
        # Built-in preset card ID
        cmd = _preset_cmd(hb, src, dst, preset_id)
        log(f"Using preset: {_PRESET_MAP.get(preset_id, {}).get('name', preset_id)}")

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    ret = subprocess.run(cmd, capture_output=True)

    # Fallback to explicit encoder flags if preset failed or output is missing
    if ret.returncode != 0 or not os.path.exists(dst) or os.path.getsize(dst) < 1000:
        log("⚠ Preset failed — retrying with direct encoder settings...")
        if _is_custom_preset_path(preset_id):
            # Can't fall back for custom presets — report error
            error(f"Compression failed. Check your preset file is valid HandBrake JSON.")
            return False
        fallback = _fallback_cmd(hb, src, dst, preset_id)
        ret2 = subprocess.run(fallback, capture_output=True)
        if ret2.returncode != 0 or not os.path.exists(dst) or os.path.getsize(dst) < 1000:
            error("Compression failed even with fallback settings.")
            return False

    orig_mb = os.path.getsize(src) / 1024 / 1024
    comp_mb = os.path.getsize(dst) / 1024 / 1024
    pct     = (1 - comp_mb / orig_mb) * 100 if orig_mb else 0
    log(f"✓ {orig_mb:.1f} MB → {comp_mb:.1f} MB ({pct:.0f}% smaller)")
    return True


# ── GUI entry points (called by gui/runner.py) ────────────────────────────────

def run_gui_compress(options: dict, q):
    """
    GUI single-file compress.
    options: {input, output, preset}
    """
    import subprocess

    def log(msg):   q.put({"type": "log",  "text": msg})
    def done(msg, path=""): q.put({"type": "done", "text": msg, "path": path}); q.put(None)
    def error(msg): q.put({"type": "error","text": msg}); q.put(None)

    hb = _find_handbrake()
    if not hb:
        error("HandBrakeCLI not found. Download from handbrake.fr/downloads2.php")
        return

    src       = options.get("input",  "").strip().strip("\"'")
    out_dir   = options.get("output", "").strip().strip("\"'")
    preset_id = options.get("preset", "web").strip()

    if not src or not os.path.isfile(src):
        error(f"Video file not found: {src or '(none given)'}"); return

    # Resolve output path
    if out_dir and os.path.isdir(out_dir):
        base = os.path.splitext(os.path.basename(src))[0]
        dst  = os.path.join(out_dir, base + "_compressed.mp4")
    else:
        base, _ = os.path.splitext(src)
        dst     = base + "_compressed.mp4"

    ok = _run_compress_single(src, dst, preset_id, hb, q)
    if ok:
        done(f"Saved to {dst}", dst)
    # error already pushed inside _run_compress_single on failure


def run_gui_bulk_compress(options: dict, q):
    """
    GUI bulk compress — every video in a folder.
    options: {folder, output, preset}
    """
    def log(msg):   q.put({"type": "log",  "text": msg})
    def done(msg, path=""): q.put({"type": "done", "text": msg, "path": path}); q.put(None)
    def error(msg): q.put({"type": "error","text": msg}); q.put(None)

    hb = _find_handbrake()
    if not hb:
        error("HandBrakeCLI not found. Download from handbrake.fr/downloads2.php")
        return

    folder    = options.get("folder", "").strip().strip("\"'")
    out_dir   = options.get("output", "").strip().strip("\"'")
    preset_id = options.get("preset", "web").strip()

    if not folder or not os.path.isdir(folder):
        error(f"Folder not found: {folder or '(none given)'}"); return

    VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}
    videos = [
        f for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in VIDEO_EXTS
        and "_compressed" not in f
    ]
    if not videos:
        error("No video files found in that folder."); return

    # Resolve output directory
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    else:
        out_dir = os.path.join(folder, "compressed")
        os.makedirs(out_dir, exist_ok=True)

    log(f"Found {len(videos)} videos → output: {out_dir}")
    log(f"Preset: {preset_id}")

    failed  = []
    success = 0
    for i, fname in enumerate(videos, 1):
        src  = os.path.join(folder, fname)
        base = os.path.splitext(fname)[0]
        dst  = os.path.join(out_dir, base + "_compressed.mp4")

        q.put({"type": "progress", "value": i - 1, "total": len(videos), "track": fname})
        log(f"[{i}/{len(videos)}] {fname[:60]}...")

        if _run_compress_single(src, dst, preset_id, hb, q):
            success += 1
        else:
            failed.append(fname)

    q.put({"type": "progress", "value": len(videos), "total": len(videos)})
    summary = f"Done — {success}/{len(videos)} compressed."
    if failed:
        summary += f" Failed: {', '.join(failed[:3])}{'…' if len(failed) > 3 else ''}"
    done(summary, out_dir)


# ── Tool 6: Single Video Compressor (terminal / menu mode) ───────────────────

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


# ── Tool 20: Bulk Video Compressor (terminal / menu mode) ────────────────────

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
