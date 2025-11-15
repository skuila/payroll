#!/usr/bin/env python3
"""
Script de test pour l'import de fichiers de paie
Teste le processus d'import complet avec un fichier de test
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from config.connection_standard import get_dsn
from services.data_repo import DataRepository
from services.import_service_complete import ImportServiceComplete
from services.kpi_snapshot_service import KPISnapshotService

settings.bootstrap_env()


def create_test_file(output_path: str) -> str:
    """
    Crée un fichier Excel de test avec des données minimales valides.

    Returns:
        Chemin vers le fichier créé
    """
    print(f"📝 Création d'un fichier de test: {output_path}")

    # Données de test minimales
    data = {
        "matricule ": ["EMP001", "EMP002", "EMP003"],
        "nom ": ["Dupont", "Martin", "Bernard"],
        "prenom ": ["Jean", "Marie", "Pierre"],
        "date de paie ": ["2025-01-15", "2025-01-15", "2025-01-15"],
        "categorie de paie ": ["Salaire", "Salaire", "Salaire"],
        "code_paie": ["SAL", "SAL", "SAL"],
        "montant ": [5000.00, 4500.00, 4800.00],
        "description_poste_budgetaire": ["Poste A", "Poste B", "Poste A"],
    }

    df = pd.DataFrame(data)

    # Créer le fichier Excel
    df.to_excel(output_path, index=False, engine="openpyxl")
    print(f"✅ Fichier créé: {output_path}")
    print(f"   - {len(df)} lignes")
    print(f"   - Colonnes: {', '.join(df.columns)}")

    return output_path


def test_import(file_path: str, pay_date: datetime):
    """
    Teste l'import d'un fichier de paie.

    Args:
        file_path: Chemin vers le fichier Excel à importer
        pay_date: Date de paie pour l'import
    """
    print("\n" + "=" * 60)
    print("TEST D'IMPORT DE FICHIER DE PAIE")
    print("=" * 60)
    print(f"Fichier: {file_path}")
    print(f"Date de paie: {pay_date.strftime('%Y-%m-%d')}")
    print("=" * 60 + "\n")

    # Vérifier que le fichier existe
    if not Path(file_path).exists():
        print(f"❌ Erreur: Le fichier {file_path} n'existe pas")
        return False

    try:
        # Initialiser les services
        print("🔧 Initialisation des services...")
        dsn = get_dsn()
        repo = DataRepository(dsn)
        kpi_service = KPISnapshotService(repo)

        # Callback de progression
        def progress_callback(percent: int, message: str, metrics: dict):
            print(f"  [{percent:3d}%] {message}")
            if metrics:
                if "rows_processed" in metrics:
                    print(f"       Lignes traitées: {metrics['rows_processed']}")
                if "batches" in metrics:
                    print(f"       Batches: {metrics['batches']}")
                if "elapsed_time" in metrics:
                    print(f"       Temps écoulé: {metrics['elapsed_time']:.2f}s")

        # Créer le service d'import
        import_service = ImportServiceComplete(
            repo=repo, kpi_service=kpi_service, progress_callback=progress_callback
        )

        print("✅ Services initialisés\n")

        # Lancer l'import
        print("🚀 Démarrage de l'import...\n")
        user_id = "test_user_" + datetime.now().strftime("%Y%m%d_%H%M%S")

        result = import_service.import_payroll_file(
            file_path=file_path,
            pay_date=pay_date,
            user_id=user_id,
            apply_sign_policy=True,
        )

        # Afficher les résultats
        print("\n" + "=" * 60)
        print("RÉSULTAT DE L'IMPORT")
        print("=" * 60)
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Batch ID: {result.get('batch_id', 'N/A')}")
        print(f"Nombre de lignes: {result.get('rows_count', 0)}")
        print(f"Date de paie: {result.get('pay_date', 'N/A')}")
        print(f"Message: {result.get('message', 'N/A')}")

        if result.get("status") == "success":
            print("\n✅ Import réussi!")

            # Afficher les KPI si disponibles
            kpi = result.get("kpi", {})
            if kpi:
                print("\n📊 KPI calculés:")
                for key, value in kpi.items():
                    if isinstance(value, (int, float)):
                        print(f"   {key}: {value:,.2f}")
                    else:
                        print(f"   {key}: {value}")

            return True
        else:
            print("\n❌ Import échoué")
            return False

    except Exception as e:
        print(f"\n❌ Erreur lors de l'import: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        # Fermer les connexions
        try:
            if "repo" in locals():
                repo.close()
        except Exception:
            pass


def main():
    """Fonction principale"""
    import argparse

    parser = argparse.ArgumentParser(description="Test d'import de fichier de paie")
    parser.add_argument(
        "--file", "-f", type=str, help="Chemin vers le fichier Excel à importer"
    )
    parser.add_argument(
        "--date",
        "-d",
        type=str,
        help="Date de paie (YYYY-MM-DD)",
        default=datetime.now().strftime("%Y-%m-%d"),
    )
    parser.add_argument(
        "--create-test",
        action="store_true",
        help="Créer un fichier de test avant l'import",
    )

    args = parser.parse_args()

    # Déterminer le fichier à utiliser
    if args.create_test:
        test_file = Path(__file__).parent.parent / "test_import_paie.xlsx"
        file_path = create_test_file(str(test_file))
    elif args.file:
        file_path = args.file
    else:
        print("❌ Erreur: Vous devez spécifier --file ou --create-test")
        parser.print_help()
        sys.exit(1)

    # Parser la date
    try:
        pay_date = datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print(f"❌ Erreur: Format de date invalide: {args.date} (attendu: YYYY-MM-DD)")
        sys.exit(1)

    # Lancer le test
    success = test_import(file_path, pay_date)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
