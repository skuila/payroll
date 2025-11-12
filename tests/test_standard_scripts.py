from __future__ import annotations

import csv
from pathlib import Path

from app.scripts.standardized import check_connection, db_overview, export_employees


def test_export_employees_writes_csv(monkeypatch, tmp_path):
    sample_rows = [
        (1, "M001", "Alice", "actif", None, None, "Quebec", "RH"),
        (2, "M002", "Bob", "actif", None, None, "Montreal", "IT"),
    ]

    monkeypatch.setattr(
        export_employees, "fetch_employees", lambda limit=None: sample_rows
    )

    output = tmp_path / "employees.csv"
    written = export_employees.export_employees(output)

    assert written == 2
    with output.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert rows[0][:3] == ["employee_id", "matricule_norm", "nom_complet"]
    assert rows[1][2] == "Alice"
    assert rows[2][2] == "Bob"


def test_db_overview_builds_structure(monkeypatch, tmp_path):
    def fake_run_select(query, params=None):  # noqa: D401
        if "FROM pg_tables" in query:
            return [("core", "employees"), ("payroll", "payroll_transactions")]
        return [(123,)]

    monkeypatch.setattr(db_overview, "run_select", fake_run_select)

    output = tmp_path / "overview.json"
    overview = db_overview.write_overview(output)

    assert overview["tables"][0]["table"] == "employees"
    assert overview["counts"]["core.employees"] == 123
    assert output.exists()


def test_check_connection_run_check(monkeypatch):
    monkeypatch.setattr(
        check_connection, "get_dsn", lambda: "postgresql://user:pass@host/db"
    )
    monkeypatch.setattr(
        check_connection,
        "test_connection",
        lambda: {"success": True, "user": "user", "database": "payroll"},
    )
    monkeypatch.setattr(
        check_connection, "mask_dsn", lambda dsn: "postgresql://user:***@host/db"
    )

    result = check_connection.run_check()

    assert result["success"] is True
    assert result["dsn_masked"] == "postgresql://user:***@host/db"
    assert result["user"] == "user"
    assert result["database"] == "payroll"
