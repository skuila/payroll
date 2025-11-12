"""
Module de connexion standardisé - Source unique de vérité
==========================================================

Ce module centralise TOUTE la logique de connexion PostgreSQL.
Tous les autres modules DOIVENT utiliser get_connection() ou get_dsn().

Règles:
1. Priorité DSN: PAYROLL_DSN > variables individuelles (PAYROLL_DB_*)
2. Validation obligatoire du mot de passe
3. Timeout de connexion: 5 secondes
4. Pool de connexions: min=2, max=10
5. Logging unifié

Auteur: Système standardisé
Date: 2025-11-11
"""

import os
import sys
import logging
from typing import Optional, Dict, Any
from pathlib import Path

# Charger .env automatiquement
try:
    from dotenv import load_dotenv

    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=False)
except ImportError:
    pass

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION STANDARD
# ============================================================================

DEFAULT_TIMEOUT = 10
DEFAULT_POOL_MIN = 2
DEFAULT_POOL_MAX = 10

# Timeouts PostgreSQL (en millisecondes, overridables par env)
PG_STATEMENT_TIMEOUT_MS = int(os.getenv("PG_STATEMENT_TIMEOUT_MS", "8000"))
PG_LOCK_TIMEOUT_MS = int(os.getenv("PG_LOCK_TIMEOUT_MS", "2000"))
PG_IDLE_IN_TX_TIMEOUT_MS = int(os.getenv("PG_IDLE_IN_TX_TIMEOUT_MS", "5000"))

# Search path standard
SEARCH_PATH = "payroll, core, reference, security, public"

# Timezone
TIMEZONE = "America/Toronto"

# ============================================================================
# OUTILS INTERNES
# ============================================================================


def _get_base_config() -> Dict[str, str]:
    """Retourne les paramètres de base (hôte, port, base, user)."""
    return {
        "host": os.getenv("PAYROLL_DB_HOST", "localhost"),
        "port": os.getenv("PAYROLL_DB_PORT", "5432"),
        "database": os.getenv("PAYROLL_DB_NAME", "payroll_db"),
        "user": os.getenv("PAYROLL_DB_USER", "payroll_unified"),
    }


# ============================================================================
# FONCTION PRINCIPALE: GET_DSN
# ============================================================================


def get_dsn() -> str:
    """
    Retourne le DSN PostgreSQL standardisé.

    Priorité:
    1. PAYROLL_DSN (complet)
    2. Construction depuis PAYROLL_DB_* (host, port, user, password, name)
    3. Fallback avec PGPASSWORD si mot de passe manquant

    Returns:
        DSN complet avec mot de passe

    Raises:
        RuntimeError: Si aucun mot de passe disponible
    """
    # Priorité 1: DSN complet
    dsn = os.getenv("PAYROLL_DSN")
    if dsn:
        # Vérifier présence mot de passe
        if (
            _has_password(dsn)
            or os.getenv("PGPASSWORD")
            or os.getenv("PAYROLL_DB_PASSWORD")
        ):
            logger.debug("DSN depuis PAYROLL_DSN")
            # Ajouter connect_timeout si absent
            dsn = _ensure_connect_timeout(dsn)
            return dsn
        else:
            raise RuntimeError(
                "PAYROLL_DSN défini mais aucun mot de passe trouvé. "
                "Ajoutez le mot de passe dans le DSN ou définissez PGPASSWORD/PAYROLL_DB_PASSWORD"
            )

    # Priorité 2: Construction depuis variables individuelles
    base_config = _get_base_config()
    host = base_config["host"]
    port = base_config["port"]
    database = base_config["database"]
    user = base_config["user"]
    password = os.getenv("PAYROLL_DB_PASSWORD") or os.getenv("PGPASSWORD")

    if not password:
        raise RuntimeError(
            "Mot de passe PostgreSQL manquant. "
            "Définissez PAYROLL_DB_PASSWORD ou PGPASSWORD dans votre .env"
        )

    dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    logger.debug(f"DSN construit depuis variables: {user}@{host}:{port}/{database}")

    # Ajouter connect_timeout si absent
    dsn = _ensure_connect_timeout(dsn)

    return dsn


def get_admin_dsn() -> str:
    """DSN pour accès superuser (opérations d'administration)."""

    base_config = _get_base_config()
    host = base_config["host"]
    port = base_config["port"]
    database = base_config["database"]

    admin_user = os.getenv("PAYROLL_DB_SUPERUSER", "postgres")
    admin_password = os.getenv("PAYROLL_DB_SUPERUSER_PASSWORD")

    if not admin_password:
        raise RuntimeError(
            "Mot de passe superuser manquant. Définissez PAYROLL_DB_SUPERUSER_PASSWORD dans votre .env"
        )

    dsn = f"postgresql://{admin_user}:{admin_password}@{host}:{port}/{database}"
    return _ensure_connect_timeout(dsn)


def _configure_new_connection(conn, *, autocommit: bool) -> None:
    """Applique les réglages standard (search_path, timeouts, etc.)."""
    conn.autocommit = autocommit
    with conn.cursor() as cur:
        cur.execute(
            f"""
                SET application_name = 'PayrollAnalyzer';
                SET search_path = {SEARCH_PATH};
                SET statement_timeout = {PG_STATEMENT_TIMEOUT_MS};
                SET lock_timeout = {PG_LOCK_TIMEOUT_MS};
                SET idle_in_transaction_session_timeout = {PG_IDLE_IN_TX_TIMEOUT_MS};
                SET TIMEZONE = '{TIMEZONE}';
            """
        )


def open_connection(
    *,
    admin: bool = False,
    autocommit: bool = False,
    dsn_override: Optional[str] = None,
):
    """Ouvre une connexion psycopg en appliquant les réglages standard."""

    import psycopg

    dsn = dsn_override or (get_admin_dsn() if admin else get_dsn())
    conn = psycopg.connect(dsn, connect_timeout=DEFAULT_TIMEOUT)
    _configure_new_connection(conn, autocommit=autocommit)
    return conn


def get_app_credentials() -> Dict[str, str]:
    """Retourne les identifiants applicatifs (user/password)."""

    base = _get_base_config()
    password = os.getenv("PAYROLL_DB_PASSWORD") or os.getenv("PGPASSWORD") or ""
    return {
        "user": base["user"],
        "password": password,
    }


def _ensure_connect_timeout(dsn: str) -> str:
    """Ajoute connect_timeout au DSN s'il n'est pas présent."""
    if "connect_timeout=" not in dsn:
        separator = "&" if "?" in dsn else "?"
        dsn = f"{dsn}{separator}connect_timeout={DEFAULT_TIMEOUT}"
    return dsn


def _has_password(dsn: str) -> bool:
    """Vérifie si un DSN contient un mot de passe."""
    if not dsn:
        return False

    # Format URL: postgresql://user:password@host:port/db
    if "://" in dsn and "@" in dsn:
        try:
            auth_part = dsn.split("://")[1].split("@")[0]
            if ":" in auth_part:
                password = auth_part.split(":")[1]
                return bool(password)
        except (IndexError, AttributeError):
            pass

    # Format conninfo: password=xxx
    if "password=" in dsn.lower():
        return True

    return False


def mask_dsn(dsn: str) -> str:
    """Masque le mot de passe dans un DSN pour les logs."""
    if not dsn:
        return ""

    try:
        if "://" in dsn and "@" in dsn:
            parts = dsn.split("://")
            scheme = parts[0]
            rest = parts[1]
            auth, location = rest.split("@", 1)

            if ":" in auth:
                user = auth.split(":")[0]
                return f"{scheme}://{user}:****@{location}"
            else:
                return dsn
        else:
            # Format conninfo
            import re

            return re.sub(
                r"(password\s*=\s*)[^\s]+", r"\1****", dsn, flags=re.IGNORECASE
            )
    except Exception:
        return dsn


# ============================================================================
# FONCTION: GET_CONNECTION (Pool de connexions)
# ============================================================================

_connection_pool = None


def get_connection_pool():
    """
    Retourne le pool de connexions global (singleton).

    Returns:
        DataRepository avec pool de connexions configuré
    """
    global _connection_pool

    if _connection_pool is None:
        from app.services.data_repo import DataRepository

        dsn = get_dsn()
        _connection_pool = DataRepository(
            connection_string=dsn, min_size=DEFAULT_POOL_MIN, max_size=DEFAULT_POOL_MAX
        )

        logger.info(f"Pool de connexions initialisé: {mask_dsn(dsn)}")

    return _connection_pool


def close_connection_pool():
    """Ferme le pool de connexions global."""
    global _connection_pool

    if _connection_pool is not None:
        try:
            _connection_pool.close()
            logger.info("Pool de connexions fermé")
        except Exception as e:
            logger.warning(f"Erreur fermeture pool: {e}")
        finally:
            _connection_pool = None


# ============================================================================
# FONCTIONS WRAPPER: RUN_SQL / RUN_SELECT
# ============================================================================


def run_sql(query: str, params: Optional[Dict[str, Any]] = None) -> None:
    """
    Exécute une requête SQL (INSERT/UPDATE/DELETE/DDL) via le pool.

    Args:
        query: Requête SQL à exécuter
        params: Paramètres de la requête (optionnel)

    Raises:
        Exception: Si la requête échoue
    """
    pool = get_connection_pool()
    pool.run_query(query, params)


def run_select(query: str, params: Optional[Dict[str, Any]] = None) -> list:
    """
    Exécute une requête SELECT via le pool et retourne les résultats.

    Args:
        query: Requête SELECT à exécuter
        params: Paramètres de la requête (optionnel)

    Returns:
        Liste de tuples avec les résultats

    Raises:
        Exception: Si la requête échoue
    """
    pool = get_connection_pool()
    return pool.run_query(query, params)


def get_connection():
    """
    Retourne une connexion du pool (context manager).

    Usage:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT ...")

    Returns:
        Connection context manager
    """
    pool = get_connection_pool()
    return pool.get_connection()


# ============================================================================
# FONCTION: TEST_CONNECTION
# ============================================================================


def test_connection() -> Dict[str, Any]:
    """
    Teste la connexion PostgreSQL.

    Returns:
        dict avec 'success', 'user', 'database', 'version', 'error'
    """
    import psycopg

    try:
        dsn = get_dsn()

        with psycopg.connect(dsn, connect_timeout=DEFAULT_TIMEOUT) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_user, current_database(), version()")
                row = cur.fetchone()
                if (
                    row is None
                    or not isinstance(row, (tuple, list))
                    or any(val is None for val in row)
                ):
                    return {
                        "success": False,
                        "error": "Aucune donnée retournée ou valeur manquante par la requête de test de connexion",
                    }
                user, database, version = row

                return {
                    "success": True,
                    "user": user,
                    "database": database,
                    "version": version.split(",")[0],
                    "dsn_masked": mask_dsn(dsn),
                }

    except Exception as e:
        logger.error(f"Échec test connexion: {e}")
        return {"success": False, "error": str(e)}


# ============================================================================
# FONCTION: GET_CONFIG_INFO
# ============================================================================


def get_config_info() -> Dict[str, Any]:
    """
    Retourne les informations de configuration (sans secrets).

    Returns:
        dict avec toutes les variables de config
    """
    return {
        "PAYROLL_DB_HOST": os.getenv("PAYROLL_DB_HOST", "localhost"),
        "PAYROLL_DB_PORT": os.getenv("PAYROLL_DB_PORT", "5432"),
        "PAYROLL_DB_NAME": os.getenv("PAYROLL_DB_NAME", "payroll_db"),
        "PAYROLL_DB_USER": os.getenv("PAYROLL_DB_USER", "payroll_unified"),
        "PAYROLL_DB_PASSWORD": (
            "***" if os.getenv("PAYROLL_DB_PASSWORD") else "(non défini)"
        ),
        "PGPASSWORD": "***" if os.getenv("PGPASSWORD") else "(non défini)",
        "PAYROLL_DSN": "défini" if os.getenv("PAYROLL_DSN") else "(non défini)",
        "APP_ENV": os.getenv("APP_ENV", "development"),
    }


# ============================================================================
# SCRIPT DE TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("TEST MODULE DE CONNEXION STANDARDISÉ")
    print("=" * 70)

    # 1. Configuration
    print("\n1. CONFIGURATION:")
    config = get_config_info()
    for key, value in config.items():
        print(f"   {key}: {value}")

    # 2. DSN
    print("\n2. DSN:")
    try:
        dsn = get_dsn()
        print(f"   ✅ DSN: {mask_dsn(dsn)}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        sys.exit(1)

    # 3. Test connexion
    print("\n3. TEST CONNEXION:")
    result = test_connection()
    if result["success"]:
        print(f"   ✅ Connecté: {result['user']}@{result['database']}")
        print(f"   Version: {result['version']}")
    else:
        print(f"   ❌ Erreur: {result['error']}")
        sys.exit(1)

    # 4. Pool
    print("\n4. POOL DE CONNEXIONS:")
    try:
        pool = get_connection_pool()
        print("   ✅ Pool initialisé")

        # Test requête
        result = pool.run_query("SELECT 1 AS test")
        print(f"   ✅ Requête test: {result}")

        close_connection_pool()
        print("   ✅ Pool fermé")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 70)
    print("✅ TOUS LES TESTS PASSENT")
    print("=" * 70)
