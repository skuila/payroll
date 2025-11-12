import os
import sys
import pandas as pd
import tempfile
import datetime
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# 1. Générer un fichier Excel temporaire avec les 15 colonnes attendues
excel_columns = [
    "N de ligne",
    "Categorie d'emploi",
    "code emploi",
    "titre d'emploi",
    "date de paie",
    "matricule",
    "employé",
    "categorie de paie",
    "code de paie",
    "desc code de paie",
    "poste Budgetaire",
    "desc poste Budgétaire",
    "montant ",
    "part employeur",
    "Mnt/Cmb",
]

row = [
    1,
    "Soutien",
    "4301.0",
    "Surveillant d'élèves",
    datetime.date.today().isoformat(),
    "2093",
    "Dupont, Jean",
    "Assurances",
    "802",
    "Soins dentaires",
    "0-000-03270-000",
    "C-Adm Gén-Ass coll à payer",
    "-14.18",
    "14.18308",
    "0.00",
]

df = pd.DataFrame([row], columns=excel_columns)

with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
    excel_path = tmp.name
    df.to_excel(excel_path, index=False)

print(f"OK: Fichier Excel de test généré: {excel_path}")

# 2. Appeler le service d'import
try:
    from app.services.import_service_complete import ImportServiceComplete
    from app.providers.postgres_provider import PostgresProvider
    from app.services.schema_editor import get_schema_editor
except Exception as e:
    print(f"[ERROR] Import des modules: {e}")
    sys.exit(1)

provider = PostgresProvider()
if not provider or not provider.repo:
    print("[ERROR] Connexion BD indisponible (définissez PGPASSWORD)")
    sys.exit(2)

import_service = ImportServiceComplete()

try:
    # Simuler l'import
    result = import_service.import_payroll_excel(
        excel_path,
        period_id="2025-11",
        pay_date=datetime.date.today(),
        user_id="test_user",
        status="completed",
    )
    print(f"OK: Import terminé: {result}")
except Exception as e:
    print(f"[ERROR] Erreur import: {e}")
    sys.exit(3)

# 3. Vérifier la présence des données dans la table imported_payroll_master
se = get_schema_editor(provider)
rows = provider.repo.run_query(
    "SELECT * FROM payroll.imported_payroll_master WHERE matricule = %s ORDER BY imported_at DESC LIMIT 1",
    {"matricule": "2093"},
)
if rows:
    print("OK: Donnée importée retrouvée en base:")
    print(json.dumps(rows[0], ensure_ascii=False, indent=2))
else:
    print("❌ Donnée non retrouvée en base !")

# 4. Nettoyer le fichier temporaire
os.remove(excel_path)
print("OK: Fichier Excel temporaire supprimé.")
