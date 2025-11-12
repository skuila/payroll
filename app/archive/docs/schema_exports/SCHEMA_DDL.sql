-- ============================================================================
-- SCHEMA DDL - POSTGRESQL
-- Généré le: 2025-10-17T17:38:29.206949
-- ============================================================================

-- NOTE: Extrait via introspection PostgreSQL
-- Pour un DDL complet, utilisez: pg_dump --schema-only

-- Schéma: core
CREATE SCHEMA IF NOT EXISTS core;

-- Schéma: payroll
CREATE SCHEMA IF NOT EXISTS payroll;

-- Schéma: reference
CREATE SCHEMA IF NOT EXISTS reference;

-- Schéma: public
CREATE SCHEMA IF NOT EXISTS public;

-- Table: core.budget_posts
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: core.employee_job_history
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: core.employees
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: core.job_categories
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: core.job_codes
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: core.pay_codes
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: payroll.budget_posts
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: payroll.import_batches
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: payroll.import_log
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: payroll.import_runs
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: payroll.imported_payroll_master
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: payroll.kpi_snapshot
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: payroll.pay_periods
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: payroll.payroll_transactions
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: payroll.payroll_transactions_2024
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: payroll.payroll_transactions_2025
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: payroll.payroll_transactions_2026
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: payroll.stg_imported_payroll
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: public.alembic_version
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: reference.budget_posts
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: reference.pay_code_mappings
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: reference.pay_codes
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- Table: reference.sign_policies
-- (Structure détaillée dans CHECK_SCHEMA_REPORT.md)

-- ============================================================================
-- FIN DU DDL
-- ============================================================================
