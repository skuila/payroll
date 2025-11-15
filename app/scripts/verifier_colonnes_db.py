#!/usr/bin/env python3
"""
Vérifie les noms de colonnes dans la base de données (source de vérité)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from config.connection_standard import open_connection

settings.bootstrap_env()


def verifier_colonnes():
    """Vérifie les colonnes dans la base de données"""

    print("=" * 70)
    print("VÉRIFICATION DES COLONNES DANS LA BASE DE DONNÉES")
    print("=" * 70)

    conn = open_connection()
    cur = conn.cursor()

    try:
        # 1. Colonnes dans imported_payroll_master (normalisées)
        print("\n1. COLONNES DANS payroll.imported_payroll_master (normalisées):")
        print("-" * 70)
        cur.execute(
            """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'payroll' 
              AND table_name = 'imported_payroll_master'
              AND column_name NOT IN ('id', 'import_run_id', 'source_file', 'source_row_number', 'imported_at')
            ORDER BY ordinal_position
        """
        )
        cols = cur.fetchall()
        for i, (col_name, col_type) in enumerate(cols, 1):
            print(f"   {i:2d}. {col_name:30s} ({col_type})")

        # 2. Colonnes dans raw_lines si elle existe (noms EXACTS Excel)
        print("\n2. COLONNES DANS payroll_raw.raw_lines (noms EXACTS Excel):")
        print("-" * 70)
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_schema = 'payroll_raw' 
                  AND table_name = 'raw_lines'
            )
        """
        )
        table_exists = cur.fetchone()[0]

        if table_exists:
            cur.execute(
                """
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'payroll_raw' 
                  AND table_name = 'raw_lines'
                  AND column_name NOT IN ('raw_row_id', 'file_id', 'created_at')
                ORDER BY ordinal_position
            """
            )
            cols_raw = cur.fetchall()
            for i, (col_name, col_type) in enumerate(cols_raw, 1):
                print(f"   {i:2d}. {col_name:30s} ({col_type})")

            # Extraire les noms de colonnes Excel
            colonnes_excel = [col[0] for col in cols_raw]
            print("\n3. NOMS DE COLONNES EXCEL (source de vérité):")
            print("-" * 70)
            for i, col in enumerate(colonnes_excel, 1):
                print(f"   {i:2d}. '{col}'")

            return colonnes_excel
        else:
            print("   ⚠️  Table payroll_raw.raw_lines n'existe pas")
            print("   Vérification dans les migrations SQL...")

            # Vérifier dans la migration 010
            print("\n3. NOMS DE COLONNES DANS LA MIGRATION 010 (alembic):")
            print("-" * 70)
            migration_file = (
                Path(__file__).parent.parent
                / "alembic"
                / "versions"
                / "010_raw_and_profiles.py"
            )
            if migration_file.exists():
                with open(migration_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Extraire les noms de colonnes entre guillemets
                    import re

                    colonnes = re.findall(r'"([^"]+)"', content)
                    # Filtrer les colonnes Excel (15 colonnes)
                    colonnes_excel = [
                        c
                        for c in colonnes
                        if c
                        in [
                            "N de ligne",
                            "Categorie d'emploi",
                            "code emploie",
                            "titre d'emploi",
                            "date de paie",
                            "matricule",
                            "employé",
                            "categorie de paie",
                            "code de paie",
                            "desc code de paie",
                            "poste Budgetaire",
                            "desc poste Budgetaire",
                            "montant",
                            "part employeur",
                            "Mnt/Cmb",
                        ]
                    ]
                    for i, col in enumerate(colonnes_excel, 1):
                        print(f"   {i:2d}. '{col}'")
                    return colonnes_excel

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    colonnes = verifier_colonnes()

    print("\n" + "=" * 70)
    print("RÉSUMÉ - NOMS DE COLONNES EXCEL (source de vérité DB):")
    print("=" * 70)
    if colonnes:
        for i, col in enumerate(colonnes, 1):
            print(f"{i:2d}. {col}")
    else:
        print("⚠️  Impossible de déterminer les colonnes depuis la DB")
