"""Performance and integrity improvements

Revision ID: 004
Revises: 003
Create Date: 2025-10-10

Changes:
1. pay_periods: UNIQUE(pay_year, period_seq_in_year) + auto-calc trigger
2. v_monthly_payroll_summary: INDEX UNIQUE for CONCURRENTLY refresh
3. import_batches: CHECK status IN (pending, processed, error)
4. audit_logs: REVOKE DELETE + trigger append-only
5. payroll_transactions partitions: BRIN index on pay_date

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    # ========================
    # 1. pay_periods: UNIQUE(pay_year, period_seq_in_year) - IDEMPOTENT
    # ========================

    # Vérifier si contrainte ou index existe déjà
    op.execute(
        """
        DO $$
        DECLARE
            constraint_exists BOOLEAN;
            index_exists BOOLEAN;
        BEGIN
            -- Vérifier si contrainte UNIQUE existe
            SELECT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'payroll.pay_periods'::regclass
                AND conname = 'uq_pay_periods_year_seq'
                AND contype = 'u'
            ) INTO constraint_exists;
            
            IF constraint_exists THEN
                RAISE NOTICE 'Contrainte uq_pay_periods_year_seq existe déjà, skip';
                RETURN;
            END IF;
            
            -- Vérifier si index UNIQUE existe (sans contrainte)
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'payroll'
                AND tablename = 'pay_periods'
                AND indexname = 'uq_pay_periods_year_seq'
            ) INTO index_exists;
            
            IF index_exists THEN
                -- Attacher l'index existant comme contrainte
                RAISE NOTICE 'Index uq_pay_periods_year_seq trouvé, attachement comme contrainte UNIQUE';
                EXECUTE 'ALTER TABLE payroll.pay_periods ADD CONSTRAINT uq_pay_periods_year_seq UNIQUE USING INDEX uq_pay_periods_year_seq';
            ELSE
                -- Créer contrainte UNIQUE (créera aussi l'index)
                RAISE NOTICE 'Création contrainte UNIQUE uq_pay_periods_year_seq';
                EXECUTE 'ALTER TABLE payroll.pay_periods ADD CONSTRAINT uq_pay_periods_year_seq UNIQUE (pay_year, period_seq_in_year)';
            END IF;
        END $$;
    """
    )

    # Fonction pour auto-calcul period_seq_in_year (CREATE OR REPLACE = idempotent)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION payroll.auto_calc_period_seq()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Si period_seq_in_year est NULL, le calculer automatiquement
            IF NEW.period_seq_in_year IS NULL THEN
                -- Calculer 1 + nombre de pay_date strictement antérieures dans la même année
                SELECT 1 + COUNT(*)
                INTO NEW.period_seq_in_year
                FROM payroll.pay_periods
                WHERE pay_year = NEW.pay_year
                AND pay_date < NEW.pay_date;
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # Trigger BEFORE INSERT OR UPDATE - IDEMPOTENT
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_auto_calc_period_seq ON payroll.pay_periods;
        
        CREATE TRIGGER trg_auto_calc_period_seq
        BEFORE INSERT OR UPDATE ON payroll.pay_periods
        FOR EACH ROW
        EXECUTE FUNCTION payroll.auto_calc_period_seq();
    """
    )

    # ========================
    # 2. v_monthly_payroll_summary: INDEX UNIQUE - IDEMPOTENT
    # ========================
    op.execute(
        """
        DO $$
        BEGIN
            -- Vérifier si index UNIQUE existe sur MV
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE schemaname = 'payroll' 
                AND tablename = 'v_monthly_payroll_summary'
                AND indexname = 'idx_v_monthly_summary_pk'
            ) THEN
                RAISE NOTICE 'Création index UNIQUE idx_v_monthly_summary_pk pour REFRESH CONCURRENTLY';
                CREATE UNIQUE INDEX idx_v_monthly_summary_pk 
                ON payroll.v_monthly_payroll_summary (pay_year, pay_month, employee_id);
            ELSE
                RAISE NOTICE 'Index idx_v_monthly_summary_pk existe déjà, skip';
            END IF;
        END $$;
    """
    )

    # ========================
    # 3. import_batches: CHECK status - IDEMPOTENT
    # ========================
    op.execute(
        """
        DO $$
        BEGIN
            -- Vérifier si CHECK constraint existe
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conrelid = 'payroll.import_batches'::regclass
                AND conname = 'ck_import_batches_status'
                AND contype = 'c'
            ) THEN
                RAISE NOTICE 'Création CHECK constraint ck_import_batches_status';
                ALTER TABLE payroll.import_batches 
                ADD CONSTRAINT ck_import_batches_status 
                CHECK (status IN ('pending', 'processed', 'error'));
            ELSE
                RAISE NOTICE 'CHECK constraint ck_import_batches_status existe déjà, skip';
            END IF;
        END $$;
    """
    )

    # ========================
    # 4. audit_logs: Protection append-only - IDEMPOTENT
    # ========================

    # Fonction trigger BEFORE DELETE (CREATE OR REPLACE = idempotent)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION security.prevent_audit_delete()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only: DELETE operation is forbidden';
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    # Trigger BEFORE DELETE - IDEMPOTENT
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_audit_logs_prevent_delete ON security.audit_logs;
        
        CREATE TRIGGER trg_audit_logs_prevent_delete
        BEFORE DELETE ON security.audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION security.prevent_audit_delete();
    """
    )

    # REVOKE DELETE pour rôles applicatifs (hors superuser)
    # Créer rôles uniquement si l'utilisateur a les privilèges CREATEROLE
    op.execute(
        """
        DO $$
        DECLARE
            has_createrole BOOLEAN;
        BEGIN
            -- Vérifier si l'utilisateur actuel a CREATEROLE ou SUPERUSER
            SELECT (rolcreaterole OR rolsuper) INTO has_createrole
            FROM pg_roles WHERE rolname = current_user;
            
            IF has_createrole THEN
                -- Créer rôles applicatifs s'ils n'existent pas
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'payroll_admin') THEN
                    RAISE NOTICE 'Création rôle payroll_admin';
                    CREATE ROLE payroll_admin NOLOGIN;
                ELSE
                    RAISE NOTICE 'Rôle payroll_admin existe déjà, skip';
                END IF;
                
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'payroll_manager') THEN
                    RAISE NOTICE 'Création rôle payroll_manager';
                    CREATE ROLE payroll_manager NOLOGIN;
                ELSE
                    RAISE NOTICE 'Rôle payroll_manager existe déjà, skip';
                END IF;
                
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'payroll_viewer') THEN
                    RAISE NOTICE 'Création rôle payroll_viewer';
                    CREATE ROLE payroll_viewer NOLOGIN;
                ELSE
                    RAISE NOTICE 'Rôle payroll_viewer existe déjà, skip';
                END IF;
            ELSE
                RAISE NOTICE 'Skipping role creation: current_user (%) lacks CREATEROLE privilege. Roles must be created manually by superuser.', current_user;
            END IF;
        END $$;
    """
    )

    op.execute(
        """
        REVOKE DELETE ON security.audit_logs FROM payroll_admin, payroll_manager, payroll_viewer;
        GRANT SELECT, INSERT ON security.audit_logs TO payroll_admin, payroll_manager;
        GRANT SELECT ON security.audit_logs TO payroll_viewer;
    """
    )

    # ========================
    # 5. BRIN indexes sur partitions payroll_transactions - IDEMPOTENT
    # ========================

    # Utiliser pg_inherits pour découvrir les partitions existantes dynamiquement
    op.execute(
        """
        DO $$
        DECLARE
            partition_rec RECORD;
            index_name TEXT;
            index_exists BOOLEAN;
        BEGIN
            -- Parcourir toutes les partitions de payroll.payroll_transactions
            FOR partition_rec IN
                SELECT 
                    c.relname AS partition_name,
                    n.nspname AS schema_name
                FROM pg_inherits i
                JOIN pg_class c ON i.inhrelid = c.oid
                JOIN pg_namespace n ON c.relnamespace = n.oid
                WHERE i.inhparent = 'payroll.payroll_transactions'::regclass
            LOOP
                index_name := 'idx_' || partition_rec.partition_name || '_pay_date_brin';
                
                -- Vérifier si index BRIN existe déjà
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE schemaname = partition_rec.schema_name
                    AND tablename = partition_rec.partition_name
                    AND indexname = index_name
                ) INTO index_exists;
                
                IF NOT index_exists THEN
                    RAISE NOTICE 'Création index BRIN % sur %.%', index_name, partition_rec.schema_name, partition_rec.partition_name;
                    EXECUTE format(
                        'CREATE INDEX %I ON %I.%I USING BRIN (pay_date) WITH (pages_per_range = 128)',
                        index_name,
                        partition_rec.schema_name,
                        partition_rec.partition_name
                    );
                ELSE
                    RAISE NOTICE 'Index BRIN % existe déjà sur %.%, skip', index_name, partition_rec.schema_name, partition_rec.partition_name;
                END IF;
            END LOOP;
        END $$;
    """
    )

    # ========================
    # Commentaires
    # ========================
    op.execute(
        """
        COMMENT ON CONSTRAINT uq_pay_periods_year_seq ON payroll.pay_periods IS
        'Unicité de la séquence de période dans une année (ex: période 1/26 de 2025)';
    """
    )

    op.execute(
        """
        COMMENT ON FUNCTION payroll.auto_calc_period_seq() IS
        'Auto-calcul de period_seq_in_year basé sur le rang de pay_date dans pay_year';
    """
    )

    op.execute(
        """
        COMMENT ON CONSTRAINT ck_import_batches_status ON payroll.import_batches IS
        'Statut limité aux valeurs: pending (en attente), processed (traité), error (erreur)';
    """
    )

    op.execute(
        """
        COMMENT ON FUNCTION security.prevent_audit_delete() IS
        'Empêche DELETE sur audit_logs (append-only): exception levée en cas de tentative';
    """
    )


def downgrade():
    # ========================
    # 5. Supprimer BRIN indexes
    # ========================
    op.execute(
        """
        DO $$
        DECLARE
            partition_rec RECORD;
            index_name TEXT;
        BEGIN
            FOR partition_rec IN
                SELECT 
                    c.relname AS partition_name,
                    n.nspname AS schema_name
                FROM pg_inherits i
                JOIN pg_class c ON i.inhrelid = c.oid
                JOIN pg_namespace n ON c.relnamespace = n.oid
                WHERE i.inhparent = 'payroll.payroll_transactions'::regclass
            LOOP
                index_name := 'idx_' || partition_rec.partition_name || '_pay_date_brin';
                EXECUTE format('DROP INDEX IF EXISTS %I.%I', partition_rec.schema_name, index_name);
            END LOOP;
        END $$;
    """
    )

    # ========================
    # 4. Restaurer DELETE sur audit_logs
    # ========================
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_audit_logs_prevent_delete ON security.audit_logs;
    """
    )

    op.execute(
        """
        DROP FUNCTION IF EXISTS security.prevent_audit_delete();
    """
    )

    op.execute(
        """
        GRANT DELETE ON security.audit_logs TO payroll_admin, payroll_manager;
    """
    )

    # ========================
    # 3. Supprimer CHECK status
    # ========================
    op.execute(
        """
        ALTER TABLE payroll.import_batches DROP CONSTRAINT IF EXISTS ck_import_batches_status;
    """
    )

    # ========================
    # 2. Note: Index UNIQUE reste (créé en migration 003)
    # ========================

    # ========================
    # 1. Supprimer trigger + UNIQUE
    # ========================
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_auto_calc_period_seq ON payroll.pay_periods;
    """
    )

    op.execute(
        """
        DROP FUNCTION IF EXISTS payroll.auto_calc_period_seq();
    """
    )

    op.execute(
        """
        ALTER TABLE payroll.pay_periods DROP CONSTRAINT IF EXISTS uq_pay_periods_year_seq;
    """
    )
