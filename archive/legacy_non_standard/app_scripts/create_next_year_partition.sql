-- ========================================
-- Script: Création automatique des partitions N+1
-- Usage: À exécuter annuellement (ex: 1er décembre)
--        via cron ou pgAgent
-- ========================================

-- Variables (à adapter selon l'année courante)
-- Exemple pour créer les partitions de 2026 (exécuté en décembre 2025)

DO $$
DECLARE
    next_year INT := EXTRACT(YEAR FROM CURRENT_DATE) + 1;
    partition_name TEXT;
    start_date TEXT;
    end_date TEXT;
    month_partition TEXT;
    month_start TEXT;
    month_end TEXT;
    i INT;
BEGIN
    -- ========================================
    -- 1) PAYROLL.PAYROLL_TRANSACTIONS
    --    Créer partition annuelle N+1
    -- ========================================
    
    partition_name := 'payroll_transactions_' || next_year;
    start_date := next_year || '-01-01';
    end_date := (next_year + 1) || '-01-01';
    
    -- Vérifier si partition existe déjà
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables
        WHERE schemaname = 'payroll'
        AND tablename = partition_name
    ) THEN
        EXECUTE format(
            'CREATE TABLE payroll.%I PARTITION OF payroll.payroll_transactions FOR VALUES FROM (%L) TO (%L);',
            partition_name,
            start_date,
            end_date
        );
        RAISE NOTICE 'Partition % créée avec succès.', partition_name;
    ELSE
        RAISE NOTICE 'Partition % existe déjà.', partition_name;
    END IF;
    
    -- ========================================
    -- 2) SECURITY.AUDIT_LOGS
    --    Créer 12 partitions mensuelles pour N+1
    -- ========================================
    
    FOR i IN 1..12 LOOP
        month_partition := 'audit_logs_' || next_year || '_' || LPAD(i::TEXT, 2, '0');
        month_start := next_year || '-' || LPAD(i::TEXT, 2, '0') || '-01';
        
        -- Calculer le premier jour du mois suivant
        IF i = 12 THEN
            month_end := (next_year + 1) || '-01-01';
        ELSE
            month_end := next_year || '-' || LPAD((i + 1)::TEXT, 2, '0') || '-01';
        END IF;
        
        -- Vérifier si partition existe déjà
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = 'security'
            AND tablename = month_partition
        ) THEN
            EXECUTE format(
                'CREATE TABLE security.%I PARTITION OF security.audit_logs FOR VALUES FROM (%L) TO (%L);',
                month_partition,
                month_start,
                month_end
            );
            RAISE NOTICE 'Partition % créée avec succès.', month_partition;
        ELSE
            RAISE NOTICE 'Partition % existe déjà.', month_partition;
        END IF;
    END LOOP;
    
    RAISE NOTICE 'Création des partitions pour % terminée.', next_year;
    
END $$;

-- ========================================
-- NOTES D'UTILISATION
-- ========================================

-- 1. Planification annuelle (pgAgent ou cron):
--    psql -U payroll_user -d payroll_db -f /path/to/create_next_year_partition.sql

-- 2. Vérifier les partitions créées:
--    SELECT tablename FROM pg_tables WHERE schemaname IN ('payroll', 'security') AND tablename LIKE '%2026%' ORDER BY tablename;

-- 3. En cas d'erreur, vérifier les logs PostgreSQL

-- 4. Après création, mettre à jour la partition DEFAULT si nécessaire (optionnel)
--    -- DROP TABLE payroll.payroll_transactions_future;
--    -- CREATE TABLE payroll.payroll_transactions_future PARTITION OF payroll.payroll_transactions DEFAULT;

