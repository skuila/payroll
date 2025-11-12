# 🎯 Commandes d'Exécution — Migration Référentiel Employés

**Version:** 3.0 FINAL  
**Durée totale:** 45-60 minutes  
**Workspace:** `C:\Users\SZERTYUIOPMLMM\Desktop\PayrollAnalyzer_Etape0`

---

## 📋 Prérequis - À vérifier AVANT de commencer

### 1. PowerShell (Shell principal)

```powershell
# Se placer dans le workspace
cd C:\Users\SZERTYUIOPMLMM\Desktop\PayrollAnalyzer_Etape0

# Vérifier psycopg3
python -c "import psycopg; print(f'psycopg {psycopg.__version__}')"
```

**Sortie attendue:** `psycopg 3.x.x`

---

### 2. PostgreSQL (Base de données)

```powershell
# Depuis PowerShell
$env:PGPASSWORD = "PayrollApp2025!"
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U payroll_app -d payroll_db -c "SELECT COUNT(*) FROM payroll.imported_payroll_master;"
```

**Sortie attendue:** `7735` (ou similaire)

---

### 3. Extensions PostgreSQL (psql)

```sql
-- Depuis psql
psql -U payroll_app -d payroll_db

-- Exécuter
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Vérifier
\dx
```

**Sortie attendue:** `unaccent` et `pgcrypto` dans la liste

---

## 🚀 PHASE 0: Backup (OBLIGATOIRE - 5 min)

### OÙ: PowerShell
### QUI: python

```powershell
# Se placer dans workspace
cd C:\Users\SZERTYUIOPMLMM\Desktop\PayrollAnalyzer_Etape0

# Exécuter backup
python migration\backup_database.py
```

### Sortie attendue:
```
✅ Backup créé avec succès (XX.XX MB)
   Fichier: backups\backup_pre_migration_20251016_HHMMSS.dump
```

### Validation:
```powershell
# Vérifier fichier créé
Get-ChildItem backups\backup_pre_migration*.dump
```

### ⚠️ SI ERREUR (pg_dump introuvable):
```powershell
# Spécifier chemin explicitement
$env:PGPASSWORD = "PayrollApp2025!"
& "C:\Program Files\PostgreSQL\17\bin\pg_dump.exe" -U payroll_app -d payroll_db -Fc -f backups\backup_manual_$(Get-Date -Format 'yyyyMMdd_HHmmss').dump
```

---

## 🗂️ PHASE 1: DDL — Création structures (5 min)

### OÙ: PowerShell → psql
### QUI: psql

```powershell
# Depuis PowerShell
cd C:\Users\SZERTYUIOPMLMM\Desktop\PayrollAnalyzer_Etape0

# Configurer mot de passe
$env:PGPASSWORD = "PayrollApp2025!"

# Exécuter DDL
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" `
    -U payroll_app `
    -d payroll_db `
    -f migration\01_ddl_referentiel.sql
```

### Sortie attendue:
```
✓ DDL exécuté avec succès
  Tables créées:
    - core.employees
    - payroll.payroll_transactions (partitions 2024-2026)
    - payroll.import_batches
    - payroll.stg_imported_payroll
    - reference.pay_codes (avec seed)
  Vues créées:
    - payroll.v_imported_payroll_compat
    - core.v_employees_enriched
  Fonctions créées:
    - core.compute_employee_key()
```

### Validation:
```powershell
# Depuis PowerShell
$env:PGPASSWORD = "PayrollApp2025!"
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U payroll_app -d payroll_db -c "\dt core.employees"
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U payroll_app -d payroll_db -c "\dt payroll.payroll_transactions*"
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U payroll_app -d payroll_db -c "\df core.compute_employee_key"
```

### ✅ Critères succès:
- [ ] Aucune erreur dans sortie
- [ ] Tables créées (5 tables)
- [ ] Partitions créées (2024, 2025, 2026)
- [ ] Fonction `compute_employee_key` existe

### ⚠️ Rollback si erreur:
```sql
-- Depuis psql
DROP TABLE IF EXISTS payroll.payroll_transactions CASCADE;
DROP TABLE IF EXISTS core.employees CASCADE;
DROP TABLE IF EXISTS payroll.import_batches CASCADE;
DROP TABLE IF EXISTS payroll.stg_imported_payroll CASCADE;
DROP FUNCTION IF EXISTS core.compute_employee_key;
```

---

## 📊 PHASE 2: Migration données (10-15 min)

### OÙ: PowerShell → psql
### QUI: psql

```powershell
# Depuis PowerShell
cd C:\Users\SZERTYUIOPMLMM\Desktop\PayrollAnalyzer_Etape0

# Configurer mot de passe
$env:PGPASSWORD = "PayrollApp2025!"

# Exécuter migration (avec log)
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" `
    -U payroll_app `
    -d payroll_db `
    -f migration\02_migrate_to_referentiel.sql `
    | Tee-Object migration_log.txt
```

### Sortie attendue:
```
============================================================================
MIGRATION TERMINÉE AVEC SUCCÈS
============================================================================
Batch ID         : 1
Staging          : 3352 lignes
Employés         : 295 uniques insérés
Transactions     : 3352 insérées
Orphelins        : 0
Montant total    : 538402.22 $
============================================================================
```

### Validation:
```powershell
# Depuis PowerShell
$env:PGPASSWORD = "PayrollApp2025!"

# Compter employés (attendu: 295)
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U payroll_app -d payroll_db -c "SELECT COUNT(*) FROM core.employees;"

# Compter transactions (attendu: 3352)
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U payroll_app -d payroll_db -c "SELECT COUNT(*) FROM payroll.payroll_transactions;"

# Vérifier batch (attendu: completed)
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U payroll_app -d payroll_db -c "SELECT status FROM payroll.import_batches WHERE batch_id = 1;"
```

### ✅ Critères succès:
- [ ] Message "MIGRATION TERMINÉE AVEC SUCCÈS"
- [ ] Employés = **295**
- [ ] Transactions = **3352**
- [ ] **Orphelins = 0** (BLOQUANT)
- [ ] Batch status = **'completed'**

### ⚠️ SI ORPHELINS > 0 (BLOQUANT):
```sql
-- Identifier orphelins
SELECT 
    s.employee_key,
    s.matricule_raw,
    s.employe_raw,
    COUNT(*) AS nb_lignes
FROM payroll.stg_imported_payroll s
LEFT JOIN core.employees e ON s.employee_key = e.employee_key
WHERE e.employee_id IS NULL
GROUP BY s.employee_key, s.matricule_raw, s.employe_raw
LIMIT 20;

-- STOP - Ne pas continuer Phase 3
```

### ⚠️ Rollback si erreur:
```sql
-- Depuis psql
BEGIN;
TRUNCATE TABLE payroll.payroll_transactions CASCADE;
TRUNCATE TABLE core.employees CASCADE;
TRUNCATE TABLE payroll.stg_imported_payroll;
DELETE FROM payroll.import_batches WHERE filename LIKE 'MIGRATION_%';
COMMIT;
```

---

## ✅ PHASE 3: Tests SQL (5 min)

### OÙ: PowerShell → psql
### QUI: psql

```powershell
# Depuis PowerShell
cd C:\Users\SZERTYUIOPMLMM\Desktop\PayrollAnalyzer_Etape0

# Configurer mot de passe
$env:PGPASSWORD = "PayrollApp2025!"

# Exécuter tests (avec log)
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" `
    -U payroll_app `
    -d payroll_db `
    -f migration\03_tests_validation.sql `
    | Tee-Object tests_sql_log.txt
```

### Sortie attendue (extraits critiques):

```
TEST 2.3: Nouveau comptage 2025-08
           test           | resultat 
--------------------------+----------
 Nouveau comptage 2025-08 |      295  ← DOIT ÊTRE 295

TEST 2.5: Transactions orphelines
          test           | nb_orphelins 
-------------------------+--------------
 Transactions orphelines |            0  ← DOIT ÊTRE 0

TEST 3.1: Comparaison comptage 2025-08
 ancien_comptage | nouveau_comptage | reduction | reduction_pct 
-----------------+------------------+-----------+---------------
             531 |              295 |       236 |          44.4
```

### Validation:
```powershell
# Vérifier log
notepad tests_sql_log.txt
```

### ✅ Critères succès (TOUS BLOQUANTS):
- [ ] Nouveau comptage 2025-08 = **295**
- [ ] Orphelins = **0**
- [ ] Doublons employee_key = **0**
- [ ] Montants = 0 dans transactions = **0**
- [ ] Écart montants source/cible < **1$**
- [ ] Réduction ~**44.4%**

### ⚠️ SI UN TEST ÉCHOUE:
**STOP - Ne pas continuer Phase 4**

Analyser log, corriger problème, rollback niveau 1 si nécessaire.

---

## 🐍 PHASE 4: Patch Python (10 min)

### OÙ: PowerShell
### QUI: python

### Étape 4.1: Backup code actuel

```powershell
# Depuis PowerShell
cd C:\Users\SZERTYUIOPMLMM\Desktop\PayrollAnalyzer_Etape0

# Backup
cp providers\postgres_provider.py providers\postgres_provider.py.backup
```

### Étape 4.2: Appliquer patch

```powershell
# Copier fichier patché
cp migration\patched_postgres_provider.py providers\postgres_provider.py
```

### Étape 4.3: Vérifier import

```powershell
# Tester import
python -c "from providers.postgres_provider import PostgresProvider; print('✓ Import OK')"
```

### Sortie attendue:
```
✓ Import OK
```

### ✅ Critères succès:
- [ ] Backup créé
- [ ] Fichier patché copié
- [ ] Import sans erreur
- [ ] Aucune erreur syntaxe

### ⚠️ SI ERREUR IMPORT:
```powershell
# Restaurer backup
cp providers\postgres_provider.py.backup providers\postgres_provider.py

# Retester
python -c "from providers.postgres_provider import PostgresProvider; print('✓ Restauré')"
```

---

## 🧪 PHASE 5: Tests Python (5 min)

### OÙ: PowerShell
### QUI: python

```powershell
# Depuis PowerShell
cd C:\Users\SZERTYUIOPMLMM\Desktop\PayrollAnalyzer_Etape0

# Exécuter tests
python tests\test_kpi_regression.py
```

### Sortie attendue:

```
================================================================================
TESTS DE RÉGRESSION KPI - POST-MIGRATION RÉFÉRENTIEL EMPLOYÉS
================================================================================

TEST 1: Comptage employés 2025-08...
  ✓ SUCCÈS: nb_employes = 295

TEST 2: Masse salariale positive...
  ✓ SUCCÈS: masse_salariale = 972,107.87 $

TEST 3: Source de données...
  ✓ SUCCÈS: source = 'referentiel_employees'

TEST 4: Cohérence montants...
  ✓ SUCCÈS: net = masse + deductions (écart = 0.00 $)

TEST 5: Net moyen...
  ✓ SUCCÈS: net_moyen = 1,825.09 $

TEST 6: Formats période...
  ✓ Format mois (YYYY-MM): 295 employés
  ✓ Format date (YYYY-MM-DD): 295 employés
  ✓ Format année (YYYY): 295 employés

TEST 7: Vérification montants ≠ 0...
  ✓ SUCCÈS: Aucune transaction avec montant = 0

TEST 8: Affichage KPI complets...

  KPI Période 2025-08:
    Salaire net total  :   538,402.22 $
    Masse salariale    :   972,107.87 $
    Déductions         :  -433,705.65 $
    Employés uniques   :          295
    Net moyen          :     1,825.09 $
    Source             : referentiel_employees
    Période            : 2025-08

  ✓ SUCCÈS: Tous les champs présents et formatés

================================================================================
✅ TOUS LES TESTS RÉUSSIS (8/8)
================================================================================

Migration validée - Prêt pour déploiement!
```

### ✅ Critères succès:
- [ ] **8/8 tests PASS**
- [ ] nb_employes = **295**
- [ ] source = **'referentiel_employees'**
- [ ] Tous formats période OK
- [ ] Aucune transaction montant = 0

### ⚠️ SI UN TEST ÉCHOUE:
```powershell
# Debug manuel
python -c "
from providers.postgres_provider import PostgresProvider
p = PostgresProvider()
kpis = p.get_kpis('2025-08')
print('nb_employes:', kpis.get('nb_employes'))
print('source:', kpis.get('source'))
p.close()
"
```

**Analyser sortie, corriger, potentiellement rollback niveau 3**

---

## 🖥️ PHASE 6: Validation UI (10 min)

### OÙ: PowerShell
### QUI: python

### Étape 6.1: Lancer application

```powershell
# Depuis PowerShell
cd C:\Users\SZERTYUIOPMLMM\Desktop\PayrollAnalyzer_Etape0

# Lancer app
python payroll_app_qt_Version4.py
```

### Étape 6.2: Tests manuels dans l'UI

**1. Ouvrir dashboard**

**2. Sélectionner période 2025-08**
   - Utiliser sélecteur de période
   - Choisir "2025-08"

**3. Vérifier carte "Employés actifs"**
   - Valeur affichée: **295** ✅
   - (Anciennement: 531)

**4. Vérifier autres cartes KPI**
   - Masse salariale: ~972,107.87 $
   - Net moyen: ~1,825.09 $
   - Déductions: ~433,705.65 $

**5. Tester table de données**
   - Filtrer période 2025-08
   - Vérifier données affichées
   - Tester filtres (matricule, catégorie)

**6. Tester navigation**
   - Changer période (2025, 2025-08-28)
   - Vérifier mise à jour KPI

**7. Vérifier performance**
   - Temps réponse < 200 ms

### ✅ Critères succès:
- [ ] Carte "Employés actifs" = **295**
- [ ] Autres KPI cohérents
- [ ] Table de données fonctionne
- [ ] Filtres fonctionnent
- [ ] Navigation fluide
- [ ] Aucune erreur console
- [ ] Performance acceptable

### ⚠️ SI PROBLÈME UI:
**Vérifier logs console, rollback niveau 3 si nécessaire**

---

## 📦 PHASE 7: Archivage (optionnel, 5 min)

### OÙ: PowerShell → psql
### QUI: psql

### Option A: Renommer (recommandé pour transition)

```sql
-- Depuis psql
psql -U payroll_app -d payroll_db

-- Renommer
ALTER TABLE payroll.imported_payroll_master
RENAME TO imported_payroll_master_archive_20251016;

-- Commentaire
COMMENT ON TABLE payroll.imported_payroll_master_archive_20251016 IS
'Archive pré-migration référentiel - NE PLUS UTILISER';
```

### Option B: Garder tel quel (durant transition)
- Conserver `imported_payroll_master` inchangé
- Utiliser `v_imported_payroll_compat` pour compatibilité

### Option C: Supprimer (après validation 3-6 mois)

```sql
-- ATTENTION: Irréversible (après backup)
DROP TABLE payroll.imported_payroll_master CASCADE;
```

**Recommandation:** Option A pendant 3-6 mois, puis Option C

---

## 🔄 PROCÉDURES ROLLBACK

### Rollback Niveau 1: Données seulement (1 min)

```sql
-- Depuis psql
psql -U payroll_app -d payroll_db

BEGIN;
TRUNCATE TABLE payroll.payroll_transactions CASCADE;
TRUNCATE TABLE core.employees CASCADE;
TRUNCATE TABLE payroll.stg_imported_payroll;
DELETE FROM payroll.import_batches WHERE filename LIKE 'MIGRATION_%';
COMMIT;
```

**Effet:** Données migrées supprimées, structure conservée

---

### Rollback Niveau 2: Backup complet (10-15 min)

```powershell
# Depuis PowerShell
cd C:\Users\SZERTYUIOPMLMM\Desktop\PayrollAnalyzer_Etape0

# Localiser backup
Get-ChildItem backups\backup_pre_migration*.dump

# Restaurer (ATTENTION: écrase tout)
$env:PGPASSWORD = "PayrollApp2025!"
& "C:\Program Files\PostgreSQL\17\bin\pg_restore.exe" `
    -U payroll_app `
    -d payroll_db `
    --clean `
    --if-exists `
    backups\backup_pre_migration_YYYYMMDD_HHMMSS.dump
```

**Effet:** Base complètement restaurée (état pré-migration)

---

### Rollback Niveau 3: Code Python (2 min)

```powershell
# Depuis PowerShell
cd C:\Users\SZERTYUIOPMLMM\Desktop\PayrollAnalyzer_Etape0

# Restaurer fichier Python
cp providers\postgres_provider.py.backup providers\postgres_provider.py

# Redémarrer application
```

**Effet:** Code restauré, données conservées

---

### Rollback Niveau 4: Complet (15 min)

```powershell
# 1. Restaurer DB
pg_restore backups\backup_pre_migration.dump

# 2. Restaurer code
cp providers\postgres_provider.py.backup providers\postgres_provider.py

# 3. Redémarrer app
python payroll_app_qt_Version4.py
```

**Effet:** Retour complet état initial

---

## 📋 CHECKLIST FINALE

### Avant migration
- [ ] Backup complet créé
- [ ] Extensions activées (unaccent, pgcrypto)
- [ ] Données source documentées (7,735 lignes)
- [ ] Créneau réservé (60 min)
- [ ] Équipe disponible

### Pendant migration
- [ ] Phase 0: Backup ✅
- [ ] Phase 1: DDL sans erreur ✅
- [ ] Phase 2: Migration complétée ✅
  - [ ] Employés = 295 ✅
  - [ ] Transactions = 3,352 ✅
  - [ ] **Orphelins = 0** ✅
- [ ] Phase 3: Tests SQL verts ✅
- [ ] Phase 4: Patch Python appliqué ✅
- [ ] Phase 5: Tests Python 8/8 ✅
- [ ] Phase 6: UI validée ✅

### Après migration
- [ ] Carte "Employés actifs" = 295
- [ ] Performance acceptable (< 200 ms)
- [ ] Aucune erreur utilisateur
- [ ] Monitoring actif (24-48h)
- [ ] Logs propres
- [ ] Documentation à jour

---

## 🚨 RAPPELS IMPORTANTS

1. **⚠️ NE JAMAIS continuer si Phase échoue**
2. **⚠️ Backup OBLIGATOIRE (Phase 0)**
3. **⚠️ Orphelins = BLOQUANT (Phase 2/3)**
4. **⚠️ Tests Python = BLOQUANT (Phase 5)**
5. **⚠️ Rollback disponible à tout moment**

---

**PRÊT À EXÉCUTER** ✅

Durée totale: **45-60 minutes**

