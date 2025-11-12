# CONTEXT.md - PayrollAnalyzer Application

## 📋 Vue d'ensemble

Application de gestion de paie développée avec:
- **Backend**: Python 3.10+ (PyQt6 + FastAPI)
- **Base de données**: PostgreSQL 17
- **Frontend**: Tabler UI (HTML/CSS/JavaScript vanilla)
- **Architecture**: Dimension/Fait (Data Warehouse)

---

## 🏗️ Architecture générale

### Stack technique

- **Python**: 3.10+
- **PyQt6**: Interface desktop avec QWebEngineView
- **FastAPI**: API REST (optionnel, peut tourner en arrière-plan)
- **PostgreSQL**: Base de données principale
- **Tabler**: Framework UI basé sur Bootstrap
- **QWebChannel**: Communication bidirectionnelle PyQt6 ↔ JavaScript

### Architecture de données

**Modèle Dimension/Fait (Data Warehouse):**

- **Dimension**: `core.employees` (référentiel unique des employés)
  - Unicité garantie par `matricule` (index unique)
  - Clé technique: `employee_id` (integer)
  - Clé métier: `employee_key` (hash de matricule + nom + prénom)
  
- **Fait**: `payroll.payroll_transactions` (transactions de paie)
  - Partitionnée par année (`payroll_transactions_2024`, `payroll_transactions_2025`, etc.)
  - Clé étrangère: `employee_id` → `core.employees`
  - Montants en centimes (`amount_cents`)

- **Staging**: `paie.stg_paie_transactions` (données brutes importées)
  - Contient toutes les colonnes du fichier Excel
  - Jointure avec `payroll_transactions` via `(source_file, source_row_number)`

- **Référence**: `ref.parameters` (paramètres globaux)
  - Taux, seuils, etc.

---

## 🗄️ Structure de la base de données

### Schémas principaux

1. **`core`**: Référentiel employés
   - `employees`: Table principale des employés
   - `employee_job_history`: Historique des postes
   - `job_categories`: Catégories d'emploi
   - `job_codes`: Codes d'emploi
   - `pay_codes`: Codes de paie

2. **`payroll`**: Données de paie
   - `payroll_transactions`: Transactions de paie (partitionnées)
   - `imported_payroll_master`: Données brutes importées depuis Excel
   - `pay_periods`: Périodes de paie
   - `import_batches`: Historique des imports
   - `kpi_snapshot`: Snapshots des KPI

3. **`paie`**: Vues et calculs KPI
   - `stg_paie_transactions`: Staging avec données Excel complètes
   - `v_kpi_mois`: KPI consolidés par mois/jour
   - `v_kpi_par_employe_mois`: KPI par employé et période
   - `v_employe_profil`: Profil dominant par employé (catégorie/titre)
   - `v_employes_groupes`: Groupements par catégorie/titre

4. **`ref`**: Référentiels et paramètres
   - `parameters`: Paramètres globaux (taux, seuils, etc.)

### Tables principales

**core.employees**
- `employee_id` (integer, PK)
- `matricule` (varchar, UNIQUE)
- `nom`, `prenom` (varchar)
- `statut` (varchar)
- `created_at`, `updated_at` (timestamptz)

**payroll.payroll_transactions**
- `transaction_id` (uuid, PK)
- `employee_id` (integer, FK → core.employees)
- `pay_date` (date)
- `amount_cents` (bigint) - Montant en centimes
- `source_file` (text)
- `source_row_no` (integer)

**paie.stg_paie_transactions**
- Toutes les colonnes du fichier Excel
- `source_file` (text)
- `source_row_number` (integer)
- `part_employeur_cents` (bigint) - Part employeur en centimes
- `categorie_emploi`, `titre_emploi` (text)

---

## 🧮 Règles de calcul

### Calculs dans les vues KPI PostgreSQL

Tous les calculs sont centralisés dans PostgreSQL pour garantir la cohérence.

#### 1. Gains bruts (gains_brut)

```sql
COALESCE(SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END), 0) / 100.0
```

- Somme de tous les montants positifs
- Conversion centimes → dollars (division par 100)

#### 2. Déductions (deductions_net)

```sql
COALESCE(SUM(CASE WHEN amount_cents < 0 THEN amount_cents ELSE 0 END), 0) / 100.0
```

- Somme de tous les montants négatifs
- Conversion centimes → dollars

#### 3. Net à payer (net_a_payer)

```sql
COALESCE(SUM(amount_cents), 0) / 100.0
```

- Somme algébrique de tous les montants
- Conversion centimes → dollars

#### 4. Part employeur (part_employeur)

```sql
COALESCE(SUM(COALESCE(s.part_employeur_cents, 0)), 0) / 100.0
```

- **Lecture directe** depuis `paie.stg_paie_transactions.part_employeur_cents`
- **Ne pas calculer** avec un taux fixe
- Les données Excel contiennent déjà la part employeur réelle
- Conversion centimes → dollars

#### 5. Coût total (cout_total)

```sql
(COALESCE(SUM(t.amount_cents), 0) + COALESCE(SUM(COALESCE(s.part_employeur_cents, 0)), 0)) / 100.0
```

- `net_a_payer + part_employeur`
- Coût réel pour l'employeur

#### 6. Taux part employeur (taux_part_employeur_pct) - INDICATIF

```sql
CASE 
    WHEN SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END) > 0 
    THEN (COALESCE(SUM(COALESCE(s.part_employeur_cents, 0)), 0)::NUMERIC / 
          SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END)) * 100.0
    ELSE NULL
END
```

- **Taux indicatif uniquement** = `part_employeur / gains_bruts * 100`
- L'application ne détermine pas le taux, elle le calcule à titre informatif
- Le taux réel varie selon les périodes et les employés

#### 7. Cash out total (cash_out_total)

```sql
COALESCE(SUM(CASE WHEN amount_cents < 0 THEN ABS(amount_cents) ELSE 0 END), 0) / 100.0
```

- Somme des déductions en valeur absolue
- Conversion centimes → dollars

### Unicité matricule

**Règle métier**: Un matricule = un seul employé

- Index unique sur `core.employees(matricule)`
- Contrôle lors de l'import/ajout d'employé
- Si conflit détecté (même matricule, nom différent):
  - Message d'erreur avec redirection vers page de modification
  - Tolérance de 4 lettres de différence maximum
  - L'utilisateur doit choisir le nom exact à enregistrer

---

## 📊 Flux de données

### Import Excel → Base de données

1. **Fichier Excel** → `services/import_service_complete.py`
   - Parsing avec pandas
   - Mapping des colonnes (configurable)
   - Validation des données

2. **Staging** → `paie.stg_paie_transactions`
   - Données brutes avec toutes les colonnes Excel
   - `source_file`: Nom du fichier
   - `source_row_number`: Numéro de ligne dans Excel

3. **Référentiel** → `core.employees`
   - Déduplication automatique par `matricule`
   - Clé technique: `employee_id`
   - Clé métier: `employee_key` (hash normalisé)

4. **Transactions** → `payroll.payroll_transactions`
   - Jointure avec `core.employees` via `employee_id`
   - Montants convertis en centimes (`amount_cents`)
   - Partitionnement par année (`pay_date`)

### Calculs KPI

Les vues KPI (`paie.v_kpi_mois`, `paie.v_kpi_par_employe_mois`) sont calculées à la volée depuis `payroll_transactions`:

- Jointure avec `paie.stg_paie_transactions` pour récupérer:
  - `part_employeur_cents`
  - `categorie_emploi`, `titre_emploi`
  - `nom_prenom`

- Agrégation par période (mois/jour) et/ou employé

---

## 🖥️ Interface utilisateur (Tabler)

### Pages principales

1. **`index.html`**: Dashboard principal
   - Cartes KPI (gains bruts, net, coût total, etc.)
   - Graphiques (barres, lignes, camemberts)
   - Sélection de période

2. **`employees.html`**: Gestion des employés
   - Liste des employés avec filtres (période, nom, catégorie, titre)
   - Colonnes: Matricule, Nom, Prénom, Catégorie, Titre, Statut
   - KPIs par employé
   - Groupements par catégorie/titre

3. **`periods.html`**: Gestion des périodes
   - Liste des périodes de paie
   - Statut (ouverte/fermée)
   - Nombre de transactions par période

### Communication PyQt6 ↔ Tabler

**Méthode**: QWebChannel (`QtWebChannel`)

**Code Python** (`payroll_app_qt_Version4.py`):
```python
class AppBridge(QObject):
    @pyqtSlot(str, result=str)
    def execute_sql(self, sql: str) -> str:
        # Exécute SQL et retourne JSON
        return json.dumps(results)
```

**Code JavaScript** (`web/tabler/js/app_bridge.js`):
```javascript
window.appBridge.execute_sql(sql).then(result => {
    const data = JSON.parse(result);
    // Utiliser les données
});
```

**Utilisation dans les pages**:
- `employees.js`: Charge les données via `AppBridge.execute_sql()`
- Formatage FR-CA: `formatCurrencyFr()`, `formatNumberFr()`

### Formatage FR-CA

- Nombres: `1 234,56` (espace pour milliers, virgule pour décimales)
- Devises: `1 234,56 $` (symbole $ après)
- Utilise `Intl.NumberFormat('fr-CA')`

---

## 🔌 API FastAPI

### Endpoints principaux

**Base URL**: `http://127.0.0.1:8001`

#### KPI
- `GET /kpi/periods?year=2025`: Liste des périodes
- `GET /kpi/kpis?period=2025-08`: KPI pour une période

#### Employés
- `GET /employees/list?period_id=...&page=1&page_size=50`: Liste paginée
- `GET /employees/grouping`: Groupements par catégorie/titre
- `GET /employees/check-conflict?matricule=...`: Vérification conflit matricule

### Provider

**`PostgresProvider`** (`providers/postgres_provider.py`):
- Pool de connexions psycopg3
- Méthodes: `get_kpis()`, `list_employees()`, `get_periods()`
- Fallback sur `payroll_transactions` si `pay_periods` vide

---

## ⚙️ Configuration

### Variables d'environnement

**`.env`** (à créer si absent):
```
PAYROLL_DSN=postgresql://payroll_app:PayrollApp2025!@localhost:5432/payroll_db
APP_ENV=development
```

**`.pgpass`** (migration/pgpass.conf):
```
localhost:5432:payroll_db:postgres:aq456*456
```

### Configuration application

**`config/settings.json`**:
- Mapping des colonnes Excel
- Règles de calcul net
- Formats de date

### DSN PostgreSQL

**Format**: `postgresql://user:password@host:port/database`

**Développement** (par défaut):
```
postgresql://payroll_app:PayrollApp2025!@localhost:5432/payroll_db
```

**Superuser** (pour migrations):
```
postgresql://postgres:aq456*456@localhost:5432/payroll_db
```

---

## 🚀 Démarrage de l'application

### Option 1: Application PyQt6 seule

```bash
python payroll_app_qt_Version4.py
```

Ou via batch:
```bash
DEMARRER.bat
```

### Option 2: Avec API FastAPI (optionnel)

**Terminal 1**:
```bash
python payroll_app_qt_Version4.py
```

**Terminal 2**:
```bash
python -m api.main
# ou
DEMARRER_API.bat
```

L'API tourne sur `http://127.0.0.1:8001`

### Prérequis

- Python 3.10+
- PostgreSQL 17
- Packages Python: `PyQt6`, `psycopg[binary]`, `fastapi`, `uvicorn`, `pandas`, etc.

---

## 📁 Structure des fichiers

### Backend Python

- `payroll_app_qt_Version4.py`: Application principale PyQt6
- `api/`: API FastAPI
- `providers/`: Data providers (PostgreSQL)
- `services/`: Services métier (import, ETL)
- `logic/`: Logique métier (KPI, métriques)
- `ui/`: Composants UI PyQt6
- `config/`: Configuration
- `agent/`: Agent IA (optionnel)

### Frontend Tabler

- `web/tabler/`: Interface web complète
  - `index.html`, `employees.html`, `periods.html`: Pages principales
  - `js/`: JavaScript (API client, helpers, bridge)
  - `css/`: Styles personnalisés

### Migrations SQL

- `migration/`: Toutes les migrations SQL
  - `014_unicite_matricule_et_vues_kpi.sql`: Unicité matricule + vues KPI
  - `015_employe_profil_et_groupes.sql`: Profils et groupements
  - `017_centralisation_parametres.sql`: Paramètres centralisés
  - `018_correction_part_employeur_reelle.sql`: Correction part employeur
  - `019_correction_jointure_part_employeur.sql`: Correction jointure

### Base de données

- `database/schema_dump.sql`: Structure complète (DDL)
- `database/data_dump.sql`: Données complètes (INSERT)

---

## 🔐 Sécurité

### Mots de passe inclus

⚠️ **ATTENTION**: Ce ZIP contient les mots de passe réels:
- PostgreSQL: `PayrollApp2025!` (payroll_app)
- PostgreSQL: `aq456*456` (postgres superuser)

Ne pas partager ce ZIP publiquement sans anonymiser les mots de passe.

### Rôles PostgreSQL

- **`payroll_app`**: Utilisateur application (lecture/écriture)
- **`postgres`**: Superuser (pour migrations)

---

## 📝 Notes importantes

1. **Calculs centralisés**: Tous les calculs sont dans PostgreSQL (vues KPI)
2. **Part employeur**: Lue depuis les données Excel, pas calculée
3. **Taux indicatif**: Calculé à titre informatif uniquement
4. **Unicité matricule**: Garantie par index unique + contrôle applicatif
5. **Formatage FR-CA**: Nombres et devises formatés selon standards français-canadiens
6. **Communication**: QWebChannel pour PyQt6 ↔ JavaScript
7. **Fallback**: Si `pay_periods` vide, utiliser `payroll_transactions` directement

---

## 🐛 Dépannage

### Application ne démarre pas
- Vérifier PostgreSQL démarré
- Vérifier DSN dans `.env` ou variable d'environnement
- Vérifier PyQt6 installé: `pip install PyQt6`

### Données non affichées
- Vérifier connexion PostgreSQL
- Vérifier que les migrations SQL sont appliquées
- Vérifier que `payroll_transactions` contient des données

### Filtres vides
- Vérifier que `paie.stg_paie_transactions` contient `categorie_emploi` et `titre_emploi`
- Vérifier que les vues KPI sont à jour

---

**Date de génération**: 2025-11-05 14:32:11
**Version application**: 2.0.1
**PostgreSQL**: 17
**Python**: 3.10+
