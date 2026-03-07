"""
gui/runner.py
All 21 EditorSuite tools fully wired — no CLI fallback.
"""
import os, sys, re, queue, threading, subprocess, asyncio, shutil
from pathlib import Path

ROOT = str(Path(__file__).parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.config import load_config
from utils.dirs   import _init_dirs
from ui.theme     import _apply_theme

load_config(); _apply_theme("default"); _init_dirs()
from utils import dirs as _dirs


def _strip(s): return re.sub(r'\033\[[0-9;]*m', '', str(s))


# ── Entry points ──────────────────────────────────────────────────────────────

def run_task(detected: dict, options: dict, q: queue.Queue):
    """Home paste-anything panel."""
    _run(detected.get("type",""), detected.get("value",""), options, q)

def run_named_tool(tool_id: str, options: dict, q: queue.Queue):
    """Sidebar tool buttons."""
    _run(tool_id, None, options, q)

def _run(kind, value, opts, q):
    _init_dirs()   # re-read config so folder settings always take effect
    log   = lambda m:   q.put({"type":"log",      "text":_strip(m)})
    prog  = lambda v,t: q.put({"type":"progress", "value":v,"total":t})
    res   = lambda d:   q.put({"type":"result",   "data":d})
    def done(m="", path=""): q.put({"type":"done", "text":str(m), "path":str(path)})
    error = lambda m:   q.put({"type":"error",    "text":str(m)})
    try:
        _dispatch(kind, value, opts, log, prog, res, done, error)
    except Exception as e:
        import traceback
        error(f"Error: {e}")
        log(traceback.format_exc())
    finally:
        q.put(None)


# ── Dispatcher ────────────────────────────────────────────────────────────────

def _dispatch(kind, value, opts, log, prog, res, done, error):
    # paste-anything shortcuts
    if kind == "hashtag":
        return _scraper(value or opts.get("hashtag",""), opts, log, prog, res, done, error)
    if kind in ("tiktok_video","youtube_video"):
        return _dl_video(value or opts.get("url",""), opts, log, done, error)
    if kind == "tiktok_profile":
        return _dl_profile(value or opts.get("url",""), opts, log, done, error)
    if kind == "youtube_playlist":
        return _dl_playlist(value or opts.get("url",""), opts, log, done, error)
    if kind in ("spotify_track","spotify_album","spotify_playlist"):
        return _spotify(value or opts.get("url",""), opts, log, prog, done, error)
    if kind == "soundcloud":
        return _soundcloud(value or opts.get("url",""), opts, log, done, error)

    # --- SCRAPERS ---
    if kind == "scraper":
        h = (opts.get("hashtag","") or "").lstrip("#").strip()
        return (error("Enter a hashtag.") if not h else
                _scraper(h, opts, log, prog, res, done, error))

    if kind == "hfreq":
        h = (opts.get("hashtag","") or "").lstrip("#").strip()
        return (error("Enter a hashtag.") if not h else
                _hashtag_freq(h, opts, log, res, done, error))

    if kind == "crosshash":
        tags = [t.strip().lstrip("#") for t in opts.get("hashtags","").split(",") if t.strip()]
        return (error("Enter at least one hashtag.") if not tags else
                _cross_hashtag(tags, opts, log, prog, res, done, error))

    if kind == "viral":
        h = (opts.get("hashtag","") or "").lstrip("#").strip()
        return (error("Enter a hashtag.") if not h else
                _viral(h, opts, log, prog, res, done, error))

    if kind == "trending":
        return _trending(opts, log, prog, res, done, error)

    if kind == "sp_exp":
        h = (opts.get("hashtag","") or "").lstrip("#").strip()
        return (error("Enter a hashtag.") if not h else
                _export_spotify(h, opts, log, prog, done, error))

    # --- ANALYTICS ---
    if kind == "hanalyze":
        tags = [t.strip().lstrip("#") for t in opts.get("hashtags","").split(",") if t.strip()]
        return (error("Enter at least one hashtag.") if not tags else
                _hashtag_analyze(tags, opts, log, prog, res, done, error))

    if kind == "competitor":
        u1 = opts.get("user1","").lstrip("@").strip()
        u2 = opts.get("user2","").lstrip("@").strip()
        return (error("Enter both usernames.") if not u1 or not u2 else
                _competitor(u1, u2, opts, log, res, done, error))

    if kind == "besttime":
        u = opts.get("username","").lstrip("@").strip()
        return (error("Enter your TikTok username.") if not u else
                _best_time(u, opts, log, res, done, error))

    if kind == "engagement":
        try:
            fol  = int(opts.get("followers","0").replace(",","").replace(".",""))
            views= int(opts.get("views","0").replace(",","").replace(".",""))
            likes= int(opts.get("likes","0").replace(",","").replace(".",""))
            coms = int(opts.get("comments","0").replace(",","").replace(".",""))
            shar = int(opts.get("shares","0").replace(",","").replace(".",""))
        except ValueError:
            return error("Enter valid whole numbers.")
        return _engagement(fol, views, likes, coms, shar, res, done, error)

    if kind == "niche":
        h = (opts.get("hashtag","") or "").lstrip("#").strip()
        return (error("Enter a hashtag.") if not h else
                _niche_report(h, opts, log, prog, res, done, error))

    if kind == "growth":
        u = opts.get("username","").lstrip("@").strip()
        return (error("Enter a TikTok username.") if not u else
                _growth(u, log, res, done, error))

    if kind == "health":
        u = opts.get("username","").lstrip("@").strip()
        return (error("Enter a TikTok username.") if not u else
                _health(u, opts, log, prog, res, done, error))

    # --- DOWNLOADERS ---
    if kind == "dl_vid":
        url = opts.get("url","").strip()
        return (error("Enter a URL.") if not url else
                _dl_video(url, opts, log, done, error))

    if kind == "dl_prof":
        url = opts.get("url","").strip()
        if url.startswith("@"):
            url = f"https://www.tiktok.com/{url}"
        return (error("Enter a URL or @username.") if not url else
                (_dl_profile(re.sub(r"https?://[^/]+/@?","",url).rstrip("/"), opts, log, done, error)
                 if "tiktok.com/@" in url else _dl_playlist(url, opts, log, done, error)))

    if kind == "dl_spotify":
        url = opts.get("url","").strip()
        if not url: return error("Enter a URL.")
        if "soundcloud" in url: return _soundcloud(url, opts, log, done, error)
        opts.setdefault("audio_quality", opts.get("quality","320"))
        return _spotify(url, opts, log, prog, done, error)

    if kind == "dl_song":
        title  = opts.get("title","").strip()
        artist = opts.get("artist","").strip()
        if not title:
            return error("Enter a song title.")
        return _dl_song(title, artist, opts, log, prog, done, error)

    if kind == "dl_audio":
        inp = opts.get("input","").strip()
        return (error("Enter a file path or URL.") if not inp else
                _audio_extract(inp, opts, log, done, error))

    # --- STUDIO ---
    if kind == "compress":
        inp = opts.get("input","").strip()
        return (error("Enter a video file path.") if not inp else
                _compress(inp, opts, log, done, error))

    if kind == "bulk_comp":
        folder = opts.get("folder","").strip()
        return (error("Enter a folder path.") if not folder else
                _bulk_compress(folder, opts, log, prog, done, error))

    if kind == "bg_rem":
        inp = opts.get("input","").strip()
        return (error("Enter a file or folder path.") if not inp else
                _bg_remove(inp, opts, log, prog, done, error))

    if kind == "calendar":
        ppw   = int(opts.get("posts_per_week","3") or "3")
        start = opts.get("start_date","").strip()
        return _calendar(ppw, start, log, res, done, error)

    error(f"Unknown tool: {kind}")


# =============================================================================
# SCRAPERS
# =============================================================================

def _scraper(hashtag, opts, log, prog, res, done, error):
    from tools.audio_scraper import scrape_sounds
    limit = int(opts.get("limit","300") or "300")
    log(f"Scraping #{hashtag} — targeting {limit} videos...")
    pcb = lambda seen, total: prog(seen, total)
    try:
        scanned, sounds = asyncio.run(scrape_sounds(hashtag, limit, progress_cb=pcb))
    except Exception as e:
        return error(f"Scrape failed: {e}")

    kept    = sorted([v for v in sounds.values() if not v["reason"]],
                     key=lambda x: x["count"], reverse=True)
    removed = [v for v in sounds.values() if v["reason"]]
    log(f"Scanned {scanned} videos · {len(kept)} sounds · {len(removed)} filtered")

    from utils.html_report import save_sounds_report
    os.makedirs(_dirs.DIR_SOUNDS, exist_ok=True)
    html_path = save_sounds_report(hashtag, scanned, kept, removed, _dirs.DIR_SOUNDS)

    res({"type":"sounds","hashtag":hashtag,"scanned":scanned,
         "kept":len(kept),"removed":len(removed),"top":kept[:15],"html_path":html_path})
    done(f"{len(kept)} trending sounds found")


def _hashtag_freq(hashtag, opts, log, prog, res, done, error):
    from tools.hashtag_analyzer import _scrape_captions
    from collections import Counter
    target = int(opts.get("limit","200") or "200")
    log(f"Scraping #{hashtag} captions ({target} videos)...")
    pcb = lambda seen, total: prog(seen, total)
    try:
        captions = asyncio.run(_scrape_captions(hashtag, target, progress_cb=pcb))
    except Exception as e:
        return error(f"Scrape failed: {e}")

    tags   = re.findall(r"#(\w+)", " ".join(captions))
    counts = Counter(tags)
    top    = [{"tag":f"#{t}","count":c} for t,c in counts.most_common(30)]
    log(f"Analysed {len(captions)} captions — {len(counts)} unique hashtags found")
    res({"type":"hashtag_freq","hashtag":hashtag,"top":top,
         "total_captions":len(captions),"total_tags":len(counts)})
    done(f"{len(top)} top hashtags for #{hashtag}")


def _cross_hashtag(tags, opts, log, prog, res, done, error):
    from tools.cross_hashtag import _scrape_tag_sounds
    from playwright.async_api import async_playwright
    target = int(opts.get("limit","300") or "300")
    log(f"Scraping {len(tags)} hashtag(s), {target} videos each...")

    all_sounds = {}

    async def _run():
        from core.browser import new_browser
        async with async_playwright() as pw:
            browser, ctx = await new_browser(pw, mute=True)
            try:
                for i, tag in enumerate(tags, 1):
                    log(f"  [{i}/{len(tags)}] Scraping #{tag}...")
                    pcb = lambda seen, total, _i=i, _n=len(tags): prog(
                        int(((_i-1) + seen/max(total,1)) * 100), _n * 100)
                    sounds, _ = await _scrape_tag_sounds(ctx, tag, target, progress_cb=pcb)
                    for sid, s in sounds.items():
                        if sid in all_sounds:
                            all_sounds[sid]["count"] += s["count"]
                            all_sounds[sid]["tags"].add(tag)
                        else:
                            all_sounds[sid] = {**s, "tags": {tag}}
            finally:
                await browser.close()

    try:
        asyncio.run(_run())
    except Exception as e:
        return error(f"Scrape failed: {e}")

    cross = sorted(
        [dict(s, tags=list(s["tags"])) for s in all_sounds.values()
         if len(s.get("tags", set())) > 1],
        key=lambda x: x["count"], reverse=True
    )[:20]
    log(f"Found {len(cross)} sounds trending across multiple hashtags")
    res({"type":"cross_sounds","tags":tags,"sounds":cross})
    done(f"{len(cross)} cross-hashtag sounds found")


def _viral(hashtag, opts, log, prog, res, done, error):
    from tools.viral_finder import _scrape_viral
    target = int(opts.get("limit","100") or "100")
    log(f"Finding viral videos in #{hashtag} ({target} videos)...")
    pcb = lambda seen, total: prog(seen, total)
    try:
        videos = asyncio.run(_scrape_viral(hashtag, target, progress_cb=pcb))
    except Exception as e:
        return error(f"Scrape failed: {e}")

    videos = sorted(videos, key=lambda v: v.get("views",0), reverse=True)
    log(f"Found {len(videos)} videos")
    res({"type":"viral","hashtag":hashtag,"videos":videos[:20]})
    done(f"Top {min(20,len(videos))} viral videos in #{hashtag}")


def _trending(opts, log, prog, res, done, error):
    from tools.trending import _scrape_trending
    target = int(opts.get("limit","300") or "300")
    log(f"Scraping TikTok trending page ({target} videos)...")
    pcb = lambda seen, total: prog(seen, total)
    try:
        sounds, removed_sounds, videos = asyncio.run(_scrape_trending(target, progress_cb=pcb))
    except Exception as e:
        return error(f"Scrape failed: {e}")

    # _scrape_trending already applies garbage filters and returns a ranked list.
    kept = list(sounds or [])
    log(f"Found {len(kept)} trending sounds, {len(videos)} trending videos")
    res({"type":"trending","sounds":kept[:15],"videos":videos[:15]})
    done(f"{len(kept)} trending sounds · {len(videos)} trending videos")


def _export_spotify(hashtag, opts, log, prog, done, error):
    from tools.audio_scraper import scrape_sounds
    cfg = load_config()
    cid = cfg.get("spotify_client_id","")
    sec = cfg.get("spotify_client_secret","")
    if not cid or not sec:
        return error("Spotify credentials missing. Add spotify_client_id and spotify_client_secret to config.json.")
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
    except ImportError:
        return error("spotipy not installed. Run: pip install spotipy")

    limit = int(opts.get("limit","500") or "500")
    top_n = int(opts.get("top_n","20") or "20")
    log(f"Scraping #{hashtag}...")
    pcb = lambda seen, total: prog(seen, total)
    try:
        scanned, sounds = asyncio.run(scrape_sounds(hashtag, limit, progress_cb=pcb))
    except Exception as e:
        return error(f"Scrape failed: {e}")

    kept = sorted([v for v in sounds.values() if not v["reason"]],
                  key=lambda x: x["count"], reverse=True)[:top_n]
    log(f"Found {len(kept)} sounds — searching Spotify...")
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=cid, client_secret=sec,
            redirect_uri="http://localhost:8888/callback",
            scope="playlist-modify-public"))
        uid = sp.current_user()["id"]
        pl  = sp.user_playlist_create(uid, f"TikTok #{hashtag} Trending", public=True)
        uris = []
        for s in kept:
            r = sp.search(q=f"{s['title']} {s.get('author','')}", type="track", limit=1)
            items = r["tracks"]["items"]
            if items:
                uris.append(items[0]["uri"])
                log(f"  ✓ {s['title']}")
            else:
                log(f"  ✗ {s['title']} — not on Spotify")
        if uris:
            sp.playlist_add_items(pl["id"], uris)
        done(f"Playlist created with {len(uris)} tracks: {pl['external_urls']['spotify']}")
    except Exception as e:
        error(f"Spotify error: {e}")


# =============================================================================
# ANALYTICS
# =============================================================================

def _hashtag_analyze(tags, opts, log, prog, res, done, error):
    from tools.hashtag_analyzer import _analyze_hashtags
    log(f"Analysing {len(tags)} hashtag(s)...")
    try:
        results = asyncio.run(_analyze_hashtags(tags))
    except Exception as e:
        return error(f"Analysis failed: {e}")

    rows = sorted([
        {"tag":f"#{tag}",
         "posts":     d.get("post_count",0),
         "avg_views": d.get("avg_views",0),
         "avg_likes": d.get("avg_likes",0),
         "difficulty":d.get("difficulty","—")}
        for tag,d in results.items()
    ], key=lambda r: r["avg_views"], reverse=True)

    res({"type":"hashtag_analyze","rows":rows})
    done(f"Analysis complete for {len(rows)} hashtags")


def _competitor(u1, u2, opts, log, res, done, error):
    from tools.competitor import _scrape_profile, _analyze_posts
    from playwright.async_api import async_playwright
    log(f"Scraping @{u1} and @{u2}...")

    async def _run():
        from core.browser import new_browser
        async with async_playwright() as pw:
            browser, ctx = await new_browser(pw, mute=True)
            try:
                _, posts1 = await _scrape_profile(ctx, u1)
                _, posts2 = await _scrape_profile(ctx, u2)
            finally:
                await browser.close()
            return posts1, posts2

    try:
        posts1, posts2 = asyncio.run(_run())
    except Exception as e:
        return error(f"Scrape failed: {e}")

    s1 = _analyze_posts(posts1)
    s2 = _analyze_posts(posts2)
    log(f"@{u1}: {len(posts1)} posts  |  @{u2}: {len(posts2)} posts")
    res({"type":"competitor","user1":u1,"user2":u2,
         "stats1":s1,"stats2":s2,
         "posts1":posts1[:5],"posts2":posts2[:5]})
    done(f"Comparison complete: @{u1} vs @{u2}")


def _best_time(username, opts, log, res, done, error):
    from tools.competitor import _scrape_profile
    from playwright.async_api import async_playwright
    from collections import defaultdict
    import datetime
    log(f"Scraping @{username} posting history...")

    async def _run():
        from core.browser import new_browser
        async with async_playwright() as pw:
            browser, ctx = await new_browser(pw, mute=True)
            try:
                _, posts = await _scrape_profile(ctx, username)
            finally:
                await browser.close()
            return posts

    try:
        posts = asyncio.run(_run())
    except Exception as e:
        return error(f"Scrape failed: {e}")

    DAYS = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    slot_views = defaultdict(list)
    for p in posts:
        ts = p.get("timestamp",0)
        if not ts: continue
        dt  = datetime.datetime.fromtimestamp(ts)
        key = (dt.weekday(), dt.hour)
        slot_views[key].append(p.get("views",0))

    slots = sorted([
        {"day":DAYS[d],"hour":h,
         "avg_views":int(sum(v)/len(v)),
         "count":len(v)}
        for (d,h),v in slot_views.items()
    ], key=lambda s: s["avg_views"], reverse=True)

    log(f"Analysed {len(posts)} posts across {len(slots)} time slots")
    res({"type":"best_time","username":username,
         "slots":slots[:10],"total_posts":len(posts)})
    done(f"Best times found from {len(posts)} posts")


def _engagement(followers, avg_views, avg_likes, avg_comms, avg_share, res, done, error):
    if not avg_views:
        return error("Avg views cannot be zero.")
    BENCH = {
        "Nano (<10K)":     {"er":17.99,"reach":40},
        "Micro (10-100K)": {"er":14.15,"reach":35},
        "Mid (100K-1M)":   {"er":10.53,"reach":25},
        "Macro (1M+)":     {"er":7.2,  "reach":15},
    }
    tier = ("Nano (<10K)" if followers<10_000 else
            "Micro (10-100K)" if followers<100_000 else
            "Mid (100K-1M)" if followers<1_000_000 else "Macro (1M+)")
    bench_er    = BENCH[tier]["er"]
    bench_reach = BENCH[tier]["reach"]
    er_likes    = avg_likes / avg_views * 100
    er_total    = (avg_likes + avg_comms + avg_share) / avg_views * 100
    reach_rate  = (avg_views / followers * 100) if followers else 0
    grade = lambda v,b: "above" if v>=b*1.2 else "average" if v>=b*0.8 else "below"
    res({"type":"engagement","tier":tier,
         "er_likes":round(er_likes,2), "er_total":round(er_total,2),
         "reach_rate":round(reach_rate,1),
         "bench_er":bench_er,"bench_reach":bench_reach,
         "grade_er":grade(er_likes,bench_er),
         "grade_reach":grade(reach_rate,bench_reach),
         "followers":followers,"avg_views":avg_views})
    done("Engagement rate calculated")


def _niche_report(hashtag, opts, log, prog, res, done, error):
    from tools.audio_scraper    import scrape_sounds
    from tools.viral_finder     import _scrape_viral
    from tools.hashtag_analyzer import _scrape_captions
    from collections import Counter
    limit = int(opts.get("limit","300") or "300")

    log(f"Full niche audit for #{hashtag}...")
    log("  [1/3] Scraping trending sounds...")
    prog(1, 3)
    try:
        scanned, sounds = asyncio.run(scrape_sounds(hashtag, limit))
    except Exception as e:
        return error(f"Sound scrape failed: {e}")

    log("  [2/3] Finding viral videos...")
    prog(2, 3)
    try:
        videos = asyncio.run(_scrape_viral(hashtag, min(limit,300)))
    except Exception as e:
        videos = []; log(f"  Viral scrape warning: {e}")

    log("  [3/3] Analysing hashtag frequency...")
    prog(3, 3)
    try:
        captions = asyncio.run(_scrape_captions(hashtag, min(limit,300)))
    except Exception as e:
        captions = []; log(f"  Caption scrape warning: {e}")

    kept     = sorted([v for v in sounds.values() if not v["reason"]],
                      key=lambda x: x["count"], reverse=True)[:10]
    viral    = sorted(videos, key=lambda v: v.get("views",0), reverse=True)[:10]
    tags     = re.findall(r"#(\w+)", " ".join(captions))
    top_tags = [{"tag":f"#{t}","count":c}
                for t,c in Counter(tags).most_common(10)]

    res({"type":"niche","hashtag":hashtag,"scanned":scanned,
         "sounds":kept,"viral":viral,"top_tags":top_tags})
    done(f"Niche report done — {len(kept)} sounds · {len(viral)} videos · {len(top_tags)} tags")


def _growth(username, log, res, done, error):
    from tools.growth_tracker import _scrape_profile_stats
    import json, datetime
    log(f"Scraping @{username} stats...")
    try:
        stats = asyncio.run(_scrape_profile_stats(username))
    except Exception as e:
        return error(f"Scrape failed: {e}")

    snap_file = os.path.join(_dirs.DIR_ANALYSIS, f"{username}_growth.json")
    os.makedirs(_dirs.DIR_ANALYSIS, exist_ok=True)
    history = []
    if os.path.exists(snap_file):
        try:
            history = json.loads(open(snap_file,encoding="utf-8").read())
        except Exception:
            pass
    history.append({**stats, "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
    open(snap_file,"w",encoding="utf-8").write(json.dumps(history, indent=2))

    log(f"Snapshot #{len(history)} saved")
    res({"type":"growth","username":username,"stats":stats,"history":history})
    done(f"@{username}: {stats.get('followers',0):,} followers · {len(history)} snapshots total")


def _health(username, opts, log, prog, res, done, error):
    from tools.account_health import _scrape_account, _analyse, _save_html
    max_posts = int(opts.get("limit","100") or "100")
    log(f"Scraping @{username} (up to {max_posts} posts)...")
    try:
        raw = asyncio.run(_scrape_account(username, max_posts))
    except Exception as e:
        return error(f"Scrape failed: {e}")

    posts = raw.get("posts",[])
    log(f"Scraped {len(posts)} posts — analysing...")
    a = _analyse(raw)
    os.makedirs(_dirs.DIR_ANALYSIS, exist_ok=True)
    html_path = _save_html(username, a, _dirs.DIR_ANALYSIS)
    log(f"Report saved: {html_path}")
    res({"type":"health","username":username,"analysis":a,"html_path":html_path})
    done(f"Health score: {a.get('health_score',0)}/100 · {len(posts)} posts analysed")


# =============================================================================
# DOWNLOADERS
# =============================================================================

def _dl_video(url, opts, log, done, error):
    quality = str(opts.get("quality","1080")).replace("p","")
    out_dir = os.path.join(_dirs.DIR_DOWNLOADS, "single")
    os.makedirs(out_dir, exist_ok=True)
    is_yt = any(x in url for x in ("youtube.com","youtu.be"))
    log(f"Downloading {'YouTube' if is_yt else 'TikTok'} video...")
    if is_yt:
        cmd = ["yt-dlp", url, "-o", os.path.join(out_dir,"%(uploader)s_%(title)s.%(ext)s"),
               "--format", f"bestvideo[height<={quality}]+bestaudio/best",
               "--merge-output-format","mp4","--add-metadata","--progress"]
    else:
        cmd = ["yt-dlp", url, "-o", os.path.join(out_dir,"%(uploader)s_%(title)s.%(ext)s"),
               "--merge-output-format","mp4","--no-warnings","--progress"]
    _stream_cmd(cmd, log)
    done(f"Saved to: {out_dir}", path=out_dir)


def _dl_profile(username, opts, log, done, error):
    url     = f"https://www.tiktok.com/@{username.lstrip('@')}"
    out_dir = os.path.join(_dirs.DIR_DOWNLOADS, username)
    os.makedirs(out_dir, exist_ok=True)
    lim = opts.get("limit","")
    cmd = ["yt-dlp", url, "-o",
           os.path.join(out_dir,"%(upload_date)s_%(title)s.%(ext)s"),
           "--format","bestvideo+bestaudio/best","--merge-output-format","mp4",
           "--yes-playlist","--ignore-errors","--no-warnings","--progress"]
    if str(lim).isdigit(): cmd += ["--playlist-end", str(lim)]
    log(f"Downloading @{username}'s videos...")
    _stream_cmd(cmd, log)
    done(f"Saved to: {out_dir}", path=out_dir)


def _dl_playlist(url, opts, log, done, error):
    out_dir = os.path.join(_dirs.DIR_DOWNLOADS, "playlists")
    os.makedirs(out_dir, exist_ok=True)
    cmd = ["yt-dlp", url, "-o",
           os.path.join(out_dir,"%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s"),
           "--format","bestvideo[height<=1080]+bestaudio/best",
           "--merge-output-format","mp4","--yes-playlist",
           "--ignore-errors","--no-warnings","--progress"]
    log("Downloading playlist / channel...")
    _stream_cmd(cmd, log)
    done(f"Saved to: {out_dir}", path=out_dir)


def _spotify(url, opts, log, prog, done, error):
    from tools.music_downloader import _get_tracks
    url = re.sub(r"\?.*$","",url.strip())
    log("Reading Spotify track info...")
    tracks = _get_tracks(url)
    if not tracks:
        return error("Could not read track info. Make sure the URL is public.")

    quality = opts.get("audio_quality", opts.get("quality","320"))
    os.makedirs(_dirs.DIR_AUDIO, exist_ok=True)
    out_tpl = os.path.join(_dirs.DIR_AUDIO, "%(artist)s - %(title)s.%(ext)s")
    log(f"Found {len(tracks)} track(s) — downloading from YouTube Music...")

    ok_n = fail_n = 0
    for i,t in enumerate(tracks, 1):
        title, artist = t.get("title",""), t.get("artist","")
        if not title: fail_n += 1; continue
        log(f"[{i}/{len(tracks)}] {title}" + (f" — {artist}" if artist else ""))
        prog(i, len(tracks))
        success = False
        _cflags = {"creationflags": 0x08000000} if os.name == "nt" else {}
        for q2 in [f"ytmsearch1:{title} {artist}".strip(),
                   f"ytsearch1:{title} {artist}".strip()]:
            r = subprocess.run(["yt-dlp", q2,
                "--extract-audio","--audio-format","mp3",
                "--audio-quality",f"{quality}k","--output",out_tpl,
                "--no-playlist","--quiet","--no-warnings",
                "--embed-thumbnail","--add-metadata"],
                capture_output=True, **_cflags)
            if r.returncode == 0: success = True; break
        if success: ok_n += 1
        else: fail_n += 1; log(f"  ✗ not found")

    done(f"{ok_n}/{len(tracks)} tracks downloaded → {_dirs.DIR_AUDIO}", path=_dirs.DIR_AUDIO)


def _dl_song(title, artist, opts, log, prog, done, error):
    """
    Download a single song using the same YouTube Music search flow as the
    Spotify downloader, but without needing a Spotify URL.
    """
    try:
        from tools.music_downloader import _dl_tracks
    except Exception as e:
        return error(f"Music downloader not available: {e}")

    quality = opts.get("audio_quality", opts.get("quality","320"))
    os.makedirs(_dirs.DIR_AUDIO, exist_ok=True)

    desc = f"{title}" + (f" — {artist}" if artist else "")
    log(f"Downloading song: {desc}")
    prog(0, 1)

    ok_n, fail_n = _dl_tracks([{"title": title, "artist": artist}], quality, _dirs.DIR_AUDIO)
    if ok_n:
        prog(1, 1)
        done(f"1/1 tracks downloaded → {_dirs.DIR_AUDIO}", path=_dirs.DIR_AUDIO)
    else:
        error("Song could not be downloaded from YouTube Music.")


def _soundcloud(url, opts, log, done, error):
    q = opts.get("quality", opts.get("audio_quality","320"))
    os.makedirs(_dirs.DIR_AUDIO, exist_ok=True)
    cmd = ["yt-dlp", url,"--extract-audio","--audio-format","mp3",
           "--audio-quality",f"{q}k",
           "--output",os.path.join(_dirs.DIR_AUDIO,"%(uploader)s - %(title)s.%(ext)s"),
           "--progress","--ignore-errors"]
    log("Downloading from SoundCloud...")
    _stream_cmd(cmd, log)
    done(f"Saved to: {_dirs.DIR_AUDIO}", path=_dirs.DIR_AUDIO)


def _audio_extract(inp, opts, log, done, error):
    bitrate = opts.get("bitrate","320")
    os.makedirs(_dirs.DIR_AUDIO, exist_ok=True)
    if inp.startswith("http"):
        cmd = ["yt-dlp", inp,"--extract-audio","--audio-format","mp3",
               "--audio-quality",f"{bitrate}k",
               "--output",os.path.join(_dirs.DIR_AUDIO,"%(title)s.%(ext)s"),
               "--progress"]
        log("Extracting audio from URL...")
        _stream_cmd(cmd, log)
        done(f"Saved to: {_dirs.DIR_AUDIO}", path=_dirs.DIR_AUDIO)
    else:
        if not os.path.exists(inp):
            return error(f"File not found: {inp}")
        out = os.path.join(_dirs.DIR_AUDIO, Path(inp).stem+"_audio.mp3")
        log(f"Extracting audio from: {Path(inp).name}")
        cmd = ["ffmpeg","-y","-i",inp,"-vn","-acodec","libmp3lame",
               "-ab",f"{bitrate}k",out,"-hide_banner","-stats"]
        _stream_cmd(cmd, log)
        done(f"Saved: {out}", path=out)


# =============================================================================
# STUDIO
# =============================================================================

def _compress(inp, opts, log, done, error):
    """Route to the GUI compressor — handles preset cards, output folder, custom HB presets."""
    import queue as _q, threading as _th
    from tools.compressor import run_gui_compress
    ql = _q.Queue()
    _th.Thread(target=run_gui_compress, args=(opts, ql), daemon=True).start()
    while True:
        item = ql.get()
        if item is None: break
        t = item.get("type","")
        if   t == "log":   log(item.get("text",""))
        elif t == "done":  done(item.get("text",""), item.get("path",""))
        elif t == "error": error(item.get("text",""))


def _bulk_compress(folder, opts, log, prog, done, error):
    """Route to the GUI bulk compressor — handles preset cards and output folder."""
    import queue as _q, threading as _th
    from tools.compressor import run_gui_bulk_compress
    ql = _q.Queue()
    _th.Thread(target=run_gui_bulk_compress, args=(opts, ql), daemon=True).start()
    while True:
        item = ql.get()
        if item is None: break
        t = item.get("type","")
        if   t == "log":      log(item.get("text",""))
        elif t == "progress": prog(item.get("value",0), item.get("total",1))
        elif t == "done":     done(item.get("text",""), item.get("path",""))
        elif t == "error":    error(item.get("text",""))


def _bg_remove(inp, opts, log, prog, done, error):
    try:
        from rembg import remove
        from PIL import Image
    except ImportError:
        return error("rembg not installed. Run: pip install rembg pillow")

    exts = {".png",".jpg",".jpeg",".webp",".bmp"}
    if os.path.isdir(inp):
        files = [f for f in Path(inp).iterdir() if f.suffix.lower() in exts]
        if not files: return error("No images found in folder.")
        out_dir = os.path.join(inp, "no_bg")
        os.makedirs(out_dir, exist_ok=True)
        log(f"Processing {len(files)} image(s)...")
        for i,f in enumerate(files, 1):
            prog(i, len(files))
            log(f"[{i}/{len(files)}] {f.name}")
            try:
                out_img = remove(Image.open(str(f)))
                out_img.save(os.path.join(out_dir, f.stem+"_no_bg.png"))
            except Exception as e:
                log(f"  ✗ {e}")
        done(f"{len(files)} images → {out_dir}", path=out_dir)
    else:
        if not os.path.exists(inp): return error(f"File not found: {inp}")
        log(f"Removing background: {Path(inp).name}")
        try:
            out_path = os.path.join(Path(inp).parent, Path(inp).stem+"_no_bg.png")
            remove(Image.open(inp)).save(out_path)
            done(f"Saved: {out_path}", path=out_path)
        except Exception as e:
            error(f"Failed: {e}")


def _calendar(ppw, start_date, log, res, done, error):
    import datetime
    from tools.calendar import _load_bptf

    try:
        best_days, best_hours, _, username = _load_bptf()
    except Exception:
        best_days, best_hours, username = [0,2,4], [18,19,20], "your account"

    try:
        start = datetime.date.fromisoformat(start_date) if start_date else datetime.date.today()
    except ValueError:
        start = datetime.date.today()

    DAYS  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    sched = []
    cur   = start
    added = 0
    while added < ppw * 4:
        if cur.weekday() in best_days:
            hour = best_hours[added % len(best_hours)] if best_hours else 18
            sched.append({"date":cur.isoformat(),"day":DAYS[cur.weekday()],
                          "hour":hour,"label":f"{DAYS[cur.weekday()]} {cur.strftime('%b %d')} at {hour:02d}:00"})
            added += 1
        cur += datetime.timedelta(days=1)
        if added == 0 and (cur - start).days > 60: break  # safety

    log(f"Generated {len(sched)}-post schedule based on {username}'s best times")
    res({"type":"calendar","username":username,"posts_per_week":ppw,"schedule":sched})
    done(f"{len(sched)}-post calendar generated starting {start.isoformat()}")


# =============================================================================
# HELPERS
# =============================================================================

def _stream_cmd(cmd, log_fn):
    try:
        kwargs = dict(
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace")
        if os.name == "nt":               # hide console window on Windows
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        proc = subprocess.Popen(cmd, **kwargs)
        for line in proc.stdout:
            line = _strip(line).strip()
            if line: log_fn(line)
        proc.wait()
        return proc.returncode
    except FileNotFoundError:
        log_fn(f"Command not found: {cmd[0]}")
        return 1
