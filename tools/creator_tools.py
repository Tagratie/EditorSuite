"""
tools/creator_tools.py
Tool 6.2 — Video Merge / Concat
Tool 6.3 — Thumbnail Extractor
Tool 6.4 — Bulk Rename
All use ffmpeg (no re-encode for merge, instant thumbnail grab).
"""
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime

from ui import theme as _T
from utils.helpers import ok, info, err, warn, divider, prompt, back_to_menu
from utils import dirs as _dirs


def _need_ffmpeg() -> bool:
    if shutil.which("ffmpeg"):
        return True
    err("ffmpeg not found.")
    info("Install from https://ffmpeg.org  or:  winget install ffmpeg")
    return False


# ── Tool 6.2: Video Merge / Concat ────────────────────────────────────────────

def tool_merge():
    divider("VIDEO MERGE / CONCAT")
    print(f"  {_T.DIM}Join multiple video clips into one file. Uses stream copy — instant, no re-encode.{_T.R}")
    print(f"  {_T.DIM}All clips must have the same resolution and codec for best results.{_T.R}\n")

    if not _need_ffmpeg():
        back_to_menu(); return

    print(f"  {_T.DIM}Drag and drop video files one at a time. Empty line when done.{_T.R}\n")
    files = []
    while True:
        raw = input(f"  {_T.CYAN}>{_T.R} Clip {len(files)+1} (blank to finish): ").strip().strip('"').strip("'")
        if not raw:
            break
        if not os.path.exists(raw):
            err(f"Not found: {raw}")
            continue
        files.append(raw)
        ok(f"Added: {os.path.basename(raw)}")

    if len(files) < 2:
        warn("Need at least 2 clips.")
        back_to_menu(); return

    base      = os.path.splitext(os.path.basename(files[0]))[0]
    ts        = datetime.now().strftime("%H%M%S")
    out_path  = os.path.join(_dirs.DIR_COMPRESS, f"{base}_merged_{ts}.mp4")
    os.makedirs(_dirs.DIR_COMPRESS, exist_ok=True)

    # Write ffmpeg concat list to a temp file
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
        for f in files:
            tmp.write(f"file '{f.replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'\n")
        tmp_path = tmp.name

    print()
    info(f"Merging {len(files)} clips...")
    ret = subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", tmp_path,
        "-c", "copy",
        out_path,
    ], capture_output=True)

    os.unlink(tmp_path)

    if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
        sz = os.path.getsize(out_path) / 1024 / 1024
        ok(f"Merged: {out_path}  ({sz:.1f} MB)")
    else:
        # Stream copy failed — try re-encode
        warn("Stream copy failed, re-encoding (slower but more compatible)...")
        # Rebuild concat list
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
            for f in files:
                tmp.write(f"file '{f}'\n")
            tmp_path = tmp.name
        ret2 = subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", tmp_path,
            "-c:v", "libx264", "-c:a", "aac",
            "-preset", "fast",
            out_path,
        ], capture_output=True)
        os.unlink(tmp_path)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            sz = os.path.getsize(out_path) / 1024 / 1024
            ok(f"Merged (re-encoded): {out_path}  ({sz:.1f} MB)")
        else:
            err("Merge failed.")
            print(ret2.stderr.decode(errors="replace")[-400:])

    back_to_menu()


# ── Tool 6.3: Thumbnail Extractor ────────────────────────────────────────────

def tool_thumbnail():
    divider("THUMBNAIL EXTRACTOR")
    print(f"  {_T.DIM}Grab any frame from a video as a high-quality PNG or JPG.{_T.R}")
    print(f"  {_T.DIM}Single video or batch-extract from an entire folder.{_T.R}\n")

    if not _need_ffmpeg():
        back_to_menu(); return

    print(f"  {_T.CYAN}1{_T.R}  Single video — pick exact timestamp")
    print(f"  {_T.CYAN}2{_T.R}  Single video — best frame auto-detect (sharpest)")
    print(f"  {_T.CYAN}3{_T.R}  Batch — extract one frame per video from a folder")
    print()
    mode = prompt("Mode [1/2/3]", "1").strip()

    if mode in ("1", "2"):
        raw = prompt("Drag a video here").strip().strip('"').strip("'")
        if not raw or not os.path.exists(raw):
            err("File not found."); back_to_menu(); return

        base    = os.path.splitext(os.path.basename(raw))[0]
        out_dir = _dirs.DIR_IMAGES
        os.makedirs(out_dir, exist_ok=True)
        out     = os.path.join(out_dir, f"{base}_thumb.jpg")

        if mode == "1":
            ts = prompt("Timestamp (HH:MM:SS or seconds)", "0:00:01")
            print()
            info("Extracting frame...")
            cmd = ["ffmpeg", "-y", "-ss", ts, "-i", raw,
                   "-vframes", "1", "-q:v", "1", out]
        else:
            print()
            info("Finding sharpest frame (scanning first 10s)...")
            # Use thumbnail filter to auto-pick the best frame
            cmd = ["ffmpeg", "-y", "-i", raw,
                   "-vf", "thumbnail=300", "-frames:v", "1",
                   "-q:v", "1", out]

        ret = subprocess.run(cmd, capture_output=True)
        if os.path.exists(out) and os.path.getsize(out) > 500:
            sz = os.path.getsize(out) / 1024
            ok(f"Saved: {out}  ({sz:.0f} KB)")
        else:
            err("Failed to extract frame.")
            print(ret.stderr.decode(errors="replace")[-300:])

    elif mode == "3":
        folder = prompt("Drag a folder here").strip().strip('"').strip("'")
        if not folder or not os.path.isdir(folder):
            err("Folder not found."); back_to_menu(); return

        exts  = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
        files = [
            os.path.join(folder, f) for f in sorted(os.listdir(folder))
            if os.path.splitext(f)[1].lower() in exts
        ]
        if not files:
            warn("No video files found."); back_to_menu(); return

        out_dir = os.path.join(folder, "thumbnails")
        os.makedirs(out_dir, exist_ok=True)
        ok_count = 0

        for i, path in enumerate(files, 1):
            base = os.path.splitext(os.path.basename(path))[0]
            out  = os.path.join(out_dir, f"{base}_thumb.jpg")
            print(f"  {_T.CYAN}[{i}/{len(files)}]{_T.R} {base[:50]}", end="... ", flush=True)
            ret  = subprocess.run(
                ["ffmpeg", "-y", "-i", path,
                 "-vf", "thumbnail=200", "-frames:v", "1", "-q:v", "1", out],
                capture_output=True,
            )
            if os.path.exists(out) and os.path.getsize(out) > 500:
                print(f"{_T.GREEN}✓{_T.R}")
                ok_count += 1
            else:
                print(f"{_T.YELLOW}✗{_T.R}")

        print()
        ok(f"Done — {ok_count}/{len(files)} thumbnails saved to: {out_dir}")

    back_to_menu()


# ── Tool 6.4: Bulk Rename ────────────────────────────────────────────────────

_RENAME_TOKENS = """
  Tokens you can use:
    {n}          original filename (no extension)
    {date}       today's date (YYYY-MM-DD)
    {num}        sequence number (001, 002, ...)
    {ext}        original extension
    {UPPER}      original name uppercased
    {lower}      original name lowercased

  Examples:
    {date}_{num}_{n}      →  2025-06-01_001_myvideo
    clip_{num}            →  clip_001, clip_002, ...
    {UPPER}_{date}        →  MYVIDEO_2025-06-01
"""


def _apply_template(tmpl: str, name: str, ext: str, num: int) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return (tmpl
            .replace("{n}",     name)
            .replace("{date}",  today)
            .replace("{num}",   f"{num:03d}")
            .replace("{ext}",   ext.lstrip("."))
            .replace("{UPPER}", name.upper())
            .replace("{lower}", name.lower()))


def tool_bulkrename():
    divider("BULK RENAME")
    print(f"  {_T.DIM}Rename every file in a folder using a template pattern.{_T.R}")
    print(_RENAME_TOKENS)

    folder = prompt("Drag a folder here").strip().strip('"').strip("'")
    if not folder or not os.path.isdir(folder):
        err("Folder not found."); back_to_menu(); return

    filter_ext = prompt("Filter by extension (e.g. mp4 — blank = all files)", "").strip().lstrip(".")
    files = sorted([
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f))
        and (not filter_ext or f.lower().endswith("." + filter_ext.lower()))
        and not f.startswith(".")
    ])

    if not files:
        warn("No files found matching that filter."); back_to_menu(); return

    print(f"\n  {_T.CYAN}{len(files)}{_T.R} files found. First 3:")
    for f in files[:3]:
        print(f"  {_T.DIM}  {f}{_T.R}")
    print()

    tmpl = prompt("Name template (without extension)", "{date}_{num}_{n}").strip()
    if not tmpl:
        back_to_menu(); return

    # Preview
    print(f"\n  {_T.BOLD}Preview (first 5):{_T.R}")
    for i, f in enumerate(files[:5], 1):
        name, ext = os.path.splitext(f)
        new_name  = _apply_template(tmpl, name, ext, i) + ext
        print(f"  {_T.DIM}{f:<40}{_T.R}  →  {_T.CYAN}{new_name}{_T.R}")

    print()
    confirm = prompt("Apply to all files? [yes/no]", "no").strip().lower()
    if confirm != "yes":
        warn("Cancelled."); back_to_menu(); return

    ok_count = skip_count = 0
    for i, f in enumerate(files, 1):
        name, ext = os.path.splitext(f)
        new_name  = _apply_template(tmpl, name, ext, i) + ext
        src       = os.path.join(folder, f)
        dst       = os.path.join(folder, new_name)
        if src == dst:
            skip_count += 1
            continue
        if os.path.exists(dst):
            warn(f"Skipped (exists): {new_name}")
            skip_count += 1
            continue
        try:
            os.rename(src, dst)
            ok_count += 1
        except Exception as e:
            err(f"Failed {f}: {e}")
            skip_count += 1

    print()
    ok(f"Done — {ok_count} renamed, {skip_count} skipped.")
    back_to_menu()
