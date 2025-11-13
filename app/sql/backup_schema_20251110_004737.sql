
-- Script de sauvegarde du schéma - Généré le 2025-11-10T00:47:37.409332
-- Fichier: backup_schema_20251110_004737.sql

-- Connexion à la base payroll_db
\c payroll_db

-- Schéma core (dimension employés)
\dn core
\dt core.*
\d core.employees

-- Schéma payroll (fait transactions)
\dn payroll
\dt payroll.*
\d payroll.payroll_transactions
\d payroll.pay_periods
\d payroll.import_batches

-- Comptage des enregistrements
SELECT 'core.employees' as table_name, COUNT(*) as count FROM core.employees
UNION ALL
SELECT 'payroll.payroll_transactions', COUNT(*) FROM payroll.payroll_transactions
UNION ALL
SELECT 'payroll.pay_periods', COUNT(*) FROM payroll.pay_periods;

-- Fin du script de sauvegarde
