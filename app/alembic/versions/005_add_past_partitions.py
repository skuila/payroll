"""Add past partitions for historical payroll data (pre-2005)

Revision ID: 005
Revises: 004
Create Date: 2025-10-10 18:00:00.000000

Objectif: Permettre l'import de paies antérieures à 2005 (ex. 1950-2004)
sans perte de performance ni de contraintes.

Solution: Créer des partitions DEFAULT ou "past" pour capturer
les dates < 2005-01-01.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Ajouter partitions pour données historiques antérieures à 2005."""

    # ========================
    # DIAGNOSTIC: Vérifier l'état actuel
    # ========================
    # La partition "payroll_transactions_future" existe déjà comme DEFAULT (Migration 002)
    # Pour pay_periods, nous devons vérifier si elle est partitionnée

    # ========================
    # 1) PAYROLL.PAY_PERIODS - Vérifier si partitionnée
    # ========================

    # pay_periods n'est PAS partitionnée dans les migrations 001-004
    # Elle est une table simple avec index sur pay_date
    # Donc pas besoin de partition "past" pour pay_periods

    # ========================
    # 2) PAYROLL.PAYROLL_TRANSACTIONS - Ajouter partition PAST
    # ========================

    # Stratégie: Créer une partition pour 1950-2004 (55 ans d'historique)
    # La partition "future" (DEFAULT) capte déjà >= 2026
    # On crée "past" pour < 2005

    op.execute(
        """
        DO $$
        DECLARE
            partition_exists BOOLEAN;
        BEGIN
            -- Vérifier si la partition past existe déjà
            SELECT EXISTS (
                SELECT 1 FROM pg_class c
                JOIN pg_namespace n ON c.relnamespace = n.oid
                WHERE n.nspname = 'payroll' 
                AND c.relname = 'payroll_transactions_past'
            ) INTO partition_exists;
            
            IF partition_exists THEN
                RAISE NOTICE 'Partition payroll_transactions_past existe déjà, skip';
            ELSE
                RAISE NOTICE 'Création partition payroll_transactions_past pour dates 1950-01-01 à 2004-12-31';
                
                -- Créer la partition pour l'historique 1950-2004
                CREATE TABLE payroll.payroll_transactions_past
                PARTITION OF payroll.payroll_transactions
                FOR VALUES FROM ('1950-01-01') TO ('2005-01-01');
                
                RAISE NOTICE 'Partition payroll_transactions_past créée avec succès';
            END IF;
        END $$;
    """
    )

    # ========================
    # 3) INDEX BRIN sur partition PAST
    # ========================

    op.execute(
        """
        DO $$
        DECLARE
            index_exists BOOLEAN;
        BEGIN
            -- Vérifier si l'index BRIN existe déjà
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'payroll'
                AND tablename = 'payroll_transactions_past'
                AND indexname = 'idx_payroll_transactions_past_pay_date_brin'
            ) INTO index_exists;
            
            IF index_exists THEN
                RAISE NOTICE 'Index BRIN sur payroll_transactions_past existe déjà, skip';
            ELSE
                RAISE NOTICE 'Création index BRIN sur payroll_transactions_past.pay_date';
                
                CREATE INDEX idx_payroll_transactions_past_pay_date_brin
                ON payroll.payroll_transactions_past
                USING BRIN (pay_date) WITH (pages_per_range = 128);
                
                RAISE NOTICE 'Index BRIN créé avec succès';
            END IF;
        END $$;
    """
    )

    # ========================
    # 4) INDEX B-Tree sur partition PAST pour période_id (FK)
    # ========================

    op.execute(
        """
        DO $$
        DECLARE
            index_exists BOOLEAN;
        BEGIN
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'payroll'
                AND tablename = 'payroll_transactions_past'
                AND indexname = 'idx_payroll_transactions_past_period_id'
            ) INTO index_exists;
            
            IF index_exists THEN
                RAISE NOTICE 'Index B-Tree sur payroll_transactions_past.period_id existe déjà, skip';
            ELSE
                RAISE NOTICE 'Création index B-Tree sur payroll_transactions_past.period_id';
                
                CREATE INDEX idx_payroll_transactions_past_period_id
                ON payroll.payroll_transactions_past (period_id);
                
                RAISE NOTICE 'Index B-Tree créé avec succès';
            END IF;
        END $$;
    """
    )

    # ========================
    # 5) INDEX B-Tree sur partition PAST pour employee_id (FK)
    # ========================

    op.execute(
        """
        DO $$
        DECLARE
            index_exists BOOLEAN;
        BEGIN
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'payroll'
                AND tablename = 'payroll_transactions_past'
                AND indexname = 'idx_payroll_transactions_past_employee_id'
            ) INTO index_exists;
            
            IF index_exists THEN
                RAISE NOTICE 'Index B-Tree sur payroll_transactions_past.employee_id existe déjà, skip';
            ELSE
                RAISE NOTICE 'Création index B-Tree sur payroll_transactions_past.employee_id';
                
                CREATE INDEX idx_payroll_transactions_past_employee_id
                ON payroll.payroll_transactions_past (employee_id);
                
                RAISE NOTICE 'Index B-Tree créé avec succès';
            END IF;
        END $$;
    """
    )


def downgrade() -> None:
    """Supprimer les partitions past (si nécessaire pour rollback)."""

    # Supprimer les index d'abord
    op.execute(
        """
        DROP INDEX IF EXISTS payroll.idx_payroll_transactions_past_employee_id;
        DROP INDEX IF EXISTS payroll.idx_payroll_transactions_past_period_id;
        DROP INDEX IF EXISTS payroll.idx_payroll_transactions_past_pay_date_brin;
    """
    )

    # Supprimer la partition
    op.execute(
        """
        DROP TABLE IF EXISTS payroll.payroll_transactions_past;
    """
    )
