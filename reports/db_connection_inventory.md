# Inventaire des scripts de connexion PostgreSQL

## 1. Sources officielles (liste blanche)

| Fichier | Rôle | Connexion |
| --- | --- | --- |
| `app/config/connection_standard.py` | Module central (DSN, pool, helpers `run_sql`, `get_connection`) | `psycopg.connect` uniquement dans les tests internes (autorisé) |
| `app/providers/postgres_provider.py` | Provider principal PyQt | Test initial `psycopg.connect` avant pool (autorisé) |
| `app/launch_payroll.py` | Lanceur desktop | Test DSN runtime via pool (autorisé) |

## 2. Scripts standardisés disponibles

| Script | Description | Commande |
| --- | --- | --- |
| `app/scripts/standardized/check_connection.py` | Vérifie la connexion via `test_connection()` | `python app/scripts/standardized/check_connection.py` |
| `app/scripts/standardized/db_overview.py` | Produit un JSON des tables principales | `python app/scripts/standardized/db_overview.py out/db.json` |
| `app/scripts/standardized/export_employees.py` | Exporte `core.employees` en CSV | `python app/scripts/standardized/export_employees.py out/employees.csv --limit 100` |

## 3. Scripts archivés (non standard)

Les anciens utilitaires ont été déplacés dans `archive/legacy_non_standard/` pour éviter toute utilisation future :

```
compare_excel_db.py
export_db_info.py
fix_password_and_test.py
get_db_structure.py
inspect_database.py
list_all_tables_columns.py
reset_payroll_app_password.py
show_database_structure.py
test_and_save.py
test_db_simple.py
test_db_working.py
test_excel_db_direct.py
test_real_connection.py
unify_passwords.py
verify_unified_setup.py
```

Ces fichiers étaient vides ou reposaient sur des connexions PostgreSQL directes. Toute nouvelle automatisation doit passer par `config.connection_standard`.

## 4. Scripts de test maintenus

| Fichier | Situation | Action |
| --- | --- | --- |
| `app/archive/scripts/tests/test_views_ok.py` | Ancien test manuel | Refactorisé pour utiliser `get_connection()` et `mask_dsn()` |

## 5. Vérification automatique

```
python scripts/forbid_direct_db_connect.py  ➜ ✅ Aucun accès direct non autorisé détecté.
```
