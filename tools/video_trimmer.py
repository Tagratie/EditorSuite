"""
tools/video_trimmer.py
Tool 25 — Video Trimmer / Cutter
Trim any video to an exact start/end time using ffmpeg.
Supports single cuts and splitting a video into multiple clips.
"""
import os
import subprocess
import shutil
from datetime import datetime

from ui import theme as _T
from utils.helpers import ok, info, err, warn, divider, prompt, back_to_menu
from utils import dirs as _dirs


def _parse_time(s: str) -> str | None:
    """Accept HH:MM:SS, MM:SS, or raw seconds. Returns ffmpeg-compatible string or None."""
    s = s.strip()
    if not s:
        return None
    # Already HH:MM:SS or MM:SS
    if ":" in s:
        parts = s.split(":")
        if all(p.isdigit() for p in parts) and 2 <= len(parts) <= 3:
            return s.zfill(2) if len(parts) == 2 else s
    # Raw seconds
    try:
        secs = float(s)
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        sec = secs % 60
        return f"{h:02d}:{m:02d}:{sec:06.3f}"
    except ValueError:
        return None


def tool_trimmer():
    divider("VIDEO TRIMMER / CUTTER")
    print(f"  {_T.DIM}Trim or split any video with frame-accurate cuts. Requires ffmpeg.{_T.R}\n")

    if not shutil.which("ffmpeg"):
        err("ffmpeg not found.")
        info("Install from https://ffmpeg.org or:  winget install ffmpeg")
        back_to_menu()
        return

    raw = prompt("Drag a video file here").strip().strip('"').strip("'")
    if not raw or not os.path.exists(raw):
        err("File not found.")
        back_to_menu()
        return

    # Show duration
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", raw],
            capture_output=True, text=True
        )
        duration = float(probe.stdout.strip())
        h = int(duration // 3600); m = int((duration % 3600) // 60); s = duration % 60
        info(f"Duration: {h:02d}:{m:02d}:{s:05.2f}  ({os.path.basename(raw)})\n")
    except Exception:
        pass

    print(f"  {_T.CYAN}1{_T.R}  Single trim  (start → end)")
    print(f"  {_T.CYAN}2{_T.R}  Split into multiple clips\n")
    mode = prompt("Mode [1/2]", "1").strip()

    base, ext = os.path.splitext(os.path.basename(raw))
    os.makedirs(_dirs.DIR_COMPRESS, exist_ok=True)   # reuse compressed dir for trimmed output

    if mode == "2":
        _split_mode(raw, base)
    else:
        _trim_mode(raw, base)

    back_to_menu()


def _trim_mode(raw: str, base: str):
    print(f"\n  {_T.DIM}Leave end blank to trim to end of file.{_T.R}")
    start_raw = prompt("Start time  (HH:MM:SS or seconds)", "0")
    end_raw   = prompt("End time    (HH:MM:SS or seconds, blank = end of file)", "")

    start = _parse_time(start_raw) or "00:00:00"
    end   = _parse_time(end_raw)

    ts  = datetime.now().strftime("%H%M%S")
    out = os.path.join(_dirs.DIR_COMPRESS, f"{base}_trim_{ts}.mp4")

    cmd = ["ffmpeg", "-y", "-i", raw, "-ss", start]
    if end:
        cmd += ["-to", end]
    # Stream copy is instant — no re-encode. Fall back to re-encode only if needed.
    cmd += ["-c", "copy", out]

    print()
    info(f"Trimming {start} → {end or 'end'}...")
    ret = subprocess.run(cmd, capture_output=True)

    if os.path.exists(out) and os.path.getsize(out) > 1000:
        sz = os.path.getsize(out) / 1024 / 1024
        ok(f"Saved: {out}  ({sz:.1f} MB)")
    else:
        # Stream copy failed (codec incompatibility) — re-encode
        warn("Stream copy failed, re-encoding...")
        cmd[-3] = "-c:v"; cmd[-2] = "libx264"; cmd[-1] = "-c:a"
        cmd += ["aac", out]
        cmd = ["ffmpeg", "-y", "-i", raw, "-ss", start]
        if end:
            cmd += ["-to", end]
        cmd += ["-c:v", "libx264", "-c:a", "aac", "-preset", "fast", out]
        ret2 = subprocess.run(cmd, capture_output=True)
        if os.path.exists(out) and os.path.getsize(out) > 1000:
            sz = os.path.getsize(out) / 1024 / 1024
            ok(f"Saved (re-encoded): {out}  ({sz:.1f} MB)")
        else:
            err("Trim failed.")
            print(ret2.stderr.decode(errors="replace")[-400:])


def _split_mode(raw: str, base: str):
    print(f"\n  {_T.DIM}Enter each clip as: start-end (e.g. 0:00-0:30), one per line.{_T.R}")
    print(f"  {_T.DIM}Empty line when done.{_T.R}\n")

    clips = []
    while True:
        entry = input(f"  {_T.CYAN}>{_T.R} Clip {len(clips)+1} start-end (blank to start): ").strip()
        if not entry:
            break
        if "-" not in entry:
            err("Format: start-end  e.g. 0:30-1:15")
            continue
        parts = entry.split("-", 1)
        start = _parse_time(parts[0])
        end   = _parse_time(parts[1])
        if not start or not end:
            err("Could not parse times. Use HH:MM:SS or seconds.")
            continue
        clips.append((start, end))

    if not clips:
        warn("No clips entered.")
        return

    out_dir = os.path.join(_dirs.DIR_COMPRESS, f"{base}_clips")
    os.makedirs(out_dir, exist_ok=True)
    ok_count = 0

    for i, (start, end) in enumerate(clips, 1):
        out = os.path.join(out_dir, f"{base}_clip{i:02d}.mp4")
        print(f"  {_T.CYAN}[{i}/{len(clips)}]{_T.R} {start} → {end}", end="... ", flush=True)
        cmd = ["ffmpeg", "-y", "-i", raw, "-ss", start, "-to", end,
               "-c", "copy", out]
        ret = subprocess.run(cmd, capture_output=True)
        if os.path.exists(out) and os.path.getsize(out) > 500:
            sz = os.path.getsize(out) / 1024
            print(f"{_T.GREEN}✓{_T.R}  ({sz:.0f} KB)")
            ok_count += 1
        else:
            print(f"{_T.YELLOW}✗ failed{_T.R}")

    print()
    ok(f"Done — {ok_count}/{len(clips)} clips saved to: {out_dir}")
