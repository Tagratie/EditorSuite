"""
tools/music_downloader.py
Spotify / SoundCloud Downloader

Spotify  → gets track info from Spotify oEmbed API (public, no auth)
           or Playwright as fallback for albums/playlists
           → downloads each track from YouTube Music via yt-dlp
SoundCloud → yt-dlp direct download
"""
import os
import re
import sys
import json
import asyncio
import subprocess
import shutil
import urllib.request
import urllib.parse

from ui import theme as _T
from utils.helpers import ok, info, err, warn, divider, prompt, back_to_menu, clear_line
from utils import dirs as _dirs


def _need_ytdlp() -> bool:
    if shutil.which("yt-dlp"):
        return True
    warn("yt-dlp not found — installing...")
    subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp", "--quiet"])
    if shutil.which("yt-dlp"):
        ok("yt-dlp ready."); return True
    err("Could not install yt-dlp.  Run:  pip install yt-dlp")
    return False


# ── Spotify oEmbed — works for single tracks, returns title + author ──────────

def _oembed_track(spotify_url: str) -> dict | None:
    """
    Spotify's public oEmbed endpoint — no auth, no JS needed.
    Returns {"title": "...", "artist": "..."} or None.
    e.g. https://open.spotify.com/oembed?url=https://open.spotify.com/track/...
    """
    endpoint = "https://open.spotify.com/oembed?url=" + urllib.parse.quote(spotify_url)
    headers  = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    try:
        req = urllib.request.Request(endpoint, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        # title is usually "Song Name" or "Song Name - Artist Name"
        title = data.get("title", "")
        # artist comes from provider_name / thumbnail_url context or title split
        # oEmbed title format: "Song Name" with artist in description not always present
        # Better: use the track page directly via Playwright for clean split
        return {"raw_title": title}
    except Exception:
        return None


# ── Playwright scraper — loads Spotify page with JS, grabs meta tags ──────────

async def _playwright_get_tracks(url: str) -> list[dict]:
    """Use a headless browser to load the Spotify page and extract track info."""
    from playwright.async_api import async_playwright
    from core.browser import new_browser

    tracks = []

    async with async_playwright() as pw:
        browser, ctx = await new_browser(pw, mute=True)
        page = await ctx.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)  # let JS render

            if "/track/" in url:
                # Single track — grab title + artist from page
                title  = await page.title()
                # Spotify page title format: "Song Name - Artist | Spotify"
                title  = re.sub(r"\s*[|\-–]\s*Spotify\s*$", "", title).strip()
                # Split "Song - Artist"
                parts  = re.split(r"\s*[-–]\s*", title, maxsplit=1)
                song   = parts[0].strip()
                artist = parts[1].strip() if len(parts) > 1 else ""
                if song:
                    tracks.append({"title": song, "artist": artist})

            else:
                # Album / Playlist — grab all track rows
                # Try multiple selectors Spotify uses
                await page.wait_for_selector(
                    "[data-testid='tracklist-row'], [class*='tracklistRow'], li[class*='track']",
                    timeout=10000
                )
                # Get track names from aria-labels or text content
                rows = await page.query_selector_all(
                    "[data-testid='tracklist-row'], [class*='tracklistRow']"
                )
                for row in rows:
                    # aria-rowindex rows have the track name in first cell
                    try:
                        name_el = await row.query_selector(
                            "[data-testid='track-name'], [class*='trackName'], "
                            "a[href*='/track/'], span[dir='auto']"
                        )
                        artist_els = await row.query_selector_all(
                            "a[href*='/artist/'], span[class*='artist']"
                        )
                        name   = (await name_el.text_content()).strip() if name_el else ""
                        artist = ", ".join(
                            [(await a.text_content()).strip() for a in artist_els[:2]]
                        )
                        if name:
                            tracks.append({"title": name, "artist": artist})
                    except Exception:
                        continue

                # Fallback: grab from page title meta
                if not tracks:
                    all_links = await page.query_selector_all("a[href*='/track/']")
                    seen = set()
                    for link in all_links:
                        try:
                            text = (await link.text_content()).strip()
                            if text and text not in seen and len(text) > 1:
                                seen.add(text)
                                tracks.append({"title": text, "artist": ""})
                        except Exception:
                            continue

        except Exception:
            pass
        finally:
            try:
                await browser.close()
            except Exception:
                pass

    return tracks


def _get_tracks(url: str) -> list[dict]:
    """Get track list from a Spotify URL. Single tracks try oEmbed first."""
    if "/track/" in url:
        # Try oEmbed first (fast, no browser)
        data = _oembed_track(url)
        if data and data.get("raw_title"):
            raw = data["raw_title"]
            # oEmbed title is "Song Name" — artist often missing
            # Try to split if it contains a dash
            parts = re.split(r"\s*[-–]\s*", raw, maxsplit=1)
            if len(parts) == 2:
                return [{"title": parts[0].strip(), "artist": parts[1].strip()}]
            # No artist in oEmbed — use Playwright to get proper split
    # Use Playwright for albums, playlists, and as fallback for tracks
    info("Loading Spotify page via browser...")
    tracks = asyncio.run(_playwright_get_tracks(url))
    return tracks


# ── Download via yt-dlp YouTube Music search ─────────────────────────────────

def _dl_tracks(tracks: list[dict], quality: str, out_dir: str) -> tuple[int, int]:
    ok_n = fail_n = 0
    for i, t in enumerate(tracks, 1):
        title  = t.get("title", "").strip()
        artist = t.get("artist", "").strip()
        if not title:
            fail_n += 1; continue

        display = (f"{title} — {artist}" if artist else title)[:65]
        print(f"  {_T.CYAN}[{i}/{len(tracks)}]{_T.R}  {display}", end="  ", flush=True)

        out_tpl = os.path.join(out_dir, "%(artist)s - %(title)s.%(ext)s")
        base_args = [
            "--extract-audio", "--audio-format", "mp3",
            "--audio-quality", f"{quality}k",
            "--output",        out_tpl,
            "--no-playlist",   "--no-warnings",
            "--embed-thumbnail", "--add-metadata",
        ]

        # Try YT Music → regular YT → YT with "audio" suffix
        success = False
        last_err = ""
        for q in [
            f"ytmsearch1:{title} {artist}".strip(),
            f"ytsearch1:{title} {artist}".strip(),
            f"ytsearch1:{title} {artist} audio".strip(),
        ]:
            r = subprocess.run(["yt-dlp", q] + base_args,
                               capture_output=True, text=True)
            if r.returncode == 0:
                success = True
                break
            last_err = (r.stderr or r.stdout or "")[-200:]

        if success:
            print(f"{_T.GREEN}✓{_T.R}"); ok_n += 1
        else:
            print(f"{_T.YELLOW}✗{_T.R}")
            if last_err:
                # Print the actual yt-dlp error so user sees what went wrong
                for line in last_err.strip().splitlines():
                    if line.strip():
                        print(f"    {_T.DIM}{line.strip()[:110]}{_T.R}")
            fail_n += 1

    return ok_n, fail_n


# ── Tool ─────────────────────────────────────────────────────────────────────

def tool_music_dl():
    divider("SPOTIFY / SOUNDCLOUD DOWNLOADER")
    print(f"  {_T.DIM}Paste any Spotify or SoundCloud URL — track, album, or playlist.{_T.R}")
    print(f"  {_T.DIM}Spotify: reads track names → downloads from YouTube Music. No login.{_T.R}\n")

    if not _need_ytdlp():
        back_to_menu(); return

    url = prompt("Paste URL").strip()
    if not url:
        back_to_menu(); return

    quality = prompt("Quality kbps [320/256/192/128]", "320").strip()
    os.makedirs(_dirs.DIR_AUDIO, exist_ok=True)

    # ── SoundCloud ────────────────────────────────────────────────────────────
    if "soundcloud.com" in url:
        print()
        info("Downloading from SoundCloud...")
        subprocess.run([
            "yt-dlp", url,
            "--extract-audio", "--audio-format", "mp3",
            "--audio-quality", f"{quality}k",
            "--output", os.path.join(_dirs.DIR_AUDIO, "%(uploader)s - %(title)s.%(ext)s"),
            "--progress", "--ignore-errors",
        ])
        print(); ok(f"Done → {_dirs.DIR_AUDIO}")
        back_to_menu(); return

    # ── Spotify ───────────────────────────────────────────────────────────────
    if "spotify.com" not in url:
        err("Unrecognised URL — paste a Spotify or SoundCloud link.")
        back_to_menu(); return

    # Strip tracking params (?si=...)
    url = re.sub(r"\?.*$", "", url.strip())

    kind = ("track" if "/track/" in url else "album" if "/album/" in url
            else "playlist" if "/playlist/" in url else "item")
    print()
    info(f"Reading Spotify {kind}...")

    tracks = _get_tracks(url)

    if not tracks:
        err("Could not read track info from Spotify.")
        info("Make sure the link is a public Spotify URL.")
        back_to_menu(); return

    info(f"Found {len(tracks)} track(s) — searching YouTube Music...\n")
    ok_n, fail_n = _dl_tracks(tracks, quality, _dirs.DIR_AUDIO)

    print()
    ok(f"{ok_n}/{len(tracks)} downloaded → {_dirs.DIR_AUDIO}")
    if fail_n:
        warn(f"{fail_n} track(s) not found on YouTube Music.")

    back_to_menu()
