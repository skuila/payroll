#!/usr/bin/env python3
"""Compute KPIs for app/nouveau.xlsx and write a JSON summary for acceptance tests.
Produces: app/_cleanup_report/kpi_summary.json
"""
from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.services.etl_paie import ETLPaie

INPUT = Path("app/nouveau.xlsx")
OUT = Path("app/_cleanup_report/kpi_summary.json")


def compute():
    etl = ETLPaie(conn_string="")
    df = etl.lire_fichier_source(str(INPUT))

    # pre-rename heuristics
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

    total_lines = len(df)
    valid_lines = len(df_valid)
    rejected_lines = total_lines - valid_lines

    total_net_cents = (
        int(df_valid["montant_cents"].sum()) if "montant_cents" in df_valid else 0
    )
    total_net = total_net_cents / 100.0

    # employees
    by_employee = {}
    if "matricule" in df_valid.columns:
        gp = df_valid.groupby("matricule")
        for m, g in gp:
            s = int(g["montant_cents"].sum())
            nom = ""
            if "nom_prenom" in g.columns:
                nonulls = g["nom_prenom"].dropna().unique()
                if len(nonulls) > 0:
                    nom = nonulls[0]
            by_employee[str(m)] = {"count": len(g), "net": s / 100.0, "nom_prenom": nom}

    nb_employees = len(by_employee)
    avg_net_per_employee = (total_net / nb_employees) if nb_employees else 0.0

    # by code
    by_code = {}
    if "code_paie" in df_valid.columns:
        grouped = df_valid.groupby("code_paie")
        for code, g in grouped:
            s = int(g["montant_cents"].sum())
            by_code[str(code)] = {"count": len(g), "total_net": s / 100.0}

    # by period
    by_period = {}
    if "date_paie_parsed" in df_valid.columns:
        gp = df_valid.groupby("date_paie_parsed")
        for pdv, g in gp:
            s = int(g["montant_cents"].sum())
            by_period[str(pdv)] = {"count": len(g), "net": s / 100.0}

    # top employees
    top_emps = sorted(by_employee.items(), key=lambda x: x[1]["net"], reverse=True)[:20]
    top_emps_out = []
    for m, info in top_emps:
        top_emps_out.append(
            {
                "matricule": m,
                "nom_prenom": info.get("nom_prenom", ""),
                "count": info["count"],
                "net": info["net"],
            }
        )

    summary = {
        "input": str(INPUT),
        "total_lines": total_lines,
        "valid_lines": valid_lines,
        "rejected_lines": rejected_lines,
        "total_net": total_net,
        "total_net_cents": total_net_cents,
        "nb_employees": nb_employees,
        "avg_net_per_employee": round(avg_net_per_employee, 2),
        "by_code": by_code,
        "by_period": by_period,
        "top_employees": top_emps_out,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote KPI summary to: {OUT}")
    return summary


if __name__ == "__main__":
    compute()
