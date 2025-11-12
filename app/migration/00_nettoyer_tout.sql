-- ============================================================================
-- NETTOYAGE COMPLET - Supprimer TOUTES les anciennes structures
-- Repartir à zéro pour nouvelle migration
-- ============================================================================

SET client_min_messages TO NOTICE;

\echo ''
\echo '============================================================================'
\echo 'NETTOYAGE COMPLET - SUPPRESSION ANCIENNES STRUCTURES'
\echo '============================================================================'
\echo ''

-- ============================================================================
-- 1. SUPPRIMER TOUTES LES TABLES ANCIENNES
-- ============================================================================

\echo '1. Suppression tables existantes...'
\echo ''

-- Supprimer tables payroll (ordre inverse FK)
DROP TABLE IF EXISTS payroll.payroll_transactions CASCADE;
DROP TABLE IF EXISTS payroll.payroll_transactions_2024 CASCADE;
DROP TABLE IF EXISTS payroll.payroll_transactions_2025 CASCADE;
DROP TABLE IF EXISTS payroll.payroll_transactions_2026 CASCADE;
DROP TABLE IF EXISTS payroll.payroll_transactions_past CASCADE;
DROP TABLE IF EXISTS payroll.payroll_transactions_future CASCADE;
DROP TABLE IF EXISTS payroll.stg_imported_payroll CASCADE;
DROP TABLE IF EXISTS payroll.import_batches CASCADE;
DROP TABLE IF EXISTS payroll.import_runs CASCADE;
DROP TABLE IF EXISTS payroll.import_log CASCADE;
DROP TABLE IF EXISTS payroll.kpi_snapshot CASCADE;

\echo '  ✓ Tables payroll supprimées'

-- Supprimer tables core
DROP TABLE IF EXISTS core.employees CASCADE;
DROP TABLE IF EXISTS core.employee_job_history CASCADE;
DROP TABLE IF EXISTS core.job_categories CASCADE;
DROP TABLE IF EXISTS core.job_codes CASCADE;
DROP TABLE IF EXISTS core.pay_codes CASCADE;
DROP TABLE IF EXISTS core.budget_posts CASCADE;

\echo '  ✓ Tables core supprimées'

-- Supprimer tables reference
DROP TABLE IF EXISTS reference.pay_codes CASCADE;
DROP TABLE IF EXISTS reference.pay_code_mappings CASCADE;
DROP TABLE IF EXISTS reference.budget_posts CASCADE;
DROP TABLE IF EXISTS reference.sign_policies CASCADE;

\echo '  ✓ Tables reference supprimées'

-- ============================================================================
-- 2. SUPPRIMER VUES
-- ============================================================================

\echo ''
\echo '2. Suppression vues...'

DROP VIEW IF EXISTS payroll.v_imported_payroll CASCADE;
DROP VIEW IF EXISTS payroll.v_imported_payroll_compat CASCADE;
DROP VIEW IF EXISTS core.v_employees_enriched CASCADE;

\echo '  ✓ Vues supprimées'

-- ============================================================================
-- 3. SUPPRIMER FONCTIONS
-- ============================================================================

\echo ''
\echo '3. Suppression fonctions...'

DROP FUNCTION IF EXISTS core.compute_employee_key(TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS core.update_updated_at_column() CASCADE;

\echo '  ✓ Fonctions supprimées'

-- ============================================================================
-- 4. GARDER LA SOURCE (imported_payroll_master)
-- ============================================================================

\echo ''
\echo '4. Conservation source...'

-- NE PAS SUPPRIMER imported_payroll_master (source de vérité)
-- On va re-importer depuis cette table

SELECT COUNT(*) AS lignes_source_conservees 
FROM payroll.imported_payroll_master;

\echo '  ✓ Source imported_payroll_master CONSERVÉE'

-- ============================================================================
-- RÉSUMÉ
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'NETTOYAGE TERMINÉ'
\echo '============================================================================'
\echo ''
\echo 'Supprimé:'
\echo '  - Toutes tables core.* (sauf imported_payroll_master)'
\echo '  - Toutes tables payroll.* (sauf imported_payroll_master)'
\echo '  - Toutes tables reference.*'
\echo '  - Toutes vues et fonctions'
\echo ''
\echo 'Conservé:'
\echo '  - payroll.imported_payroll_master (source Excel)'
\echo ''
\echo 'Prêt pour:'
\echo '  - Exécuter migration/01_ddl_referentiel.sql'
\echo '  - Puis migration/02_migrate_to_referentiel.sql'
\echo ''
\echo '============================================================================'

