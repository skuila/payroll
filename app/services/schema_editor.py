"""Schema Editor Service

Fonctions pour lister les tables, inspecter les colonnes et préparer/appliquer
les modifications de schéma (ajout / renommage de colonnes) avec garde-fous.

Principes:
- Lecture uniquement: list_tables, get_table_columns
- Prévisualisation: retourne le SQL sans exécution
- Application: nécessite APP_ENV != 'production'
- Validation forte des identifiants et des types
- Journalisation dans app/schema_changes.log
"""

from __future__ import annotations
import os
import re
import json
from datetime import datetime
from typing import List, Dict, Optional


from config.connection_standard import get_connection_pool, get_app_credentials

VALID_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
# Types autorisés (extension possible)
ALLOWED_TYPES = {
    "text",
    "varchar(255)",
    "integer",
    "numeric(12,2)",
    "date",
    "timestamp",
    "boolean",
}

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "schema_changes.log")
APP_ENV = os.getenv("APP_ENV", "development")


class SchemaEditor:
    def __init__(self, repo):
        self.repo = repo

    # ---------------------- VALIDATIONS ----------------------
    def _validate_identifier(self, ident: str, kind: str) -> None:
        if not ident:
            raise ValueError(f"{kind} vide")
        if not VALID_IDENTIFIER.match(ident):
            raise ValueError(f"{kind} invalide: {ident}")
        if ident.lower() in {
            "select",
            "from",
            "where",
            "table",
            "group",
            "order",
            "and",
            "or",
            "not",
        }:
            raise ValueError(f"{kind} réservé: {ident}")

    def _validate_type(self, type_name: str) -> None:
        t = type_name.strip().lower()
        if t not in ALLOWED_TYPES:
            raise ValueError(
                f"Type non autorisé: {type_name}. Autorisés: {', '.join(sorted(ALLOWED_TYPES))}"
            )

    # ---------------------- LISTING ----------------------
    def list_tables(self, schema: str = "public") -> List[str]:
        self._validate_identifier(schema, "Schéma")
        if not self.repo:
            raise RuntimeError("DB non disponible")
        # Accès direct via connexion
        with self.repo.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = %s AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """,
                    (schema,),
                )
                rows = cur.fetchall()
        return [r[0] for r in rows]

    def get_table_columns(self, schema: str, table: str) -> List[Dict[str, str]]:
        self._validate_identifier(schema, "Schéma")
        self._validate_identifier(table, "Table")
        if not self.repo:
            raise RuntimeError("DB non disponible")
        with self.repo.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """,
                    (schema, table),
                )
                rows = cur.fetchall()
        return [
            {"name": r[0], "type": r[1], "nullable": (r[2] == "YES"), "default": r[3]}
            for r in rows
        ]

    # ---------------------- PREVIEW ----------------------
    def preview_add_column(
        self,
        schema: str,
        table: str,
        col_name: str,
        data_type: str,
        nullable: bool = True,
        default: Optional[str] = None,
    ) -> Dict[str, str]:
        self._validate_identifier(schema, "Schéma")
        self._validate_identifier(table, "Table")
        self._validate_identifier(col_name, "Colonne")
        self._validate_type(data_type)
        # Construction SQL
        parts = [f"ALTER TABLE {schema}.{table} ADD COLUMN {col_name} {data_type}"]
        if not nullable:
            parts.append("NOT NULL")
        if default:
            parts.append(f"DEFAULT {default}")
        sql_stmt = " ".join(parts) + ";"
        return {"action": "add_column", "sql": sql_stmt}

    def preview_rename_column(
        self, schema: str, table: str, old_name: str, new_name: str
    ) -> Dict[str, str]:
        self._validate_identifier(schema, "Schéma")
        self._validate_identifier(table, "Table")
        self._validate_identifier(old_name, "Ancien nom")
        self._validate_identifier(new_name, "Nouveau nom")
        sql_stmt = (
            f"ALTER TABLE {schema}.{table} RENAME COLUMN {old_name} TO {new_name};"
        )
        return {"action": "rename_column", "sql": sql_stmt}

    # ---------------------- APPLY ----------------------
    def apply_changes(self, sql_statements: List[str]) -> Dict[str, any]:
        if APP_ENV == "production":
            raise PermissionError("Modifications de schéma interdites en production")
        if not self.repo:
            raise RuntimeError("DB non disponible")
        executed = []
        errors = []
        with self.repo.get_connection() as conn:
            for stmt in sql_statements:
                s = stmt.strip()
                if not s:
                    continue
                try:
                    with conn.cursor() as cur:
                        cur.execute(s)
                    executed.append(s)
                except Exception as e:
                    errors.append({"sql": s, "error": str(e)})
            conn.commit()
        # Log
        self._log_changes(executed, errors)
        return {"executed": executed, "errors": errors, "success": len(errors) == 0}

    def _log_changes(self, executed: List[str], errors: List[Dict[str, str]]):
        try:
            line = json.dumps(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "user": get_app_credentials().get("user", "unknown"),
                    "executed": executed,
                    "errors": errors,
                },
                ensure_ascii=False,
            )
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


# Helper factory
def get_schema_editor(provider) -> Optional[SchemaEditor]:
    # Toujours retourner un éditeur, même si repo None, pour permettre la prévisualisation offline
    if not provider:
        return SchemaEditor(None)
    repo = getattr(provider, "repo", None) or get_connection_pool()
    return SchemaEditor(repo)
