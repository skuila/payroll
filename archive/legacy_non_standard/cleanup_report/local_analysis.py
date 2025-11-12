#!/usr/bin/env python3
"""Run a local analysis of the provided Excel file using the project's ETL logic
but WITHOUT connecting to the database. Produces a human-readable report with
KPIs computed from the file only.
"""
from pathlib import Path
import sys
from datetime import date

# Ensure project root is on sys.path so `import app...` works when running this
# script directly.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.services.etl_paie import ETLPaie

INPUT = Path("app/scripts/Classeur1.xlsx")
OUT = Path("app/_cleanup_report/local_analysis.txt")


def main():
    etl = ETLPaie(conn_string="")  # no DB connection for local preview

    # Read and transform
    df = etl.lire_fichier_source(str(INPUT))

    # Quick pre-normalization for common header variants found in test files
    col_renames = {}
    if "nom_employe" in df.columns and "nom_prenom" not in df.columns:
        col_renames["nom_employe"] = "nom_prenom"
    if "montant_employe" in df.columns and "montant" not in df.columns:
        col_renames["montant_employe"] = "montant"
    if col_renames:
        df = df.rename(columns=col_renames)
        print("Applied column pre-rename:", col_renames)
    mapping = etl.mapper_colonnes(df)
    df = etl.renommer_colonnes(df, mapping)
    df = etl.transformer_dataframe(df)
    df = etl.valider_dataframe(df)

    # Filter valid lines
    df_valid = df[df["is_valid"]]

    # KPIs
    total_lines = len(df)
    valid_lines = len(df_valid)
    rejected_lines = total_lines - valid_lines

    total_net_cents = (
        int(df_valid["montant_cents"].sum()) if "montant_cents" in df_valid else 0
    )
    total_net = total_net_cents / 100.0

    # Categories
    categories = {}
    if "categorie_emploi" in df_valid.columns:
        for c, g in df_valid.groupby("categorie_emploi"):
            categories[c] = len(g)

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

    # By employee
    by_employee = {}
    if "matricule" in df_valid.columns:
        gp = df_valid.groupby("matricule")
        for m, g in gp:
            s = int(g["montant_cents"].sum())
            # capture a representative name when available
            nom = ""
            if "nom_prenom" in g.columns:
                nonulls = g["nom_prenom"].dropna().unique()
                if len(nonulls) > 0:
                    nom = nonulls[0]

            by_employee[str(m)] = {"count": len(g), "net": s / 100.0, "nom_prenom": nom}

    # Basic metrics
    nb_employees = len(by_employee)
    avg_net_per_employee = (total_net / nb_employees) if nb_employees else 0

    # Write report
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("Local analysis report\n")
        f.write("Input file: " + str(INPUT) + "\n")
        f.write("\n")
        f.write(f"Total lines: {total_lines}\n")
        f.write(f"Valid lines: {valid_lines}\n")
        f.write(f"Rejected lines: {rejected_lines}\n")
        f.write("\n")
        f.write(f"Total net (file): {total_net:.2f} \n")
        f.write(f"Employees distincts (valid): {nb_employees}\n")
        f.write(f"Average net per employee: {avg_net_per_employee:.2f}\n")
        f.write("\n")
        f.write("Categories (counts):\n")
        for k, v in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            f.write(f"  {k}: {v}\n")
        f.write("\n")
        f.write("By pay code:\n")
        for code, info in sorted(
            by_code.items(), key=lambda x: x[1]["total_net"], reverse=True
        ):
            f.write(
                f'  {code}: count={info["count"]}, total_net={info["total_net"]:.2f}\n'
            )
        f.write("\n")
        f.write("By period:\n")
        for per, info in sorted(by_period.items()):
            f.write(f'  {per}: count={info["count"]}, net={info["net"]:.2f}\n')
        f.write("\n")
        f.write("Top 10 employees by net:\n")
        # include name in report and write a CSV for quick inspection
        top_list = sorted(by_employee.items(), key=lambda x: x[1]["net"], reverse=True)
        for m, info in top_list[:10]:
            f.write(
                f'  {m} | {info.get("nom_prenom", "")} | count={info["count"]}, net={info["net"]:.2f}\n'
            )

        csv_out = Path(__file__).parent / "top10_employees.csv"
        with csv_out.open("w", encoding="utf-8") as csvf:
            csvf.write("matricule,nom_prenom,count,net\n")
            for m, info in top_list[:100]:
                safe_nom = str(info.get("nom_prenom", "")).replace(",", ";")
                csvf.write(f'{m},{safe_nom},{info["count"]},{info["net"]:.2f}\n')

        f.write(f"CSV top employees written to: {csv_out}\n")

    print("Local analysis written to", OUT)


if __name__ == "__main__":
    main()
