#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exécuter la correction des types de montants"""
import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import psycopg
import os

print("=" * 70)
print("CORRECTION DES TYPES DE MONTANTS")
print("=" * 70)
print("")

# Connexion avec utilisateur ayant les droits — DSN depuis l'environnement
DSN = os.getenv("PAYROLL_DSN") or (
    f"postgresql://{os.getenv('PAYROLL_DB_USER','payroll_owner')}:{os.getenv('PAYROLL_DB_PASSWORD','')}@{os.getenv('PAYROLL_DB_HOST','localhost')}:{os.getenv('PAYROLL_DB_PORT','5432')}/{os.getenv('PAYROLL_DB_NAME','payroll_db')}"
)
conn = psycopg.connect(DSN)
cur = conn.cursor()
try:

    print("1. ÉTAT ACTUEL:")
    print("-" * 70)

    # Vérifier les types actuels
    cur.execute(
        """
        SELECT 
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_schema = 'payroll'
          AND table_name = 'imported_payroll_master'
          AND column_name IN ('montant_employe', 'part_employeur', 'montant_combine')
        ORDER BY column_name
    """
    )

    cols_before = cur.fetchall()
    for col_name, data_type in cols_before:
        status = (
            "✅ NUMERIC"
            if data_type in ["numeric", "double precision", "real"]
            else "❌ TEXT"
        )
        print(f"   {col_name}: {data_type} {status}")

    print("")

    # Colonnes à corriger
    cols_to_fix = []
    for col_name, data_type in cols_before:
        if data_type in ["character varying", "text", "varchar"]:
            cols_to_fix.append(col_name)

    if not cols_to_fix:
        print("   ✅ Toutes les colonnes sont déjà en NUMERIC")
        conn.close()
        sys.exit(0)

    print(f"2. CORRECTION DES COLONNES EN TEXT:")
    print("-" * 70)

    for col_name in cols_to_fix:
        print(f"\n   Correction de {col_name}...")

        try:
            # ALTER TABLE
            sql = f"""
                ALTER TABLE payroll.imported_payroll_master
                ALTER COLUMN {col_name} TYPE NUMERIC(18,2)
                USING CASE
                    WHEN {col_name} ~ '^[-]?[0-9]+\\.?[0-9]*$'
                    THEN {col_name}::numeric(18,2)
                    ELSE 0
                END
            """

            cur.execute(sql)
            conn.commit()

            print(f"      ✅ {col_name} converti en NUMERIC(18,2)")

        except psycopg.errors.InsufficientPrivilege as e:
            print(f"      ❌ Erreur de droits: {str(e)[:100]}")
            print(f"      → Exécuter manuellement avec un superuser (postgres)")
            print(f"\n      SQL à exécuter:")
            print(f"      ALTER TABLE payroll.imported_payroll_master")
            print(f"        ALTER COLUMN {col_name} TYPE NUMERIC(18,2)")
            print(f"        USING CASE")
            print(f"          WHEN {col_name} ~ '^[-]?[0-9]+\\.?[0-9]*$'")
            print(f"          THEN {col_name}::numeric(18,2)")
            print(f"          ELSE 0")
            print(f"        END;")
        except Exception as e:
            print(f"      ❌ Erreur: {str(e)[:150]}")

    print("")

    # Vérification après correction
    print("3. VÉRIFICATION APRÈS CORRECTION:")
    print("-" * 70)

    cur.execute(
        """
        SELECT 
            column_name,
            data_type,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns
        WHERE table_schema = 'payroll'
          AND table_name = 'imported_payroll_master'
          AND column_name IN ('montant_employe', 'part_employeur', 'montant_combine')
        ORDER BY column_name
    """
    )

    cols_after = cur.fetchall()
    all_numeric = True

    for col_name, data_type, precision, scale in cols_after:
        type_str = data_type
        if precision:
            type_str += f"({precision},{scale})"

        if data_type in ["numeric", "double precision", "real"]:
            print(f"   ✅ {col_name}: {type_str}")
        else:
            print(f"   ❌ {col_name}: {type_str} (toujours TEXT)")
            all_numeric = False

    conn.close()

    print("")
    print("=" * 70)

    if all_numeric:
        print("✅ SUCCÈS: Toutes les colonnes de montants sont maintenant en NUMERIC")
    else:
        print("WARN:  Certaines colonnes sont toujours en TEXT")
        print("   → Exécuter le script SQL avec un superuser (postgres)")
        print("   → Script: corriger_montants_en_numeric.sql")
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback

    traceback.print_exc()

print("")
