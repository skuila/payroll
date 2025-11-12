"""Schema corrections: MV monthly, CHECK constraints, triggers, roles_permissions

Revision ID: 003
Revises: 002
Create Date: 2025-10-09 16:00:00.000000

Corrections appliquées:
1. v_monthly_payroll_summary: regrouper par pay_year/pay_month au lieu de pay_date
2. pay_periods: CHECK constraints sur pay_day, pay_month, period_seq_in_year + trigger cohérence
3. payroll_transactions: trigger BEFORE INSERT/UPDATE pour cohérence pay_date/period_id
4. amount_employer_norm_cents: CHECK >= 0
5. import_batches: FK period_id au lieu de pay_date
6. security.roles_permissions: nouvelle table pour RBAC granulaire
7. employee_job_history: EXCLUDE constraint pour empêcher chevauchements dates
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply schema corrections."""

    # ========================
    # 1. RE-CRÉER v_monthly_payroll_summary (par pay_year/pay_month)
    # ========================

    # Drop ancienne vue
    op.execute(
        "DROP MATERIALIZED VIEW IF EXISTS payroll.v_monthly_payroll_summary CASCADE;"
    )

    # Recréer avec regroupement par pay_year/pay_month
    op.execute(
        """
        CREATE MATERIALIZED VIEW payroll.v_monthly_payroll_summary AS
        SELECT
            pp.pay_year,
            pp.pay_month,
            e.employee_id,
            e.matricule,
            e.nom,
            e.prenom,
            SUM(pt.amount_employee_norm_cents) / 100.0 AS total_employee_amount,
            SUM(pt.amount_employer_norm_cents) / 100.0 AS total_employer_amount,
            SUM(pt.amount_employee_norm_cents + pt.amount_employer_norm_cents) / 100.0 AS total_combined_amount,
            COUNT(*) AS transaction_count
        FROM payroll.payroll_transactions pt
        JOIN core.employees e ON pt.employee_id = e.employee_id
        JOIN payroll.pay_periods pp ON pt.period_id = pp.period_id
        GROUP BY pp.pay_year, pp.pay_month, e.employee_id, e.matricule, e.nom, e.prenom
        WITH DATA;
    """
    )

    # Créer index UNIQUE (pay_year, pay_month, employee_id) pour CONCURRENTLY refresh
    op.create_index(
        "idx_v_monthly_summary_pk",
        "v_monthly_payroll_summary",
        ["pay_year", "pay_month", "employee_id"],
        unique=True,
        schema="payroll",
    )

    # Index supplémentaires
    op.create_index(
        "idx_v_monthly_summary_year_month",
        "v_monthly_payroll_summary",
        ["pay_year", "pay_month"],
        schema="payroll",
    )
    op.create_index(
        "idx_v_monthly_summary_employee",
        "v_monthly_payroll_summary",
        ["employee_id"],
        schema="payroll",
    )

    # ========================
    # 2. pay_periods: CHECK constraints
    # ========================

    op.execute(
        """
        ALTER TABLE payroll.pay_periods
        ADD CONSTRAINT ck_pay_periods_pay_day CHECK (pay_day >= 1 AND pay_day <= 31);
    """
    )

    op.execute(
        """
        ALTER TABLE payroll.pay_periods
        ADD CONSTRAINT ck_pay_periods_pay_month CHECK (pay_month >= 1 AND pay_month <= 12);
    """
    )

    op.execute(
        """
        ALTER TABLE payroll.pay_periods
        ADD CONSTRAINT ck_pay_periods_period_seq CHECK (period_seq_in_year >= 1 AND period_seq_in_year <= 53);
    """
    )

    # Trigger pour cohérence pay_date <-> (pay_day, pay_month, pay_year)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION payroll.check_pay_date_consistency()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Extraire composantes de pay_date
            IF EXTRACT(DAY FROM NEW.pay_date) != NEW.pay_day THEN
                RAISE EXCEPTION 'pay_day (%) ne correspond pas à pay_date (%) [jour=%]',
                    NEW.pay_day, NEW.pay_date, EXTRACT(DAY FROM NEW.pay_date);
            END IF;
            
            IF EXTRACT(MONTH FROM NEW.pay_date) != NEW.pay_month THEN
                RAISE EXCEPTION 'pay_month (%) ne correspond pas à pay_date (%) [mois=%]',
                    NEW.pay_month, NEW.pay_date, EXTRACT(MONTH FROM NEW.pay_date);
            END IF;
            
            IF EXTRACT(YEAR FROM NEW.pay_date) != NEW.pay_year THEN
                RAISE EXCEPTION 'pay_year (%) ne correspond pas à pay_date (%) [année=%]',
                    NEW.pay_year, NEW.pay_date, EXTRACT(YEAR FROM NEW.pay_date);
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    op.execute(
        """
        CREATE TRIGGER trg_pay_periods_date_consistency
        BEFORE INSERT OR UPDATE OF pay_date, pay_day, pay_month, pay_year
        ON payroll.pay_periods
        FOR EACH ROW
        EXECUTE FUNCTION payroll.check_pay_date_consistency();
    """
    )

    # ========================
    # 3. payroll_transactions: trigger cohérence pay_date/period_id
    # ========================

    op.execute(
        """
        CREATE OR REPLACE FUNCTION payroll.check_transaction_pay_date()
        RETURNS TRIGGER AS $$
        DECLARE
            period_pay_date DATE;
        BEGIN
            -- Récupérer pay_date de la période
            SELECT pay_date INTO period_pay_date
            FROM payroll.pay_periods
            WHERE period_id = NEW.period_id;
            
            IF NOT FOUND THEN
                RAISE EXCEPTION 'period_id % inexistant dans pay_periods', NEW.period_id;
            END IF;
            
            -- Vérifier cohérence
            IF NEW.pay_date != period_pay_date THEN
                RAISE EXCEPTION 'pay_date transaction (%) diffère de pay_date période (%) pour period_id=%',
                    NEW.pay_date, period_pay_date, NEW.period_id;
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    op.execute(
        """
        CREATE TRIGGER trg_payroll_transactions_pay_date_check
        BEFORE INSERT OR UPDATE OF pay_date, period_id
        ON payroll.payroll_transactions
        FOR EACH ROW
        EXECUTE FUNCTION payroll.check_transaction_pay_date();
    """
    )

    # ========================
    # 4. amount_employer_norm_cents: CHECK >= 0
    # ========================

    op.execute(
        """
        ALTER TABLE payroll.payroll_transactions
        ADD CONSTRAINT ck_payroll_amount_employer_positive
        CHECK (amount_employer_norm_cents >= 0);
    """
    )

    # ========================
    # 5. import_batches: remplacer pay_date par period_id (FK)
    # ========================

    # Ajouter colonne period_id
    op.add_column(
        "import_batches",
        sa.Column(
            "period_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True
        ),
        schema="payroll",
    )

    # Remplir period_id depuis pay_date existant (migration données)
    op.execute(
        """
        UPDATE payroll.import_batches ib
        SET period_id = (
            SELECT period_id FROM payroll.pay_periods pp
            WHERE pp.pay_date = ib.pay_date
            LIMIT 1
        );
    """
    )

    # Rendre period_id NOT NULL
    op.alter_column("import_batches", "period_id", nullable=False, schema="payroll")

    # Ajouter FK period_id -> pay_periods
    op.create_foreign_key(
        "fk_import_batches_period",
        "import_batches",
        "pay_periods",
        ["period_id"],
        ["period_id"],
        source_schema="payroll",
        referent_schema="payroll",
    )

    # Remplacer contrainte UNIQUE (pay_date, checksum) par (period_id, checksum)
    op.drop_constraint("uq_import_date_checksum", "import_batches", schema="payroll")
    op.create_unique_constraint(
        "uq_import_period_checksum",
        "import_batches",
        ["period_id", "checksum"],
        schema="payroll",
    )

    # Mettre à jour index
    op.drop_index(
        "idx_import_batches_pay_date", table_name="import_batches", schema="payroll"
    )
    op.create_index(
        "idx_import_batches_period", "import_batches", ["period_id"], schema="payroll"
    )

    # Note: on garde pay_date comme colonne (dénormalisée) pour traçabilité / affichage rapide
    # Mais la FK et UNIQUE sont sur period_id

    # ========================
    # 6. security.roles_permissions: nouvelle table RBAC
    # ========================

    op.create_table(
        "roles_permissions",
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("table_name", sa.String(100), nullable=False),
        sa.Column("can_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("can_write", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("can_delete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("role", "table_name"),
        schema="security",
    )

    op.create_index(
        "idx_roles_permissions_role", "roles_permissions", ["role"], schema="security"
    )
    op.create_index(
        "idx_roles_permissions_table",
        "roles_permissions",
        ["table_name"],
        schema="security",
    )

    # Insérer permissions par défaut (exemples)
    op.execute(
        """
        INSERT INTO security.roles_permissions (role, table_name, can_read, can_write, can_delete) VALUES
        -- Admin: tous droits
        ('admin', 'core.employees', true, true, true),
        ('admin', 'payroll.payroll_transactions', true, true, true),
        ('admin', 'payroll.pay_periods', true, true, false),
        ('admin', 'payroll.import_batches', true, true, false),
        ('admin', 'security.users', true, true, true),
        ('admin', 'security.audit_logs', true, false, false),
        
        -- Manager: lecture/écriture (pas delete sur transactions)
        ('manager', 'core.employees', true, true, false),
        ('manager', 'payroll.payroll_transactions', true, true, false),
        ('manager', 'payroll.pay_periods', true, true, false),
        ('manager', 'payroll.import_batches', true, true, false),
        ('manager', 'security.users', true, false, false),
        ('manager', 'security.audit_logs', true, false, false),
        
        -- Viewer: lecture seule
        ('viewer', 'core.employees', true, false, false),
        ('viewer', 'payroll.payroll_transactions', true, false, false),
        ('viewer', 'payroll.pay_periods', true, false, false),
        ('viewer', 'payroll.import_batches', true, false, false),
        ('viewer', 'security.users', false, false, false),
        ('viewer', 'security.audit_logs', true, false, false);
    """
    )

    # ========================
    # 7. employee_job_history: empêcher chevauchements dates
    # ========================

    # Créer extension btree_gist si pas déjà présente (requis pour EXCLUDE sur dates)
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")

    # EXCLUDE constraint pour empêcher chevauchements
    # Syntaxe: EXCLUDE USING gist (employee_id WITH =, daterange WITH &&)
    op.execute(
        """
        ALTER TABLE core.employee_job_history
        ADD CONSTRAINT excl_employee_job_history_no_overlap
        EXCLUDE USING gist (
            employee_id WITH =,
            daterange(date_debut, COALESCE(date_fin, 'infinity'::date), '[]') WITH &&
        );
    """
    )


def downgrade() -> None:
    """Revert schema corrections."""

    # 7. Drop EXCLUDE constraint employee_job_history
    op.execute(
        "ALTER TABLE core.employee_job_history DROP CONSTRAINT IF EXISTS excl_employee_job_history_no_overlap;"
    )

    # 6. Drop security.roles_permissions
    op.drop_table("roles_permissions", schema="security")

    # 5. Revert import_batches (supprimer period_id, remettre pay_date comme FK conceptuelle)
    op.drop_constraint("fk_import_batches_period", "import_batches", schema="payroll")
    op.drop_constraint("uq_import_period_checksum", "import_batches", schema="payroll")
    op.drop_index(
        "idx_import_batches_period", table_name="import_batches", schema="payroll"
    )

    # Recréer contrainte UNIQUE originale (pay_date, checksum)
    op.create_unique_constraint(
        "uq_import_date_checksum",
        "import_batches",
        ["pay_date", "checksum"],
        schema="payroll",
    )
    op.create_index(
        "idx_import_batches_pay_date", "import_batches", ["pay_date"], schema="payroll"
    )

    # Supprimer colonne period_id
    op.drop_column("import_batches", "period_id", schema="payroll")

    # 4. Drop CHECK amount_employer
    op.execute(
        "ALTER TABLE payroll.payroll_transactions DROP CONSTRAINT IF EXISTS ck_payroll_amount_employer_positive;"
    )

    # 3. Drop trigger transactions pay_date
    op.execute(
        "DROP TRIGGER IF EXISTS trg_payroll_transactions_pay_date_check ON payroll.payroll_transactions;"
    )
    op.execute("DROP FUNCTION IF EXISTS payroll.check_transaction_pay_date();")

    # 2. Drop CHECK constraints et trigger pay_periods
    op.execute(
        "DROP TRIGGER IF EXISTS trg_pay_periods_date_consistency ON payroll.pay_periods;"
    )
    op.execute("DROP FUNCTION IF EXISTS payroll.check_pay_date_consistency();")
    op.execute(
        "ALTER TABLE payroll.pay_periods DROP CONSTRAINT IF EXISTS ck_pay_periods_period_seq;"
    )
    op.execute(
        "ALTER TABLE payroll.pay_periods DROP CONSTRAINT IF EXISTS ck_pay_periods_pay_month;"
    )
    op.execute(
        "ALTER TABLE payroll.pay_periods DROP CONSTRAINT IF EXISTS ck_pay_periods_pay_day;"
    )

    # 1. Revert v_monthly_payroll_summary (ancienne version par pay_date)
    op.execute(
        "DROP MATERIALIZED VIEW IF EXISTS payroll.v_monthly_payroll_summary CASCADE;"
    )

    # Recréer version originale
    op.execute(
        """
        CREATE MATERIALIZED VIEW payroll.v_monthly_payroll_summary AS
        SELECT
            pt.pay_date,
            e.employee_id,
            e.matricule,
            e.nom,
            e.prenom,
            SUM(pt.amount_employee_norm_cents) / 100.0 AS total_employee_amount,
            SUM(pt.amount_employer_norm_cents) / 100.0 AS total_employer_amount,
            SUM(pt.amount_employee_norm_cents + pt.amount_employer_norm_cents) / 100.0 AS total_combined_amount,
            COUNT(*) AS transaction_count
        FROM payroll.payroll_transactions pt
        JOIN core.employees e ON pt.employee_id = e.employee_id
        GROUP BY pt.pay_date, e.employee_id, e.matricule, e.nom, e.prenom
        WITH DATA;
    """
    )

    op.create_index(
        "idx_v_monthly_summary_pk",
        "v_monthly_payroll_summary",
        ["pay_date", "employee_id"],
        unique=True,
        schema="payroll",
    )
    op.create_index(
        "idx_v_monthly_summary_date",
        "v_monthly_payroll_summary",
        ["pay_date"],
        schema="payroll",
    )
    op.create_index(
        "idx_v_monthly_summary_employee",
        "v_monthly_payroll_summary",
        ["employee_id"],
        schema="payroll",
    )
