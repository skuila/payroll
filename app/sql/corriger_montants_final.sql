-- Script pour corriger les types de montants en NUMERIC
-- À exécuter avec un superuser (postgres)
-- 
-- Usage: psql -U postgres -d payroll_db -f corriger_montants_final.sql

BEGIN;

-- Vérifier les types actuels
SELECT 
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'payroll'
  AND table_name = 'imported_payroll_master'
  AND column_name IN ('montant_employe', 'part_employeur', 'montant_combine')
ORDER BY column_name;

-- Convertir part_employeur en NUMERIC
ALTER TABLE payroll.imported_payroll_master
  ALTER COLUMN part_employeur TYPE NUMERIC(18,2)
  USING CASE
    WHEN part_employeur ~ '^[-]?[0-9]+\.?[0-9]*$'
    THEN part_employeur::numeric(18,2)
    ELSE 0
  END;

-- Convertir montant_combine en NUMERIC
ALTER TABLE payroll.imported_payroll_master
  ALTER COLUMN montant_combine TYPE NUMERIC(18,2)
  USING CASE
    WHEN montant_combine ~ '^[-]?[0-9]+\.?[0-9]*$'
    THEN montant_combine::numeric(18,2)
    ELSE 0
  END;

-- Vérification après correction
SELECT 
    column_name,
    data_type,
    numeric_precision,
    numeric_scale
FROM information_schema.columns
WHERE table_schema = 'payroll'
  AND table_name = 'imported_payroll_master'
  AND column_name IN ('montant_employe', 'part_employeur', 'montant_combine')
ORDER BY column_name;

COMMIT;

-- Résultat attendu:
-- montant_employe: NUMERIC(18,2) ✅
-- part_employeur: NUMERIC(18,2) ✅
-- montant_combine: NUMERIC(18,2) ✅









