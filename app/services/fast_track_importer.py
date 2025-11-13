# services/fast_track_importer.py
# ========================================
# VOIE RAPIDE IMPORT (Fast Track)
# ========================================
# Import direct si en-têtes exactes (15 colonnes maître)
# AUCUN échec bloquant - tolérance totale

import re
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from .locale_fr_ca import parse_date_fr_ca, parse_number_fr_ca


# ========== MAPPING EXACT (15 colonnes) ==========

MASTER_COLUMNS = {
    "N de ligne": "n_de_ligne",
    "Categorie d'emploi": "categorie_emploi",
    "code emploie": "code_emploie",
    "titre d'emploi": "titre_emploi",
    "date de paie": "date_paie",
    "matricule": "matricule",
    "employé": "employe",
    "categorie de paie": "categorie_paie",
    "code de paie": "code_paie",
    "desc code de paie": "desc_code_paie",
    "poste Budgetaire": "poste_budgetaire",
    "desc poste Budgetaire": "desc_poste_budgetaire",
    "montant": "montant",
    "part employeur": "part_employeur",
    "Mnt/Cmb": "mnt_cmb",
}


def normalize_header(h: str) -> str:
    """
    Normalise un en-tête pour matching (lowercase, trim, collapse spaces)

    Args:
        h: En-tête brut

    Returns:
        str: En-tête normalisé
    """
    s = str(h).strip().lower()
    s = " ".join(s.split())  # Collapse espaces
    return s


def is_fast_track_eligible(headers: List[str]) -> Tuple[bool, Dict[str, int]]:
    """
    Vérifie si le fichier est éligible à la voie rapide

    Critères:
    - Les 15 colonnes maître sont présentes (ordre libre)
    - Match exact des libellés (après normalisation)

    Args:
        headers: Liste en-têtes fichier

    Returns:
        (eligible: bool, mapping: dict)
        mapping = {db_field: col_idx}
    """
    # Normaliser headers fichier
    norm_headers = {normalize_header(h): i for i, h in enumerate(headers)}

    # Normaliser colonnes maître
    norm_master = {normalize_header(k): v for k, v in MASTER_COLUMNS.items()}

    # Vérifier présence toutes colonnes
    mapping = {}
    missing = []

    for master_key_norm, db_field in norm_master.items():
        if master_key_norm in norm_headers:
            col_idx = norm_headers[master_key_norm]
            mapping[db_field] = col_idx
        else:
            missing.append(master_key_norm)

    eligible = len(missing) == 0

    if not eligible:
        print(f"⚠️ Fast track NON éligible: {len(missing)} colonnes manquantes")
        for m in missing[:5]:
            print(f"   - '{m}'")
    else:
        print(f"✅ Fast track ÉLIGIBLE: 15/15 colonnes détectées")

    return eligible, mapping


# ========== CONVERSIONS TOLÉRANTES ==========


def convert_to_integer(value: Any) -> Optional[int]:
    """Convertit en INTEGER (tolérant)"""
    if value is None or str(value).strip() == "":
        return None

    try:
        # Si déjà un nombre
        if isinstance(value, (int, float)):
            return int(value)

        # Parse texte
        s = str(value).strip()
        return int(float(s))
    except:
        return None


def convert_to_date(value: Any) -> Optional[date]:
    """Convertit en DATE (tolérant, multiples formats)"""
    result = parse_date_fr_ca(value)
    return result


def convert_to_numeric(value: Any) -> Optional[Decimal]:
    """Convertit en NUMERIC(18,2) (tolérant FR-CA)"""
    result = parse_number_fr_ca(value)
    return result


def convert_to_text(value: Any) -> Optional[str]:
    """Convertit en TEXT (trim soft)"""
    if value is None:
        return None

    s = str(value).strip()
    return s if s != "" else None


# ========== CONVERTISSEURS PAR COLONNE ==========

FIELD_CONVERTERS = {
    "n_de_ligne": convert_to_integer,
    "categorie_emploi": convert_to_text,
    "code_emploie": convert_to_text,
    "titre_emploi": convert_to_text,
    "date_paie": convert_to_date,
    "matricule": convert_to_text,
    "employe": convert_to_text,
    "categorie_paie": convert_to_text,
    "code_paie": convert_to_text,
    "desc_code_paie": convert_to_text,
    "poste_budgetaire": convert_to_text,
    "desc_poste_budgetaire": convert_to_text,
    "montant": convert_to_numeric,
    "part_employeur": convert_to_numeric,
    "mnt_cmb": convert_to_numeric,  # NUMERIC maintenant (était TEXT)
}


# ========== IMPORTEUR FAST TRACK ==========


class FastTrackImporter:
    """
    Importeur voie rapide (sans détection)

    Workflow:
    1. Vérifier éligibilité (15 colonnes exactes)
    2. Convertir valeurs (tolérant, NULL si échec)
    3. Logger alertes (non bloquant)
    4. Insérer en masse
    """

    def __init__(self, db_repo=None):
        self.db_repo = db_repo
        self.current_run_id = None
        self.alerts = []

    def import_dataframe(self, df, source_file: str) -> Dict:
        """
        Importe un DataFrame en voie rapide

        Args:
            df: DataFrame pandas ou list[list]
            source_file: Nom fichier source

        Returns:
            dict: {
                "success": bool,
                "mode": "fast_track",
                "rows_imported": int,
                "rows_skipped": int,
                "alerts_count": int,
                "run_id": int
            }
        """
        print(f"🚀 FAST TRACK IMPORT: {source_file}")

        # ========== PARSING ==========

        try:
            import pandas as pd

            is_pandas = isinstance(df, pd.DataFrame)
        except:
            is_pandas = False
            pd = None

        if is_pandas:
            headers = [str(h) for h in df.columns]
            rows_data = df.values.tolist()
        else:
            if not df or len(df) == 0:
                return {"success": False, "message": "Fichier vide"}
            headers = [str(h) for h in df[0]]
            rows_data = df[1:]

        # ========== VÉRIFIER ÉLIGIBILITÉ ==========

        eligible, mapping = is_fast_track_eligible(headers)

        if not eligible:
            return {
                "success": False,
                "mode": "detection",
                "message": "Fast track non éligible - basculer sur détection",
            }

        print(f"  ✓ Mapping: {len(mapping)} colonnes")

        # ========== CRÉER RUN ==========

        if self.db_repo:
            self.current_run_id = self._create_run(source_file, len(rows_data))

        # ========== CONVERTIR LIGNES ==========

        rows_imported = 0
        rows_skipped = 0
        self.alerts = []

        converted_rows = []

        for row_idx, row in enumerate(rows_data, start=1):
            converted_row = {"source_row_number": row_idx}

            skip_row = False

            # Convertir chaque champ
            for db_field, col_idx in mapping.items():
                raw_value = row[col_idx] if col_idx < len(row) else None

                # Appliquer conversion
                converter = FIELD_CONVERTERS.get(db_field, convert_to_text)

                try:
                    converted_value = converter(raw_value)
                    converted_row[db_field] = converted_value

                    # Logger si NULL après conversion
                    if (
                        converted_value is None
                        and raw_value is not None
                        and str(raw_value).strip() != ""
                    ):
                        self.alerts.append(
                            {
                                "row": row_idx,
                                "column": db_field,
                                "raw_value": str(raw_value)[:100],
                                "alert_type": "conversion_failed",
                                "message": f"Conversion échouée: '{raw_value}' → NULL",
                            }
                        )

                except Exception as e:
                    converted_row[db_field] = None
                    self.alerts.append(
                        {
                            "row": row_idx,
                            "column": db_field,
                            "raw_value": str(raw_value)[:100] if raw_value else "",
                            "alert_type": "conversion_failed",
                            "message": str(e),
                        }
                    )

            # RÈGLE: Seule date_paie est obligatoire
            if converted_row.get("date_paie") is None:
                rows_skipped += 1
                self.alerts.append(
                    {
                        "row": row_idx,
                        "column": "date_paie",
                        "raw_value": str(
                            row[mapping.get("date_paie", 0)]
                            if mapping.get("date_paie") is not None
                            else ""
                        ),
                        "alert_type": "constraint_violation",
                        "message": "date_paie NULL (ligne ignorée)",
                    }
                )
                continue

            converted_rows.append(converted_row)
            rows_imported += 1

        # ========== INSÉRER EN DB ==========

        if self.db_repo and converted_rows:
            self._bulk_insert(converted_rows, source_file)

        # ========== LOGGER ALERTES ==========

        if self.db_repo and self.alerts:
            self._log_alerts()

        # ========== FINALISER RUN ==========

        if self.db_repo and self.current_run_id:
            self._complete_run(rows_imported, rows_skipped, len(self.alerts))

        print(f"  ✓ {rows_imported} lignes importées")
        print(f"  ⚠️ {rows_skipped} lignes ignorées")
        print(f"  📋 {len(self.alerts)} alertes")

        return {
            "success": True,
            "mode": "fast_track",
            "rows_imported": rows_imported,
            "rows_skipped": rows_skipped,
            "alerts_count": len(self.alerts),
            "run_id": self.current_run_id,
        }

    def _create_run(self, source_file: str, total_rows: int) -> int:
        """Crée un enregistrement import_runs"""
        sql = """
        INSERT INTO payroll.import_runs 
        (source_file, total_rows, status, import_mode, started_at)
        VALUES (%(file)s, %(rows)s, 'running', 'fast_track', CURRENT_TIMESTAMP)
        RETURNING run_id
        """

        with self.db_repo.pool.connection() as conn:
            result = self.db_repo.run_execute_returning(
                conn, sql, {"file": source_file, "rows": total_rows}
            )
            conn.commit()

            if result:
                print(f"  ✓ Run créé: ID {result[0]}")
                return result[0]

        return None

    def _bulk_insert(self, rows: List[Dict], source_file: str):
        """Insert en masse dans imported_payroll_master"""
        sql = """
        INSERT INTO payroll.imported_payroll_master (
            n_de_ligne, categorie_emploi, code_emploie, titre_emploi,
            date_paie, matricule, employe, categorie_paie,
            code_paie, desc_code_paie, poste_budgetaire, desc_poste_budgetaire,
            montant, part_employeur, mnt_cmb,
            import_run_id, source_file, source_row_number
        ) VALUES (
            %(n_de_ligne)s, %(categorie_emploi)s, %(code_emploie)s, %(titre_emploi)s,
            %(date_paie)s, %(matricule)s, %(employe)s, %(categorie_paie)s,
            %(code_paie)s, %(desc_code_paie)s, %(poste_budgetaire)s, %(desc_poste_budgetaire)s,
            %(montant)s, %(part_employeur)s, %(mnt_cmb)s,
            %(import_run_id)s, %(source_file)s, %(source_row_number)s
        )
        """

        with self.db_repo.pool.connection() as conn:
            for row in rows:
                params = {
                    **row,
                    "import_run_id": self.current_run_id,
                    "source_file": source_file,
                }
                self.db_repo.run_execute(conn, sql, params)

            conn.commit()
            print(f"  ✓ {len(rows)} lignes insérées")

    def _log_alerts(self):
        """Insère alertes dans import_log"""
        sql = """
        INSERT INTO payroll.import_log (
            run_id, source_row_number, column_name, raw_value, alert_type, alert_message
        ) VALUES (
            %(run_id)s, %(row)s, %(column)s, %(raw)s, %(type)s, %(message)s
        )
        """

        with self.db_repo.pool.connection() as conn:
            for alert in self.alerts[:1000]:  # Limite 1000 alertes
                self.db_repo.run_execute(
                    conn,
                    sql,
                    {
                        "run_id": self.current_run_id,
                        "row": alert["row"],
                        "column": alert["column"],
                        "raw": alert["raw_value"],
                        "type": alert["alert_type"],
                        "message": alert["message"],
                    },
                )

            conn.commit()
            print(f"  ✓ {len(self.alerts[:1000])} alertes loggées")

    def _complete_run(self, rows_imported: int, rows_skipped: int, alerts_count: int):
        """Finalise le run"""
        sql = """
        UPDATE payroll.import_runs
        SET completed_at = CURRENT_TIMESTAMP,
            status = 'completed',
            rows_imported = %(imported)s,
            rows_skipped = %(skipped)s,
            alerts_count = %(alerts)s
        WHERE run_id = %(run_id)s
        """

        with self.db_repo.pool.connection() as conn:
            self.db_repo.run_execute(
                conn,
                sql,
                {
                    "run_id": self.current_run_id,
                    "imported": rows_imported,
                    "skipped": rows_skipped,
                    "alerts": alerts_count,
                },
            )
            conn.commit()


# ========== TESTS ==========

if __name__ == "__main__":
    print("=" * 70)
    print("TEST FAST TRACK IMPORTER")
    print("=" * 70)

    # Test données avec headers EXACTS
    test_data = [
        # Headers EXACTS (15 colonnes)
        [
            "N de ligne",
            "Categorie d'emploi",
            "code emploie",
            "titre d'emploi",
            "date de paie",
            "matricule",
            "employé",
            "categorie de paie",
            "code de paie",
            "desc code de paie",
            "poste Budgetaire",
            "desc poste Budgetaire",
            "montant",
            "part employeur",
            "Mnt/Cmb",
        ],
        # Données
        [
            "1",
            "Régulier",
            "EMP01",
            "Technicien",
            "2023-01-15",
            "1001",
            "Dupont, Jean",
            "Gains",
            "SAL",
            "Salaire base",
            "1234",
            "Salaires",
            "1234.56",
            "200.00",
            "=A+B",
        ],
        [
            "2",
            "Régulier",
            "EMP01",
            "Analyste",
            "15/01/2023",
            "1002",
            "Martin, Claire",
            "Déductions",
            "DED",
            "RQAP",
            "5678",
            "Cotisations",
            "(50.00)",
            "0",
            "",
        ],
    ]

    # Test éligibilité
    print("\n1️⃣ Test éligibilité:")
    eligible, mapping = is_fast_track_eligible(test_data[0])

    print(f"\n   Éligible: {eligible}")
    print(f"   Mapping: {len(mapping)} champs")

    # Test conversion
    if eligible:
        print("\n2️⃣ Test conversion:")
        importer = FastTrackImporter()

        # Simuler import (sans DB)
        result = importer.import_dataframe(test_data, "test.xlsx")

        print(f"\n   Mode: {result.get('mode')}")
        print(f"   Success: {result.get('success')}")
        print(f"   Imported: {result.get('rows_imported')}")
        print(f"   Alerts: {result.get('alerts_count')}")

    print("\n✅ Test terminé")
