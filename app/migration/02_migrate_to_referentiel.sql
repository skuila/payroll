-- ============================================================================
-- MIGRATION: Données historiques → Référentiel Employés
-- PostgreSQL 17
-- Version: 1.0
-- Date: 2025-10-16
-- ============================================================================

-- Configuration
SET client_min_messages TO INFO;
SET search_path TO payroll, core, reference, public;

-- Variables pour statistiques
DO $$
DECLARE
    v_batch_id INTEGER;
    v_staging_count INTEGER;
    v_employees_count INTEGER;
    v_transactions_count INTEGER;
    v_orphan_count INTEGER;
    v_total_amount_new NUMERIC;
    v_total_amount_old NUMERIC;
BEGIN
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'MIGRATION VERS RÉFÉRENTIEL EMPLOYÉS - Démarrage';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '';
    
    -- ========================================================================
    -- PHASE 1: CRÉER BATCH D'IMPORT
    -- ========================================================================
    
    RAISE NOTICE 'Phase 1: Création batch import...';
    
    INSERT INTO payroll.import_batches (
        filename, 
        file_checksum, 
        status
    ) VALUES (
        'MIGRATION_INITIALE_' || TO_CHAR(CURRENT_TIMESTAMP, 'YYYYMMDD_HH24MISS'),
        MD5('migration_initiale_' || CURRENT_TIMESTAMP::text),
        'processing'
    )
    RETURNING batch_id INTO v_batch_id;
    
    RAISE NOTICE '  ✓ Batch %  créé', v_batch_id;
    RAISE NOTICE '';
    
    -- ========================================================================
    -- PHASE 2: CHARGER STAGING AVEC NORMALISATION
    -- ========================================================================
    
    RAISE NOTICE 'Phase 2: Chargement staging avec normalisation...';
    
    INSERT INTO payroll.stg_imported_payroll (
        matricule_raw,
        employe_raw,
        date_paie_raw,
        categorie_paie_raw,
        montant_raw,
        matricule_clean,
        nom_norm,
        prenom_norm,
        employee_key,
        pay_date,
        pay_code,
        amount_cents,
        import_batch_id,
        source_row_no
    )
    SELECT
        -- Données brutes
        ipm."matricule "::text,
        ipm."employé "::text,
        ipm."date de paie "::text,
        ipm."categorie de paie "::text,
        ipm."montant "::text,
        
        -- Matricule nettoyé
        NULLIF(
            CASE WHEN BTRIM(regexp_replace(ipm."matricule "::text, '[^0-9A-Za-z\-]', '', 'g')) ~ '^[0-9]+$'
                 THEN regexp_replace(
                        BTRIM(regexp_replace(ipm."matricule "::text, '[^0-9A-Za-z\-]', '', 'g')),
                        '^0+', ''
                      )
                 ELSE BTRIM(regexp_replace(ipm."matricule "::text, '[^0-9A-Za-z\-]', '', 'g'))
            END, ''
        ),
        
        -- Nom normalisé
        BTRIM(
            regexp_replace(
                unaccent(LOWER(SPLIT_PART(ipm."employé "::text, ',', 1))),
                '\s+', ' ', 'g'
            )
        ),
        
        -- Prénom normalisé
        NULLIF(
            BTRIM(
                regexp_replace(
                    unaccent(LOWER(SPLIT_PART(ipm."employé "::text, ',', 2))),
                    '\s+', ' ', 'g'
                )
            ), ''
        ),
        
        -- employee_key via fonction
        core.compute_employee_key(
            ipm."matricule "::text,
            ipm."employé "::text
        ),
        
        -- Date paie
        ipm."date de paie "::date,
        
        -- Code paie (normaliser)
        COALESCE(
            NULLIF(BTRIM(ipm."categorie de paie "::text), ''),
            'NON_SPECIFIE'
        ),
        
        -- Montant en cents
        ROUND(COALESCE(ipm."montant ", 0) * 100)::BIGINT,
        
        -- Traçabilité
        v_batch_id,
        ROW_NUMBER() OVER ()
        
    FROM payroll.imported_payroll_master ipm
    WHERE COALESCE(ipm."montant ", 0) <> 0;  -- Exclure montants = 0
    
    GET DIAGNOSTICS v_staging_count = ROW_COUNT;
    RAISE NOTICE '  ✓ Staging: % lignes chargées (montants ≠ 0)', v_staging_count;
    RAISE NOTICE '';
    
    -- ========================================================================
    -- PHASE 3: EXTRAIRE EMPLOYÉS UNIQUES
    -- ========================================================================
    
    RAISE NOTICE 'Phase 3: Extraction employés uniques...';
    
    INSERT INTO core.employees (
        employee_key,
        matricule_norm,
        matricule_raw,
        nom_norm,
        prenom_norm,
        nom_complet,
        statut,
        source_system
    )
    SELECT DISTINCT ON (employee_key)
        employee_key,
        matricule_clean,
        matricule_raw,
        nom_norm,
        prenom_norm,
        employe_raw,
        'actif',
        'migration_initiale'
    FROM payroll.stg_imported_payroll
    WHERE employee_key IS NOT NULL
    ORDER BY employee_key, source_row_no ASC
    ON CONFLICT (employee_key) DO NOTHING;
    
    GET DIAGNOSTICS v_employees_count = ROW_COUNT;
    RAISE NOTICE '  ✓ Employés: % insérés (dédupliqués)', v_employees_count;
    RAISE NOTICE '';
    
    -- ========================================================================
    -- PHASE 4: INSÉRER TRANSACTIONS
    -- ========================================================================
    
    RAISE NOTICE 'Phase 4: Insertion transactions...';
    
    INSERT INTO payroll.payroll_transactions (
        employee_id,
        pay_date,
        period_seq_in_year,
        pay_code,
        amount_cents,
        import_batch_id,
        source_file,
        source_row_no
    )
    SELECT
        e.employee_id,
        s.pay_date,
        DENSE_RANK() OVER (
            PARTITION BY EXTRACT(YEAR FROM s.pay_date)
            ORDER BY s.pay_date
        ),
        s.pay_code,
        s.amount_cents,
        s.import_batch_id,
        'imported_payroll_master',
        s.source_row_no
    FROM payroll.stg_imported_payroll s
    JOIN core.employees e ON s.employee_key = e.employee_key
    WHERE s.amount_cents <> 0;  -- Double sécurité
    
    GET DIAGNOSTICS v_transactions_count = ROW_COUNT;
    RAISE NOTICE '  ✓ Transactions: % insérées', v_transactions_count;
    RAISE NOTICE '';
    
    -- ========================================================================
    -- PHASE 5: VÉRIFICATIONS
    -- ========================================================================
    
    RAISE NOTICE 'Phase 5: Vérifications...';
    
    -- Orphelins
    SELECT COUNT(*) INTO v_orphan_count
    FROM payroll.stg_imported_payroll s
    LEFT JOIN core.employees e ON s.employee_key = e.employee_key
    WHERE e.employee_id IS NULL;
    
    IF v_orphan_count > 0 THEN
        RAISE WARNING '  ⚠️  % lignes staging orphelines détectées!', v_orphan_count;
    ELSE
        RAISE NOTICE '  ✓ Pas d''orphelins';
    END IF;
    
    -- Cohérence montants
    SELECT 
        ROUND(SUM(amount_cents)::NUMERIC / 100, 2) INTO v_total_amount_new
    FROM payroll.payroll_transactions;
    
    SELECT 
        ROUND(SUM(COALESCE("montant ", 0))::NUMERIC, 2) INTO v_total_amount_old
    FROM payroll.imported_payroll_master
    WHERE COALESCE("montant ", 0) <> 0;
    
    IF ABS(v_total_amount_new - v_total_amount_old) > 1 THEN
        RAISE WARNING '  ⚠️  Écart montants: Ancien=%, Nouveau=%', 
                      v_total_amount_old, v_total_amount_new;
    ELSE
        RAISE NOTICE '  ✓ Montants cohérents (écart < 1$)';
    END IF;
    
    RAISE NOTICE '';
    
    -- ========================================================================
    -- PHASE 6: FINALISER BATCH
    -- ========================================================================
    
    RAISE NOTICE 'Phase 6: Finalisation batch...';
    
    UPDATE payroll.import_batches
    SET 
        status = 'completed',
        total_rows = v_staging_count,
        valid_rows = v_transactions_count,
        invalid_rows = v_orphan_count,
        new_employees = v_employees_count,
        new_transactions = v_transactions_count,
        completed_at = CURRENT_TIMESTAMP
    WHERE batch_id = v_batch_id;
    
    RAISE NOTICE '  ✓ Batch % finalisé', v_batch_id;
    RAISE NOTICE '';
    
    -- ========================================================================
    -- PHASE 7: ANALYSER TABLES (Optimisation)
    -- ========================================================================
    
    RAISE NOTICE 'Phase 7: Analyse tables...';
    
    ANALYZE core.employees;
    ANALYZE payroll.payroll_transactions;
    ANALYZE payroll.stg_imported_payroll;
    
    RAISE NOTICE '  ✓ ANALYZE exécuté';
    RAISE NOTICE '';
    
    -- ========================================================================
    -- RÉSUMÉ
    -- ========================================================================
    
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'MIGRATION TERMINÉE AVEC SUCCÈS';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Batch ID         : %', v_batch_id;
    RAISE NOTICE 'Staging          : % lignes', v_staging_count;
    RAISE NOTICE 'Employés         : % uniques insérés', v_employees_count;
    RAISE NOTICE 'Transactions     : % insérées', v_transactions_count;
    RAISE NOTICE 'Orphelins        : %', v_orphan_count;
    RAISE NOTICE 'Montant total    : % $', v_total_amount_new;
    RAISE NOTICE '============================================================================';
    
END $$;

