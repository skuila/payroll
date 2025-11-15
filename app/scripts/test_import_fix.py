#!/usr/bin/env python3
"""
Script de test pour valider les correctifs d'import (AmbiguousParameter)
"""

import sys
import uuid
from datetime import datetime
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration logging
import logging

from config.connection_standard import get_dsn
from services.data_repo import DataRepository
from services.import_service_complete import ImportServiceComplete
from services.kpi_snapshot_service import KPISnapshotService

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_test_excel_file():
    """Crée un fichier Excel de test minimal"""
    import pandas as pd

    # Colonnes exactes requises
    _COLUMNS = [
        "N de ligne",
        "catégorie d'emploi",
        "code emploi",
        "titre d'emploi",
        "date de paie",
        "matricule",
        "employé",
        "catégorie de paie",
        "code de paie",
        "description du code de paie",
        "poste budgétaire",
        "description du poste budgétaire",
        "montant",
        "part employeur",
        "montant combiné",
    ]

    # Données de test minimales (3 lignes)
    # IMPORTANT: Les matricules doivent être numériques (clean_payroll_excel_df filtre les non-numériques)
    data = {
        "N de ligne": [1, 2, 3],
        "catégorie d'emploi": ["Permanent", "Permanent", "Contractuel"],
        "code emploi": ["EMP001", "EMP002", "EMP003"],
        "titre d'emploi": ["Analyste", "Gestionnaire", "Technicien"],
        "date de paie": ["2025-11-20", "2025-11-20", "2025-11-20"],
        "matricule": [
            "1001",
            "1002",
            "1003",
        ],  # Matricules numériques pour passer le filtre
        "employé": ["Test Dupont", "Test Martin", "Test Bernard"],
        "catégorie de paie": ["Salaire", "Salaire", "Salaire"],
        "code de paie": ["SAL", "SAL", "SAL"],
        "description du code de paie": [
            "Salaire de base",
            "Salaire de base",
            "Salaire de base",
        ],
        "poste budgétaire": ["1001", "1002", "1001"],
        "description du poste budgétaire": ["Poste A", "Poste B", "Poste A"],
        "montant": [5000.00, 4500.00, 4800.00],
        "part employeur": [750.00, 675.00, 720.00],
        "montant combiné": [5750.00, 5175.00, 5520.00],
    }

    df = pd.DataFrame(data)[_COLUMNS]
    test_file = Path(__file__).parent.parent / "test_import_fix.xlsx"
    df.to_excel(test_file, index=False, engine="openpyxl")

    logger.info(f"✅ Fichier de test créé: {test_file}")
    logger.info(f"   - {len(df)} lignes")
    return str(test_file)


def progress_callback(percent, message, metrics):
    """Callback pour suivre la progression"""
    logger.info(f"📊 Progression: {percent}% - {message}")
    if metrics:
        logger.info(f"   Métriques: {metrics}")


def test_import():
    """Teste l'import avec les correctifs"""
    logger.info("=" * 60)
    logger.info("TEST D'IMPORT - VALIDATION DES CORRECTIFS")
    logger.info("=" * 60)

    try:
        # 1. Créer le fichier de test
        logger.info("\n1️⃣ Création du fichier Excel de test...")
        test_file = create_test_excel_file()

        # 2. Initialiser les services
        logger.info("\n2️⃣ Initialisation des services...")
        dsn = get_dsn()
        repo = DataRepository(dsn)
        kpi_service = KPISnapshotService(repo)
        import_service = ImportServiceComplete(
            repo=repo, kpi_service=kpi_service, progress_callback=progress_callback
        )
        logger.info("✅ Services initialisés")

        # 3. Préparer les paramètres d'import
        pay_date = datetime(2025, 11, 20)
        user_id = str(uuid.uuid4())

        logger.info("\n3️⃣ Paramètres d'import:")
        logger.info(f"   - Fichier: {test_file}")
        logger.info(f"   - Date de paie: {pay_date.date()}")
        logger.info(f"   - User ID: {user_id}")

        # 4. Exécuter l'import
        logger.info("\n4️⃣ Exécution de l'import...")
        result = import_service.import_payroll_file(
            file_path=test_file,
            pay_date=pay_date,
            user_id=user_id,
            apply_sign_policy=False,  # Pas de correction de signes pour le test
        )

        # 5. Vérifier le résultat
        logger.info("\n5️⃣ Vérification du résultat...")
        if result.get("status") == "success":
            logger.info("✅ Import réussi !")
            logger.info(f"   - Batch ID: {result.get('batch_id')}")
            logger.info(f"   - Lignes importées: {result.get('rows_count')}")
            logger.info(f"   - Date de paie: {result.get('pay_date')}")
            logger.info(f"   - Message: {result.get('message')}")
        else:
            logger.error(f"❌ Import échoué: {result}")
            return False

        # 6. Vérifier les données dans la base
        logger.info("\n6️⃣ Vérification des données en base...")

        # Vérifier imported_payroll_master
        sql_check_imported = """
        SELECT COUNT(*) 
        FROM payroll.imported_payroll_master 
        WHERE date_paie = %(pay_date)s::date
        """
        count_imported = repo.run_query(
            sql_check_imported, {"pay_date": "2025-11-20"}, fetch_one=True
        )
        if count_imported and count_imported[0] > 0:
            logger.info(f"✅ {count_imported[0]} lignes dans imported_payroll_master")
        else:
            logger.warning("⚠️ Aucune ligne dans imported_payroll_master")

        # Vérifier core.employees (matricules numériques 1001, 1002, 1003)
        sql_check_employees = """
        SELECT COUNT(*) 
        FROM core.employees 
        WHERE matricule_norm IN ('1001', '1002', '1003') 
           OR matricule_raw IN ('1001', '1002', '1003')
        """
        count_employees = repo.run_query(sql_check_employees, {}, fetch_one=True)
        if count_employees and count_employees[0] > 0:
            logger.info(
                f"✅ {count_employees[0]} employés de test créés dans core.employees"
            )
        else:
            logger.warning("⚠️ Aucun employé de test trouvé dans core.employees")

        # Vérifier payroll_transactions (si créées)
        sql_check_transactions = """
        SELECT COUNT(*) 
        FROM payroll.payroll_transactions 
        WHERE pay_date = %(pay_date)s::date
        """
        count_transactions = repo.run_query(
            sql_check_transactions, {"pay_date": "2025-11-20"}, fetch_one=True
        )
        if count_transactions:
            logger.info(
                f"ℹ️ {count_transactions[0]} transactions dans payroll_transactions (peut être 0 si transformation non automatique)"
            )

        logger.info("\n" + "=" * 60)
        logger.info("✅ TEST RÉUSSI - Les correctifs fonctionnent correctement")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error(f"\n❌ ERREUR LORS DU TEST: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_import()
    sys.exit(0 if success else 1)
