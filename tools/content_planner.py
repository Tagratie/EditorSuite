"""
tools/content_planner.py
Tool 21 — Caption & Hook Writer
Tool 22 — Content Ideas Generator
No scraping — pure local generation based on proven TikTok content frameworks.
"""
import os
from datetime import datetime

from ui import theme as _T
from utils.helpers import ok, info, divider, prompt, save, saved_in, back_to_menu
from utils import dirs as _dirs


# ── Tool 21: Caption & Hook Writer ────────────────────────────────────────────

_HOOK_TEMPLATES = [
    # Curiosity / open loops
    ("Curiosity Hook",    "Nobody talks about this but {topic} completely changed how I {action}..."),
    ("Curiosity Hook",    "I wish someone told me this about {topic} before I {action}..."),
    ("Curiosity Hook",    "Stop scrolling — if you're into {topic} you NEED to see this"),
    # Controversy / bold claim
    ("Bold Claim",        "Unpopular opinion: {topic} is {bold_statement} and here's why"),
    ("Bold Claim",        "Everything you know about {topic} is wrong"),
    ("Bold Claim",        "Hot take: the {topic} advice everyone gives is actually terrible"),
    # Relatable pain point
    ("Pain Point",        "If you struggle with {pain}, you're not alone — here's what actually works"),
    ("Pain Point",        "The {topic} mistake I made that cost me {cost}"),
    ("Pain Point",        "Why {common_thing} never works for {topic} (and what does)"),
    # Social proof / results
    ("Results Hook",      "How I {result} in {timeframe} using nothing but {topic}"),
    ("Results Hook",      "{number} {topic} tips that actually got me {result}"),
    ("Results Hook",      "I tried every {topic} method so you don't have to — here's the winner"),
    # Educational / value
    ("Value Hook",        "{number} things every {niche} creator needs to know about {topic}"),
    ("Value Hook",        "The {topic} framework no one is teaching in {niche}"),
    ("Value Hook",        "How to {action} using {topic} — step by step"),
    # FOMO / urgency
    ("FOMO Hook",         "This {topic} trend is blowing up right now and most people haven't caught on"),
    ("FOMO Hook",         "Everyone in {niche} is doing this — are you?"),
    ("FOMO Hook",         "If you're not using {topic} for {action} yet, you're already behind"),
    # Story / personal
    ("Story Hook",        "A year ago I knew nothing about {topic}. Here's what changed everything"),
    ("Story Hook",        "The moment I realised {topic} was the missing piece for {action}"),
]

_CAPTION_CLOSERS = [
    "Save this so you don't forget it.",
    "Drop a comment if this helped you.",
    "Follow for more {niche} tips like this.",
    "Tag someone who needs to hear this.",
    "Share this with your {niche} friends.",
    "Which tip surprised you most? Let me know below.",
]


def tool_caption_writer():
    divider("CAPTION & HOOK WRITER")
    print(f"  {_T.DIM}Generates ready-to-use TikTok hooks & captions using proven frameworks.{_T.R}\n")

    niche  = prompt("Your niche / topic (e.g. video editing, gym, cooking)")
    if not niche:
        back_to_menu(); return

    action   = prompt("Action your audience wants (e.g. grow, edit faster, lose weight)", "grow")
    pain     = prompt("Main pain point they have (e.g. low views, no motivation)", "low views")
    result   = prompt("Result you can promise (e.g. 10k followers, better edits)", "better results")
    number   = prompt("A number to use in list posts", "5")

    # Fill placeholders
    fills = {
        "{topic}":          niche,
        "{niche}":          niche,
        "{action}":         action,
        "{pain}":           pain,
        "{result}":         result,
        "{number}":         number,
        "{timeframe}":      "30 days",
        "{cost}":           "months of progress",
        "{bold_statement}": "overrated",
        "{common_thing}":   "generic advice",
    }

    def _fill(s: str) -> str:
        for k, v in fills.items():
            s = s.replace(k, v)
        return s

    print()
    divider(f"HOOKS & CAPTIONS — {niche}")
    lines = [f"Caption & Hook Pack — {niche}", f"Generated: {datetime.now().strftime('%Y-%m-%d')}", "=" * 70]

    current_type = None
    for i, (hook_type, template) in enumerate(_HOOK_TEMPLATES, 1):
        if hook_type != current_type:
            print(f"\n  {_T.CYAN}{_T.BOLD}{hook_type}{_T.R}")
            lines.append(f"\n{hook_type}")
            current_type = hook_type
        filled = _fill(template)
        col    = _T.GREEN if i <= 3 else _T.R
        print(f"    {col}{i:>2}.{_T.R} {filled}")
        lines.append(f"  {i:>2}. {filled}")

    print(f"\n  {_T.BOLD}Caption closers:{_T.R}")
    lines.append("\nCAPTION CLOSERS")
    for closer in _CAPTION_CLOSERS:
        filled = _fill(closer)
        print(f"    {_T.DIM}→{_T.R}  {filled}")
        lines.append(f"  → {filled}")

    # Clipboard
    clip_text = "\n".join(
        _fill(t) for _, t in _HOOK_TEMPLATES
    )
    try:
        import subprocess
        subprocess.run("clip", input=clip_text.encode("utf-8"), check=True, shell=True)
        print(f"\n  {_T.GREEN}All hooks copied to clipboard!{_T.R}")
    except Exception:
        pass

    date = datetime.now().strftime("%Y-%m-%d_%H-%M")
    save(_dirs.DIR_ANALYSIS, f"captions_{niche.replace(' ','_')}_{date}.txt", lines)
    print(); saved_in(_dirs.DIR_ANALYSIS)
    back_to_menu()


# ── Tool 22: Content Ideas Generator ─────────────────────────────────────────

_CONTENT_TYPES = [
    ("Tutorial / How-To",     [
        "Step-by-step: how to {action} as a {niche} creator",
        "Beginner's guide to {topic} (no experience needed)",
        "The exact process I use for {action} — full breakdown",
        "How to {action} in under {timeframe}",
        "Common {topic} mistakes — and how to fix them",
    ]),
    ("Trending / Timely",     [
        "My honest reaction to the {topic} trend everyone is doing",
        "Rating viral {niche} content — what actually works",
        "This {topic} trend is everywhere right now — here's why",
        "Testing the most popular {niche} advice on TikTok",
        "The {topic} trend nobody's talking about yet",
    ]),
    ("Behind-the-Scenes",     [
        "A realistic day in my life as a {niche} creator",
        "My full {action} setup — everything I use",
        "What it actually takes to succeed at {topic}",
        "Unfiltered: what {niche} doesn't show you",
        "The real numbers behind my {topic} journey",
    ]),
    ("List / Roundup",        [
        "{number} {topic} tools that changed everything for me",
        "{number} things I wish I knew before starting {niche}",
        "{number} {action} tips I'd give my past self",
        "The only {number} {topic} resources you need",
        "{number} signs you're ready to level up in {niche}",
    ]),
    ("Challenge / Test",      [
        "I tried {topic} every day for 30 days — here's what happened",
        "Testing the most hyped {niche} method so you don't have to",
        "Can you really {result} in {timeframe}? I tested it",
        "{number}-day {topic} challenge — days 1, 15, and 30",
        "Doing what every {niche} guru recommends for a week",
    ]),
    ("Opinion / Hot Take",    [
        "The {topic} advice that's actually holding you back",
        "Overrated {niche} tools (and what to use instead)",
        "Why I quit {common_thing} and what I do now",
        "Unpopular opinion: {topic} is not what you think",
        "The {niche} myth I believed for too long",
    ]),
]


def tool_content_ideas():
    divider("CONTENT IDEAS GENERATOR")
    print(f"  {_T.DIM}Generates a full month of content ideas for your niche.{_T.R}\n")

    niche    = prompt("Your niche (e.g. video editing, fitness, cooking)")
    if not niche:
        back_to_menu(); return
    topic    = prompt(f"Main topic within {niche}", niche)
    action   = prompt("Core action your content teaches (e.g. edit, grow, cook)", "grow")
    result   = prompt("Result your audience wants", "better results")
    number   = prompt("Favourite list number", "5")
    timeframe= prompt("Timeframe for challenges/results", "30 days")
    per_week = int(prompt("Posts per week", "3") or "3")

    fills = {
        "{topic}":          topic,
        "{niche}":          niche,
        "{action}":         action,
        "{result}":         result,
        "{number}":         number,
        "{timeframe}":      timeframe,
        "{common_thing}":   "generic advice",
    }

    def _fill(s: str) -> str:
        for k, v in fills.items():
            s = s.replace(k, v)
        return s

    total_ideas = per_week * 4   # one month
    ideas_per_type = max(1, total_ideas // len(_CONTENT_TYPES))

    print()
    divider(f"30-DAY CONTENT IDEAS — {niche}")

    all_ideas = []
    lines = [
        f"Content Ideas — {niche}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d')}",
        f"Posts per week: {per_week} | Monthly total: {total_ideas}",
        "=" * 70,
    ]

    idea_num = 1
    for content_type, templates in _CONTENT_TYPES:
        print(f"\n  {_T.CYAN}{_T.BOLD}{content_type}{_T.R}")
        lines.append(f"\n{content_type}")
        for tmpl in templates[:ideas_per_type]:
            idea = _fill(tmpl)
            col  = _T.GREEN if idea_num <= 5 else _T.R
            print(f"    {col}{idea_num:>2}.{_T.R}  {idea}")
            lines.append(f"  {idea_num:>2}. {idea}")
            all_ideas.append(idea)
            idea_num += 1

    # Build a weekly schedule
    print(f"\n  {_T.BOLD}Suggested 4-week schedule ({per_week}x/week):{_T.R}\n")
    lines += ["", "4-WEEK SCHEDULE"]
    sched_ideas = (all_ideas * 4)[:total_ideas]
    idx = 0
    for week in range(1, 5):
        week_ideas = sched_ideas[idx:idx + per_week]
        week_line  = f"  Week {week}:"
        print(f"  {_T.CYAN}Week {week}{_T.R}")
        lines.append(f"Week {week}")
        for i, idea in enumerate(week_ideas, 1):
            print(f"    Post {i}:  {idea[:70]}")
            lines.append(f"  Post {i}:  {idea}")
        idx += per_week
        print()
        lines.append("")

    date = datetime.now().strftime("%Y-%m-%d_%H-%M")
    save(_dirs.DIR_ANALYSIS, f"ideas_{niche.replace(' ','_')}_{date}.txt", lines)
    print(); saved_in(_dirs.DIR_ANALYSIS)
    back_to_menu()
