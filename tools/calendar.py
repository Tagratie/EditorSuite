"""
tools/calendar.py
Tool 11 — Posting Calendar Generator
Builds a 4-week posting schedule from saved BPTF data (or sensible defaults).
"""
import os
from datetime import datetime, date, timedelta

from ui import theme as _T
from utils.helpers import ok, info, warn, divider, prompt, save, saved_in, back_to_menu
from utils import dirs as _dirs

DAY_NAMES  = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_ORDER  = {d: i for i, d in enumerate(DAY_NAMES)}


def _load_bptf() -> tuple[list, list, dict, str]:
    """
    Try to load saved BPTF file from DIR_ANALYSIS.
    Returns (best_days, best_hours, day_best_hour, username).
    Falls back to sensible defaults if nothing is found.
    """
    bptf_files = sorted(
        [f for f in os.listdir(_dirs.DIR_ANALYSIS) if f.startswith("bptf_")],
        reverse=True,
    ) if os.path.isdir(_dirs.DIR_ANALYSIS) else []

    if not bptf_files:
        warn("No saved BPTF data found — using best-practice defaults.")
        return (
            [("Tuesday",1),("Wednesday",1),("Thursday",1),
             ("Friday",1),("Saturday",1),("Sunday",1),("Monday",1)],
            [(18,1),(12,1),(8,1)],
            {},
            "you",
        )

    info(f"Found saved analysis: {bptf_files[0]}")
    use = prompt("Use this file? [y/n]", "y")
    if use.lower() != "y":
        return (
            [("Tuesday",1),("Wednesday",1),("Thursday",1),
             ("Friday",1),("Saturday",1),("Sunday",1),("Monday",1)],
            [(18,1),(12,1),(8,1)],
            {},
            "you",
        )

    path = os.path.join(_dirs.DIR_ANALYSIS, bptf_files[0])
    username = bptf_files[0].replace("bptf_", "").split("_2")[0]

    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    day_data: dict  = {}
    hour_data: dict = {}
    day_best_hour: dict = {}
    section = None

    for line in lines:
        l = line.strip()
        if l == "BEST DAYS":         section = "days"
        elif l == "BEST HOURS":      section = "hours"
        elif l == "DAY_HOUR_MATRIX": section = "matrix"
        elif section == "days" and l:
            for d in DAY_NAMES:
                if l.startswith(d):
                    try:
                        day_data[d] = int(l.split("avg:")[-1].split("(")[0].replace(",","").strip())
                    except Exception:
                        pass
        elif section == "hours" and l:
            try:
                hr  = int(l.strip().split(":")[0])
                avg = int(l.split("avg:")[-1].split("(")[0].replace(",","").strip())
                hour_data[hr] = avg
            except Exception:
                pass
        elif section == "matrix" and l:
            for d in DAY_NAMES:
                if l.startswith(d) and "best_hour:" in l:
                    try:
                        day_best_hour[d] = int(l.split("best_hour:")[-1].strip())
                    except Exception:
                        pass

    if not day_data:
        warn("Could not parse BPTF file — using defaults.")
        return (
            [("Tuesday",1),("Wednesday",1),("Thursday",1),
             ("Friday",1),("Saturday",1),("Sunday",1),("Monday",1)],
            [(18,1),(12,1),(8,1)],
            {},
            username,
        )

    best_days  = sorted(day_data.items(),  key=lambda x: x[1], reverse=True)
    best_hours = sorted(hour_data.items(), key=lambda x: x[1], reverse=True)[:3]
    return best_days, best_hours, day_best_hour, username


def tool_calendar():
    divider("POSTING CALENDAR GENERATOR")
    print(f"  {_T.DIM}Generates a 4-week schedule from your Best Posting Time data.{_T.R}\n")

    best_days, best_hours, day_best_hour, username = _load_bptf()

    posts_per_week = int(prompt("Posts per week", "3") or "3")
    start_str      = prompt("Start date (YYYY-MM-DD)", datetime.now().strftime("%Y-%m-%d"))
    try:
        start = date.fromisoformat(start_str)
    except Exception:
        start = datetime.now().date()

    top_days = [d for d, _ in best_days[:posts_per_week]]
    top_hrs  = [h for h, _ in best_hours] or [18, 12, 8]

    lines_out = [
        f"Posting Calendar — @{username}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d')} | {posts_per_week} posts/week",
        "=" * 60, "",
    ]

    print()
    divider(f"4-WEEK CALENDAR  —  {posts_per_week}x/week")
    print(f"  {_T.BOLD}Best days :{_T.R} {', '.join(top_days)}")
    print(f"  {_T.BOLD}Best times:{_T.R} {', '.join(f'{h:02d}:00' for h in top_hrs)}\n")

    # Advance to first Monday on or after start
    current = start
    while current.weekday() != 0:
        current += timedelta(days=1)

    for week in range(4):
        week_start = current + timedelta(weeks=week)
        week_end   = week_start + timedelta(days=6)
        week_label = (f"Week {week+1}  "
                      f"({week_start.strftime('%b %d')} – {week_end.strftime('%b %d')})")
        print(f"  {_T.CYAN}{_T.BOLD}{week_label}{_T.R}")
        lines_out.append(week_label)
        hour_cycle = 0
        for d in sorted(top_days, key=lambda x: DAY_ORDER.get(x, 9)):
            day_offset = DAY_ORDER[d]
            post_date  = week_start + timedelta(days=day_offset)
            if d in day_best_hour:
                post_time = f"{day_best_hour[d]:02d}:00"
            else:
                post_time = f"{top_hrs[hour_cycle % len(top_hrs)]:02d}:00"
                hour_cycle += 1
            print(f"  {_T.GREEN}✓{_T.R}  {_T.BOLD}{post_date.strftime('%a %b %d')}{_T.R}  {post_time}")
            lines_out.append(f"    {post_date.strftime('%a %b %d')}  {post_time}")
        print()
        lines_out.append("")

    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
    save(_dirs.DIR_ANALYSIS, f"calendar_{username}_{date_str}.txt", lines_out)
    saved_in(_dirs.DIR_ANALYSIS)
    back_to_menu()
