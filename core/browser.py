"""
core/browser.py
Shared Playwright browser setup used by all scraper tools.
"""

_BARGS = [
    "--disable-blink-features=AutomationControlled",
    "--window-position=-32000,-32000",
    "--window-size=1280,900",
]
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


async def new_browser(pw, mute: bool = False):
    """Launch a headless-off Chromium browser context. Returns (browser, ctx)."""
    args = (["--mute-audio"] if mute else []) + _BARGS
    browser = await pw.chromium.launch(headless=False, args=args)
    ctx = await browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent=_UA,
        locale="en-US",
    )
    return browser, ctx
