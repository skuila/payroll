-- Création d'une vue accessible pour les catégories d'emploi par période
CREATE OR REPLACE VIEW payroll.v_emp_categories AS
SELECT
  t.pay_date::date AS date_paie,
  COALESCE(NULLIF(p.categorie_emploi, ''), 'Non classé') AS categorie_emploi,
  COUNT(DISTINCT t.employee_id) AS nb_employes
FROM payroll.payroll_transactions t
JOIN paie.v_employe_profil p ON p.employee_id = t.employee_id
GROUP BY t.pay_date::date, COALESCE(NULLIF(p.categorie_emploi, ''), 'Non classé');

ALTER VIEW payroll.v_emp_categories OWNER TO payroll_app;

GRANT USAGE ON SCHEMA paie TO payroll_app;
GRANT SELECT ON ALL TABLES IN SCHEMA paie TO payroll_app;
GRANT SELECT ON payroll.v_emp_categories TO payroll_app;

