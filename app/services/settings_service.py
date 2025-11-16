import json
import logging
from typing import Any, Dict, List

from psycopg import errors
from psycopg.types.json import Json

from app.services.data_repo import DataRepository


class SettingsService:
    """Service centralisé pour la lecture/écriture des options UI/Analytique/Paie."""

    DEFAULT_INTERFACE = {
        "dark_mode": False,
        "language": "fr",
        "date_format": "dd/MM/yyyy",
        "validate_unknown_codes": False,
        "default_period": "",
    }
    DEFAULT_PAIE = {"use_sign_fallback": True}

    def __init__(self, repo: DataRepository):
        if repo is None:
            raise ValueError("DataRepository requis pour SettingsService")
        self.repo = repo
        self.logger = logging.getLogger(__name__)
        self._ui_table_ready = False

    def get_options(self) -> Dict[str, Any]:
        """Retourne les options prêtes à être envoyées au frontend."""
        ui_payload = self._load_ui_payload()
        interface = {
            "dark_mode": bool(
                ui_payload.get("dark_mode", self.DEFAULT_INTERFACE["dark_mode"])
            ),
            "language": ui_payload.get("language", self.DEFAULT_INTERFACE["language"]),
            "date_format": ui_payload.get(
                "date_format", self.DEFAULT_INTERFACE["date_format"]
            ),
        }
        synonyms = self._load_synonyms()
        paie_flags = self._load_paie_flags()
        paie_flags.update(
            {
                "validate_unknown_codes": bool(
                    ui_payload.get(
                        "validate_unknown_codes",
                        self.DEFAULT_INTERFACE["validate_unknown_codes"],
                    )
                ),
                "default_period": ui_payload.get(
                    "default_period", self.DEFAULT_INTERFACE["default_period"]
                ),
            }
        )

        return {
            "interface": interface,
            "analytique": {"synonyms": synonyms},
            "paie": paie_flags,
        }

    def update_options(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Met à jour les options depuis un payload JSON partiel."""
        if not isinstance(payload, dict):
            raise ValueError("Payload options invalide (dict attendu)")

        ui_payload = self._load_ui_payload()

        interface_opts = payload.get("interface")
        if isinstance(interface_opts, dict):
            if "dark_mode" in interface_opts:
                ui_payload["dark_mode"] = bool(interface_opts["dark_mode"])
            if "language" in interface_opts and interface_opts["language"]:
                ui_payload["language"] = str(interface_opts["language"])
            if "date_format" in interface_opts and interface_opts["date_format"]:
                ui_payload["date_format"] = str(interface_opts["date_format"])

        analytique_opts = payload.get("analytique", {}).get("synonyms", {})
        if isinstance(analytique_opts, dict):
            self._update_synonyms(analytique_opts)

        paie_opts = payload.get("paie")
        if isinstance(paie_opts, dict):
            if "use_sign_fallback" in paie_opts:
                self._update_paie_flags(bool(paie_opts["use_sign_fallback"]))
            if "validate_unknown_codes" in paie_opts:
                ui_payload["validate_unknown_codes"] = bool(
                    paie_opts["validate_unknown_codes"]
                )
            if "default_period" in paie_opts:
                ui_payload["default_period"] = (
                    paie_opts["default_period"] or ""
                ).strip()

        self._save_ui_payload(ui_payload)
        return self.get_options()

    # -------------------- Chargement --------------------
    def _load_synonyms(self) -> Dict[str, List[str]]:
        sql = """
            SELECT categorie, synonyms
            FROM paie.param_categories_synonyms
            WHERE categorie IN ('Gains', 'Deductions')
        """
        data: Dict[str, List[str]] = {"Gains": [], "Deductions": []}
        try:
            with self.repo.get_connection() as conn:
                rows = self.repo.run_select(conn, sql)
            for categorie, synonyms in rows:
                if categorie in data:
                    data[categorie] = [s for s in (synonyms or []) if s]
        except errors.UndefinedTable:
            self.logger.warning(
                "Table paie.param_categories_synonyms absente, utilisation des valeurs par défaut."
            )
        except Exception as exc:
            self.logger.error("Erreur chargement synonymes: %s", exc)
        return data

    def _load_paie_flags(self) -> Dict[str, Any]:
        sql = """
            SELECT use_sign_fallback
            FROM paie.param_calcul_flags
            WHERE id = 1
        """
        flags = dict(self.DEFAULT_PAIE)
        try:
            with self.repo.get_connection() as conn:
                rows = self.repo.run_select(conn, sql)
            if rows:
                flags["use_sign_fallback"] = bool(rows[0][0])
        except errors.UndefinedTable:
            self.logger.warning(
                "Table paie.param_calcul_flags absente, use_sign_fallback par défaut."
            )
        except Exception as exc:
            self.logger.error("Erreur chargement flags paie: %s", exc)
        return flags

    def _load_ui_payload(self) -> Dict[str, Any]:
        self._ensure_ui_table()
        sql = "SELECT payload FROM paie.param_ui_options WHERE id = 1"
        result: Dict[str, Any] = {}
        try:
            with self.repo.get_connection() as conn:
                rows = self.repo.run_select(conn, sql)
            if rows:
                stored = rows[0][0]
                if isinstance(stored, dict):
                    result = stored
                elif isinstance(stored, str):
                    result = json.loads(stored)
        except errors.UndefinedTable:
            self.logger.warning(
                "Table param_ui_options absente, utilisation des valeurs par défaut."
            )
        except Exception as exc:
            self.logger.error("Erreur chargement des options UI: %s", exc)

        if not result:
            result = dict(self.DEFAULT_INTERFACE)
            self._save_ui_payload(result)
        return result

    # -------------------- Mise à jour --------------------
    def _update_synonyms(self, synonyms_map: Dict[str, Any]) -> None:
        if not synonyms_map:
            return
        sql = """
            INSERT INTO paie.param_categories_synonyms (categorie, synonyms, updated_at)
            VALUES (%(categorie)s, %(synonyms)s, NOW())
            ON CONFLICT (categorie)
            DO UPDATE SET synonyms = EXCLUDED.synonyms, updated_at = NOW()
        """
        try:
            with self.repo.get_connection() as conn:
                for categorie, values in synonyms_map.items():
                    if categorie not in {"Gains", "Deductions"}:
                        continue
                    if isinstance(values, str):
                        values = [v.strip() for v in values.split(",") if v.strip()]
                    elif isinstance(values, (list, tuple)):
                        values = [str(v).strip() for v in values if str(v).strip()]
                    else:
                        continue
                    self.repo.run_execute(
                        conn,
                        sql,
                        {"categorie": categorie, "synonyms": values},
                    )
        except errors.UndefinedTable:
            self.logger.warning(
                "Table paie.param_categories_synonyms absente, impossible d'enregistrer les synonymes."
            )
        except Exception as exc:
            self.logger.error("Erreur mise à jour synonymes: %s", exc)

    def _update_paie_flags(self, use_sign_fallback: bool) -> None:
        sql = """
            INSERT INTO paie.param_calcul_flags (id, use_sign_fallback, updated_at)
            VALUES (1, %(value)s, NOW())
            ON CONFLICT (id)
            DO UPDATE SET use_sign_fallback = EXCLUDED.use_sign_fallback,
                          updated_at = NOW()
        """
        try:
            with self.repo.get_connection() as conn:
                self.repo.run_execute(conn, sql, {"value": use_sign_fallback})
        except errors.UndefinedTable:
            self.logger.warning(
                "Table paie.param_calcul_flags absente, impossible d'enregistrer use_sign_fallback."
            )
        except Exception as exc:
            self.logger.error("Erreur mise à jour flags paie: %s", exc)

    def _save_ui_payload(self, payload: Dict[str, Any]) -> None:
        self._ensure_ui_table()
        sql = """
            INSERT INTO paie.param_ui_options (id, payload, updated_at)
            VALUES (1, %(payload)s, NOW())
            ON CONFLICT (id)
            DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW()
        """
        try:
            with self.repo.get_connection() as conn:
                self.repo.run_execute(conn, sql, {"payload": Json(payload)})
        except Exception as exc:
            self.logger.error("Erreur sauvegarde options UI: %s", exc)

    # -------------------- Helpers --------------------
    def _ensure_ui_table(self) -> None:
        if self._ui_table_ready:
            return
        ddl = """
            CREATE TABLE IF NOT EXISTS paie.param_ui_options (
              id SMALLINT PRIMARY KEY DEFAULT 1,
              payload JSONB NOT NULL DEFAULT '{}'::jsonb,
              updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """
        try:
            with self.repo.get_connection() as conn:
                self.repo.run_execute(conn, ddl)
            self._ui_table_ready = True
        except Exception as exc:
            self.logger.warning(
                "Impossible de créer/valider paie.param_ui_options: %s", exc
            )
            self._ui_table_ready = True  # éviter boucle infinie même en cas d'échec
