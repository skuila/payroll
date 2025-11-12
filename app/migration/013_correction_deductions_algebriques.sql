-- ============================================================================
-- Migration 013: Correction déductions algébriques + nouveaux KPIs
-- ============================================================================
-- Description:
--   Correction du calcul des déductions (algébrique au lieu d'ABS)
--   Ajout de nouveaux KPIs : cout_employeur_pnl, cash_out_total
--   Exposition déductions_brutes et remboursements
--
-- Objectif: 
--   Net = Gains + Déductions_NET (algébrique)
--   Cash_out = Gains + Part_employeur (validation P&L)
--
-- Date: 2025-10-21
-- ============================================================================

\set ON_ERROR_STOP on

BEGIN;

-- ============================================================================
-- ÉTAPE 1: Ajouter colonnes tags dans fact_paie
-- ============================================================================

ALTER TABLE paie.fact_paie 
ADD COLUMN IF NOT EXISTS is_adjustment BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_refund BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS duplicate_of VARCHAR(255),
ADD COLUMN IF NOT EXISTS first_seen_batch_id VARCHAR(50);

COMMENT ON COLUMN paie.fact_paie.is_adjustment IS 
'TRUE si gain négatif (ajustement/correction)';

COMMENT ON COLUMN paie.fact_paie.is_refund IS 
'TRUE si retenue positive (remboursement)';

COMMENT ON COLUMN paie.fact_paie.duplicate_of IS 
'Clé métier de la transaction originale si doublon détecté';

COMMENT ON COLUMN paie.fact_paie.first_seen_batch_id IS 
'Premier batch ayant inséré cette clé métier';

-- ============================================================================
-- ÉTAPE 2: Ajouter segments dans dim_poste_budgetaire
-- ============================================================================

ALTER TABLE paie.dim_poste_budgetaire
ADD COLUMN IF NOT EXISTS fonds VARCHAR(50),
ADD COLUMN IF NOT EXISTS fonction VARCHAR(50),
ADD COLUMN IF NOT EXISTS compte VARCHAR(50),
ADD COLUMN IF NOT EXISTS entite VARCHAR(50);

COMMENT ON COLUMN paie.dim_poste_budgetaire.fonds IS 
'Segment 1 : Fonds budgétaire';

COMMENT ON COLUMN paie.dim_poste_budgetaire.fonction IS 
'Segment 2 : Fonction/Direction';

COMMENT ON COLUMN paie.dim_poste_budgetaire.compte IS 
'Segment 3 : Compte GL';

COMMENT ON COLUMN paie.dim_poste_budgetaire.entite IS 
'Segment 4 : Entité organisationnelle';

-- Index sur segments pour performance
CREATE INDEX IF NOT EXISTS idx_dim_poste_fonds ON paie.dim_poste_budgetaire(fonds);
CREATE INDEX IF NOT EXISTS idx_dim_poste_fonction ON paie.dim_poste_budgetaire(fonction);

-- ============================================================================
-- ÉTAPE 3: Table de logging déduplication
-- ============================================================================

CREATE TABLE IF NOT EXISTS paie.dedup_log (
    dedup_id BIGSERIAL PRIMARY KEY,
    cle_metier VARCHAR(255) NOT NULL,
    source_batch_id VARCHAR(50) NOT NULL,
    duplicate_of_batch_id VARCHAR(50),
    date_paie DATE,
    matricule VARCHAR(50),
    code_paie VARCHAR(50),
    montant_cents BIGINT,
    raison VARCHAR(100) DEFAULT 'DOUBLON_CLE_METIER',
    detected_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dedup_log_batch ON paie.dedup_log(source_batch_id);
CREATE INDEX IF NOT EXISTS idx_dedup_log_cle ON paie.dedup_log(cle_metier);

COMMENT ON TABLE paie.dedup_log IS 
'Log des transactions rejetées pour cause de doublon';

-- ============================================================================
-- ÉTAPE 4: Remplacer vue v_kpi_mois (déductions algébriques)
-- ============================================================================

DROP VIEW IF EXISTS paie.v_kpi_mois CASCADE;

CREATE OR REPLACE VIEW paie.v_kpi_mois AS
SELECT
    t.date_paie,
    t.mois_paie,
    t.annee_paie,
    t.mois_paie,
    t.trimestre,
    t.exercice_fiscal,
    
    -- Nombre d'employés
    COUNT(DISTINCT f.employe_id) as nb_employes,
    
    -- Nombre de transactions
    COUNT(*) as nb_transactions,
    
    -- Gains (positifs uniquement, hors ajustements)
    SUM(
        CASE WHEN c.categorie_paie = 'Gains' AND f.montant_cents >= 0
        THEN f.montant_cents 
        ELSE 0 END
    ) / 100.0 as gains_brut,
    
    -- Ajustements (gains négatifs)
    SUM(
        CASE WHEN c.categorie_paie = 'Gains' AND f.montant_cents < 0
        THEN ABS(f.montant_cents)
        ELSE 0 END
    ) / 100.0 as ajustements_gains,
    
    -- DÉDUCTIONS NET (ALGÉBRIQUE - clé de la correction)
    SUM(
        CASE WHEN c.categorie_paie IN ('Deductions', 'Deductions_legales', 'Assurances', 'Syndicats')
        THEN f.montant_cents  -- ALGÉBRIQUE (négatif)
        ELSE 0 END
    ) / 100.0 as deductions_net,
    
    -- Déductions BRUTES (valeur absolue des montants négatifs seulement)
    SUM(
        CASE WHEN c.categorie_paie IN ('Deductions', 'Deductions_legales', 'Assurances', 'Syndicats')
             AND f.montant_cents < 0
        THEN ABS(f.montant_cents)
        ELSE 0 END
    ) / 100.0 as deductions_brutes,
    
    -- Remboursements (retenues positives)
    SUM(
        CASE WHEN c.categorie_paie IN ('Deductions', 'Deductions_legales', 'Assurances', 'Syndicats')
             AND f.montant_cents > 0
        THEN f.montant_cents
        ELSE 0 END
    ) / 100.0 as remboursements,
    
    -- Déductions par type (algébriques)
    SUM(
        CASE WHEN c.categorie_paie = 'Deductions_legales'
        THEN f.montant_cents
        ELSE 0 END
    ) / 100.0 as deductions_legales_net,
    
    SUM(
        CASE WHEN c.categorie_paie = 'Assurances'
        THEN f.montant_cents
        ELSE 0 END
    ) / 100.0 as assurances_net,
    
    SUM(
        CASE WHEN c.categorie_paie = 'Syndicats'
        THEN f.montant_cents
        ELSE 0 END
    ) / 100.0 as syndicats_net,
    
    -- Net à payer (ALGÉBRIQUE)
    SUM(f.montant_cents) / 100.0 as net_a_payer,
    
    -- Part employeur
    SUM(f.part_employeur_cents) / 100.0 as part_employeur,
    
    -- NOUVEAU: Coût employeur P&L (vision comptable)
    (SUM(CASE WHEN c.categorie_paie = 'Gains' THEN f.montant_cents ELSE 0 END) + 
     SUM(f.part_employeur_cents)) / 100.0 as cout_employeur_pnl,
    
    -- NOUVEAU: Cash-out total (vision trésorerie)
    (SUM(f.montant_cents) + SUM(f.part_employeur_cents)) / 100.0 as cash_out_total,
    
    -- DÉPRÉCIÉ: Ancien coût total (pour compatibilité temporaire)
    (SUM(f.montant_cents) + SUM(f.part_employeur_cents)) / 100.0 as cout_total_employeur_obsolete,
    
    -- Moyenne par employé
    SUM(f.montant_cents) / NULLIF(COUNT(DISTINCT f.employe_id), 0) / 100.0 as net_moyen_par_employe,
    
    -- Compteurs tags
    COUNT(*) FILTER (WHERE f.is_adjustment) as nb_ajustements,
    COUNT(*) FILTER (WHERE f.is_refund) as nb_remboursements

FROM paie.fact_paie f
JOIN paie.dim_temps t ON f.temps_id = t.temps_id
JOIN paie.dim_code_paie c ON f.code_paie_id = c.code_paie_id
GROUP BY 
    t.date_paie, 
    t.mois_paie, 
    t.annee_paie, 
    t.mois_paie, 
    t.trimestre, 
    t.exercice_fiscal
ORDER BY t.date_paie DESC;

COMMENT ON VIEW paie.v_kpi_mois IS 
'KPIs par date paie - DÉDUCTIONS ALGÉBRIQUES (correction v2)';

-- ============================================================================
-- ÉTAPE 5: Remplacer vue matérialisée v_kpi_temps_mensuel
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS paie.v_kpi_temps_mensuel CASCADE;

CREATE MATERIALIZED VIEW paie.v_kpi_temps_mensuel AS
SELECT
    t.mois_paie,
    t.annee_paie,
    t.mois_paie,
    
    COUNT(DISTINCT f.employe_id) as nb_employes,
    COUNT(*) as nb_transactions,
    
    -- Gains
    SUM(CASE WHEN c.categorie_paie = 'Gains' AND f.montant_cents >= 0 THEN f.montant_cents ELSE 0 END) / 100.0 as gains_brut,
    SUM(CASE WHEN c.categorie_paie = 'Gains' AND f.montant_cents < 0 THEN ABS(f.montant_cents) ELSE 0 END) / 100.0 as ajustements_gains,
    
    -- Déductions (ALGÉBRIQUES)
    SUM(CASE WHEN c.categorie_paie IN ('Deductions', 'Deductions_legales', 'Assurances', 'Syndicats') 
        THEN f.montant_cents ELSE 0 END) / 100.0 as deductions_net,
    SUM(CASE WHEN c.categorie_paie IN ('Deductions', 'Deductions_legales', 'Assurances', 'Syndicats') AND f.montant_cents < 0 
        THEN ABS(f.montant_cents) ELSE 0 END) / 100.0 as deductions_brutes,
    SUM(CASE WHEN c.categorie_paie IN ('Deductions', 'Deductions_legales', 'Assurances', 'Syndicats') AND f.montant_cents > 0 
        THEN f.montant_cents ELSE 0 END) / 100.0 as remboursements,
    
    -- Par type
    SUM(CASE WHEN c.categorie_paie = 'Deductions_legales' THEN f.montant_cents ELSE 0 END) / 100.0 as deductions_legales_net,
    SUM(CASE WHEN c.categorie_paie = 'Assurances' THEN f.montant_cents ELSE 0 END) / 100.0 as assurances_net,
    SUM(CASE WHEN c.categorie_paie = 'Syndicats' THEN f.montant_cents ELSE 0 END) / 100.0 as syndicats_net,
    
    -- Net
    SUM(f.montant_cents) / 100.0 as net_a_payer,
    SUM(f.part_employeur_cents) / 100.0 as part_employeur,
    
    -- Nouveaux KPIs
    (SUM(CASE WHEN c.categorie_paie = 'Gains' THEN f.montant_cents ELSE 0 END) + SUM(f.part_employeur_cents)) / 100.0 as cout_employeur_pnl,
    (SUM(f.montant_cents) + SUM(f.part_employeur_cents)) / 100.0 as cash_out_total,
    
    SUM(f.montant_cents) / NULLIF(COUNT(DISTINCT f.employe_id), 0) / 100.0 as net_moyen_par_employe,
    
    -- Tags
    COUNT(*) FILTER (WHERE f.is_adjustment) as nb_ajustements,
    COUNT(*) FILTER (WHERE f.is_refund) as nb_remboursements,
    
    MAX(f.created_at) as derniere_mise_a_jour

FROM paie.fact_paie f
JOIN paie.dim_temps t ON f.temps_id = t.temps_id
JOIN paie.dim_code_paie c ON f.code_paie_id = c.code_paie_id
GROUP BY t.mois_paie, t.annee_paie, t.mois_paie
ORDER BY t.mois_paie DESC;

CREATE UNIQUE INDEX idx_v_kpi_temps_mensuel_mois ON paie.v_kpi_temps_mensuel(mois_paie);

COMMENT ON MATERIALIZED VIEW paie.v_kpi_temps_mensuel IS 
'KPIs mensuels - Déductions algébriques (v2)';

-- ============================================================================
-- ÉTAPE 6: VUE de déduplication
-- ============================================================================

CREATE OR REPLACE VIEW paie.v_dedup_report AS
SELECT
    d.source_batch_id,
    d.date_paie,
    COUNT(*) as nb_doublons,
    SUM(ABS(d.montant_cents)) / 100.0 as montant_total_ignore,
    STRING_AGG(DISTINCT d.code_paie, ', ') as codes_paie_concernes,
    STRING_AGG(DISTINCT d.matricule, ', ') as matricules_concernes
FROM paie.dedup_log d
GROUP BY d.source_batch_id, d.date_paie
ORDER BY d.source_batch_id DESC;

COMMENT ON VIEW paie.v_dedup_report IS 
'Rapport de déduplication - Volume et répartition';

-- ============================================================================
-- ÉTAPE 7: Vue de validation (tests bloquants)
-- ============================================================================

CREATE OR REPLACE VIEW paie.v_tests_validation AS
WITH kpis AS (
    SELECT * FROM paie.v_kpi_mois
)
SELECT
    mois_paie,
    
    -- Test 1: Net = Gains + Déductions_NET
    ABS(net_a_payer - (gains_brut - ajustements_gains + deductions_net)) as ecart_net,
    ABS((net_a_payer - (gains_brut - ajustements_gains + deductions_net)) / NULLIF(gains_brut, 0)) as ecart_net_pct,
    
    -- Test 2: Cash_out = Gains + Part_employeur
    ABS(cash_out_total - (gains_brut - ajustements_gains + part_employeur)) as ecart_cash_out,
    ABS((cash_out_total - (gains_brut - ajustements_gains + part_employeur)) / NULLIF(gains_brut + part_employeur, 0)) as ecart_cash_out_pct,
    
    -- Test 3: Déductions_NET = Déductions_brutes - Remboursements (algébrique)
    ABS(deductions_net - (-deductions_brutes + remboursements)) as ecart_deductions,
    
    -- Seuils
    CASE WHEN ABS((net_a_payer - (gains_brut - ajustements_gains + deductions_net)) / NULLIF(gains_brut, 0)) > 0.0001 
         THEN 'FAIL' ELSE 'PASS' END as test_net_status,
    CASE WHEN ABS((cash_out_total - (gains_brut - ajustements_gains + part_employeur)) / NULLIF(gains_brut + part_employeur, 0)) > 0.0001 
         THEN 'FAIL' ELSE 'PASS' END as test_cash_out_status

FROM kpis;

COMMENT ON VIEW paie.v_tests_validation IS 
'Tests de validation BLOQUANTS - Seuil ±0.01%';

COMMIT;

\echo '✓ Migration 013 appliquée : déductions algébriques + nouveaux KPIs'




