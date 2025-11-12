-- ============================================================================
-- TESTS DE VALIDATION: Avant/Après Migration
-- PostgreSQL 17
-- Version: 1.0
-- ============================================================================

SET client_min_messages TO INFO;
SET search_path TO payroll, core, reference, public;

\echo ''
\echo '============================================================================'
\echo 'TESTS DE VALIDATION MIGRATION'
\echo '============================================================================'
\echo ''

-- ============================================================================
-- PARTIE 1: TESTS PRÉ-MIGRATION (Source)
-- ============================================================================

\echo '--- PARTIE 1: TESTS PRÉ-MIGRATION (Source) ---'
\echo ''

-- TEST 1.1: Compter lignes source
\echo 'TEST 1.1: Total lignes source'
SELECT 
    'imported_payroll_master' AS table_name,
    COUNT(*) AS total_lignes
FROM payroll.imported_payroll_master;

-- TEST 1.2: Employés distincts (brut, tous montants)
\echo ''
\echo 'TEST 1.2: Employés distincts (brut, tous montants)'
SELECT 
    'Employés distincts (brut)' AS test,
    COUNT(DISTINCT "matricule ") AS resultat
FROM payroll.imported_payroll_master;

-- TEST 1.3: Employés distincts (montants ≠ 0)
\echo ''
\echo 'TEST 1.3: Employés distincts (montants ≠ 0)'
SELECT 
    'Employés distincts (montants ≠ 0)' AS test,
    COUNT(DISTINCT "matricule ") AS resultat
FROM payroll.imported_payroll_master
WHERE COALESCE("montant ", 0) <> 0;

-- TEST 1.4: Période 2025-08 spécifique
\echo ''
\echo 'TEST 1.4: Employés période 2025-08 (ancien comptage)'
SELECT 
    'Ancien comptage 2025-08' AS test,
    COUNT(DISTINCT "matricule ") AS resultat
FROM payroll.imported_payroll_master
WHERE TO_CHAR("date de paie ", 'YYYY-MM') = '2025-08';

-- TEST 1.5: Montant total (montants ≠ 0)
\echo ''
\echo 'TEST 1.5: Montant total (montants ≠ 0)'
SELECT 
    'Montant total source' AS test,
    ROUND(SUM(COALESCE("montant ", 0))::NUMERIC, 2) AS montant_total
FROM payroll.imported_payroll_master
WHERE COALESCE("montant ", 0) <> 0;

-- TEST 1.6: Lignes avec montant = 0
\echo ''
\echo 'TEST 1.6: Lignes avec montant = 0'
SELECT 
    'Lignes montant = 0' AS test,
    COUNT(*) AS nb_lignes
FROM payroll.imported_payroll_master
WHERE COALESCE("montant ", 0) = 0;

-- TEST 1.7: Périodes couvertes
\echo ''
\echo 'TEST 1.7: Périodes couvertes'
SELECT 
    TO_CHAR("date de paie ", 'YYYY-MM') AS mois,
    COUNT(*) AS nb_lignes,
    COUNT(DISTINCT "matricule ") AS nb_employes_brut
FROM payroll.imported_payroll_master
GROUP BY TO_CHAR("date de paie ", 'YYYY-MM')
ORDER BY mois DESC
LIMIT 10;

\echo ''
\echo '============================================================================'
\echo '--- PARTIE 2: TESTS POST-MIGRATION (Cible) ---'
\echo '============================================================================'
\echo ''

-- TEST 2.1: Employés dans référentiel
\echo 'TEST 2.1: Employés dans référentiel'
SELECT 
    'core.employees' AS table_name,
    COUNT(*) AS nb_employes
FROM core.employees;

-- TEST 2.2: Transactions insérées
\echo ''
\echo 'TEST 2.2: Transactions insérées'
SELECT 
    'payroll.payroll_transactions' AS table_name,
    COUNT(*) AS nb_transactions
FROM payroll.payroll_transactions;

-- TEST 2.3: Nouveau comptage période 2025-08
\echo ''
\echo 'TEST 2.3: Nouveau comptage période 2025-08'
SELECT 
    'Nouveau comptage 2025-08' AS test,
    COUNT(DISTINCT t.employee_id) AS resultat
FROM payroll.payroll_transactions t
WHERE TO_CHAR(t.pay_date, 'YYYY-MM') = '2025-08';

-- TEST 2.4: Montant total (cohérence)
\echo ''
\echo 'TEST 2.4: Montant total (cohérence avec source)'
SELECT 
    'Montant total cible' AS test,
    ROUND(SUM(amount_cents)::NUMERIC / 100, 2) AS montant_total
FROM payroll.payroll_transactions;

-- TEST 2.5: Orphelins (doit être 0)
\echo ''
\echo 'TEST 2.5: Transactions orphelines (FK)'
SELECT 
    'Transactions orphelines' AS test,
    COUNT(*) AS nb_orphelins
FROM payroll.payroll_transactions t
LEFT JOIN core.employees e ON t.employee_id = e.employee_id
WHERE e.employee_id IS NULL;

-- TEST 2.6: Doublons employee_key (doit être 0)
\echo ''
\echo 'TEST 2.6: Doublons employee_key'
SELECT 
    'Doublons employee_key' AS test,
    COUNT(*) AS nb_doublons
FROM (
    SELECT employee_key
    FROM core.employees
    GROUP BY employee_key
    HAVING COUNT(*) > 1
) x;

-- TEST 2.7: Montants = 0 (doit être 0)
\echo ''
\echo 'TEST 2.7: Transactions avec montant = 0'
SELECT 
    'Transactions montant = 0' AS test,
    COUNT(*) AS nb_transactions
FROM payroll.payroll_transactions
WHERE amount_cents = 0;

-- TEST 2.8: Cohérence colonnes générées
\echo ''
\echo 'TEST 2.8: Cohérence colonnes générées (pay_year/month/day)'
SELECT 
    'Incohérence colonnes générées' AS test,
    COUNT(*) AS nb_incoherences
FROM payroll.payroll_transactions
WHERE pay_year <> EXTRACT(YEAR FROM pay_date)
   OR pay_month <> EXTRACT(MONTH FROM pay_date)
   OR pay_day <> EXTRACT(DAY FROM pay_date);

-- TEST 2.9: Distribution par partition
\echo ''
\echo 'TEST 2.9: Distribution par partition (année)'
SELECT 
    pay_year,
    COUNT(*) AS nb_transactions,
    COUNT(DISTINCT employee_id) AS nb_employes,
    ROUND(SUM(amount_cents)::NUMERIC / 100, 2) AS montant_total
FROM payroll.payroll_transactions
GROUP BY pay_year
ORDER BY pay_year;

-- TEST 2.10: Batch import
\echo ''
\echo 'TEST 2.10: Batch import (dernier)'
SELECT 
    batch_id,
    filename,
    status,
    total_rows,
    valid_rows,
    invalid_rows,
    new_employees,
    new_transactions,
    TO_CHAR(started_at, 'YYYY-MM-DD HH24:MI:SS') AS started_at,
    TO_CHAR(completed_at, 'YYYY-MM-DD HH24:MI:SS') AS completed_at
FROM payroll.import_batches
ORDER BY batch_id DESC
LIMIT 1;

\echo ''
\echo '============================================================================'
\echo '--- PARTIE 3: COMPARAISON ANCIEN vs NOUVEAU ---'
\echo '============================================================================'
\echo ''

-- TEST 3.1: Comparaison comptage 2025-08
\echo 'TEST 3.1: Comparaison comptage 2025-08'
WITH ancien AS (
    SELECT COUNT(DISTINCT "matricule ") AS nb
    FROM payroll.imported_payroll_master
    WHERE TO_CHAR("date de paie ", 'YYYY-MM') = '2025-08'
),
nouveau AS (
    SELECT COUNT(DISTINCT t.employee_id) AS nb
    FROM payroll.payroll_transactions t
    WHERE TO_CHAR(t.pay_date, 'YYYY-MM') = '2025-08'
)
SELECT
    ancien.nb AS ancien_comptage,
    nouveau.nb AS nouveau_comptage,
    ancien.nb - nouveau.nb AS reduction,
    ROUND((ancien.nb - nouveau.nb)::NUMERIC / ancien.nb * 100, 1) AS reduction_pct
FROM ancien, nouveau;

-- TEST 3.2: Comparaison montants par période
\echo ''
\echo 'TEST 3.2: Comparaison montants (Top 5 périodes)'
WITH ancien AS (
    SELECT 
        TO_CHAR("date de paie ", 'YYYY-MM') AS mois,
        ROUND(SUM(COALESCE("montant ", 0))::NUMERIC, 2) AS montant
    FROM payroll.imported_payroll_master
    WHERE COALESCE("montant ", 0) <> 0
    GROUP BY TO_CHAR("date de paie ", 'YYYY-MM')
),
nouveau AS (
    SELECT 
        TO_CHAR(pay_date, 'YYYY-MM') AS mois,
        ROUND(SUM(amount_cents)::NUMERIC / 100, 2) AS montant
    FROM payroll.payroll_transactions
    GROUP BY TO_CHAR(pay_date, 'YYYY-MM')
)
SELECT
    COALESCE(a.mois, n.mois) AS mois,
    a.montant AS ancien_montant,
    n.montant AS nouveau_montant,
    ROUND(ABS(COALESCE(a.montant, 0) - COALESCE(n.montant, 0))::NUMERIC, 2) AS ecart
FROM ancien a
FULL OUTER JOIN nouveau n ON a.mois = n.mois
ORDER BY mois DESC
LIMIT 5;

\echo ''
\echo '============================================================================'
\echo 'FIN DES TESTS'
\echo '============================================================================'
\echo ''
\echo 'ATTENDUS:'
\echo '  - Ancien comptage 2025-08: 531 employés'
\echo '  - Nouveau comptage 2025-08: 295 employés'
\echo '  - Réduction: 236 employés (44.4%)'
\echo '  - Orphelins: 0'
\echo '  - Doublons employee_key: 0'
\echo '  - Montants = 0: 0'
\echo '  - Écart montants: < 1$'
\echo ''

