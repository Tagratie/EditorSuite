"""
tools/niche_report.py
Tool 17 — Niche Report Generator
Full audit: trending sounds + hashtag frequency + viral videos for any niche.
"""
import asyncio
import re
from collections import Counter
from datetime import datetime

from ui import theme as _T
from utils.helpers import ok, info, warn, divider, prompt, save, saved_in, back_to_menu
from utils.validator import validate_sounds, validate_videos
from utils.html_report import save_niche_report, _save_and_open
from utils import dirs as _dirs
from tools.audio_scraper import scrape_sounds
from tools.viral_finder import _scrape_viral
from tools.hashtag_analyzer import _scrape_captions


def tool_nichereport():
    divider("NICHE REPORT GENERATOR")
    print(f"  {_T.DIM}Full analysis: top sounds + hashtags + viral videos for any niche.{_T.R}\n")
    hashtag = prompt("Niche hashtag (no #)", "edit").lstrip("#")
    videos  = int(prompt("Videos to scan", "300") or "300")
    print()

    info("Phase 1/3 — Scraping trending sounds...")
    scanned, sounds = asyncio.run(scrape_sounds(hashtag, videos))
    all_s = sorted(sounds.values(), key=lambda x: x["count"], reverse=True)
    kept  = [s for s in all_s if not s["reason"]]
    ok(f"Found {len(kept)} sounds from {scanned} videos")

    info("Phase 2/3 — Scraping viral videos...")
    viral = asyncio.run(_scrape_viral(hashtag, min(videos, 300)))
    viral.sort(key=lambda x: x["views"], reverse=True)
    ok(f"Found {len(viral)} videos")

    info("Phase 3/3 — Scraping hashtag frequency...")
    captions  = asyncio.run(_scrape_captions(hashtag, min(videos, 300)))
    tag_count = Counter()
    for cap in captions:
        for tag in re.findall(r"#(\w+)", cap.lower()):
            tag_count[tag] += 1
    ok(f"Analyzed {len(captions)} captions")

    # Validate results
    v_ok, v_msg = validate_sounds(scanned, kept)
    if not v_ok: warn(v_msg)
    vv_ok, vv_msg = validate_videos(scanned, viral)
    if not vv_ok: warn(vv_msg)
    print()

    avg_views = sum(v["views"] for v in viral) // max(len(viral), 1)
    date      = datetime.now().strftime("%Y-%m-%d_%H-%M")

    divider(f"NICHE REPORT: #{hashtag}")
    print(f"  {_T.BOLD}Top 10 Sounds:{_T.R}")
    for i, s in enumerate(kept[:10], 1):
        print(f"    {i:>2}. {s['title'][:40]:<40} "
              f"{_T.DIM}{s['author'][:22]}{_T.R}  {_T.CYAN}{s['count']}x{_T.R}")

    print(f"\n  {_T.BOLD}Top Hashtags:{_T.R}")
    for t, c in tag_count.most_common(15):
        print(f"    {c:>4}x  {_T.CYAN}#{t}{_T.R}")

    print(f"\n  {_T.BOLD}Top 5 Viral Videos:{_T.R}")
    for i, v in enumerate(viral[:5], 1):
        print(f"    {i}. {v['views']:>10,} views  @{v['user']:<20}  {v['desc'][:50]}")
        print(f"       {_T.DIM}Sound: {v['sound'][:50]}{_T.R}")

    lines = [
        f"NICHE REPORT: #{hashtag} | {date}",
        f"Scanned: {scanned} videos | Avg viral views: {avg_views:,}",
        "=" * 80, "", "TOP SOUNDS",
    ]
    for i, s in enumerate(kept[:20], 1):
        lines.append(f"  {i:>2}. {s['count']}x  {s['title'][:50]}  —  {s['author']}")
    lines += ["", "TOP HASHTAGS"]
    for t, c in tag_count.most_common(25):
        lines.append(f"  {c}x  #{t}")
    lines += ["", "TOP VIRAL VIDEOS"]
    for i, v in enumerate(viral[:20], 1):
        lines.append(f"  {i:>2}. {v['views']:>10,} views  @{v['user']:<22}  {v['desc'][:70]}")
        lines.append(f"       https://www.tiktok.com/@{v['user']}/video/{v['id']}")

    save(_dirs.DIR_ANALYSIS, f"niche_{hashtag}_{date}.txt", lines)
    print(); saved_in(_dirs.DIR_ANALYSIS)
    _save_and_open(save_niche_report,
                   hashtag, kept, tag_count.most_common(25), viral, scanned,
                   _dirs.DIR_ANALYSIS, label="Niche Report")
    back_to_menu()
