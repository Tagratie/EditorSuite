"""
tools/cross_hashtag.py
Tool 9 — Cross-Hashtag Sound Finder
Scrapes multiple hashtags simultaneously, then surfaces sounds that
trend across all of them.
"""
import asyncio
from datetime import datetime

from ui import theme as _T
from utils.helpers import ok, info, err, warn, divider, prompt, save, saved_in, back_to_menu
from utils import dirs as _dirs
from core.browser import new_browser
from core.filters import check_garbage


async def _scrape_tag_sounds(pw, hashtag: str, target: int = 300) -> tuple[dict, set]:
    sounds: dict = {}
    seen:   set  = set()

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
                m   = item.get("music") or {}
                t   = (m.get("title") or "").strip()
                a   = (m.get("authorName") or m.get("author") or "").strip()
                mid = str(m.get("id") or t or "unknown")
                if check_garbage(t, a):
                    continue
                if mid not in sounds:
                    sounds[mid] = {"title": t, "author": a, "count": 0}
                sounds[mid]["count"] += 1
        except Exception:
            pass

    browser, ctx = await new_browser(pw, mute=True)
    page = await ctx.new_page()
    page.on("response", on_resp)
    try:
        await page.goto(f"https://www.tiktok.com/tag/{hashtag}",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
        stale = 0
        while len(seen) < target and stale < 8:
            prev_h = await page.evaluate("document.body.scrollHeight")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1.8)
            stale = stale + 1 if await page.evaluate("document.body.scrollHeight") == prev_h else 0
    except Exception:
        pass
    await browser.close()
    return sounds, seen


def tool_crosshash():
    from playwright.async_api import async_playwright

    divider("CROSS-HASHTAG SOUND FINDER")
    print(f"  {_T.DIM}Finds sounds trending across ALL your hashtags simultaneously.{_T.R}\n")
    raw  = prompt("Hashtags (comma-separated, no #)", "edit,fyp,trending")
    tags = [t.strip().lstrip("#") for t in raw.split(",") if t.strip()]
    if not tags:
        err("No hashtags entered."); back_to_menu(); return
    target = int(prompt("Videos per hashtag", "300") or "300")
    print()

    tag_sounds: dict = {}

    async def _run_all():
        async with async_playwright() as pw:
            for tag in tags:
                info(f"Scanning #{tag}...")
                sounds, seen = await _scrape_tag_sounds(pw, tag, target)
                tag_sounds[tag] = sounds
                ok(f"#{tag}: {len(seen)} videos, {len(sounds)} sounds")

    asyncio.run(_run_all())

    # Find sounds present in ≥2 hashtags
    all_mids = set()
    for s in tag_sounds.values():
        all_mids.update(s.keys())

    cross: dict = {}
    for mid in all_mids:
        present_in = [t for t in tags if mid in tag_sounds.get(t, {})]
        if len(present_in) < 2:
            continue
        total  = sum(tag_sounds[t][mid]["count"] for t in present_in)
        title  = next((tag_sounds[t][mid]["title"]  for t in present_in), mid)
        author = next((tag_sounds[t][mid]["author"] for t in present_in), "")
        cross[mid] = {"tags": present_in, "total": total, "title": title, "author": author}

    ranked = sorted(cross.items(), key=lambda x: (len(x[1]["tags"]), x[1]["total"]), reverse=True)

    divider(f"SOUNDS ACROSS {len(tags)} HASHTAGS")
    if not ranked:
        warn("No sounds found across multiple hashtags. Try scanning more videos.")
        back_to_menu(); return

    print(f"  {'Song':<36} {'Artist':<20} {'Tags':>5}  Hashtags")
    print(f"  {'-'*36} {'-'*20} {'-'*5}  {'-'*40}")
    for _, data in ranked[:30]:
        col     = (_T.GREEN if len(data["tags"]) == len(tags)
                   else (_T.YELLOW if len(data["tags"]) >= 3 else _T.R))
        tag_str = ", ".join(f"#{t}" for t in data["tags"])
        title   = (data["title"][:33]  + "...") if len(data["title"])  > 36 else data["title"]
        author  = (data["author"][:17] + "...") if len(data["author"]) > 20 else data["author"]
        print(f"  {col}{_T.BOLD}{title:<36}{_T.R} {_T.DIM}{author:<20}{_T.R} "
              f"{col}{len(data['tags']):>5}{_T.R}  {_T.DIM}{tag_str}{_T.R}")

    date  = datetime.now().strftime("%Y-%m-%d_%H-%M")
    lines = [f"Cross-Hashtag Sounds | {','.join('#'+t for t in tags)} | {date}", "=" * 70]
    for _, data in ranked:
        lines.append(f"  {data['title']:<40}  {data['author']:<24}  "
                     f"{len(data['tags'])} tags: {', '.join(data['tags'])}")
    save(_dirs.DIR_ANALYSIS, f"cross_{'+'.join(tags)}_{date}.txt", lines)
    print(); saved_in(_dirs.DIR_ANALYSIS)
    back_to_menu()
