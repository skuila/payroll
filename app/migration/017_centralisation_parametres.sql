-- ============================================================================
-- Migration 017: Centralisation des paramètres + MAJ vues KPI (vérité PG)
-- Objectif: Créer ref.parameters et utiliser un taux paramétrable pour part_employeur
-- Exécution: psql -d payroll_db -f migration/017_centralisation_parametres.sql
-- Idempotence: Oui (CREATE IF NOT EXISTS, UPSERT conditionnel, CREATE OR REPLACE VIEW)
-- ============================================================================

\set ON_ERROR_STOP on
SET client_min_messages TO NOTICE;

\echo ''
\echo '========================================================================='
\echo '017 - Début migration: Centralisation paramètres + MAJ vues KPI'
\echo '========================================================================='
\echo ''

-- ============================================================================
-- 1) Schéma de paramètres
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS ref;

-- Table paramètres génériques (clé/valeur)
CREATE TABLE IF NOT EXISTS ref.parameters (
    key         TEXT PRIMARY KEY,
    value_num   NUMERIC,
    value_text  TEXT,
    value_json  JSONB,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Paramètre: taux part employeur (par défaut 0.15)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM ref.parameters WHERE key = 'part_employeur_taux'
    ) THEN
        INSERT INTO ref.parameters(key, value_num)
        VALUES('part_employeur_taux', 0.15);
    END IF;
END $$;

\echo '  ✓ Schéma ref et paramètre part_employeur_taux prêts'

-- Droits de lecture pour l'application
GRANT USAGE ON SCHEMA ref TO payroll_app;
GRANT SELECT ON ALL TABLES IN SCHEMA ref TO payroll_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA ref GRANT SELECT ON TABLES TO payroll_app;

-- ============================================================================
-- 2) Mettre à jour les vues KPI pour utiliser le paramètre ref.parameters
--    Taux utilisé: COALESCE((SELECT value_num FROM ref.parameters WHERE key='part_employeur_taux' LIMIT 1), 0.15)
-- ============================================================================

-- Vue mensuelle/quotidienne consolidée
CREATE OR REPLACE VIEW paie.v_kpi_mois AS
WITH taux AS (
    SELECT COALESCE((SELECT value_num FROM ref.parameters WHERE key = 'part_employeur_taux' LIMIT 1), 0.15) AS t
)
SELECT
    -- Date de paie exacte (OBLIGATOIRE)
    TO_CHAR(t.pay_date, 'YYYY-MM-DD') AS date_paie,
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS gains_brut,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS deductions_net,
    COALESCE(SUM(t.amount_cents), 0) / 100.0 AS net_a_payer,
    -- part_employeur paramétrée
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * (SELECT t FROM taux) ELSE 0 END), 0) / 100.0 AS part_employeur,
    (COALESCE(SUM(t.amount_cents), 0) + COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * (SELECT t FROM taux) ELSE 0 END), 0)) / 100.0 AS cout_total,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN ABS(t.amount_cents) ELSE 0 END), 0) / 100.0 AS cash_out_total,
    COUNT(DISTINCT CASE WHEN t.amount_cents <> 0 THEN t.employee_id END) AS nb_employes,
    COUNT(*) AS nb_transactions
FROM payroll.payroll_transactions t
GROUP BY t.pay_date, TO_CHAR(t.pay_date, 'YYYY-MM-DD')
ORDER BY date_paie;

COMMENT ON VIEW paie.v_kpi_mois IS 'KPI consolidés par mois/jour (paramètre part_employeur via ref.parameters)';

-- Vue par employé et période (mois/jour)
CREATE OR REPLACE VIEW paie.v_kpi_par_employe_mois AS
WITH taux AS (
    SELECT COALESCE((SELECT value_num FROM ref.parameters WHERE key = 'part_employeur_taux' LIMIT 1), 0.15) AS t
)
SELECT
    -- Date de paie exacte (OBLIGATOIRE)
    TO_CHAR(t.pay_date, 'YYYY-MM-DD') AS date_paie,
    t.employee_id                      AS matricule,
    COALESCE(s.nom_prenom, 'N/A')      AS nom_prenom,
    COALESCE(s.categorie_emploi, 'Non défini')  AS categorie_emploi,
    COALESCE(s.titre_emploi, 'Non défini')      AS titre_emploi,
    COALESCE(s.poste_budgetaire, 'Non défini')  AS poste_budgetaire,
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS gains_brut,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS deductions,
    COALESCE(SUM(t.amount_cents), 0) / 100.0 AS net,
    -- part_employeur paramétrée
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * (SELECT t FROM taux) ELSE 0 END), 0) / 100.0 AS part_employeur,
    (COALESCE(SUM(t.amount_cents), 0) + COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * (SELECT t FROM taux) ELSE 0 END), 0)) / 100.0 AS cout_total
FROM payroll.payroll_transactions t
LEFT JOIN paie.stg_paie_transactions s
  ON t.source_file = s.source_file
 AND t.source_row_no = s.source_row_number
GROUP BY t.pay_date, TO_CHAR(t.pay_date, 'YYYY-MM-DD'),
         t.employee_id, s.nom_prenom, s.categorie_emploi, s.titre_emploi, s.poste_budgetaire
ORDER BY date_paie, matricule;

COMMENT ON VIEW paie.v_kpi_par_employe_mois IS 'KPI par employé et période (paramètre part_employeur via ref.parameters)';

\echo '  ✓ Vues KPI mises à jour pour utiliser ref.parameters'

\echo ''
\echo '========================================================================='
\echo '017 - Migration terminée avec succès'
\echo '========================================================================='
\echo ''


