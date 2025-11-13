#!/usr/bin/env python3
"""
Script pour gérer les modifications de schéma de base de données PostgreSQL
Permet d'ajouter des champs ou changer les noms de colonnes
"""

import os
import sys
from datetime import datetime

# Ajouter le chemin pour importer les services
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.providers.postgres_provider import PostgresProvider


def show_current_schema():
    """Affiche la structure actuelle des tables principales"""
    print("=== STRUCTURE ACTUELLE DE LA BASE DE DONNÉES ===\n")

    p = PostgresProvider()

    # Tables principales
    tables = [
        ("core", "employees"),
        ("payroll", "payroll_transactions"),
        ("payroll", "pay_periods"),
        ("payroll", "import_batches"),
    ]

    for schema, table in tables:
        print(f"📋 Table {schema}.{table}:")

        try:
            result = p.repo.run_query(
                f"""
                SELECT column_name, data_type, is_nullable,
                       column_default, character_maximum_length
                FROM information_schema.columns
                WHERE table_schema = '{schema}' AND table_name = '{table}'
                ORDER BY ordinal_position;
            """
            )

            for row in result:
                col_name, data_type, nullable, default, max_len = row
                nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                default_str = f" DEFAULT {default}" if default else ""
                len_str = f"({max_len})" if max_len else ""
                print(
                    f"  - {col_name}: {data_type}{len_str} {nullable_str}{default_str}"
                )

        except Exception as e:
            print(f"  ❌ Erreur: {e}")

        print()


def add_column_example():
    """Exemple d'ajout d'une colonne"""
    print("=== EXEMPLE: AJOUT D'UNE COLONNE ===\n")

    p = PostgresProvider()

    # Exemple: Ajouter une colonne "department" à core.employees
    sql = """
    ALTER TABLE core.employees
    ADD COLUMN department VARCHAR(100) NULL;
    """

    print("SQL à exécuter pour ajouter une colonne 'department':")
    print(sql)

    # Pour exécuter réellement, décommentez:
    # try:
    #     p.repo.run_query(sql)
    #     print("✅ Colonne ajoutée avec succès!")
    # except Exception as e:
    #     print(f"❌ Erreur: {e}")


def rename_column_example():
    """Exemple de changement de nom de colonne"""
    print("=== EXEMPLE: CHANGEMENT DE NOM DE COLONNE ===\n")

    p = PostgresProvider()

    # Exemple: Renommer "nom_complet" en "full_name" dans core.employees
    sql = """
    ALTER TABLE core.employees
    RENAME COLUMN nom_complet TO full_name;
    """

    print("SQL à exécuter pour renommer la colonne 'nom_complet' en 'full_name':")
    print(sql)

    # Pour exécuter réellement, décommentez:
    # try:
    #     p.repo.run_query(sql)
    #     print("✅ Colonne renommée avec succès!")
    # except Exception as e:
    #     print(f"❌ Erreur: {e}")


def modify_column_type_example():
    """Exemple de modification du type d'une colonne"""
    print("=== EXEMPLE: MODIFICATION DU TYPE D'UNE COLONNE ===\n")

    p = PostgresProvider()

    # Exemple: Changer le type de statut (VARCHAR) en ENUM
    sqls = [
        # Créer le type enum si nécessaire
        """
        DO $$ BEGIN
            CREATE TYPE employee_status AS ENUM ('actif', 'inactif', 'suspendu');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """,
        # Modifier la colonne
        """
        ALTER TABLE core.employees
        ALTER COLUMN statut TYPE employee_status USING statut::employee_status;
        """,
    ]

    print("SQL à exécuter pour changer le type de la colonne 'statut':")
    for i, sql in enumerate(sqls, 1):
        print(f"Étape {i}:")
        print(sql.strip())

    # Pour exécuter réellement, décommentez:
    # try:
    #     for sql in sqls:
    #         p.repo.run_query(sql)
    #     print("✅ Type de colonne modifié avec succès!")
    # except Exception as e:
    #     print(f"❌ Erreur: {e}")


def add_constraint_example():
    """Exemple d'ajout de contraintes"""
    print("=== EXEMPLE: AJOUT DE CONTRAINTES ===\n")

    p = PostgresProvider()

    constraints = [
        # Contrainte de vérification sur le matricule
        """
        ALTER TABLE core.employees
        ADD CONSTRAINT chk_matricule_format
        CHECK (matricule_norm ~ '^[0-9]{4,6}$');
        """,
        # Index sur les colonnes fréquemment recherchées
        """
        CREATE INDEX IF NOT EXISTS idx_employees_matricule
        ON core.employees(matricule_norm);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_employees_nom
        ON core.employees(nom_norm);
        """,
        # Contrainte unique sur employee_key
        """
        ALTER TABLE core.employees
        ADD CONSTRAINT uk_employee_key UNIQUE (employee_key);
        """,
    ]

    print("SQL pour ajouter des contraintes et index:")
    for i, sql in enumerate(constraints, 1):
        print(f"Contrainte {i}:")
        print(sql.strip())
        print()

    # Pour exécuter réellement, décommentez:
    # try:
    #     for sql in constraints:
    #         p.repo.run_query(sql)
    #     print("✅ Contraintes ajoutées avec succès!")
    # except Exception as e:
    #     print(f"❌ Erreur: {e}")


def create_backup_script():
    """Génère un script de sauvegarde avant modifications"""
    print("=== SCRIPT DE SAUVEGARDE ===\n")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_schema_{timestamp}.sql"

    backup_sql = f"""
-- Script de sauvegarde du schéma - Généré le {datetime.now().isoformat()}
-- Fichier: {backup_file}

-- Connexion à la base payroll_db
\\c payroll_db

-- Schéma core (dimension employés)
\\dn core
\\dt core.*
\\d core.employees

-- Schéma payroll (fait transactions)
\\dn payroll
\\dt payroll.*
\\d payroll.payroll_transactions
\\d payroll.pay_periods
\\d payroll.import_batches

-- Comptage des enregistrements
SELECT 'core.employees' as table_name, COUNT(*) as count FROM core.employees
UNION ALL
SELECT 'payroll.payroll_transactions', COUNT(*) FROM payroll.payroll_transactions
UNION ALL
SELECT 'payroll.pay_periods', COUNT(*) FROM payroll.pay_periods;

-- Fin du script de sauvegarde
"""

    print(f"Script de sauvegarde généré: {backup_file}")
    print("Contenu du script:")
    print(backup_sql)

    # Sauvegarder dans un fichier
    with open(backup_file, "w", encoding="utf-8") as f:
        f.write(backup_sql)

    print(f"✅ Script sauvegardé dans: {backup_file}")


def main():
    """Fonction principale"""
    print("🔧 OUTIL DE GESTION DU SCHÉMA DE BASE DE DONNÉES\n")

    try:
        # Afficher la structure actuelle
        show_current_schema()

        # Montrer les exemples
        add_column_example()
        print()
        rename_column_example()
        print()
        modify_column_type_example()
        print()
        add_constraint_example()
        print()
        create_backup_script()

        print("\n" + "=" * 60)
        print("📝 INSTRUCTIONS:")
        print("1. Faites toujours une sauvegarde avant les modifications")
        print("2. Testez les changements sur une base de développement")
        print("3. Vérifiez l'impact sur l'application existante")
        print("4. Documentez tous les changements")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Erreur lors de l'exécution: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
