"""
tools/audio_scraper.py
Tool 1 — Trending Audio Scraper
Scrapes TikTok hashtag + search pages for trending sounds.
"""
import asyncio
import os
from datetime import datetime

from ui import theme as _T
from utils.helpers import ok, info, err, divider, prompt, save, saved_in, back_to_menu, clear_line
from utils import dirs as _dirs
from core.browser import new_browser
from core.filters import check_garbage, is_funk


# ── Core scraper ──────────────────────────────────────────────────────────────

async def scrape_sounds(hashtag: str, target: int) -> tuple[int, dict]:
    """
    Dual-source scrape: hashtag page + search page.
    Returns (videos_seen_count, sounds_dict).
    """
    from playwright.async_api import async_playwright

    sounds     = {}
    seen       = set()
    new_sounds = []
    printed    = 0

    def _ingest(items):
        for item in items:
            if isinstance(item, dict) and "item" in item:
                item = item["item"]
            vid = str(item.get("id") or "")
            if not vid or vid in seen:
                return
            seen.add(vid)
            m   = item.get("music") or {}
            t   = (m.get("title") or "").strip()
            a   = (m.get("authorName") or m.get("author") or "").strip()
            mid = str(m.get("id") or t or "unknown")
            is_new = mid not in sounds
            if is_new:
                sounds[mid] = {
                    "title": t, "author": a, "count": 0,
                    "reason": check_garbage(t, a), "funk": is_funk(t),
                }
            sounds[mid]["count"] += 1
            if is_new and not sounds[mid]["reason"]:
                new_sounds.append(sounds[mid])

    def _flush_print():
        nonlocal printed
        while printed < len(new_sounds):
            s   = new_sounds[printed]
            num = printed + 1
            t   = (s["title"][:35] + "...") if len(s["title"]) > 38 else s["title"]
            a   = (s["author"][:21] + "...") if len(s["author"]) > 24 else s["author"]
            fk  = f"{_T.MAGENTA}[FUNK]{_T.R}" if s["funk"] else ""
            col = _T.CYAN if num <= 3 else _T.R
            print(f"  {col}{num:<5}{_T.R} {_T.BOLD}{t:<38}{_T.R} {_T.DIM}{a:<24}{_T.R} {fk}", flush=True)
            printed += 1

    def _status(phase: str):
        print(f"  {len(seen)}/{target} videos  |  {_T.GREEN}{len(new_sounds)}{_T.R} songs  "
              f"{_T.DIM}[{phase}]{_T.R}", end="\r", flush=True)

    async def _scroll_until_stale(page, label: str, max_stale: int = 8):
        stale = 0
        while len(seen) < target and stale < max_stale:
            _flush_print()
            _status(label)
            prev_h = await page.evaluate("document.body.scrollHeight")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2.0)
            new_h = await page.evaluate("document.body.scrollHeight")
            stale = stale + 1 if new_h == prev_h else 0

    print()
    print(f"  {'#':<5} {'Song':<38} {'Artist':<24} {'Tag':<6}")
    print(f"  {'-'*5} {'-'*38} {'-'*24} {'-'*6}")
    info(f"Scanning #{hashtag}...")

    async with async_playwright() as pw:
        # Phase 1: hashtag page (~280 video cap)
        browser, ctx = await new_browser(pw, mute=True)

        async def on_resp_tag(response):
            if "item_list" not in response.url:
                return
            try:
                body  = await response.json()
                items = body.get("itemList") or body.get("ItemList") or []
                _ingest(items)
            except Exception:
                pass

        page = await ctx.new_page()
        page.on("response", on_resp_tag)
        try:
            await page.goto(f"https://www.tiktok.com/tag/{hashtag}",
                            wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            await _scroll_until_stale(page, "hashtag page")
        except Exception:
            pass
        await browser.close()
        _flush_print()

        # Phase 2: search page — different API, no 280-cap
        if len(seen) < target:
            browser, ctx = await new_browser(pw, mute=True)

            async def on_resp_search(response):
                if "/api/search/" not in response.url:
                    return
                try:
                    body  = await response.json()
                    items = (body.get("data") or body.get("itemList") or
                             body.get("ItemList") or [])
                    _ingest(items)
                except Exception:
                    pass

            page2 = await ctx.new_page()
            page2.on("response", on_resp_search)
            try:
                import urllib.parse as _up
                q = _up.quote(f"#{hashtag}")
                await page2.goto(f"https://www.tiktok.com/search/video?q={q}",
                                 wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
                await _scroll_until_stale(page2, "search page", max_stale=12)
            except Exception:
                pass
            await browser.close()
            _flush_print()

    clear_line()
    return len(seen), sounds


async def scrape_for_spotify(hashtag: str, videos: int) -> tuple[int, dict]:
    return await scrape_sounds(hashtag, videos)


# ── Download helper ───────────────────────────────────────────────────────────

def download_via_ytdlp(title: str, artist: str) -> str | None:
    """Download a song as MP3 using yt-dlp. Returns saved path or None."""
    import subprocess
    import shutil
    dl_path = _dirs.DIR_AUDIO
    os.makedirs(dl_path, exist_ok=True)
    if not shutil.which("yt-dlp"):
        err("yt-dlp not found. Install with:  pip install yt-dlp")
        return None
    query   = f"{title} {artist}".strip()
    out_tpl = os.path.join(dl_path, "%(title)s.%(ext)s")
    cmd = [
        "yt-dlp", f"ytsearch1:{query}",
        "--extract-audio", "--audio-format", "mp3",
        "--audio-quality", "0",
        "--output", out_tpl,
        "--no-playlist", "--quiet", "--progress",
    ]
    info(f"Searching YouTube for: {query}")
    try:
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode == 0:
            mp3s = sorted(
                [f for f in os.listdir(dl_path) if f.endswith(".mp3")],
                key=lambda f: os.path.getmtime(os.path.join(dl_path, f)),
                reverse=True,
            )
            return os.path.join(dl_path, mp3s[0]) if mp3s else None
        err("yt-dlp returned an error.")
        return None
    except Exception as e:
        err(f"Download failed: {e}")
        return None


# ── Chart display ─────────────────────────────────────────────────────────────

def show_chart_and_download(hashtag, top_n, scanned, kept, removed_count):
    if not kept:
        err("No songs to display.")
        return

    max_c  = kept[0]["count"]
    medals = {1: "1st", 2: "2nd", 3: "3rd"}

    divider(f"TOP {min(top_n, len(kept))} in #{hashtag}")
    print(f"  {'#':<4} {'Song':<36} {'Artist':<22}  {'':6}  {'Videos':>7}  Chart")
    print(f"  {'-'*4} {'-'*36} {'-'*22}  {'-'*6}  {'-'*7}  {'-'*22}")

    for rank, r in enumerate(kept[:top_n], 1):
        t    = (r["title"][:33]  + "...") if len(r["title"])  > 36 else r["title"]
        a    = (r["author"][:19] + "...") if len(r["author"]) > 22 else r["author"]
        bar  = "#" * int((r["count"] / max_c) * 20) + "." * (20 - int((r["count"] / max_c) * 20))
        col  = _T.GREEN if rank == 1 else (_T.YELLOW if rank <= 3 else _T.R)
        icon = medals.get(rank, f"{rank:>3}.")
        fv   = f"{_T.MAGENTA}[FUNK]{_T.R}" if r["funk"] else "      "
        print(f"  {col}{icon:<4}{_T.R} {_T.BOLD}{t:<36}{_T.R} {_T.DIM}{a:<22}{_T.R}  {fv}  "
              f"{col}{r['count']:>7}{_T.R}  {col}{bar}{_T.R}")

    print(f"\n  {_T.DIM}Videos: {scanned} | Kept: {len(kept)} | Filtered: {removed_count}{_T.R}\n")

    choice = input(
        f"  {_T.CYAN}>{_T.R} Enter 1-{min(top_n, len(kept))} to download a song, or Enter to skip: "
    ).strip()
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(kept[:top_n]):
            song = kept[idx]
            print()
            info(f"Downloading: {song['title']} - {song['author']}")
            dest = download_via_ytdlp(song["title"], song["author"])
            if dest:
                print(); ok(f"Saved to: {dest}")
            else:
                err("Download did not complete.")
        else:
            err("Number out of range.")


# ── Tool entrypoint ───────────────────────────────────────────────────────────

def tool_scraper():
    divider("TRENDING AUDIO SCRAPER")
    hashtag = prompt("Hashtag (no #)", "edit").lstrip("#")
    videos  = prompt("Videos to scan", "500")
    top_n   = prompt("Top N songs to show", "50")
    try:    videos = int(videos)
    except: videos = 500
    try:    top_n  = int(top_n)
    except: top_n  = 50

    print()
    scanned, sounds = asyncio.run(scrape_sounds(hashtag, videos))
    all_s   = sorted(sounds.values(), key=lambda x: x["count"], reverse=True)
    kept    = [s for s in all_s if not s["reason"]]
    removed = [s for s in all_s if s["reason"]]
    ok(f"Done — {scanned} videos | {len(kept)} songs | {len(removed)} filtered\n")

    show_chart_and_download(hashtag, top_n, scanned, kept, len(removed))

    date   = datetime.now().strftime("%Y-%m-%d_%H-%M")
    medals = {1: "1st", 2: "2nd", 3: "3rd"}
    lines  = [
        f"TikTok Trending Sounds - #{hashtag}",
        f"Date: {date} | Scanned: {scanned} videos",
        f"Kept: {len(kept)} | Filtered: {len(removed)}",
        "=" * 90, "",
        f"TOP {min(top_n, len(kept))} CHART", "-" * 90,
    ]
    for rank, s in enumerate(kept[:top_n], 1):
        funk = " [FUNK]" if s["funk"] else ""
        lines.append(
            f"  {medals.get(rank, str(rank)+'.'):<5} "
            f"{s['title']+funk:<52} {s['author']:<26} {s['count']} videos"
        )
    lines += ["", "FULL LIST", "-" * 90,
              f"  {'#':<5} {'Status':<10} {'Funk':<6} {'Title':<42} {'Artist':<24} {'Videos':>7}  Reason"]
    for i, s in enumerate(all_s, 1):
        t      = (s["title"][:39]  + "...") if len(s["title"])  > 42 else s["title"]
        a      = (s["author"][:21] + "...") if len(s["author"]) > 24 else s["author"]
        status = "REMOVED" if s["reason"] else "KEPT"
        funk   = "FUNK" if s["funk"] else ""
        lines.append(f"  {i:<5} {status:<10} {funk:<6} {t:<42} {a:<24} {s['count']:>7}  {s['reason'] or ''}")

    save(_dirs.DIR_SOUNDS, f"sounds_{hashtag}_{date}.txt", lines)
    print(); saved_in(_dirs.DIR_SOUNDS)
    back_to_menu()
