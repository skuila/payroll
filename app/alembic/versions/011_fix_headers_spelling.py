"""Rename RAW columns to corrected French spelling + rebuild indexes + migrate profiles mapping_json"""

from alembic import op

revision = "011"
down_revision = "010"  # ajuste si nécessaire
branch_labels = None
depends_on = None


def upgrade():
    # Renommer les colonnes dans payroll_raw.raw_lines
    # Mapping ancien -> nouveau
    # 1: "N de ligne"             -> "N de ligne" (inchangé)
    # 2: "Categorie d'emploi"     -> "catégorie d'emploi"
    # 3: "code emploie"           -> "code emploi"
    # 4: "titre d'emploi"         -> "titre d'emploi" (inchangé)
    # 5: "date de paie"           -> "date de paie" (inchangé)
    # 6: "matricule"              -> "matricule" (inchangé)
    # 7: "employé"                -> "employé" (inchangé)
    # 8: "categorie de paie"      -> "catégorie de paie"
    # 9: "code de paie"           -> "code de paie" (inchangé)
    # 10:"desc code de paie"      -> "description du code de paie"
    # 11:"poste Budgetaire"       -> "poste budgétaire"
    # 12:"desc poste Budgetaire"  -> "description du poste budgétaire"
    # 13:"montant"                -> "montant" (inchangé)
    # 14:"part employeur"         -> "part employeur" (inchangé)
    # 15:"Mnt/Cmb"                -> "montant combiné"

    # Renommer colonnes
    op.execute(
        'ALTER TABLE payroll_raw.raw_lines RENAME COLUMN "Categorie d\'emploi" TO "catégorie d\'emploi";'
    )
    op.execute(
        'ALTER TABLE payroll_raw.raw_lines RENAME COLUMN "code emploie" TO "code emploi";'
    )
    op.execute(
        'ALTER TABLE payroll_raw.raw_lines RENAME COLUMN "categorie de paie" TO "catégorie de paie";'
    )
    op.execute(
        'ALTER TABLE payroll_raw.raw_lines RENAME COLUMN "desc code de paie" TO "description du code de paie";'
    )
    op.execute(
        'ALTER TABLE payroll_raw.raw_lines RENAME COLUMN "poste Budgetaire" TO "poste budgétaire";'
    )
    op.execute(
        'ALTER TABLE payroll_raw.raw_lines RENAME COLUMN "desc poste Budgetaire" TO "description du poste budgétaire";'
    )
    op.execute(
        'ALTER TABLE payroll_raw.raw_lines RENAME COLUMN "Mnt/Cmb" TO "montant combiné";'
    )

    # Recréer index dépendants (DROP si existants, CREATE sur nouveaux noms)
    op.execute("DROP INDEX IF EXISTS idx_raw_employe_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_raw_matricule_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_raw_code_paie_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_raw_poste_budgetaire_trgm;")
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_raw_employe_trgm ON payroll_raw.raw_lines USING GIN ( (unaccent(lower("employé"))) gin_trgm_ops );'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_raw_matricule_trgm ON payroll_raw.raw_lines USING GIN ( "matricule" gin_trgm_ops );'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_raw_code_paie_trgm ON payroll_raw.raw_lines USING GIN ( "code de paie" gin_trgm_ops );'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_raw_poste_budgetaire_trgm ON payroll_raw.raw_lines USING GIN ( (unaccent(lower("poste budgétaire"))) gin_trgm_ops );'
    )

    # Mettre à jour les noms dans payroll.ingestion_profiles.mapping_json (remplacement texte contrôlé)
    # NOTE: on fait des replace ciblés sur les clés/valeurs JSON (safe si guillemets)
    op.execute(
        """
        UPDATE payroll.ingestion_profiles
        SET mapping_json = REPLACE(mapping_json::text, '\"Categorie d\\'emploi\"', '\"catégorie d\\'emploi\"')::jsonb
    """
    )
    op.execute(
        """
        UPDATE payroll.ingestion_profiles
        SET mapping_json = REPLACE(mapping_json::text, '\"code emploie\"', '\"code emploi\"')::jsonb
    """
    )
    op.execute(
        """
        UPDATE payroll.ingestion_profiles
        SET mapping_json = REPLACE(mapping_json::text, '\"categorie de paie\"', '\"catégorie de paie\"')::jsonb
    """
    )
    op.execute(
        """
        UPDATE payroll.ingestion_profiles
        SET mapping_json = REPLACE(mapping_json::text, '\"desc code de paie\"', '\"description du code de paie\"')::jsonb
    """
    )
    op.execute(
        """
        UPDATE payroll.ingestion_profiles
        SET mapping_json = REPLACE(mapping_json::text, '\"poste Budgetaire\"', '\"poste budgétaire\"')::jsonb
    """
    )
    op.execute(
        """
        UPDATE payroll.ingestion_profiles
        SET mapping_json = REPLACE(mapping_json::text, '\"desc poste Budgetaire\"', '\"description du poste budgétaire\"')::jsonb
    """
    )
    op.execute(
        """
        UPDATE payroll.ingestion_profiles
        SET mapping_json = REPLACE(mapping_json::text, '\"Mnt/Cmb\"', '\"montant combiné\"')::jsonb
    """
    )

    # Option: signature tolérante (on laisse le code gérer l'aliasing pour match 100%)
    # (pas d'update header_signature ici)


def downgrade():
    # Impossible de revenir proprement sans perdre l'orthographe corrigée ; on tente le best-effort.
    op.execute(
        'ALTER TABLE payroll_raw.raw_lines RENAME COLUMN "montant combiné" TO "Mnt/Cmb";'
    )
    op.execute(
        'ALTER TABLE payroll_raw.raw_lines RENAME COLUMN "description du poste budgétaire" TO "desc poste Budgetaire";'
    )
    op.execute(
        'ALTER TABLE payroll_raw.raw_lines RENAME COLUMN "poste budgétaire" TO "poste Budgetaire";'
    )
    op.execute(
        'ALTER TABLE payroll_raw.raw_lines RENAME COLUMN "description du code de paie" TO "desc code de paie";'
    )
    op.execute(
        'ALTER TABLE payroll_raw.raw_lines RENAME COLUMN "catégorie de paie" TO "categorie de paie";'
    )
    op.execute(
        'ALTER TABLE payroll_raw.raw_lines RENAME COLUMN "code emploi" TO "code emploie";'
    )
    op.execute(
        'ALTER TABLE payroll_raw.raw_lines RENAME COLUMN "catégorie d\'emploi" TO "Categorie d\'emploi";'
    )

    op.execute("DROP INDEX IF EXISTS idx_raw_poste_budgetaire_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_raw_code_paie_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_raw_matricule_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_raw_employe_trgm;")
