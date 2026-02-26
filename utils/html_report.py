"""
utils/html_report.py
Shared HTML report engine.

Produces self-contained single-file HTML dashboards that open in any browser.
Uses Chart.js (from cdnjs CDN) for bar charts and inline CSS — no build tools.

Public API:
    save_sounds_report(hashtag, scanned, kept, removed, dir_path) -> path
    save_hashtag_report(tags, results, dir_path) -> path
    save_niche_report(hashtag, sounds, tags, videos, scanned, dir_path) -> path
    save_viral_report(hashtag, videos, dir_path) -> path
"""
from __future__ import annotations
import os
import sys
from datetime import datetime


# ── Base template ─────────────────────────────────────────────────────────────

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #0d0d0d; color: #e0e0e0; min-height: 100vh; }
.header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
          border-bottom: 1px solid #00fff520; padding: 28px 40px; }
.header h1 { font-size: 1.6rem; font-weight: 700; color: #00fff5; letter-spacing: 1px; }
.header .meta { color: #888; font-size: 0.82rem; margin-top: 6px; }
.badge { display: inline-block; background: #00fff515; border: 1px solid #00fff530;
         color: #00fff5; border-radius: 999px; padding: 2px 12px;
         font-size: 0.75rem; margin-right: 8px; }
.container { max-width: 1100px; margin: 0 auto; padding: 32px 24px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }
.grid.thirds { grid-template-columns: 1fr 1fr 1fr; }
.grid.full { grid-template-columns: 1fr; }
@media (max-width: 768px) { .grid, .grid.thirds { grid-template-columns: 1fr; } }
.card { background: #111; border: 1px solid #222; border-radius: 12px; padding: 24px; }
.card h2 { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 2px;
           color: #555; margin-bottom: 16px; }
.card h2 span { color: #00fff5; }
.stat { font-size: 2.4rem; font-weight: 700; color: #fff; }
.stat-label { color: #555; font-size: 0.8rem; margin-top: 4px; }
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th { text-align: left; color: #555; font-size: 0.72rem; text-transform: uppercase;
     letter-spacing: 1px; padding: 8px 0; border-bottom: 1px solid #222; }
td { padding: 10px 0; border-bottom: 1px solid #191919; vertical-align: top; }
tr:last-child td { border-bottom: none; }
.rank { color: #555; width: 32px; }
.gold { color: #ffd700; } .silver { color: #c0c0c0; } .bronze { color: #cd7f32; }
.name { font-weight: 600; color: #e0e0e0; }
.sub { color: #555; font-size: 0.78rem; margin-top: 2px; }
.count { color: #00fff5; font-weight: 700; text-align: right; min-width: 60px; }
.tag { display: inline-block; background: #00fff510; border: 1px solid #00fff520;
       color: #00fff5; border-radius: 6px; padding: 3px 10px; margin: 3px;
       font-size: 0.8rem; }
.bar-wrap { background: #1a1a1a; border-radius: 4px; height: 6px; margin-top: 6px; }
.bar-fill { background: linear-gradient(90deg, #00fff5, #0080ff);
            border-radius: 4px; height: 6px; transition: width 0.5s; }
a { color: #4a9eff; text-decoration: none; } a:hover { text-decoration: underline; }
.chart-wrap { position: relative; height: 280px; }
.section-title { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 2px;
                 color: #444; margin: 32px 0 16px; }
"""

_CHART_JS = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"


def _base(title: str, meta: list[str], body: str) -> str:
    badges = "".join(f'<span class="badge">{m}</span>' for m in meta)
    ts = datetime.now().strftime("%B %d, %Y  %H:%M")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — EditorSuite</title>
<script src="{_CHART_JS}"></script>
<style>{_CSS}</style>
</head>
<body>
<div class="header">
  <h1>{title}</h1>
  <div class="meta">{badges}<span style="color:#333">{ts}</span></div>
</div>
<div class="container">
{body}
</div>
</body>
</html>"""


def _bar_chart(canvas_id: str, labels: list, values: list, color: str = "#00fff5") -> str:
    import json
    lbl_js  = json.dumps([str(l) for l in labels[:20]])
    val_js  = json.dumps([v for v in values[:20]])
    return f"""
<div class="chart-wrap">
<canvas id="{canvas_id}"></canvas>
</div>
<script>
new Chart(document.getElementById('{canvas_id}'), {{
  type: 'bar',
  data: {{
    labels: {lbl_js},
    datasets: [{{ data: {val_js}, backgroundColor: '{color}22',
      borderColor: '{color}', borderWidth: 1, borderRadius: 4 }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ color: '#555', font: {{ size: 10 }} }},
             grid: {{ color: '#1a1a1a' }} }},
      y: {{ ticks: {{ color: '#555' }}, grid: {{ color: '#1a1a1a' }} }}
    }}
  }}
}});
</script>"""


def _rank_icon(i: int) -> str:
    return {1: "&#x1F947;", 2: "&#x1F948;", 3: "&#x1F949;"}.get(i, "") if i <= 3 else ""


# ── Public report builders ────────────────────────────────────────────────────

def save_sounds_report(hashtag: str, scanned: int, kept: list, removed: list, out_dir: str) -> str:
    top     = kept[:20]
    max_c   = top[0]["count"] if top else 1
    labels  = [s["title"][:25] for s in top]
    values  = [s["count"] for s in top]

    rows = ""
    for i, s in enumerate(top, 1):
        pct  = int(100 * s["count"] / max_c)
        icon = _rank_icon(i)
        rows += f"""<tr>
  <td class="rank">{icon or i}</td>
  <td><div class="name">{s['title']}</div><div class="sub">{s['author']}</div>
      <div class="bar-wrap"><div class="bar-fill" style="width:{pct}%"></div></div></td>
  <td class="count">{s['count']}x</td>
</tr>"""

    body = f"""
<div class="grid thirds">
  <div class="card"><h2>Videos <span>Scanned</span></h2>
    <div class="stat">{scanned:,}</div></div>
  <div class="card"><h2>Sounds <span>Found</span></h2>
    <div class="stat">{len(kept):,}</div></div>
  <div class="card"><h2>Sounds <span>Filtered</span></h2>
    <div class="stat" style="color:#555">{len(removed):,}</div></div>
</div>
<div class="grid full">
  <div class="card"><h2>Top 20 <span>Chart</span></h2>
    {_bar_chart('soundsChart', labels, values)}</div>
</div>
<div class="grid full">
  <div class="card"><h2>Full <span>Rankings</span></h2>
  <table><tr><th>#</th><th>Sound</th><th style="text-align:right">Videos</th></tr>
  {rows}</table></div>
</div>"""

    return _write(out_dir, f"sounds_{hashtag}_{_ts()}.html",
                  _base(f"Trending Sounds — #{hashtag}", [f"#{hashtag}", f"{scanned} videos", f"{len(kept)} sounds"], body))


def save_hashtag_report(tags: list, results: dict, out_dir: str) -> str:
    ranked = sorted(results.items(), key=lambda x: x[1]["avg"], reverse=True)
    labels = [f"#{t}" for t, _ in ranked]
    values = [d["avg"] for _, d in ranked]

    rows = ""
    for i, (tag, d) in enumerate(ranked, 1):
        icon = _rank_icon(i)
        rows += f"""<tr>
  <td class="rank">{icon or i}</td>
  <td><div class="name">#{tag}</div></td>
  <td class="count">{d['avg']:,}</td>
  <td class="count" style="color:#888">{d.get('videos', '?')}</td>
</tr>"""

    body = f"""
<div class="grid full">
  <div class="card"><h2>Average Views <span>by Hashtag</span></h2>
    {_bar_chart('hashChart', labels, values, '#7c3aed')}</div>
</div>
<div class="grid full">
  <div class="card"><h2>Full <span>Results</span></h2>
  <table><tr><th>#</th><th>Hashtag</th>
    <th style="text-align:right">Avg Views</th>
    <th style="text-align:right">Videos</th></tr>
  {rows}</table></div>
</div>"""

    return _write(out_dir, f"hashtags_{_ts()}.html",
                  _base("Hashtag Analyzer", [f"{len(tags)} hashtags"], body))


def save_niche_report(hashtag: str, sounds: list, tag_counts: list, videos: list,
                      scanned: int, out_dir: str) -> str:
    # sounds: list of dicts,  tag_counts: [(tag,count)],  videos: list of dicts
    top_sounds  = sounds[:15]
    top_tags    = tag_counts[:20]
    top_videos  = videos[:10]

    s_labels = [s["title"][:20] for s in top_sounds]
    s_vals   = [s["count"] for s in top_sounds]
    t_labels = [f"#{t}" for t, _ in top_tags]
    t_vals   = [c for _, c in top_tags]

    sound_rows = ""
    for i, s in enumerate(top_sounds, 1):
        sound_rows += f'<tr><td class="rank">{_rank_icon(i) or i}</td>' \
                      f'<td><div class="name">{s["title"]}</div>' \
                      f'<div class="sub">{s["author"]}</div></td>' \
                      f'<td class="count">{s["count"]}x</td></tr>'

    tag_html = "".join(f'<span class="tag">#{t} <strong>{c}</strong></span>'
                       for t, c in top_tags)

    video_rows = ""
    for v in top_videos:
        url = f"https://www.tiktok.com/@{v['user']}/video/{v['id']}"
        video_rows += f'<tr><td><div class="name">' \
                      f'<a href="{url}" target="_blank">@{v["user"]}</a></div>' \
                      f'<div class="sub">{v["desc"][:80]}</div></td>' \
                      f'<td class="count">{v["views"]:,}</td></tr>'

    body = f"""
<div class="grid thirds">
  <div class="card"><h2>Videos <span>Scanned</span></h2>
    <div class="stat">{scanned:,}</div></div>
  <div class="card"><h2>Sounds <span>Found</span></h2>
    <div class="stat">{len(sounds):,}</div></div>
  <div class="card"><h2>Viral <span>Videos</span></h2>
    <div class="stat">{len(videos):,}</div></div>
</div>
<div class="grid">
  <div class="card"><h2>Top Sounds <span>Chart</span></h2>
    {_bar_chart('soundsNiche', s_labels, s_vals)}</div>
  <div class="card"><h2>Top Hashtags <span>Chart</span></h2>
    {_bar_chart('tagsNiche', t_labels, t_vals, '#7c3aed')}</div>
</div>
<div class="grid">
  <div class="card"><h2>Top <span>Sounds</span></h2>
  <table><tr><th>#</th><th>Sound</th><th style="text-align:right">Uses</th></tr>
  {sound_rows}</table></div>
  <div class="card"><h2>Top <span>Hashtags</span></h2>
  <div style="padding-top:8px">{tag_html}</div></div>
</div>
<div class="grid full">
  <div class="card"><h2>Top Viral <span>Videos</span></h2>
  <table><tr><th>Video</th><th style="text-align:right">Views</th></tr>
  {video_rows}</table></div>
</div>"""

    return _write(out_dir, f"niche_{hashtag}_{_ts()}.html",
                  _base(f"Niche Report — #{hashtag}", [f"#{hashtag}", f"{scanned} videos"], body))


def save_viral_report(hashtag: str, videos: list, out_dir: str) -> str:
    top     = videos[:20]
    labels  = [f"@{v['user']}" for v in top]
    values  = [v["views"] for v in top]

    rows = ""
    for i, v in enumerate(top, 1):
        url = f"https://www.tiktok.com/@{v['user']}/video/{v['id']}"
        rows += f'<tr><td class="rank">{_rank_icon(i) or i}</td>' \
                f'<td><div class="name"><a href="{url}" target="_blank">@{v["user"]}</a></div>' \
                f'<div class="sub">{v["desc"][:90]}</div></td>' \
                f'<td class="count">{v["views"]:,}</td></tr>'

    body = f"""
<div class="grid full">
  <div class="card"><h2>Views <span>by Video</span></h2>
    {_bar_chart('viralChart', labels, values, '#f59e0b')}</div>
</div>
<div class="grid full">
  <div class="card"><h2>Top <span>Videos</span></h2>
  <table><tr><th>#</th><th>Video</th><th style="text-align:right">Views</th></tr>
  {rows}</table></div>
</div>"""

    return _write(out_dir, f"viral_{hashtag}_{_ts()}.html",
                  _base(f"Viral Videos — #{hashtag}", [f"#{hashtag}", f"{len(videos)} videos"], body))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M")


def _write(folder: str, filename: str, html: str) -> str:
    """Write HTML to disk. Falls back to Desktop if primary path fails."""
    # Try primary path
    for attempt_dir in [folder, os.path.join(os.path.expanduser("~"), "Desktop")]:
        try:
            os.makedirs(attempt_dir, exist_ok=True)
            path = os.path.join(attempt_dir, filename)
            with open(path, "w", encoding="utf-8", errors="replace") as f:
                f.write(html)
            if attempt_dir != folder:
                print(f"  [!] Primary save path failed — saved to Desktop instead")
            return path
        except Exception as e:
            print(f"  [!] Could not save to {attempt_dir}: {e}")
    return ""


def open_report(path: str) -> None:
    """Open HTML report in default browser. Uses os.startfile on Windows (most reliable)."""
    if not path:
        return
    if not os.path.exists(path):
        print(f"  [!] Report file not found: {path}")
        return
    print(f"  [i] Report saved: {path}")
    try:
        if os.name == "nt":
            # os.startfile is the correct Windows API — webbrowser is unreliable
            os.startfile(path)
        elif sys.platform == "darwin":
            import subprocess
            subprocess.Popen(["open", path])
        else:
            import subprocess
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print(f"  [!] Could not auto-open browser: {e}")
        print(f"  [i] Open manually: {path}")


def _save_and_open(save_fn, *args, label: str = "Report") -> None:
    """
    Call save_fn(*args), print the path, and open in browser.
    Shows full traceback if save fails instead of silently doing nothing.
    Tries multiple open methods on Windows for maximum compatibility.
    """
    import traceback
    import subprocess

    # Save
    try:
        path = save_fn(*args)
    except Exception:
        print("\n  [!] HTML report generation failed:")
        traceback.print_exc()
        return

    if not path or not os.path.exists(path):
        print("  [!] HTML file was not written — check disk permissions.")
        return

    sz = os.path.getsize(path) / 1024
    print(f"  [+] {label} saved ({sz:.0f} KB):")
    print(f"      {path}")

    # Open — try every method until one works
    if os.name == "nt":
        methods = [
            ("os.startfile",   lambda: os.startfile(path)),
            ("explorer",       lambda: subprocess.Popen(["explorer", path])),
            ("cmd start",      lambda: subprocess.Popen(
                                   f'start "" "{path}"', shell=True)),
        ]
        for name, fn in methods:
            try:
                fn()
                return   # success
            except Exception as e:
                pass
        # All failed — just show the path
        print(f"  [!] Could not auto-open. Open the file above manually.")
    else:
        try:
            from pathlib import Path
            import webbrowser
            webbrowser.open(Path(path).resolve().as_uri())
        except Exception:
            try:
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.Popen([opener, path])
            except Exception as e:
                print(f"  [!] Could not open: {e}\n  Open manually: {path}")
