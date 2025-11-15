#!/usr/bin/env python3
"""
Crée les transactions dans payroll_transactions à partir de imported_payroll_master
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from config.connection_standard import open_connection

settings.bootstrap_env()


def creer_transactions():
    """Crée les transactions depuis imported_payroll_master"""

    print("=" * 70)
    print("CRÉATION DES TRANSACTIONS DEPUIS imported_payroll_master")
    print("=" * 70)

    conn = open_connection()
    cur = conn.cursor()

    try:
        # Vérifier combien de lignes à transformer
        cur.execute(
            """
            SELECT COUNT(*) 
            FROM payroll.imported_payroll_master ipm
            WHERE NOT EXISTS (
                SELECT 1 FROM payroll.payroll_transactions pt
                WHERE pt.pay_date = ipm.date_paie
                AND pt.source_file = ipm.source_file
                AND pt.source_row_no = ipm.source_row_number
            )
        """
        )
        nb_a_creer = cur.fetchone()[0]
        print(f"\n📊 Lignes à transformer: {nb_a_creer}")

        if nb_a_creer == 0:
            print("✅ Toutes les transactions sont déjà créées")
            return

        # Vérifier les employés
        cur.execute("SELECT COUNT(*) FROM core.employees")
        nb_employes = cur.fetchone()[0]
        print(f"📊 Employés dans core.employees: {nb_employes}")

        if nb_employes == 0:
            print("⚠️  Aucun employé trouvé dans core.employees")
            print(
                "   Il faut d'abord créer les employés depuis imported_payroll_master"
            )
            return

        # Créer les transactions
        print("\n🔄 Création des transactions...")

        sql = """
        INSERT INTO payroll.payroll_transactions (
            employee_id,
            pay_date,
            pay_code,
            amount_cents,
            source_file,
            source_row_no
        )
        SELECT 
            e.employee_id,
            ipm.date_paie,
            COALESCE(ipm.code_paie, 'NON_SPECIFIE'),
            ROUND(COALESCE(ipm.montant_employe, 0) * 100)::BIGINT as amount_cents,
            ipm.source_file,
            ipm.source_row_number
        FROM payroll.imported_payroll_master ipm
        LEFT JOIN core.employees e ON
            COALESCE(
                NULLIF(LOWER(e.matricule), ''),
                LOWER(e.matricule_norm),
                LOWER(e.matricule_raw)
            ) = LOWER(TRIM(ipm.matricule))
        WHERE NOT EXISTS (
            SELECT 1 FROM payroll.payroll_transactions pt
            WHERE pt.pay_date = ipm.date_paie
            AND pt.source_file = ipm.source_file
            AND pt.source_row_no = ipm.source_row_number
        )
        AND ipm.montant_employe IS NOT NULL
        AND ipm.montant_employe != 0
        AND ipm.matricule IS NOT NULL
        AND TRIM(ipm.matricule) <> ''
        AND e.employee_id IS NOT NULL
        """

        cur.execute(sql)
        nb_crees = cur.rowcount
        conn.commit()

        print(f"✅ {nb_crees} transactions créées")

        # Vérifier les lignes sans employé correspondant
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

        if nb_sans_employe > 0:
            print(f"\n⚠️  {nb_sans_employe} lignes sans employé correspondant")
            print("   Il faut créer les employés manquants")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Erreur: {e}")
        import traceback

        traceback.print_exc()
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    creer_transactions()
