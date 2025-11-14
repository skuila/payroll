"""
Data Repository: Interface PostgreSQL avec psycopg3 + connection pool

Usage:
    repo = DataRepository(connection_string)
    result = repo.run_query("SELECT * FROM core.employees WHERE matricule = %s", ('1234',))
    repo.run_tx(lambda conn: conn.execute("INSERT INTO ..."))
    count = repo.delete_orphan_employees()  # Supprime uniquement les employés orphelins
"""

import logging
from typing import Any, Callable, Optional, Union
from contextlib import contextmanager
import psycopg
from psycopg_pool import ConnectionPool
import os

DEFAULT_STMT_TIMEOUT_MS = int(os.getenv("PG_STATEMENT_TIMEOUT_MS", "8000"))
DEFAULT_LOCK_TIMEOUT_MS = int(os.getenv("PG_LOCK_TIMEOUT_MS", "2000"))
DEFAULT_IDLE_IN_TX_TIMEOUT_MS = int(os.getenv("PG_IDLE_IN_TX_TIMEOUT_MS", "5000"))

logger = logging.getLogger(__name__)


class DataRepository:
    """Repository pour accès base de données PostgreSQL avec pool de connexions."""

    def __init__(self, connection_string: str, min_size: int = 2, max_size: int = 10):
        """
        Initialise le repository avec un pool de connexions.

        Args:
            connection_string: DSN PostgreSQL (ex: "postgresql://user:pass@host:5432/dbname")
            min_size: Nombre minimum de connexions dans le pool
            max_size: Nombre maximum de connexions dans le pool
        """
        # Ajouter connect_timeout au DSN si absent
        if "?" in connection_string:
            self.connection_string = connection_string + "&connect_timeout=10"
        else:
            self.connection_string = connection_string + "?connect_timeout=10"

        self.pool: Optional[ConnectionPool] = None
        self.min_size = min_size
        self.max_size = max_size
        self._init_pool()

    def _init_pool(self) -> None:
        """Initialise le pool de connexions avec timeouts renforcés."""
        try:

            def configure_connection(conn):
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SET application_name = 'PayrollAnalyzer';
                        SET search_path = public, core, payroll, reference, agent;
                        SET statement_timeout = {DEFAULT_STMT_TIMEOUT_MS};
                        SET lock_timeout = {DEFAULT_LOCK_TIMEOUT_MS};
                        SET idle_in_transaction_session_timeout = {DEFAULT_IDLE_IN_TX_TIMEOUT_MS};
                        SET tcp_keepalives_idle = 60;
                        SET tcp_keepalives_interval = 10;
                        SET tcp_keepalives_count = 3;
                    """
                    )

            self.pool = ConnectionPool(
                conninfo=self.connection_string,
                min_size=self.min_size,
                max_size=self.max_size,
                timeout=30,  # Timeout pour obtenir une connexion du pool
                max_lifetime=3600,  # Renouveler connexions après 1h
                max_idle=600,  # Fermer connexions idle > 10min
                open=True,
                configure=configure_connection,
            )
            logger.info(
                "Connection pool initialisé (autocommit + timeouts + keepalive + lifecycle)"
            )
        except Exception:
            logger.exception("Erreur initialisation pool")
            raise

    def close(self) -> None:
        """Ferme le pool de connexions."""
        if self.pool:
            self.pool.close()
            logger.info("Connection pool fermé")

    @contextmanager
    def get_connection(self):
        """
        Context manager pour obtenir une connexion du pool.

        Usage:
            with repo.get_connection() as conn:
                cursor = conn.execute("SELECT ...")
        """
        if not self.pool:
            raise RuntimeError("Connection pool non initialisé")

        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)

    def healthcheck(self) -> dict[str, Any]:
        """
        Vérifie la santé de la connexion DB.

        Returns:
            dict avec 'status' ('ok' ou 'error'), 'message', 'pool_stats'
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1 AS healthcheck")
                    result = cursor.fetchone()

                    if result and result[0] == 1:
                        pool_stats = {}
                        if self.pool:
                            stats = self.pool.get_stats()
                            pool_stats = {
                                "size": stats.get("pool_size", 0),
                                "available": stats.get("pool_available", 0),
                            }
                        return {
                            "status": "ok",
                            "message": "Database connection healthy",
                            "pool_stats": pool_stats,
                        }
                    else:
                        return {
                            "status": "error",
                            "message": "Healthcheck query returned unexpected result",
                        }
        except Exception as e:
            logger.error(f"Healthcheck failed: {e}")
            return {"status": "error", "message": str(e)}

    # ========== HELPERS DB DISCIPLINÉS ==========

    @staticmethod
    def run_select(
        conn, sql: str, params: Optional[Union[tuple, list, dict]] = None
    ) -> list[tuple]:
        """SELECT → fetchall, pas de commit

        Accepts positional (tuple/list) or named (dict) parameters and passes
        them through to the psycopg cursor.execute call.
        """
        with conn.cursor() as cur:
            # psycopg accepts None for no params
            cur.execute(sql, params if params is not None else None)
            return cur.fetchall()

    @staticmethod
    def run_execute(
        conn, sql: str, params: Optional[Union[tuple, list, dict]] = None
    ) -> int:
        """DML sans RETURNING → commit, pas de fetch

        Accepts positional (tuple/list) or named (dict) parameters.
        """
        with conn.cursor() as cur:
            cur.execute(sql, params if params is not None else None)
            conn.commit()
            return cur.rowcount

    @staticmethod
    def run_execute_returning(
        conn, sql: str, params: Optional[Union[tuple, list, dict]] = None
    ) -> Optional[tuple]:
        """DML avec RETURNING → fetchone + commit

        Accepts positional (tuple/list) or named (dict) parameters.
        """
        with conn.cursor() as cur:
            cur.execute(sql, params if params is not None else None)
            row = cur.fetchone()
            conn.commit()
            return row

    # ========== MÉTHODE LEGACY (COMPATIBILITÉ) ==========

    def run_query(
        self,
        sql: str,
        params: Optional[Union[tuple, list, dict]] = None,
        one: bool = False,
        fetch_one: bool = False,
        fetch_all: bool = True,
    ) -> Any:
        """
        Méthode legacy pour compatibilité.
        Signature modernisée:
            run_query(sql, params=None, one=False)

        Backward-compatible: conserve fetch_one/fetch_all args et les mappe sur `one`.
        Pour le nouveau code, préférez run_select/run_execute/run_execute_returning.
        """
        # Compat layer: mapper les anciens arguments
        if fetch_one:
            one = True

        try:
            with self.get_connection() as conn:
                # SELECT ou WITH (CTEs)
                if sql.strip().upper().startswith(("SELECT", "WITH")):
                    result = self.run_select(conn, sql, params)
                    if one:
                        return result[0] if result else None
                    return result

                # DML avec RETURNING
                elif "RETURNING" in sql.upper():
                    returning_result = self.run_execute_returning(conn, sql, params)
                    # run_execute_returning retourne un tuple, on le retourne tel quel
                    # (la méthode run_query peut retourner Any pour compatibilité)
                    return returning_result

                # DML sans RETURNING
                else:
                    self.run_execute(conn, sql, params)
                    return []

        except Exception as e:
            logger.error(f"Erreur run_query: {e}\nSQL: {sql}\nParams: {params}")
            raise

    def run_tx(
        self,
        transaction_fn: Callable[[psycopg.Connection], Any],
        isolation_level: Optional[str] = None,
    ) -> Any:
        """
        Exécute une fonction dans une transaction.

        Args:
            transaction_fn: Fonction à exécuter (reçoit une connexion)
            isolation_level: Niveau d'isolation ('READ COMMITTED', 'REPEATABLE READ', 'SERIALIZABLE')

        Returns:
            Retour de transaction_fn

        Example:
            def insert_employee(conn):
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO core.employees (matricule, nom, prenom, nom_norm, prenom_norm, statut) "
                        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING employee_id",
                        ('1234', 'Dupont', 'Jean', 'dupont', 'jean', 'actif')
                    )
                    return cur.fetchone()[0]

            employee_id = repo.run_tx(insert_employee)
        """
        try:
            with self.get_connection() as conn:
                # Désactiver autocommit pour la transaction
                old_autocommit = conn.autocommit
                conn.autocommit = False

                if isolation_level:
                    conn.isolation_level = isolation_level

                try:
                    with conn.transaction():
                        result = transaction_fn(conn)
                        return result
                finally:
                    # Restaurer autocommit
                    conn.autocommit = old_autocommit

        except Exception as e:
            logger.error(f"Erreur run_tx: {e}")
            raise

    def execute_dml(
        self, sql: str, params: Optional[tuple] = None, returning: bool = False
    ) -> Any:
        """
        Exécute une requête DML (INSERT/UPDATE/DELETE) dans une transaction.

        Args:
            sql: Requête SQL DML
            params: Paramètres de la requête
            returning: Si True, retourne les lignes avec RETURNING

        Returns:
            None, ou list[dict] si returning=True

        Example:
            repo.execute_dml(
                "UPDATE core.employees SET statut = %s WHERE matricule = %s",
                ('inactif', '1234')
            )

            new_id = repo.execute_dml(
                "INSERT INTO core.employees (...) VALUES (...) RETURNING employee_id",
                (...),
                returning=True
            )
        """
        try:
            with self.get_connection() as conn:
                # Désactiver autocommit pour DML
                old_autocommit = conn.autocommit
                conn.autocommit = False

                try:
                    with conn.transaction():
                        with conn.cursor() as cursor:
                            cursor.execute(sql, params or ())

                            if returning and cursor.description:
                                rows = cursor.fetchall()
                                columns = [desc[0] for desc in cursor.description]
                                return [dict(zip(columns, row)) for row in rows]

                            return None
                finally:
                    # Restaurer autocommit
                    conn.autocommit = old_autocommit

        except Exception as e:
            logger.error(f"Erreur execute_dml: {e}\nSQL: {sql}\nParams: {params}")
            raise

    def execute_many(self, sql: str, params_list: list[tuple]) -> None:
        """
        Exécute une requête DML avec plusieurs jeux de paramètres (batch insert).

        Args:
            sql: Requête SQL DML (INSERT/UPDATE)
            params_list: Liste de tuples de paramètres

        Example:
            repo.execute_many(
                "INSERT INTO payroll.payroll_transactions (...) VALUES (%s, %s, %s, ...)",
                [
                    (employee_id1, period_id, pay_code, ...),
                    (employee_id2, period_id, pay_code, ...),
                    ...
                ]
            )
        """
        try:
            with self.get_connection() as conn:
                # Désactiver autocommit pour batch DML
                old_autocommit = conn.autocommit
                conn.autocommit = False

                try:
                    with conn.transaction():
                        with conn.cursor() as cursor:
                            cursor.executemany(sql, params_list)
                            logger.info(
                                f"Batch insert: {len(params_list)} lignes insérées"
                            )
                finally:
                    # Restaurer autocommit
                    conn.autocommit = old_autocommit

        except Exception as e:
            logger.error(
                f"Erreur execute_many: {e}\nSQL: {sql}\nParams count: {len(params_list)}"
            )
            raise

    def delete_orphan_employees(self) -> int:
        """
        Supprime UNIQUEMENT les employés orphelins (sans transactions dans aucune période).

        Cette méthode garantit que :
        - Seuls les employés qui n'ont plus aucune transaction sont supprimés
        - Les employés utilisés dans d'autres périodes sont conservés
        - Respecte les contraintes de clés étrangères

        Returns:
            Nombre d'employés orphelins supprimés

        Example:
            count = repo.delete_orphan_employees()
            logger.info(f"{count} employés orphelins supprimés")
        """
        # Compter AVANT suppression pour avoir le nombre exact
        sql_count = """
            SELECT COUNT(*)
            FROM core.employees 
            WHERE employee_id IS NOT NULL
            AND employee_id NOT IN (
                SELECT DISTINCT employee_id 
                FROM payroll.payroll_transactions
                WHERE employee_id IS NOT NULL
            )
        """
        count_result = self.run_query(sql_count, {}, fetch_one=True)
        # run_query avec fetch_one=True retourne directement le tuple (ou None)
        # Pour COUNT(*), c'est (count,) ou None
        if count_result is None:
            count_before = 0
        elif isinstance(count_result, (list, tuple)) and len(count_result) > 0:
            # count_result est un tuple: (count,)
            count_value = (
                count_result[0] if isinstance(count_result[0], (int, float)) else 0
            )
            count_before = int(count_value)
        else:
            count_before = 0

        if count_before == 0:
            logger.debug("Aucun employé orphelin à supprimer")
            return 0

        # Exécuter la suppression
        sql_delete = """
            DELETE FROM core.employees 
            WHERE employee_id IS NOT NULL
            AND employee_id NOT IN (
                SELECT DISTINCT employee_id 
                FROM payroll.payroll_transactions
                WHERE employee_id IS NOT NULL
            )
        """
        self.run_query(sql_delete, {})

        logger.info(
            f"Suppression de {count_before} employés orphelins (sans transactions dans aucune période)"
        )
        return count_before


# ========================================
# HELPER FUNCTIONS
# ========================================


def create_repository_from_config(config: dict) -> DataRepository:
    """
    Crée un DataRepository à partir d'un dictionnaire de config.

    Args:
        config: dict avec 'host', 'port', 'database', 'user', 'password', 'min_size', 'max_size'

    Returns:
        DataRepository configuré

    Example:
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'payroll_db',
            'user': 'payroll_user',
            'password': 'secure_password',
            'min_size': 2,
            'max_size': 10
        }
        repo = create_repository_from_config(config)
    """
    connection_string = (
        f"postgresql://{config['user']}:{config['password']}"
        f"@{config['host']}:{config['port']}/{config['database']}"
    )

    return DataRepository(
        connection_string=connection_string,
        min_size=config.get("min_size", 2),
        max_size=config.get("max_size", 10),
    )


# ========================================
# EXEMPLE D'UTILISATION
# ========================================

if __name__ == "__main__":
    # Configuration
    config = {
        "host": "localhost",
        "port": 5432,
        "database": "payroll_db",
        "user": "payroll_user",
        "password": "your_password",
        "min_size": 2,
        "max_size": 5,
    }

    # Créer repository
    repo = create_repository_from_config(config)

    try:
        # Healthcheck
        health = repo.healthcheck()
        print(f"Healthcheck: {health}")

        # Query simple
        employees = repo.run_query("SELECT * FROM core.employees LIMIT 5")
        print(f"Employés: {employees}")

        # Transaction
        def create_test_employee(conn):
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO core.employees (matricule, nom, prenom, nom_norm, prenom_norm, statut) "
                    "VALUES (%s, %s, %s, %s, %s, %s) RETURNING employee_id",
                    ("TEST123", "Test", "User", "test", "user", "actif"),
                )
                return cur.fetchone()[0]

        # employee_id = repo.run_tx(create_test_employee)
        # print(f"Nouvel employé créé: {employee_id}")

    finally:
        repo.close()
