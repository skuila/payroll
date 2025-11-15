#!/usr/bin/env python3
"""
Vérifie la structure réelle de core.employees dans la DB
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from config.connection_standard import open_connection

settings.bootstrap_env()


def verifier_structure():
    """Vérifie la structure de core.employees"""

    print("=" * 70)
    print("STRUCTURE DE core.employees")
    print("=" * 70)

    conn = open_connection()
    cur = conn.cursor()

    try:
        # Vérifier les colonnes
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'core' AND table_name = 'employees'
            ORDER BY ordinal_position
        """
        )
        cols = cur.fetchall()

        print("\n📋 Colonnes dans core.employees:")
        for col_name, data_type, is_nullable in cols:
            nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
            print(f"   {col_name}: {data_type} ({nullable})")

        # Vérifier si matricule existe
        colonnes = [c[0] for c in cols]
        if "matricule" in colonnes:
            print("\n✅ La colonne 'matricule' EXISTE dans core.employees")
        else:
            print("\n❌ La colonne 'matricule' N'EXISTE PAS dans core.employees")
            print("   Colonnes disponibles: matricule_norm, matricule_raw")

        # Vérifier les contraintes
        print("\n🔑 Contraintes:")
        cur.execute(
            """
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_schema = 'core' AND table_name = 'employees'
        """
        )
        constraints = cur.fetchall()
        for constraint_name, constraint_type in constraints:
            print(f"   {constraint_name}: {constraint_type}")

        # Vérifier les index
        print("\n📇 Index:")
        cur.execute(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'core' AND tablename = 'employees'
        """
        )
        indexes = cur.fetchall()
        for indexname, indexdef in indexes:
            print(f"   {indexname}")
            print(f"      {indexdef}")

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    verifier_structure()
