"""Create kpi_snapshot table for cached KPI calculations

Revision ID: 006
Revises: 005
Create Date: 2025-10-12 14:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create kpi_snapshot table."""

    # ========================
    # payroll.kpi_snapshot
    # ========================
    # Table pour stocker les KPI pré-calculés par période
    # Structure JSONB pour flexibilité

    op.create_table(
        "kpi_snapshot",
        sa.Column(
            "period",
            sa.String(20),
            primary_key=True,
            comment="Date de paie exacte au format YYYY-MM-DD (ex: 2025-08-28)",
        ),
        sa.Column(
            "period_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="FK vers pay_periods (optionnel)",
        ),
        sa.Column(
            "data",
            postgresql.JSONB,
            nullable=False,
            comment="KPI pré-calculés en JSONB",
        ),
        sa.Column(
            "calculated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="Date de calcul",
        ),
        sa.Column(
            "row_count",
            sa.Integer,
            nullable=False,
            server_default="0",
            comment="Nombre de lignes source",
        ),
        schema="payroll",
    )

    # Index sur calculated_at pour purge des anciens snapshots
    op.create_index(
        "idx_kpi_snapshot_calculated",
        "kpi_snapshot",
        ["calculated_at"],
        schema="payroll",
    )

    # FK vers pay_periods (optionnel - permet lien mais pas de contrainte stricte pour flexibilité)
    # Commenté car période peut être un agrégat (ex: "2025" pour année entière)
    # op.create_foreign_key(
    #     'fk_kpi_snapshot_period',
    #     'kpi_snapshot', 'pay_periods',
    #     ['period_id'], ['period_id'],
    #     source_schema='payroll', referent_schema='payroll'
    # )

    print("OK: Table payroll.kpi_snapshot créée avec succès")
    print("OK: Structure JSONB pour flexibilité des KPI")
    print("OK: Index sur calculated_at pour maintenance")


def downgrade() -> None:
    """Drop kpi_snapshot table."""
    op.drop_table("kpi_snapshot", schema="payroll")
    print("OK: Table payroll.kpi_snapshot supprimée")
