
# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

ROOT = Path(r'C:\Program Files\GitHub\EditorSuite')

a = Analysis(
    [str(ROOT / 'gui_launcher.py')],
    pathex=[str(ROOT)],
    binaries=[
        # Bundle yt-dlp and ffmpeg directly — available in _MEIPASS at runtime
        (str(ROOT / 'bin' / 'yt-dlp.exe'), '.'),
        (str(ROOT / 'bin' / 'ffmpeg.exe'), '.'),
    ],
    datas=[
        (str(ROOT / 'gui' / 'static'), 'gui/static'),
        (str(ROOT / 'gui' / 'detector.py'), 'gui'),
        (str(ROOT / 'gui' / 'runner.py'), 'gui'),
        (str(ROOT / 'gui' / 'server.py'), 'gui'),
        (str(ROOT / 'tools'), 'tools'),
        (str(ROOT / 'utils'), 'utils'),
        (str(ROOT / 'ui'), 'ui'),
        (str(ROOT / 'core'), 'core'),
        (str(ROOT / 'pw_hook.py'), '.'),
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
        'multiprocessing', 'multiprocessing.spawn', 'multiprocessing.forkserver',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(ROOT / 'pw_hook.py')],
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
    # Fixed extraction dir — avoids random _MEI* temp folders.
    # Files persist between runs; PyInstaller only re-extracts changed ones.
    # Must be a string the bootloader can evaluate — we use %LOCALAPPDATA%.
    runtime_tmpdir=r'%LOCALAPPDATA%\EditorSuite\runtime',
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=str(ROOT / 'gui' / 'static' / 'favicon.ico'),
    version=None,
)
