"""
tools/hashtag_analyzer.py
Tool 2  — Hashtag Performance Analyzer (HPA): compare views across hashtags
Tool 7  — Hashtag Frequency: count hashtags from captions in a niche
"""
import asyncio
import re
from collections import Counter, defaultdict
from datetime import datetime

from ui import theme as _T
from utils.helpers import ok, info, err, divider, prompt, save, saved_in, back_to_menu, clear_line
from utils import dirs as _dirs
from core.browser import new_browser


# ── Shared scraper: raw captions from a hashtag page ─────────────────────────

async def _scrape_captions(hashtag: str, target: int) -> list[str]:
    from playwright.async_api import async_playwright
    captions: list[str] = []
    seen: set[str] = set()

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
                    desc = (item.get("desc") or "").strip()
                    if desc:
                        captions.append(desc)
            except Exception:
                pass

        page = await ctx.new_page()
        page.on("response", on_resp)
        await page.goto(f"https://www.tiktok.com/tag/{hashtag}",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
        stale = 0
        while len(seen) < target and stale < 8:
            print(f"  {len(seen)}/{target} captions scraped...", end="\r", flush=True)
            prev_h = await page.evaluate("document.body.scrollHeight")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2.0)
            stale = stale + 1 if await page.evaluate("document.body.scrollHeight") == prev_h else 0
        await browser.close()

    clear_line()
    return captions


# ── Tool 7: Hashtag Frequency ─────────────────────────────────────────────────

def tool_caption():
    divider("HASHTAG FREQUENCY ANALYZER")
    hashtag = prompt("Hashtag (no #)", "edit").lstrip("#")
    target  = int(prompt("Videos to scan", "200") or "200")
    print()
    captions = asyncio.run(_scrape_captions(hashtag, target))

    if not captions:
        err("No captions found."); back_to_menu(); return

    ok(f"Collected {len(captions)} captions\n")

    tag_count = Counter()
    for cap in captions:
        for tag in re.findall(r"#(\w+)", cap.lower()):
            tag_count[tag] += 1

    divider(f"#{hashtag}  —  {len(captions)} captions")
    print(f"  {_T.BOLD}Most used hashtags:{_T.R}\n")
    max_val = max(tag_count.values(), default=1)
    for i, (t, c) in enumerate(tag_count.most_common(30)):
        bar = "#" * min(int(c / max_val * 28), 28)
        pad = "." * (28 - len(bar))
        col = _T.GREEN if i == 0 else (_T.YELLOW if i < 3 else _T.R)
        print(f"    {c:>4}x  {col}#{t:<28}{_T.R}  {_T.DIM}{bar}{pad}{_T.R}")

    date  = datetime.now().strftime("%Y-%m-%d_%H-%M")
    lines = [
        f"Hashtag Frequency: #{hashtag} | {date}",
        f"Videos: {len(captions)}", "=" * 70, "", "TOP HASHTAGS",
    ]
    for t, c in tag_count.most_common(50):
        lines.append(f"  {c}x  #{t}")
    save(_dirs.DIR_HASHTAGS, f"hashtags_{hashtag}_{date}.txt", lines)
    print(); saved_in(_dirs.DIR_HASHTAGS)
    back_to_menu()


# ── Tool 2: Hashtag Performance Analyzer ─────────────────────────────────────

async def _scrape_one_tag(pw, tag: str) -> tuple[str, dict]:
    result = {"views": 0, "videos": 0, "top_views": []}
    seen: set[str] = set()
    browser, ctx = await new_browser(pw, mute=True)

    async def on_resp(response):
        if "item_list" not in response.url:
            return
        try:
            body  = await response.json()
            items = body.get("itemList") or body.get("ItemList") or []
            for item in items:
                vid = str(item.get("id") or "")
                if vid in seen:
                    continue
                seen.add(vid)
                stats = item.get("stats") or item.get("statistics") or {}
                v = int(stats.get("playCount") or stats.get("play_count") or 0)
                result["videos"] += 1
                result["views"]  += v
                result["top_views"].append(v)
        except Exception:
            pass

    page = await ctx.new_page()
    page.on("response", on_resp)
    await page.goto(f"https://www.tiktok.com/tag/{tag}",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(2)
    for _ in range(8):
        print(f"  [~] #{tag}  |  {result['videos']} videos", end="\r", flush=True)
        await page.evaluate("window.scrollBy(0, 2000)")
        await asyncio.sleep(1.0)
    clear_line()
    await browser.close()

    tv = sorted(result["top_views"], reverse=True)
    result["avg"]     = result["views"] // max(result["videos"], 1)
    result["top3avg"] = sum(tv[:3]) // max(len(tv[:3]), 1)
    return tag, result


async def _analyze_hashtags(tags: list[str]) -> dict:
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        tasks   = [_scrape_one_tag(pw, tag) for tag in tags]
        results = await asyncio.gather(*tasks)
    return dict(results)


def tool_hpa():
    divider("HASHTAG PERFORMANCE ANALYZER")
    raw  = prompt("Hashtags (comma-separated, no #)", "edit,fyp,trending")
    tags = [t.strip().lstrip("#") for t in raw.split(",") if t.strip()]
    print()
    info(f"Scanning {len(tags)} hashtags in parallel...\n")
    results = asyncio.run(_analyze_hashtags(tags))
    ranked  = sorted(results.items(), key=lambda x: x[1]["avg"], reverse=True)

    medals = {1: "1st", 2: "2nd", 3: "3rd"}
    divider("RESULTS")
    print(f"  {'#':<4} {'Hashtag':<22} {'Videos':>8} {'Avg Views':>12} {'Top 3 Avg':>12}")
    print(f"  {'-'*4} {'-'*22} {'-'*8} {'-'*12} {'-'*12}")
    for rank, (tag, d) in enumerate(ranked, 1):
        col  = _T.GREEN if rank == 1 else (_T.YELLOW if rank <= 3 else _T.R)
        icon = medals.get(rank, f"{rank}.")
        print(f"  {col}{icon:<4}{_T.R} #{tag:<21} {d['videos']:>8} "
              f"{col}{d['avg']:>12,}{_T.R} {d['top3avg']:>12,}")

    date  = datetime.now().strftime("%Y-%m-%d_%H-%M")
    lines = [f"Hashtag Analysis | {date}", "=" * 60]
    for rank, (tag, d) in enumerate(ranked, 1):
        lines.append(f"  {rank}. #{tag:<20} avg:{d['avg']:>10,}  "
                     f"top3avg:{d['top3avg']:>10,}  videos:{d['videos']}")
    save(_dirs.DIR_ANALYSIS, f"hpa_{date}.txt", lines)
    print(); saved_in(_dirs.DIR_ANALYSIS)
    back_to_menu()
