"""
utils/validator.py
Scraper result validator — detects when a scrape silently returns garbage.

TikTok regularly changes its API response format, DOM structure, and bot
detection. When a scraper breaks it typically returns 0 results or a handful
of identical/malformed entries rather than raising an exception.

Usage:
    from utils.validator import validate_sounds, validate_videos
    ok, warning = validate_sounds(scanned=450, sounds=kept_list)
    if not ok:
        warn(warning)
"""
from __future__ import annotations
from typing import Any


# ── Sounds validator ──────────────────────────────────────────────────────────

def validate_sounds(scanned: int, sounds: list[dict]) -> tuple[bool, str]:
    """
    Returns (ok, warning_message).
    ok=False means results look suspicious and the user should be told.
    """
    n = len(sounds)

    if scanned == 0:
        return False, (
            "No videos were loaded from TikTok. "
            "The scraper may be blocked or the hashtag doesn't exist.\n"
            "  Try: a different hashtag, or wait a few minutes and retry."
        )

    if n == 0 and scanned > 50:
        return False, (
            f"Scraped {scanned} videos but found 0 sounds — something is wrong.\n"
            "  TikTok may have changed their data format. "
            "Check github.com/yt-dlp/yt-dlp for updates."
        )

    # Detect if every sound has the same title (DOM parsing returned one repeated element)
    if n >= 3:
        titles = [s.get("title", "") for s in sounds]
        if len(set(titles)) == 1:
            return False, (
                f"All {n} sounds have identical titles — the scraper is misreading TikTok's layout.\n"
                "  This usually means TikTok changed their DOM. Results may be unreliable."
            )

    # Very low hit rate
    if scanned >= 100 and n < 3:
        return False, (
            f"Only {n} sounds from {scanned} videos — suspiciously low.\n"
            "  TikTok may be serving a CAPTCHA or rate-limiting requests.\n"
            "  Try again in a few minutes, or reduce the number of videos to scan."
        )

    return True, ""


# ── Videos / viral validator ──────────────────────────────────────────────────

def validate_videos(scanned: int, videos: list[dict]) -> tuple[bool, str]:
    """Same logic for video results."""
    n = len(videos)

    if scanned == 0:
        return False, (
            "No videos were loaded. "
            "The hashtag may not exist or TikTok is blocking the request."
        )

    if n == 0 and scanned > 20:
        return False, (
            f"Scraped {scanned} videos but parsed 0 — TikTok's data format may have changed.\n"
            "  Results cannot be trusted. Try again or check for tool updates."
        )

    zero_view = sum(1 for v in videos if v.get("views", 0) == 0)
    if n >= 5 and zero_view / n > 0.8:
        return False, (
            f"{zero_view}/{n} videos have 0 views — view count parsing is broken.\n"
            "  Rankings will be inaccurate. TikTok likely changed their API response."
        )

    return True, ""


# ── Generic key-value result validator ───────────────────────────────────────

def validate_generic(label: str, count: int, min_expected: int = 1) -> tuple[bool, str]:
    if count < min_expected:
        return False, (
            f"Only {count} {label} returned — expected at least {min_expected}.\n"
            "  The scraper may be broken or the source has changed."
        )
    return True, ""
