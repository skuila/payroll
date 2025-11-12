import os
import sys
import pandas as pd
import tempfile
import datetime
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

print("=" * 80)
print("TEST END-TO-END: IMPORT FICHIER EXCEL → BASE DE DONNÉES")
print("=" * 80)

# 1. Générer un fichier Excel temporaire avec les 15 colonnes attendues
print("\n[ÉTAPE 1] Génération fichier Excel de test...")
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

test_date = datetime.date.today()
row = [
    1,
    "Soutien",
    "4301",
    "Surveillant d'élèves",
    test_date.isoformat(),
    "2093",
    "Dupont, Jean",
    "Assurances",
    "802",
    "Soins dentaires",
    "0-000-03270-000",
    "C-Adm Gén-Ass coll à payer",
    -14.18,
    14.18,
    0.00,
]

df = pd.DataFrame([row], columns=excel_columns)

with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False, mode="wb") as tmp:
    excel_path = tmp.name

df.to_excel(excel_path, index=False, engine="openpyxl")
print(f"OK: Fichier Excel généré: {excel_path}")
print(f"  - {len(excel_columns)} colonnes")
print(f"  - 1 ligne de données de test")

# 2. Importer les modules nécessaires
print("\n[ÉTAPE 2] Import des modules Python...")
try:
    from app.services.import_service_complete import ImportServiceComplete
    from app.providers.postgres_provider import PostgresProvider
    from app.services.kpi_snapshot_service import KPISnapshotService

    print("OK: Modules importés avec succès")
except Exception as e:
    print(f"❌ Erreur import modules: {e}")
    import traceback

    traceback.print_exc()
    os.remove(excel_path)
    sys.exit(1)

# 3. Initialiser le provider et vérifier la connexion BD
print("\n[ÉTAPE 3] Connexion à la base de données...")
try:
    provider = PostgresProvider()
    if not provider or not provider.repo:
        print("❌ Provider repo indisponible (vérifiez PGPASSWORD)")
        os.remove(excel_path)
        sys.exit(2)
    print("OK: Connexion PostgreSQL établie")
except Exception as e:
    print(f"❌ Erreur connexion BD: {e}")
    os.remove(excel_path)
    sys.exit(2)

# 4. Initialiser le service d'import
print("\n[ÉTAPE 4] Initialisation du service d'import...")
try:
    repo = provider.repo
    kpi_service = KPISnapshotService(repo)
    import_service = ImportServiceComplete(repo=repo, kpi_service=kpi_service)
    print("OK: ImportServiceComplete initialisé")
except Exception as e:
    print(f"❌ Erreur init service: {e}")
    import traceback

    traceback.print_exc()
    os.remove(excel_path)
    sys.exit(3)

# 5. Exécuter l'import
print("\n[ÉTAPE 5] Exécution de l'import...")
try:
    result = import_service.import_payroll_file(
        file_path=excel_path,
        pay_date=datetime.datetime.combine(test_date, datetime.time()),
        user_id="00000000-0000-0000-0000-000000000001",
        apply_sign_policy=False,
    )
    print("OK: Import terminé avec succès!")
    print(f"  - Batch ID: {result.get('batch_id')}")
    print(f"  - Lignes: {result.get('rows_count')}")
    print(f"  - Période: {result.get('period')}")
    print(f"  - Message: {result.get('message')}")
except Exception as e:
    print(f"❌ Erreur pendant l'import: {e}")
    import traceback

    traceback.print_exc()
    os.remove(excel_path)
    sys.exit(4)

# 6. Vérifier la présence des données dans la BD
print("\n[ÉTAPE 6] Vérification des données importées...")
try:
    rows = repo.run_query(
        "SELECT matricule, nom_employe, code_paie, montant_employe, part_employeur FROM payroll.imported_payroll_master WHERE matricule = %s ORDER BY imported_at DESC LIMIT 1",
        {"matricule": "2093"},
    )
    if rows:
        print("OK: Donnée importée retrouvée en base:")
        print(f"  - Matricule: {rows[0][0]}")
        print(f"  - Nom: {rows[0][1]}")
        print(f"  - Code paie: {rows[0][2]}")
        print(f"  - Montant employé: {rows[0][3]}")
        print(f"  - Part employeur: {rows[0][4]}")
    else:
        print("❌ Donnée non retrouvée en base!")
        os.remove(excel_path)
        sys.exit(5)
except Exception as e:
    print(f"❌ Erreur vérification BD: {e}")
    import traceback

    traceback.print_exc()
    os.remove(excel_path)
    sys.exit(5)

# 7. Nettoyer le fichier temporaire
print("\n[ÉTAPE 7] Nettoyage...")
try:
    os.remove(excel_path)
    print("OK: Fichier Excel temporaire supprimé")
except Exception as e:
    print(f"WARN: Impossible de supprimer le fichier temporaire: {e}")

print("\n" + "=" * 80)
print("✅ TEST END-TO-END RÉUSSI!")
print("=" * 80)
print("\nRésumé:")
print("  1. OK: Fichier Excel généré avec 15 colonnes attendues")
print("  2. OK: Import exécuté sans erreur")
print("  3. OK: Données vérifiées en base de données")
print("\nLa chaîne complète (Import → BD → Lecture) fonctionne correctement!")
