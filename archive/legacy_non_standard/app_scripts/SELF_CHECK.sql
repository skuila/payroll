-- ========================================
-- SELF-CHECK: Diagnostic Automatique
-- ========================================
-- But: Vérifier l'état du système avant/après déploiement
-- Exécution: psql -U payroll_app -d payroll_db -f scripts/SELF_CHECK.sql
-- Version: 2.0.1

\echo '🔍 SELF-CHECK: Diagnostic du système PayrollAnalyzer'
\echo ''

SET search_path = payroll, core, reference, security, public;
SET client_min_messages = warning;

-- ========================================
-- 1. IDENTITÉ ET SESSION
-- ========================================
\echo '1️⃣ Identité et Session:'
SELECT 
    current_user AS "Current User", 
    session_user AS "Session User",
    current_database() AS "Database",
    inet_client_addr() AS "Client IP",
    pg_backend_pid() AS "Backend PID";

\echo ''

-- ========================================
-- 2. PRIVILÈGES ESSENTIELS
-- ========================================
\echo '2️⃣ Privilèges Essentiels (doit être TRUE):'
SELECT 
    has_schema_privilege(current_user, 'payroll', 'USAGE') AS "✓ payroll.USAGE",
    has_schema_privilege(current_user, 'core', 'USAGE') AS "✓ core.USAGE",
    has_schema_privilege(current_user, 'reference', 'USAGE') AS "✓ reference.USAGE",
    has_schema_privilege(current_user, 'security', 'USAGE') AS "✓ security.USAGE";

\echo ''
SELECT 
    has_table_privilege(current_user, 'payroll.pay_periods', 'SELECT') AS "✓ pay_periods.SELECT",
    has_table_privilege(current_user, 'payroll.pay_periods', 'INSERT') AS "✓ pay_periods.INSERT",
    has_table_privilege(current_user, 'payroll.pay_periods', 'UPDATE') AS "✓ pay_periods.UPDATE",
    has_table_privilege(current_user, 'payroll.pay_periods', 'DELETE') AS "✓ pay_periods.DELETE";

\echo ''
SELECT 
    has_table_privilege(current_user, 'payroll.kpi_snapshot', 'SELECT') AS "✓ kpi_snapshot.SELECT",
    has_table_privilege(current_user, 'payroll.kpi_snapshot', 'INSERT') AS "✓ kpi_snapshot.INSERT",
    has_table_privilege(current_user, 'payroll.v_imported_payroll', 'SELECT') AS "✓ v_imported_payroll.SELECT";

\echo ''

-- ========================================
-- 3. CONTRAINTES ET FONCTIONS CRITIQUES
-- ========================================
\echo '3️⃣ Contraintes et Fonctions Critiques:'
SELECT 
    conname AS "Constraint Name",
    contype AS "Type"
FROM pg_constraint
WHERE conname IN ('uq_pay_periods_date', 'uq_pay_periods_year_seq')
ORDER BY conname;

\echo ''
SELECT 
    n.nspname AS "Schema",
    p.proname AS "Function Name",
    pg_get_function_identity_arguments(p.oid) AS "Arguments"
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE p.proname = 'ensure_period' 
  AND n.nspname = 'payroll';

\echo ''

-- ========================================
-- 4. SANTÉ DE LA BASE (Périodes)
-- ========================================
\echo '4️⃣ Santé de la Base:'
SELECT 
    COUNT(*) AS "Total Périodes",
    SUM(CASE WHEN status = 'ouverte' THEN 1 ELSE 0 END) AS "Périodes Ouvertes",
    SUM(CASE WHEN status = 'fermée' THEN 1 ELSE 0 END) AS "Périodes Fermées",
    MIN(pay_date) AS "Première Période",
    MAX(pay_date) AS "Dernière Période"
FROM payroll.pay_periods;

\echo ''

-- ========================================
-- 5. EMPLOYÉS ET TRANSACTIONS
-- ========================================
\echo '5️⃣ Employés et Transactions:'
SELECT 
    (SELECT COUNT(*) FROM core.employees) AS "Total Employés",
    (SELECT COUNT(*) FROM core.employees WHERE statut = 'actif') AS "Employés Actifs",
    (SELECT COUNT(*) FROM payroll.imported_payroll_master) AS "Transactions Importées",
    (SELECT COUNT(DISTINCT source_file) FROM payroll.imported_payroll_master WHERE source_file IS NOT NULL) AS "Fichiers Importés";

\echo ''

-- ========================================
-- 6. TAILLE DE LA BASE
-- ========================================
\echo '6️⃣ Taille de la Base:'
SELECT 
    pg_size_pretty(pg_database_size(current_database())) AS "Taille DB",
    pg_size_pretty(pg_total_relation_size('payroll.pay_periods')) AS "pay_periods",
    pg_size_pretty(pg_total_relation_size('payroll.imported_payroll_master')) AS "imported_payroll",
    pg_size_pretty(pg_total_relation_size('core.employees')) AS "employees";

\echo ''

-- ========================================
-- 7. CONNEXIONS ACTIVES
-- ========================================
\echo '7️⃣ Connexions Actives:'
SELECT 
    COUNT(*) AS "Total Connexions",
    COUNT(*) FILTER (WHERE state = 'active') AS "Connexions Actives",
    COUNT(*) FILTER (WHERE state = 'idle') AS "Connexions Idle"
FROM pg_stat_activity
WHERE datname = current_database();

\echo ''

-- ========================================
-- 8. TEST FONCTIONNEL ensure_period()
-- ========================================
\echo '8️⃣ Test Fonctionnel ensure_period():'
\echo 'Test avec date 2025-12-31 (doit retourner un UUID):'
SELECT payroll.ensure_period('2025-12-31')::text AS "Period ID Test";

\echo ''

-- ========================================
-- 9. DERNIERS IMPORTS
-- ========================================
\echo '9️⃣ 5 Derniers Imports:'
SELECT 
    source_file AS "Fichier",
    MIN("date de paie ") AS "Date Paie",
    COUNT(*) AS "Lignes",
    MIN(imported_at) AS "Importé Le"
FROM payroll.imported_payroll_master
WHERE source_file IS NOT NULL
GROUP BY source_file
ORDER BY MIN(imported_at) DESC
LIMIT 5;

\echo ''
\echo '========================================='
\echo '✅ SELF-CHECK TERMINÉ'
\echo '========================================='
\echo ''
\echo 'Si tous les tests montrent TRUE et des valeurs cohérentes,'
\echo 'le système est opérationnel. ✅'
\echo ''
\echo 'En cas d''erreur, exécuter à nouveau:'
\echo '  psql -U postgres -d payroll_db -f scripts/FIX_01_roles_et_privileges.sql'
\echo '  psql -U postgres -d payroll_db -f scripts/FIX_02_ensure_period_atomique.sql'
\echo ''

