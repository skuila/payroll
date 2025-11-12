# Guide d'Exécution - Migration Référentiel Employés

**Version:** 1.0  
**Date:** 16 octobre 2025  
**PostgreSQL:** 17  
**Python:** 3.10+

---

## 📋 Pré-requis

### Vérifications
- [x] PostgreSQL 17 installé et accessible
- [x] Extension `unaccent` disponible
- [x] Base `payroll_db` avec schémas `payroll`, `core`, `reference`
- [x] Table source `payroll.imported_payroll_master` remplie
- [x] Python 3.10+ avec psycopg3
- [x] Accès utilisateur `payroll_app` avec permissions suffisantes

### Commandes de vérification

```bash
# Vérifier PostgreSQL
psql --version  # Attendu: 17.x

# Vérifier base et extension
psql -U payroll_app -d payroll_db -c "SELECT version();"
psql -U payroll_app -d payroll_db -c "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'unaccent');"

# Vérifier Python
python --version  # Attendu: 3.10+
python -c "import psycopg; print(f'psycopg {psycopg.__version__}')"
```

---

## 🗂️ Fichiers livrés

```
migration/
├── 01_ddl_referentiel.sql          # DDL tables, index, fonctions
├── 02_migrate_to_referentiel.sql   # Script de migration
├── 03_tests_validation.sql         # Tests SQL avant/après
├── 04_patch_python.md              # Instructions patch Python
├── test_kpi_regression.py          # Tests Python
└── README_EXECUTION.md             # Ce fichier
```

---

## 🚀 Procédure d'exécution

### **PHASE 0: Backup (OBLIGATOIRE)**

```bash
# Créer backup complet
pg_dump -h localhost -U payroll_app -d payroll_db \
        -F custom -f backup_pre_migration_$(date +%Y%m%d_%H%M%S).dump

# Vérifier backup
pg_restore --list backup_pre_migration_*.dump | head -20

# Tester restauration (sur base test si disponible)
```

**⚠️ NE PAS CONTINUER SANS BACKUP VALIDE**

---

### **PHASE 1: Tests pré-migration**

Exécuter les tests SQL pour documenter l'état actuel :

```bash
cd migration

# Exécuter tests pré-migration (partie 1 uniquement)
psql -U payroll_app -d payroll_db -f 03_tests_validation.sql 2>&1 | tee tests_pre_migration.log

# Vérifier résultats attendus
grep "TEST 1.4" tests_pre_migration.log
# Attendu: 531 employés (ancien comptage 2025-08)
```

**Valider avant de continuer:**
- [ ] Ancien comptage 2025-08 = 531 employés
- [ ] Total lignes source documenté
- [ ] Montant total source documenté

---

### **PHASE 2: Création structures**

Créer toutes les tables, index, fonctions :

```bash
# Exécuter DDL
psql -U payroll_app -d payroll_db -f 01_ddl_referentiel.sql 2>&1 | tee ddl_execution.log

# Vérifier succès
tail -20 ddl_execution.log
# Attendu: "✓ DDL exécuté avec succès"

# Vérifier tables créées
psql -U payroll_app -d payroll_db -c "\dt core.employees"
psql -U payroll_app -d payroll_db -c "\dt payroll.payroll_transactions*"
```

**Valider:**
- [ ] `core.employees` créée
- [ ] `payroll.payroll_transactions` créée avec partitions 2024-2026
- [ ] `payroll.import_batches` créée
- [ ] `payroll.stg_imported_payroll` créée
- [ ] Fonction `core.compute_employee_key()` existe

---

### **PHASE 3: Migration données**

**⚠️ CETTE ÉTAPE PEUT PRENDRE 5-15 MINUTES SELON VOLUME**

```bash
# Exécuter migration
psql -U payroll_app -d payroll_db -f 02_migrate_to_referentiel.sql 2>&1 | tee migration_execution.log

# Surveiller progression
tail -f migration_execution.log

# Vérifier succès
grep "MIGRATION TERMINÉE AVEC SUCCÈS" migration_execution.log
```

**Attendus dans les logs:**
```
Batch ID         : 1
Staging          : 3352 lignes (exemple)
Employés         : 295 uniques insérés
Transactions     : 3352 insérées
Orphelins        : 0
Montant total    : 538402.22 $
```

**Valider:**
- [ ] Batch complété (status = 'completed')
- [ ] Employés insérés (attendu: 295 pour 2025-08)
- [ ] Transactions insérées (attendu: 3352 pour 2025-08)
- [ ] **Orphelins = 0** (CRITIQUE)
- [ ] Montant total cohérent avec source

---

### **PHASE 4: Tests post-migration**

Exécuter tous les tests de validation :

```bash
# Exécuter tests SQL complets
psql -U payroll_app -d payroll_db -f 03_tests_validation.sql 2>&1 | tee tests_post_migration.log

# Vérifier résultats clés
grep "TEST 2.3" tests_post_migration.log  # Nouveau comptage 2025-08
grep "TEST 2.5" tests_post_migration.log  # Orphelins
grep "TEST 3.1" tests_post_migration.log  # Comparaison
```

**Attendus:**
```
TEST 2.3: Nouveau comptage 2025-08
 test              | resultat
-------------------+----------
 Nouveau comptage  |      295

TEST 2.5: Transactions orphelines
 test                    | nb_orphelins
-------------------------+--------------
 Transactions orphelines |            0

TEST 3.1: Comparaison
 ancien_comptage | nouveau_comptage | reduction | reduction_pct
-----------------+------------------+-----------+---------------
             531 |              295 |       236 |          44.4
```

**Valider:**
- [ ] Nouveau comptage 2025-08 = 295
- [ ] Orphelins = 0
- [ ] Doublons employee_key = 0
- [ ] Montants = 0 dans transactions = 0
- [ ] Écart montants < 1$
- [ ] Réduction ~44.4%

---

### **PHASE 5: Patch Python**

Appliquer les modifications au code Python :

```bash
# Backup fichiers Python
cp services/data_repo.py services/data_repo.py.backup
cp providers/postgres_provider.py providers/postgres_provider.py.backup

# Appliquer patches manuellement (voir 04_patch_python.md)
# OU utiliser éditeur de texte pour modifier :

# 1. services/data_repo.py ligne 159:
#    Remplacer: if sql.strip().upper().startswith('SELECT'):
#    Par:       if sql.strip().upper().startswith(('SELECT', 'WITH')):

# 2. providers/postgres_provider.py:
#    Remplacer méthode get_kpis() complète (voir 04_patch_python.md)
#    Remplacer SQL dans get_table() (voir 04_patch_python.md)
```

**Vérifier imports:**
```bash
python -c "from providers.postgres_provider import PostgresProvider; print('✓ Import OK')"
```

---

### **PHASE 6: Tests Python**

Tester les KPI via l'API Python :

```bash
# Exécuter tests de régression
cd migration
python test_kpi_regression.py 2>&1 | tee tests_python.log

# Vérifier succès
grep "TOUS LES TESTS RÉUSSIS" tests_python.log
```

**Attendus:**
```
TEST 1: Comptage employés 2025-08...
  ✓ nb_employes = 295 (correct)

TEST 2: Masse salariale positive...
  ✓ masse_salariale = 972,107.87 $ (correct)

...

✅ TOUS LES TESTS RÉUSSIS
```

**Valider:**
- [ ] Tous les tests Python passent
- [ ] KPI source = 'referentiel_employees'
- [ ] Formats période (mois/date/année) fonctionnent

---

### **PHASE 7: Tests UI (manuel)**

Tester l'application complète :

```bash
# Démarrer application
python payroll_app_qt_Version4.py

# Tester dans l'UI:
# 1. Ouvrir dashboard Tabler
# 2. Sélectionner période 2025-08
# 3. Vérifier carte "Employés actifs" affiche 295
# 4. Vérifier masse salariale cohérente
# 5. Tester table de données (filtres)
# 6. Tester navigation entre périodes
```

**Valider:**
- [ ] Carte "Employés actifs" = 295
- [ ] Cartes KPI affichent valeurs cohérentes
- [ ] Table de données fonctionne
- [ ] Filtres (période, matricule) fonctionnent
- [ ] Pas d'erreurs console/logs

---

## 🔄 Rollback (si problème)

### Option 1: Rollback tables uniquement

```sql
BEGIN;

-- Vider tables cibles
TRUNCATE TABLE payroll.payroll_transactions CASCADE;
TRUNCATE TABLE core.employees CASCADE;
TRUNCATE TABLE payroll.stg_imported_payroll CASCADE;
DELETE FROM payroll.import_batches WHERE filename LIKE 'MIGRATION_INITIALE%';

-- Supprimer tables
DROP TABLE IF EXISTS payroll.payroll_transactions CASCADE;
DROP TABLE IF EXISTS core.employees CASCADE;
DROP TABLE IF EXISTS payroll.stg_imported_payroll CASCADE;
DROP TABLE IF EXISTS payroll.import_batches CASCADE;
DROP SCHEMA IF EXISTS core CASCADE;

COMMIT;
```

### Option 2: Restauration complète

```bash
# Arrêter application
# Restaurer backup
pg_restore -h localhost -U payroll_app -d payroll_db \
           --clean --if-exists \
           backup_pre_migration_YYYYMMDD_HHMMSS.dump

# Redémarrer application
```

### Option 3: Rollback code Python

```bash
# Restaurer fichiers Python
cp services/data_repo.py.backup services/data_repo.py
cp providers/postgres_provider.py.backup providers/postgres_provider.py

# Redémarrer application
```

---

## 📊 Checklist finale

### Migration réussie si:
- [x] DDL exécuté sans erreur
- [x] Migration complétée (logs OK)
- [x] Tests SQL: tous verts
  - [x] Nouveau comptage 2025-08 = 295
  - [x] Orphelins = 0
  - [x] Écart montants < 1$
- [x] Tests Python: tous passés
- [x] UI fonctionne correctement
- [x] Carte "Employés actifs" = 295
- [x] Performances acceptables

### Post-migration
- [ ] Archiver ancienne table (après validation stabilité)
  ```sql
  ALTER TABLE payroll.imported_payroll_master 
  RENAME TO imported_payroll_master_ARCHIVE_20251016;
  ```
- [ ] Documenter changements
- [ ] Former utilisateurs si nécessaire
- [ ] Monitoring 1-2 jours

---

## 🆘 En cas de problème

### Orphelins détectés
```sql
-- Identifier orphelins
SELECT s.*, e.employee_id
FROM payroll.stg_imported_payroll s
LEFT JOIN core.employees e ON s.employee_key = e.employee_key
WHERE e.employee_id IS NULL
LIMIT 10;

-- Analyser employee_key problématiques
SELECT employee_key, COUNT(*)
FROM payroll.stg_imported_payroll
WHERE employee_key NOT IN (SELECT employee_key FROM core.employees)
GROUP BY employee_key;
```

### Écart montants
```sql
-- Comparer en détail
SELECT 
    'Source' AS origine,
    ROUND(SUM(COALESCE("montant ", 0)), 2) AS total
FROM payroll.imported_payroll_master
WHERE COALESCE("montant ", 0) <> 0

UNION ALL

SELECT 
    'Cible',
    ROUND(SUM(amount_cents) / 100.0, 2)
FROM payroll.payroll_transactions;
```

### Performance lente
```sql
-- Vérifier statistiques
ANALYZE VERBOSE core.employees;
ANALYZE VERBOSE payroll.payroll_transactions;

-- Vérifier index utilisés
EXPLAIN ANALYZE
SELECT COUNT(DISTINCT employee_id)
FROM payroll.payroll_transactions
WHERE TO_CHAR(pay_date, 'YYYY-MM') = '2025-08';
```

---

## 📞 Support

Pour questions ou problèmes:
1. Consulter logs: `migration_execution.log`, `tests_post_migration.log`
2. Vérifier section "En cas de problème" ci-dessus
3. Contacter équipe technique avec logs

---

**SUCCÈS DE LA MIGRATION ✅**

Après validation complète, vous avez migré avec succès vers une architecture dimension/fait avec:
- Référentiel employés dédupliqué (295 uniques)
- Faits de paie normalisés (3,352 transactions)
- Clé technique stable (`employee_id`)
- Performance optimisée (partitionnement, index)
- Traçabilité complète

