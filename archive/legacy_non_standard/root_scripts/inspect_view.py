from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from typing import List
from urllib.parse import urlparse

from sqlalchemy import create_engine, text
from sqlalchemy import exc as sa_exc


def load_settings() -> SimpleNamespace:
    """Charge la configuration PostgreSQL depuis l'environnement."""
    dsn = os.getenv("PAYROLL_DSN") or os.getenv("DATABASE_URL")
    if dsn:
        parsed = urlparse(dsn)
        return SimpleNamespace(
            pguser=parsed.username or "postgres",
            pgpassword=parsed.password or "",
            pghost=parsed.hostname or "localhost",
            pgport=parsed.port or 5432,
            pgdatabase=(parsed.path.lstrip("/") or "postgres"),
        )

    return SimpleNamespace(
        pguser=os.getenv("PAYROLL_DB_USER", "postgres"),
        pgpassword=(os.getenv("PAYROLL_DB_PASSWORD") or os.getenv("PGPASSWORD") or ""),
        pghost=os.getenv("PAYROLL_DB_HOST", "localhost"),
        pgport=int(os.getenv("PAYROLL_DB_PORT", "5432")),
        pgdatabase=os.getenv("PAYROLL_DB_NAME", "payroll_db"),
    )


settings = load_settings()


def ensure_settings() -> None:
    required_keys: List[str] = [
        "pguser",
        "pgpassword",
        "pghost",
        "pgport",
        "pgdatabase",
    ]
    missing: List[str] = []
    for key in required_keys:
        if not hasattr(settings, key):
            missing.append(key)
            continue
        value = getattr(settings, key)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            missing.append(key)
        if key == "pgport":
            try:
                # Port doit être un entier > 0
                if int(value) <= 0:
                    missing.append(key)
            except Exception:
                missing.append(key)
    if missing:
        raise RuntimeError(
            "Paramètres manquants/invalides dans la configuration PostgreSQL (variables d'environnement): "
            + ", ".join(sorted(set(missing)))
        )


def build_urls() -> tuple[str, str]:
    # URL complète et version masquée pour logs (mot de passe caché)
    url = (
        f"postgresql+pg8000://{settings.pguser}:{settings.pgpassword}"
        f"@{settings.pghost}:{settings.pgport}/{settings.pgdatabase}"
    )
    masked = (
        f"postgresql+pg8000://{settings.pguser}:********"
        f"@{settings.pghost}:{settings.pgport}/{settings.pgdatabase}"
    )
    return url, masked


def main() -> int:
    try:
        ensure_settings()
        url, masked = build_urls()
    except Exception as e:
        print(f"Erreur de configuration: {e}", file=sys.stderr)
        return 1

    # Créer l'engine SQLAlchemy (v2 style)
    try:
        engine = create_engine(url, future=True, echo=False)
    except Exception as e:
        print(f"Erreur création engine SQLAlchemy: {e}", file=sys.stderr)
        return 1

    # Connexion + test de connectivité + inspection de la vue
    try:
        with engine.connect() as conn:
            # Test de connectivité minimal
            conn.exec_driver_sql("SELECT 1")

            # Exécuter la requête d'inspection
            result = conn.execute(text("SELECT * FROM paie.v_employes LIMIT 1"))

            # Sortie demandée
            print("Colonnes:", list(result.keys()))
            row = result.fetchone()
            if row:
                print(dict(row._mapping))
            else:
                print({})

    except sa_exc.OperationalError as e:
        # Erreurs de connexion/auth/host/port
        print(
            (
                "Erreur opérationnelle (connexion/auth) vers PostgreSQL — URL: "
                f"{masked}. Détail: {e}"
            ),
            file=sys.stderr,
        )
        return 2
    except sa_exc.ProgrammingError as e:
        # Erreurs SQL: schéma/table/colonne manquants, droits, etc.
        print(
            (
                "Erreur SQL (programmation) lors de l'accès à paie.v_employes — "
                f"URL: {masked}. Détail: {e}"
            ),
            file=sys.stderr,
        )
        return 3
    except Exception as e:
        print(f"Erreur inattendue: {e}", file=sys.stderr)
        return 4

    return 0


if __name__ == "__main__":
    sys.exit(main())
