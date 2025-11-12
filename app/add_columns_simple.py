#!/usr/bin/env python3
"""
Script simplifié pour ajouter des colonnes à la base payroll
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.providers.postgres_provider import PostgresProvider


def add_sample_columns():
    """Ajouter quelques colonnes d'exemple"""

    print("AJOUT DE COLONNES EXEMPLE A LA BASE PAYROLL\n")

    p = PostgresProvider()

    # Colonnes à ajouter à core.employees
    columns_to_add = [
        ("department", "VARCHAR(100)", "NULL", "Departement de l'employe"),
        ("job_title", "VARCHAR(150)", "NULL", "Poste occupe"),
        ("hire_date", "DATE", "NULL", "Date d'embauche"),
        ("email", "VARCHAR(150)", "NULL", "Adresse email"),
        ("phone", "VARCHAR(20)", "NULL", "Numero de telephone"),
    ]

    print("Colonnes a ajouter a core.employees:")
    for col_name, col_type, constraints, description in columns_to_add:
        sql = f"ALTER TABLE core.employees ADD COLUMN IF NOT EXISTS {col_name} {col_type} {constraints};"
        print(f"  - {col_name}: {description}")
        print(f"    SQL: {sql}")

        # Décommenter pour exécuter réellement
        # try:
        #     p.repo.run_query(sql)
        #     print("    OK: Colonne ajoutee")
        # except Exception as e:
        #     print(f"    ERREUR: {e}")

    print(f"\nTotal: {len(columns_to_add)} colonnes proposees\n")

    # Générer script SQL
    generate_sql_script(columns_to_add)


def generate_sql_script(columns):
    """Génère un script SQL"""

    script_content = f"""-- Script d'ajout de colonnes - Genere le {datetime.now().isoformat()}
-- Base de donnees: payroll_db

\\c payroll_db

-- AJOUT DE COLONNES A core.employees
"""

    for col_name, col_type, constraints, description in columns:
        script_content += f"-- {description}\n"
        script_content += f"ALTER TABLE core.employees ADD COLUMN IF NOT EXISTS {col_name} {col_type} {constraints};\n\n"

    script_content += "-- CREATION D'INDEX\n"
    script_content += "CREATE INDEX IF NOT EXISTS idx_employees_department ON core.employees(department);\n"
    script_content += (
        "CREATE INDEX IF NOT EXISTS idx_employees_email ON core.employees(email);\n\n"
    )

    script_content += "-- FIN DU SCRIPT\n\\q\n"

    filename = f"add_columns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(script_content)

    print(f"Script SQL genere: {filename}")


def main():
    """Fonction principale"""
    try:
        add_sample_columns()

        print("\n" + "=" * 60)
        print("RESUME:")
        print("- 5 colonnes proposees pour core.employees")
        print("- Script SQL genere automatiquement")
        print("- Index inclus")
        print("=" * 60)
        print("\nIMPORTANT:")
        print("- Testez sur base developpement d'abord")
        print("- Sauvegardez avant execution")
        print("- Verifiez impact application")

    except Exception as e:
        print(f"ERREUR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
