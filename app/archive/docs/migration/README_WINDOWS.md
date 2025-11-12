# Guide Exécution Windows - Migration Référentiel Employés

**Plateforme:** Windows 10/11  
**PowerShell:** 5.1+ ou PowerShell Core 7+  
**Python:** 3.10+

---

## 🪟 Spécificités Windows

### Problème: `pg_dump` non dans PATH

Sur Windows, les outils PostgreSQL ne sont pas automatiquement dans le PATH.

**Solutions:**

### Option 1: Utiliser le script Python de backup (RECOMMANDÉ)

```powershell
# Le script cherche automatiquement pg_dump ou propose un backup SQL alternatif
python migration\backup_database.py
```

Le script va:
1. Chercher `pg_dump` dans les emplacements standards:
   - `C:\Program Files\PostgreSQL\17\bin\pg_dump.exe`
   - `C:\Program Files\PostgreSQL\16\bin\pg_dump.exe`
   - etc.
2. Si trouvé → utilise `pg_dump` (backup complet)
3. Si non trouvé → propose backup SQL alternatif

---

### Option 2: Ajouter PostgreSQL au PATH

```powershell
# Temporaire (session PowerShell actuelle)
$env:Path += ";C:\Program Files\PostgreSQL\17\bin"

# Permanent (nécessite redémarrage PowerShell)
[Environment]::SetEnvironmentVariable(
    "Path",
    $env:Path + ";C:\Program Files\PostgreSQL\17\bin",
    [EnvironmentVariableTarget]::User
)
```

Vérifier:
```powershell
pg_dump --version
```

---

### Option 3: Utiliser chemin complet

```powershell
& "C:\Program Files\PostgreSQL\17\bin\pg_dump.exe" -U payroll_app -d payroll_db -F custom -f backup.dump
```

---

## 🚀 Exécution Automatisée (PowerShell)

### Script tout-en-un

```powershell
cd C:\Users\SZERTYUIOPMLMM\Desktop\PayrollAnalyzer_Etape0\migration

# Exécuter migration complète
.\execute_migration.ps1
```

**Le script va:**
1. ✅ Vérifier pré-requis
2. ✅ Créer backup (via Python)
3. ✅ Exécuter DDL
4. ✅ Migrer données
5. ✅ Exécuter tests SQL
6. ✅ Exécuter tests Python
7. ✅ Afficher résumé

**Options:**
```powershell
# Spécifier chemin psql personnalisé
.\execute_migration.ps1 -PsqlPath "C:\Program Files\PostgreSQL\16\bin\psql.exe"

# Sauter backup (non recommandé)
.\execute_migration.ps1 -SkipBackup
```

---

## 📋 Exécution Manuelle (étape par étape)

### ÉTAPE 1: Backup

```powershell
# Via script Python (recommandé)
python backup_database.py

# OU via pg_dump si dans PATH
pg_dump -U payroll_app -d payroll_db -F custom -f backup_pre_migration.dump

# OU avec chemin complet
& "C:\Program Files\PostgreSQL\17\bin\pg_dump.exe" -U payroll_app -d payroll_db -F custom -f backup_pre_migration.dump
```

**Important:** Ne pas continuer sans backup valide!

---

### ÉTAPE 2: DDL (Création structures)

```powershell
# Définir mot de passe (évite prompt)
$env:PGPASSWORD = "PayrollApp2025!"

# Exécuter DDL
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U payroll_app -d payroll_db -f 01_ddl_referentiel.sql

# OU si psql dans PATH
psql -U payroll_app -d payroll_db -f 01_ddl_referentiel.sql
```

**Attendu:** Message "✓ DDL exécuté avec succès"

---

### ÉTAPE 3: Migration données

```powershell
$env:PGPASSWORD = "PayrollApp2025!"

psql -U payroll_app -d payroll_db -f 02_migrate_to_referentiel.sql | Tee-Object migration_log.txt
```

**Attendu:**
```
MIGRATION TERMINÉE AVEC SUCCÈS
Employés         : 295 uniques insérés
Transactions     : 3352 insérées
Orphelins        : 0
```

---

### ÉTAPE 4: Tests validation

```powershell
psql -U payroll_app -d payroll_db -f 03_tests_validation.sql | Tee-Object tests_log.txt
```

**Vérifier dans `tests_log.txt`:**
- Nouveau comptage 2025-08 = 295
- Orphelins = 0
- Réduction ~44.4%

---

### ÉTAPE 5: Tests Python

```powershell
python test_kpi_regression.py
```

**Attendu:**
```
✅ TOUS LES TESTS RÉUSSIS
```

---

## 🔧 Localisation PostgreSQL sur Windows

### Chercher installation PostgreSQL

```powershell
# Méthode 1: Chercher répertoire PostgreSQL
Get-ChildItem "C:\Program Files\" -Filter "PostgreSQL" -Directory

# Méthode 2: Chercher pg_dump.exe
Get-ChildItem "C:\Program Files\PostgreSQL\" -Recurse -Filter "pg_dump.exe"

# Méthode 3: Via registre
Get-ItemProperty "HKLM:\SOFTWARE\PostgreSQL\Installations\*" | Select-Object DisplayName, InstallLocation
```

### Chemins typiques

```
C:\Program Files\PostgreSQL\17\bin\
C:\Program Files\PostgreSQL\16\bin\
C:\Program Files\PostgreSQL\15\bin\
C:\Program Files (x86)\PostgreSQL\17\bin\
```

---

## 🐍 Vérifications Python

```powershell
# Version Python
python --version
# Attendu: Python 3.10 ou supérieur

# Modules requis
python -c "import psycopg; print(f'psycopg {psycopg.__version__}')"
python -c "import sys; sys.path.insert(0, '..'); from services.data_repo import DataRepository; print('✓ Import OK')"
```

---

## 🔄 Rollback Windows

### Option 1: Restaurer backup pg_dump

```powershell
# Localiser backup
Get-ChildItem ..\backups\backup_pre_migration*.dump

# Restaurer (ATTENTION: écrase données!)
$env:PGPASSWORD = "PayrollApp2025!"
& "C:\Program Files\PostgreSQL\17\bin\pg_restore.exe" `
    -U payroll_app `
    -d payroll_db `
    --clean `
    --if-exists `
    ..\backups\backup_pre_migration_YYYYMMDD_HHMMSS.dump
```

### Option 2: Vider tables manuellement

```powershell
$env:PGPASSWORD = "PayrollApp2025!"

$rollbackSQL = @"
BEGIN;
TRUNCATE TABLE payroll.payroll_transactions CASCADE;
TRUNCATE TABLE core.employees CASCADE;
TRUNCATE TABLE payroll.stg_imported_payroll CASCADE;
DELETE FROM payroll.import_batches WHERE filename LIKE 'MIGRATION_INITIALE%';
COMMIT;
"@

$rollbackSQL | psql -U payroll_app -d payroll_db
```

### Option 3: Restaurer backup SQL alternatif

```powershell
psql -U payroll_app -d payroll_db -f ..\backups\backup_pre_migration_YYYYMMDD_HHMMSS.sql
```

---

## ⚠️ Résolution de problèmes Windows

### Erreur: "psql n'est pas reconnu"

**Solution:** Utiliser chemin complet ou ajouter au PATH (voir ci-dessus)

### Erreur: "Accès refusé" ou "Permission denied"

**Solution:** Lancer PowerShell en tant qu'administrateur

```powershell
# Clic droit sur PowerShell → "Exécuter en tant qu'administrateur"
```

### Erreur: "Mot de passe requis"

**Solution:** Définir variable d'environnement

```powershell
$env:PGPASSWORD = "PayrollApp2025!"
```

### Erreur: Script PowerShell bloqué

**Solution:** Autoriser exécution scripts

```powershell
# Voir politique actuelle
Get-ExecutionPolicy

# Autoriser (session actuelle)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# OU débloquer fichier spécifique
Unblock-File .\execute_migration.ps1
```

### Python: Module psycopg introuvable

**Solution:** Installer psycopg3

```powershell
pip install psycopg[binary]
```

---

## 📊 Logs et Diagnostics

### Sauvegarder tous les outputs

```powershell
# Démarrer transcript PowerShell
Start-Transcript -Path "migration_complete_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# Exécuter migration
.\execute_migration.ps1

# Arrêter transcript
Stop-Transcript
```

### Vérifier état migration

```powershell
# Dernier batch import
psql -U payroll_app -d payroll_db -c "SELECT * FROM payroll.import_batches ORDER BY batch_id DESC LIMIT 1;"

# Comptage employés
psql -U payroll_app -d payroll_db -c "SELECT COUNT(*) FROM core.employees;"

# Comptage transactions
psql -U payroll_app -d payroll_db -c "SELECT COUNT(*) FROM payroll.payroll_transactions;"
```

---

## ✅ Checklist Windows

Avant de commencer:
- [ ] PostgreSQL installé (vérifier avec `Get-Service postgresql*`)
- [ ] Python 3.10+ installé
- [ ] Module psycopg3 installé (`pip install psycopg[binary]`)
- [ ] Accès base `payroll_db` avec user `payroll_app`
- [ ] PowerShell 5.1+ (vérifier avec `$PSVersionTable`)

Après migration:
- [ ] Backup créé dans `backups/`
- [ ] Logs sauvegardés
- [ ] Tests SQL tous verts
- [ ] Tests Python tous réussis
- [ ] Nouveau comptage = 295 employés

---

## 🚀 Quick Start Windows

**Méthode rapide (tout automatisé):**

```powershell
cd C:\Users\SZERTYUIOPMLMM\Desktop\PayrollAnalyzer_Etape0\migration

# Tout en une commande
.\execute_migration.ps1 -PsqlPath "C:\Program Files\PostgreSQL\17\bin\psql.exe"
```

**Durée:** 30-60 minutes

---

**Support Windows complet fourni!** 🪟✅

