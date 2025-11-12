#!/usr/bin/env python3
"""Local analysis runner for a specific file (app/nouveau.xlsx).
Reuses ETLPaie mapping/transform/validation steps but does NOT connect to DB.
Prints KPIs to stdout so you can test the existing code paths.
"""
from pathlib import Path
import sys

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.services.etl_paie import ETLPaie

INPUT = Path("app/nouveau.xlsx")


def run():
    etl = ETLPaie(conn_string="")  # no DB connection for local preview

    # Read
    df = etl.lire_fichier_source(str(INPUT))

    # Apply the same pre-normalization used in local_analysis.py
    col_renames = {}
    if "nom_employe" in df.columns and "nom_prenom" not in df.columns:
        col_renames["nom_employe"] = "nom_prenom"
    if "montant_employe" in df.columns and "montant" not in df.columns:
        col_renames["montant_employe"] = "montant"
    if col_renames:
        df = df.rename(columns=col_renames)
        print("Applied column pre-rename:", col_renames)

    # Map -> rename -> transform -> validate
    mapping = etl.mapper_colonnes(df)
    df = etl.renommer_colonnes(df, mapping)
    df = etl.transformer_dataframe(df)
    df = etl.valider_dataframe(df)

    df_valid = df[df["is_valid"]]

    # KPIs
    total_lines = len(df)
    valid_lines = len(df_valid)
    rejected_lines = total_lines - valid_lines

    total_net_cents = (
        int(df_valid["montant_cents"].sum()) if "montant_cents" in df_valid else 0
    )
    total_net = total_net_cents / 100.0

    nb_employees = 0
    avg_net_per_employee = 0.0
    by_employee = {}
    if "matricule" in df_valid.columns:
        gp = df_valid.groupby("matricule")
        for m, g in gp:
            s = int(g["montant_cents"].sum())
            by_employee[str(m)] = {"count": len(g), "net": s / 100.0}
        nb_employees = len(by_employee)
        avg_net_per_employee = (total_net / nb_employees) if nb_employees else 0.0

    # By pay code
    by_code = {}
    if "code_paie" in df_valid.columns:
        grouped = df_valid.groupby("code_paie")
        for code, g in grouped:
            s = int(g["montant_cents"].sum())
            by_code[code] = {"count": len(g), "total_net": s / 100.0}

    # By period
    by_period = {}
    if "date_paie_parsed" in df_valid.columns:
        gp = df_valid.groupby("date_paie_parsed")
        for pdv, g in gp:
            s = int(g["montant_cents"].sum())
            by_period[str(pdv)] = {"count": len(g), "net": s / 100.0}

    # Output summary
    print("\n=== Local analysis summary for:", INPUT, "===")
    print(f"Total lines: {total_lines}")
    print(f"Valid lines: {valid_lines}")
    print(f"Rejected lines: {rejected_lines}")
    print(f"Total net (file): {total_net:.2f}")
    print(f"Employees distincts (valid): {nb_employees}")
    print(f"Average net per employee: {avg_net_per_employee:.2f}")

    print("\nTop 10 employees by net:")
    for m, info in sorted(by_employee.items(), key=lambda x: x[1]["net"], reverse=True)[
        :10
    ]:
        print(f'  {m}: count={info["count"]}, net={info["net"]:.2f}')

    print("\nBy pay code (top 10 by total net):")
    for code, info in sorted(
        by_code.items(), key=lambda x: x[1]["total_net"], reverse=True
    )[:10]:
        print(f'  {code}: count={info["count"]}, total_net={info["total_net"]:.2f}')

    print("\nBy period:")
    for per, info in sorted(by_period.items()):
        print(f'  {per}: count={info["count"]}, net={info["net"]:.2f}')


if __name__ == "__main__":
    run()
