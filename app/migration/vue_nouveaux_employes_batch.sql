-- ============================================================================
-- Vue: Détection des nouveaux employés par BATCH (fichier import)
-- Règle métier: 1 période = 1 fichier = 1 date exacte
-- Nouveau employé = matricule > MAX(matricule du batch précédent)
-- ============================================================================
-- Version: 1.0
-- Date: 2025-10-17
-- ============================================================================

SET client_min_messages TO WARNING;
SET search_path TO payroll, core, public;

-- ============================================================================
-- VUE: v_nouveaux_par_batch
-- ============================================================================

CREATE OR REPLACE VIEW payroll.v_nouveaux_par_batch AS
WITH batches_avec_date AS (
    -- Liste des batches avec leur date de paie unique (1 fichier = 1 date)
    SELECT DISTINCT
        ib.batch_id,
        ib.filename,
        t.pay_date,
        ib.started_at
    FROM payroll.import_batches ib
    JOIN payroll.payroll_transactions t ON t.import_batch_id = ib.batch_id
    WHERE ib.status = 'completed'
),
matricules_par_batch AS (
    -- Pour chaque batch, liste des matricules actifs (montant ≠ 0)
    SELECT DISTINCT
        t.import_batch_id as batch_id,
        b.pay_date,
        b.filename,
        e.employee_id,
        e.matricule_norm,
        e.nom_norm,
        e.prenom_norm,
        -- Convertir matricule en entier (si numérique)
        CASE 
            WHEN e.matricule_norm ~ '^[0-9]+$' 
            THEN e.matricule_norm::INTEGER
            ELSE NULL
        END as matricule_int
    FROM payroll.payroll_transactions t
    JOIN core.employees e ON t.employee_id = e.employee_id
    JOIN batches_avec_date b ON b.batch_id = t.import_batch_id
    WHERE e.matricule_norm IS NOT NULL
    AND e.matricule_norm ~ '^[0-9]+$'  -- Seulement matricules numériques
    AND t.amount_cents <> 0             -- KPI: montants ≠ 0
),
max_par_batch AS (
    -- Matricule maximum par batch
    SELECT 
        batch_id,
        pay_date,
        filename,
        MAX(matricule_int) as max_matricule,
        COUNT(DISTINCT employee_id) as nb_employes
    FROM matricules_par_batch
    GROUP BY batch_id, pay_date, filename
),
batches_avec_precedent AS (
    -- Pour chaque batch, récupérer le max du batch précédent (ordre chronologique)
    SELECT 
        batch_id,
        pay_date,
        filename,
        max_matricule as max_actuel,
        nb_employes,
        LAG(max_matricule) OVER (ORDER BY pay_date) as max_precedent,
        LAG(pay_date) OVER (ORDER BY pay_date) as date_precedente
    FROM max_par_batch
)
-- Résultat final : employés avec indicateur nouveau/ancien
SELECT 
    mp.batch_id,
    mp.pay_date,
    mp.filename,
    mp.employee_id,
    mp.matricule_norm,
    mp.matricule_int,
    mp.nom_norm,
    mp.prenom_norm,
    bp.max_precedent,
    bp.max_actuel,
    bp.date_precedente,
    -- Nouveau si matricule > max_precedent (ou premier batch)
    CASE 
        WHEN mp.matricule_int > COALESCE(bp.max_precedent, 0) 
        THEN TRUE 
        ELSE FALSE 
    END as est_nouveau
FROM matricules_par_batch mp
JOIN batches_avec_precedent bp ON mp.batch_id = bp.batch_id
ORDER BY mp.pay_date DESC, mp.matricule_int ASC;

COMMENT ON VIEW payroll.v_nouveaux_par_batch IS 
'Détecte les nouveaux employés par fichier import (batch). Règle: nouveau = matricule > max(batch_precedent)';

-- ============================================================================
-- FONCTION: get_stats_nouveaux_date
-- ============================================================================

CREATE OR REPLACE FUNCTION payroll.get_stats_nouveaux_date(p_pay_date DATE)
RETURNS TABLE(
    batch_id INTEGER,
    pay_date DATE,
    filename VARCHAR(500),
    total_employes BIGINT,
    nouveaux_employes BIGINT,
    anciens_employes BIGINT,
    max_precedent INTEGER,
    max_actuel INTEGER,
    date_precedente DATE,
    liste_nouveaux VARCHAR(255)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        v.batch_id,
        v.pay_date,
        v.filename::VARCHAR(500),
        COUNT(DISTINCT v.employee_id)::BIGINT as total_employes,
        COUNT(DISTINCT v.employee_id) FILTER (WHERE v.est_nouveau = TRUE)::BIGINT as nouveaux,
        COUNT(DISTINCT v.employee_id) FILTER (WHERE v.est_nouveau = FALSE)::BIGINT as anciens,
        MAX(v.max_precedent) as max_prec,
        MAX(v.max_actuel) as max_act,
        MAX(v.date_precedente) as date_prec,
        STRING_AGG(
            DISTINCT v.matricule_norm, ', ' 
            ORDER BY v.matricule_norm
        ) FILTER (WHERE v.est_nouveau = TRUE)::VARCHAR(255) as liste_nouveaux
    FROM payroll.v_nouveaux_par_batch v
    WHERE v.pay_date = p_pay_date
    GROUP BY v.batch_id, v.pay_date, v.filename;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION payroll.get_stats_nouveaux_date IS 
'Retourne les statistiques nouveaux/anciens employés pour une date de paie donnée';

-- ============================================================================
-- PERMISSIONS
-- ============================================================================

GRANT SELECT ON payroll.v_nouveaux_par_batch TO payroll_app;
GRANT EXECUTE ON FUNCTION payroll.get_stats_nouveaux_date(DATE) TO payroll_app;

-- ============================================================================
-- TESTS RAPIDES
-- ============================================================================

DO $$
DECLARE
    v_test_date DATE;
    v_count INTEGER;
BEGIN
    -- Vérifier que la vue retourne des données
    SELECT COUNT(*) INTO v_count FROM payroll.v_nouveaux_par_batch;
    RAISE NOTICE '✓ Vue v_nouveaux_par_batch: % lignes', v_count;
    
    -- Tester la fonction sur la dernière date disponible
    SELECT MAX(pay_date) INTO v_test_date FROM payroll.v_nouveaux_par_batch;
    IF v_test_date IS NOT NULL THEN
        RAISE NOTICE '✓ Fonction testée sur date: %', v_test_date;
        PERFORM * FROM payroll.get_stats_nouveaux_date(v_test_date);
        RAISE NOTICE '✓ Fonction get_stats_nouveaux_date OK';
    END IF;
END $$;

