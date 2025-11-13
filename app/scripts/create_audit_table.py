#!/usr/bin/env python3
"""Crée la table d'audit pour les périodes supprimées"""

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from config.connection_standard import get_connection

print("=" * 70)
print("CRÉATION DE LA TABLE D'AUDIT")
print("=" * 70)
print()

# Lire le script SQL
sql_file = Path(__file__).parent / "sql" / "create_deleted_periods_audit.sql"
sql = sql_file.read_text(encoding="utf-8")

print(f"📄 Lecture du script: {sql_file}")
print()

try:
    with get_connection() as conn:
        with conn.cursor() as cur:
            print("🔄 Exécution du script SQL...")
            cur.execute(sql)
            conn.commit()
            print("✅ Table deleted_periods_audit créée avec succès")
            print()

            # Vérifier que la table existe
            cur.execute(
                """
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'payroll' 
                AND table_name = 'deleted_periods_audit'
            """
            )
            count = cur.fetchone()[0]

            if count > 0:
                print("✅ Vérification: Table existe bien dans la base")
            else:
                print("❌ Erreur: Table non trouvée après création")

    print()
    print("=" * 70)
    print("✅ OPÉRATION TERMINÉE")
    print("=" * 70)

except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback

    traceback.print_exc()
    print()
    print("=" * 70)
    print("❌ ÉCHEC")
    print("=" * 70)
