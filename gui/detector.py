"""
gui/detector.py
Auto-detects what action to take from a pasted URL or text.
"""
import re


TYPES = {
    "tiktok_video":    "Download Video",
    "tiktok_profile":  "Download Profile",
    "youtube_video":   "Download Video",
    "youtube_playlist":"Download Playlist",
    "spotify_track":   "Download Track",
    "spotify_album":   "Download Album",
    "spotify_playlist":"Download Playlist",
    "soundcloud":      "Download Audio",
    "hashtag":         "Scrape Hashtag",
    "unknown":         "Unknown",
}


def detect(text: str) -> dict:
    """
    Returns {"type": key, "label": human label, "value": cleaned input}
    """
    t = text.strip().strip('"\'')

    if not t:
        return {"type": None, "label": "", "value": t}

    # TikTok video
    if re.search(r'tiktok\.com/@[\w.]+/video/\d+', t):
        return {"type": "tiktok_video",   "label": TYPES["tiktok_video"],   "value": t}

    # TikTok profile
    if re.search(r'tiktok\.com/@[\w.]+/?$', t) or re.match(r'^@[\w.]+$', t):
        username = re.sub(r'https?://.*?@', '', t).rstrip('/')
        return {"type": "tiktok_profile",  "label": TYPES["tiktok_profile"],  "value": username}

    # YouTube playlist / channel
    if re.search(r'youtube\.com/(playlist|channel|c/|@)', t) or 'list=' in t:
        return {"type": "youtube_playlist","label": TYPES["youtube_playlist"],"value": t}

    # YouTube single video
    if re.search(r'(youtube\.com/watch|youtu\.be/)', t):
        return {"type": "youtube_video",  "label": TYPES["youtube_video"],   "value": t}

    # Spotify (spotify.com, open.spotify.com, spotify.link short URLs)
    if 'spotify.com' in t or 'spotify.link' in t:
        if '/track/'    in t: return {"type": "spotify_track",    "label": TYPES["spotify_track"],    "value": t}
        if '/album/'    in t: return {"type": "spotify_album",    "label": TYPES["spotify_album"],    "value": t}
        if '/playlist/' in t: return {"type": "spotify_playlist", "label": TYPES["spotify_playlist"], "value": t}
        # spotify.link short URLs don't have a path type — treat as track by default
        if 'spotify.link' in t: return {"type": "spotify_track", "label": TYPES["spotify_track"], "value": t}

    # SoundCloud
    if 'soundcloud.com' in t:
        return {"type": "soundcloud", "label": TYPES["soundcloud"], "value": t}

    # Hashtag (with or without #)
    if re.match(r'^#?[a-zA-Z]\w{1,49}$', t):
        tag = t.lstrip('#')
        return {"type": "hashtag", "label": f"Scrape #{tag}", "value": tag}

    return {"type": "unknown", "label": TYPES["unknown"], "value": t}


# Icon per type
ICONS = {
    "tiktok_video":     "󰑊",   # play
    "tiktok_profile":   "󰀙",   # person
    "youtube_video":    "󰑊",
    "youtube_playlist": "󰲸",   # playlist
    "spotify_track":    "󰝚",   # music note
    "spotify_album":    "󰲸",
    "spotify_playlist": "󰲸",
    "soundcloud":       "󰋋",
    "hashtag":          "#",
    "unknown":          "?",
}

EMOJI = {
    "tiktok_video":     "▶",
    "tiktok_profile":   "👤",
    "youtube_video":    "▶",
    "youtube_playlist": "📋",
    "spotify_track":    "🎵",
    "spotify_album":    "💿",
    "spotify_playlist": "🎧",
    "soundcloud":       "🎵",
    "hashtag":          "#",
    "unknown":          "?",
}
