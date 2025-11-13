
-- Corriger montant_combine
ALTER TABLE payroll.imported_payroll_master
  ALTER COLUMN montant_combine TYPE NUMERIC(18,2)
  USING CASE
    WHEN montant_combine ~ '^[-]?[0-9]+\.?[0-9]*$'
    THEN montant_combine::numeric(18,2)
    ELSE 0
  END;

-- Corriger part_employeur
ALTER TABLE payroll.imported_payroll_master
  ALTER COLUMN part_employeur TYPE NUMERIC(18,2)
  USING CASE
    WHEN part_employeur ~ '^[-]?[0-9]+\.?[0-9]*$'
    THEN part_employeur::numeric(18,2)
    ELSE 0
  END;
