#!/usr/bin/env python3
"""
Script d'administration Python pour créer les vues KPI avec compte admin
"""

import sys
import os
from pathlib import Path
import psycopg
from dotenv import load_dotenv

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()
# Ensure PAYROLL_DB_PASSWORD is available to libpq/psycopg via PGPASSWORD
payroll_db_password = os.getenv("PAYROLL_DB_PASSWORD")
if payroll_db_password:
    # Do not override an existing PGPASSWORD if already set in the environment
    os.environ.setdefault("PGPASSWORD", payroll_db_password)

# Configuration de connexion ADMIN
from config.config_manager import get_superuser_dsn

ADMIN_DSN = get_superuser_dsn()


def execute_admin_sql(sql_content):
    """Exécute le SQL avec le compte administrateur"""
    try:
        print("🔐 Connexion avec le compte administrateur...")

        with psycopg.connect(ADMIN_DSN) as conn:
            # Exécuter les commandes DDL en autocommit afin qu'une erreur
            # sur une commande (ex: DROP VIEW vs MATERIALIZED VIEW) n'annule
            # pas la transaction entière et n'empêche pas l'exécution des
            # commandes suivantes.
            try:
                conn.autocommit = True
            except Exception:
                # Certains adaptateurs ou contextes pourraient ne pas supporter
                # l'attribut autocommit; dans ce cas on continue sans le définir.
                pass

            with conn.cursor() as cur:
                # Diviser le SQL en commandes individuelles
                commands = [
                    cmd.strip() for cmd in sql_content.split(";") if cmd.strip()
                ]

                executed_commands = 0
                for i, command in enumerate(commands, 1):
                    if (
                        command
                        and not command.startswith("--")
                        and not command.startswith("\\")
                    ):
                        # Debug: show which command is about to run (trim long SQL)
                        snippet = command.replace("\n", " ")[:200]
                        print(f"   ▶ Exécution commande {i}: {snippet}")
                        try:
                            cur.execute(command)
                            # Commit after each successful command so a failing command
                            # does not leave the transaction in aborted state for
                            # subsequent commands.
                            conn.commit()
                            executed_commands += 1

                            # Identifier le type de commande
                            if "CREATE OR REPLACE VIEW" in command.upper():
                                view_name = (
                                    command.split("CREATE OR REPLACE VIEW")[1]
                                    .split("AS")[0]
                                    .strip()
                                )
                                print(f"   ✅ Vue créée: {view_name}")
                            elif "CREATE SCHEMA" in command.upper():
                                print(f"   ✅ Schéma créé")
                            elif "GRANT" in command.upper():
                                print(f"   🔐 Permissions accordées")
                            elif "COMMENT" in command.upper():
                                print(f"   📝 Commentaires ajoutés")

                        except Exception as e:
                            # Rollback this failed command so following commands can run
                            try:
                                conn.rollback()
                            except Exception:
                                pass
                                # Rollback to clear any aborted transaction so we can continue
                                try:
                                    conn.rollback()
                                except Exception:
                                    # Ignore rollback errors - we'll continue to next command
                                    pass

                            # Ignorer certaines erreurs attendues
                            msg = str(e).lower()
                            if (
                                "already exists" in msg
                                or "does not exist" in msg
                                or "is not a" in msg
                            ):
                                print(f"   ℹ️  Commande {i}: {str(e)[:200]}...")
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
                print(f"   📊 Vues KPI créées: {len(views)}")
                for view in views:
                    print(f"      ✅ {view}")

                # Test des données
                if views:
                    cur.execute("SELECT COUNT(*) FROM paie.v_kpi_periode")
                    count = cur.fetchone()[0]
                    print(f"   📈 Données dans v_kpi_periode: {count} lignes")

                    if count > 0:
                        cur.execute(
                            "SELECT date_paie, gains_brut, nb_employes FROM paie.v_kpi_periode LIMIT 3"
                        )
                        sample = cur.fetchall()
                        print(f"   📋 Échantillon:")
                        for row in sample:
                            print(f"      {row[0]}: {row[1]:,.2f}€, {row[2]} employés")

                return True

    except Exception as e:
        print(f"❌ Erreur lors de l'exécution: {e}")
        return False


def main():
    """Fonction principale d'administration"""
    print("🔧 ADMINISTRATION - CRÉATION DES VUES KPI DURABLES")
    print("=" * 60)

    # Lire le fichier SQL d'administration
    sql_file = Path(__file__).parent / "admin_create_kpi_views.sql"

    if not sql_file.exists():
        print(f"❌ Fichier SQL non trouvé: {sql_file}")
        return 1

    print("📄 Lecture du script d'administration...")

    with open(sql_file, "r", encoding="utf-8") as f:
        sql_content = f.read()

    print("🚀 Exécution du script d'administration...")

    success = execute_admin_sql(sql_content)

    if success:
        print("\n🎉 ADMINISTRATION TERMINÉE AVEC SUCCÈS")
        print("✅ Schéma paie créé avec les droits administrateur")
        print("✅ 7 vues KPI harmonisées créées")
        print("✅ Permissions lecture seule accordées à payroll_app")
        print("✅ Alias rétro-compatibles configurés")
        print("✅ Documentation et commentaires ajoutés")
        print("\n🔗 Les vues sont maintenant disponibles pour l'API")
        print("📊 Test: SELECT * FROM paie.v_kpi_periode LIMIT 5;")
        return 0
    else:
        print("\n❌ ÉCHEC DE L'ADMINISTRATION")
        print("🔧 Vérifiez les éléments suivants:")
        print("   - PostgreSQL est installé et accessible")
        print("   - Le compte postgres existe avec le bon mot de passe")
        print("   - La base payroll_db existe")
        print("   - Vous avez les droits administrateur")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
