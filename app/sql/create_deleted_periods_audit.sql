-- Table d'audit pour tracer les périodes supprimées
-- Cette table garde une trace de toutes les périodes qui ont été supprimées

CREATE TABLE IF NOT EXISTS payroll.deleted_periods_audit (
    audit_id SERIAL PRIMARY KEY,
    period_id UUID NOT NULL,
    pay_date DATE NOT NULL,
    pay_year INTEGER NOT NULL,
    pay_month INTEGER NOT NULL,
    status VARCHAR(50),
    transactions_count INTEGER DEFAULT 0,
    deleted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_by VARCHAR(100),
    notes TEXT,
    CONSTRAINT deleted_periods_audit_unique UNIQUE (period_id, deleted_at)
);

-- Index pour rechercher rapidement
CREATE INDEX IF NOT EXISTS idx_deleted_periods_pay_date 
    ON payroll.deleted_periods_audit(pay_date);

CREATE INDEX IF NOT EXISTS idx_deleted_periods_deleted_at 
    ON payroll.deleted_periods_audit(deleted_at DESC);

-- Commentaires
COMMENT ON TABLE payroll.deleted_periods_audit IS 
    'Historique des périodes de paie supprimées pour traçabilité';

COMMENT ON COLUMN payroll.deleted_periods_audit.period_id IS 
    'UUID de la période supprimée';

COMMENT ON COLUMN payroll.deleted_periods_audit.transactions_count IS 
    'Nombre de transactions qui ont été supprimées avec cette période';

COMMENT ON COLUMN payroll.deleted_periods_audit.deleted_at IS 
    'Date et heure de la suppression';

COMMENT ON COLUMN payroll.deleted_periods_audit.deleted_by IS 
    'Utilisateur qui a effectué la suppression';

-- Afficher un message de confirmation
SELECT 'Table deleted_periods_audit créée avec succès' AS message;

