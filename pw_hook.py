# PyInstaller runtime hook — runs before any app code
# Redirects Playwright to system-installed browsers instead of temp dir
import os
ms_playwright = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
if os.path.isdir(ms_playwright):
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", ms_playwright)
