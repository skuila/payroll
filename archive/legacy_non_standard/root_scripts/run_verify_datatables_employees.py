import os
import psycopg


DATE_TEST = os.getenv("PAY_DATE", "2025-08-28")


SQL_DT = f"""
WITH agg AS (
  SELECT 
    e.employee_id,
    COALESCE(e.nom_complet, e.nom_norm || ', ' || COALESCE(e.prenom_norm, '')) AS nom,
    COALESCE(e.matricule_norm, '') AS matricule,
    COALESCE(SUM(t.amount_cents) / 100.0, 0.0) AS salaire_net
  FROM payroll.payroll_transactions t
  JOIN core.employees e ON e.employee_id = t.employee_id
  WHERE t.pay_date = DATE '{DATE_TEST}'
  GROUP BY e.employee_id, e.nom_complet, e.nom_norm, e.prenom_norm, e.matricule_norm
),
stg AS (
  SELECT
    COALESCE(matricule::text, '') AS matricule,
    MAX(categorie_emploi) AS categorie_emploi,
    MAX(titre_emploi) AS titre_emploi
  FROM paie.stg_paie_transactions
  WHERE date_paie = DATE '{DATE_TEST}'
    AND COALESCE(is_valid, TRUE) = TRUE
  GROUP BY COALESCE(matricule::text, '')
)
SELECT
  a.nom,
  a.matricule,
  COALESCE(s.categorie_emploi, '') AS categorie_emploi,
  COALESCE(s.titre_emploi, '') AS titre_emploi,
  a.salaire_net AS total_a_payer
FROM agg a
LEFT JOIN stg s ON s.matricule = a.matricule
ORDER BY a.nom;
"""

SQL_TRUTH = f"""
SELECT 
  COALESCE(e.matricule_norm, '') AS matricule,
  COALESCE(e.nom_complet, e.nom_norm || ', ' || COALESCE(e.prenom_norm, '')) AS nom,
  ROUND(SUM(t.amount_cents) / 100.0, 2) AS salaire_net
FROM payroll.payroll_transactions t
JOIN core.employees e ON e.employee_id = t.employee_id
WHERE t.pay_date = DATE '{DATE_TEST}'
GROUP BY e.matricule_norm, e.nom_complet, e.nom_norm, e.prenom_norm
ORDER BY nom;
"""


def main() -> None:
    dsn = os.getenv("DATABASE_URL") or os.getenv("PAYROLL_DSN")
    if not dsn:
        raise SystemExit("DATABASE_URL/PAYROLL_DSN absent")

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute("SET search_path TO public, core, payroll, paie, reference, agent")

        cur.execute(SQL_DT)
        dt_rows = cur.fetchall()
        # Map matricule -> net (DataTables SQL)
        dt_map = {(r[1] or "").strip(): float(r[4] or 0.0) for r in dt_rows}

        cur.execute(SQL_TRUTH)
        tr_rows = cur.fetchall()
        tr_map = {(r[0] or "").strip(): float(r[2] or 0.0) for r in tr_rows}

        # Comparaison
        keys = sorted(set(dt_map.keys()) | set(tr_map.keys()))
        mismatches = []
        for k in keys:
            v1 = dt_map.get(k)
            v2 = tr_map.get(k)
            if v1 is None or v2 is None or round(v1 - v2, 2) != 0.0:
                mismatches.append((k, v1, v2))

        print(
            {
                "date": DATE_TEST,
                "rows_datatables": len(dt_rows),
                "rows_truth": len(tr_rows),
                "mismatches": len(mismatches),
            }
        )
        if mismatches:
            print("SAMPLE_MISMATCHES:", mismatches[:10])


if __name__ == "__main__":
    main()
