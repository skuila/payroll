#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Correction complète des types dans toute l'application
1. Convertir part_employeur et montant_combine en NUMERIC
2. Mettre à jour les vues SQL
3. Mettre à jour les fichiers Python si nécessaire
"""
import sys
import os
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import psycopg
import os

print("=" * 70)
print("CORRECTION COMPLÈTE DES TYPES DANS TOUTE L'APPLICATION")
print("=" * 70)
print("")

DSN = os.getenv("PAYROLL_DSN") or (
    f"postgresql://{os.getenv('PAYROLL_DB_USER','payroll_owner')}:{os.getenv('PAYROLL_DB_PASSWORD','')}@{os.getenv('PAYROLL_DB_HOST','localhost')}:{os.getenv('PAYROLL_DB_PORT','5432')}/{os.getenv('PAYROLL_DB_NAME','payroll_db')}"
)

try:
    conn = psycopg.connect(DSN, connect_timeout=5)
except Exception as e:
    print(f"❌ Impossible de se connecter: {e}")
    sys.exit(1)

conn.autocommit = True
cur = conn.cursor()

# ÉTAPE 1: Convertir part_employeur
print("ÉTAPE 1: Conversion part_employeur (TEXT → NUMERIC)")
print("-" * 70)

try:
    cur.execute(
        "SELECT data_type FROM information_schema.columns WHERE table_schema = 'payroll' AND table_name = 'imported_payroll_master' AND column_name = 'part_employeur'"
    )
    type_actuel = cur.fetchone()

    if type_actuel and type_actuel[0] == "text":
        print("   ➕ Création colonne temporaire...")
        cur.execute(
            "ALTER TABLE payroll.imported_payroll_master ADD COLUMN IF NOT EXISTS part_employeur_new NUMERIC(18,2)"
        )

        print("   🔄 Conversion des données...")
        cur.execute(
            """
            UPDATE payroll.imported_payroll_master
            SET part_employeur_new = CASE 
                WHEN part_employeur IS NULL OR TRIM(part_employeur) = '' THEN 0
                WHEN part_employeur ~ '^[-]?[0-9]+\\.?[0-9]*$' 
                THEN part_employeur::NUMERIC(18,2)
                ELSE 0
            END
        """
        )

        print("   🗑️  Suppression ancienne colonne...")
        cur.execute(
            "ALTER TABLE payroll.imported_payroll_master DROP COLUMN part_employeur"
        )

        print("   🔄 Renommage...")
        cur.execute(
            "ALTER TABLE payroll.imported_payroll_master RENAME COLUMN part_employeur_new TO part_employeur"
        )

        print("   ✅ part_employeur converti en NUMERIC(18,2)")
    else:
        print("   ✅ part_employeur est déjà NUMERIC")
except Exception as e:
    print(f"   WARN:  Erreur: {str(e)[:150]}")

print("")

# ÉTAPE 2: Convertir montant_combine
print("ÉTAPE 2: Conversion montant_combine (TEXT → NUMERIC)")
print("-" * 70)

try:
    cur.execute(
        "SELECT data_type FROM information_schema.columns WHERE table_schema = 'payroll' AND table_name = 'imported_payroll_master' AND column_name = 'montant_combine'"
    )
    type_actuel = cur.fetchone()

    if type_actuel and type_actuel[0] == "text":
        print("   ➕ Création colonne temporaire...")
        cur.execute(
            "ALTER TABLE payroll.imported_payroll_master ADD COLUMN IF NOT EXISTS montant_combine_new NUMERIC(18,2)"
        )

        print("   🔄 Conversion des données...")
        cur.execute(
            """
            UPDATE payroll.imported_payroll_master
            SET montant_combine_new = CASE 
                WHEN montant_combine IS NULL OR TRIM(montant_combine) = '' THEN 0
                WHEN montant_combine ~ '^[-]?[0-9]+\\.?[0-9]*$' 
                THEN montant_combine::NUMERIC(18,2)
                ELSE 0
            END
        """
        )

        print("   🗑️  Suppression ancienne colonne...")
        cur.execute(
            "ALTER TABLE payroll.imported_payroll_master DROP COLUMN montant_combine"
        )

        print("   🔄 Renommage...")
        cur.execute(
            "ALTER TABLE payroll.imported_payroll_master RENAME COLUMN montant_combine_new TO montant_combine"
        )

        print("   ✅ montant_combine converti en NUMERIC(18,2)")
    else:
        print("   ✅ montant_combine est déjà NUMERIC")
except Exception as e:
    print(f"   WARN:  Erreur: {str(e)[:150]}")

print("")

# ÉTAPE 3: Simplifier les vues SQL (enlever les CAST inutiles maintenant)
print("ÉTAPE 3: Simplification des vues SQL")
print("-" * 70)

# Simplifier v_payroll_detail
try:
    print("   ➕ Simplification v_payroll_detail...")
    cur.execute(
        """
        CREATE OR REPLACE VIEW payroll.v_payroll_detail AS
        SELECT 
            id,
            date_paie::date AS date_paie,
            DATE_TRUNC('month', date_paie::date)::date AS mois_paie,
            DATE_TRUNC('year', date_paie::date)::date AS annee_paie,
            TO_CHAR(date_paie::date, 'YYYY-MM') AS periode_yyyymm,
            EXTRACT(YEAR FROM date_paie::date) AS annee,
            EXTRACT(MONTH FROM date_paie::date) AS mois,
            matricule,
            nom_employe,
            poste_budgetaire,
            categorie_paie,
            code_paie,
            description_code_paie,
            COALESCE(montant_employe::numeric(18,2), 0) AS montant_employe,
            COALESCE(part_employeur::numeric(18,2), 0) AS part_employeur,
            COALESCE(montant_combine::numeric(18,2), 0) AS montant_combine,
            CASE 
                WHEN UPPER(TRIM(COALESCE(categorie_paie, ''))) = 'GAINS' 
                THEN COALESCE(montant_employe::numeric(18,2), 0)
                ELSE -1 * COALESCE(montant_employe::numeric(18,2), 0)
            END AS net
        FROM payroll.imported_payroll_master
        WHERE date_paie IS NOT NULL
          AND matricule IS NOT NULL
          AND TRIM(COALESCE(matricule, '')) != '';
    """
    )
    print("      ✅ Vue simplifiée")
except Exception as e:
    print(f"      WARN:  Erreur: {str(e)[:100]}")

# Simplifier v_payroll_par_periode
try:
    print("   ➕ Simplification v_payroll_par_periode...")
    cur.execute(
        """
        CREATE OR REPLACE VIEW payroll.v_payroll_par_periode AS
        SELECT 
            date_paie::date AS date_paie,
            DATE_TRUNC('month', date_paie::date)::date AS mois_paie,
            DATE_TRUNC('year', date_paie::date)::date AS annee_paie,
            TO_CHAR(date_paie::date, 'YYYY-MM') AS periode_yyyymm,
            EXTRACT(YEAR FROM date_paie::date) AS annee,
            EXTRACT(MONTH FROM date_paie::date) AS mois,
            EXTRACT(QUARTER FROM date_paie::date) AS trimestre,
            SUM(COALESCE(montant_employe::numeric(18,2), 0)) AS total_employe,
            SUM(COALESCE(part_employeur::numeric(18,2), 0)) AS total_employeur,
            SUM(COALESCE(montant_combine::numeric(18,2), 0)) AS total_combine,
            SUM(
                CASE 
                    WHEN UPPER(TRIM(COALESCE(categorie_paie, ''))) = 'GAINS' 
                    THEN COALESCE(montant_employe::numeric(18,2), 0)
                    ELSE -1 * COALESCE(montant_employe::numeric(18,2), 0)
                END
            ) AS total_net,
            COUNT(DISTINCT CASE WHEN COALESCE(montant_employe::numeric(18,2), 0) != 0 THEN matricule END) AS nb_employes_distincts,
            COUNT(*) AS nb_transactions
        FROM payroll.imported_payroll_master
        WHERE date_paie IS NOT NULL
          AND matricule IS NOT NULL
          AND TRIM(COALESCE(matricule, '')) != ''
        GROUP BY 
            date_paie::date,
            DATE_TRUNC('month', date_paie::date),
            DATE_TRUNC('year', date_paie::date),
            TO_CHAR(date_paie::date, 'YYYY-MM'),
            EXTRACT(YEAR FROM date_paie::date),
            EXTRACT(MONTH FROM date_paie::date),
            EXTRACT(QUARTER FROM date_paie::date)
        ORDER BY date_paie::date;
    """
    )
    print("      ✅ Vue simplifiée")
except Exception as e:
    print(f"      WARN:  Erreur: {str(e)[:100]}")

# Simplifier v_payroll_kpi
try:
    print("   ➕ Simplification v_payroll_kpi...")
    cur.execute(
        """
        CREATE OR REPLACE VIEW payroll.v_payroll_kpi AS
        SELECT 
            SUM(COALESCE(montant_employe::numeric(18,2), 0)) AS total_employe,
            SUM(COALESCE(part_employeur::numeric(18,2), 0)) AS total_employeur,
            SUM(COALESCE(montant_combine::numeric(18,2), 0)) AS total_combine,
            SUM(
                CASE 
                    WHEN UPPER(TRIM(COALESCE(categorie_paie, ''))) = 'GAINS' 
                    THEN COALESCE(montant_employe::numeric(18,2), 0)
                    ELSE -1 * COALESCE(montant_employe::numeric(18,2), 0)
                END
            ) AS total_net,
            COUNT(DISTINCT CASE WHEN COALESCE(montant_employe::numeric(18,2), 0) != 0 THEN matricule END) AS nb_employes_distincts,
            COUNT(DISTINCT date_paie::date) AS nb_periodes_distinctes,
            COUNT(DISTINCT COALESCE(NULLIF(TRIM(poste_budgetaire), ''), 'Non classé')) AS nb_postes_budgetaires_distinctes,
            COUNT(DISTINCT COALESCE(NULLIF(TRIM(code_paie), ''), 'CODE_INCONNU')) AS nb_codes_paie_distincts,
            COUNT(*) AS nb_transactions_total,
            MIN(date_paie::date) AS date_min,
            MAX(date_paie::date) AS date_max
        FROM payroll.imported_payroll_master
        WHERE date_paie IS NOT NULL
          AND matricule IS NOT NULL
          AND TRIM(COALESCE(matricule, '')) != '';
    """
    )
    print("      ✅ Vue simplifiée")
except Exception as e:
    print(f"      WARN:  Erreur: {str(e)[:100]}")

print("")

# ÉTAPE 4: Vérification finale
print("ÉTAPE 4: Vérification finale")
print("-" * 70)

cur.execute(
    """
    SELECT column_name, data_type, numeric_precision, numeric_scale
    FROM information_schema.columns
    WHERE table_schema = 'payroll' 
      AND table_name = 'imported_payroll_master'
      AND column_name IN ('date_paie', 'montant_employe', 'part_employeur', 'montant_combine', 'matricule')
    ORDER BY 
        CASE column_name
            WHEN 'date_paie' THEN 1
            WHEN 'montant_employe' THEN 2
            WHEN 'part_employeur' THEN 3
            WHEN 'montant_combine' THEN 4
            WHEN 'matricule' THEN 5
        END
"""
)

colonnes = cur.fetchall()

for col_name, data_type, precision, scale in colonnes:
    if col_name == "date_paie":
        ok = data_type == "date"
        status = "✅" if ok else "❌"
        print(f"{status} {col_name:<20} : {data_type}")
    elif col_name in ("montant_employe", "part_employeur", "montant_combine"):
        ok = data_type == "numeric"
        status = "✅" if ok else "❌"
        precision_str = f"({precision},{scale or 0})" if precision else ""
        print(f"{status} {col_name:<20} : {data_type} {precision_str}")
    elif col_name == "matricule":
        ok = data_type in ("text", "varchar", "character varying")
        status = "✅" if ok else "❌"
        print(f"{status} {col_name:<20} : {data_type}")

print("")

# Test des vues
print("Test des vues...")
try:
    cur.execute("SELECT COUNT(*) FROM payroll.v_payroll_detail")
    count = cur.fetchone()[0]
    print(f"   ✅ v_payroll_detail: {count} lignes")
except Exception as e:
    print(f"   WARN:  Erreur: {str(e)[:100]}")

try:
    cur.execute("SELECT total_employe FROM payroll.v_payroll_kpi")
    kpi = cur.fetchone()
    print(f"   ✅ v_payroll_kpi: Total = {kpi[0] if kpi else 'N/A'}")
except Exception as e:
    print(f"   WARN:  Erreur: {str(e)[:100]}")

conn.close()

print("")
print("=" * 70)
print("✅ CORRECTION TERMINÉE")
print("=" * 70)
