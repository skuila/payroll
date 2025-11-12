-- ========================================
-- Création partition PostgreSQL 1900-1949
-- Pour supporter les données historiques
-- ========================================

-- Table partitionnée pour dates 1900-1949
CREATE TABLE IF NOT EXISTS payroll.payroll_transactions_very_past 
PARTITION OF payroll.payroll_transactions 
FOR VALUES FROM ('1900-01-01') TO ('1950-01-01');

-- Index BRIN pour performance (adapté aux partitions par date)
CREATE INDEX IF NOT EXISTS idx_payroll_transactions_very_past_pay_date_brin 
ON payroll.payroll_transactions_very_past 
USING BRIN (pay_date);

-- Index BTREE pour recherches employé+date
CREATE INDEX IF NOT EXISTS idx_payroll_transactions_very_past_employee_date 
ON payroll.payroll_transactions_very_past 
USING BTREE (employee_id, pay_date);

-- Vérification
SELECT 
    'Partition 1900-1949 créée avec succès' as message,
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as taille
FROM pg_tables 
WHERE tablename = 'payroll_transactions_very_past';

-- Lister toutes les partitions
SELECT 
    c.relname as partition_name,
    pg_get_expr(c.relpartbound, c.oid) as partition_range
FROM pg_class c
JOIN pg_inherits i ON c.oid = i.inhrelid
JOIN pg_class p ON i.inhparent = p.oid
WHERE p.relname = 'payroll_transactions'
ORDER BY c.relname;
