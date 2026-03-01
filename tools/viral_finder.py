"""
tools/viral_finder.py
Tool 10 — Viral Video Finder
Scrapes a hashtag page and ranks videos by view count.
"""
import asyncio
from datetime import datetime

from ui import theme as _T
from utils.helpers import ok, err, warn, divider, prompt, save, saved_in, back_to_menu, clear_line
from utils.validator import validate_videos
from utils.html_report import save_viral_report, _save_and_open
from utils import dirs as _dirs
from core.browser import new_browser


async def _scrape_viral(hashtag: str, target: int, progress_cb=None) -> list[dict]:
    from playwright.async_api import async_playwright
    videos: list[dict] = []
    seen:   set[str]   = set()

    async with async_playwright() as pw:
        browser, ctx = await new_browser(pw, mute=True)

        async def on_resp(response):
            if "item_list" not in response.url:
                return
            try:
                body  = await response.json()
                items = body.get("itemList") or body.get("ItemList") or []
                for item in items:
                    vid = str(item.get("id") or "")
                    if not vid or vid in seen:
                        continue
                    seen.add(vid)
                    stats  = item.get("stats") or item.get("statistics") or {}
                    music  = item.get("music") or {}
                    author = item.get("author") or {}
                    videos.append({
                        "views": int(stats.get("playCount") or stats.get("play_count") or 0),
                        "likes": int(stats.get("diggCount") or stats.get("digg_count") or 0),
                        "desc":  (item.get("desc") or "").strip()[:120],
                        "user":  (author.get("uniqueId") or author.get("unique_id") or ""),
                        "sound": (music.get("title") or "").strip(),
                        "ts":    int(item.get("createTime") or 0),
                        "id":    vid,
                    })
            except Exception:
                pass

        page = await ctx.new_page()
        page.on("response", on_resp)
        await page.goto(f"https://www.tiktok.com/tag/{hashtag}",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
        stale = 0
        while len(seen) < target and stale < 8:
            print(f"  {len(seen)}/{target} videos...", end="\r", flush=True)
            if progress_cb: progress_cb(len(seen), target)
            prev_h = await page.evaluate("document.body.scrollHeight")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2.0)
            stale = stale + 1 if await page.evaluate("document.body.scrollHeight") == prev_h else 0
        await browser.close()

    clear_line()
    return videos


def tool_viral():
    divider("VIRAL VIDEO FINDER")
    hashtag = prompt("Hashtag (no #)", "edit").lstrip("#")
    target  = int(prompt("Videos to scan", "300") or "300")
    top_n   = int(prompt("Show top N videos", "20") or "20")
    print()
    videos = asyncio.run(_scrape_viral(hashtag, target))
    valid, msg = validate_videos(len(videos), videos)
    if not valid:
        warn(msg)
    if not videos:
        err("No videos found."); back_to_menu(); return

    videos.sort(key=lambda x: x["views"], reverse=True)
    avg = sum(v["views"] for v in videos) // max(len(videos), 1)
    ok(f"Scanned {len(videos)} videos | avg {avg:,} views\n")

    divider(f"TOP {min(top_n, len(videos))} in #{hashtag}")
    print(f"  {'#':<4} {'Views':>10} {'Likes':>8}  {'@User':<22}  Caption")
    print(f"  {'-'*4} {'-'*10} {'-'*8}  {'-'*22}  {'-'*40}")
    for rank, v in enumerate(videos[:top_n], 1):
        col  = _T.GREEN if rank <= 3 else _T.R
        desc = (v["desc"][:38] + "...") if len(v["desc"]) > 40 else v["desc"]
        user = (v["user"][:20] + "..") if len(v["user"]) > 22 else v["user"]
        link = f"https://www.tiktok.com/@{v['user']}/video/{v['id']}"
        print(f"  {col}{rank:<4}{_T.R} {col}{v['views']:>10,}{_T.R} {v['likes']:>8,}  "
              f"{_T.DIM}@{user:<21}{_T.R}  {desc}")
        print(f"       {_T.DIM}{link}{_T.R}")

    date  = datetime.now().strftime("%Y-%m-%d_%H-%M")
    lines = [f"Viral Videos: #{hashtag} | {date}",
             f"Scanned {len(videos)} | Avg {avg:,} views", "=" * 90]
    for rank, v in enumerate(videos[:50], 1):
        link = f"https://www.tiktok.com/@{v['user']}/video/{v['id']}"
        lines.append(f"  {rank}. {v['views']:>10,} views  @{v['user']:<22}  {v['desc'][:80]}")
        lines.append(f"     Sound: {v['sound']}")
        lines.append(f"     {link}")
        lines.append("")
    save(_dirs.DIR_VIRAL, f"viral_{hashtag}_{date}.txt", lines)
    print(); saved_in(_dirs.DIR_VIRAL)
    _save_and_open(save_viral_report, hashtag, videos, _dirs.DIR_VIRAL,
                   label="Viral Report")
    back_to_menu()
