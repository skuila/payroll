import os
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

EXPECTED_FILE = os.getenv(
    "EXPECTED_FILE", os.path.join(ROOT, "LISTE_COLONNES_EXCEL_REQUISES.txt")
)
SCHEMA = os.getenv("TARGET_SCHEMA", "payroll")
TABLE = os.getenv("TARGET_TABLE", "imported_payroll_master")

print(f"[COMPARE] Fichier attendu: {EXPECTED_FILE}")
print(f"[COMPARE] Cible BD: {SCHEMA}.{TABLE}")

# Parse expected headers
expected = []
with open(EXPECTED_FILE, "r", encoding="utf-8") as f:
    for line in f.readlines():
        # Conserver les espaces de fin pour détecter "montant "
        if line.endswith("\n"):
            line = line[:-1]
        # Skip separators and empty
        if not line.strip():
            continue
        if line.startswith("=") or line.startswith("("):
            continue
        # Lines with enumeration pattern '1.  ' etc.
        if line[:2].isdigit() or line.split(".")[0].isdigit():
            # Extract after the number & dot
            try:
                dot_index = line.index(".")
                # Ne retirer que les espaces de début, préserver les espaces de fin
                header = line[dot_index + 1 :]
                header = header.lstrip()
                if header:
                    expected.append(header)
            except ValueError:
                pass

print(f"[COMPARE] Entêtes attendues ({len(expected)}): {expected}")

try:
    from app.providers.postgres_provider import PostgresProvider
    from app.services.schema_editor import get_schema_editor
except Exception as e:
    print("[ERROR] Import failed:", e)
    sys.exit(1)

provider = PostgresProvider()
if not provider or not provider.repo:
    print("[ERROR] Connexion BD indisponible")
    sys.exit(2)

se = get_schema_editor(provider)
cols = se.get_table_columns(SCHEMA, TABLE)
normalized = [c["name"] for c in cols]

# Mapping (from doc) Excel -> DB
mapping = {
    "N de ligne": "numero_ligne",
    "Categorie d'emploi": "categorie_emploi",
    "code emploi": "code_emploi",
    "titre d'emploi": "titre_emploi",
    "date de paie": "date_paie",
    "matricule": "matricule",
    "employé": "nom_employe",
    "categorie de paie": "categorie_paie",
    "code de paie": "code_paie",
    "desc code de paie": "description_code_paie",
    "poste Budgetaire": "poste_budgetaire",
    "desc poste Budgétaire": "description_poste_budgetaire",
    "montant ": "montant_employe",  # espace intentionnel
    "part employeur": "part_employeur",
    "Mnt/Cmb": "montant_combine",
}

missing_in_db = []
extra_in_db = []
for header in expected:
    target = mapping.get(header)
    if not target:
        missing_in_db.append({"header": header, "reason": "mapping absent"})
    else:
        if target not in normalized:
            missing_in_db.append(
                {
                    "header": header,
                    "target_col": target,
                    "reason": "colonne BD manquante",
                }
            )

# Extra columns not mapped
mapped_targets = set(mapping.values())
for col in normalized:
    if col not in mapped_targets:
        extra_in_db.append(col)

result = {
    "schema": SCHEMA,
    "table": TABLE,
    "expected_headers_count": len(expected),
    "db_columns_count": len(normalized),
    "expected_headers": expected,
    "db_columns": normalized,
    "missing_or_unmapped": missing_in_db,
    "extra_db_columns": extra_in_db,
}

print(json.dumps(result, ensure_ascii=False, indent=2))
