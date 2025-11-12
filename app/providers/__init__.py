# providers/__init__.py
"""
Module providers pour l'accès aux données de paie.

Contient les implémentations pour PostgreSQL et SQLite (fallback).
"""

from .data_provider import AbstractDataProvider
from .postgres_provider import PostgresProvider

__all__ = ["AbstractDataProvider", "PostgresProvider"]
