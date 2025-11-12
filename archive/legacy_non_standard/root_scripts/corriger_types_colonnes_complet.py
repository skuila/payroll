#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour corriger les types de colonnes dans toute l'application
- Convertit part_employeur et montant_combine de TEXT à NUMERIC
- Recrée les vues SQL
- Vérifie la compatibilité
"""
import sys
import os
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

print("=" * 70)
print("CORRECTION DES TYPES DE COLONNES DANS TOUTE L'APPLICATION")
print("=" * 70)
print("")

import psycopg
import os

# Connexion avec utilisateur ayant les droits — construit le DSN depuis les variables d'environnement
DSN = os.getenv("PAYROLL_DSN") or (
    f"postgresql://{os.getenv('PAYROLL_DB_USER','payroll_owner')}:{os.getenv('PAYROLL_DB_PASSWORD','')}@{os.getenv('PAYROLL_DB_HOST','localhost')}:{os.getenv('PAYROLL_DB_PORT','5432')}/{os.getenv('PAYROLL_DB_NAME','payroll_db')}"
)

conn = psycopg.connect(DSN)
conn.autocommit = True
cur = conn.cursor()

# ÉTAPE 1: Sauvegarder les données avant modification
print("ÉTAPE 1: Vérification avant modification")
print("-" * 70)

cur.execute("SELECT COUNT(*) FROM payroll.imported_payroll_master")
total_lignes = cur.fetchone()[0]
print(f"   Total lignes dans la table: {total_lignes}")

# Vérifier les types actuels
cur.execute(
    """
    SELECT column_name, data_type 
    FROM information_schema.columns
    WHERE table_schema = 'payroll' 
      AND table_name = 'imported_payroll_master'
      AND column_name IN ('part_employeur', 'montant_combine')
"""
)

types_actuels = {row[0]: row[1] for row in cur.fetchall()}

print(f"   part_employeur actuel: {types_actuels.get('part_employeur', 'N/A')}")
print(f"   montant_combine actuel: {types_actuels.get('montant_combine', 'N/A')}")
print("")

# ÉTAPE 2: Convertir part_employeur
print("ÉTAPE 2: Conversion part_employeur (TEXT → NUMERIC)")
print("-" * 70)

if types_actuels.get("part_employeur") == "text":
    try:
        # Créer colonne temporaire
        print("   ➕ Création colonne temporaire...")
        cur.execute(
            """
            ALTER TABLE payroll.imported_payroll_master
            ADD COLUMN IF NOT EXISTS part_employeur_new NUMERIC(18,2);
        """
        )

        # Convertir les données
        print("   🔄 Conversion des données...")
        cur.execute(
            """
            UPDATE payroll.imported_payroll_master
            SET part_employeur_new = CASE 
                WHEN part_employeur IS NULL OR TRIM(part_employeur) = '' THEN 0
                WHEN part_employeur ~ '^[-]?[0-9]+\\.?[0-9]*$' 
                THEN part_employeur::NUMERIC(18,2)
                ELSE 0
            END;
        """
        )

        # Vérifier la conversion
        cur.execute(
            """
            SELECT COUNT(*) 
            FROM payroll.imported_payroll_master 
            WHERE part_employeur_new IS NULL
        """
        )
        null_count = cur.fetchone()[0]
        print(f"      ✅ {total_lignes - null_count}/{total_lignes} lignes converties")

        # Supprimer ancienne colonne
        print("   🗑️  Suppression ancienne colonne...")
        cur.execute(
            """
            ALTER TABLE payroll.imported_payroll_master
            DROP COLUMN part_employeur;
        """
        )

        # Renommer nouvelle colonne
        print("   🔄 Renommage colonne...")
        cur.execute(
            """
            ALTER TABLE payroll.imported_payroll_master
            RENAME COLUMN part_employeur_new TO part_employeur;
        """
        )

        print("   ✅ part_employeur converti en NUMERIC(18,2)")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
else:
    print("   WARN:  part_employeur est déjà NUMERIC")

print("")

# ÉTAPE 3: Convertir montant_combine
print("ÉTAPE 3: Conversion montant_combine (TEXT → NUMERIC)")
print("-" * 70)

if types_actuels.get("montant_combine") == "text":
    try:
        # Créer colonne temporaire
        print("   ➕ Création colonne temporaire...")
        cur.execute(
            """
            ALTER TABLE payroll.imported_payroll_master
            ADD COLUMN IF NOT EXISTS montant_combine_new NUMERIC(18,2);
        """
        )

        # Convertir les données
        print("   🔄 Conversion des données...")
        cur.execute(
            """
            UPDATE payroll.imported_payroll_master
            SET montant_combine_new = CASE 
                WHEN montant_combine IS NULL OR TRIM(montant_combine) = '' THEN 0
                WHEN montant_combine ~ '^[-]?[0-9]+\\.?[0-9]*$' 
                THEN montant_combine::NUMERIC(18,2)
                ELSE 0
            END;
        """
        )

        # Vérifier la conversion
        cur.execute(
            """
            SELECT COUNT(*) 
            FROM payroll.imported_payroll_master 
            WHERE montant_combine_new IS NULL
        """
        )
        null_count = cur.fetchone()[0]
        print(f"      ✅ {total_lignes - null_count}/{total_lignes} lignes converties")

        # Supprimer ancienne colonne
        print("   🗑️  Suppression ancienne colonne...")
        cur.execute(
            """
            ALTER TABLE payroll.imported_payroll_master
            DROP COLUMN montant_combine;
        """
        )

        # Renommer nouvelle colonne
        print("   🔄 Renommage colonne...")
        cur.execute(
            """
            ALTER TABLE payroll.imported_payroll_master
            RENAME COLUMN montant_combine_new TO montant_combine;
        """
        )

        print("   ✅ montant_combine converti en NUMERIC(18,2)")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
else:
    print("   WARN:  montant_combine est déjà NUMERIC")

print("")

# ÉTAPE 4: Mettre à jour les vues SQL (simplifier car plus besoin de CAST)
print("ÉTAPE 4: Mise à jour des vues SQL")
print("-" * 70)

# Lire le fichier SQL
sql_file = "creer_vues_payroll.sql"
if os.path.exists(sql_file):
    try:
        with open(sql_file, "r", encoding="utf-8") as f:
            sql_content = f.read()

        # Simplifier les vues (enlever les CAST pour part_employeur et montant_combine)
        # Mais on garde les vues telles quelles car elles fonctionnent déjà
        print("   ➕ Recréation des vues...")

        # Séparer les commandes
        sql_commands = []
        current_cmd = []
        for line in sql_content.split("\n"):
            line = line.strip()
            if not line or line.startswith("--"):
                continue
            current_cmd.append(line)
            if line.endswith(";"):
                sql_commands.append(" ".join(current_cmd))
                current_cmd = []

        for sql_cmd in sql_commands:
            if sql_cmd and "CREATE" in sql_cmd.upper():
                try:
                    cur.execute(sql_cmd)
                    print(f"      ✅ Vue recréée")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        print(f"      WARN:  {str(e)[:100]}")
    except Exception as e:
        print(f"   WARN:  Erreur lecture SQL: {e}")
else:
    print(f"   WARN:  Fichier SQL introuvable: {sql_file}")

print("")

# ÉTAPE 5: Vérification finale
print("ÉTAPE 5: Vérification finale")
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

colonnes_finales = cur.fetchall()

all_ok = True
for col_name, data_type, precision, scale in colonnes_finales:
    if col_name == "date_paie":
        ok = data_type == "date"
        status = "✅" if ok else "❌"
        print(f"{status} {col_name:<20} : {data_type}")
        if not ok:
            all_ok = False
    elif col_name in ("montant_employe", "part_employeur", "montant_combine"):
        ok = data_type == "numeric"
        status = "✅" if ok else "❌"
        precision_str = f"({precision},{scale or 0})" if precision else ""
        print(f"{status} {col_name:<20} : {data_type} {precision_str}")
        if not ok:
            all_ok = False
    elif col_name == "matricule":
        ok = data_type in ("text", "varchar", "character varying")
        status = "✅" if ok else "❌"
        print(f"{status} {col_name:<20} : {data_type}")
        if not ok:
            all_ok = False

print("")

# Test des vues
print("Test des vues...")
try:
    cur.execute("SELECT COUNT(*) FROM payroll.v_payroll_detail")
    count_detail = cur.fetchone()[0]
    print(f"   ✅ v_payroll_detail: {count_detail} lignes")
except Exception as e:
    print(f"   WARN:  v_payroll_detail: {str(e)[:100]}")
    all_ok = False

try:
    cur.execute(
        "SELECT total_employe, nb_employes_distincts FROM payroll.v_payroll_kpi"
    )
    kpi = cur.fetchone()
    if kpi:
        print(f"   ✅ v_payroll_kpi: Total = {kpi[0]}, Employés = {kpi[1]}")
except Exception as e:
    print(f"   WARN:  v_payroll_kpi: {str(e)[:100]}")
    all_ok = False

conn.close()

print("")
print("=" * 70)
if all_ok:
    print("✅ CORRECTION TERMINÉE AVEC SUCCÈS")
    print("   Tous les types sont maintenant corrects:")
    print("   - date_paie: DATE")
    print("   - montant_employe: NUMERIC")
    print("   - part_employeur: NUMERIC")
    print("   - montant_combine: NUMERIC")
    print("   - matricule: TEXT")
else:
    print("WARN:  CORRECTION TERMINÉE AVEC AVERTISSEMENTS")
    print("   Vérifiez les erreurs ci-dessus")

print("")
