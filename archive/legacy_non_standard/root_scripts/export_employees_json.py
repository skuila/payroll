import os
import json
import psycopg
from pathlib import Path


DSN = os.getenv("DATABASE_URL") or os.getenv("PAYROLL_DSN")
if not DSN:
    raise SystemExit("DATABASE_URL/PAYROLL_DSN absente")

SQL = """
WITH agg AS (
  SELECT e.employee_id,
         COALESCE(e.nom_complet, e.nom_norm || ', ' || COALESCE(e.prenom_norm, '')) AS nom,
         COALESCE(e.matricule_norm, '') AS matricule,
         COALESCE(SUM(t.amount_cents)/100.0, 0.0) AS salaire_net
  FROM payroll.payroll_transactions t
  JOIN core.employees e ON e.employee_id = t.employee_id
  WHERE t.pay_date = DATE '2025-08-28'
  GROUP BY e.employee_id, e.nom_complet, e.nom_norm, e.prenom_norm, e.matricule_norm
),
stg AS (
  SELECT COALESCE(matricule::text, '') AS matricule,
         MAX(categorie_emploi) AS categorie_emploi,
         MAX(titre_emploi) AS titre_emploi
  FROM paie.stg_paie_transactions
  WHERE date_paie = DATE '2025-08-28' AND COALESCE(is_valid, TRUE) = TRUE
  GROUP BY COALESCE(matricule::text, '')
)
SELECT agg.nom,
       agg.matricule,
       COALESCE(stg.categorie_emploi, '') AS categorie_emploi,
       COALESCE(stg.titre_emploi, '') AS titre_emploi,
       agg.salaire_net AS total_a_payer
FROM agg
LEFT JOIN stg ON stg.matricule = agg.matricule
ORDER BY agg.nom;
"""


def main() -> None:
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(SQL)
        rows = cur.fetchall()

    output = [
        {
            "nom": r[0],
            "matricule": r[1],
            "categorie_emploi": r[2],
            "titre_emploi": r[3],
            "total_a_payer": float(r[4] or 0.0),
        }
        for r in rows
    ]

    path = Path("web/tabler/data")
    path.mkdir(parents=True, exist_ok=True)
    file_path = path / "employees_2025-08-28.json"
    file_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"OK: {len(output)} lignes exportées vers {file_path}")


if __name__ == "__main__":
    main()
