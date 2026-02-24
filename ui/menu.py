"""
ui/menu.py
Two-screen navigation.
  build_menu()          → main screen (4 categories)
  build_category(idx)   → tool list for that category
Escape key handling is in main.py (_input returns "__esc__").
"""
from ui import theme as _T


CATEGORIES = [
    ("SCRAPERS", [
        ("Trending Audio Scraper",   "Find top songs from any hashtag"),
        ("Hashtag Frequency",        "Most-used hashtags in a niche"),
        ("Cross-Hashtag Sounds",     "Sounds trending across multiple niches"),
        ("Viral Video Finder",       "Top performing videos by view count"),
        ("TikTok Trending Now",      "What's blowing up globally right now"),
        ("Export to Spotify",        "Push trending TikTok sounds to a playlist"),
    ]),
    ("ANALYTICS", [
        ("Hashtag Analyzer",         "Compare hashtag reach & avg views"),
        ("Competitor Tracker",       "Side-by-side analysis of any account"),
        ("Best Posting Time",        "Find your best days & hours to post"),
        ("Engagement Calculator",    "ER rate benchmarked against TikTok averages"),
        ("Niche Report",             "Full audit: sounds + hashtags + viral"),
        ("Growth Tracker",           "Snapshot & chart follower growth over time"),
    ]),
    ("DOWNLOADERS", [
        ("TikTok / YouTube DL",             "Single video — best quality, MP4 output"),
        ("Profile & Playlist Downloader",   "Full profiles, playlists & channels"),
        ("Spotify / SoundCloud DL",         "Download any track, album, or playlist"),
        ("Audio Extractor",                 "MP3 from local file or TikTok / YouTube URL"),
    ]),
    ("STUDIO", [
        ("Video Compressor",         "HandBrake compress a single video file"),
        ("Bulk Compressor",          "Compress every video in a folder at once"),
        ("Background Remover",       "AI remove.bg locally — single or batch"),
        ("Posting Calendar",         "Posting schedule based on your account's data"),
    ]),
]


def build_menu() -> str:
    C, B, r, D, W = _T.CYAN, _T.BOLD, _T.R, _T.DIM, _T.WHITE
    lines = []
    for i, (label, tools) in enumerate(CATEGORIES, 1):
        lines.append(f"  {W}{B}{i}{r}  {label:<14}  {D}{len(tools)} tools{r}")
    lines += [
        "",
        f"  {C}S{r}  Settings",
        "",
        f"  {D}Pick a category (1-4), S for Settings, or Esc to quit.{r}",
    ]
    return "\n".join(lines)


def build_category(cat_idx: int) -> str:
    C, B, r, D, W = _T.CYAN, _T.BOLD, _T.R, _T.DIM, _T.WHITE
    cat_label, tools = CATEGORIES[cat_idx - 1]
    n = len(tools)
    lines = [
        f"  {D}EditorSuite  ›  {r}{B}{cat_label}{r}",
        f"  {D}{'─' * 52}{r}",
        "",
    ]
    for i, (name, desc) in enumerate(tools, 1):
        lines.append(f"  {W}{i}{r}  {B}{name:<32}{r}  {D}{desc}{r}")
    lines += [
        "",
        f"  {D}Pick a tool (1-{n}), or Esc for Home.{r}",
    ]
    return "\n".join(lines)
