# try_passwords_and_launch.py (archived original)
# Essaie une liste de mots de passe pour la base et lance l'UI au premier succès.
import os
import sys
import time
import traceback
from urllib.parse import urlparse

# ensure project root in path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.config import config_manager

# Ne pas stocker de mots de passe en dur ici. Pour tester une liste de mots de passe,
# fournissez le chemin vers un fichier contenant une liste via la variable d'environnement
# PASSWORD_LIST_FILE (une valeur par ligne), ou définissez la variable PASSWORDS
# comme une chaîne CSV dans l'environnement.
pw_env = os.getenv("PASSWORDS", "")
if pw_env:
    PASSWORDS = [p for p in pw_env.split(",") if p]
else:
    pw_file = os.getenv("PASSWORD_LIST_FILE")
    if pw_file and os.path.exists(pw_file):
        with open(pw_file, "r", encoding="utf-8") as fh:
            PASSWORDS = [l.strip() for l in fh.readlines() if l.strip()]
    else:
        PASSWORDS = []

try:
    base = config_manager.get_dsn()
except Exception:
    base = None

if base is None:
    print("Impossible d’obtenir un DSN de base via config_manager.get_dsn()")
    sys.exit(2)

# parse existing DSN
p = urlparse(base)
user = p.username or os.getenv("PAYROLL_DB_USER", "payroll_app")
host = p.hostname or os.getenv("PAYROLL_DB_HOST", "localhost")
port = p.port or int(os.getenv("PAYROLL_DB_PORT", "5432"))
db = (
    p.path[1:]
    if p.path and p.path.startswith("/")
    else (os.getenv("PAYROLL_DB_NAME") or "payroll_db")
)

import psycopg

for pwd in PASSWORDS:
    dsn = f"postgresql://{user}:{pwd}@{host}:{port}/{db}"
    print("\nTrying password:", pwd)
    print("DSN: (hidden)")
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_user;")
                print("SUCCESS:", cur.fetchone())
            # on success, set env and launch UI
            os.environ["PAYROLL_DB_PASSWORD"] = pwd
            os.environ["PGPASSWORD"] = pwd
            print("Launching GUI...")
            # use subprocess to start GUI and attach to same terminal
            import subprocess

            ui_cmd = [
                sys.executable,
                os.path.join(ROOT, "app", "payroll_app_qt_Version4.py"),
            ]
            # launch and wait a short time to allow UI to start
            proc = subprocess.Popen(ui_cmd, env=os.environ)
            print("GUI process started with PID", proc.pid)
            print("Done — leaving GUI running.")
            sys.exit(0)
    except Exception:
        print("Failed:")
        traceback.print_exc()
        time.sleep(0.5)

print("\nNo password from list succeeded.")
sys.exit(1)
