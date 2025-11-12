-- Corriger les permissions sur payroll.kpi_snapshot

-- Donner tous les droits à payroll_app sur kpi_snapshot
GRANT SELECT, INSERT, UPDATE, DELETE ON payroll.kpi_snapshot TO payroll_app;

-- Donner SELECT à payroll_ro
GRANT SELECT ON payroll.kpi_snapshot TO payroll_ro;

-- Vérifier les permissions
\dp payroll.kpi_snapshot

