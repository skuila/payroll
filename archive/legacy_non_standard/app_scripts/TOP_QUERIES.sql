-- ========================================
-- TOP QUERIES: Analyse des Requêtes Lentes
-- ========================================
-- But: Identifier les requêtes les plus coûteuses
-- Prérequis: Extension pg_stat_statements doit être activée
-- Activation: CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
-- Exécution: psql -U postgres -d payroll_db -f scripts/TOP_QUERIES.sql
-- Version: 2.0.1

\echo '📊 TOP QUERIES: Analyse des Performances'
\echo ''

SET client_min_messages = warning;

-- Vérifier si pg_stat_statements est disponible
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
    ) THEN
        RAISE NOTICE 'Extension pg_stat_statements non installée.';
        RAISE NOTICE 'Pour l''installer: CREATE EXTENSION pg_stat_statements;';
        RAISE NOTICE 'Et redémarrer PostgreSQL.';
    END IF;
END $$;

\echo ''
\echo '1️⃣ Top 10 Requêtes par Temps Total d''Exécution:'
\echo ''

SELECT 
    substring(query, 1, 80) AS "Query (80 chars)",
    calls AS "Appels",
    round(total_exec_time::numeric, 2) AS "Temps Total (ms)",
    round(mean_exec_time::numeric, 2) AS "Temps Moyen (ms)",
    round(max_exec_time::numeric, 2) AS "Temps Max (ms)",
    round((100.0 * total_exec_time / sum(total_exec_time) OVER ())::numeric, 2) AS "% Total"
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
  AND query NOT LIKE '%pg_catalog%'
ORDER BY total_exec_time DESC
LIMIT 10;

\echo ''
\echo '2️⃣ Top 10 Requêtes par Nombre d''Appels:'
\echo ''

SELECT 
    substring(query, 1, 80) AS "Query (80 chars)",
    calls AS "Appels",
    round(total_exec_time::numeric, 2) AS "Temps Total (ms)",
    round(mean_exec_time::numeric, 2) AS "Temps Moyen (ms)"
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
  AND query NOT LIKE '%pg_catalog%'
ORDER BY calls DESC
LIMIT 10;

\echo ''
\echo '3️⃣ Top 10 Requêtes par Temps Moyen (lentes):'
\echo ''

SELECT 
    substring(query, 1, 80) AS "Query (80 chars)",
    calls AS "Appels",
    round(mean_exec_time::numeric, 2) AS "Temps Moyen (ms)",
    round(max_exec_time::numeric, 2) AS "Temps Max (ms)"
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
  AND query NOT LIKE '%pg_catalog%'
  AND calls > 5
ORDER BY mean_exec_time DESC
LIMIT 10;

\echo ''
\echo '4️⃣ Statistiques Globales:'
\echo ''

SELECT 
    (SELECT count(*) FROM pg_stat_statements) AS "Total Requêtes Uniques",
    (SELECT sum(calls) FROM pg_stat_statements) AS "Total Appels",
    round((SELECT sum(total_exec_time) FROM pg_stat_statements)::numeric, 2) AS "Temps Total (ms)",
    pg_size_pretty(pg_database_size(current_database())) AS "Taille DB";

\echo ''
\echo '5️⃣ Requêtes sur payroll.pay_periods:'
\echo ''

SELECT 
    substring(query, 1, 100) AS "Query",
    calls AS "Appels",
    round(mean_exec_time::numeric, 2) AS "Temps Moyen (ms)"
FROM pg_stat_statements
WHERE query LIKE '%pay_periods%'
  AND query NOT LIKE '%pg_stat_statements%'
ORDER BY calls DESC
LIMIT 5;

\echo ''
\echo '========================================='
\echo '✅ ANALYSE TERMINÉE'
\echo '========================================='
\echo ''
\echo 'Actions recommandées si requêtes lentes détectées:'
\echo '1. Créer des index sur les colonnes fréquemment filtrées'
\echo '2. Exécuter ANALYZE sur les tables concernées'
\echo '3. Vérifier les plans d''exécution avec EXPLAIN ANALYZE'
\echo ''
\echo 'Pour réinitialiser les statistiques:'
\echo 'SELECT pg_stat_statements_reset();'
\echo ''

