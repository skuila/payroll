#!/usr/bin/env python3
"""Imprime le Top 10 des employés par salaire net total en utilisant ETLPaie (sans DB)."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.services.etl_paie import ETLPaie

INPUT = Path("app/nouveau.xlsx")


def run():
    etl = ETLPaie(conn_string="")
    df = etl.lire_fichier_source(str(INPUT))

    # Pre-rename
    col_renames = {}
    if "nom_employe" in df.columns and "nom_prenom" not in df.columns:
        col_renames["nom_employe"] = "nom_prenom"
    if "montant_employe" in df.columns and "montant" not in df.columns:
        col_renames["montant_employe"] = "montant"
    if col_renames:
        df = df.rename(columns=col_renames)

    mapping = etl.mapper_colonnes(df)
    df = etl.renommer_colonnes(df, mapping)
    df = etl.transformer_dataframe(df)
    df = etl.valider_dataframe(df)

    df_valid = df[df["is_valid"]]

    # Group by matricule and include nom_prenom (take first non-null)
    grouped = df_valid.groupby("matricule")
    rows = []
    for matricule, g in grouped:
        total_net = int(g["montant_cents"].sum()) / 100.0
        count = len(g)
        # pick first non-null nom_prenom
        nom = None
        if "nom_prenom" in g.columns:
            nonulls = g["nom_prenom"].dropna().unique()
            if len(nonulls) > 0:
                nom = nonulls[0]
        rows.append((matricule, nom or "", count, total_net))

    # sort by total_net desc
    rows_sorted = sorted(rows, key=lambda x: x[3], reverse=True)

    print("Top 10 employés par salaire net total:")
    print("matricule | nom_prenom | count | net")
    for matricule, nom, count, net in rows_sorted[:10]:
        print(f"{matricule} | {nom} | {count} | {net:.2f}")

    # Optionnel: write CSV
    out = Path("app/_cleanup_report/top10_employees.csv")
    with out.open("w", encoding="utf-8") as f:
        f.write("matricule,nom_prenom,count,net\n")
        for matricule, nom, count, net in rows_sorted[:100]:
            # escape commas in name
            safe_nom = nom.replace(",", ";")
            f.write(f"{matricule},{safe_nom},{count},{net:.2f}\n")
    print("\nCSV written to", out)


if __name__ == "__main__":
    run()
