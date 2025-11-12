-- Script SQL pour accorder les droits nécessaires
-- À exécuter avec un superuser (postgres)

-- 1. Accorder SELECT sur la table source
GRANT SELECT ON payroll.imported_payroll_master TO payroll_app;
GRANT SELECT ON payroll.imported_payroll_master TO payroll_ro;

-- 2. Accorder SELECT sur toutes les vues SQL
GRANT SELECT ON payroll.v_payroll_detail TO payroll_app;
GRANT SELECT ON payroll.v_payroll_detail TO payroll_ro;

GRANT SELECT ON payroll.v_payroll_par_periode TO payroll_app;
GRANT SELECT ON payroll.v_payroll_par_periode TO payroll_ro;

GRANT SELECT ON payroll.v_payroll_par_budget TO payroll_app;
GRANT SELECT ON payroll.v_payroll_par_budget TO payroll_ro;

GRANT SELECT ON payroll.v_payroll_par_code TO payroll_app;
GRANT SELECT ON payroll.v_payroll_par_code TO payroll_ro;

GRANT SELECT ON payroll.v_payroll_kpi TO payroll_app;
GRANT SELECT ON payroll.v_payroll_kpi TO payroll_ro;

-- Vérification
SELECT 
    grantee, 
    table_schema, 
    table_name, 
    privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'payroll'
  AND table_name IN ('imported_payroll_master', 'v_payroll_detail', 'v_payroll_par_periode', 
                     'v_payroll_par_budget', 'v_payroll_par_code', 'v_payroll_kpi')
  AND grantee IN ('payroll_app', 'payroll_ro')
ORDER BY table_name, grantee;









