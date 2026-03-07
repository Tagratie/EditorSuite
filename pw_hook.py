# PyInstaller runtime hook — executes before any app code.
#
# WHY THIS EXISTS:
# When frozen as a .exe, Playwright looks up browser paths from its internal
# registry file which gets extracted to _MEI.../playwright/driver/package/...
# That temp path is recreated on every launch with a different suffix, so
# browsers installed there are never found on the next run.
#
# FIX: Always point PLAYWRIGHT_BROWSERS_PATH at the real persistent location
# BEFORE any Playwright import can happen.  Two critical rules:
#   1. No `if os.path.isdir()` guard — the dir may not exist yet on first run,
#      but we still need the var set so Playwright installs there, not in _MEI.
#   2. Hard-assign, never setdefault — PyInstaller may have already injected
#      a _MEI path via its own hooks; setdefault would silently keep it.

import os

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "ms-playwright"
)
