"""
tools/best_posting_time.py
Tool 4 — Best Posting Time Finder
Scrapes your own profile, then shows which days/hours get the most views.
"""
import asyncio
from collections import defaultdict
from datetime import datetime

from ui import theme as _T
from utils.helpers import ok, info, err, warn, divider, prompt, save, saved_in, back_to_menu
from utils import dirs as _dirs
from utils.config import get_my_username, set_my_username
from tools.competitor import _scrape_profile   # reuse the same profile scraper

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def tool_bptf():
    divider("BEST POSTING TIME FINDER")
    username = get_my_username()
    if not username:
        warn("Your account is not set.")
        username = set_my_username(prompt("Your TikTok username"))

    print(f"  {_T.DIM}Scraping @{username}...{_T.R}\n")

    from playwright.async_api import async_playwright

    async def _run():
        async with async_playwright() as pw:
            _, posts = await _scrape_profile(pw, username)
        return posts

    posts = asyncio.run(_run())
    if not posts:
        err("No posts found. Profile may be private."); back_to_menu(); return

    ok(f"Analysing {len(posts)} posts...\n")

    # Build day/hour views maps
    day_views:  defaultdict[int, list] = defaultdict(list)
    hour_views: defaultdict[int, list] = defaultdict(list)
    for p in posts:
        if not p["ts"]:
            continue
        dt = datetime.fromtimestamp(p["ts"])
        day_views[dt.weekday()].append(p["views"])
        hour_views[dt.hour].append(p["views"])

    def avg(lst): return sum(lst) // len(lst) if lst else 0

    day_avg  = {d: avg(day_views[d])  for d in day_views}
    hour_avg = {h: avg(hour_views[h]) for h in hour_views}

    best_days = sorted(day_avg.items(),  key=lambda x: x[1], reverse=True)
    best_hrs  = sorted(hour_avg.items(), key=lambda x: x[1], reverse=True)

    divider("BEST DAYS TO POST")
    max_d = best_days[0][1] if best_days else 1
    for day, avg_v in best_days:
        bar = "#" * int((avg_v / max_d) * 20) + "." * (20 - int((avg_v / max_d) * 20))
        col = _T.GREEN if avg_v == max_d else _T.R
        print(f"    {col}{DAY_NAMES[day]:<12}{_T.R}  avg {col}{avg_v:>9,}{_T.R}  "
              f"{col}{bar}{_T.R}  {_T.DIM}({len(day_views[day])} posts){_T.R}")

    print(f"\n  {_T.BOLD}Best hours (local time):{_T.R}")
    max_h = best_hrs[0][1] if best_hrs else 1
    for hour, avg_v in best_hrs:
        label = f"{hour:02d}:00-{(hour+1)%24:02d}:00"
        bar   = "#" * int((avg_v / max_h) * 20) + "." * (20 - int((avg_v / max_h) * 20))
        col   = _T.GREEN if avg_v == max_h else _T.R
        print(f"    {col}{label:<14}{_T.R}  avg {col}{avg_v:>9,}{_T.R}  "
              f"{col}{bar}{_T.R}  {_T.DIM}({len(hour_views[hour])} posts){_T.R}")

    # Per-day best-hour matrix
    day_hour_views: defaultdict = defaultdict(lambda: defaultdict(list))
    for p in posts:
        if p["ts"]:
            dt = datetime.fromtimestamp(p["ts"])
            day_hour_views[dt.weekday()][dt.hour].append(p["views"])

    date  = datetime.now().strftime("%Y-%m-%d_%H-%M")
    lines = [f"Best Posting Times: @{username} | {date}",
             f"Posts: {len(posts)}", "=" * 60, "BEST DAYS"]
    for day, avg_v in best_days:
        lines.append(f"  {DAY_NAMES[day]:<12}  avg:{avg_v:>10,}  ({len(day_views[day])} posts)")
    lines += ["", "BEST HOURS"]
    for hour, avg_v in sorted(hour_avg.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"  {hour:02d}:00          avg:{avg_v:>10,}  ({len(hour_views[hour])} posts)")
    lines += ["", "DAY_HOUR_MATRIX"]
    for d in range(7):
        if d not in day_hour_views:
            continue
        dh     = day_hour_views[d]
        best_h = max(dh.items(), key=lambda x: sum(x[1]) // len(x[1]) if x[1] else 0)
        lines.append(f"  {DAY_NAMES[d]}  best_hour:{best_h[0]:02d}")

    save(_dirs.DIR_ANALYSIS, f"bptf_{username}_{date}.txt", lines)
    print(); saved_in(_dirs.DIR_ANALYSIS)
    back_to_menu()
