"""
build_exe.py — Package EditorSuite into a standalone Windows release
Run once:  python build_exe.py

Output:
  dist/
    EditorSuite.exe          — main app (single-file, no Python needed)
    EditorSuiteInstaller.exe — run once to install/update into Program Files
    version.txt              — version string read by installer
    README_INSTALL.txt       — instructions

Workflow:
  1. Bump VERSION below
  2. python build_exe.py
  3. Zip dist/ and distribute it
  4. User extracts + runs EditorSuiteInstaller.exe
  5. Future updates: run EditorSuiteInstaller.exe again — config/data preserved
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

ROOT    = Path(__file__).parent
DIST    = ROOT / "dist"
BUILD   = ROOT / "build_tmp"

# ── Bump this for every release ───────────────────────────────────────────────
VERSION = "2.0.0"

print(f"\n  EditorSuite v{VERSION} — Build\n")

# ── Step 1: ensure PyInstaller ────────────────────────────────────────────────
try:
    import PyInstaller
    print("  [✓] PyInstaller found")
except ImportError:
    print("  [→] Installing PyInstaller...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "--quiet"], check=True)
    print("  [✓] PyInstaller installed")

# ── Step 2: write the .spec file ─────────────────────────────────────────────
# ── Download yt-dlp.exe and ffmpeg.exe into a local bin/ folder ──────────────
# These get bundled directly into the .exe — no runtime download needed.
_bin_dir = ROOT / "bin"
_bin_dir.mkdir(exist_ok=True)

def _fetch(name, url):
    dest = _bin_dir / name
    if dest.exists():
        print(f"  [✓] {name} already in bin/")
        return
    print(f"  [→] Downloading {name}...")
    import urllib.request
    urllib.request.urlretrieve(url, str(dest) + ".tmp")
    (dest.parent / (name + ".tmp")).rename(dest)
    print(f"  [✓] {name} ready")

_fetch("yt-dlp.exe",
    "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe")

_ffmpeg = _bin_dir / "ffmpeg.exe"
if not _ffmpeg.exists():
    print("  [→] Downloading ffmpeg (one-time, ~70 MB)...")
    import urllib.request, zipfile, io
    _furl = ("https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
             "ffmpeg-master-latest-win64-gpl.zip")
    _data = urllib.request.urlopen(_furl, timeout=180).read()
    with zipfile.ZipFile(io.BytesIO(_data)) as z:
        for m in z.namelist():
            if m.endswith("/bin/ffmpeg.exe"):
                _ffmpeg.write_bytes(z.read(m)); break
    print("  [✓] ffmpeg ready")

spec_content = f"""
# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

ROOT = Path(r'{ROOT}')

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
    hooksconfig={{}},
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
    runtime_tmpdir=r'%LOCALAPPDATA%\\EditorSuite\\runtime',
    console=False,
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
if not exe_path.exists():
    print("\n  [✗] EditorSuite.exe not found in dist/ — check build errors above.")
    sys.exit(1)

size_mb = exe_path.stat().st_size / 1024 / 1024
print(f"  [✓] EditorSuite.exe  ({size_mb:.0f} MB)")

# ── Step 3b: Sign EditorSuite.exe if cert exists ─────────────────────────────
_pfx = ROOT / "editorsuite.pfx"
_pfx_pass_file = ROOT / "editorsuite.pfx.pass"
if _pfx.exists():
    _pfx_pass = _pfx_pass_file.read_text().strip() if _pfx_pass_file.exists() else ""
    _signtool = None
    import glob as _glob
    # Find signtool in any installed Windows SDK
    _candidates = _glob.glob(
        r"C:\Program Files (x86)\Windows Kitsin\*d\signtool.exe"
    ) + _glob.glob(
        r"C:\Program Files\Windows Kitsin\*d\signtool.exe"
    )
    if _candidates:
        _signtool = sorted(_candidates)[-1]  # newest SDK version

    if _signtool:
        print("  [→] Signing EditorSuite.exe...")
        _sign_args = [
            _signtool, "sign",
            "/f", str(_pfx),
            "/t", "http://timestamp.digicert.com",
            "/fd", "sha256",
            "/d", "EditorSuite",
        ]
        if _pfx_pass:
            _sign_args += ["/p", _pfx_pass]
        _sign_args.append(str(exe_path))
        _sign_result = subprocess.run(_sign_args, capture_output=True, text=True)
        if _sign_result.returncode == 0:
            print("  [✓] EditorSuite.exe signed")
        else:
            print(f"  [!] Signing failed: {_sign_result.stderr.strip()}")
    else:
        print("  [!] signtool.exe not found — install Windows SDK to enable signing")
else:
    print("  [i] No editorsuite.pfx found — skipping signing (run create_cert.py first)")

# ── Step 4: write version.txt into dist/ ─────────────────────────────────────
(DIST / "version.txt").write_text(VERSION, encoding="utf-8")
# Also write one next to the exe source so install.py can read it
(ROOT / "version.txt").write_text(VERSION, encoding="utf-8")
print(f"  [✓] version.txt → {VERSION}")

# ── Step 5: build EditorSuiteInstaller.exe ────────────────────────────────────
print("\n  [→] Building EditorSuiteInstaller.exe...")

installer_spec = f"""
# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
ROOT = Path(r'{ROOT}')
a = Analysis(
    [str(ROOT / 'install.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'version.txt'), '.'),
    ],
    hiddenimports=['winreg', 'win32gui', 'ctypes'],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='EditorSuiteInstaller',
    debug=False, strip=False, upx=True, upx_exclude=[],
    runtime_tmpdir=None,
    console=True,   # installer shows a console window for progress
    icon=str(ROOT / 'gui' / 'static' / 'favicon.ico'),
)
"""

inst_spec_path = ROOT / "EditorSuiteInstaller.spec"
inst_spec_path.write_text(installer_spec, encoding="utf-8")

inst_result = subprocess.run(
    [sys.executable, "-m", "PyInstaller",
     "--distpath", str(DIST),
     "--workpath", str(BUILD),
     "--noconfirm",
     str(inst_spec_path)],
    cwd=str(ROOT)
)

if inst_result.returncode != 0:
    print("  [!] Installer build failed — main app is still fine, installer skipped.")
else:
    inst_exe = DIST / "EditorSuiteInstaller.exe"
    if inst_exe.exists():
        inst_mb = inst_exe.stat().st_size / 1024 / 1024
        print(f"  [✓] EditorSuiteInstaller.exe  ({inst_mb:.0f} MB)")

# ── Step 6: copy install.py into dist/ as fallback (runs with system Python) ──
shutil.copy2(ROOT / "install.py", DIST / "install.py")
print("  [✓] install.py copied to dist/")

# ── Step 7: write README ──────────────────────────────────────────────────────
readme = f"""EditorSuite v{VERSION}
======================

FIRST TIME INSTALL
------------------
1. Run EditorSuiteInstaller.exe (recommended)
   - Installs to Program Files\\EditorSuite
   - Creates Start Menu + Desktop shortcuts
   - Registers in Apps & Features for easy uninstall

   OR if you don't want to install:
   - Just run EditorSuite.exe directly from this folder

UPDATING
--------
1. Extract the new zip into any folder
2. Run EditorSuiteInstaller.exe again
   - Only changed files are replaced
   - Your config.json, collections and settings are NEVER touched

UNINSTALL
---------
  Apps & Features → EditorSuite → Uninstall
  OR: python install.py --uninstall

Your data (config, collections) stays in:
  %APPDATA%\\EditorSuite\
Delete that folder manually for a completely clean removal.
"""

(DIST / "README_INSTALL.txt").write_text(readme, encoding="utf-8")
print("  [✓] README_INSTALL.txt written")

# ── Step 8: refresh Windows icon cache ───────────────────────────────────────
if os.name == "nt":
    subprocess.run(["ie4uinit.exe", "-show"], capture_output=True)
    import ctypes
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"""
  ✓ Build complete — v{VERSION}

  dist/
    EditorSuite.exe            {(DIST/"EditorSuite.exe").stat().st_size//1024//1024} MB  ← the app
    EditorSuiteInstaller.exe   {(DIST/"EditorSuiteInstaller.exe").stat().st_size//1024//1024 if (DIST/"EditorSuiteInstaller.exe").exists() else "??"} MB  ← run this to install
    version.txt                {VERSION}
    README_INSTALL.txt         instructions

  Zip the dist/ folder and share it.
  Users run EditorSuiteInstaller.exe — done.
""")
