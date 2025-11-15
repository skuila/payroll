#!/usr/bin/env python3
"""
Vérifie les imports récents et les transactions créées
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from config.connection_standard import open_connection

settings.bootstrap_env()


def verifier_imports():
    """Vérifie les imports et transactions"""

    print("=" * 70)
    print("VÉRIFICATION DES IMPORTS ET TRANSACTIONS")
    print("=" * 70)

    conn = open_connection()
    cur = conn.cursor()

    try:
        # 1. Vérifier les batches d'import récents
        print("\n1. BATCHES D'IMPORT RÉCENTS:")
        print("-" * 70)
        cur.execute(
            """
            SELECT 
                batch_id,
                file_name,
                pay_date,
                rows_count,
                status,
                created_at
            FROM payroll.import_batches
            ORDER BY created_at DESC
            LIMIT 10
        """
        )
        batches = cur.fetchall()
        if batches:
            for batch in batches:
                batch_id, file_name, pay_date, rows_count, status, created_at = batch
                print(f"   Batch {batch_id}: {file_name}")
                print(f"      Date de paie: {pay_date}")
                print(f"      Lignes: {rows_count}")
                print(f"      Status: {status}")
                print(f"      Créé: {created_at}")
                print()
        else:
            print("   ⚠️  Aucun batch d'import trouvé")

        # 2. Vérifier les données dans imported_payroll_master
        print("\n2. DONNÉES DANS imported_payroll_master:")
        print("-" * 70)
        cur.execute(
            """
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT date_paie) as nb_dates,
                MIN(date_paie) as date_min,
                MAX(date_paie) as date_max
            FROM payroll.imported_payroll_master
        """
        )
        result = cur.fetchone()
        if result:
            total, nb_dates, date_min, date_max = result
            print(f"   Total lignes: {total}")
            print(f"   Nombre de dates distinctes: {nb_dates}")
            if date_min:
                print(f"   Date min: {date_min}")
                print(f"   Date max: {date_max}")

            # Détails par date
            if nb_dates > 0:
                print("\n   Détails par date de paie:")
                cur.execute(
                    """
                    SELECT 
                        date_paie,
                        COUNT(*) as nb_lignes,
                        COUNT(DISTINCT matricule) as nb_employes
                    FROM payroll.imported_payroll_master
                    GROUP BY date_paie
                    ORDER BY date_paie DESC
                """
                )
                dates = cur.fetchall()
                for date_paie, nb_lignes, nb_employes in dates:
                    print(
                        f"      {date_paie}: {nb_lignes} lignes, {nb_employes} employés"
                    )
        else:
            print("   ⚠️  Aucune donnée dans imported_payroll_master")

        # 3. Vérifier les transactions dans payroll_transactions
        print("\n3. TRANSACTIONS DANS payroll_transactions:")
        print("-" * 70)
        cur.execute(
            """
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT pay_date) as nb_dates,
                MIN(pay_date) as date_min,
                MAX(pay_date) as date_max
            FROM payroll.payroll_transactions
        """
        )
        result = cur.fetchone()
        if result:
            total, nb_dates, date_min, date_max = result
            print(f"   Total transactions: {total}")
            print(f"   Nombre de dates distinctes: {nb_dates}")
            if date_min:
                print(f"   Date min: {date_min}")
                print(f"   Date max: {date_max}")

            # Détails par date
            if nb_dates > 0:
                print("\n   Détails par date de paie:")
                cur.execute(
                    """
                    SELECT 
                        pay_date,
                        COUNT(*) as nb_transactions,
                        COUNT(DISTINCT employee_id) as nb_employes
                    FROM payroll.payroll_transactions
                    GROUP BY pay_date
                    ORDER BY pay_date DESC
                """
                )
                dates = cur.fetchall()
                for pay_date, nb_trans, nb_employes in dates:
                    print(
                        f"      {pay_date}: {nb_trans} transactions, {nb_employes} employés"
                    )
        else:
            print("   ⚠️  Aucune transaction dans payroll_transactions")

        # 4. Comparer imported_payroll_master vs payroll_transactions
        print("\n4. COMPARAISON imported_payroll_master vs payroll_transactions:")
        print("-" * 70)
        cur.execute(
            """
            SELECT 
                COALESCE(ipm.date_paie, pt.pay_date) as date_paie,
                COUNT(DISTINCT ipm.id) as lignes_importees,
                COUNT(DISTINCT pt.transaction_id) as transactions_creees
            FROM payroll.imported_payroll_master ipm
            FULL OUTER JOIN payroll.payroll_transactions pt 
                ON ipm.date_paie = pt.pay_date
            GROUP BY COALESCE(ipm.date_paie, pt.pay_date)
            ORDER BY date_paie DESC
        """
        )
        comparaisons = cur.fetchall()
        if comparaisons:
            for date_paie, lignes, transactions in comparaisons:
                if lignes > 0 and transactions == 0:
                    print(
                        f"   ❌ {date_paie}: {lignes} lignes importées mais 0 transactions créées"
                    )
                elif lignes > 0 and transactions > 0:
                    print(
                        f"   ✅ {date_paie}: {lignes} lignes → {transactions} transactions"
                    )
                elif lignes == 0 and transactions > 0:
                    print(
                        f"   ⚠️  {date_paie}: 0 lignes mais {transactions} transactions"
                    )
        else:
            print("   ⚠️  Aucune comparaison possible")

        # 5. Vérifier les périodes (pay_periods)
        print("\n5. PÉRIODES DE PAIE (pay_periods):")
        print("-" * 70)
        cur.execute(
            """
            SELECT 
                pay_date,
                status,
                period_seq_in_year
            FROM payroll.pay_periods
            ORDER BY pay_date DESC
            LIMIT 10
        """
        )
        periods = cur.fetchall()
        if periods:
            for pay_date, status, seq in periods:
                print(f"   {pay_date}: status={status}, seq={seq}")
        else:
            print("   ⚠️  Aucune période trouvée")

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    verifier_imports()
