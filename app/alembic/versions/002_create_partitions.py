"""Create initial partitions for payroll_transactions and audit_logs

Revision ID: 002
Revises: 001
Create Date: 2025-10-09 14:10:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create partitions for payroll_transactions (by year) and audit_logs (by month)."""

    # ========================
    # 1) PAYROLL_TRANSACTIONS PARTITIONS (BY YEAR)
    # ========================

    # Historique: 2005-2024 (20 ans)
    for year in range(2005, 2025):
        partition_name = f"payroll_transactions_{year}"
        start_date = f"{year}-01-01"
        end_date = f"{year + 1}-01-01"

        op.execute(
            f"""
            CREATE TABLE IF NOT EXISTS payroll.{partition_name}
            PARTITION OF payroll.payroll_transactions
            FOR VALUES FROM ('{start_date}') TO ('{end_date}');
        """
        )

    # Année courante: 2025
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS payroll.payroll_transactions_2025
        PARTITION OF payroll.payroll_transactions
        FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
    """
    )

    # Partition DEFAULT pour données futures (>= 2026)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS payroll.payroll_transactions_future
        PARTITION OF payroll.payroll_transactions
        DEFAULT;
    """
    )

    # ========================
    # 2) AUDIT_LOGS PARTITIONS (BY MONTH)
    # ========================

    # Créer partitions mensuelles pour 2024-2025 + quelques mois en 2026
    months = [
        ("2024-01", "2024-01-01", "2024-02-01"),
        ("2024-02", "2024-02-01", "2024-03-01"),
        ("2024-03", "2024-03-01", "2024-04-01"),
        ("2024-04", "2024-04-01", "2024-05-01"),
        ("2024-05", "2024-05-01", "2024-06-01"),
        ("2024-06", "2024-06-01", "2024-07-01"),
        ("2024-07", "2024-07-01", "2024-08-01"),
        ("2024-08", "2024-08-01", "2024-09-01"),
        ("2024-09", "2024-09-01", "2024-10-01"),
        ("2024-10", "2024-10-01", "2024-11-01"),
        ("2024-11", "2024-11-01", "2024-12-01"),
        ("2024-12", "2024-12-01", "2025-01-01"),
        ("2025-01", "2025-01-01", "2025-02-01"),
        ("2025-02", "2025-02-01", "2025-03-01"),
        ("2025-03", "2025-03-01", "2025-04-01"),
        ("2025-04", "2025-04-01", "2025-05-01"),
        ("2025-05", "2025-05-01", "2025-06-01"),
        ("2025-06", "2025-06-01", "2025-07-01"),
        ("2025-07", "2025-07-01", "2025-08-01"),
        ("2025-08", "2025-08-01", "2025-09-01"),
        ("2025-09", "2025-09-01", "2025-10-01"),
        ("2025-10", "2025-10-01", "2025-11-01"),
        ("2025-11", "2025-11-01", "2025-12-01"),
        ("2025-12", "2025-12-01", "2026-01-01"),
        ("2026-01", "2026-01-01", "2026-02-01"),
        ("2026-02", "2026-02-01", "2026-03-01"),
        ("2026-03", "2026-03-01", "2026-04-01"),
        ("2026-04", "2026-04-01", "2026-05-01"),
        ("2026-05", "2026-05-01", "2026-06-01"),
        ("2026-06", "2026-06-01", "2026-07-01"),
    ]

    for month_label, start_date, end_date in months:
        partition_name = f'audit_logs_{month_label.replace("-", "_")}'

        op.execute(
            f"""
            CREATE TABLE IF NOT EXISTS security.{partition_name}
            PARTITION OF security.audit_logs
            FOR VALUES FROM ('{start_date}') TO ('{end_date}');
        """
        )

    # Partition DEFAULT pour audit_logs (>= 2026-07-01)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS security.audit_logs_future
        PARTITION OF security.audit_logs
        DEFAULT;
    """
    )


def downgrade() -> None:
    """Drop all partitions."""

    # ========================
    # 1) DROP PAYROLL_TRANSACTIONS PARTITIONS
    # ========================

    op.execute("DROP TABLE IF EXISTS payroll.payroll_transactions_future;")
    op.execute("DROP TABLE IF EXISTS payroll.payroll_transactions_2025;")

    for year in range(2005, 2025):
        op.execute(f"DROP TABLE IF EXISTS payroll.payroll_transactions_{year};")

    # ========================
    # 2) DROP AUDIT_LOGS PARTITIONS
    # ========================

    op.execute("DROP TABLE IF EXISTS security.audit_logs_future;")

    for year in [2024, 2025, 2026]:
        for month in range(1, 13):
            month_str = f"{month:02d}"
            partition_name = f"audit_logs_{year}_{month_str}"
            op.execute(f"DROP TABLE IF EXISTS security.{partition_name};")
