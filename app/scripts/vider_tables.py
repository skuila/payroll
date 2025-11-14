#!/usr/bin/env python3
"""
Script pour vider les tables de la base de données
===================================================

Ce script supprime toutes les données des tables principales
pour permettre un nouveau test avec un fichier frais.

ATTENTION: Cette opération est IRRÉVERSIBLE !

Auteur: Système de gestion
Date: 2025-11-11
"""

from config.connection_standard import get_connection
import sys


def confirmer_suppression():
    """Demande confirmation avant de supprimer."""
    print("=" * 70)
    print("⚠️  ATTENTION - SUPPRESSION DE TOUTES LES DONNÉES")
    print("=" * 70)
    print()
    print("Cette opération va supprimer:")
    print("  • Toutes les transactions de paie (payroll.payroll_transactions)")
    print("  • Toutes les données importées (payroll.imported_payroll_master)")
    print("  • Tous les batches d'import (payroll.import_batches)")
    print("  • Toutes les périodes (payroll.pay_periods)")
    print("  • Tous les employés (core.employees)")
    print()
    print("⚠️  CETTE OPÉRATION EST IRRÉVERSIBLE !")
    print()

    reponse = input("Voulez-vous continuer? (tapez 'OUI' en majuscules): ")

    return reponse == "OUI"


def compter_donnees():
    """Compte les données actuelles."""
    from config.connection_standard import run_select

    print()
    print("📊 DONNÉES ACTUELLES:")
    print("-" * 70)

    try:
        # Compter les transactions
        result = run_select("SELECT COUNT(*) FROM payroll.payroll_transactions")
        nb_transactions = result[0][0] if result else 0
        print(f"  • Transactions de paie: {nb_transactions}")

        # Compter les données importées
        result = run_select("SELECT COUNT(*) FROM payroll.imported_payroll_master")
        nb_imported = result[0][0] if result else 0
        print(f"  • Données importées: {nb_imported}")

        # Compter les batches
        result = run_select("SELECT COUNT(*) FROM payroll.import_batches")
        nb_batches = result[0][0] if result else 0
        print(f"  • Batches d'import: {nb_batches}")

        # Compter les périodes
        result = run_select("SELECT COUNT(*) FROM payroll.pay_periods")
        nb_periods = result[0][0] if result else 0
        print(f"  • Périodes: {nb_periods}")

        # Compter les employés
        result = run_select("SELECT COUNT(*) FROM core.employees")
        nb_employes = result[0][0] if result else 0
        print(f"  • Employés: {nb_employes}")

        print("-" * 70)
        print()

        return nb_transactions, nb_employes

    except Exception as e:
        print(f"❌ Erreur lors du comptage: {e}")
        return 0, 0


def vider_tables():
    """Vide toutes les tables principales dans l'ordre correct (respect des FK)."""
    print()
    print("🗑️  SUPPRESSION EN COURS...")
    print("-" * 70)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Supprimer les transactions de paie (AVANT les employés pour respecter FK)
                print("  1. Suppression des transactions de paie...")
                cur.execute("DELETE FROM payroll.payroll_transactions")
                nb_transactions = cur.rowcount
                print(f"     ✅ {nb_transactions} transactions supprimées")

                # 2. Supprimer les données dans imported_payroll_master
                print("  2. Suppression des données importées...")
                cur.execute("DELETE FROM payroll.imported_payroll_master")
                nb_imported = cur.rowcount
                print(
                    f"     ✅ {nb_imported} lignes supprimées dans imported_payroll_master"
                )

                # 3. Supprimer les batches d'import
                print("  3. Suppression des batches d'import...")
                cur.execute("DELETE FROM payroll.import_batches")
                nb_batches = cur.rowcount
                print(f"     ✅ {nb_batches} batches supprimés")

                # 4. Supprimer les périodes
                print("  4. Suppression des périodes...")
                cur.execute("DELETE FROM payroll.pay_periods")
                nb_periods = cur.rowcount
                print(f"     ✅ {nb_periods} périodes supprimées")

                # 5. Supprimer les employés orphelins (après les transactions)
                # Note: Comme toutes les transactions sont supprimées, tous les employés deviennent orphelins
                # On utilise la logique standardisée pour garantir la cohérence
                print("  5. Suppression des employés orphelins...")
                # Compter AVANT suppression
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM core.employees 
                    WHERE employee_id IS NOT NULL
                    AND employee_id NOT IN (
                        SELECT DISTINCT employee_id 
                        FROM payroll.payroll_transactions
                        WHERE employee_id IS NOT NULL
                    )
                """
                )
                nb_employes = cur.fetchone()[0] if cur.rowcount > 0 else 0

                # Supprimer les employés orphelins
                cur.execute(
                    """
                    DELETE FROM core.employees 
                    WHERE employee_id IS NOT NULL
                    AND employee_id NOT IN (
                        SELECT DISTINCT employee_id 
                        FROM payroll.payroll_transactions
                        WHERE employee_id IS NOT NULL
                    )
                """
                )
                print(
                    f"     ✅ {nb_employes} employés orphelins supprimés (sans transactions dans aucune période)"
                )

                # 6. Réinitialiser les séquences si nécessaire
                print("  6. Réinitialisation des séquences...")
                try:
                    cur.execute(
                        """
                        SELECT setval('payroll.payroll_transactions_id_seq', 1, false);
                    """
                    )
                    print("     ✅ Séquences réinitialisées")
                except Exception as seq_error:
                    print(f"     ⚠️  Réinitialisation séquences: {seq_error}")

            # Commit la transaction
            conn.commit()
            print("-" * 70)
            print("✅ SUPPRESSION TERMINÉE AVEC SUCCÈS")

        return True

    except Exception as e:
        print(f"❌ Erreur lors de la suppression: {e}")
        print("La transaction a été annulée (rollback automatique)")
        return False


def verifier_suppression():
    """Vérifie que les tables sont bien vides."""
    from config.connection_standard import run_select

    print()
    print("🔍 VÉRIFICATION:")
    print("-" * 70)

    try:
        # Vérifier les transactions
        result = run_select("SELECT COUNT(*) FROM payroll.payroll_transactions")
        nb_transactions = result[0][0] if result else 0

        # Vérifier les données importées
        result = run_select("SELECT COUNT(*) FROM payroll.imported_payroll_master")
        nb_imported = result[0][0] if result else 0

        # Vérifier les batches
        result = run_select("SELECT COUNT(*) FROM payroll.import_batches")
        nb_batches = result[0][0] if result else 0

        # Vérifier les périodes
        result = run_select("SELECT COUNT(*) FROM payroll.pay_periods")
        nb_periods = result[0][0] if result else 0

        # Vérifier les employés
        result = run_select("SELECT COUNT(*) FROM core.employees")
        nb_employes = result[0][0] if result else 0

        print(f"  • Transactions restantes: {nb_transactions}")
        print(f"  • Données importées restantes: {nb_imported}")
        print(f"  • Batches restants: {nb_batches}")
        print(f"  • Périodes restantes: {nb_periods}")
        print(f"  • Employés restants: {nb_employes}")
        print("-" * 70)

        if (
            nb_transactions == 0
            and nb_imported == 0
            and nb_batches == 0
            and nb_periods == 0
            and nb_employes == 0
        ):
            print("✅ Les tables sont vides")
            return True
        else:
            print("⚠️  Attention: Des données subsistent")
            return False

    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        return False


def main():
    """Point d'entrée principal."""
    print()
    print("=" * 70)
    print("SCRIPT DE VIDAGE DES TABLES")
    print("=" * 70)

    # 1. Compter les données actuelles
    compter_donnees()

    # Vérifier si toutes les tables sont vides (utilise compter_donnees mais vérifie toutes les tables)
    from config.connection_standard import run_select

    result = run_select("SELECT COUNT(*) FROM payroll.payroll_transactions")
    nb_transactions = result[0][0] if result else 0
    result = run_select("SELECT COUNT(*) FROM payroll.imported_payroll_master")
    nb_imported = result[0][0] if result else 0
    result = run_select("SELECT COUNT(*) FROM payroll.import_batches")
    nb_batches = result[0][0] if result else 0
    result = run_select("SELECT COUNT(*) FROM payroll.pay_periods")
    nb_periods = result[0][0] if result else 0
    result = run_select("SELECT COUNT(*) FROM core.employees")
    nb_employes = result[0][0] if result else 0

    if (
        nb_transactions == 0
        and nb_imported == 0
        and nb_batches == 0
        and nb_periods == 0
        and nb_employes == 0
    ):
        print("ℹ️  Les tables sont déjà vides. Rien à faire.")
        return 0

    # 2. Demander confirmation
    if not confirmer_suppression():
        print()
        print("❌ OPÉRATION ANNULÉE")
        print()
        return 1

    # 3. Vider les tables
    if not vider_tables():
        return 1

    # 4. Vérifier
    if not verifier_suppression():
        return 1

    # 5. Message final
    print()
    print("=" * 70)
    print("✅ OPÉRATION TERMINÉE")
    print("=" * 70)
    print()
    print("Vous pouvez maintenant:")
    print("  1. Importer un nouveau fichier Excel")
    print("  2. Tester l'application avec des données fraîches")
    print()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        print()
        print("❌ OPÉRATION INTERROMPUE PAR L'UTILISATEUR")
        print()
        sys.exit(1)
    except Exception as e:
        print()
        print(f"❌ ERREUR FATALE: {e}")
        import traceback

        traceback.print_exc()
        print()
        sys.exit(1)
