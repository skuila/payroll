-- ============================================================================
-- Migration 018: Vues d'agrégation par mois et par année
-- Objectif: Créer des vues pour analyser les données par mois ou par année
--           tout en gardant la règle: "période de paie" = date exacte (YYYY-MM-DD)
-- Exécution: psql -d payroll_db -f migration/018_vues_agregation_mois_annee.sql
-- Idempotence: Oui (CREATE OR REPLACE VIEW)
-- ============================================================================

\set ON_ERROR_STOP on
SET client_min_messages TO NOTICE;

\echo ''
\echo '========================================================================='
\echo '018 - Début migration: Vues d''agrégation par mois et par année'
\echo '========================================================================='
\echo ''

-- ============================================================================
-- VUE D'AGRÉGATION PAR MOIS
-- ============================================================================
-- Cette vue agrège les données par mois (YYYY-MM) pour des analyses mensuelles
-- Note: "période de paie" reste une date exacte, mais cette vue permet
--       des analyses agrégées par mois

DROP VIEW IF EXISTS payroll.v_kpi_agregation_mensuelle CASCADE;

CREATE VIEW payroll.v_kpi_agregation_mensuelle AS
SELECT 
    -- Mois d'agrégation (format YYYY-MM pour analyses mensuelles)
    TO_CHAR(pay_date, 'YYYY-MM') AS mois,
    -- Année (format YYYY)
    TO_CHAR(pay_date, 'YYYY') AS annee,
    
    -- Contrat de colonnes standard (agrégés)
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END), 0) / 100.0 AS gains_brut,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 AS deductions_net,
    COALESCE(SUM(amount_cents), 0) / 100.0 AS net_a_payer,
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0) / 100.0 AS part_employeur,
    (COALESCE(SUM(amount_cents), 0) + COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 AS cout_total,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN ABS(amount_cents) ELSE 0 END), 0) / 100.0 AS cash_out_total,
    COUNT(DISTINCT CASE WHEN amount_cents != 0 THEN employee_id END) AS nb_employes,
    COUNT(DISTINCT pay_date) AS nb_dates_paie,  -- Nombre de dates de paie distinctes dans le mois
    COUNT(*) AS nb_transactions,
    COALESCE(SUM(CASE WHEN amount_cents > 0 AND pay_code LIKE '%AJUST%' THEN amount_cents ELSE 0 END), 0) / 100.0 AS ajustements_gains,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 AS deductions_brutes,
    COALESCE(SUM(CASE WHEN amount_cents < 0 AND pay_code LIKE '%REMBOURSE%' THEN amount_cents ELSE 0 END), 0) / 100.0 AS remboursements

FROM payroll.payroll_transactions
GROUP BY TO_CHAR(pay_date, 'YYYY-MM'), TO_CHAR(pay_date, 'YYYY')
ORDER BY mois DESC;

COMMENT ON VIEW payroll.v_kpi_agregation_mensuelle IS 
'Vue d''agrégation mensuelle - KPI consolidés par mois (YYYY-MM) pour analyses temporelles. 
Note: "période de paie" reste une date exacte (YYYY-MM-DD), cette vue est pour agrégation/analyse uniquement.';

-- ============================================================================
-- VUE D'AGRÉGATION PAR ANNÉE
-- ============================================================================
-- Cette vue agrège les données par année (YYYY) pour des analyses annuelles

DROP VIEW IF EXISTS payroll.v_kpi_agregation_annuelle CASCADE;

CREATE VIEW payroll.v_kpi_agregation_annuelle AS
SELECT 
    -- Année d'agrégation (format YYYY)
    TO_CHAR(pay_date, 'YYYY') AS annee,
    
    -- Contrat de colonnes standard (agrégés)
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END), 0) / 100.0 AS gains_brut,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 AS deductions_net,
    COALESCE(SUM(amount_cents), 0) / 100.0 AS net_a_payer,
    COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0) / 100.0 AS part_employeur,
    (COALESCE(SUM(amount_cents), 0) + COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 AS cout_total,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN ABS(amount_cents) ELSE 0 END), 0) / 100.0 AS cash_out_total,
    COUNT(DISTINCT CASE WHEN amount_cents != 0 THEN employee_id END) AS nb_employes,
    COUNT(DISTINCT pay_date) AS nb_dates_paie,  -- Nombre de dates de paie distinctes dans l'année
    COUNT(DISTINCT TO_CHAR(pay_date, 'YYYY-MM')) AS nb_mois,  -- Nombre de mois distincts dans l'année
    COUNT(*) AS nb_transactions,
    COALESCE(SUM(CASE WHEN amount_cents > 0 AND pay_code LIKE '%AJUST%' THEN amount_cents ELSE 0 END), 0) / 100.0 AS ajustements_gains,
    COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0 AS deductions_brutes,
    COALESCE(SUM(CASE WHEN amount_cents < 0 AND pay_code LIKE '%REMBOURSE%' THEN amount_cents ELSE 0 END), 0) / 100.0 AS remboursements

FROM payroll.payroll_transactions
GROUP BY TO_CHAR(pay_date, 'YYYY')
ORDER BY annee DESC;

COMMENT ON VIEW payroll.v_kpi_agregation_annuelle IS 
'Vue d''agrégation annuelle - KPI consolidés par année (YYYY) pour analyses temporelles. 
Note: "période de paie" reste une date exacte (YYYY-MM-DD), cette vue est pour agrégation/analyse uniquement.';

-- ============================================================================
-- VUE D'AGRÉGATION PAR MOIS ET CATÉGORIE D'EMPLOI
-- ============================================================================

DROP VIEW IF EXISTS payroll.v_kpi_agregation_mensuelle_par_categorie CASCADE;

CREATE VIEW payroll.v_kpi_agregation_mensuelle_par_categorie AS
SELECT 
    -- Mois d'agrégation
    TO_CHAR(t.pay_date, 'YYYY-MM') AS mois,
    TO_CHAR(t.pay_date, 'YYYY') AS annee,
    -- Catégorie d'emploi
    COALESCE(e.categorie_emploi, 'Non défini') AS categorie_emploi,
    
    -- Contrat de colonnes standard (agrégés)
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS gains_brut,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS deductions_net,
    COALESCE(SUM(t.amount_cents), 0) / 100.0 AS net_a_payer,
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0) / 100.0 AS part_employeur,
    (COALESCE(SUM(t.amount_cents), 0) + COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 AS cout_total,
    COUNT(DISTINCT CASE WHEN t.amount_cents != 0 THEN t.employee_id END) AS nb_employes,
    COUNT(*) AS nb_transactions

FROM payroll.payroll_transactions t
LEFT JOIN payroll.employees e ON t.employee_id = e.employee_id
GROUP BY TO_CHAR(t.pay_date, 'YYYY-MM'), TO_CHAR(t.pay_date, 'YYYY'), e.categorie_emploi
ORDER BY mois DESC, categorie_emploi;

COMMENT ON VIEW payroll.v_kpi_agregation_mensuelle_par_categorie IS 
'Vue d''agrégation mensuelle par catégorie d''emploi - pour analyses par mois et catégorie.';

-- ============================================================================
-- GRANTS ET PERMISSIONS
-- ============================================================================

GRANT SELECT ON payroll.v_kpi_agregation_mensuelle TO payroll_app;
GRANT SELECT ON payroll.v_kpi_agregation_annuelle TO payroll_app;
GRANT SELECT ON payroll.v_kpi_agregation_mensuelle_par_categorie TO payroll_app;

\echo '  ✓ Vues d''agrégation par mois et par année créées'
\echo ''
\echo '========================================================================='
\echo '018 - Migration terminée avec succès'
\echo '========================================================================='
\echo ''
\echo 'Vues créées:'
\echo '  - payroll.v_kpi_agregation_mensuelle (agrégation par mois YYYY-MM)'
\echo '  - payroll.v_kpi_agregation_annuelle (agrégation par année YYYY)'
\echo '  - payroll.v_kpi_agregation_mensuelle_par_categorie (mois + catégorie)'
\echo ''
\echo 'Note: Ces vues sont pour analyses/agrégation uniquement.'
\echo '      "Période de paie" reste toujours une date exacte (YYYY-MM-DD).'
\echo ''

