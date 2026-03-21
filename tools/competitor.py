"""
tools/competitor.py
Tool 3 — Competitor Tracker
Scrapes two TikTok profiles side-by-side and produces a head-to-head report.
"""
import asyncio
from collections import defaultdict
from datetime import datetime

from ui import theme as _T
from utils.helpers import ok, err, warn, divider, prompt, save, saved_in, back_to_menu, clear_line, get_stat, unwrap_item
from utils import dirs as _dirs
from utils.config import get_my_username, set_my_username
from core.browser import new_browser
from core.filters import check_garbage


# ── Profile scraper ───────────────────────────────────────────────────────────

def _live_post_line(p: dict, avg: int, col: str) -> str:
    c = col if p["views"] > avg else _T.R
    s = (p["sound"][:30] + "...") if len(p["sound"]) > 33 else p["sound"]
    return (f"  {p['date']:<18} {c}{p['views']:>10,}{_T.R} "
            f"{p['likes']:>8,} {p['shares']:>8,}  {_T.DIM}{s}{_T.R}")


async def _scrape_profile(ctx, username: str,
                           live_col: str | None = None,
                           live_avg_ref: list | None = None) -> tuple[str, list]:
    """Scrape a profile using an existing browser context (new tab)."""
    posts: list[dict] = []
    seen:  set[str]   = set()
    has_more          = True

    async def on_resp(response):
        nonlocal has_more
        if "/api/post/item_list" not in response.url:
            return
        try:
            body = await response.json()
            if not body.get("hasMore", 1):
                has_more = False
            for item in body.get("itemList") or []:
                item = unwrap_item(item)
                vid = str(item.get("id") or "")
                if not vid or vid in seen:
                    continue
                seen.add(vid)
                music  = item.get("music") or {}
                ts     = int(item.get("createTime") or 0)
                posts.append({
                    "views":  get_stat(item, "playCount", "play_count", "viewCount", "view_count", "views"),
                    "likes":  get_stat(item, "diggCount", "digg_count", "likeCount", "like_count"),
                    "shares": get_stat(item, "shareCount", "share_count"),
                    "sound":  (music.get("title") or "").strip(),
                    "ts":     ts,
                    "date":   datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "?",
                })
        except Exception:
            pass

    pages = ctx.pages
    page = pages[0] if pages else await ctx.new_page()
    page.on("response", on_resp)
    await page.goto(f"https://www.tiktok.com/@{username}",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(4)
    try:
        await page.click("body")
    except Exception:
        pass

    last = 0; stale = 0; total_scrolls = 0; printed = 0
    while has_more and stale < 12:
        if not live_col:
            print(f"  [~] @{username}  |  {len(posts)} posts", end="\r", flush=True)
        else:
            while printed < len(posts):
                avg = live_avg_ref[0] if live_avg_ref else 0
                print(_live_post_line(posts[printed], avg, live_col), flush=True)
                printed += 1
                if printed < len(posts):
                    await asyncio.sleep(0.01)

        await page.evaluate("window.scrollBy(0, 800)")
        total_scrolls += 1
        await asyncio.sleep(2.0)
        if not has_more:
            break
        stale = 0 if len(posts) != last else stale + 1
        if stale > 0:
            await page.evaluate("window.scrollBy(0, 3000)")
            await asyncio.sleep(3.0)
        last = len(posts)
        if len(posts) >= 500:
            break

    if not live_col:
        clear_line()
    await asyncio.sleep(4.0)

    # Flush any posts that arrived in the final API batch
    if live_col:
        while printed < len(posts):
            avg = live_avg_ref[0] if live_avg_ref else 0
            print(_live_post_line(posts[printed], avg, live_col), flush=True)
            printed += 1

    await page.close()
    ok(f"@{username}: {len(posts)} posts  ({total_scrolls} scrolls)")
    return username, posts


# ── Analysis helpers ──────────────────────────────────────────────────────────

def _analyze_posts(posts: list[dict]) -> dict:
    if not posts:
        return {"avg": 0, "total": 0, "count": 0, "top_views": [], "sounds": []}
    total = sum(p["views"] for p in posts)
    avg   = total // len(posts)
    sc: defaultdict[str, int] = defaultdict(int)
    for p in posts:
        if p["sound"] and not check_garbage(p["sound"], ""):
            sc[p["sound"]] += 1
    return {
        "avg":       avg,
        "total":     total,
        "count":     len(posts),
        "top_views": sorted((p["views"] for p in posts), reverse=True),
        "sounds":    sorted(sc.items(), key=lambda x: x[1], reverse=True)[:5],
    }


def _print_account_block(label: str, posts: list[dict], stats: dict, col: str) -> None:
    avg  = stats["avg"]
    peak = stats["top_views"][0] if stats["top_views"] else 0
    print(f"  {col}{_T.BOLD}{label}{_T.R}")
    print(f"  {_T.DIM}{'-'*50}{_T.R}")
    print(f"  Posts      : {stats['count']}   "
          f"Avg: {col}{avg:>10,}{_T.R}   "
          f"Peak: {col}{peak:>12,}{_T.R}")
    print()
    display = sorted(posts, key=lambda x: x["ts"], reverse=True)[:100]
    if len(posts) > len(display):
        print(f"  {_T.DIM}Showing {len(display)} most recent of {len(posts)} total "
              f"(all used for stats){_T.R}\n")
    print(f"  {'Date':<18} {'Views':>10} {'Likes':>8} {'Shares':>8}  Sound")
    print(f"  {'-'*18} {'-'*10} {'-'*8} {'-'*8}  {'-'*36}")
    for p in display:
        c = col if p["views"] > avg else _T.R
        s = (p["sound"][:34] + "...") if len(p["sound"]) > 36 else p["sound"]
        print(f"  {p['date']:<18} {c}{p['views']:>10,}{_T.R} "
              f"{p['likes']:>8,} {p['shares']:>8,}  {_T.DIM}{s}{_T.R}")


# ── Tool entrypoint ───────────────────────────────────────────────────────────

def tool_ct():
    divider("COMPETITOR TRACKER")
    my_user = get_my_username()
    if not my_user:
        warn("Your account is not set.")
        my_user = set_my_username(prompt("Your TikTok username"))
    else:
        print(f"  {_T.DIM}Your account: @{my_user}{_T.R}")
        if input(f"  {_T.CYAN}>{_T.R} Change it? [y/N]: ").strip().lower() == "y":
            my_user = set_my_username(prompt("Your TikTok username"))

    comp_user = prompt("Competitor username").lstrip("@")
    if not comp_user:
        err("No competitor username."); back_to_menu(); return

    async def scrape_sequential():
        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            browser, ctx = await new_browser(pw, mute=True)
            try:
                divider(f"LIVE  @{my_user}")
                print(f"  {'Date':<18} {'Views':>10} {'Likes':>8} {'Shares':>8}  Sound")
                print(f"  {'-'*18} {'-'*10} {'-'*8} {'-'*8}  {'-'*33}")
                _, my_posts = await _scrape_profile(ctx, my_user, live_col=_T.GREEN, live_avg_ref=[0])
                print()
                divider(f"LIVE  @{comp_user}")
                print(f"  {'Date':<18} {'Views':>10} {'Likes':>8} {'Shares':>8}  Sound")
                print(f"  {'-'*18} {'-'*10} {'-'*8} {'-'*8}  {'-'*33}")
                _, comp_posts = await _scrape_profile(ctx, comp_user, live_col=_T.YELLOW, live_avg_ref=[0])
            finally:
                await browser.close()
        return my_posts, comp_posts

    print()
    my_posts, comp_posts = asyncio.run(scrape_sequential())
    if not my_posts and not comp_posts:
        err("Could not scrape either account."); back_to_menu(); return

    my_s   = _analyze_posts(my_posts)
    comp_s = _analyze_posts(comp_posts)

    divider("HEAD TO HEAD")
    print(f"  {'Metric':<22} {_T.GREEN}@{my_user:<22}{_T.R} {_T.YELLOW}@{comp_user:<22}{_T.R}")
    print(f"  {'-'*22} {'-'*24} {'-'*24}")

    def cmp_row(label, mine, theirs):
        mb = _T.GREEN if mine >= theirs else _T.RED
        tb = _T.GREEN if theirs >= mine else _T.RED
        print(f"  {label:<22} {mb}{mine:<24,}{_T.R} {tb}{theirs:<24,}{_T.R}")

    cmp_row("Posts scraped",    my_s["count"],         comp_s["count"])
    cmp_row("Avg views",        my_s["avg"],           comp_s["avg"])
    cmp_row("Peak views",       my_s["top_views"][0] if my_s["top_views"]   else 0,
                                comp_s["top_views"][0] if comp_s["top_views"] else 0)

    print(f"\n  {_T.BOLD}Your top sounds:{_T.R}")
    for s, c in my_s["sounds"]:
        print(f"    {c}x  {s[:55]}")
    print(f"\n  {_T.BOLD}Competitor top sounds:{_T.R}")
    for s, c in comp_s["sounds"]:
        print(f"    {c}x  {s[:55]}")

    divider(f"DETAIL  @{my_user}")
    _print_account_block(f"@{my_user}", my_posts, my_s, _T.GREEN)
    divider(f"DETAIL  @{comp_user}")
    _print_account_block(f"@{comp_user}", comp_posts, comp_s, _T.YELLOW)

    date  = datetime.now().strftime("%Y-%m-%d_%H-%M")
    lines = [f"Competitor Report | @{my_user} vs @{comp_user} | {date}", "=" * 80,
             f"  Your avg views     : {my_s['avg']:,}",
             f"  Competitor avg views: {comp_s['avg']:,}",
             "", "YOUR TOP SOUNDS"]
    for s, c in my_s["sounds"]:
        lines.append(f"  {c}x  {s}")
    lines.append("\nCOMPETITOR TOP SOUNDS")
    for s, c in comp_s["sounds"]:
        lines.append(f"  {c}x  {s}")
    save(_dirs.DIR_COMPETE, f"vs_{my_user}_vs_{comp_user}_{date}.txt", lines)
    print(); saved_in(_dirs.DIR_COMPETE)
    back_to_menu()
