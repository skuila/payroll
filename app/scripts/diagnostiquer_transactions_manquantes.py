#!/usr/bin/env python3
"""
Diagnostique pourquoi certaines transactions ne sont pas créées
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from config.connection_standard import open_connection

settings.bootstrap_env()


def diagnostiquer():
    """Diagnostique les transactions manquantes"""

    print("=" * 70)
    print("DIAGNOSTIC DES TRANSACTIONS MANQUANTES")
    print("=" * 70)

    conn = open_connection()
    cur = conn.cursor()

    try:
        # 1. Lignes sans employé correspondant
        print("\n1. LIGNES SANS EMPLOYÉ CORRESPONDANT:")
        print("-" * 70)
        cur.execute(
            """
            SELECT COUNT(*) 
            FROM payroll.imported_payroll_master ipm
            LEFT JOIN core.employees e ON e.matricule = ipm.matricule
            WHERE e.employee_id IS NULL
            AND ipm.montant_employe IS NOT NULL
            AND ipm.montant_employe != 0
        """
        )
        nb_sans_employe = cur.fetchone()[0]
        print(f"   {nb_sans_employe} lignes sans employé correspondant")

        if nb_sans_employe > 0:
            print("\n   Exemples de matricules sans employé:")
            cur.execute(
                """
                SELECT DISTINCT ipm.matricule, COUNT(*) as nb_lignes
                FROM payroll.imported_payroll_master ipm
                LEFT JOIN core.employees e ON e.matricule = ipm.matricule
                WHERE e.employee_id IS NULL
                AND ipm.montant_employe IS NOT NULL
                AND ipm.montant_employe != 0
                GROUP BY ipm.matricule
                ORDER BY nb_lignes DESC
                LIMIT 10
            """
            )
            exemples = cur.fetchall()
            for matricule, nb in exemples:
                print(f"      {matricule}: {nb} lignes")

        # 2. Lignes avec montant = 0 ou NULL
        print("\n2. LIGNES AVEC MONTANT = 0 OU NULL:")
        print("-" * 70)
        cur.execute(
            """
            SELECT 
                COUNT(*) FILTER (WHERE montant_employe IS NULL) as nb_null,
                COUNT(*) FILTER (WHERE montant_employe = 0) as nb_zero
            FROM payroll.imported_payroll_master
        """
        )
        result = cur.fetchone()
        nb_null, nb_zero = result
        print(f"   Montant NULL: {nb_null}")
        print(f"   Montant = 0: {nb_zero}")

        # 3. Lignes déjà transformées
        print("\n3. LIGNES DÉJÀ TRANSFORMÉES:")
        print("-" * 70)
        cur.execute(
            """
            SELECT COUNT(*) 
            FROM payroll.imported_payroll_master ipm
            WHERE EXISTS (
                SELECT 1 FROM payroll.payroll_transactions pt
                WHERE pt.pay_date = ipm.date_paie
                AND pt.source_file = ipm.source_file
                AND pt.source_row_no = ipm.source_row_number
            )
        """
        )
        nb_deja_transformees = cur.fetchone()[0]
        print(f"   {nb_deja_transformees} lignes déjà transformées")

        # 4. Résumé
        print("\n4. RÉSUMÉ:")
        print("-" * 70)
        cur.execute("SELECT COUNT(*) FROM payroll.imported_payroll_master")
        total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM payroll.payroll_transactions")
        total_transactions = cur.fetchone()[0]

        print(f"   Total lignes dans imported_payroll_master: {total}")
        print(f"   Total transactions créées: {total_transactions}")
        print(f"   Lignes sans employé: {nb_sans_employe}")
        print(f"   Lignes avec montant NULL/0: {nb_null + nb_zero}")
        print(f"   Lignes déjà transformées: {nb_deja_transformees}")

        manquantes = total - total_transactions - (nb_null + nb_zero) - nb_sans_employe
        print(f"\n   ⚠️  Transactions manquantes (non expliquées): {manquantes}")

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    diagnostiquer()
