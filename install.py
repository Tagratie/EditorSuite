"""
EditorSuite Installer / Updater
--------------------------------
Run this once to install into Program Files.
Run again with a new build folder to update (keeps config.json and local data).

Usage:
  python install.py            # installs or updates from current folder
  python install.py --uninstall
"""

import os, sys, shutil, subprocess, winreg, ctypes, json
from pathlib import Path

APP_NAME     = "EditorSuite"
INSTALL_DIR  = Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / APP_NAME
DATA_DIR     = Path(os.environ.get("APPDATA", "")) / APP_NAME
SHORTCUT_DST = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs" / f"{APP_NAME}.lnk"
DESKTOP_LINK = Path(os.path.expanduser("~")) / "Desktop" / f"{APP_NAME}.lnk"

# Files/folders that store user data and should NEVER be overwritten on update
PRESERVE = {
    "config.json",
    "data",            # collections, history, etc.
    "browser_profile", # Playwright session cookies
}

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def elevate():
    """Re-launch as admin if not already."""
    if not is_admin():
        print("Requesting administrator privileges…")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable,
            " ".join(f'"{a}"' for a in sys.argv), None, 1
        )
        sys.exit(0)

def get_install_version():
    ver_file = INSTALL_DIR / "version.txt"
    if ver_file.exists():
        return ver_file.read_text().strip()
    return None

def get_source_version():
    ver_file = Path(__file__).parent / "version.txt"
    if ver_file.exists():
        return ver_file.read_text().strip()
    return "unknown"

def install_or_update():
    source = Path(__file__).parent.resolve()
    installed_ver = get_install_version()
    source_ver    = get_source_version()

    if installed_ver:
        print(f"Existing install found: v{installed_ver}")
        print(f"Updating to:            v{source_ver}")
        mode = "update"
    else:
        print(f"Installing EditorSuite v{source_ver} to:")
        print(f"  {INSTALL_DIR}")
        mode = "install"

    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # ── Copy files, skipping preserved user data on update ────────────────────
    copied = 0
    skipped = 0
    for item in source.rglob("*"):
        rel = item.relative_to(source)
        # Never copy the installer itself into Program Files
        if item.name in ("install.py", "install.exe"):
            continue
        # Check if any part of the path is a preserved item
        parts = rel.parts
        if any(p in PRESERVE for p in parts):
            if mode == "update":
                skipped += 1
                continue
        dst = INSTALL_DIR / rel
        if item.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dst)
            copied += 1

    print(f"  Copied {copied} files, skipped {skipped} (user data preserved)")

    # ── Migrate config/data to AppData if they exist in Program Files ─────────
    # (first install: config might be in source folder)
    src_config = source / "config.json"
    dst_config = DATA_DIR / "config.json"
    if src_config.exists() and not dst_config.exists():
        shutil.copy2(src_config, dst_config)
        print(f"  Migrated config.json → {dst_config}")

    # ── Write version file ─────────────────────────────────────────────────────
    (INSTALL_DIR / "version.txt").write_text(source_ver)

    # ── Create shortcuts ───────────────────────────────────────────────────────
    exe = INSTALL_DIR / f"{APP_NAME}.exe"
    if exe.exists():
        _create_shortcut(str(exe), str(SHORTCUT_DST))
        _create_shortcut(str(exe), str(DESKTOP_LINK))
        print(f"  Shortcuts created")

    # ── Register in Add/Remove Programs ──────────────────────────────────────
    try:
        key_path = f"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}"
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            winreg.SetValueEx(key, "DisplayName",     0, winreg.REG_SZ, APP_NAME)
            winreg.SetValueEx(key, "DisplayVersion",  0, winreg.REG_SZ, source_ver)
            winreg.SetValueEx(key, "Publisher",       0, winreg.REG_SZ, "Tagratie")
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(INSTALL_DIR))
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ,
                              f'"{sys.executable}" "{INSTALL_DIR / "install.py"}" --uninstall')
        print("  Registered in Apps & Features")
    except Exception as e:
        print(f"  Registry skip: {e}")

    print(f"\n{'Updated' if mode=='update' else 'Installed'} successfully!")
    if mode == "install":
        print(f"\nLaunch EditorSuite from your Desktop or Start Menu.")

def uninstall():
    print(f"Uninstalling {APP_NAME}…")
    if INSTALL_DIR.exists():
        shutil.rmtree(INSTALL_DIR)
        print(f"  Removed {INSTALL_DIR}")
    for link in (SHORTCUT_DST, DESKTOP_LINK):
        if Path(link).exists():
            Path(link).unlink()
    # Remove registry entry
    try:
        winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE,
            f"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}")
    except Exception:
        pass
    print("Uninstalled. Your data in AppData\\Roaming\\EditorSuite is kept.")
    print("Delete that folder manually if you want a clean removal.")

def _create_shortcut(target: str, link_path: str):
    """Use PowerShell to create a .lnk shortcut."""
    script = (
        f'$ws = New-Object -ComObject WScript.Shell; '
        f'$sc = $ws.CreateShortcut("{link_path}"); '
        f'$sc.TargetPath = "{target}"; '
        f'$sc.WorkingDirectory = "{Path(target).parent}"; '
        f'$sc.Save()'
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True
    )

if __name__ == "__main__":
    if sys.platform != "win32":
        print("This installer is Windows-only.")
        sys.exit(1)

    elevate()

    if "--uninstall" in sys.argv:
        uninstall()
    else:
        install_or_update()

    input("\nPress Enter to close…")
