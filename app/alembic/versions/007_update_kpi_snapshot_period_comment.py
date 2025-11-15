"""Update kpi_snapshot.period comment to reflect exact date format

Revision ID: 007
Revises: 006
Create Date: 2025-01-15 10:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Update comment on kpi_snapshot.period to reflect exact date format."""

    # Mettre à jour le commentaire de la colonne period
    op.execute(
        """
        COMMENT ON COLUMN payroll.kpi_snapshot.period IS 
        'Date de paie exacte au format YYYY-MM-DD (ex: 2025-08-28)'
    """
    )

    print("OK: Commentaire de payroll.kpi_snapshot.period mis à jour")


def downgrade() -> None:
    """Revert comment on kpi_snapshot.period to month format."""

    op.execute(
        """
        COMMENT ON COLUMN payroll.kpi_snapshot.period IS 
        'Période au format YYYY-MM (ex: 2025-01)'
    """
    )

    print("OK: Commentaire de payroll.kpi_snapshot.period restauré")
