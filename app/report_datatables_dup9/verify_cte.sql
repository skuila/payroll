-- Vérifier total net et nb employés pour la date
WITH agg AS (
  SELECT e.employee_id,
         COALESCE(e.nom_complet, e.nom_norm || ', ' || COALESCE(e.prenom_norm,'')) AS nom,
         COALESCE(e.matricule_norm,'') AS matricule,
         SUM(t.amount_cents)/100.0 AS salaire_net
  FROM payroll.payroll_transactions t
  JOIN core.employees e ON e.employee_id = t.employee_id
  WHERE t.pay_date = DATE :d
  GROUP BY e.employee_id, e.nom_complet, e.nom_norm, e.prenom_norm, e.matricule_norm
)
SELECT COUNT(*) nb_employes, SUM(salaire_net) total FROM agg;

-- Détails 3 employés
WITH agg AS (
  SELECT COALESCE(e.matricule_norm,'') AS matricule,
         COALESCE(e.nom_complet, e.nom_norm || ', ' || COALESCE(e.prenom_norm,'')) AS nom,
         SUM(t.amount_cents)/100.0 AS salaire_net
  FROM payroll.payroll_transactions t
  JOIN core.employees e ON e.employee_id = t.employee_id
  WHERE t.pay_date = DATE :d
  GROUP BY e.matricule_norm, e.nom_complet, e.nom_norm, e.prenom_norm
)
SELECT matricule, nom, salaire_net FROM agg ORDER BY nom LIMIT 3;

-- Détecter duplication potentielle côté staging
SELECT matricule, COUNT(*) AS nb_lignes_stg
FROM paie.stg_paie_transactions
WHERE date_paie = DATE :d AND is_valid = TRUE
GROUP BY matricule
ORDER BY nb_lignes_stg DESC
LIMIT 10;

-- Vérifier base
SELECT current_database(), current_user, inet_server_addr(), inet_server_port();


