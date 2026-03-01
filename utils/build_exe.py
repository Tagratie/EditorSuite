"""
build_exe.py — Package EditorSuite into a standalone Windows .exe
Run once:  python build_exe.py

Output: dist/EditorSuite.exe  (~50-80 MB, no Python install needed)
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
BUILD = ROOT / "build_tmp"

print("\n  EditorSuite — Build .exe\n")

# ── Step 1: ensure PyInstaller ────────────────────────────────────────────────
try:
    import PyInstaller
    print("  [✓] PyInstaller found")
except ImportError:
    print("  [→] Installing PyInstaller...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "--quiet"], check=True)
    print("  [✓] PyInstaller installed")

# ── Step 2: write the .spec file ─────────────────────────────────────────────
spec_content = f"""
# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

ROOT = Path(r'{ROOT}')

a = Analysis(
    [str(ROOT / 'gui_launcher.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'gui' / 'static'), 'gui/static'),   # includes favicon.ico
        (str(ROOT / 'gui' / 'detector.py'), 'gui'),
        (str(ROOT / 'gui' / 'runner.py'), 'gui'),
        (str(ROOT / 'gui' / 'server.py'), 'gui'),
        (str(ROOT / 'tools'), 'tools'),
        (str(ROOT / 'utils'), 'utils'),
        (str(ROOT / 'ui'), 'ui'),
        (str(ROOT / 'core'), 'core'),
    ],
    hiddenimports=[
        'flask', 'flask.json', 'werkzeug', 'jinja2', 'click',
        'playwright', 'playwright.async_api', 'playwright.sync_api',
        'asyncio', 'aiohttp',
        'yt_dlp', 'mutagen',
        'PIL', 'PIL.Image',
        'spotipy',
        'rembg',
        'win32gui', 'win32con', 'win32process', 'win32api',
        'pywintypes', 'winreg',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'numpy.testing'],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='EditorSuite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=str(ROOT / 'gui' / 'static' / 'favicon.ico'),
    version=None,
)
"""

spec_path = ROOT / "EditorSuite.spec"
spec_path.write_text(spec_content, encoding="utf-8")
print("  [✓] EditorSuite.spec written")

# ── Step 3: run PyInstaller ───────────────────────────────────────────────────
print("  [→] Building... (this takes 1-3 minutes)\n")
result = subprocess.run(
    [sys.executable, "-m", "PyInstaller",
     "--distpath", str(DIST),
     "--workpath", str(BUILD),
     "--noconfirm",
     str(spec_path)],
    cwd=str(ROOT)
)

if result.returncode != 0:
    print("\n  [✗] Build failed. Check output above.")
    sys.exit(1)

exe_path = DIST / "EditorSuite.exe"
if exe_path.exists():
    size_mb = exe_path.stat().st_size / 1024 / 1024
    print(f"\n  ✓ Done!  dist/EditorSuite.exe  ({size_mb:.0f} MB)")

    # Refresh Windows icon cache — forces Explorer to show the new icon immediately
    if os.name == "nt":
        print("  [→] Refreshing icon cache...")
        subprocess.run(["ie4uinit.exe", "-show"], capture_output=True)
        import ctypes
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
        print("  [✓] Icon cache cleared")

    print(f"  → Double-click EditorSuite.exe to launch — no Python needed.\n")
else:
    print("\n  [!] Build finished but EditorSuite.exe not found in dist/")
