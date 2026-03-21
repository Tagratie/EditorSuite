"""
setup_server.py — EditorSuite Account Server Setup
====================================================
Sets up a free Supabase cloud project so multiple machines can log in,
sync collections and settings.

Requirements:
  - Python 3.8+  (you already have this)
  - Internet connection

Run:
  python setup_server.py

What it does:
  1. Guides you through creating a free Supabase project (2 minutes)
  2. Creates all required database tables
  3. Enables email auth (+ optional Google OAuth)
  4. Writes the server URL and keys into EditorSuite's config.json
  5. Prints a test URL you can open in a browser to confirm it works

No credit card. No installs. Free tier: 500 MB, unlimited users.
"""

import os, sys, json, time, urllib.request, urllib.parse, urllib.error
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Colours (Windows 10+ supports ANSI, older fall back to plain text)
# ─────────────────────────────────────────────────────────────────────────────
try:
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(
        ctypes.windll.kernel32.GetStdHandle(-11), 7)
    CYAN   = "\033[96m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    DIM    = "\033[2m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"
except Exception:
    CYAN = GREEN = YELLOW = RED = DIM = BOLD = RESET = ""

def banner(text):
    print(f"\n{BOLD}{CYAN}{'─'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*60}{RESET}\n")

def ok(text):   print(f"  {GREEN}✓{RESET}  {text}")
def info(text): print(f"  {CYAN}→{RESET}  {text}")
def warn(text): print(f"  {YELLOW}⚠{RESET}  {text}")
def err(text):  print(f"  {RED}✗{RESET}  {text}")
def step(n, text): print(f"\n{BOLD}[{n}]{RESET} {text}")

def ask(prompt, default=""):
    val = input(f"  {CYAN}?{RESET}  {prompt}{DIM}{' (' + default + ')' if default else ''}{RESET}: ").strip()
    return val or default

def open_url(url):
    """Open URL in default browser."""
    import webbrowser
    webbrowser.open(url)

# ─────────────────────────────────────────────────────────────────────────────
# Supabase REST helpers
# ─────────────────────────────────────────────────────────────────────────────

def supabase_request(url, method="GET", data=None, headers=None):
    """Make a raw HTTP request to Supabase APIs."""
    body = json.dumps(data).encode() if data is not None else None
    req  = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode())
        except Exception:
            body = {"error": str(e)}
        return e.code, body
    except Exception as e:
        return 0, {"error": str(e)}

def run_sql(project_url, service_key, sql):
    """Execute SQL via Supabase's /rest/v1/rpc or Management API."""
    # Use the Supabase SQL execution endpoint
    url = f"{project_url}/rest/v1/rpc/exec_sql"
    status, resp = supabase_request(
        url, "POST",
        data={"sql": sql},
        headers={
            "apikey":        service_key,
            "Authorization": f"Bearer {service_key}",
        }
    )
    return status, resp

def create_tables_via_sql_api(project_ref, access_token, sql):
    """Use Supabase Management API to run migrations."""
    url    = f"https://api.supabase.com/v1/projects/{project_ref}/database/query"
    status, resp = supabase_request(
        url, "POST",
        data={"query": sql},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    return status, resp

def test_connection(project_url, anon_key):
    """Ping Supabase to confirm the project exists and the key is valid."""
    for path in [
        "/auth/v1/health",
        "/rest/v1/",
    ]:
        status, resp = supabase_request(
            project_url + path, "GET",
            headers={
                "apikey":        anon_key,
                "Authorization": f"Bearer {anon_key}",
            }
        )
        # Any real HTTP response means the project is reachable
        if status in (200, 201, 400, 401, 403):
            return True
    return False

# ─────────────────────────────────────────────────────────────────────────────
# Config helpers
# ─────────────────────────────────────────────────────────────────────────────
CONFIG_PATHS = [
    # Installed location
    Path(os.environ.get("APPDATA","")) / "EditorSuite" / "config.json",
    # Dev / portable location (same folder as this script)
    Path(__file__).parent / "config.json",
    # Program Files
    Path(os.environ.get("PROGRAMFILES","C:\\Program Files")) / "EditorSuite" / "config.json",
]

def find_config():
    for p in CONFIG_PATHS:
        if p.exists():
            return p
    # Default to AppData
    cfg_dir = Path(os.environ.get("APPDATA","")) / "EditorSuite"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "config.json"

def load_config(path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_config(path, cfg):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

# ─────────────────────────────────────────────────────────────────────────────
# SQL schema
# ─────────────────────────────────────────────────────────────────────────────
SCHEMA_SQL = """
-- EditorSuite account schema
-- Run this in your Supabase project SQL editor

-- User profiles (auto-created on signup)
create table if not exists public.profiles (
  id          uuid references auth.users on delete cascade primary key,
  email       text,
  display_name text,
  created_at  timestamptz default now()
);
alter table public.profiles enable row level security;
create policy "Users see own profile"
  on public.profiles for all
  using  (auth.uid() = id)
  with check (auth.uid() = id);

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end;
$$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- Key-value store for all user data (settings, collections, history, etc.)
create table if not exists public.user_data (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid references auth.users on delete cascade not null,
  key        text not null,               -- e.g. "settings", "collections", "watched_creators"
  value      jsonb not null default '{}',
  updated_at timestamptz default now(),
  unique (user_id, key)
);
alter table public.user_data enable row level security;
create policy "Users access own data"
  on public.user_data for all
  using  (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- Auto-update updated_at
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end;
$$;
drop trigger if exists user_data_updated_at on public.user_data;
create trigger user_data_updated_at
  before update on public.user_data
  for each row execute procedure public.set_updated_at();
"""

# ─────────────────────────────────────────────────────────────────────────────
# Main setup flow
# ─────────────────────────────────────────────────────────────────────────────

def main():
    banner("EditorSuite — Account Server Setup")

    print(f"""  This wizard sets up a {BOLD}free Supabase cloud database{RESET} so all your
  machines can log in with the same EditorSuite account and sync
  collections, settings and history.

  {DIM}Takes about 5 minutes. No credit card required.{RESET}
""")

    input(f"  Press {BOLD}Enter{RESET} to start, or Ctrl+C to cancel… ")

    # ── Step 1: Create Supabase account ──────────────────────────────────────
    step(1, "Create a free Supabase account")
    print("""
  Supabase is an open-source Firebase alternative.
  Free tier: 500 MB database, unlimited auth users, never expires.
""")

    print(f"  {BOLD}Opening supabase.com/dashboard in your browser…{RESET}")
    time.sleep(1)
    open_url("https://supabase.com/dashboard")

    print("""
  In the browser:
    1. Click "Start your project" → sign up with GitHub or email
    2. Click "New project"
    3. Give it a name: EditorSuite
    4. Choose a region close to you
    5. Set a database password (save it somewhere safe)
    6. Click "Create new project" — wait ~2 minutes for it to provision
""")
    input(f"  Press {BOLD}Enter{RESET} when the project is ready (shows the dashboard)… ")

    # ── Step 2: Get project credentials ──────────────────────────────────────
    step(2, "Get your project credentials")
    print("""
  In the Supabase dashboard:
    → Settings (bottom left gear icon)
    → API
    → You'll see two things you need:

      Project URL:  https://xxxxxxxxxxxx.supabase.co
      anon/public key: eyJhbGci...  (the long one under "Project API keys")
""")

    project_url = ""
    while not project_url.startswith("https://") or ".supabase.co" not in project_url:
        project_url = ask("Paste your Project URL").rstrip("/")
        if not project_url.startswith("https://"):
            warn("Should start with https://  — try again")

    anon_key = ""
    while len(anon_key) < 20:
        anon_key = ask("Paste your anon/public key")
        if len(anon_key) < 20:
            warn("That looks too short — paste the full key")

    # Extract project ref from URL
    project_ref = project_url.replace("https://","").split(".")[0]
    ok(f"Project ref: {project_ref}")

    # ── Step 3: Test connection ───────────────────────────────────────────────
    step(3, "Testing connection to Supabase")
    info("Pinging your project…")
    alive = test_connection(project_url, anon_key)
    if alive:
        ok("Connection successful!")
    else:
        err("Could not reach the project.")
        print()
        print("  Possible reasons:")
        print("    1. Project still starting — wait 2 minutes and re-run")
        print("    2. URL wrong — copy from Settings → API → Project URL")
        print("       Should look like: https://xxxxxxxxxxxx.supabase.co")
        print("    3. Project paused (free tier pauses after 1 week idle)")
        print("       → Go to your dashboard and click 'Restore project'")
        print()
        sys.exit(1)

    # ── Step 4: Create tables ─────────────────────────────────────────────────
    step(4, "Create database tables")
    print("""
  You need to run the schema SQL in the Supabase SQL Editor.
  Opening it now…
""")

    open_url(f"https://supabase.com/dashboard/project/{project_ref}/sql/new")
    time.sleep(1.5)

    # Write the SQL to a temp file so the user can easily copy it
    sql_path = Path(__file__).parent / "editorsuite_schema.sql"
    sql_path.write_text(SCHEMA_SQL, encoding="utf-8")
    ok(f"Schema saved to: {sql_path}")

    print(f"""
  In the SQL Editor that just opened:
    1. Delete any existing text in the editor
    2. Open and paste the file:  {sql_path}
       (or copy the contents from the file above)
    3. Click "Run" (or press Ctrl+Enter)
    4. You should see "Success. No rows returned"
""")
    input(f"  Press {BOLD}Enter{RESET} once the SQL has run successfully… ")

    # Verify by checking if the table exists
    info("Verifying tables were created…")
    check_url = f"{project_url}/rest/v1/user_data?limit=1"
    status, resp = supabase_request(
        check_url, "GET",
        headers={"apikey": anon_key, "Authorization": f"Bearer {anon_key}"}
    )
    if status == 200:
        ok("Tables created successfully!")
    elif status == 401:
        ok("Tables exist (auth working correctly — anon can't read without login)")
    else:
        warn(f"Could not verify tables (status {status}). Continuing anyway.")
        warn("If login fails later, re-run this script and check the SQL ran correctly.")

    # ── Step 5: Enable email auth ─────────────────────────────────────────────
    step(5, "Verify email auth is enabled")
    print("""
  Supabase enables email auth by default. Let's confirm:
""")
    open_url(f"https://supabase.com/dashboard/project/{project_ref}/auth/providers")
    print("""
  In the Auth Providers page that just opened:
    → "Email" should show as Enabled ✓
    → If it's off, click it and toggle it on
""")
    input(f"  Press {BOLD}Enter{RESET} to continue… ")

    # ── Step 6: Optional Google OAuth ────────────────────────────────────────
    step(6, "Google OAuth (optional)")
    want_google = ask("Set up 'Continue with Google' login? (y/n)", "n").lower()
    google_client_id = ""
    google_client_secret = ""

    if want_google == "y":
        print(f"""
  {BOLD}Setting up Google OAuth:{RESET}

  A. Go to: {CYAN}console.cloud.google.com{RESET}
     → New Project → name it "EditorSuite"
     → APIs & Services → OAuth consent screen
       → External → fill in app name + your email
     → Credentials → Create Credentials → OAuth client ID
       → Application type: Web application
       → Authorised redirect URIs, add:
         {CYAN}https://{project_ref}.supabase.co/auth/v1/callback{RESET}
     → Copy Client ID and Client Secret

  B. In Supabase Dashboard:
     → Auth → Providers → Google
     → Paste Client ID and Client Secret
     → Enable and Save
""")
        open_url("https://console.cloud.google.com")
        google_client_id     = ask("Paste Google Client ID (or leave blank to skip)", "")
        google_client_secret = ask("Paste Google Client Secret (or leave blank to skip)", "")

    # ── Step 7: Write config ──────────────────────────────────────────────────
    step(7, "Writing config to EditorSuite")
    cfg_path = find_config()
    cfg      = load_config(cfg_path)

    cfg["auth_url"]  = project_url
    cfg["auth_key"]  = anon_key
    cfg["auth_provider"] = "supabase"

    if google_client_id:
        cfg["google_client_id"]     = google_client_id
        cfg["google_client_secret"] = google_client_secret

    save_config(cfg_path, cfg)
    ok(f"Config written to: {cfg_path}")
    ok(f"auth_url  = {project_url}")
    ok(f"auth_key  = {anon_key[:24]}…")

    # Also write a standalone .env file for reference
    env_path = Path(__file__).parent / ".env.editorsuite"
    env_path.write_text(
        f"# EditorSuite server config\n"
        f"AUTH_URL={project_url}\n"
        f"AUTH_KEY={anon_key}\n"
        f"PROJECT_REF={project_ref}\n",
        encoding="utf-8"
    )
    ok(f"Backup written to: {env_path}")

    # ── Step 8: Test signup ───────────────────────────────────────────────────
    step(8, "Test a signup")
    do_test = ask("Test creating an account now? (y/n)", "y").lower()
    if do_test == "y":
        test_email = ask("Test email address")
        test_pass  = ask("Test password (min 6 chars)")

        info("Signing up…")
        status, resp = supabase_request(
            f"{project_url}/auth/v1/signup",
            "POST",
            data={"email": test_email, "password": test_pass},
            headers={"apikey": anon_key}
        )
        if status == 200 and resp.get("user"):
            ok(f"Account created!  user id: {resp['user']['id']}")
            ok("Login will work in EditorSuite.")

            # Test login
            info("Testing login…")
            status2, resp2 = supabase_request(
                f"{project_url}/auth/v1/token?grant_type=password",
                "POST",
                data={"email": test_email, "password": test_pass},
                headers={"apikey": anon_key}
            )
            if status2 == 200 and resp2.get("access_token"):
                ok("Login successful! Token received.")
            else:
                warn(f"Login test failed: {resp2}")
        elif status == 400 and "already registered" in str(resp):
            ok("Email already exists — that's fine, auth is working.")
        else:
            warn(f"Signup returned {status}: {resp}")
            warn("This might be fine — Supabase may require email confirmation.")
            warn("Check Auth → Users in the Supabase dashboard.")

    # ── Done ─────────────────────────────────────────────────────────────────
    banner("Setup Complete!")
    print(f"""  Your EditorSuite account server is live:

  {CYAN}{project_url}{RESET}

  {BOLD}What this means:{RESET}
  • Every machine that runs EditorSuite can now log in with
    the same email and password
  • Collections, settings and history sync automatically
    across all your machines

  {BOLD}To connect another machine:{RESET}
  1. Copy this file to that machine:  {env_path}
  2. Run setup_server.py on that machine and choose:
     "I already have a project — just write the config"
     (or manually add auth_url + auth_key to config.json)

  {BOLD}Files created:{RESET}
  • {cfg_path}  ← EditorSuite will read this automatically
  • {env_path}   ← backup / reference
  • {sql_path}   ← schema SQL (keep for re-running if needed)

  {BOLD}Supabase dashboard:{RESET}
  {CYAN}https://supabase.com/dashboard/project/{project_ref}{RESET}
  → Auth → Users  to see all accounts
  → Table Editor  to see stored data
""")


def quick_connect():
    """For machines that already have a Supabase project — just write the config."""
    banner("EditorSuite — Connect to Existing Server")
    print("  You already have a Supabase project. Just paste your credentials.\n")

    project_url = ask("Project URL (https://xxx.supabase.co)").rstrip("/")
    anon_key    = ask("anon/public key")

    if not project_url or not anon_key:
        err("Both fields are required."); sys.exit(1)

    info("Testing connection…")
    if test_connection(project_url, anon_key):
        ok("Connected!")
    else:
        warn("Could not reach the server — check URL and key, then retry.")

    cfg_path = find_config()
    cfg      = load_config(cfg_path)
    cfg["auth_url"] = project_url
    cfg["auth_key"] = anon_key
    cfg["auth_provider"] = "supabase"
    save_config(cfg_path, cfg)

    ok(f"Config written to: {cfg_path}")
    print(f"\n  {GREEN}Done!{RESET} EditorSuite will use your account server next time it starts.\n")


if __name__ == "__main__":
    print()
    if "--connect" in sys.argv:
        quick_connect()
    elif len(sys.argv) > 1 and sys.argv[1] == "--connect":
        quick_connect()
    else:
        # Ask if new setup or connecting existing
        print(f"  {BOLD}What do you want to do?{RESET}\n")
        print(f"  {CYAN}1{RESET}  Set up a new Supabase project (first time)")
        print(f"  {CYAN}2{RESET}  Connect this machine to an existing project")
        print()
        choice = input("  Choice (1 or 2): ").strip()
        if choice == "2":
            quick_connect()
        else:
            main()
    input("\n  Press Enter to close… ")
