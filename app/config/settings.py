"""Central configuration and environment bootstrap for the application.

Responsibilities:
- bootstrap environment from app/.env (python-dotenv if available)
- expose get_dsn() with priority: CLI --dsn > PAYROLL_DSN env
- validate presence of password (or PGPASSWORD) and set dsn_error_reason
- provide small logging configuration helper
"""

from __future__ import annotations

import os
import logging
from typing import Optional

from .connection_standard import (
    get_dsn as get_standard_dsn,
    mask_dsn as standard_mask_dsn,
)

_logger = logging.getLogger(__name__)

# Internal flag to avoid double-installing console sanitizers
_console_sanitizer_installed = False

# Public settings
APPLICATION_NAME = os.getenv("APPLICATION_NAME", "PayrollApp")
APP_ENV = os.getenv("APP_ENV", "production")

# Error reason when DSN considered invalid
dsn_error_reason: Optional[str] = None


def bootstrap_env(app_root: Optional[str] = None) -> None:
    """Load .env file located in app/ if present and configure basic logging.

    This function is safe to call multiple times.
    """
    # Configure short, timestamped logging if not already configured
    configure_logging()

    # Try to load dotenv from app/.env
    try:
        from dotenv import load_dotenv
    except Exception:
        _logger.debug("python-dotenv not available, skipping .env load")
        return

    if app_root is None:
        # app package path (this file lives in app/config)
        app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    env_path = os.path.join(app_root, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path, override=False)
        _logger.info(f"Chargé .env depuis: {env_path}")
    else:
        _logger.debug("Aucun fichier .env trouvé dans app/ (c'est OK en production)")

    # Install console sanitizers (idempotent)
    _install_console_sanitizer()


def _parse_cli_dsn() -> Optional[str]:
    """Parse --dsn from sys.argv without interfering with the program.

    Returns the provided DSN string or None.
    """
    import argparse

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--dsn", dest="dsn", help="Postgres DSN (overrides env)")
    try:
        ns, _ = parser.parse_known_args()
        return ns.dsn
    except Exception:
        return None


def _has_password_in_dsn(dsn: str) -> bool:
    """Return True if DSN contains a password portion or if PGPASSWORD present."""
    if not dsn:
        return False
    # Simple check for user:password@ or password= in conninfo
    if "password=" in dsn:
        return True
    # URL style: user:pass@host
    if "://" in dsn and "@" in dsn:
        # crude detection: find : between scheme// and @
        try:
            rest = dsn.split("://", 1)[1]
            if ":" in rest and "@" in rest:
                # ensure colon is before at
                colon_idx = rest.find(":")
                at_idx = rest.find("@")
                return colon_idx < at_idx
        except Exception:
            pass
    return False


def get_dsn() -> Optional[str]:
    """Return an validated DSN or None.

    Priority: CLI --dsn > PAYROLL_DSN env

    If DSN exists in env (PAYROLL_DSN) but contains no password and PGPASSWORD
    is not set, this function will return None and set `dsn_error_reason`.
    """
    global dsn_error_reason
    dsn_error_reason = None

    # 1) CLI
    cli = _parse_cli_dsn()
    if cli:
        _logger.debug("DSN fourni via CLI")
        # If CLI DSN lacks password, allow if PGPASSWORD env set
        if _has_password_in_dsn(cli) or os.getenv("PGPASSWORD"):
            return cli
        dsn_error_reason = "no password supplied (CLI)"
        _logger.warning("DSN fourni par CLI mais aucun mot de passe détecté")
        return None

    # 2) Environment
    try:
        dsn = get_standard_dsn()
        return dsn
    except RuntimeError as exc:
        dsn_error_reason = str(exc)
        _logger.warning(f"Impossible d'obtenir un DSN standard: {exc}")
        return None


def get_runtime_config() -> dict:
    """Return a runtime configuration dictionary.

    Keys:
      - dsn: str | None
      - reason: str | None (if invalid)

    Priority: CLI --dsn > PAYROLL_DSN env
    """
    dsn = get_dsn()
    return {"dsn": dsn, "reason": dsn_error_reason}


def mask_dsn(dsn: Optional[str]) -> str:
    """Return DSN with password masked for safe logging."""
    return standard_mask_dsn(dsn) if dsn else ""


def _sanitize_text_for_console(s: str) -> str:
    """Replace non-ASCII symbolic decorations with ASCII equivalents.

    This function targets visual symbols commonly used in log/print
    messages (check marks, crosses, warning emoji) and replaces them
    with short ASCII tokens so printing to Windows consoles doesn't
    raise encoding errors.
    """
    if not isinstance(s, str) or not s:
        return s
    # mapping: symbol -> ASCII replacement
    mapping = {
        "✅": "[OK]",
        "❌": "[ERR]",
        "⚠️": "[WARN]",
    }
    out = s
    for k, v in mapping.items():
        out = out.replace(k, v)
    return out


def _install_console_sanitizer() -> None:
    """Monkeypatch builtins.print and add a logging filter to sanitize
    all console-bound strings. Safe to call multiple times.
    """
    global _console_sanitizer_installed
    if _console_sanitizer_installed:
        return
    try:
        import builtins

        # Wrap print
        _orig_print = builtins.print

        def _safe_print(*args, **kwargs):
            try:
                new_args = tuple(
                    _sanitize_text_for_console(a) if isinstance(a, str) else a
                    for a in args
                )
            except Exception:
                new_args = args
            return _orig_print(*new_args, **kwargs)

        builtins.print = _safe_print

        # Logging filter
        class _SanitizeFilter(logging.Filter):
            def filter(self, record: logging.LogRecord) -> bool:
                try:
                    if isinstance(record.msg, str):
                        record.msg = _sanitize_text_for_console(record.msg)
                    if record.args:
                        if isinstance(record.args, tuple):
                            record.args = tuple(
                                (
                                    _sanitize_text_for_console(a)
                                    if isinstance(a, str)
                                    else a
                                )
                                for a in record.args
                            )
                        elif isinstance(record.args, dict):
                            record.args = {
                                k: (
                                    _sanitize_text_for_console(v)
                                    if isinstance(v, str)
                                    else v
                                )
                                for k, v in record.args.items()
                            }
                except Exception:
                    pass
                return True

        logging.getLogger().addFilter(_SanitizeFilter())
        _console_sanitizer_installed = True
        _logger.debug("Console sanitizer installé (print/logs seront normalisés)")
    except Exception:
        _logger.debug("Impossible d'installer le console sanitizer")


def configure_logging(level: int = logging.INFO) -> None:
    """Basic logging configuration used by the application.

    Sets a short timestamped format if no handlers are configured yet.
    """
    if logging.getLogger().handlers:
        # Assume logging already configured
        return
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, datefmt="%Y-%m-%d %H:%M:%S")
    _logger.debug("Logging initialisé")


__all__ = [
    "bootstrap_env",
    "get_dsn",
    "configure_logging",
    "APPLICATION_NAME",
    "APP_ENV",
    "dsn_error_reason",
]
