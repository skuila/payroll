
CREATE OR REPLACE VIEW payroll.v_employee_period_summary AS

SELECT
  pp.pay_date::date AS pay_date,
  e.employee_id,
  COALESCE(e.nom_complet, e.nom_norm || ', ' || COALESCE(e.prenom_norm,'')) AS nom,
  e.matricule_norm AS matricule,
  e.statut,
  COALESCE(e.poste_budgetaire, '') AS categorie_emploi,
  COALESCE(e.titre, '') AS titre_emploi,
  COALESCE(SUM(COALESCE(t.amount_employee_norm_cents, t.amount_cents, 0)),0) / 100.0 AS salaire_net
FROM payroll.pay_periods pp
JOIN payroll.payroll_transactions t ON t.period_id = pp.period_id
JOIN core.employees e ON e.employee_id = t.employee_id
GROUP BY pp.pay_date, e.employee_id, e.nom_complet, e.nom_norm, e.prenom_norm, e.matricule_norm, e.statut, e.poste_budgetaire, e.titre
ORDER BY pp.pay_date DESC, e.nom_complet NULLS LAST;
