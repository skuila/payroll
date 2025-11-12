"""RAW 15 colonnes + ingestion profiles + vue de contrôle"""

from alembic import op

revision = "010"
down_revision = "009"  # ajuste si nécessaire selon ton historique
branch_labels = None
depends_on = None


def upgrade():
    # Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # Schémas
    op.execute("CREATE SCHEMA IF NOT EXISTS payroll_raw;")
    op.execute("CREATE SCHEMA IF NOT EXISTS payroll;")

    # Fichiers importés
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS payroll_raw.ingestion_files (
            file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            filename TEXT NOT NULL,
            imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            header_json JSONB NOT NULL,
            total_rows INTEGER NOT NULL DEFAULT 0
        );
    """
    )

    # Table RAW (15 colonnes EXACTES du fichier Excel, strip espaces finaux)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS payroll_raw.raw_lines (
            raw_row_id BIGSERIAL PRIMARY KEY,
            file_id UUID NOT NULL REFERENCES payroll_raw.ingestion_files(file_id) ON DELETE CASCADE,

            "N de ligne" TEXT,
            "Categorie d'emploi" TEXT,
            "code emploie" TEXT,
            "titre d'emploi" TEXT,
            "date de paie" DATE,
            "matricule" TEXT,
            "employé" TEXT,
            "categorie de paie" TEXT,
            "code de paie" TEXT,
            "desc code de paie" TEXT,
            "poste Budgetaire" TEXT,
            "desc poste Budgetaire" TEXT,
            "montant" NUMERIC,
            "part employeur" NUMERIC,
            "Mnt/Cmb" NUMERIC,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """
    )

    # Index RAW (perf usuelles)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_raw_file ON payroll_raw.raw_lines(file_id);"
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_raw_date ON payroll_raw.raw_lines("date de paie");'
    )
    op.execute(
        """CREATE INDEX IF NOT EXISTS idx_raw_employe_trgm
                  ON payroll_raw.raw_lines USING GIN ( (unaccent(lower(\"employé\"))) gin_trgm_ops );"""
    )
    op.execute(
        """CREATE INDEX IF NOT EXISTS idx_raw_matricule_trgm
                  ON payroll_raw.raw_lines USING GIN ( \"matricule\" gin_trgm_ops );"""
    )
    op.execute(
        """CREATE INDEX IF NOT EXISTS idx_raw_code_paie_trgm
                  ON payroll_raw.raw_lines USING GIN ( \"code de paie\" gin_trgm_ops );"""
    )
    op.execute(
        """CREATE INDEX IF NOT EXISTS idx_raw_poste_budgetaire_trgm
                  ON payroll_raw.raw_lines USING GIN ( (unaccent(lower(\"poste Budgetaire\"))) gin_trgm_ops );"""
    )

    # Profils d'ingestion (mapping JSON)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS payroll.ingestion_profiles (
            profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_key TEXT NOT NULL,
            profile_name TEXT NOT NULL,
            header_signature TEXT,
            mapping_json JSONB NOT NULL,
            options_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            confidence NUMERIC NOT NULL DEFAULT 0.0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ing_profiles_client ON payroll.ingestion_profiles(client_key);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ing_profiles_mapping ON payroll.ingestion_profiles USING GIN (mapping_json);"
    )

    # Vue de contrôle: signale les colonnes OBLIGATOIRES manquantes (ligne à ligne)
    # Rappel de tes règles:
    # - OPTIONNELLES: part employeur, Mnt/Cmb, titre d'emploi, code emploie, Categorie d'emploi
    # - OBLIGATOIRES: le reste (ci-dessous)
    op.execute(
        """
        CREATE OR REPLACE VIEW payroll.v_import_required_check AS
        SELECT
            rl.raw_row_id,
            rl.file_id,
            -- Obligatoires
            (rl."N de ligne" IS NOT NULL AND rl."N de ligne" <> '') AS ok_n_de_ligne,
            (rl."date de paie" IS NOT NULL) AS ok_date_de_paie,
            (rl."matricule" IS NOT NULL AND rl."matricule" <> '') AS ok_matricule,
            (rl."employé" IS NOT NULL AND rl."employé" <> '') AS ok_employe,
            (rl."categorie de paie" IS NOT NULL AND rl."categorie de paie" <> '') AS ok_categorie_de_paie,
            (rl."code de paie" IS NOT NULL AND rl."code de paie" <> '') AS ok_code_de_paie,
            (rl."desc code de paie" IS NOT NULL AND rl."desc code de paie" <> '') AS ok_desc_code_de_paie,
            (rl."poste Budgetaire" IS NOT NULL AND rl."poste Budgetaire" <> '') AS ok_poste_budgetaire,
            (rl."desc poste Budgetaire" IS NOT NULL AND rl."desc poste Budgetaire" <> '') AS ok_desc_poste_budgetaire,
            (rl."montant" IS NOT NULL) AS ok_montant,

            -- Optionnelles (avec alerte si NULL -> risque de biais)
            (rl."part employeur" IS NOT NULL) AS has_part_employeur,
            (rl."Mnt/Cmb" IS NOT NULL) AS has_mnt_cmb,
            (rl."titre d'emploi" IS NOT NULL AND rl."titre d'emploi" <> '') AS has_titre_emploi,
            (rl."code emploie" IS NOT NULL AND rl."code emploie" <> '') AS has_code_emploi,
            (rl."Categorie d'emploi" IS NOT NULL AND rl."Categorie d'emploi" <> '') AS has_categorie_emploi
        FROM payroll_raw.raw_lines rl;
    """
    )


def downgrade():
    op.execute("DROP VIEW IF EXISTS payroll.v_import_required_check;")
    op.execute("DROP TABLE IF EXISTS payroll.ingestion_profiles;")
    op.execute("DROP INDEX IF EXISTS idx_raw_poste_budgetaire_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_raw_code_paie_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_raw_matricule_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_raw_employe_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_raw_date;")
    op.execute("DROP INDEX IF EXISTS idx_raw_file;")
    op.execute("DROP TABLE IF EXISTS payroll_raw.raw_lines;")
    op.execute("DROP TABLE IF EXISTS payroll_raw.ingestion_files;")
    # Schémas laissés en place volontairement
