from app.providers.postgres_provider import PostgresProvider

p = PostgresProvider()
sql = """
WITH agg AS (
   SELECT 
     e.employee_id,
     COALESCE(e.nom_complet, e.nom_norm || ', ' || COALESCE(e.prenom_norm, '')) AS nom,
     COALESCE(e.matricule_norm, '') AS matricule,
     COALESCE(SUM(t.amount_cents) / 100.0, 0.0) AS salaire_net
   FROM payroll.payroll_transactions t
   JOIN core.employees e ON e.employee_id = t.employee_id
   WHERE t.pay_date = DATE '2025-08-28'
   GROUP BY e.employee_id, e.nom_complet, e.nom_norm, e.prenom_norm, e.matricule_norm
),
stg AS (
   SELECT
     COALESCE(matricule::text, '') AS matricule,
     MAX(categorie_emploi) AS categorie_emploi,
     MAX(titre_emploi) AS titre_emploi
   FROM paie.stg_paie_transactions
   WHERE date_paie = DATE '2025-08-28' AND is_valid = TRUE
   GROUP BY COALESCE(matricule::text, '')
)
SELECT COUNT(*) as nb, SUM(agg.salaire_net) as total
FROM agg
LEFT JOIN stg USING (matricule)
"""
rows = p.repo.run_query(sql)
print(rows[0])
