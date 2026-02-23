"""
tools/spotify.py
Tool 5 — Export to Spotify
Scrapes trending sounds then adds them to a Spotify playlist.
"""
import asyncio
import os
from datetime import datetime

from ui import theme as _T
from utils.helpers import ok, info, err, warn, divider, prompt, back_to_menu
from utils import dirs as _dirs
from utils.config import load_config, SCRIPT_DIR
from tools.audio_scraper import scrape_sounds


def tool_ets():
    divider("EXPORT TO SPOTIFY")
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
    except ImportError:
        err("spotipy not installed. Run: pip install spotipy")
        back_to_menu()
        return

    cfg        = load_config()
    client_id  = cfg.get("spotify_client_id", "")
    client_sec = cfg.get("spotify_client_secret", "")

    # Try creds file as fallback
    creds_path = os.path.join(_dirs.DIR_LOGS, "spotify_creds.txt")
    if not client_id and os.path.exists(creds_path):
        with open(creds_path, encoding="utf-8") as f:
            lines = [l.strip() for l in f]
        client_id  = lines[0] if lines else ""
        client_sec = lines[1] if len(lines) > 1 else ""
        ok("Loaded saved Spotify credentials.")
    elif client_id:
        ok("Using credentials from Settings.")
    else:
        print(f"\n  {_T.YELLOW}First-time setup:{_T.R}")
        print(f"  1. Go to https://developer.spotify.com/dashboard")
        print(f"  2. Create an app, set redirect URI to: http://127.0.0.1:8888/callback")
        print(f"  3. Copy Client ID and Secret\n")
        client_id  = prompt("Client ID")
        client_sec = prompt("Client Secret")
        os.makedirs(_dirs.DIR_LOGS, exist_ok=True)
        with open(creds_path, "w", encoding="utf-8") as f:
            f.write(client_id + "\n" + client_sec + "\n")
        ok("Credentials saved. You can also store them in Settings → 16.")

    print(f"\n  {_T.DIM}Redirect URI: http://127.0.0.1:8888/callback{_T.R}")
    print(f"  {_T.DIM}Make sure this matches your Spotify app settings.{_T.R}\n")

    if not client_id or not client_sec:
        err("Missing credentials.")
        back_to_menu()
        return

    hashtag = prompt("Hashtag to scrape", "edit").lstrip("#")
    videos  = int(prompt("Videos to scan", "500") or "500")
    top_n   = int(prompt("Top N to export", "50") or "50")
    print()
    info("Running audio scraper...\n")
    scanned, sounds = asyncio.run(scrape_sounds(hashtag, videos))
    all_s     = sorted(sounds.values(), key=lambda x: x["count"], reverse=True)
    kept      = [s for s in all_s if not s["reason"]]
    top_songs = kept[:top_n]
    ok(f"Scraped {scanned} videos | {len(kept)} songs\n")

    info("Connecting to Spotify...\n")
    cache_path = os.path.join(SCRIPT_DIR, ".spotify_cache")
    if os.path.exists(cache_path):
        try:
            os.remove(cache_path)
        except Exception:
            pass
    try:
        auth = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_sec,
            redirect_uri="http://127.0.0.1:8888/callback",
            scope="playlist-modify-private playlist-modify-public",
            cache_path=cache_path,
            show_dialog=True,
            open_browser=True,
        )
        sp      = spotipy.Spotify(auth_manager=auth)
        me      = sp.me()
        user_id = me["id"]
        ok(f"Logged in as: {user_id}\n")
    except Exception as e:
        err(f"Spotify login failed: {e}")
        warn("Ensure redirect URI is http://127.0.0.1:8888/callback in your Spotify app.")
        back_to_menu()
        return

    date = datetime.now().strftime("%Y-%m-%d")
    try:
        playlist = sp._post("me/playlists", payload={
            "name":        f"TikTok #{hashtag} Trending - {date}",
            "public":      True,
            "description": f"Top sounds from #{hashtag} on {date}",
        })
        pid = playlist["id"]
    except Exception as e:
        err(f"Could not create playlist: {e}")
        back_to_menu()
        return

    track_uris = []
    not_found  = []
    for s in top_songs:
        try:
            res = sp.search(q=f"{s['title']} {s['author']}", type="track", limit=1)
            t   = (res.get("tracks") or {}).get("items", [])
            if t:
                track_uris.append(t[0]["uri"])
                ok(f"Found: {t[0]['name']}")
            else:
                not_found.append(s["title"])
        except Exception:
            not_found.append(s["title"])

    # Copy track URLs to clipboard
    track_urls     = [u.replace("spotify:track:", "https://open.spotify.com/track/")
                      for u in track_uris]
    clipboard_text = "\n".join(track_urls)
    clipboard_ok   = False
    try:
        import subprocess
        subprocess.run("clip", input=clipboard_text.encode("utf-8"), check=True, shell=True)
        clipboard_ok = True
    except Exception:
        pass

    playlist_url = playlist["external_urls"]["spotify"]
    print()
    ok(f"Playlist created: {playlist_url}")
    ok(f"Found {len(track_uris)} tracks | Not found: {len(not_found)}")
    print()

    if not track_uris:
        warn("No tracks found to add.")
        back_to_menu()
        return

    import webbrowser
    webbrowser.open(playlist_url)

    if clipboard_ok:
        print(f"  {_T.GREEN}All {len(track_uris)} track links copied to clipboard!{_T.R}\n")
        print(f"  {_T.BOLD}How to add them:{_T.R}")
        print(f"  {_T.CYAN}1.{_T.R} Spotify just opened in your browser")
        print(f"  {_T.CYAN}2.{_T.R} Click inside the playlist")
        print(f"  {_T.CYAN}3.{_T.R} Press {_T.BOLD}Ctrl+V{_T.R} — all songs paste in at once")
    else:
        url_file = os.path.join(_dirs.DIR_LOGS, "spotify_tracks.txt")
        with open(url_file, "w", encoding="utf-8") as f:
            f.write(clipboard_text)
        print(f"  {_T.YELLOW}Clipboard unavailable — track links saved to:{_T.R}")
        print(f"  {url_file}\n")
        print(f"  {_T.BOLD}How to add them:{_T.R}")
        print(f"  {_T.CYAN}1.{_T.R} Open that file, select all, copy")
        print(f"  {_T.CYAN}2.{_T.R} Click inside the Spotify playlist")
        print(f"  {_T.CYAN}3.{_T.R} Press {_T.BOLD}Ctrl+V{_T.R}")

    back_to_menu()
