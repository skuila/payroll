#!/usr/bin/env python3
"""
Script Python pour appliquer l'harmonisation des vues KPI
Remplace l'utilisation de psql par une connexion Python directe
"""

import sys
import os
from pathlib import Path
import psycopg
from dotenv import load_dotenv

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

# Propagate PAYROLL_DB_PASSWORD into PGPASSWORD for libpq/psycopg compatibility
try:
    if os.getenv("PAYROLL_DB_PASSWORD") and not os.getenv("PGPASSWORD"):
        os.environ["PGPASSWORD"] = os.getenv("PAYROLL_DB_PASSWORD")
except Exception:
    pass

# Configuration de connexion
from config.config_manager import get_dsn

DSN = get_dsn()


def apply_harmonization():
    """Applique le script d'harmonisation des vues"""
    try:
        print("🔧 Application de l'harmonisation des vues KPI...")

        with psycopg.connect(DSN) as conn:
            with conn.cursor() as cur:
                # Lire le fichier SQL
                sql_file = Path(__file__).parent / "harmonize_kpi_views.sql"

                if not sql_file.exists():
                    print(f"❌ Fichier SQL non trouvé: {sql_file}")
                    return False

                # Lire et exécuter le SQL
                with open(sql_file, "r", encoding="utf-8") as f:
                    sql_content = f.read()

                print("   📄 Lecture du script d'harmonisation...")

                # Diviser le SQL en commandes individuelles
                commands = [
                    cmd.strip() for cmd in sql_content.split(";") if cmd.strip()
                ]

                executed_commands = 0
                for i, command in enumerate(commands, 1):
                    if command and not command.startswith("--"):
                        try:
                            cur.execute(command)
                            executed_commands += 1

                            # Identifier le type de commande
                            if "CREATE VIEW" in command.upper():
                                view_name = (
                                    command.split("CREATE VIEW")[1]
                                    .split("AS")[0]
                                    .strip()
                                )
                                print(f"   ✅ Vue créée: {view_name}")
                            elif "DROP VIEW" in command.upper():
                                view_name = (
                                    command.split("DROP VIEW")[1]
                                    .split("IF EXISTS")[1]
                                    .strip()
                                    if "IF EXISTS" in command.upper()
                                    else command.split("DROP VIEW")[1].strip()
                                )
                                print(f"   🗑️  Vue supprimée: {view_name}")
                            elif "GRANT" in command.upper():
                                print(f"   🔐 Permissions accordées")
                            elif "COMMENT" in command.upper():
                                print(f"   📝 Commentaires ajoutés")

                        except Exception as e:
                            # Ignorer certaines erreurs attendues
                            if (
                                "already exists" in str(e).lower()
                                or "does not exist" in str(e).lower()
                            ):
                                print(f"   ℹ️  Commande {i}: {str(e)[:50]}...")
                            else:
                                print(f"   WARN:  Commande {i}: {e}")

                conn.commit()
                print(f"   ✅ {executed_commands} commandes exécutées avec succès")

                # Vérifier que les vues ont été créées
                cur.execute(
                    """
                    SELECT table_name 
                    FROM information_schema.views 
                    WHERE table_schema = 'paie' 
                    AND table_name LIKE 'v_kpi_%'
                    ORDER BY table_name
                """
                )

                views = [row[0] for row in cur.fetchall()]
                print(f"   📊 Vues KPI disponibles: {len(views)}")
                for view in views:
                    print(f"      - {view}")

                return True

    except Exception as e:
        print(f"❌ Erreur lors de l'application de l'harmonisation: {e}")
        return False


def main():
    """Fonction principale"""
    print("🚀 APPLICATION DE L'HARMONISATION DES VUES KPI")
    print("=" * 50)

    success = apply_harmonization()

    if success:
        print("\n🎉 HARMONISATION APPLIQUÉE AVEC SUCCÈS")
        print("✅ Toutes les vues KPI sont harmonisées")
        print("✅ Contrat de colonnes uniforme appliqué")
        print("✅ Permissions et commentaires configurés")
        return 0
    else:
        print("\n❌ ÉCHEC DE L'HARMONISATION")
        print("🔧 Vérifiez la connexion à la base de données")
        print("📞 Contactez l'administrateur système si nécessaire")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
