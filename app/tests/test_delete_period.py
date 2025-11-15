#!/usr/bin/env python3
"""
Tests d'intégration pour delete_period dans AppBridge

Ces tests vérifient que delete_period respecte les contraintes FK
et maintient la cohérence de la base de données.
"""

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from config.connection_standard import get_connection

# Charger .env AVANT tout
from dotenv import load_dotenv
from payroll_app_qt_Version4 import AppBridge

load_dotenv()


class FakeMainWindow:
    """Fausse fenêtre principale pour les tests"""

    pass


@pytest.fixture(scope="function")
def bridge():
    """Fixture pour créer une instance de AppBridge"""
    fake_window = FakeMainWindow()
    bridge = AppBridge(fake_window)
    return bridge


@pytest.fixture(scope="function")
def db_connection():
    """Fixture pour obtenir une connexion à la base de données"""
    with get_connection() as conn:
        yield conn


def create_test_period(conn, pay_date: str, status: str = "ouverte") -> str:
    """Crée une période de test et retourne son period_id"""
    with conn.cursor() as cur:
        # Générer un UUID pour la période
        period_id = str(uuid.uuid4())

        # Extraire année et mois de la date
        pay_date_obj = datetime.strptime(pay_date, "%Y-%m-%d").date()
        pay_year = pay_date_obj.year
        pay_month = pay_date_obj.month
        pay_day = (
            pay_date_obj.day
        )  # pay_day est généré mais on peut le fournir pour éviter les erreurs

        # Trouver le prochain period_seq_in_year disponible pour cette année
        cur.execute(
            """
            SELECT COALESCE(MAX(period_seq_in_year), 0) + 1
            FROM payroll.pay_periods
            WHERE pay_year = %s
            """,
            (pay_year,),
        )
        result_seq = cur.fetchone()
        period_seq_in_year = result_seq[0] if result_seq else 1

        # Insérer la période
        # Note: pay_day est une colonne GENERATED ALWAYS AS, mais on peut la fournir explicitement
        # pour éviter les problèmes de contrainte NOT NULL
        cur.execute(
            """
            INSERT INTO payroll.pay_periods 
            (period_id, pay_date, pay_day, pay_year, pay_month, status, period_seq_in_year)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING period_id::text
            """,
            (
                period_id,
                pay_date,
                pay_day,
                pay_year,
                pay_month,
                status,
                period_seq_in_year,
            ),
        )
        result = cur.fetchone()
        conn.commit()
        return result[0] if result else period_id


def create_test_employee(
    conn, matricule: str, nom: str, prenom: str = "Test"
) -> int | None:
    """Crée un employé de test et retourne son employee_id"""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO core.employees 
            (matricule, nom, prenom, nom_norm, prenom_norm, nom_complet, statut)
            VALUES (%s, %s, %s, %s, %s, %s, 'actif')
            RETURNING employee_id
            """,
            (matricule, nom, prenom, nom.lower(), prenom.lower(), f"{nom} {prenom}"),
        )
        result = cur.fetchone()
        conn.commit()
        return result[0] if result else None


def create_test_transaction(
    conn, employee_id: int, pay_date: str, amount_cents: int = 100000
) -> int | None:
    """Crée une transaction de test et retourne son transaction_id"""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO payroll.payroll_transactions 
            (employee_id, pay_date, pay_code, amount_cents)
            VALUES (%s, %s, 'SAL', %s)
            RETURNING transaction_id
            """,
            (employee_id, pay_date, amount_cents),
        )
        result = cur.fetchone()
        conn.commit()
        return result[0] if result else None


def create_test_import_batch(
    conn, pay_date: str, period_id: str | None = None
) -> int | None:
    """Crée un batch d'import de test et retourne son batch_id"""
    with conn.cursor() as cur:
        # Utiliser les colonnes comme dans import_service_complete.py
        # file_name, checksum, period_id, pay_date, rows_count, status, imported_by
        # Status autorisés: 'pending', 'running', 'success', 'error', 'failed'
        cur.execute(
            """
            INSERT INTO payroll.import_batches 
            (file_name, rows_count, status, pay_date, period_id)
            VALUES (%s, %s, 'success', %s, %s)
            RETURNING batch_id
            """,
            ("test_file.xlsx", 10, pay_date, period_id),
        )
        result = cur.fetchone()
        conn.commit()
        return result[0] if result else None


def create_test_imported_data(conn, pay_date: str) -> int:
    """Crée des données dans imported_payroll_master et retourne le nombre de lignes"""
    with conn.cursor() as cur:
        # Utiliser les colonnes exactes de imported_payroll_master
        # D'après le schéma: date_paie, matricule, montant (pas "montant" mais peut-être autre chose)
        # Colonnes minimales requises: date_paie (NOT NULL)
        cur.execute(
            """
            INSERT INTO payroll.imported_payroll_master 
            (date_paie, matricule, source_file)
            VALUES (%s, 'TEST001', 'test_file.xlsx')
            RETURNING id
            """,
            (pay_date,),
        )
        result = cur.fetchone()
        conn.commit()
        return 1 if result else 0


def count_rows(
    conn, table: str, where_clause: str = "", params: tuple | None = None
) -> int:
    """Compte les lignes dans une table avec condition optionnelle"""
    with conn.cursor() as cur:
        sql = f"SELECT COUNT(*) FROM {table}"
        if where_clause:
            sql += f" WHERE {where_clause}"
        if params is None:
            params = ()
        cur.execute(sql, params)
        result = cur.fetchone()
        return result[0] if result else 0


def cleanup_test_data(conn, period_id: str | None = None, pay_date: str | None = None):
    """Nettoie les données de test dans le bon ordre pour respecter les FK"""
    with conn.cursor() as cur:
        # 1. Supprimer les transactions d'abord (pour respecter FK employee)
        if pay_date:
            cur.execute(
                "DELETE FROM payroll.payroll_transactions WHERE pay_date = %s",
                (pay_date,),
            )
        # 2. Supprimer les données importées
        if pay_date:
            cur.execute(
                "DELETE FROM payroll.imported_payroll_master WHERE date_paie = %s",
                (pay_date,),
            )
        # 3. Supprimer les batches
        if pay_date:
            cur.execute(
                "DELETE FROM payroll.import_batches WHERE pay_date = %s", (pay_date,)
            )
        if period_id:
            cur.execute(
                "DELETE FROM payroll.import_batches WHERE period_id = %s", (period_id,)
            )
        # 4. Supprimer les périodes
        if period_id:
            cur.execute(
                "DELETE FROM payroll.pay_periods WHERE period_id = %s", (period_id,)
            )
        # 5. Supprimer les employés orphelins (après les transactions)
        cur.execute(
            """
            DELETE FROM core.employees 
            WHERE matricule LIKE 'TEST%'
            AND employee_id NOT IN (
                SELECT DISTINCT employee_id 
                FROM payroll.payroll_transactions
                WHERE employee_id IS NOT NULL
            )
            """
        )
        # 6. Supprimer les audits de test
        if period_id:
            cur.execute(
                "DELETE FROM payroll.deleted_periods_audit WHERE period_id = %s",
                (period_id,),
            )
        conn.commit()


class TestDeletePeriod:
    """Tests d'intégration pour delete_period"""

    def test_delete_period_with_orphan_employees(self, bridge, db_connection):
        """
        Scénario 1: Suppression d'une période avec transactions et employés
        uniquement dans cette période

        Vérifie que:
        - Toutes les transactions de la période sont supprimées
        - Les employés uniquement dans cette période sont supprimés (orphelins)
        - La période est supprimée
        - Un audit est créé
        - Aucune erreur FK
        """
        pay_date = "2025-12-31"  # Date unique pour éviter les conflits
        period_id = None
        employee_id = None

        try:
            # Créer les données de test
            period_id = create_test_period(db_connection, pay_date)
            employee_id = create_test_employee(
                db_connection, "TEST001", "Orphan", "Employee"
            )
            create_test_transaction(db_connection, employee_id, pay_date, 100000)
            batch_id = create_test_import_batch(db_connection, pay_date, period_id)
            create_test_imported_data(db_connection, pay_date)

            # Vérifier que les données existent avant suppression
            assert (
                count_rows(
                    db_connection, "payroll.pay_periods", "period_id = %s", (period_id,)
                )
                == 1
            )
            assert (
                count_rows(
                    db_connection,
                    "payroll.payroll_transactions",
                    "pay_date = %s",
                    (pay_date,),
                )
                == 1
            )
            assert (
                count_rows(
                    db_connection, "core.employees", "employee_id = %s", (employee_id,)
                )
                == 1
            )
            assert (
                count_rows(
                    db_connection,
                    "payroll.import_batches",
                    "batch_id = %s",
                    (batch_id,),
                )
                == 1
            )

            # Appeler delete_period
            result_json = bridge.delete_period(period_id)
            result = json.loads(result_json)

            # Vérifier le succès
            assert (
                result["success"] is True
            ), f"delete_period a échoué: {result.get('error')}"
            assert result["deleted_count"] == 1
            assert (
                result["employees_deleted"] == 1
            )  # L'employé orphelin doit être supprimé
            assert result["pay_date"] == pay_date

            # Vérifier que les données sont supprimées
            assert (
                count_rows(
                    db_connection, "payroll.pay_periods", "period_id = %s", (period_id,)
                )
                == 0
            )
            assert (
                count_rows(
                    db_connection,
                    "payroll.payroll_transactions",
                    "pay_date = %s",
                    (pay_date,),
                )
                == 0
            )
            assert (
                count_rows(
                    db_connection, "core.employees", "employee_id = %s", (employee_id,)
                )
                == 0
            )  # Orphelin supprimé
            assert (
                count_rows(
                    db_connection,
                    "payroll.import_batches",
                    "batch_id = %s",
                    (batch_id,),
                )
                == 0
            )
            assert (
                count_rows(
                    db_connection,
                    "payroll.imported_payroll_master",
                    "date_paie = %s",
                    (pay_date,),
                )
                == 0
            )

            # Vérifier que l'audit est créé
            with db_connection.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM payroll.deleted_periods_audit WHERE period_id = %s",
                    (period_id,),
                )
                audit_count = cur.fetchone()[0]
                assert audit_count == 1, "L'audit doit être créé"

        finally:
            # Nettoyage
            cleanup_test_data(db_connection, period_id, pay_date)

    def test_delete_period_with_shared_employees(self, bridge, db_connection):
        """
        Scénario 2: Suppression d'une période où les employés ont aussi
        des transactions dans d'autres périodes

        Vérifie que:
        - Seules les transactions de la période cible sont supprimées
        - Les employés ne sont PAS supprimés (ils ont d'autres transactions)
        - La période est supprimée
        - Aucune erreur FK
        """
        pay_date_1 = "2025-11-30"  # Dates uniques pour éviter les conflits
        pay_date_2 = "2025-11-29"
        period_id_1 = None
        period_id_2 = None
        employee_id = None

        try:
            # Créer deux périodes
            period_id_1 = create_test_period(db_connection, pay_date_1)
            period_id_2 = create_test_period(db_connection, pay_date_2)

            # Créer un employé partagé
            employee_id = create_test_employee(
                db_connection, "TEST002", "Shared", "Employee"
            )

            # Créer des transactions dans les deux périodes
            create_test_transaction(db_connection, employee_id, pay_date_1, 100000)
            create_test_transaction(db_connection, employee_id, pay_date_2, 150000)

            # Vérifier que les données existent avant suppression
            assert (
                count_rows(
                    db_connection,
                    "payroll.payroll_transactions",
                    "pay_date = %s",
                    (pay_date_1,),
                )
                == 1
            )
            assert (
                count_rows(
                    db_connection,
                    "payroll.payroll_transactions",
                    "pay_date = %s",
                    (pay_date_2,),
                )
                == 1
            )
            assert (
                count_rows(
                    db_connection, "core.employees", "employee_id = %s", (employee_id,)
                )
                == 1
            )

            # Appeler delete_period pour la première période
            result_json = bridge.delete_period(period_id_1)
            result = json.loads(result_json)

            # Vérifier le succès
            assert (
                result["success"] is True
            ), f"delete_period a échoué: {result.get('error')}"
            assert result["deleted_count"] == 1
            assert (
                result["employees_deleted"] == 0
            )  # L'employé ne doit PAS être supprimé
            assert result["pay_date"] == pay_date_1

            # Vérifier que seule la première période est supprimée
            assert (
                count_rows(
                    db_connection,
                    "payroll.pay_periods",
                    "period_id = %s",
                    (period_id_1,),
                )
                == 0
            )
            assert (
                count_rows(
                    db_connection,
                    "payroll.pay_periods",
                    "period_id = %s",
                    (period_id_2,),
                )
                == 1
            )  # La deuxième période existe toujours

            # Vérifier que seule la transaction de la première période est supprimée
            assert (
                count_rows(
                    db_connection,
                    "payroll.payroll_transactions",
                    "pay_date = %s",
                    (pay_date_1,),
                )
                == 0
            )
            assert (
                count_rows(
                    db_connection,
                    "payroll.payroll_transactions",
                    "pay_date = %s",
                    (pay_date_2,),
                )
                == 1
            )  # La transaction de la deuxième période existe toujours

            # Vérifier que l'employé n'est PAS supprimé (il a encore des transactions)
            assert (
                count_rows(
                    db_connection, "core.employees", "employee_id = %s", (employee_id,)
                )
                == 1
            )

            # Vérifier qu'aucune erreur FK n'a été levée (implicite si on arrive ici)

        finally:
            # Nettoyage
            cleanup_test_data(db_connection, period_id_1, pay_date_1)
            cleanup_test_data(db_connection, period_id_2, pay_date_2)

    def test_delete_period_with_no_transactions(self, bridge, db_connection):
        """
        Scénario 3: Suppression d'une période sans transactions

        Vérifie que:
        - Aucune suppression sur payroll_transactions (pas de transactions)
        - La période est supprimée proprement
        - Un audit est créé quand même
        - Aucune erreur FK
        """
        pay_date = "2025-11-28"  # Date unique pour éviter les conflits
        period_id = None

        try:
            # Créer une période sans transactions
            period_id = create_test_period(db_connection, pay_date)

            # Vérifier que la période existe et qu'il n'y a pas de transactions
            assert (
                count_rows(
                    db_connection, "payroll.pay_periods", "period_id = %s", (period_id,)
                )
                == 1
            )
            assert (
                count_rows(
                    db_connection,
                    "payroll.payroll_transactions",
                    "pay_date = %s",
                    (pay_date,),
                )
                == 0
            )

            # Appeler delete_period
            result_json = bridge.delete_period(period_id)
            result = json.loads(result_json)

            # Vérifier le succès
            assert (
                result["success"] is True
            ), f"delete_period a échoué: {result.get('error')}"
            assert result["deleted_count"] == 0  # Aucune transaction à supprimer
            assert result["employees_deleted"] == 0  # Aucun employé à supprimer
            assert result["pay_date"] == pay_date

            # Vérifier que la période est supprimée
            assert (
                count_rows(
                    db_connection, "payroll.pay_periods", "period_id = %s", (period_id,)
                )
                == 0
            )

            # Vérifier qu'il n'y a toujours pas de transactions (pas de changement)
            assert (
                count_rows(
                    db_connection,
                    "payroll.payroll_transactions",
                    "pay_date = %s",
                    (pay_date,),
                )
                == 0
            )

            # Vérifier que l'audit est créé même sans transactions
            with db_connection.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM payroll.deleted_periods_audit WHERE period_id = %s",
                    (period_id,),
                )
                audit_count = cur.fetchone()[0]
                assert audit_count == 1, "L'audit doit être créé même sans transactions"

        finally:
            # Nettoyage
            cleanup_test_data(db_connection, period_id, pay_date)

    def test_delete_period_foreign_key_violation_prevention(
        self, bridge, db_connection
    ):
        """
        Test supplémentaire: Vérifier qu'aucune erreur FK n'est levée
        même dans un scénario complexe avec plusieurs employés et transactions
        """
        pay_date = "2025-11-27"  # Date unique pour éviter les conflits
        period_id = None
        employee_ids = []

        try:
            # Créer une période
            period_id = create_test_period(db_connection, pay_date)

            # Créer plusieurs employés avec transactions
            for i in range(3):
                emp_id = create_test_employee(
                    db_connection, f"TEST{i + 3:03d}", f"Employee{i + 1}", "Test"
                )
                employee_ids.append(emp_id)
                create_test_transaction(
                    db_connection, emp_id, pay_date, 100000 + i * 10000
                )

            # Vérifier que les données existent
            assert (
                count_rows(
                    db_connection,
                    "payroll.payroll_transactions",
                    "pay_date = %s",
                    (pay_date,),
                )
                == 3
            )
            # Vérifier chaque employé individuellement pour éviter les problèmes avec IN
            for emp_id in employee_ids:
                assert (
                    count_rows(
                        db_connection, "core.employees", "employee_id = %s", (emp_id,)
                    )
                    == 1
                )

            # Appeler delete_period - ne doit pas lever d'erreur FK
            result_json = bridge.delete_period(period_id)
            result = json.loads(result_json)

            # Vérifier le succès (pas d'exception FK)
            assert (
                result["success"] is True
            ), f"delete_period a échoué: {result.get('error')}"
            assert "ForeignKeyViolation" not in str(
                result.get("error", "")
            ), "Une erreur FK ne doit pas être levée"

            # Vérifier que tout est supprimé proprement
            assert (
                count_rows(
                    db_connection, "payroll.pay_periods", "period_id = %s", (period_id,)
                )
                == 0
            )
            assert (
                count_rows(
                    db_connection,
                    "payroll.payroll_transactions",
                    "pay_date = %s",
                    (pay_date,),
                )
                == 0
            )
            # Les employés orphelins doivent être supprimés
            for emp_id in employee_ids:
                assert (
                    count_rows(
                        db_connection, "core.employees", "employee_id = %s", (emp_id,)
                    )
                    == 0
                )

        finally:
            # Nettoyage
            cleanup_test_data(db_connection, period_id, pay_date)


if __name__ == "__main__":
    # Permet d'exécuter les tests directement
    pytest.main([__file__, "-v"])
