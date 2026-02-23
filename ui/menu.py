"""
ui/menu.py
Two-screen navigation system.

  build_menu()          → full category list  (main screen)
  build_category(idx)   → slim tool list for one category  (submenu)

Design goals:
  - Main screen: full banner + clean numbered categories
  - Submenu: NO banner repeat — just a breadcrumb + tool list
  - Consistent column alignment
"""
from ui import theme as _T


CATEGORIES = [
    ("SCRAPERS", [
        ("Trending Audio Scraper",   "Find top songs from any hashtag"),
        ("Hashtag Frequency",        "Most-used hashtags in a niche"),
        ("Cross-Hashtag Sounds",     "Sounds trending across multiple niches"),
        ("Viral Video Finder",       "Top performing videos by view count"),
        ("Hashtag Suggester",        "Find related hashtags from TikTok search"),
    ]),
    ("ANALYZERS", [
        ("Hashtag Analyzer",         "Compare hashtag reach & avg views"),
        ("Competitor Tracker",       "Side-by-side analysis of any account"),
        ("Best Posting Time",        "Find your best days & hours to post"),
        ("Engagement Calculator",    "ER rate benchmarked against TikTok averages"),
        ("Niche Report",             "Full audit: sounds + hashtags + viral"),
    ]),
    ("PLANNERS", [
        ("Export to Spotify",        "Push trending TikTok sounds to a playlist"),
        ("Posting Calendar",         "Generate your 4-week posting schedule"),
        ("Growth Tracker",           "Snapshot & chart follower growth over time"),
        ("Caption & Hook Writer",    "Generate hooks & captions for your niche"),
        ("Content Ideas Generator",  "30 days of content ideas in one go"),
    ]),
    ("DOWNLOADERS", [
        ("TikTok / YouTube DL",      "Single video — best quality, MP4 output"),
        ("Profile Downloader",       "All videos from a TikTok / YouTube profile"),
        ("YouTube Playlist DL",      "Download a full playlist or channel"),
        ("Spotify / SoundCloud DL",  "Download any track, album, or playlist"),
        ("Audio Extractor",          "Rip audio from any local video to MP3"),
    ]),
    ("VIDEO TOOLS", [
        ("Video Compressor",         "HandBrake compress a single video file"),
        ("Video Speed Changer",      "Slow-mo or speed up any video with ffmpeg"),
        ("Background Remover",       "AI remove.bg locally — single or batch"),
        ("Bulk Compressor",          "Compress every video in a folder at once"),
        ("Video Trimmer / Cutter",   "Trim or split any video with exact timestamps"),
    ]),
    ("CREATOR TOOLS", [
        ("Caption Generator",        "Transcribe any video to SRT/TXT/VTT with local AI"),
        ("Video Merge",              "Join multiple clips into one — no re-encode"),
        ("Thumbnail Extractor",      "Grab any frame from a video as a PNG/JPG"),
        ("Bulk Rename",              "Rename every file in a folder with a template"),
        ("TikTok Trending Now",      "What's blowing up globally right now"),
    ]),
]


def build_menu() -> str:
    """Main screen — shows the 5 categories."""
    C, B, r, D, W = _T.CYAN, _T.BOLD, _T.R, _T.DIM, _T.WHITE

    lines = []
    for i, (label, _) in enumerate(CATEGORIES, 1):
        lines.append(f"  {W}{B}{i}{r}  {label}")

    lines += [
        "",
        f"  {C}S{r}  Settings",
        "",
        f"  {D}Pick a category (1-6), S for Settings, or q to quit.{r}",
    ]
    return "\n".join(lines)


def build_category(cat_idx: int) -> str:
    """
    Submenu — compact header + tool list for one category.
    No banner, no clearing — caller handles that.
    cat_idx is 1-based.
    """
    C, B, r, D, W, G = _T.CYAN, _T.BOLD, _T.R, _T.DIM, _T.WHITE, _T.GREEN
    cat_label, tools  = CATEGORIES[cat_idx - 1]

    # Breadcrumb header
    lines = [
        f"  {D}EditorSuite  ›  {r}{B}{cat_label}{r}",
        f"  {D}{'─' * 52}{r}",
        "",
    ]

    for i, (name, desc) in enumerate(tools, 1):
        lines.append(f"  {W}{i}{r}  {B}{name:<28}{r}  {D}{desc}{r}")

    lines += [
        "",
        f"  {D}Pick a tool (1-5), or b for Home.{r}",
    ]
    return "\n".join(lines)
