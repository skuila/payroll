# Standardisation des Connexions PostgreSQL

**Date:** 2025-11-11  
**Statut:** ✅ En cours d'implémentation  
**Objectif:** Une seule source de vérité pour toutes les connexions PostgreSQL

---

## 🎯 Objectif

**AUCUNE connexion directe ne doit subsister en dehors du module standard `config/connection_standard.py`.**

Interdiction globale de:
- `psycopg.connect()` (sauf liste blanche)
- `create_engine()` (sauf liste blanche)
- `os.getenv('PAYROLL_*')` pour la DB (sauf liste blanche)

---

## 📋 Architecture Standardisée

### Module Standard: `config/connection_standard.py`

**API Publique:**

```python
from config.connection_standard import (
    get_dsn,              # Obtenir le DSN validé
    get_connection_pool,  # Obtenir le pool singleton
    get_connection,       # Obtenir une connexion du pool
    run_select,           # Exécuter un SELECT
    run_sql,              # Exécuter INSERT/UPDATE/DELETE
    test_connection,      # Tester la connexion
)
```

### Configuration

**Timeouts (overridables par env):**
- `PG_STATEMENT_TIMEOUT_MS=8000` (8 secondes)
- `PG_LOCK_TIMEOUT_MS=2000` (2 secondes)
- `PG_IDLE_IN_TX_TIMEOUT_MS=5000` (5 secondes)

**Search Path:**
```sql
payroll, core, reference, security, public
```

**Timezone:**
```sql
America/Toronto
```

**Connect Timeout:**
```
10 secondes (ajouté automatiquement au DSN)
```

---

## 🔒 Liste Blanche

**Seuls ces fichiers peuvent avoir des connexions directes:**

1. `app/config/connection_standard.py` - Module standard
2. `app/services/data_repo.py` - Pool bas niveau
3. `app/providers/postgres_provider.py` - Provider (doit déléguer à connection_standard)
4. `app/launch_payroll.py` - Lanceur (tests uniquement)

**Tous les autres fichiers DOIVENT utiliser l'API standardisée.**

---

## 📝 Guide de Migration

### Avant (❌ Interdit)

```python
import psycopg
import os

# ❌ Construction DSN manuelle
dsn = f"postgresql://{os.getenv('PAYROLL_DB_USER')}:{os.getenv('PAYROLL_DB_PASSWORD')}@..."

# ❌ Connexion directe
conn = psycopg.connect(dsn, connect_timeout=5)
cur = conn.cursor()
cur.execute("SELECT * FROM employees")
results = cur.fetchall()
conn.close()
```

### Après (✅ Correct)

```python
from config.connection_standard import get_connection, run_select

# ✅ Méthode 1: Utiliser run_select (simple)
results = run_select("SELECT * FROM employees")

# ✅ Méthode 2: Utiliser get_connection (avancé)
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM employees WHERE status = %s", ('actif',))
        results = cur.fetchall()
```

### Exemples par Cas d'Usage

#### 1. SELECT Simple

```python
# ❌ Avant
conn = psycopg.connect(DSN)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM employees")
count = cur.fetchone()[0]
conn.close()

# ✅ Après
from config.connection_standard import run_select
result = run_select("SELECT COUNT(*) FROM employees")
count = result[0][0]
```

#### 2. INSERT/UPDATE/DELETE

```python
# ❌ Avant
conn = psycopg.connect(DSN)
cur = conn.cursor()
cur.execute("UPDATE employees SET status = %s WHERE id = %s", ('inactif', 123))
conn.commit()
conn.close()

# ✅ Après
from config.connection_standard import run_sql
run_sql("UPDATE employees SET status = %s WHERE id = %s", {'status': 'inactif', 'id': 123})
```

#### 3. Transaction Complexe

```python
# ❌ Avant
conn = psycopg.connect(DSN)
try:
    cur = conn.cursor()
    cur.execute("INSERT INTO ...")
    cur.execute("UPDATE ...")
    conn.commit()
except:
    conn.rollback()
    raise
finally:
    conn.close()

# ✅ Après
from config.connection_standard import get_connection
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO ...")
        cur.execute("UPDATE ...")
    conn.commit()  # Auto-rollback si exception
```

#### 4. SQLAlchemy (create_engine)

```python
# ❌ Avant
from sqlalchemy import create_engine
engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text("SELECT ..."))

# ✅ Après
from config.connection_standard import run_select
result = run_select("SELECT ...")
```

#### 5. Lecture DSN

```python
# ❌ Avant
dsn = os.getenv('PAYROLL_DSN') or os.getenv('DATABASE_URL')

# ✅ Après
from config.connection_standard import get_dsn
dsn = get_dsn()
```

---

## 🛡️ Protection Anti-Régression

### Script de Validation

**Fichier:** `app/scripts/forbid_direct_db_connect.py`

**Usage:**
```bash
python scripts/forbid_direct_db_connect.py
```

Le script scanne tout le dépôt (hors `.git`, `.venv`, `node_modules`, `legacy_non_standard`) et échoue si des connexions non standard sont détectées.

---

## 🧰 Scripts standardisés disponibles

Les utilitaires compatibles avec l’API standard sont regroupés dans `app/scripts/standardized/` :

| Script | Description | Exemple d’utilisation |
| --- | --- | --- |
| `check_connection.py` | Test rapide de la connexion PostgreSQL | `python app/scripts/standardized/check_connection.py` |
| `db_overview.py` | Génère un JSON listant tables et volumes principaux | `python app/scripts/standardized/db_overview.py out/db_overview.json` |
| `export_employees.py` | Exporte `core.employees` en CSV | `python app/scripts/standardized/export_employees.py out/employees.csv --limit 100` |

Tout nouveau script doit utiliser `config.connection_standard` et vivre dans ce répertoire.

---

## 🗃️ Zone legacy

Les anciens scripts (connexions manuelles, tests obsolètes) sont archivés dans `archive/legacy_non_standard/`. Ils sont conservés à titre documentaire uniquement et ignorés par le verrou de connexion. Ne pas les utiliser en production.

## 📊 État Actuel

### Statistiques (2025-11-11)

**Avant standardisation:**
- 57 fichiers avec violations
- 259 occurrences de connexions directes
- 52 `psycopg.connect()`
- 6 `create_engine()`
- 155 lectures `os.getenv('PAYROLL_*')`

**Après standardisation:**
- ✅ Module `connection_standard.py` créé
- ✅ Script anti-régression créé
- ✅ CI/CD configuré
- ⏳ Migration en cours

### Fichiers Refactorisés

- ✅ `connect_check.py` - Refactorisé
- ⏳ 56 fichiers restants

---

## 🔍 Vérification

### Test Manuel

```bash
cd app

# 1. Tester le module standard
python config/connection_standard.py

# 2. Vérifier les violations
python scripts/forbid_direct_db_connect.py

# 3. Tester l'application
LANCER_APP.bat
```

### Commandes Utiles

```bash
# Trouver tous les psycopg.connect()
grep -r "psycopg\.connect(" app/ --include="*.py"

# Trouver tous les create_engine()
grep -r "create_engine(" app/ --include="*.py"

# Trouver toutes les lectures d'env
grep -r "os\.getenv.*PAYROLL" app/ --include="*.py"
```

---

## 📚 Documentation Associée

- **Guide principal:** `guides/GUIDE_CONNEXION.md`
- **Architecture:** `guides/CONNEXION_STANDARDISEE.md`
- **Ce document:** `guides/STANDARDISATION_CONNEXIONS.md`

---

## ✅ Checklist de Migration

### Pour Chaque Fichier

- [ ] Remplacer `psycopg.connect()` par `get_connection()`
- [ ] Remplacer `create_engine()` par `get_connection_pool()`
- [ ] Remplacer `os.getenv('PAYROLL_*')` par `get_dsn()`
- [ ] Ajouter `from config.connection_standard import ...`
- [ ] Tester le fichier modifié
- [ ] Vérifier avec `forbid_direct_db_connect.py`

### Pour le Projet

- [x] Créer `config/connection_standard.py`
- [x] Créer `scripts/forbid_direct_db_connect.py`
- [x] Créer `.github/workflows/validate-db-standard.yml`
- [ ] Refactoriser tous les fichiers (57)
- [ ] Tester l'application complète
- [ ] Mettre à jour la documentation
- [ ] Former l'équipe

---

## 🚨 Règles Strictes

### ❌ INTERDIT

1. `psycopg.connect()` en dehors de la liste blanche
2. `create_engine()` en dehors de la liste blanche
3. `os.getenv('PAYROLL_DSN')` en dehors de la liste blanche
4. `os.getenv('DATABASE_URL')` en dehors de la liste blanche
5. `os.getenv('PAYROLL_DB_*')` en dehors de la liste blanche
6. Construction manuelle de DSN
7. Pools de connexions multiples

### ✅ OBLIGATOIRE

1. Utiliser `from config.connection_standard import ...`
2. Utiliser `get_connection_pool()` pour le pool singleton
3. Utiliser `get_connection()` pour les connexions
4. Utiliser `run_select()` / `run_sql()` pour les requêtes simples
5. Passer tous les tests anti-régression
6. Documenter les exceptions (si justifiées)

---

## 💡 Avantages

### Avant (Problèmes)

- ❌ 57 fichiers avec connexions différentes
- ❌ DSN construits manuellement partout
- ❌ Timeouts incohérents
- ❌ Pas de pool de connexions unifié
- ❌ Search path non standardisé
- ❌ Timezone non fixée
- ❌ Difficile à maintenir
- ❌ Risques de sécurité (mots de passe en dur)

### Après (Solutions)

- ✅ **UN SEUL** module de connexion
- ✅ DSN validé automatiquement
- ✅ Timeouts configurables et cohérents
- ✅ Pool singleton optimisé
- ✅ Search path standardisé
- ✅ Timezone fixée (America/Toronto)
- ✅ Facile à maintenir
- ✅ Sécurisé (mots de passe masqués dans logs)
- ✅ Protection anti-régression (CI)

---

## 📞 Support

**En cas de problème:**

1. Consulter `guides/GUIDE_CONNEXION.md`
2. Consulter `guides/CONNEXION_STANDARDISEE.md`
3. Exécuter `python scripts/forbid_direct_db_connect.py`
4. Vérifier la liste blanche
5. Contacter l'équipe

---

**Version:** 1.0  
**Auteur:** Système de standardisation  
**Statut:** ✅ En cours d'implémentation

