"""
tools/hashtag_suggester.py
Tool 15 — Hashtag Suggester
Intercepts TikTok's search-suggest API to surface related hashtags.
"""
import asyncio
from datetime import datetime

from ui import theme as _T
from utils.helpers import ok, info, warn, divider, prompt, save, saved_in, back_to_menu
from utils import dirs as _dirs
from core.browser import new_browser


async def _scrape_hashtag_suggestions(seed: str) -> list[str]:
    from playwright.async_api import async_playwright
    results: list[str] = []

    async with async_playwright() as pw:
        browser, ctx = await new_browser(pw, mute=True)
        page  = await ctx.new_page()
        sugg:  list[str] = []

        async def on_resp(r):
            if "search_suggest" not in r.url and "suggest" not in r.url:
                return
            try:
                body = await r.json()
                for item in (body.get("sug_list") or body.get("data") or []):
                    kw = item.get("keyword") or item.get("content") or ""
                    if kw:
                        sugg.append(kw.lstrip("#"))
            except Exception:
                pass

        page.on("response", on_resp)
        import urllib.parse as _up
        await page.goto(f"https://www.tiktok.com/search?q=%23{_up.quote(seed)}",
                        wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(3)

        # Also scrape visible hashtag chips on the search results page
        try:
            chips = await page.query_selector_all(
                '[data-e2e="search-hashtag-item"], .tiktok-hashtag-item, [href*="/tag/"]'
            )
            for chip in chips:
                text = await chip.inner_text()
                if text:
                    sugg.append(text.lstrip("#").strip())
        except Exception:
            pass

        await browser.close()

        # Deduplicate preserving order
        seen: set[str] = set()
        for s in sugg:
            if s and s.lower() not in seen:
                seen.add(s.lower())
                results.append(s)

    return results


def tool_hashsugg():
    divider("HASHTAG SUGGESTER")
    print(f"  {_T.DIM}Finds related hashtags from TikTok search suggestions.{_T.R}\n")
    seed = prompt("Enter a topic or hashtag (no #)", "edit").lstrip("#")
    if not seed:
        back_to_menu(); return

    print()
    info(f"Fetching suggestions for #{seed}...")
    suggestions = asyncio.run(_scrape_hashtag_suggestions(seed))
    if not suggestions:
        warn("No suggestions found. TikTok may have blocked the request.")
        back_to_menu(); return

    divider(f"Hashtag suggestions for #{seed}")
    for i, s in enumerate(suggestions[:40], 1):
        col = _T.GREEN if i <= 3 else _T.R
        print(f"  {col}{i:>2}.{_T.R}  {_T.BOLD}#{s}{_T.R}")

    date  = datetime.now().strftime("%Y-%m-%d_%H-%M")
    lines = [f"Hashtag Suggestions: #{seed} | {date}", "=" * 60]
    for s in suggestions:
        lines.append(f"  #{s}")
    save(_dirs.DIR_HASHTAGS, f"suggestions_{seed}_{date}.txt", lines)
    print(); saved_in(_dirs.DIR_HASHTAGS)
    back_to_menu()
