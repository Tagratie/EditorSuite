"""
create_cert.py — Create a self-signed code signing certificate for EditorSuite
================================================================================
Run this ONCE from your EditorSuite source folder.
Outputs:
  editorsuite.pfx       — the signing cert (keep safe, never commit to git)
  editorsuite.pfx.pass  — the password (keep safe)
  editorsuite.key        — private key (keep safe)
  editorsuite.crt        — public cert

After running this, build_exe.py will automatically sign every build.
"""

import os, sys, subprocess, secrets, string
from pathlib import Path

ROOT = Path(__file__).parent

# ── Colour output ─────────────────────────────────────────────────────────────
try:
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(
        ctypes.windll.kernel32.GetStdHandle(-11), 7)
    G = "\033[92m"; C = "\033[96m"; Y = "\033[93m"; R = "\033[91m"; B = "\033[1m"; X = "\033[0m"
except Exception:
    G = C = Y = R = B = X = ""

def ok(t):   print(f"  {G}✓{X}  {t}")
def info(t): print(f"  {C}→{X}  {t}")
def warn(t): print(f"  {Y}⚠{X}  {t}")
def err(t):  print(f"  {R}✗{X}  {t}")

# ── Find OpenSSL ──────────────────────────────────────────────────────────────
def find_openssl():
    # Try PATH first
    try:
        r = subprocess.run(["openssl", "version"], capture_output=True)
        if r.returncode == 0:
            return "openssl"
    except FileNotFoundError:
        pass
    # Git for Windows bundles OpenSSL
    candidates = [
        r"C:\Program Files\Git\usr\bin\openssl.exe",
        r"C:\Program Files (x86)\Git\usr\bin\openssl.exe",
        r"C:\Git\usr\bin\openssl.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return None

# ── Find signtool ─────────────────────────────────────────────────────────────
def find_signtool():
    import glob
    paths = glob.glob(r"C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe")
    paths += glob.glob(r"C:\Program Files\Windows Kits\10\bin\*\x64\signtool.exe")
    return sorted(paths)[-1] if paths else None

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{B}{C}EditorSuite — Certificate Creator{X}\n")
    print("  Creates a self-signed code signing certificate.")
    print("  Your exe will show 'EditorSuite by Tagratie' in SmartScreen")
    print(f"  instead of 'Unknown publisher'.\n")

    # Check if cert already exists
    pfx = ROOT / "editorsuite.pfx"
    if pfx.exists():
        warn("editorsuite.pfx already exists.")
        overwrite = input(f"  {C}?{X}  Overwrite? (y/n): ").strip().lower()
        if overwrite != "y":
            info("Keeping existing certificate.")
            return

    # Find OpenSSL
    openssl = find_openssl()
    if not openssl:
        err("OpenSSL not found.")
        print("""
  Install one of:
    • Git for Windows: https://git-scm.com/download/win
      (includes OpenSSL at C:\\Program Files\\Git\\usr\\bin\\openssl.exe)
    • Or: winget install ShiningLight.OpenSSL
""")
        sys.exit(1)
    ok(f"OpenSSL found: {openssl}")

    # Gather info
    print()
    name = input(f"  {C}?{X}  Your name / studio name (e.g. Tagratie): ").strip() or "Tagratie"
    country = input(f"  {C}?{X}  2-letter country code (e.g. DE): ").strip().upper() or "DE"
    years = input(f"  {C}?{X}  Cert validity in years (default 10): ").strip() or "10"
    try:
        days = int(years) * 365
    except ValueError:
        days = 3650

    # Generate a strong random password
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    password = "".join(secrets.choice(alphabet) for _ in range(32))

    key_path = ROOT / "editorsuite.key"
    crt_path = ROOT / "editorsuite.crt"
    pfx_path = ROOT / "editorsuite.pfx"
    pass_path = ROOT / "editorsuite.pfx.pass"

    subj = f"/CN=EditorSuite/O={name}/C={country}"

    print(f"\n  {B}Generating RSA-4096 private key…{X}")
    r1 = subprocess.run([
        openssl, "req", "-x509",
        "-newkey", "rsa:4096",
        "-keyout", str(key_path),
        "-out",    str(crt_path),
        "-days",   str(days),
        "-nodes",
        "-subj",   subj,
        "-addext", "extendedKeyUsage=codeSigning",
    ], capture_output=True, text=True)

    if r1.returncode != 0:
        err("Key generation failed:")
        print(r1.stderr)
        sys.exit(1)
    ok("Private key + certificate generated")

    print(f"  {B}Packaging as .pfx…{X}")
    r2 = subprocess.run([
        openssl, "pkcs12", "-export",
        "-out",     str(pfx_path),
        "-inkey",   str(key_path),
        "-in",      str(crt_path),
        "-passout", f"pass:{password}",
    ], capture_output=True, text=True)

    if r2.returncode != 0:
        err("PFX export failed:")
        print(r2.stderr)
        sys.exit(1)
    ok("editorsuite.pfx created")

    # Save password
    pass_path.write_text(password, encoding="utf-8")
    ok(f"Password saved to editorsuite.pfx.pass")

    # Test sign if signtool available
    signtool = find_signtool()
    if signtool:
        ok(f"signtool found: {signtool}")
    else:
        warn("signtool not found — install Windows SDK:")
        print(f"    winget install Microsoft.WindowsSDK.10.0.22621")

    print(f"""
{G}{B}Done!{X}

  Files created:
    editorsuite.pfx       ← signing cert (used by build_exe.py automatically)
    editorsuite.pfx.pass  ← password
    editorsuite.key        ← private key
    editorsuite.crt        ← public cert

  {Y}{B}IMPORTANT — keep these files safe:{X}
    • Never commit them to git  →  add to .gitignore
    • Back them up somewhere secure
    • If someone gets editorsuite.pfx + pass they can sign as you

  {B}Next steps:{X}
    1. Run:  python build_exe.py
       → EditorSuite.exe will be automatically signed
    2. SmartScreen will still show a warning (self-signed = no trust chain)
       but it will say:
       {G}"EditorSuite" — Publisher: {name}{X}
       instead of "Unknown publisher"
    3. Users click "More info" → "Run anyway"  (one time only)

  {B}To get rid of SmartScreen entirely:{X}
    Buy an EV code signing cert (~$300/yr from DigiCert or Sectigo).
    Or sign up for SignPath.io (free for open source projects).
""")

    # Add to .gitignore
    gitignore = ROOT / ".gitignore"
    ignore_lines = [
        "editorsuite.pfx",
        "editorsuite.pfx.pass",
        "editorsuite.key",
        "editorsuite.crt",
    ]
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    additions = [l for l in ignore_lines if l not in existing]
    if additions:
        with gitignore.open("a", encoding="utf-8") as f:
            f.write("\n# Code signing — never commit these\n")
            f.write("\n".join(additions) + "\n")
        ok(f".gitignore updated with cert files")


if __name__ == "__main__":
    main()
    input("\n  Press Enter to close… ")
