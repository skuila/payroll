#!/usr/bin/env python3
"""Génère un inventaire des fichiers violant le standard de connexion DB."""

from __future__ import annotations

import csv
from pathlib import Path

import scripts.forbid_direct_db_connect as checker

ROOT = checker.ROOT

PRODUCTION = {
    "app/config/config_manager.py",
    "app/config/settings.py",
    "app/logic/audit.py",
    "app/services/etl_paie.py",
    "app/services/schema_editor.py",
    "app/agent/knowledge_index.py",
    "app/alembic/env.py",
    "app/launch_debug.py",
    "app/run_validate.py",
    "app/run_verify_datatables_employees.py",
    "app/export_employees_json.py",
    "app/get_db_overview.py",
}

ARCHIVE_PREFIXES = (
    "archive/",
    "app/archive/",
    "app/_cleanup_report/",
    "app/tests/legacy/",
)

UTILITY_PREFIXES = (
    "app/scripts/",
    "app/migration/",
    "app/_cleanup_report/",
)

OUTPUT = ROOT / "reports" / "db_violation_inventory.csv"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

records: dict[str, set[str]] = {}

for path in ROOT.rglob("*.py"):
    if any(part in checker.SKIP_DIRS for part in path.parts):
        continue
    for hit in checker.scan_file(path):
        rel = hit.split(":", 1)[0].replace("\\", "/")
        info = hit.split(":", 1)[1].strip()
        records.setdefault(rel, set()).add(info)

rows = []
for rel_path, issues in sorted(records.items()):
    if rel_path in PRODUCTION:
        category = "production"
        action = "refactoriser"
    elif any(rel_path.startswith(prefix) for prefix in ARCHIVE_PREFIXES):
        category = "archive"
        action = "archiver"
    elif any(rel_path.startswith(prefix) for prefix in UTILITY_PREFIXES):
        category = "utilitaire"
        action = "refactoriser"
    else:
        category = "utilitaire"
        action = "refactoriser"

    rows.append(
        {
            "path": rel_path,
            "category": category,
            "action": action,
            "violations": "; ".join(sorted(issues)),
        }
    )

with OUTPUT.open("w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(
        csvfile, fieldnames=["path", "category", "action", "violations"]
    )
    writer.writeheader()
    writer.writerows(rows)

print(f"✅ Inventaire écrit dans {OUTPUT}")
