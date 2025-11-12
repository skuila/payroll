#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lister toutes les colonnes de la table imported_payroll_master"""
import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import os
import psycopg

print("=" * 70)
print("LISTE COMPLÈTE DES COLONNES")
print("=" * 70)
print("")

try:
    # Build DSN from environment or use PAYROLL_DSN if provided.
    dsn = os.getenv("PAYROLL_DSN")
    if not dsn:
        user = os.getenv("PAYROLL_DB_USER", "payroll_owner")
        password = os.getenv("PAYROLL_DB_PASSWORD")
        host = os.getenv("PAYROLL_DB_HOST", "localhost")
        port = os.getenv("PAYROLL_DB_PORT", "5432")
        dbname = os.getenv("PAYROLL_DB_NAME", "payroll_db")
        if password:
            dsn = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        else:
            # Use a placeholder when no password is configured to avoid leaking secrets in the tree.
            dsn = f"postgresql://{user}:__SET_AT_DEPLOY__@{host}:{port}/{dbname}"
            print(
                "   WARN:  Aucune variable PAYROLL_DB_PASSWORD ou PAYROLL_DSN trouvée. Utilisation d'un mot de passe placeholder dans la DSN. Définissez PAYROLL_DB_PASSWORD pour vous connecter."
            )

    # Connect using the constructed DSN
    conn = psycopg.connect(dsn)
    cur = conn.cursor()

    # Vérifier si la table existe
    cur.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'payroll' 
            AND table_name = 'imported_payroll_master'
        )
    """
    )

    table_exists = cur.fetchone()[0]

    if not table_exists:
        print("   ❌ La table imported_payroll_master n'existe pas!")
        print("\n   Vérification des tables disponibles...")

        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'payroll'
            ORDER BY table_name
        """
        )

        tables = cur.fetchall()
        print("\n   Tables dans le schéma payroll:")
        for (table_name,) in tables:
            print(f"      - {table_name}")
    else:
        print("   ✅ Table imported_payroll_master existe\n")

        # Lister toutes les colonnes
        cur.execute(
            """
            SELECT 
                column_name,
                data_type,
                character_maximum_length,
                numeric_precision,
                numeric_scale,
                is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'payroll'
              AND table_name = 'imported_payroll_master'
            ORDER BY ordinal_position
        """
        )

        all_cols = cur.fetchall()

        print(f"   Total colonnes: {len(all_cols)}\n")
        print("   Toutes les colonnes:")
        print("-" * 70)

        montant_cols_found = []

        for col_name, data_type, max_len, precision, scale, nullable in all_cols:
            type_str = data_type
            if max_len:
                type_str += f"({max_len})"
            elif precision:
                type_str += f"({precision},{scale})" if scale else f"({precision})"

            # Marquer les colonnes de montants
            is_montant = any(
                keyword in col_name.lower()
                for keyword in [
                    "montant",
                    "part",
                    "mnt",
                    "amount",
                    "cost",
                    "prix",
                    "total",
                ]
            )

            marker = ""
            if is_montant:
                if data_type in [
                    "numeric",
                    "double precision",
                    "real",
                    "bigint",
                    "integer",
                ]:
                    marker = " ✅ NUMERIC"
                elif data_type in ["character varying", "text", "varchar"]:
                    marker = " ❌ TEXT"
                    montant_cols_found.append({"name": col_name, "type": data_type})

            print(f"   {col_name:40} {type_str:25} {marker}")

        print("-" * 70)

        if montant_cols_found:
            print(f"\n   Colonnes de montants en TEXT à corriger:")
            for col in montant_cols_found:
                print(f"      - {col['name']}: {col['type']}")

    conn.close()

except Exception as e:
    print(f"   ❌ Erreur: {e}")
    import traceback

    traceback.print_exc()

print("")
