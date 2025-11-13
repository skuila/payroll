-- Script pour corriger les types de colonnes de montants
-- À exécuter avec un superuser (postgres)

-- Vérifier les types actuels
SELECT 
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'payroll'
  AND table_name = 'imported_payroll_master'
  AND column_name IN ('montant_employe', 'part_employeur', 'montant_combine')
ORDER BY column_name;

-- Convertir en NUMERIC si nécessaire
-- (Décommenter les lignes nécessaires)

-- ALTER TABLE payroll.imported_payroll_master 
--   ALTER COLUMN montant_employe TYPE NUMERIC(18,2) 
--   USING CASE 
--     WHEN montant_employe ~ '^[-]?[0-9]+\.?[0-9]*$' 
--     THEN montant_employe::numeric(18,2)
--     ELSE 0
--   END;

-- ALTER TABLE payroll.imported_payroll_master 
--   ALTER COLUMN part_employeur TYPE NUMERIC(18,2) 
--   USING CASE 
--     WHEN part_employeur ~ '^[-]?[0-9]+\.?[0-9]*$' 
--     THEN part_employeur::numeric(18,2)
--     ELSE 0
--   END;

-- ALTER TABLE payroll.imported_payroll_master 
--   ALTER COLUMN montant_combine TYPE NUMERIC(18,2) 
--   USING CASE 
--     WHEN montant_combine ~ '^[-]?[0-9]+\.?[0-9]*$' 
--     THEN montant_combine::numeric(18,2)
--     ELSE 0
--   END;

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
