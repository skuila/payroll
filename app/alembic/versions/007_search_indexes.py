"""Search indexes for employees (trigram + unaccent)

Revision ID: 007
Revises: 006
Create Date: 2025-10-20
"""

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_employees_nom_unaccent_trgm
        ON core.employees
        USING GIN ( (unaccent(lower(nom_complet))) gin_trgm_ops );
    """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_employees_matricule_trgm
        ON core.employees
        USING GIN ( matricule_norm gin_trgm_ops );
    """
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_employees_nom_unaccent_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_employees_matricule_trgm;")
