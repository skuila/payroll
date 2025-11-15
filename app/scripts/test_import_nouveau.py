#!/usr/bin/env python3
"""
Script de test pour importer nouveau.xlsx et vérifier le salaire net global et le nombre d'employés
"""

import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

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


def analyze_excel_file(file_path):
    """Analyse le fichier Excel avant import"""
    logger.info("=" * 60)
    logger.info("ANALYSE DU FICHIER EXCEL")
    logger.info("=" * 60)

    try:
        df = pd.read_excel(file_path, engine="openpyxl")
        logger.info(f"✅ Fichier lu: {file_path}")
        logger.info(f"   - Nombre de lignes: {len(df)}")
        logger.info(f"   - Nombre de colonnes: {len(df.columns)}")

        # Afficher les colonnes
        logger.info("\n📋 Colonnes détectées:")
        for i, col in enumerate(df.columns, 1):
            logger.info(f"   {i:2d}. {col}")

        # Chercher la colonne montant
        montant_cols = [
            col
            for col in df.columns
            if "montant" in str(col).lower() and "combiné" not in str(col).lower()
        ]
        if montant_cols:
            logger.info(f"\n💰 Colonnes de montant trouvées: {montant_cols}")
            for col in montant_cols:
                if col in df.columns:
                    # Convertir en numérique
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                    total = df[col].sum()
                    non_zero = (df[col] != 0).sum()
                    logger.info(
                        f"   - {col}: Total={total:,.2f}$, Lignes non-zéro={non_zero}"
                    )

        # Chercher la colonne matricule
        matricule_cols = [col for col in df.columns if "matricule" in str(col).lower()]
        if matricule_cols:
            logger.info(f"\n👤 Colonnes de matricule trouvées: {matricule_cols}")
            for col in matricule_cols:
                if col in df.columns:
                    unique = df[col].nunique()
                    logger.info(f"   - {col}: {unique} matricules uniques")

        # Chercher la colonne date de paie
        date_cols = [
            col
            for col in df.columns
            if "date" in str(col).lower() and "paie" in str(col).lower()
        ]
        if date_cols:
            logger.info(f"\n📅 Colonnes de date de paie trouvées: {date_cols}")
            for col in date_cols:
                if col in df.columns:
                    unique_dates = df[col].nunique()
                    dates = df[col].unique()[:5]  # Premières 5 dates
                    logger.info(f"   - {col}: {unique_dates} dates uniques")
                    logger.info(f"     Exemples: {dates}")

        return df

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'analyse: {e}", exc_info=True)
        return None


def progress_callback(percent, message, metrics):
    """Callback pour suivre la progression"""
    logger.info(f"📊 Progression: {percent}% - {message}")
    if metrics:
        logger.info(f"   Métriques: {metrics}")


def test_import_nouveau():
    """Teste l'import du fichier nouveau.xlsx"""
    logger.info("=" * 60)
    logger.info("TEST D'IMPORT - nouveau.xlsx")
    logger.info("=" * 60)

    file_path = r"C:\Users\SZERTYUIOPMLMM\Desktop\APP\app\nouveau.xlsx"

    if not os.path.exists(file_path):
        logger.error(f"❌ Fichier introuvable: {file_path}")
        return False

    try:
        # 1. Analyser le fichier Excel
        logger.info("\n1️⃣ Analyse du fichier Excel...")
        df = analyze_excel_file(file_path)
        if df is None:
            return False

        # 2. Initialiser les services
        logger.info("\n2️⃣ Initialisation des services...")
        dsn = get_dsn()
        repo = DataRepository(dsn)
        kpi_service = KPISnapshotService(repo)
        import_service = ImportServiceComplete(
            repo=repo, kpi_service=kpi_service, progress_callback=progress_callback
        )
        logger.info("✅ Services initialisés")

        # 3. Déterminer la date de paie depuis le fichier
        logger.info("\n3️⃣ Détermination de la date de paie...")
        date_cols = [
            col
            for col in df.columns
            if "date" in str(col).lower() and "paie" in str(col).lower()
        ]
        pay_date = None

        if date_cols:
            date_col = date_cols[0]
            # Prendre la première date non-nulle
            dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
            if not dates.empty:
                pay_date = dates.iloc[0].to_pydatetime()
                logger.info(f"   Date de paie détectée: {pay_date.date()}")
            else:
                logger.warning(
                    "   Aucune date valide trouvée, utilisation de la date par défaut"
                )
                pay_date = datetime(2025, 8, 28)  # Date par défaut
        else:
            logger.warning(
                "   Colonne date de paie non trouvée, utilisation de la date par défaut"
            )
            pay_date = datetime(2025, 8, 28)  # Date par défaut

        user_id = str(uuid.uuid4())

        logger.info("\n4️⃣ Paramètres d'import:")
        logger.info(f"   - Fichier: {file_path}")
        logger.info(f"   - Date de paie: {pay_date.date()}")
        logger.info(f"   - User ID: {user_id}")

        # 5. Exécuter l'import
        logger.info("\n5️⃣ Exécution de l'import...")
        result = import_service.import_payroll_file(
            file_path=file_path,
            pay_date=pay_date,
            user_id=user_id,
            apply_sign_policy=False,  # Pas de correction de signes pour le test
        )

        # 6. Vérifier le résultat
        logger.info("\n6️⃣ Vérification du résultat...")
        if result.get("status") == "success":
            logger.info("✅ Import réussi !")
            logger.info(f"   - Batch ID: {result.get('batch_id')}")
            logger.info(f"   - Lignes importées: {result.get('rows_count')}")
            logger.info(f"   - Date de paie: {result.get('pay_date')}")
        else:
            logger.error(f"❌ Import échoué: {result}")
            return False

        # 7. Calculer le salaire net global et le nombre d'employés
        logger.info("\n7️⃣ Calcul du salaire net global et nombre d'employés...")
        pay_date_str = result.get("pay_date") or pay_date.strftime("%Y-%m-%d")

        # Requête pour calculer le salaire net global
        sql_salaire_net = """
        SELECT 
            COUNT(DISTINCT e.employee_id) as nb_employes,
            COUNT(*) as nb_transactions,
            COALESCE(SUM(t.amount_cents), 0) / 100.0 as salaire_net_total,
            COALESCE(SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END), 0) / 100.0 as gains_brut,
            COALESCE(SUM(CASE WHEN t.amount_cents < 0 THEN ABS(t.amount_cents) ELSE 0 END), 0) / 100.0 as deductions
        FROM payroll.payroll_transactions t
        JOIN core.employees e ON t.employee_id = e.employee_id
        WHERE t.pay_date = %(pay_date)s::date
        """

        result_salaire = repo.run_query(
            sql_salaire_net, {"pay_date": pay_date_str}, fetch_one=True
        )

        if result_salaire:
            nb_employes = result_salaire[0] or 0
            nb_transactions = result_salaire[1] or 0
            salaire_net_total = result_salaire[2] or 0.0
            gains_brut = result_salaire[3] or 0.0
            deductions = result_salaire[4] or 0.0

            logger.info("\n" + "=" * 60)
            logger.info("📊 RÉSULTATS DE L'IMPORT")
            logger.info("=" * 60)
            logger.info(f"📅 Date de paie: {pay_date_str}")
            logger.info(f"👤 Nombre d'employés: {nb_employes}")
            logger.info(f"📝 Nombre de transactions: {nb_transactions}")
            logger.info(f"💰 Salaire net global: {salaire_net_total:,.2f} $")
            logger.info(f"   - Gains bruts: {gains_brut:,.2f} $")
            logger.info(f"   - Déductions: {deductions:,.2f} $")
            logger.info("=" * 60)

        # Toujours vérifier aussi dans imported_payroll_master pour avoir les données complètes
        logger.info("\n8️⃣ Vérification dans imported_payroll_master...")
        sql_imported = """
        SELECT 
            COUNT(DISTINCT matricule) as nb_employes,
            COUNT(*) as nb_lignes,
            COALESCE(SUM(montant_employe), 0) as salaire_net_total,
            COALESCE(SUM(CASE WHEN montant_employe > 0 THEN montant_employe ELSE 0 END), 0) as gains_brut,
            COALESCE(SUM(CASE WHEN montant_employe < 0 THEN ABS(montant_employe) ELSE 0 END), 0) as deductions
        FROM payroll.imported_payroll_master
        WHERE date_paie = %(pay_date)s::date
        """

        result_imported = repo.run_query(
            sql_imported, {"pay_date": pay_date_str}, fetch_one=True
        )

        if result_imported:
            nb_employes_imported = result_imported[0] or 0
            nb_lignes_imported = result_imported[1] or 0
            salaire_net_total_imported = result_imported[2] or 0.0
            gains_brut_imported = result_imported[3] or 0.0
            deductions_imported = result_imported[4] or 0.0

            logger.info("\n" + "=" * 60)
            logger.info("📊 RÉSULTATS DE L'IMPORT (depuis imported_payroll_master)")
            logger.info("=" * 60)
            logger.info(f"📅 Date de paie: {pay_date_str}")
            logger.info(f"👤 Nombre d'employés: {nb_employes_imported}")
            logger.info(f"📝 Nombre de lignes: {nb_lignes_imported}")
            logger.info(f"💰 Salaire net global: {salaire_net_total_imported:,.2f} $")
            logger.info(f"   - Gains bruts: {gains_brut_imported:,.2f} $")
            logger.info(f"   - Déductions: {deductions_imported:,.2f} $")
            logger.info("=" * 60)

            if nb_transactions == 0:
                logger.info(
                    "ℹ️ Note: Les transactions n'ont pas encore été transformées en payroll_transactions"
                )
                logger.info(
                    "   Les données sont disponibles dans imported_payroll_master"
                )

            # Vérifier dans imported_payroll_master
            sql_imported = """
            SELECT 
                COUNT(DISTINCT matricule) as nb_employes,
                COUNT(*) as nb_lignes,
                COALESCE(SUM(montant_employe), 0) as salaire_net_total
            FROM payroll.imported_payroll_master
            WHERE date_paie = %(pay_date)s::date
            """

            result_imported = repo.run_query(
                sql_imported, {"pay_date": pay_date_str}, fetch_one=True
            )

            if result_imported:
                nb_employes = result_imported[0] or 0
                nb_lignes = result_imported[1] or 0
                salaire_net_total = result_imported[2] or 0.0

                logger.info("\n" + "=" * 60)
                logger.info("📊 RÉSULTATS DE L'IMPORT (depuis imported_payroll_master)")
                logger.info("=" * 60)
                logger.info(f"📅 Date de paie: {pay_date_str}")
                logger.info(f"👤 Nombre d'employés: {nb_employes}")
                logger.info(f"📝 Nombre de lignes: {nb_lignes}")
                logger.info(f"💰 Salaire net global: {salaire_net_total:,.2f} $")
                logger.info("=" * 60)
                logger.info(
                    "ℹ️ Note: Les transactions n'ont pas encore été transformées en payroll_transactions"
                )

        logger.info("\n✅ TEST TERMINÉ")
        return True

    except Exception as e:
        logger.error(f"\n❌ ERREUR LORS DU TEST: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_import_nouveau()
    sys.exit(0 if success else 1)
