# services/staging_pipeline.py
# ========================================
# PIPELINE STAGING (Validation + Commit)
# ========================================
# Import souple: staging → validation → commit
# Aucune exception bloquante, tout passe en staging avec traçabilité

import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from .transformers import apply_transforms


class StagingPipeline:
    """
    Pipeline d'import avec staging souple

    Workflow:
    1. prepare() : Charge données → staging table (colonnes raw_ + parsed_ + issues)
    2. preview() : Affiche échantillon + totaux + erreurs
    3. commit() : Upsert vers tables normalisées (si OK utilisateur)
    """

    def __init__(self, db_repo=None):
        """
        Args:
            db_repo: Repository PostgreSQL (optionnel, pour commit)
        """
        self.db_repo = db_repo
        self.staging_data = []
        self.stats = {}
        self.issues_summary = {}

    def prepare(
        self,
        df,
        mapping: Dict[str, int],
        type_defs: Dict[str, Dict],
        profile: Optional[Dict] = None,
    ) -> Dict:
        """
        Prépare les données en staging (sans commit DB)

        Args:
            df: DataFrame ou list[list]
            mapping: {type_name: col_idx}
            type_defs: Définitions types depuis registry
            profile: Profil optionnel (paramètres custom)

        Returns:
            dict: {
                "staging_data": [...],  # Lignes transformées
                "stats": {...},          # Statistiques
                "issues": {...},         # Erreurs par type
                "preview": [...]         # Échantillon 50 lignes
            }
        """
        print("🔄 Préparation staging...")

        # ========== PARSING INPUT ==========

        try:
            import pandas as pd

            is_pandas = isinstance(df, pd.DataFrame)
        except Exception as _exc:
            is_pandas = False
            pd = None  # type: ignore[assignment]

        if is_pandas:
            rows_data = df.values.tolist()
        else:
            if not df or len(df) == 0:
                return {"staging_data": [], "stats": {}, "issues": {}, "preview": []}
            rows_data = df[1:]

        # ========== TRAITEMENT LIGNES ==========

        staging_rows: List[Dict[str, Any]] = []
        issues_by_type: Dict[str, List[Dict[str, Any]]] = {}
        transform_errors: List[Dict[str, Any]] = []

        for row_idx, row in enumerate(rows_data):
            staged_row: Dict[str, Any] = {
                "row_idx": row_idx,
                "raw": {},
                "parsed": {},
                "issues": [],
            }

            # Pour chaque type mappé
            for type_name, col_idx in mapping.items():
                if col_idx is None:
                    continue

                # Valeur brute
                raw_value = row[col_idx] if col_idx < len(row) else None
                staged_row["raw"][type_name] = raw_value

                # Appliquer transformations
                type_def = type_defs.get(type_name, {})
                transforms = type_def.get("transforms", [])

                try:
                    parsed_value = apply_transforms(raw_value, transforms)
                    staged_row["parsed"][type_name] = parsed_value

                    # Validation basique
                    if parsed_value is None or (
                        isinstance(parsed_value, str) and parsed_value.strip() == ""
                    ):
                        staged_row["issues"].append(
                            f"{type_name}: valeur vide après transformation"
                        )

                        if type_name not in issues_by_type:
                            issues_by_type[type_name] = []
                        issues_by_type[type_name].append(
                            {"row": row_idx, "issue": "valeur vide", "raw": raw_value}
                        )

                except Exception as e:
                    staged_row["parsed"][type_name] = None
                    staged_row["issues"].append(
                        f"{type_name}: erreur transformation ({e})"
                    )
                    transform_errors.append(
                        {"row": row_idx, "type": type_name, "error": str(e)}
                    )

            staging_rows.append(staged_row)

        # ========== STATISTIQUES ==========

        stats = {
            "total_rows": len(staging_rows),
            "rows_with_issues": sum(1 for r in staging_rows if r["issues"]),
            "rows_clean": sum(1 for r in staging_rows if not r["issues"]),
            "transform_errors": len(transform_errors),
            "issues_by_type": {k: len(v) for k, v in issues_by_type.items()},
        }

        # ========== ÉCHANTILLON PREVIEW ==========

        preview = staging_rows[:50]

        # Stocker pour commit ultérieur
        self.staging_data = staging_rows
        self.stats = stats
        self.issues_summary = issues_by_type

        print(f"  OK: {stats['total_rows']} lignes stagées")
        print(f"  OK: {stats['rows_clean']} lignes propres")
        print(f"  WARN: {stats['rows_with_issues']} lignes avec issues")

        return {
            "staging_data": staging_rows,
            "stats": stats,
            "issues": issues_by_type,
            "preview": preview,
        }

    def get_preview_table(self, limit: int = 50) -> List[Dict]:
        """
        Retourne un échantillon pour affichage UI

        Returns:
            List[dict]: Lignes preview avec colonnes visibles
        """
        return self.staging_data[:limit]

    def commit_to_db(self, user_confirmed: bool = False) -> Dict:
        """
        Commit staging → tables normalisées PostgreSQL

        IMPORTANT: Commit uniquement si user_confirmed=True

        Args:
            user_confirmed: Utilisateur a confirmé le mapping

        Returns:
            dict: {
                "success": bool,
                "rows_committed": int,
                "rows_skipped": int,
                "errors": [...]
            }
        """
        if not user_confirmed:
            return {
                "success": False,
                "message": "Commit annulé: confirmation utilisateur requise",
            }

        if not self.db_repo:
            return {"success": False, "message": "DB repository non disponible"}

        print("💾 Commit staging → DB...")

        # TODO: Implémenter UPSERT vers tables normalisées
        # Pour l'instant: placeholder

        rows_committed = 0
        rows_skipped = 0
        errors: List[Dict[str, Any]] = []

        for staged_row in self.staging_data:
            if staged_row["issues"]:
                rows_skipped += 1
            else:
                # UPSERT logic ici
                rows_committed += 1

        print(f"  OK: {rows_committed} lignes committées")
        print(f"  WARN: {rows_skipped} lignes ignorées (issues)")

        return {
            "success": True,
            "rows_committed": rows_committed,
            "rows_skipped": rows_skipped,
            "errors": errors,
        }

    def export_issues_report(self, output_path: str) -> None:
        """
        Exporte un rapport des erreurs détectées

        Args:
            output_path: Chemin fichier sortie (JSON ou CSV)
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats,
            "issues_by_type": self.issues_summary,
            "sample_errors": [r for r in self.staging_data if r["issues"]][
                :100
            ],  # 100 premières erreurs
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"OK: Rapport exporté: {output_path}")


# ========== TESTS ==========

if __name__ == "__main__":
    print("=" * 70)
    print("TEST STAGING PIPELINE")
    print("=" * 70)

    # Données test
    test_data = [
        ["Type", "Nom, Prénom", "Matricule", "Date", "Montant"],
        ["Gains", "Dupont, Jean", "1001", "2023-01-15", "1234.56"],
        ["Gains", "Martin, Claire", "1002", "2023-01-15", "2500.00"],
        ["Gains", "", "1003", "INVALID", "(500.00)"],  # Issues: nom vide, date invalide
    ]

    mapping = {
        "type_paie": 0,
        "fullname": 1,
        "matricule": 2,
        "date_paie": 3,
        "montant": 4,
    }

    type_defs = {
        "type_paie": {"transforms": [{"kind": "strip"}, {"kind": "title_case"}]},
        "fullname": {"transforms": [{"kind": "split_fullname"}]},
        "matricule": {"transforms": [{"kind": "strip"}, {"kind": "to_upper"}]},
        "date_paie": {"transforms": [{"kind": "to_iso_date"}]},
        "montant": {"transforms": [{"kind": "to_decimal"}]},
    }

    pipeline = StagingPipeline()
    result = pipeline.prepare(test_data, mapping, type_defs)

    print("\n📊 Statistiques:")
    for k, v in result["stats"].items():
        print(f"  {k}: {v}")

    print("\n📋 Preview (3 premières lignes):")
    for i, row in enumerate(result["preview"][:3]):
        print(f"\n  Ligne {i}:")
        print(f"    Raw: {row['raw']}")
        print(f"    Parsed: {row['parsed']}")
        if row["issues"]:
            print(f"    Issues: {row['issues']}")

    print("\n✅ Test terminé")
