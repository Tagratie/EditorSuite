"""
tools/engagement.py
Tool 16 — Engagement Rate Calculator
Calculates ER and benchmarks against TikTok tier averages.
"""
from ui import theme as _T
from utils.helpers import ok, err, warn, divider, prompt, back_to_menu

BENCHMARKS = {
    "Nano (<10K)":     {"er": 17.99, "reach": 40},
    "Micro (10-100K)": {"er": 14.15, "reach": 35},
    "Mid (100K-1M)":   {"er": 10.53, "reach": 25},
    "Macro (1M+)":     {"er": 7.2,   "reach": 15},
}


def _grade(val: float, bench: float) -> str:
    if val >= bench * 1.2:
        return f"{_T.GREEN}ABOVE AVERAGE ✓{_T.R}"
    if val >= bench * 0.8:
        return f"{_T.YELLOW}AVERAGE{_T.R}"
    return f"{_T.RED}BELOW AVERAGE ✗{_T.R}"


def tool_engagerate():
    divider("ENGAGEMENT RATE CALCULATOR")
    print(f"  {_T.DIM}Calculate ER and benchmark against TikTok averages.{_T.R}")
    print(f"  {_T.DIM}Tip: use Competitor Tracker (tool 3) to get these numbers.{_T.R}\n")

    try:
        followers = int(prompt("Followers").replace(",", "").replace(".", ""))
        avg_views = int(prompt("Avg views per video").replace(",", "").replace(".", ""))
        avg_likes = int(prompt("Avg likes per video").replace(",", "").replace(".", ""))
        avg_comms = int(prompt("Avg comments per video", "0").replace(",", "").replace(".", ""))
        avg_share = int(prompt("Avg shares per video",  "0").replace(",", "").replace(".", ""))
    except Exception:
        err("Invalid number."); back_to_menu(); return

    er_likes   = (avg_likes / avg_views * 100) if avg_views else 0
    er_total   = ((avg_likes + avg_comms + avg_share) / avg_views * 100) if avg_views else 0
    reach_rate = (avg_views / followers * 100) if followers else 0

    tier = (
        "Nano (<10K)"     if followers < 10_000    else
        "Micro (10-100K)" if followers < 100_000   else
        "Mid (100K-1M)"   if followers < 1_000_000 else
        "Macro (1M+)"
    )
    bench_er    = BENCHMARKS[tier]["er"]
    bench_reach = BENCHMARKS[tier]["reach"]

    divider("RESULTS")
    print(f"  {_T.BOLD}Follower Tier:{_T.R}  {tier}\n")
    print(f"  {_T.BOLD}Engagement Rate (likes/views):{_T.R}  {er_likes:.2f}%  "
          f"{_T.DIM}(benchmark: {bench_er:.1f}%){_T.R}  {_grade(er_likes, bench_er)}")
    print(f"  {_T.BOLD}Total ER (likes+comments+shares):{_T.R}  {er_total:.2f}%")
    print(f"  {_T.BOLD}Reach Rate (views/followers):{_T.R}  {reach_rate:.1f}%  "
          f"{_T.DIM}(benchmark: {bench_reach}%){_T.R}  {_grade(reach_rate, bench_reach)}")

    print()
    if reach_rate < bench_reach * 0.7:
        warn("Low reach rate. Consider posting more often or changing posting times.")
    if er_likes < bench_er * 0.7:
        warn("Low engagement. Try stronger hooks in the first 2 seconds.")
    if er_likes >= bench_er:
        ok("Your engagement rate is healthy!")

    back_to_menu()
