#!/usr/bin/env python3
"""Export CSV des employés via l'API de connexion standard."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable, Optional

try:  # Compatibilité exécution depuis la racine ou depuis app/
    from app.config.connection_standard import run_select
except ImportError:  # pragma: no cover
    from config.connection_standard import run_select  # type: ignore

DEFAULT_QUERY = """
SELECT
    employee_id,
    matricule_norm,
    nom_complet,
    statut,
    date_embauche,
    date_depart,
    pay_site,
    pay_department
FROM core.employees
ORDER BY nom_complet
"""


def fetch_employees(limit: Optional[int] = None) -> Iterable[tuple]:
    """Récupère la liste des employés depuis la base."""
    query = DEFAULT_QUERY
    if limit:
        query = f"{DEFAULT_QUERY}\nLIMIT %(limit)s"
        return run_select(query, {"limit": limit})
    return run_select(query)


def export_employees(output_path: Path, limit: Optional[int] = None) -> int:
    """Exporte les employés vers un fichier CSV.

    Args:
        output_path: fichier de sortie.
        limit: limite optionnelle du nombre d’enregistrements.
    Returns:
        Nombre de lignes écrites.
    """
    rows = fetch_employees(limit)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "employee_id",
                "matricule_norm",
                "nom_complet",
                "statut",
                "date_embauche",
                "date_depart",
                "pay_site",
                "pay_department",
            ]
        )
        count = 0
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Export CSV des employés")
    parser.add_argument("output", type=Path, help="Chemin du fichier CSV de sortie")
    parser.add_argument("--limit", type=int, help="Nombre maximum de lignes")
    args = parser.parse_args()

    written = export_employees(args.output, args.limit)
    print(f"✅ {written} employés exportés vers {args.output}")


if __name__ == "__main__":
    main()
