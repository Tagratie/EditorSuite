"""
tools/account_health.py
TikTok Account Health Dashboard
Scrapes a profile and produces a full HTML report + terminal summary:
  - Follower/following/total-likes counts
  - Per-video stats (views, likes, shares, comments)
  - Avg views, engagement rate, posting frequency
  - Views trend (30d / 60d / 90d)
  - Best & worst performing videos
  - Top sounds used
  - Posting time heatmap (hour × weekday)
  - Growth health score (0-100)
"""
import asyncio
from collections import Counter, defaultdict
from datetime import datetime, timezone

from ui import theme as _T
from utils.helpers import ok, info, err, warn, divider, prompt, back_to_menu, clear_line
from utils import dirs as _dirs
from core.browser import new_browser


# ── Scraper ───────────────────────────────────────────────────────────────────

async def _scrape_account(username: str, max_posts: int) -> dict:
    from playwright.async_api import async_playwright

    profile = {}
    posts   = []
    seen    = set()

    async with async_playwright() as pw:
        browser, ctx = await new_browser(pw, mute=True)

        async def on_resp(response):
            url = response.url
            # Account info
            if "/api/user/detail" in url:
                try:
                    body    = await response.json()
                    u       = (body.get("userInfo") or body.get("UserInfo") or {})
                    user    = u.get("user") or u.get("User") or {}
                    stats   = u.get("stats") or u.get("Stats") or {}
                    profile.update({
                        "followers":  int(stats.get("followerCount")  or stats.get("fans")        or 0),
                        "following":  int(stats.get("followingCount") or stats.get("following")   or 0),
                        "likes":      int(stats.get("heartCount")     or stats.get("digg")        or 0),
                        "videos":     int(stats.get("videoCount")     or 0),
                        "nickname":   user.get("nickname") or username,
                        "bio":        user.get("signature") or "",
                        "verified":   bool(user.get("verified")),
                    })
                except Exception:
                    pass

            # Post list
            if "/api/post/item_list" in url:
                try:
                    body  = await response.json()
                    items = body.get("itemList") or []
                    for item in items:
                        vid = str(item.get("id") or "")
                        if not vid or vid in seen:
                            continue
                        seen.add(vid)
                        stats   = item.get("stats") or item.get("statistics") or {}
                        music   = item.get("music") or {}
                        author  = item.get("author") or {}
                        ts      = int(item.get("createTime") or 0)
                        dt      = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None
                        posts.append({
                            "id":       vid,
                            "views":    int(stats.get("playCount")    or 0),
                            "likes":    int(stats.get("diggCount")    or 0),
                            "comments": int(stats.get("commentCount") or 0),
                            "shares":   int(stats.get("shareCount")   or 0),
                            "sound":    (music.get("title") or "").strip(),
                            "desc":     (item.get("desc") or "").strip()[:120],
                            "ts":       ts,
                            "dt":       dt,
                            "weekday":  dt.weekday() if dt else -1,   # 0=Mon
                            "hour":     dt.hour      if dt else -1,
                            "url":      f"https://www.tiktok.com/@{username}/video/{vid}",
                        })
                except Exception:
                    pass

        pages = ctx.pages
    page = pages[0] if pages else await ctx.new_page()
        page.on("response", on_resp)
        await page.goto(f"https://www.tiktok.com/@{username}",
                        wait_until="domcontentloaded", timeout=30000)

        import asyncio as _a
        await _a.sleep(4)

        # TikTok profile pages load ~20 posts initially then require scrolling
        # to trigger more /api/post/item_list calls. We scroll + wait for
        # new network responses, and also try clicking any "load more" elements.
        import random as _r
        last_count = 0
        stale      = 0
        while len(seen) < max_posts and stale < 16:
            print(f"  Loaded {len(seen)} posts...", end="\r", flush=True)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.6)")
            await _a.sleep(0.3 + _r.random() * 0.3)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await _a.sleep(1.8 + _r.random() * 1.2)

            # Try clicking any visible "load more" / skeleton buttons
            for sel in [
                "[data-e2e='user-post-item-list'] ~ button",
                "button[class*='loadmore' i]",
                "button[class*='load-more' i]",
                "div[class*='loadmore' i]",
            ]:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=500):
                        await btn.click()
                        await _a.sleep(1.5)
                except Exception:
                    pass

            if len(seen) == last_count:
                stale += 1
                if stale < 16:
                    await _a.sleep(2.5 + _r.random() * 1.5)
            else:
                stale = 0
            last_count = len(seen)

        await browser.close()

    clear_line()
    return {"profile": profile, "posts": posts}


# ── Analytics ─────────────────────────────────────────────────────────────────

def _analyse(data: dict) -> dict:
    posts    = sorted(data["posts"], key=lambda p: p["ts"], reverse=True)
    profile  = data["profile"]
    n        = len(posts)
    if not n:
        return {}

    now_ts = datetime.now(tz=timezone.utc).timestamp()

    def _window(days):
        cutoff = now_ts - days * 86400
        return [p for p in posts if p["ts"] >= cutoff]

    def _avg_views(ps):
        return sum(p["views"] for p in ps) // max(len(ps), 1)

    w30, w60, w90 = _window(30), _window(60), _window(90)

    all_views = [p["views"] for p in posts]
    avg_views = sum(all_views) // n
    followers = profile.get("followers", 1) or 1

    # Engagement rate per post = (likes + comments + shares) / views
    eng_rates = []
    for p in posts:
        if p["views"] > 0:
            eng_rates.append((p["likes"] + p["comments"] + p["shares"]) / p["views"] * 100)
    avg_er = sum(eng_rates) / max(len(eng_rates), 1)

    # Posting frequency (posts per week over last 90 days)
    if w90 and len(w90) >= 2:
        span_days = (w90[0]["ts"] - w90[-1]["ts"]) / 86400
        freq_week = len(w90) / max(span_days, 1) * 7
    else:
        freq_week = 0

    # Views trend: compare 0-30 vs 31-60 vs 61-90 day windows
    avg_30  = _avg_views(w30)
    avg_31_60 = _avg_views([p for p in w60 if p not in w30])
    trend = ((avg_30 - avg_31_60) / max(avg_31_60, 1)) * 100 if avg_31_60 else 0

    # Top/bottom videos
    by_views = sorted(posts, key=lambda p: p["views"], reverse=True)
    top5     = by_views[:5]
    worst3   = [p for p in by_views[-5:] if p["views"] > 0]

    # Sound usage
    sound_counter = Counter(p["sound"] for p in posts if p["sound"] and
                            "original sound" not in p["sound"].lower())

    # Posting time heatmap: hour × weekday count
    heatmap = defaultdict(int)
    for p in posts:
        if p["hour"] >= 0 and p["weekday"] >= 0:
            heatmap[(p["weekday"], p["hour"])] += 1

    # Best posting slots (by avg views)
    slot_views = defaultdict(list)
    for p in posts:
        if p["hour"] >= 0 and p["weekday"] >= 0:
            slot_views[(p["weekday"], p["hour"])].append(p["views"])
    best_slots = sorted(
        [((d, h), sum(v)/len(v)) for (d, h), v in slot_views.items() if len(v) >= 2],
        key=lambda x: x[1], reverse=True
    )[:5]

    # Health score 0-100
    score = 50
    if avg_er >= 5:    score += 15
    elif avg_er >= 2:  score += 8
    if trend > 10:     score += 15
    elif trend > 0:    score += 8
    elif trend < -20:  score -= 15
    elif trend < 0:    score -= 8
    if freq_week >= 7:  score += 10
    elif freq_week >= 4: score += 5
    elif freq_week < 1:  score -= 10
    if n >= 50:         score += 10
    score = max(0, min(100, score))

    _days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    return {
        "profile":    profile,
        "n":          n,
        "avg_views":  avg_views,
        "avg_er":     avg_er,
        "freq_week":  freq_week,
        "trend":      trend,
        "avg_30":     avg_30,
        "avg_31_60":  avg_31_60,
        "avg_90":     _avg_views(w90),
        "w30_n":      len(w30),
        "w60_n":      len(w60),
        "w90_n":      len(w90),
        "top5":       top5,
        "worst3":     worst3,
        "sounds":     sound_counter.most_common(10),
        "best_slots": best_slots,
        "score":      score,
        "posts":      posts,
        "_days":      _days,
    }


# ── HTML Report ───────────────────────────────────────────────────────────────

def _save_html(username: str, a: dict, out_dir: str) -> str:
    import json, os
    from utils.html_report import _base, _write, _ts

    p    = a["profile"]
    days = a["_days"]
    score_color = ("#22c55e" if a["score"] >= 70 else
                   "#f59e0b" if a["score"] >= 40 else "#ef4444")
    trend_color = "#22c55e" if a["trend"] >= 0 else "#ef4444"
    trend_arrow = "↑" if a["trend"] >= 0 else "↓"

    # Top videos table
    top_rows = ""
    for i, v in enumerate(a["top5"], 1):
        top_rows += (f'<tr><td class="rank">{i}</td>'
                     f'<td><div class="name"><a href="{v["url"]}" target="_blank">'
                     f'{v["desc"][:70] or "(no caption)"}</a></div>'
                     f'<div class="sub">{v.get("dt","")}</div></td>'
                     f'<td class="count">{v["views"]:,}</td>'
                     f'<td class="count" style="color:#888">{v["likes"]:,}</td></tr>')

    # Views chart (last 30 posts chronological)
    chart_posts = list(reversed(a["posts"][:30]))
    c_labels = json.dumps([p2["dt"].strftime("%b %d") if p2["dt"] else "" for p2 in chart_posts])
    c_values = json.dumps([p2["views"] for p2 in chart_posts])

    views_chart = f"""
<div style="position:relative;height:240px">
<canvas id="viewsChart"></canvas>
</div>
<script>
new Chart(document.getElementById('viewsChart'), {{
  type: 'line',
  data: {{
    labels: {c_labels},
    datasets: [{{
      data: {c_values},
      borderColor: '#00fff5', backgroundColor: '#00fff510',
      borderWidth: 2, pointRadius: 3, fill: true, tension: 0.3
    }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ color:'#555', font:{{ size:9 }} }}, grid:{{ color:'#1a1a1a' }} }},
      y: {{ ticks: {{ color:'#555' }}, grid:{{ color:'#1a1a1a' }} }}
    }}
  }}
}});
</script>"""

    # Sounds bar chart
    s_labels = json.dumps([s for s, _ in a["sounds"][:8]])
    s_values = json.dumps([c for _, c in a["sounds"][:8]])
    sounds_chart = f"""
<div style="position:relative;height:200px">
<canvas id="soundsChart"></canvas>
</div>
<script>
new Chart(document.getElementById('soundsChart'), {{
  type: 'bar',
  data: {{
    labels: {s_labels},
    datasets: [{{ data: {s_values},
      backgroundColor: '#7c3aed22', borderColor: '#7c3aed', borderWidth:1, borderRadius:4 }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display:false }} }},
    scales: {{
      x: {{ ticks: {{ color:'#555', font:{{ size:9 }} }}, grid:{{ color:'#1a1a1a' }} }},
      y: {{ ticks: {{ color:'#555' }}, grid:{{ color:'#1a1a1a' }} }}
    }}
  }}
}});
</script>"""

    # Best posting slots
    slot_rows = ""
    for (d, h), avg in a["best_slots"]:
        ampm = f"{h % 12 or 12}{'am' if h < 12 else 'pm'}"
        slot_rows += (f'<tr><td class="name">{days[d]}</td>'
                      f'<td class="name">{ampm}</td>'
                      f'<td class="count">{avg:,.0f} avg views</td></tr>')

    body = f"""
<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:16px;margin-bottom:20px">
  <div class="card"><h2>Followers</h2><div class="stat">{p.get("followers",0):,}</div></div>
  <div class="card"><h2>Avg Views</h2><div class="stat">{a["avg_views"]:,}</div></div>
  <div class="card"><h2>Eng Rate</h2><div class="stat">{a["avg_er"]:.1f}%</div></div>
  <div class="card"><h2>Health Score</h2>
    <div class="stat" style="color:{score_color}">{a["score"]}/100</div></div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:20px">
  <div class="card"><h2>30-Day Avg</h2>
    <div class="stat">{a["avg_30"]:,}</div>
    <div class="stat-label">{a["w30_n"]} posts</div></div>
  <div class="card"><h2>60-Day Avg</h2>
    <div class="stat">{a["avg_31_60"]:,}</div></div>
  <div class="card"><h2>Views Trend</h2>
    <div class="stat" style="color:{trend_color}">{trend_arrow} {abs(a["trend"]):.0f}%</div>
    <div class="stat-label">vs previous 30 days</div></div>
</div>
<div style="display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-bottom:20px">
  <div class="card"><h2>Views Over Last 30 <span>Posts</span></h2>{views_chart}</div>
  <div class="card"><h2>Posting Stats</h2>
    <div style="margin-top:16px">
      <div class="stat-label">Posts per week</div>
      <div class="stat">{a["freq_week"]:.1f}</div>
    </div>
    <div style="margin-top:20px">
      <div class="stat-label">Total posts scraped</div>
      <div class="stat" style="font-size:1.6rem">{a["n"]}</div>
    </div>
    <div style="margin-top:20px">
      <div class="stat-label">Account verified</div>
      <div class="stat" style="font-size:1.4rem">{"✓ Yes" if p.get("verified") else "No"}</div>
    </div>
  </div>
</div>
<div style="display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-bottom:20px">
  <div class="card"><h2>Top <span>Sounds Used</span></h2>{sounds_chart}</div>
  <div class="card"><h2>Best <span>Posting Slots</span></h2>
  <table style="margin-top:8px">
    <tr><th>Day</th><th>Time</th><th style="text-align:right">Performance</th></tr>
    {slot_rows or "<tr><td colspan=3 style='color:#555'>Not enough data</td></tr>"}
  </table></div>
</div>
<div class="card" style="margin-bottom:20px"><h2>Top 5 <span>Performing Videos</span></h2>
<table><tr><th>#</th><th>Video</th><th style="text-align:right">Views</th>
  <th style="text-align:right">Likes</th></tr>
{top_rows or "<tr><td colspan=4 style='color:#555'>No data</td></tr>"}
</table></div>"""

    filename = f"health_{username}_{_ts()}.html"
    title    = f"@{username} — Account Health"
    meta     = [f"@{username}",
                f"{p.get('followers',0):,} followers",
                f"Score: {a['score']}/100"]
    return _write(out_dir, filename, _base(title, meta, body))


# ── Terminal summary ──────────────────────────────────────────────────────────

def _print_summary(username: str, a: dict) -> None:
    C, B, r, D, G, Y = _T.CYAN, _T.BOLD, _T.R, _T.DIM, _T.GREEN, _T.YELLOW
    p    = a["profile"]
    days = a["_days"]

    score_col = G if a["score"] >= 70 else (Y if a["score"] >= 40 else _T.RED)
    trend_col = G if a["trend"] >= 0 else _T.RED
    arrow     = "↑" if a["trend"] >= 0 else "↓"

    divider(f"ACCOUNT HEALTH — @{username}")
    print(f"  {B}{p.get('nickname', username)}{r}",
          f"{'  ✓ Verified' if p.get('verified') else ''}")
    if p.get("bio"):
        print(f"  {D}{p['bio'][:80]}{r}")
    print()

    print(f"  {'Followers':<20} {C}{B}{p.get('followers',0):>12,}{r}")
    print(f"  {'Following':<20} {D}{p.get('following',0):>12,}{r}")
    print(f"  {'Total Likes':<20} {D}{p.get('likes',0):>12,}{r}")
    print(f"  {'Posts scraped':<20} {D}{a['n']:>12,}{r}")
    print()
    print(f"  {'Avg Views (all)':<20} {C}{a['avg_views']:>12,}{r}")
    print(f"  {'Avg Views (30d)':<20} {C}{a['avg_30']:>12,}{r}")
    print(f"  {'Views Trend':<20} {trend_col}{arrow} {abs(a['trend']):.0f}%{r}  {D}vs prev 30d{r}")
    print(f"  {'Eng Rate':<20} {C}{a['avg_er']:>11.1f}%{r}")
    print(f"  {'Posts/week':<20} {C}{a['freq_week']:>12.1f}{r}")
    print()
    print(f"  Health Score:  {score_col}{B}{a['score']}/100{r}")
    print()

    if a["top5"]:
        print(f"  {B}Top Videos:{r}")
        for i, v in enumerate(a["top5"][:3], 1):
            print(f"  {i}. {G}{v['views']:>10,}{r} views  {D}{v['desc'][:55]}{r}")
    print()

    if a["sounds"]:
        print(f"  {B}Most-used Sounds:{r}")
        for s, c in a["sounds"][:5]:
            print(f"  {D}{c:>3}x{r}  {s[:50]}")
    print()

    if a["best_slots"]:
        print(f"  {B}Best Posting Times:{r}")
        for (d, h), avg in a["best_slots"][:3]:
            ampm = f"{h%12 or 12}{'am' if h<12 else 'pm'}"
            print(f"  {days[d]} {ampm:<6}  {D}{avg:>10,.0f} avg views{r}")
    print()


# ── Tool entrypoint ───────────────────────────────────────────────────────────

def tool_account_health():
    divider("TIKTOK ACCOUNT HEALTH DASHBOARD")
    print(f"  {_T.DIM}Full analysis: views trend, engagement, posting habits, top sounds.{_T.R}\n")

    from utils.config import get_my_username
    default_user = get_my_username() or ""
    username = prompt(f"TikTok username (no @)", default_user).strip().lstrip("@")
    if not username:
        back_to_menu(); return

    max_posts = int(prompt("Max posts to scrape", "100") or "100")
    print()
    info(f"Scraping @{username} — loading up to {max_posts} posts...")
    info("This takes 30-60 seconds depending on post count.\n")

    try:
        raw = asyncio.run(_scrape_account(username, max_posts))
    except Exception as e:
        err(f"Scrape failed: {e}")
        back_to_menu(); return

    if not raw["posts"]:
        err("No posts found — account may be private or username incorrect.")
        back_to_menu(); return

    ok(f"Loaded {len(raw['posts'])} posts\n")

    a = _analyse(raw)
    if not a:
        err("Could not analyse data."); back_to_menu(); return

    _print_summary(username, a)

    import os
    os.makedirs(_dirs.DIR_ANALYSIS, exist_ok=True)
    from utils.html_report import _save_and_open
    _save_and_open(_save_html, username, a, _dirs.DIR_ANALYSIS,
                   label="Account Health Report")

    back_to_menu()
