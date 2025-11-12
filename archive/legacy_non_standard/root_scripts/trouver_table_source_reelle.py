#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Trouver la table source réelle pour les données de paie"""
import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import psycopg

print("=" * 70)
print("RECHERCHE DE LA TABLE SOURCE RÉELLE")
print("=" * 70)
print("")

try:
    import os

    # Construire le DSN depuis les variables d'environnement pour éviter les secrets en clair
    dsn = os.getenv("PAYROLL_DSN") or (
        f"postgresql://{os.getenv('PAYROLL_DB_USER','payroll_owner')}:{os.getenv('PAYROLL_DB_PASSWORD','')}@{os.getenv('PAYROLL_DB_HOST','localhost')}:{os.getenv('PAYROLL_DB_PORT','5432')}/{os.getenv('PAYROLL_DB_NAME','payroll_db')}"
    )
    conn = psycopg.connect(dsn)
    cur = conn.cursor()

    # Lister toutes les tables
    print("1. TOUTES LES TABLES DANS LE SCHÉMA PAYROLL:")
    print("-" * 70)

    cur.execute(
        """
        SELECT table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = 'payroll'
        ORDER BY table_type, table_name
    """
    )

    tables = cur.fetchall()

    real_tables = []
    views = []

    for table_name, table_type in tables:
        if table_type == "BASE TABLE":
            real_tables.append(table_name)
            print(f"   📊 TABLE: {table_name}")
        else:
            views.append(table_name)
            print(f"   👁️  VIEW: {table_name}")

    print("")

    # Examiner les vues pour trouver la table source
    print("2. VÉRIFICATION DES VUES POUR TROUVER LA TABLE SOURCE:")
    print("-" * 70)

    for view_name in views:
        if "payroll" in view_name.lower():
            try:
                cur.execute(
                    f"""
                    SELECT definition
                    FROM pg_views
                    WHERE schemaname = 'payroll'
                      AND viewname = '{view_name}'
                """
                )

                result = cur.fetchone()
                if result:
                    view_def = result[0]

                    # Chercher FROM dans la définition
                    if "FROM payroll." in view_def:
                        # Extraire le nom de la table
                        lines = view_def.split("\n")
                        for line in lines:
                            if "FROM payroll." in line or "FROM" in line.upper():
                                # Extraire le nom de table
                                parts = line.upper().split("FROM")
                                if len(parts) > 1:
                                    table_part = parts[1].strip().split()[0]
                                    table_name = table_part.replace(
                                        "PAYROLL.", ""
                                    ).strip()
                                    if table_name and table_name not in [""]:
                                        print(
                                            f"   Vue {view_name} utilise la table: {table_name.lower()}"
                                        )
            except Exception as e:
                pass

    print("")

    # Si aucune table trouvée, vérifier les colonnes d'une vue
    if real_tables:
        print(f"3. EXAMEN DES COLONNES DE LA TABLE:")
        print("-" * 70)

        for table_name in real_tables[:3]:  # Limiter à 3 premières
            print(f"\n   Table: {table_name}")

            cur.execute(
                f"""
                SELECT 
                    column_name,
                    data_type,
                    numeric_precision,
                    numeric_scale
                FROM information_schema.columns
                WHERE table_schema = 'payroll'
                  AND table_name = '{table_name}'
                ORDER BY ordinal_position
                LIMIT 20
            """
            )

            cols = cur.fetchall()
            for col_name, data_type, precision, scale in cols:
                type_str = data_type
                if precision:
                    type_str += f"({precision},{scale})" if scale else f"({precision})"
                print(f"      {col_name}: {type_str}")

    # Vérifier v_payroll_detail pour voir quelle table elle utilise
    print("\n4. TABLE UTILISÉE PAR v_payroll_detail:")
    print("-" * 70)

    try:
        cur.execute(
            """
            SELECT definition
            FROM pg_views
            WHERE schemaname = 'payroll'
              AND viewname = 'v_payroll_detail'
        """
        )

        result = cur.fetchone()
        if result:
            view_def = result[0]
            # Chercher FROM
            if "FROM payroll." in view_def:
                import re

                match = re.search(r"FROM\s+payroll\.(\w+)", view_def, re.IGNORECASE)
                if match:
                    source_table = match.group(1)
                    print(f"   ✅ Table source trouvée: {source_table}")

                    # Vérifier les colonnes de cette table
                    print(f"\n   Colonnes de {source_table}:")
                    cur.execute(
                        f"""
                        SELECT 
                            column_name,
                            data_type,
                            numeric_precision,
                            numeric_scale
                        FROM information_schema.columns
                        WHERE table_schema = 'payroll'
                          AND table_name = '{source_table}'
                          AND (column_name LIKE '%montant%' OR column_name LIKE '%part%' 
                               OR column_name LIKE '%mnt%' OR column_name LIKE '%amount%')
                        ORDER BY ordinal_position
                    """
                    )

                    montant_cols = cur.fetchall()
                    for col_name, data_type, precision, scale in montant_cols:
                        type_str = data_type
                        if precision:
                            type_str += (
                                f"({precision},{scale})" if scale else f"({precision})"
                            )

                        status = (
                            "✅ NUMERIC"
                            if data_type in ["numeric", "double precision", "real"]
                            else "❌ TEXT"
                        )
                        print(f"      {col_name}: {type_str} {status}")
    except Exception as e:
        print(f"   WARN:  Erreur: {e}")

    conn.close()

except Exception as e:
    print(f"   ❌ Erreur: {e}")
    import traceback

    traceback.print_exc()

print("")
