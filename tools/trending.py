"""
tools/trending.py
Tool 1.5 — TikTok Trending Now
Scrapes TikTok's global trending / discover page for sounds and videos
that are blowing up RIGHT NOW — not filtered by niche, just raw momentum.
"""
import asyncio
import re
from collections import Counter
from datetime import datetime

from ui import theme as _T
from utils.helpers import ok, info, err, warn, divider, save, saved_in, prompt, back_to_menu, clear_line
from utils import dirs as _dirs
from utils.validator import validate_sounds, validate_videos
from core.browser import new_browser
from core.filters import check_garbage, is_funk


# ── Scraper ───────────────────────────────────────────────────────────────────

async def _scrape_trending(target: int) -> tuple[list, list]:
    """
    Returns (trending_sounds, trending_videos).
    Hits /api/explore/item_list and the Trending/Discover tab.
    """
    from playwright.async_api import async_playwright
    sounds_counter: Counter = Counter()
    sound_meta: dict = {}
    videos: list = []
    seen: set = set()

    async with async_playwright() as pw:
        browser, ctx = await new_browser(pw, mute=True)

        async def on_resp(response):
            url = response.url
            # Catch both explore/trending and any item_list endpoints
            if not any(k in url for k in ("item_list", "explore", "trending", "recommend")):
                return
            try:
                body  = await response.json()
                items = (body.get("itemList")
                      or body.get("item_list")
                      or body.get("items")
                      or body.get("data", {}).get("itemList")
                      or [])
                for item in items:
                    vid = str(item.get("id") or "")
                    if not vid or vid in seen:
                        continue
                    seen.add(vid)
                    stats  = item.get("stats") or item.get("statistics") or {}
                    music  = item.get("music") or {}
                    author = item.get("author") or {}
                    views  = int(stats.get("playCount") or stats.get("play_count") or 0)

                    title  = (music.get("title") or "").strip()
                    artist = (music.get("authorName") or music.get("author_name") or "").strip()
                    mid    = str(music.get("id") or "")

                    if title and mid:
                        sounds_counter[mid] += 1
                        sound_meta[mid] = {"title": title, "author": artist, "id": mid}

                    videos.append({
                        "views": views,
                        "likes": int(stats.get("diggCount") or stats.get("digg_count") or 0),
                        "desc":  (item.get("desc") or "").strip()[:120],
                        "user":  (author.get("uniqueId") or author.get("unique_id") or ""),
                        "sound": title,
                        "id":    vid,
                    })
            except Exception:
                pass

        page = await ctx.new_page()
        page.on("response", on_resp)

        # Hit both the trending tab and the explore API directly
        await page.goto("https://www.tiktok.com/explore",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        stale = 0
        while len(seen) < target and stale < 6:
            print(f"  Captured {len(seen)} videos...", end="\r", flush=True)
            prev = await page.evaluate("document.body.scrollHeight")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2.5)
            new_h = await page.evaluate("document.body.scrollHeight")
            stale = stale + 1 if new_h == prev else 0

        await browser.close()

    clear_line()

    # Build sorted sound list — apply same garbage filter as audio_scraper
    top_sounds = []
    removed_sounds = []
    for mid, count in sounds_counter.most_common():
        meta   = sound_meta.get(mid, {})
        title  = meta.get("title", "Unknown")
        author = meta.get("author", "")
        reason = check_garbage(title, author)
        entry  = {"title": title, "author": author, "count": count, "funk": is_funk(title)}
        if reason:
            removed_sounds.append(entry)
        else:
            top_sounds.append(entry)

    videos.sort(key=lambda x: x["views"], reverse=True)
    return top_sounds, removed_sounds, videos


# ── Tool ──────────────────────────────────────────────────────────────────────

def tool_trending():
    divider("TIKTOK TRENDING NOW")
    print(f"  {_T.DIM}Scrapes TikTok's global Explore/Trending page — no hashtag filter.{_T.R}")
    print(f"  {_T.DIM}Shows what's blowing up RIGHT NOW across all niches.{_T.R}\n")

    target = int(prompt("Videos to capture", "300") or "300")
    top_n  = int(prompt("Show top N results per category", "20") or "20")
    print()
    info("Opening TikTok Explore page...")
    info("Capturing trending content — this takes 30-60 seconds...\n")

    sounds, removed_sounds, videos = asyncio.run(_scrape_trending(target))

    # Validate
    ok_s, msg_s = validate_sounds(len(videos), sounds)
    ok_v, msg_v = validate_videos(len(videos), videos)
    if not ok_s:
        warn(msg_s)
    if not ok_v:
        warn(msg_v)

    if not sounds and not removed_sounds and not videos:
        err("Nothing captured — TikTok may have blocked the request or changed their page.")
        info("Try again in a few minutes.")
        back_to_menu(); return

    ok(f"Captured {len(videos)} videos | {len(sounds)} sounds kept | {len(removed_sounds)} filtered\n")

    # ── Display ───────────────────────────────────────────────────────────────
    if sounds:
        divider(f"TOP {min(top_n, len(sounds))} TRENDING SOUNDS")
        print(f"  {'#':<4} {'Sound':<45} {'Artist':<24} {'Used'}")
        print(f"  {'-'*4} {'-'*45} {'-'*24} {'-'*6}")
        for i, s in enumerate(sounds[:top_n], 1):
            col  = _T.GREEN if i <= 3 else _T.R
            name = (s["title"][:42] + "...") if len(s["title"]) > 45 else s["title"]
            art  = (s["author"][:22] + "..") if len(s["author"]) > 24 else s["author"]
            print(f"  {col}{i:<4}{_T.R} {name:<45} {_T.DIM}{art:<24}{_T.R} {_T.CYAN}{s['count']}x{_T.R}")

    print()

    if videos:
        divider(f"TOP {min(top_n, len(videos))} TRENDING VIDEOS")
        print(f"  {'#':<4} {'Views':>10}  {'@User':<22}  Caption")
        print(f"  {'-'*4} {'-'*10}  {'-'*22}  {'-'*40}")
        for i, v in enumerate(videos[:top_n], 1):
            col  = _T.GREEN if i <= 3 else _T.R
            desc = (v["desc"][:45] + "...") if len(v["desc"]) > 48 else v["desc"]
            user = (v["user"][:20] + "..") if len(v["user"]) > 22 else v["user"]
            link = f"https://www.tiktok.com/@{v['user']}/video/{v['id']}"
            print(f"  {col}{i:<4}{_T.R} {col}{v['views']:>10,}{_T.R}  {_T.DIM}@{user:<21}{_T.R}  {desc}")
            print(f"       {_T.DIM}{link}{_T.R}")

    # ── Save TXT + HTML ───────────────────────────────────────────────────────
    date  = datetime.now().strftime("%Y-%m-%d_%H-%M")
    lines = [
        f"TikTok Trending Now | {date}",
        f"Captured {len(videos)} videos | {len(sounds)} unique sounds",
        "=" * 90, "",
        "TOP TRENDING SOUNDS",
    ]
    for i, s in enumerate(sounds[:50], 1):
        lines.append(f"  {i:>2}. {s['count']}x  {s['title'][:50]}  —  {s['author']}")
    lines += ["", "TOP TRENDING VIDEOS"]
    for i, v in enumerate(videos[:50], 1):
        link = f"https://www.tiktok.com/@{v['user']}/video/{v['id']}"
        lines.append(f"  {i:>2}. {v['views']:>10,} views  @{v['user']:<22}  {v['desc'][:70]}")
        lines.append(f"      {link}")

    save(_dirs.DIR_SOUNDS, f"trending_{date}.txt", lines)

    from utils.html_report import save_viral_report, _save_and_open
    print()
    saved_in(_dirs.DIR_SOUNDS)
    _save_and_open(save_viral_report, "trending", videos, _dirs.DIR_SOUNDS,
                   label="Trending Report")

    back_to_menu()
