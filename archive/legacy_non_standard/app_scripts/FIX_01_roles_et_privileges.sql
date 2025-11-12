-- ========================================
-- CORRECTIF 1: Rôles et Privilèges
-- ========================================
-- But: Que l'app lise/écrive ce qu'il faut, sans trous de droits
-- Exécuter en tant que: payroll_user (ou l'utilisateur qui a créé les schémas)
-- IDEMPOTENT: Peut être exécuté plusieurs fois sans erreur
-- Version: 2.0.1 (Production Hardened)

\echo '🔐 CORRECTIF 1: Application des droits minimaux...'

-- Transaction avec timeouts et search_path
BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL client_min_messages = warning;
SET LOCAL search_path = payroll, core, reference, security, public;

-- Vérifier le rôle actuel
SELECT current_user AS "Utilisateur actuel", session_user AS "Session";

-- Créer le rôle payroll_app s'il n'existe pas
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'payroll_app') THEN
        -- REMARQUE: le mot de passe n'est pas versionné dans le dépôt. Remplacez <REDACTED_PAYROLL_APP_PASSWORD>
        -- par une valeur sécurisée lors de l'exécution (ou créez le rôle sans mot de passe et assignez un password via un secret manager).
        CREATE ROLE payroll_app WITH LOGIN PASSWORD '<REDACTED_PAYROLL_APP_PASSWORD>';
        RAISE NOTICE 'Rôle payroll_app créé (mot de passe à fournir en dehors du dépôt)';
    ELSE
        RAISE NOTICE 'Rôle payroll_app existe déjà';
    END IF;
END $$;

-- ========================================
-- SCHÉMA PAYROLL
-- ========================================

-- Accès au schéma
GRANT USAGE ON SCHEMA payroll TO payroll_app;

-- Gestion des périodes depuis l'UI
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE payroll.pay_periods TO payroll_app;

-- Source d'affichage (vue normalisée recommandée)
GRANT SELECT ON TABLE payroll.v_imported_payroll TO payroll_app;

-- Table RAW imports
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE payroll.imported_payroll_master TO payroll_app;

-- Import batches
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE payroll.import_batches TO payroll_app;

-- KPI Snapshot (CRITIQUE)
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE payroll.kpi_snapshot TO payroll_app;

-- Si table transactions normalisée existe
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'payroll' AND table_name = 'payroll_transactions'
    ) THEN
        GRANT SELECT ON TABLE payroll.payroll_transactions TO payroll_app;
        RAISE NOTICE 'GRANT SELECT sur payroll.payroll_transactions appliqué';
    END IF;
END $$;

-- Séquences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA payroll TO payroll_app;

-- Éviter regressions au prochain déploiement
ALTER DEFAULT PRIVILEGES IN SCHEMA payroll
  GRANT SELECT ON TABLES TO payroll_app;

\echo '✅ Droits accordés sur schéma payroll'

-- ========================================
-- SCHÉMA CORE
-- ========================================

GRANT USAGE ON SCHEMA core TO payroll_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA core TO payroll_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA core TO payroll_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA core
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO payroll_app;

\echo '✅ Droits accordés sur schéma core'

-- ========================================
-- SCHÉMA REFERENCE
-- ========================================

GRANT USAGE ON SCHEMA reference TO payroll_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA reference TO payroll_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA reference TO payroll_app;

\echo '✅ Droits accordés sur schéma reference'

-- ========================================
-- SCHÉMA SECURITY
-- ========================================

GRANT USAGE ON SCHEMA security TO payroll_app;
GRANT SELECT ON TABLE security.users TO payroll_app;
GRANT SELECT, INSERT ON TABLE security.audit_logs TO payroll_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA security TO payroll_app;

-- Interdire DELETE sur audit_logs (append-only)
REVOKE DELETE ON TABLE security.audit_logs FROM payroll_app;

\echo '✅ Droits accordés sur schéma security'

\echo ''
\echo '========================================='
\echo '✅ CORRECTIF 1 TERMINÉ AVEC SUCCÈS!'
\echo '========================================='
\echo ''
\echo 'Vérification des privilèges:'
\echo ''

-- Vérifier les privilèges accordés à payroll_app
SELECT 
    schemaname AS "Schéma",
    tablename AS "Table/Vue",
    CASE 
        WHEN has_table_privilege('payroll_app', schemaname||'.'||tablename, 'SELECT') THEN 'SELECT '
        ELSE ''
    END ||
    CASE 
        WHEN has_table_privilege('payroll_app', schemaname||'.'||tablename, 'INSERT') THEN 'INSERT '
        ELSE ''
    END ||
    CASE 
        WHEN has_table_privilege('payroll_app', schemaname||'.'||tablename, 'UPDATE') THEN 'UPDATE '
        ELSE ''
    END ||
    CASE 
        WHEN has_table_privilege('payroll_app', schemaname||'.'||tablename, 'DELETE') THEN 'DELETE'
        ELSE ''
    END AS "Privilèges"
FROM pg_tables
WHERE schemaname IN ('payroll', 'core', 'reference', 'security')
    AND tablename IN ('pay_periods', 'imported_payroll_master', 'kpi_snapshot', 'payroll_transactions', 
                      'employees', 'pay_codes', 'budget_posts', 'users', 'audit_logs')
ORDER BY schemaname, tablename;

\echo ''
\echo 'Test rapide:'
\echo 'Commande: SELECT current_user, session_user;'
\echo ''
\echo 'Pour tester en tant que payroll_app:'
\echo 'SET ROLE payroll_app;'
\echo 'SELECT * FROM payroll.pay_periods LIMIT 1;'
\echo 'RESET ROLE;'
\echo ''
\echo 'Pour vérification complète, exécuter:'
\echo 'psql -U postgres -d payroll_db -f scripts/SELF_CHECK.sql'

-- Commit transaction
COMMIT;

\echo ''
\echo '✅ Transaction COMMIT réussie - Privilèges appliqués de manière atomique'

