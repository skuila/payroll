"""
Provider hybride permanent - Utilise les vraies données avec fallback intelligent
Source de vérité unique avec données réelles garanties
"""

"""
Adapter placeholder for removed Hybrid provider.

This module intentionally raises when the legacy hybrid provider is requested.
The old implementation has been archived under `app/tests/legacy/providers/`.

Rationale: the project now enforces a strict PostgreSQL-only connection
strategy (psycopg + DSN with password). Any attempt to use a non-Postgres
provider must fail fast and explicitly.
"""


def get_hybrid_provider(*args, **kwargs):
    """Legacy adapter that explicitly fails to force Postgres-only usage."""
    raise RuntimeError(
        "Provider obsolète : supprimé par stratégie stricte. Utilisez PostgresProvider."
    )


class HybridDataProvider:
    """Compatibility stub which always raises on instantiation."""

    def __init__(self, *args, **kwargs):
        raise RuntimeError(
            "Provider obsolète : supprimé par stratégie stricte. Utilisez PostgresProvider."
        )
