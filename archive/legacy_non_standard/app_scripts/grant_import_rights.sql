-- Script pour accorder les droits nécessaires à payroll_unified

-- Droits sur pay_periods
GRANT INSERT, UPDATE, DELETE ON payroll.pay_periods TO payroll_unified;

-- Droits sur import_batches
GRANT INSERT, UPDATE, DELETE ON payroll.import_batches TO payroll_unified;

-- Droits sur imported_payroll_master
GRANT INSERT, UPDATE, DELETE ON payroll.imported_payroll_master TO payroll_unified;

-- Droits sur les autres tables payroll
GRANT INSERT, UPDATE, DELETE ON payroll.payroll_transactions TO payroll_unified;

-- Droits sur les séquences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA payroll TO payroll_unified;

-- Droits sur core (pour upsert employees, pay_codes, budget_posts)
GRANT INSERT, UPDATE ON core.employees TO payroll_unified;
GRANT INSERT, UPDATE ON core.pay_codes TO payroll_unified;
GRANT INSERT, UPDATE ON core.budget_posts TO payroll_unified;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA core TO payroll_unified;
