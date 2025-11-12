-- =============================================================================
-- Migration 014: Unicité matricule + Vues KPI standardisées (vérité côté PG)
-- Exécution: psql -d payroll_db -f migration/014_unicite_matricule_et_vues_kpi.sql
-- =============================================================================

\set ON_ERROR_STOP on
SET client_min_messages TO NOTICE;

\echo ''
\echo '========================================================================='
\echo '014 - Début migration: Unicité matricule + Vues KPI standard'
\echo '========================================================================='
\echo ''

-- ============================================================================
-- 1) Pré-requis schémas
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS paie;

-- ============================================================================
-- 2) Audit de base sur core.employees
--    Ajout des colonnes created_at / updated_at si manquantes
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'core' AND table_name = 'employees' AND column_name = 'created_at'
    ) THEN
        EXECUTE 'ALTER TABLE core.employees ADD COLUMN created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'core' AND table_name = 'employees' AND column_name = 'updated_at'
    ) THEN
        EXECUTE 'ALTER TABLE core.employees ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP';
    END IF;
END $$;

-- Déclencheur de mise à jour du champ updated_at
CREATE OR REPLACE FUNCTION core.set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_core_employees_updated_at'
    ) THEN
        CREATE TRIGGER trg_core_employees_updated_at
        BEFORE UPDATE ON core.employees
        FOR EACH ROW
        EXECUTE FUNCTION core.set_updated_at();
    END IF;
END $$;

\echo '  ✓ Colonnes d\'audit et trigger updated_at prêts sur core.employees'

-- ============================================================================
-- 3) Unicité du matricule (1 matricule = 1 employé)
--    On crée un index unique (plus souple qu'une contrainte pour IF NOT EXISTS)
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE schemaname = 'core' AND indexname = 'ux_core_employees_matricule'
    ) THEN
        EXECUTE 'CREATE UNIQUE INDEX ux_core_employees_matricule ON core.employees(matricule)';
    END IF;
END $$;

\echo '  ✓ Index unique sur core.employees(matricule)'

-- ============================================================================
-- 4) Vues KPI standardisées pour consommation API/UI
--    v_kpi_mois          : agrégats mensuels/quotidiens
--    v_kpi_par_employe_mois : agrégats par employé et période
-- ============================================================================

-- Nettoyage préalable des vues si elles existent (évite conflits de colonnes)
DROP VIEW IF EXISTS paie.v_kpi_par_employe_mois CASCADE;
DROP VIEW IF EXISTS paie.v_kpi_mois CASCADE;

-- Vue mensuelle/quotidienne consolidée
CREATE OR REPLACE VIEW paie.v_kpi_mois AS
SELECT
    TO_CHAR(t.pay_date, 'YYYY-MM')    AS periode_paie,
    TO_CHAR(t.pay_date, 'YYYY-MM-DD') AS date_paie,
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS gains_brut,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS deductions_net,
    COALESCE(SUM(t.amount_cents), 0) / 100.0 AS net_a_payer,
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0) / 100.0 AS part_employeur,
    (COALESCE(SUM(t.amount_cents), 0) + COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 AS cout_total,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN ABS(t.amount_cents) ELSE 0 END), 0) / 100.0 AS cash_out_total,
    COUNT(DISTINCT CASE WHEN t.amount_cents <> 0 THEN t.employee_id END) AS nb_employes,
    COUNT(*) AS nb_transactions
FROM payroll.payroll_transactions t
GROUP BY TO_CHAR(t.pay_date, 'YYYY-MM'), TO_CHAR(t.pay_date, 'YYYY-MM-DD')
ORDER BY periode_paie, date_paie;

COMMENT ON VIEW paie.v_kpi_mois IS 'KPI consolidés par mois/jour pour overview (net, coût total, etc.)';

-- Vue par employé et période (mois/jour)
CREATE OR REPLACE VIEW paie.v_kpi_par_employe_mois AS
SELECT
    TO_CHAR(t.pay_date, 'YYYY-MM')    AS periode_paie,
    TO_CHAR(t.pay_date, 'YYYY-MM-DD') AS date_paie,
    t.employee_id                      AS matricule,
    COALESCE(s.nom_prenom, 'N/A')      AS nom_prenom,
    COALESCE(s.categorie_emploi, 'Non défini')  AS categorie_emploi,
    COALESCE(s.titre_emploi, 'Non défini')      AS titre_emploi,
    COALESCE(s.poste_budgetaire, 'Non défini')  AS poste_budgetaire,
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS gains_brut,
    COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 AS deductions,
    COALESCE(SUM(t.amount_cents), 0) / 100.0 AS net,
    COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0) / 100.0 AS part_employeur,
    (COALESCE(SUM(t.amount_cents), 0) + COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents * 0.15 ELSE 0 END), 0)) / 100.0 AS cout_total
FROM payroll.payroll_transactions t
LEFT JOIN paie.stg_paie_transactions s
  ON t.source_file = s.source_file
 AND t.source_row_no = s.source_row_number
GROUP BY TO_CHAR(t.pay_date, 'YYYY-MM'), TO_CHAR(t.pay_date, 'YYYY-MM-DD'),
         t.employee_id, s.nom_prenom, s.categorie_emploi, s.titre_emploi, s.poste_budgetaire
ORDER BY periode_paie, date_paie, matricule;

COMMENT ON VIEW paie.v_kpi_par_employe_mois IS 'KPI par employé et période (mois/jour) pour top-employes et détail.';

\echo '  ✓ Vues paie.v_kpi_mois et paie.v_kpi_par_employe_mois créées'

-- ============================================================================
-- 5) Droits de lecture pour l\'application
-- ============================================================================
GRANT USAGE ON SCHEMA paie TO payroll_app;
GRANT SELECT ON ALL TABLES IN SCHEMA paie TO payroll_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA paie GRANT SELECT ON TABLES TO payroll_app;

\echo ''
\echo '========================================================================='
\echo '014 - Migration terminée avec succès'
\echo '========================================================================='
\echo ''


