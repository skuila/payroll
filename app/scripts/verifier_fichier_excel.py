#!/usr/bin/env python3
"""
Vérifie le fichier Excel et compare avec les données importées
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from config.connection_standard import open_connection

settings.bootstrap_env()


def verifier_fichier_excel():
    """Vérifie le fichier Excel et compare avec la DB"""

    fichier_excel = Path(r"C:\Users\SZERTYUIOPMLMM\Desktop\APP\app\nouveau.xlsx")

    if not fichier_excel.exists():
        print(f"❌ Fichier non trouvé: {fichier_excel}")
        return

    print("=" * 70)
    print("VÉRIFICATION DU FICHIER EXCEL")
    print("=" * 70)

    # Lire le fichier Excel
    print(f"\n📄 Lecture du fichier: {fichier_excel.name}")
    try:
        df = pd.read_excel(fichier_excel)
        print(f"   Colonnes: {list(df.columns)}")
        print(f"   Nombre de lignes: {len(df)}")

        # Afficher les premières lignes
        print("\n📋 Premières lignes du fichier:")
        print(df.head(10).to_string())

        # Compter les lignes avec montant != 0
        if "montant" in df.columns or "montant_employe" in df.columns:
            col_montant = "montant" if "montant" in df.columns else "montant_employe"
            df_montant = pd.to_numeric(df[col_montant], errors="coerce")
            nb_non_zero = (df_montant != 0).sum()
            nb_zero = (df_montant == 0).sum()
            nb_null = df_montant.isna().sum()
            print("\n💰 Analyse des montants:")
            print(f"   Lignes avec montant != 0: {nb_non_zero}")
            print(f"   Lignes avec montant = 0: {nb_zero}")
            print(f"   Lignes avec montant NULL: {nb_null}")

        # Vérifier les dates
        if "date de paie" in df.columns or "date_paie" in df.columns:
            col_date = "date de paie" if "date de paie" in df.columns else "date_paie"
            dates = df[col_date].unique()
            print("\n📅 Dates de paie dans le fichier:")
            for date in dates[:5]:
                print(f"   {date}")

        # Vérifier les matricules
        if "matricule" in df.columns:
            nb_matricules = df["matricule"].nunique()
            print(f"\n👤 Nombre de matricules uniques: {nb_matricules}")

    except Exception as e:
        print(f"❌ Erreur lors de la lecture: {e}")
        import traceback

        traceback.print_exc()
        return

    # Vérifier dans la DB
    print("\n" + "=" * 70)
    print("VÉRIFICATION DANS LA BASE DE DONNÉES")
    print("=" * 70)

    conn = open_connection()
    cur = conn.cursor()

    try:
        # Vérifier les imports récents pour ce fichier
        print("\n📦 Imports récents pour 'nouveau.xlsx':")
        cur.execute(
            """
            SELECT batch_id, file_name, pay_date, rows_count, status, created_at
            FROM payroll.import_batches
            WHERE file_name LIKE '%nouveau%'
            ORDER BY created_at DESC
            LIMIT 5
        """
        )
        batches = cur.fetchall()
        if batches:
            for batch in batches:
                batch_id, file_name, pay_date, rows_count, status, created_at = batch
                print(f"   Batch {batch_id}: {file_name}")
                print(f"      Date: {pay_date}, Lignes: {rows_count}, Status: {status}")
                print(f"      Créé: {created_at}")
        else:
            print("   ⚠️  Aucun import trouvé pour ce fichier")

        # Vérifier imported_payroll_master
        print("\n📊 Données dans imported_payroll_master:")
        cur.execute(
            """
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT date_paie) as nb_dates,
                COUNT(DISTINCT matricule) as nb_matricules,
                SUM(CASE WHEN montant_employe != 0 AND montant_employe IS NOT NULL THEN 1 ELSE 0 END) as nb_non_zero
            FROM payroll.imported_payroll_master
            WHERE source_file LIKE '%nouveau%'
        """
        )
        result = cur.fetchone()
        if result:
            total, nb_dates, nb_matricules, nb_non_zero = result
            print(f"   Total lignes: {total}")
            print(f"   Dates distinctes: {nb_dates}")
            print(f"   Matricules distincts: {nb_matricules}")
            print(f"   Lignes avec montant != 0: {nb_non_zero}")

        # Vérifier payroll_transactions
        print("\n💳 Transactions dans payroll_transactions:")
        cur.execute(
            """
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT pay_date) as nb_dates,
                COUNT(DISTINCT employee_id) as nb_employes
            FROM payroll.payroll_transactions pt
            WHERE EXISTS (
                SELECT 1 FROM payroll.imported_payroll_master ipm
                WHERE ipm.source_file LIKE '%nouveau%'
                AND ipm.date_paie = pt.pay_date
                AND ipm.source_row_number = pt.source_row_no
            )
        """
        )
        result = cur.fetchone()
        if result:
            total, nb_dates, nb_employes = result
            print(f"   Total transactions: {total}")
            print(f"   Dates distinctes: {nb_dates}")
            print(f"   Employés distincts: {nb_employes}")

        # Comparer ligne par ligne (échantillon)
        print("\n🔍 Comparaison ligne par ligne (échantillon):")
        cur.execute(
            """
            SELECT 
                ipm.matricule,
                ipm.montant_employe,
                ipm.date_paie,
                ipm.source_row_number,
                CASE WHEN pt.transaction_id IS NOT NULL THEN 'OUI' ELSE 'NON' END as transaction_creee
            FROM payroll.imported_payroll_master ipm
            LEFT JOIN payroll.payroll_transactions pt 
                ON pt.pay_date = ipm.date_paie
                AND pt.source_file = ipm.source_file
                AND pt.source_row_no = ipm.source_row_number
            WHERE ipm.source_file LIKE '%nouveau%'
            ORDER BY ipm.source_row_number
            LIMIT 20
        """
        )
        lignes = cur.fetchall()
        if lignes:
            print("   Matricule | Montant | Date | Row | Transaction créée?")
            print("   " + "-" * 60)
            for ligne in lignes:
                matricule, montant, date_paie, row_no, trans = ligne
                print(f"   {matricule} | {montant} | {date_paie} | {row_no} | {trans}")

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    verifier_fichier_excel()
