import os
import sys
import subprocess

# Ensure project root on path (project root is the parent of the 'app' folder)
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import the DSN from the migration fallback file (parse the literal to avoid importing)
FALLBACK_DSN = None

# Try importing the migration module (ensure 'app' directory is on sys.path)
app_dir = os.path.join(PROJECT_ROOT, "app")
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)
try:
    import migration.backup_database as mb

    FALLBACK_DSN = getattr(mb, "DSN", None)
except Exception:
    # Fallback: parse file content without importing
    fallback_path = os.path.join(PROJECT_ROOT, "app", "migration", "backup_database.py")
    if os.path.exists(fallback_path):
        try:
            with open(fallback_path, "r", encoding="utf-8") as fh:
                text = fh.read()
            import re

            m2 = re.search(r"DSN\s*=\s*['\"](postgresql://[^'\"]+)['\"]", text)
            if m2:
                FALLBACK_DSN = m2.group(1)
        except Exception:
            FALLBACK_DSN = None

# Prefer existing env var PAYROLL_DSN, otherwise use fallback from file
env = os.environ.copy()
if env.get("PAYROLL_DSN"):
    print("[INFO] PAYROLL_DSN already set in environment; using it for the test")
else:
    if FALLBACK_DSN:
        env["PAYROLL_DSN"] = FALLBACK_DSN
        print(
            "[INFO] PAYROLL_DSN set from migration backup fallback for this test (not printed)"
        )
    else:
        print(
            "[ERROR] No PAYROLL_DSN set and no fallback DSN found in migration.backup_database"
        )
        sys.exit(2)

# Run the existing smoke test script using the venv Python (try several common locations)

possible = [
    os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe"),
    os.path.join(PROJECT_ROOT, ".venv", "bin", "python"),
    os.path.join(PROJECT_ROOT, "venv", "Scripts", "python.exe"),
    os.path.join(PROJECT_ROOT, "venv", "bin", "python"),
    sys.executable,  # fallback to current interpreter
]
venv_py = None
for p in possible:
    if p and os.path.exists(p):
        venv_py = p
        break

script = os.path.join(PROJECT_ROOT, "app", "scripts", "test_schema_editor.py")

if not venv_py:
    print("[ERROR] Aucun interpréteur Python virtuel trouvé; abandon")
    sys.exit(3)

print("[INFO] Running smoke test (will attempt real DB connection)")
rc = subprocess.call([venv_py, script], env=env)
print("[INFO] Test process exited with code", rc)
sys.exit(rc)
