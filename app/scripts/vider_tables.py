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
    """Vide toutes les tables principales."""
    print()
    print("🗑️  SUPPRESSION EN COURS...")
    print("-" * 70)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Supprimer les transactions de paie
                print("  1. Suppression des transactions de paie...")
                cur.execute("DELETE FROM payroll.payroll_transactions")
                nb_transactions = cur.rowcount
                print(f"     ✅ {nb_transactions} transactions supprimées")

                # 2. Supprimer les employés
                print("  2. Suppression des employés...")
                cur.execute("DELETE FROM core.employees")
                nb_employes = cur.rowcount
                print(f"     ✅ {nb_employes} employés supprimés")

                # 3. Réinitialiser les séquences si nécessaire
                print("  3. Réinitialisation des séquences...")
                cur.execute(
                    """
                    SELECT setval('payroll.payroll_transactions_id_seq', 1, false);
                """
                )
                print("     ✅ Séquences réinitialisées")

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

        # Vérifier les employés
        result = run_select("SELECT COUNT(*) FROM core.employees")
        nb_employes = result[0][0] if result else 0

        print(f"  • Transactions restantes: {nb_transactions}")
        print(f"  • Employés restants: {nb_employes}")
        print("-" * 70)

        if nb_transactions == 0 and nb_employes == 0:
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
    nb_transactions, nb_employes = compter_donnees()

    if nb_transactions == 0 and nb_employes == 0:
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
