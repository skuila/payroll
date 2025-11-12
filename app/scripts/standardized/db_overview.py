#!/usr/bin/env python3
"""Génère un aperçu JSON de la base via l'API standardisée."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

try:
    from app.config.connection_standard import run_select
except ImportError:  # pragma: no cover
    from config.connection_standard import run_select  # type: ignore


def get_table_list() -> List[Dict[str, str]]:
    rows = run_select(
        """
        SELECT schemaname, tablename
        FROM pg_tables
        WHERE schemaname IN ('core', 'payroll', 'reference', 'security')
        ORDER BY schemaname, tablename
        """
    )
    return [{"schema": schema, "table": table} for schema, table in rows]


def get_row_counts() -> Dict[str, int]:
    counts = {}
    for schema, table in [
        ("core", "employees"),
        ("payroll", "payroll_transactions"),
        ("payroll", "pay_periods"),
    ]:
        rows = run_select("SELECT COUNT(*) FROM {}.{}".format(schema, table))
        counts[f"{schema}.{table}"] = rows[0][0] if rows else 0
    return counts


def build_overview() -> Dict[str, object]:
    return {
        "tables": get_table_list(),
        "counts": get_row_counts(),
    }


def write_overview(output: Path) -> Dict[str, object]:
    overview = build_overview()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(overview, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return overview


def main() -> None:
    parser = argparse.ArgumentParser(description="Génère un aperçu JSON de la BD")
    parser.add_argument("output", type=Path, help="Fichier de sortie JSON")
    args = parser.parse_args()

    write_overview(args.output)
    print(f"✅ Aperçu base écrit dans {args.output}")


if __name__ == "__main__":
    main()
