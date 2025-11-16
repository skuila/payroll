"""Initial schema: core, payroll, reference, security

Revision ID: 001
Revises:
Create Date: 2025-10-09 14:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = "000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema with all tables, indexes, and constraints."""

    # ========================
    # 1) EXTENSIONS
    # ========================
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "unaccent";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    # pgaudit: optionnel (requis pour audit avance)
    # Si non installe, on ignore l'erreur avec SAVEPOINT
    op.execute("SAVEPOINT before_pgaudit;")
    try:
        op.execute('CREATE EXTENSION IF NOT EXISTS "pgaudit";')
        op.execute("RELEASE SAVEPOINT before_pgaudit;")
    except Exception:
        op.execute("ROLLBACK TO SAVEPOINT before_pgaudit;")
        print("WARNING: pgaudit non disponible (optionnel) - Extension ignoree")

    # ========================
    # 2) SCHEMAS
    # ========================
    op.execute("CREATE SCHEMA IF NOT EXISTS core;")
    op.execute("CREATE SCHEMA IF NOT EXISTS payroll;")
    op.execute("CREATE SCHEMA IF NOT EXISTS reference;")
    op.execute("CREATE SCHEMA IF NOT EXISTS security;")

    # ========================
    # 3) SECURITY SCHEMA
    # ========================

    # security.users
    op.create_table(
        "users",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),  # admin, manager, viewer
        sa.Column("email", sa.String(255)),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("last_login", sa.TIMESTAMP(timezone=True)),
        schema="security",
    )
    op.create_unique_constraint(
        "uq_users_username", "users", ["username"], schema="security"
    )
    op.create_index("idx_users_role", "users", ["role"], schema="security")
    op.create_index("idx_users_active", "users", ["active"], schema="security")

    # security.audit_logs (PARENT TABLE - partitioned by month)
    # Note: PK doit inclure created_at (colonne de partitionnement)
    op.execute(
        """
        CREATE TABLE security.audit_logs (
            log_id UUID DEFAULT uuid_generate_v4(),
            user_id UUID REFERENCES security.users(user_id),
            action TEXT NOT NULL,  -- SELECT, INSERT, UPDATE, DELETE, LOGIN, LOGOUT
            table_name TEXT,
            record_id TEXT,
            old_value JSONB,
            new_value JSONB,
            ip_address INET,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (log_id, created_at)
        ) PARTITION BY RANGE (created_at);
    """
    )
    op.create_index("idx_audit_user", "audit_logs", ["user_id"], schema="security")
    op.create_index("idx_audit_action", "audit_logs", ["action"], schema="security")
    op.create_index("idx_audit_table", "audit_logs", ["table_name"], schema="security")
    op.create_index(
        "idx_audit_created", "audit_logs", ["created_at"], schema="security"
    )

    # ========================
    # 4) CORE SCHEMA
    # ========================

    # core.employees
    op.create_table(
        "employees",
        sa.Column(
            "employee_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("matricule", sa.String(50), nullable=False),
        sa.Column("nom", sa.String(255), nullable=False),
        sa.Column("prenom", sa.String(255), nullable=False),
        sa.Column(
            "nom_norm", sa.String(255), nullable=False
        ),  # nom normalisé (lowercase, unaccent)
        sa.Column("prenom_norm", sa.String(255), nullable=False),  # prénom normalisé
        sa.Column("date_embauche", sa.Date()),
        sa.Column("date_depart", sa.Date()),
        sa.Column(
            "statut", sa.String(20), nullable=False, server_default="actif"
        ),  # actif, inactif, retraite
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema="core",
    )
    op.create_unique_constraint(
        "uq_employees_matricule", "employees", ["matricule"], schema="core"
    )
    op.create_index("idx_employees_nom_norm", "employees", ["nom_norm"], schema="core")
    op.create_index(
        "idx_employees_prenom_norm", "employees", ["prenom_norm"], schema="core"
    )
    op.create_index("idx_employees_statut", "employees", ["statut"], schema="core")
    op.create_index(
        "idx_employees_date_embauche", "employees", ["date_embauche"], schema="core"
    )

    # Fonction wrapper IMMUTABLE pour unaccent (requis pour index GIN)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION core.immutable_unaccent(text)
        RETURNS text AS $$
        BEGIN
            RETURN unaccent($1);
        END;
        $$ LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE;
    """
    )

    # GIN index for full-text search (trigram) avec fonction IMMUTABLE
    op.execute(
        """
        CREATE INDEX idx_employees_fts ON core.employees 
        USING gin (lower(core.immutable_unaccent(nom_norm || ' ' || prenom_norm)) gin_trgm_ops);
    """
    )

    # core.job_categories
    op.create_table(
        "job_categories",
        sa.Column("category_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nom", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema="core",
    )
    op.create_unique_constraint(
        "uq_job_categories_nom", "job_categories", ["nom"], schema="core"
    )

    # core.job_codes
    op.create_table(
        "job_codes",
        sa.Column("code_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("titre", sa.String(255), nullable=False),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("core.job_categories.category_id"),
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema="core",
    )
    op.create_unique_constraint(
        "uq_job_codes_code", "job_codes", ["code"], schema="core"
    )
    op.create_index(
        "idx_job_codes_category", "job_codes", ["category_id"], schema="core"
    )

    # core.employee_job_history (lien employé <-> job_code avec historique)
    op.create_table(
        "employee_job_history",
        sa.Column(
            "history_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "employee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("core.employees.employee_id"),
            nullable=False,
        ),
        sa.Column(
            "code_id",
            sa.Integer(),
            sa.ForeignKey("core.job_codes.code_id"),
            nullable=False,
        ),
        sa.Column("date_debut", sa.Date(), nullable=False),
        sa.Column("date_fin", sa.Date()),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema="core",
    )
    op.create_index(
        "idx_emp_job_hist_employee",
        "employee_job_history",
        ["employee_id"],
        schema="core",
    )
    op.create_index(
        "idx_emp_job_hist_code", "employee_job_history", ["code_id"], schema="core"
    )
    op.create_index(
        "idx_emp_job_hist_dates",
        "employee_job_history",
        ["date_debut", "date_fin"],
        schema="core",
    )

    # core.pay_codes (codes de paie: 101, 159, 703, 801, etc.)
    op.create_table(
        "pay_codes",
        sa.Column("pay_code", sa.String(20), primary_key=True),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column(
            "category", sa.String(100), nullable=False
        ),  # Gains, Syndicats, Assurances, Déductions légales
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema="core",
    )
    op.create_index("idx_pay_codes_category", "pay_codes", ["category"], schema="core")
    op.create_index("idx_pay_codes_active", "pay_codes", ["active"], schema="core")

    # core.budget_posts
    op.create_table(
        "budget_posts",
        sa.Column("budget_post_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(50), nullable=False),  # ex: 1-101-23600-160
        sa.Column("description", sa.String(500)),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema="core",
    )
    op.create_unique_constraint(
        "uq_budget_posts_code", "budget_posts", ["code"], schema="core"
    )
    op.create_index(
        "idx_budget_posts_active", "budget_posts", ["active"], schema="core"
    )

    # ========================
    # 5) PAYROLL SCHEMA
    # ========================

    # payroll.pay_periods
    op.create_table(
        "pay_periods",
        sa.Column(
            "period_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "pay_date", sa.Date(), nullable=False
        ),  # DATE au JOUR (ex: 2025-08-28)
        sa.Column("pay_day", sa.Integer(), nullable=False),  # jour (1-31)
        sa.Column("pay_month", sa.Integer(), nullable=False),  # mois (1-12)
        sa.Column("pay_year", sa.Integer(), nullable=False),  # année
        sa.Column(
            "period_seq_in_year", sa.Integer(), nullable=False
        ),  # numéro de paie dans l'année (1-26 pour bi-hebdo)
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="ouverte"
        ),  # ouverte, fermée, archivée
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column(
            "closed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("security.users.user_id"),
        ),
        schema="payroll",
    )
    op.create_unique_constraint(
        "uq_pay_periods_date", "pay_periods", ["pay_date"], schema="payroll"
    )
    # Note: uq_pay_periods_year_seq sera créée par Migration 004 (avec trigger auto-calcul)
    op.create_index(
        "idx_pay_periods_year", "pay_periods", ["pay_year"], schema="payroll"
    )
    op.create_index(
        "idx_pay_periods_status", "pay_periods", ["status"], schema="payroll"
    )
    op.create_index(
        "idx_pay_periods_date", "pay_periods", ["pay_date"], schema="payroll"
    )

    # payroll.import_batches (traçabilité des imports)
    op.create_table(
        "import_batches",
        sa.Column(
            "batch_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),  # SHA256
        sa.Column("pay_date", sa.Date(), nullable=False),
        sa.Column("rows_count", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(20), nullable=False
        ),  # pending, completed, failed
        sa.Column("error_message", sa.Text()),
        sa.Column(
            "imported_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("security.users.user_id"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema="payroll",
    )
    op.create_unique_constraint(
        "uq_import_date_checksum",
        "import_batches",
        ["pay_date", "checksum"],
        schema="payroll",
    )
    op.create_index(
        "idx_import_batches_pay_date", "import_batches", ["pay_date"], schema="payroll"
    )
    op.create_index(
        "idx_import_batches_status", "import_batches", ["status"], schema="payroll"
    )
    op.create_index(
        "idx_import_batches_created", "import_batches", ["created_at"], schema="payroll"
    )

    # payroll.payroll_transactions (PARENT TABLE - partitioned by year on pay_date)
    # Note: PK doit inclure pay_date (colonne de partitionnement)
    op.execute(
        """
        CREATE TABLE payroll.payroll_transactions (
            transaction_id UUID DEFAULT uuid_generate_v4(),
            employee_id UUID NOT NULL REFERENCES core.employees(employee_id),
            period_id UUID NOT NULL REFERENCES payroll.pay_periods(period_id),
            pay_date DATE NOT NULL,  -- Colonne de partitionnement
            pay_code TEXT NOT NULL REFERENCES core.pay_codes(pay_code),
            budget_post_id INTEGER NOT NULL REFERENCES core.budget_posts(budget_post_id),
            amount_employee_norm_cents BIGINT NOT NULL,  -- Montant employé normalisé en centimes
            amount_employer_norm_cents BIGINT NOT NULL,  -- Montant employeur normalisé en centimes
            source_file TEXT,
            source_row_no INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (transaction_id, pay_date)
        ) PARTITION BY RANGE (pay_date);
    """
    )

    # Indexes sur la table parent (seront hérités par les partitions)
    op.create_index(
        "idx_payroll_employee",
        "payroll_transactions",
        ["employee_id"],
        schema="payroll",
    )
    op.create_index(
        "idx_payroll_period", "payroll_transactions", ["period_id"], schema="payroll"
    )
    op.create_index(
        "idx_payroll_pay_date", "payroll_transactions", ["pay_date"], schema="payroll"
    )
    op.create_index(
        "idx_payroll_pay_code", "payroll_transactions", ["pay_code"], schema="payroll"
    )
    op.create_index(
        "idx_payroll_budget_post",
        "payroll_transactions",
        ["budget_post_id"],
        schema="payroll",
    )
    op.create_index(
        "idx_payroll_employee_pay_date",
        "payroll_transactions",
        ["employee_id", "pay_date"],
        schema="payroll",
    )

    # ========================
    # 6) REFERENCE SCHEMA
    # ========================

    # reference.pay_code_mappings (mapping colonnes Excel -> pay_code)
    op.create_table(
        "pay_code_mappings",
        sa.Column("mapping_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_column_name", sa.String(255), nullable=False),
        sa.Column("source_value", sa.String(255)),
        sa.Column(
            "pay_code",
            sa.String(20),
            sa.ForeignKey("core.pay_codes.pay_code"),
            nullable=False,
        ),
        sa.Column("priority", sa.Integer(), server_default="100"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema="reference",
    )
    op.create_index(
        "idx_pay_code_mappings_source",
        "pay_code_mappings",
        ["source_column_name"],
        schema="reference",
    )
    op.create_index(
        "idx_pay_code_mappings_pay_code",
        "pay_code_mappings",
        ["pay_code"],
        schema="reference",
    )

    # reference.sign_policies (règles de signe pour les montants)
    op.create_table(
        "sign_policies",
        sa.Column("policy_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "pay_code",
            sa.String(20),
            sa.ForeignKey("core.pay_codes.pay_code"),
            nullable=False,
        ),
        sa.Column("employee_sign", sa.SmallInteger(), nullable=False),  # +1 ou -1
        sa.Column("employer_sign", sa.SmallInteger(), nullable=False),  # +1 ou -1
        sa.Column("description", sa.Text()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema="reference",
    )
    op.create_unique_constraint(
        "uq_sign_policies_pay_code", "sign_policies", ["pay_code"], schema="reference"
    )
    op.execute(
        """
        ALTER TABLE reference.sign_policies
        ADD CONSTRAINT ck_sign_policies_employee_sign CHECK (employee_sign IN (-1, 1))
    """
    )
    op.execute(
        """
        ALTER TABLE reference.sign_policies
        ADD CONSTRAINT ck_sign_policies_employer_sign CHECK (employer_sign IN (-1, 1))
    """
    )

    # ========================
    # 7) MATERIALIZED VIEWS
    # ========================

    # v_monthly_payroll_summary
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

    # v_employee_current_salary
    op.execute(
        """
        CREATE MATERIALIZED VIEW payroll.v_employee_current_salary AS
        WITH latest_pay AS (
            SELECT DISTINCT ON (employee_id)
                employee_id,
                pay_date,
                SUM(amount_employee_norm_cents) / 100.0 AS last_net_salary
            FROM payroll.payroll_transactions
            GROUP BY employee_id, pay_date
            ORDER BY employee_id, pay_date DESC
        )
        SELECT
            e.employee_id,
            e.matricule,
            e.nom,
            e.prenom,
            e.statut,
            lp.pay_date AS last_pay_date,
            lp.last_net_salary
        FROM core.employees e
        LEFT JOIN latest_pay lp ON e.employee_id = lp.employee_id
        WHERE e.statut = 'actif'
        WITH DATA;
    """
    )
    op.create_index(
        "idx_v_current_salary_pk",
        "v_employee_current_salary",
        ["employee_id"],
        unique=True,
        schema="payroll",
    )
    op.create_index(
        "idx_v_current_salary_matricule",
        "v_employee_current_salary",
        ["matricule"],
        schema="payroll",
    )

    # v_employee_annual_history
    op.execute(
        """
        CREATE MATERIALIZED VIEW payroll.v_employee_annual_history AS
        SELECT
            EXTRACT(YEAR FROM pt.pay_date)::INTEGER AS year,
            e.employee_id,
            e.matricule,
            e.nom,
            e.prenom,
            SUM(pt.amount_employee_norm_cents) / 100.0 AS annual_employee_total,
            SUM(pt.amount_employer_norm_cents) / 100.0 AS annual_employer_total,
            SUM(pt.amount_employee_norm_cents + pt.amount_employer_norm_cents) / 100.0 AS annual_combined_total,
            COUNT(DISTINCT pt.pay_date) AS pay_periods_count
        FROM payroll.payroll_transactions pt
        JOIN core.employees e ON pt.employee_id = e.employee_id
        GROUP BY EXTRACT(YEAR FROM pt.pay_date), e.employee_id, e.matricule, e.nom, e.prenom
        WITH DATA;
    """
    )
    op.create_index(
        "idx_v_annual_hist_pk",
        "v_employee_annual_history",
        ["year", "employee_id"],
        unique=True,
        schema="payroll",
    )
    op.create_index(
        "idx_v_annual_hist_year",
        "v_employee_annual_history",
        ["year"],
        schema="payroll",
    )
    op.create_index(
        "idx_v_annual_hist_employee",
        "v_employee_annual_history",
        ["employee_id"],
        schema="payroll",
    )

    # ========================
    # 8) TRIGGERS
    # ========================

    # Trigger pour updated_at sur core.employees
    op.execute(
        """
        CREATE OR REPLACE FUNCTION core.update_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    op.execute(
        """
        CREATE TRIGGER trg_employees_updated_at
        BEFORE UPDATE ON core.employees
        FOR EACH ROW
        EXECUTE FUNCTION core.update_timestamp();
    """
    )


def downgrade() -> None:
    """Drop all created objects."""

    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trg_employees_updated_at ON core.employees;")
    op.execute("DROP FUNCTION IF EXISTS core.update_timestamp();")

    # Drop materialized views
    op.execute("DROP MATERIALIZED VIEW IF EXISTS payroll.v_employee_annual_history;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS payroll.v_employee_current_salary;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS payroll.v_monthly_payroll_summary;")

    # Drop reference tables
    op.drop_table("sign_policies", schema="reference")
    op.drop_table("pay_code_mappings", schema="reference")

    # Drop payroll tables
    op.execute("DROP TABLE IF EXISTS payroll.payroll_transactions CASCADE;")
    op.drop_table("import_batches", schema="payroll")
    op.drop_table("pay_periods", schema="payroll")

    # Drop core tables
    op.drop_table("budget_posts", schema="core")
    op.drop_table("pay_codes", schema="core")
    op.drop_table("employee_job_history", schema="core")
    op.drop_table("job_codes", schema="core")
    op.drop_table("job_categories", schema="core")
    op.drop_table("employees", schema="core")

    # Drop security tables
    op.execute("DROP TABLE IF EXISTS security.audit_logs CASCADE;")
    op.drop_table("users", schema="security")

    # Drop schemas
    op.execute("DROP SCHEMA IF EXISTS security CASCADE;")
    op.execute("DROP SCHEMA IF EXISTS reference CASCADE;")
    op.execute("DROP SCHEMA IF EXISTS payroll CASCADE;")
    op.execute("DROP SCHEMA IF EXISTS core CASCADE;")

    # Drop extensions (optionnel - peut être partagé avec d'autres DB)
    # op.execute('DROP EXTENSION IF EXISTS "pgaudit";')
    # op.execute('DROP EXTENSION IF EXISTS "pgcrypto";')
    # op.execute('DROP EXTENSION IF EXISTS "pg_trgm";')
    # op.execute('DROP EXTENSION IF EXISTS "unaccent";')
    # op.execute('DROP EXTENSION IF EXISTS "uuid-ossp";')
