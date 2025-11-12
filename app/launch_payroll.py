#!/usr/bin/env python3
"""
Script de lancement unifié pour l'application Payroll
Configure automatiquement les variables d'environnement et lance l'application
"""

import os
import sys
import subprocess
import psycopg
from config import settings

# Bootstrap environment early
settings.bootstrap_env()
from pathlib import Path


def main():
    """Fonction principale de lancement"""

    print("LANCEMENT UNIFIE DE L'APPLICATION PAYROLL")
    print("=" * 60)

    # Définir les variables d'environnement unifiées en lisant les valeurs
    # depuis l'environnement (ou .env local) — NE PAS stocker de secrets dans le code.
    env = os.environ.copy()

    env_vars = {
        "PAYROLL_DB_USER": os.getenv("PAYROLL_DB_USER", "payroll_unified"),
        "PAYROLL_DB_PASSWORD": os.getenv("PAYROLL_DB_PASSWORD", ""),
        "PAYROLL_DB_HOST": os.getenv("PAYROLL_DB_HOST", "localhost"),
        "PAYROLL_DB_PORT": os.getenv("PAYROLL_DB_PORT", "5432"),
        "PAYROLL_DB_NAME": os.getenv("PAYROLL_DB_NAME", "payroll_db"),
        "PAYROLL_DB_SUPERUSER": os.getenv("PAYROLL_DB_SUPERUSER", "postgres"),
        "PAYROLL_DB_SUPERUSER_PASSWORD": os.getenv("PAYROLL_DB_SUPERUSER_PASSWORD", ""),
        "APP_ENV": os.getenv("APP_ENV", "development"),
        "PAYROLL_FORCE_OFFLINE": os.getenv("PAYROLL_FORCE_OFFLINE", "0"),
        "USE_COPY": os.getenv("USE_COPY", "0"),
    }

    # Définir les variables en mémoire et afficher un état non confidentiel
    for key, value in env_vars.items():
        env[key] = value
        if "PASSWORD" in key.upper():
            print(f"[OK] {key} = {'***REDACTED***' if value else '(not set)'}")
        else:
            print(f"[OK] {key} = {value}")

    print("Variables d'environnement configurees")
    print("Utilisation du role unifie: payroll_unified")
    print("Connexion PostgreSQL securisee")

    # Chemin vers l'application principale
    app_dir = Path(__file__).parent
    app_file = app_dir / "payroll_app_qt_Version4.py"

    if not app_file.exists():
        print(f"Erreur: Fichier application introuvable: {app_file}")
        sys.exit(1)

    print(f"Lancement de l'application: {app_file}")
    print("=" * 60)

    # --- Construire la DSN à partir des variables d'environnement ---
    def build_dsn(e: dict) -> str:
        if e.get("PAYROLL_DSN"):
            return e.get("PAYROLL_DSN")
        user = e.get("PAYROLL_DB_USER", "payroll_unified")
        pwd = e.get("PAYROLL_DB_PASSWORD", "")
        host = e.get("PAYROLL_DB_HOST", "localhost")
        port = e.get("PAYROLL_DB_PORT", "5432")
        db = e.get("PAYROLL_DB_NAME", "payroll_db")
        return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"

    dsn = build_dsn(env)

    # Vérifier la connexion à la DB avant d'ouvrir l'UI.
    # Vérifier la configuration runtime via settings (priorité CLI > env)
    runtime = settings.get_runtime_config()
    dsn_runtime = runtime.get("dsn")
    if not dsn_runtime:
        print(
            "ERROR: Aucun DSN valide fourni (CLI --dsn ou PAYROLL_DSN manquant ou sans mot de passe)."
        )
        sys.exit(1)

    # Test de connexion unique et rapide (échec = arrêt immédiat)
    try:
        with psycopg.connect(dsn_runtime, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), current_user;")
                # Intentionally do not print a generic SUCCESS here; provider logs authoritative SUCCESS.
                _ = cur.fetchone()
    except Exception as e:
        print(f"ERROR: échec de connexion PostgreSQL: {e}")
        sys.exit(1)

    try:
        # Lancer l'application avec les variables d'environnement
        result = subprocess.run(
            [sys.executable, str(app_file)], env=env, cwd=str(app_dir)
        )
        sys.exit(result.returncode)

    except KeyboardInterrupt:
        print("Application arretee par l'utilisateur")
        sys.exit(0)
    except Exception as e:
        print(f"Erreur lors du lancement: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
