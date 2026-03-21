"""
tools/growth_tracker.py
Tool 19 — Account Growth Tracker
Snapshots follower/video/like counts over time.
Run daily for trends; data is stored in DIR_LOGS/growth_tracker.json.
"""
import asyncio
import json
import os
from datetime import datetime

from ui import theme as _T
from utils.helpers import ok, info, err, divider, prompt, back_to_menu, clear_line, get_stat
from utils import dirs as _dirs
from core.browser import new_browser


# ── Profile stats scraper ─────────────────────────────────────────────────────

async def _scrape_profile_stats(username: str) -> dict:
    from playwright.async_api import async_playwright
    stats = {}

    async with async_playwright() as pw:
        browser, ctx = await new_browser(pw, mute=True)

        async def on_resp(r):
            if "user/detail" not in r.url and "userInfo" not in r.url:
                return
            try:
                body = await r.json()
                u    = body.get("userInfo") or body.get("user") or {}
                s    = u.get("stats") or u.get("userStats") or {}
                if s:
                    stats["followers"] = get_stat(s, "followerCount", "fans")
                    stats["following"] = get_stat(s, "followingCount")
                    stats["likes"]     = get_stat(s, "heartCount", "heart")
                    stats["videos"]    = get_stat(s, "videoCount")
            except Exception:
                pass

        pages = ctx.pages
        page = pages[0] if pages else await ctx.new_page()
        page.on("response", on_resp)
        try:
            await page.goto(
                f"https://www.tiktok.com/@{username}",
                wait_until="domcontentloaded",
                timeout=20000,
            )
            import asyncio as _a
            await _a.sleep(3)
        except Exception:
            pass
        await browser.close()

    return stats


# ── Tool entrypoint ───────────────────────────────────────────────────────────

def tool_growthtrack():
    divider("ACCOUNT GROWTH TRACKER")
    print(f"  {_T.DIM}Snapshots follower/video counts over time. Run daily for trends.{_T.R}\n")

    username = prompt("TikTok username (no @)").lstrip("@")
    if not username:
        back_to_menu()
        return

    db_path = os.path.join(_dirs.DIR_LOGS, "growth_tracker.json")
    os.makedirs(_dirs.DIR_LOGS, exist_ok=True)
    try:
        db = json.load(open(db_path, encoding="utf-8")) if os.path.exists(db_path) else {}
    except Exception:
        db = {}

    info("Fetching profile stats...")
    stats = asyncio.run(_scrape_profile_stats(username))

    if not stats:
        err("Could not fetch stats. Profile may be private or the username is wrong.")
        back_to_menu()
        return

    entry = {
        "date":      datetime.now().strftime("%Y-%m-%d"),
        "followers": stats.get("followers", 0),
        "following": stats.get("following", 0),
        "likes":     stats.get("likes", 0),
        "videos":    stats.get("videos", 0),
    }

    if username not in db:
        db[username] = []
    db[username] = [e for e in db[username] if e["date"] != entry["date"]]  # dedup today
    db[username].append(entry)
    db[username].sort(key=lambda x: x["date"])

    try:
        json.dump(db, open(db_path, "w", encoding="utf-8"), indent=2)
        ok("Snapshot saved.")
    except Exception as e:
        err(f"Could not save: {e}")

    history = db[username]
    divider(f"@{username}  —  {len(history)} snapshots")
    print(f"  {_T.BOLD}{'Date':<12} {'Followers':>12} {'Δ':>10} {'Likes':>14} {'Videos':>8}{_T.R}")
    print(f"  {'-'*12} {'-'*12} {'-'*10} {'-'*14} {'-'*8}")

    for i, e in enumerate(history[-20:]):
        prev  = history[i - 1] if i > 0 else e
        delta = e["followers"] - prev["followers"]
        if delta > 0:
            d_str = f"{_T.GREEN}+{delta:,}{_T.R}"
        elif delta == 0:
            d_str = f"{_T.DIM}—{_T.R}"
        else:
            d_str = f"{_T.YELLOW}{delta:,}{_T.R}"
        print(f"  {e['date']:<12} {e['followers']:>12,}  {d_str:<10}  "
              f"{e['likes']:>14,} {e['videos']:>8,}")

    if len(history) >= 2:
        first, last = history[0], history[-1]
        days   = max(
            (datetime.strptime(last["date"], "%Y-%m-%d") -
             datetime.strptime(first["date"], "%Y-%m-%d")).days, 1
        )
        growth = last["followers"] - first["followers"]
        daily  = growth / days
        col    = _T.GREEN if growth >= 0 else _T.YELLOW
        print(f"\n  {_T.BOLD}Total growth:{_T.R}  {col}{growth:+,}{_T.R} followers over {days} days")
        print(f"  {_T.BOLD}Daily avg   :{_T.R}  {daily:+.0f} followers/day")

    back_to_menu()
