-- Corriger toutes les permissions manquantes

-- 1. Permissions sur kpi_snapshot
GRANT SELECT, INSERT, UPDATE, DELETE ON payroll.kpi_snapshot TO payroll_app;
GRANT SELECT ON payroll.kpi_snapshot TO payroll_ro;

-- 2. Permissions sur vues matérialisées (REFRESH)
GRANT SELECT ON ALL MATERIALIZED VIEWS IN SCHEMA payroll TO payroll_app, payroll_ro;

-- Permettre à payroll_app de rafraîchir les MVs
ALTER MATERIALIZED VIEW payroll.v_monthly_payroll_summary OWNER TO payroll_app;
ALTER MATERIALIZED VIEW payroll.v_employee_current_salary OWNER TO payroll_app;
ALTER MATERIALIZED VIEW payroll.v_employee_annual_history OWNER TO payroll_app;

-- 3. Permissions futures (pour tables créées après)
ALTER DEFAULT PRIVILEGES IN SCHEMA payroll
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO payroll_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA payroll
    GRANT SELECT ON TABLES TO payroll_ro;

\echo '✅ Toutes les permissions corrigées'

