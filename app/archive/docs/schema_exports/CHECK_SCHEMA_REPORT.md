# 📊 RAPPORT SCHÉMA POSTGRESQL

## 📅 Informations générales

**Date extraction** : 2025-10-17T17:38:28.465943

**Serveur** : ::1:5432

**Base de données** : payroll_db

**Utilisateur** : payroll_app

**Version PostgreSQL** : PostgreSQL 17.6 on x86_64-windows, compiled by msvc-19.44.35213, 64-bit

**Taille base** : 20 MB

## ⚙️ Paramètres PostgreSQL

| Paramètre | Valeur |
|-----------|--------|
| server_version | N/A |
| server_encoding | N/A |
| client_encoding | N/A |
| DateStyle | N/A |
| TimeZone | N/A |
| search_path | N/A |

## 🗂️ Schémas présents

- **core** : 6 table(s)
- **payroll** : 12 table(s)
- **public** : 1 table(s)
- **reference** : 4 table(s)

## 📋 Tables du schéma `core`

| Table | Lignes (est.) | Taille | Commentaire |
|-------|---------------|--------|-------------|
| `budget_posts` | 170 | 152 kB | - |
| `employee_job_history` | -1 | 40 kB | - |
| `employees` | 295 | 200 kB | RÃ©fÃ©rentiel unique employÃ©s (dimension) |
| `job_categories` | -1 | 24 kB | - |
| `job_codes` | -1 | 24 kB | - |
| `pay_codes` | 148 | 104 kB | - |

### Table `core.budget_posts`

**Commentaire** : Aucun

**Estimation lignes** : 170

**Taille** : 152 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `budget_post_id` | integer | NO | nextval('core.budget_posts_bud | - |
| 2 | `code` | character varying(50) | NO | - | - |
| 3 | `description` | character varying(500) | YES | - | - |
| 4 | `active` | boolean | NO | true | - |
| 5 | `created_at` | timestamp with time zone | NO | CURRENT_TIMESTAMP | - |

**Contraintes** :

- `budget_posts_pkey` (PRIMARY KEY) : PRIMARY KEY (budget_post_id)
- `uq_budget_posts_code` (UNIQUE) : UNIQUE (code)

**Index** :

- `budget_posts_pkey` (16 kB) : CREATE UNIQUE INDEX budget_posts_pkey ON core.budget_posts USING btree (budget_post_id)
- `idx_budget_posts_active` (16 kB) : CREATE INDEX idx_budget_posts_active ON core.budget_posts USING btree (active)
- `uq_budget_posts_code` (40 kB) : CREATE UNIQUE INDEX uq_budget_posts_code ON core.budget_posts USING btree (code)

### Table `core.employee_job_history`

**Commentaire** : Aucun

**Estimation lignes** : -1

**Taille** : 40 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `history_id` | uuid | NO | uuid_generate_v4() | - |
| 2 | `employee_id` | uuid | NO | - | - |
| 3 | `code_id` | integer | NO | - | - |
| 4 | `date_debut` | date | NO | - | - |
| 5 | `date_fin` | date | YES | - | - |
| 6 | `created_at` | timestamp with time zone | NO | CURRENT_TIMESTAMP | - |

**Contraintes** :

- `employee_job_history_pkey` (PRIMARY KEY) : PRIMARY KEY (history_id)
- `excl_employee_job_history_no_overlap` (EXCLUDE) : EXCLUDE USING gist (employee_id WITH =, daterange(date_debut, COALESCE(date_fin, 'infinity'::date), '[]'::text) WITH &&)

**Index** :

- `employee_job_history_pkey` (8192 bytes) : CREATE UNIQUE INDEX employee_job_history_pkey ON core.employee_job_history USING btree (history_id)
- `excl_employee_job_history_no_overlap` (8192 bytes) : CREATE INDEX excl_employee_job_history_no_overlap ON core.employee_job_history USING gist (employee_id, daterange(date_debut, COALESCE(date_fin, 'infinity'::date), '[]'::text))
- `idx_emp_job_hist_code` (8192 bytes) : CREATE INDEX idx_emp_job_hist_code ON core.employee_job_history USING btree (code_id)
- `idx_emp_job_hist_dates` (8192 bytes) : CREATE INDEX idx_emp_job_hist_dates ON core.employee_job_history USING btree (date_debut, date_fin)
- `idx_emp_job_hist_employee` (8192 bytes) : CREATE INDEX idx_emp_job_hist_employee ON core.employee_job_history USING btree (employee_id)

### Table `core.employees`

**Commentaire** : RÃ©fÃ©rentiel unique employÃ©s (dimension)

**Estimation lignes** : 295

**Taille** : 200 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `employee_id` | integer | NO | - | ClÃ© technique IDENTITY |
| 2 | `employee_key` | character varying(255) | NO | - | ClÃ© mÃ©tier normalisÃ©e (unique) |
| 3 | `matricule_norm` | character varying(50) | YES | - | Matricule normalisÃ© (trim, zÃ©ros, para |
| 4 | `matricule_raw` | character varying(100) | YES | - | - |
| 5 | `nom_norm` | character varying(255) | NO | - | - |
| 6 | `prenom_norm` | character varying(255) | YES | - | - |
| 7 | `nom_complet` | character varying(500) | YES | - | - |
| 8 | `statut` | character varying(20) | YES | 'actif'::character varying | actif | inactif | suspendu |
| 9 | `source_system` | character varying(50) | YES | 'excel_import'::character vary | - |
| 10 | `created_at` | timestamp with time zone | YES | CURRENT_TIMESTAMP | - |
| 11 | `updated_at` | timestamp with time zone | YES | CURRENT_TIMESTAMP | - |
| 12 | `created_by` | character varying(100) | YES | CURRENT_USER | - |
| 13 | `updated_by` | character varying(100) | YES | CURRENT_USER | - |

**Contraintes** :

- `employees_statut_check` (CHECK) : CHECK (((statut)::text = ANY ((ARRAY['actif'::character varying, 'inactif'::character varying, 'suspendu'::character varying])::text[])))
- `employees_pkey` (PRIMARY KEY) : PRIMARY KEY (employee_id)
- `employees_employee_key_key` (UNIQUE) : UNIQUE (employee_key)

**Index** :

- `employees_employee_key_key` (16 kB) : CREATE UNIQUE INDEX employees_employee_key_key ON core.employees USING btree (employee_key)
- `employees_pkey` (16 kB) : CREATE UNIQUE INDEX employees_pkey ON core.employees USING btree (employee_id)
- `idx_employees_key` (16 kB) : CREATE UNIQUE INDEX idx_employees_key ON core.employees USING btree (employee_key)
- `idx_employees_matricule` (16 kB) : CREATE INDEX idx_employees_matricule ON core.employees USING btree (matricule_norm) WHERE (matricule_norm IS NOT NULL)
- `idx_employees_nom` (40 kB) : CREATE INDEX idx_employees_nom ON core.employees USING btree (nom_norm, prenom_norm)
- `idx_employees_statut` (16 kB) : CREATE INDEX idx_employees_statut ON core.employees USING btree (statut)

### Table `core.job_categories`

**Commentaire** : Aucun

**Estimation lignes** : -1

**Taille** : 24 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `category_id` | integer | NO | nextval('core.job_categories_c | - |
| 2 | `nom` | character varying(100) | NO | - | - |
| 3 | `description` | text | YES | - | - |
| 4 | `active` | boolean | NO | true | - |
| 5 | `created_at` | timestamp with time zone | NO | CURRENT_TIMESTAMP | - |

**Contraintes** :

- `job_categories_pkey` (PRIMARY KEY) : PRIMARY KEY (category_id)
- `uq_job_categories_nom` (UNIQUE) : UNIQUE (nom)

**Index** :

- `job_categories_pkey` (8192 bytes) : CREATE UNIQUE INDEX job_categories_pkey ON core.job_categories USING btree (category_id)
- `uq_job_categories_nom` (8192 bytes) : CREATE UNIQUE INDEX uq_job_categories_nom ON core.job_categories USING btree (nom)

### Table `core.job_codes`

**Commentaire** : Aucun

**Estimation lignes** : -1

**Taille** : 24 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `code_id` | integer | NO | nextval('core.job_codes_code_i | - |
| 2 | `code` | character varying(20) | NO | - | - |
| 3 | `titre` | character varying(255) | NO | - | - |
| 4 | `category_id` | integer | YES | - | - |
| 5 | `active` | boolean | NO | true | - |
| 6 | `created_at` | timestamp with time zone | NO | CURRENT_TIMESTAMP | - |

**Contraintes** :

- `job_codes_pkey` (PRIMARY KEY) : PRIMARY KEY (code_id)
- `uq_job_codes_code` (UNIQUE) : UNIQUE (code)

**Index** :

- `idx_job_codes_category` (8192 bytes) : CREATE INDEX idx_job_codes_category ON core.job_codes USING btree (category_id)
- `job_codes_pkey` (8192 bytes) : CREATE UNIQUE INDEX job_codes_pkey ON core.job_codes USING btree (code_id)
- `uq_job_codes_code` (8192 bytes) : CREATE UNIQUE INDEX uq_job_codes_code ON core.job_codes USING btree (code)

### Table `core.pay_codes`

**Commentaire** : Aucun

**Estimation lignes** : 148

**Taille** : 104 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `pay_code` | character varying(100) | NO | - | - |
| 2 | `label` | character varying(255) | NO | - | - |
| 3 | `category` | character varying(100) | NO | - | - |
| 4 | `active` | boolean | NO | true | - |
| 5 | `created_at` | timestamp with time zone | NO | CURRENT_TIMESTAMP | - |

**Contraintes** :

- `pay_codes_pkey` (PRIMARY KEY) : PRIMARY KEY (pay_code)

**Index** :

- `idx_pay_codes_active` (16 kB) : CREATE INDEX idx_pay_codes_active ON core.pay_codes USING btree (active)
- `idx_pay_codes_category` (16 kB) : CREATE INDEX idx_pay_codes_category ON core.pay_codes USING btree (category)
- `pay_codes_pkey` (16 kB) : CREATE UNIQUE INDEX pay_codes_pkey ON core.pay_codes USING btree (pay_code)

## 📋 Tables du schéma `payroll`

| Table | Lignes (est.) | Taille | Commentaire |
|-------|---------------|--------|-------------|
| `budget_posts` | -1 | 48 kB | - |
| `import_batches` | -1 | 80 kB | Historique imports (audit/traÃ§abilitÃ©) |
| `import_log` | -1 | 32 kB | Log détaillé alertes import (non bloquant) |
| `import_runs` | -1 | 32 kB | Historique des imports (traçabilité) |
| `imported_payroll_master` | 7,735 | 3944 kB | - |
| `kpi_snapshot` | -1 | 48 kB | - |
| `pay_periods` | 0 | 584 kB | - |
| `payroll_transactions` | 3,352 | 0 bytes | Fait paie (partitionnÃ© par annÃ©e sur pay_date) |
| `payroll_transactions_2024` | 0 | 56 kB | Partition annÃ©e 2024 |
| `payroll_transactions_2025` | 3,352 | 856 kB | Partition annÃ©e 2025 |
| `payroll_transactions_2026` | 0 | 56 kB | Partition annÃ©e 2026 |
| `stg_imported_payroll` | 3,352 | 720 kB | Staging import (temporaire, nettoyÃ© aprÃ¨s valida |

### Table `payroll.budget_posts`

**Commentaire** : Aucun

**Estimation lignes** : -1

**Taille** : 48 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `post_id` | integer | NO | nextval('payroll.budget_posts_ | - |
| 2 | `code` | text | YES | - | - |
| 3 | `description` | text | YES | - | - |
| 4 | `category` | text | YES | - | - |
| 5 | `is_active` | boolean | YES | true | - |

**Contraintes** :

- `budget_posts_pkey` (PRIMARY KEY) : PRIMARY KEY (post_id)
- `budget_posts_code_key` (UNIQUE) : UNIQUE (code)

**Index** :

- `budget_posts_code_key` (16 kB) : CREATE UNIQUE INDEX budget_posts_code_key ON payroll.budget_posts USING btree (code)
- `budget_posts_pkey` (16 kB) : CREATE UNIQUE INDEX budget_posts_pkey ON payroll.budget_posts USING btree (post_id)

### Table `payroll.import_batches`

**Commentaire** : Historique imports (audit/traÃ§abilitÃ©)

**Estimation lignes** : -1

**Taille** : 80 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `batch_id` | integer | NO | - | - |
| 2 | `batch_uuid` | uuid | YES | gen_random_uuid() | - |
| 3 | `filename` | character varying(500) | YES | - | - |
| 4 | `file_checksum` | character varying(64) | YES | - | - |
| 5 | `total_rows` | integer | YES | - | - |
| 6 | `valid_rows` | integer | YES | - | - |
| 7 | `invalid_rows` | integer | YES | - | - |
| 8 | `new_employees` | integer | YES | - | - |
| 9 | `new_transactions` | integer | YES | - | - |
| 10 | `status` | character varying(20) | YES | 'pending'::character varying | - |
| 11 | `error_message` | text | YES | - | - |
| 12 | `started_at` | timestamp with time zone | YES | CURRENT_TIMESTAMP | - |
| 13 | `completed_at` | timestamp with time zone | YES | - | - |
| 14 | `created_by` | character varying(100) | YES | CURRENT_USER | - |

**Contraintes** :

- `import_batches_status_check` (CHECK) : CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'processing'::character varying, 'completed'::character varying, 'failed'::character varying, 'rolled_back'::character varying])::text[])))
- `import_batches_pkey` (PRIMARY KEY) : PRIMARY KEY (batch_id)
- `import_batches_batch_uuid_key` (UNIQUE) : UNIQUE (batch_uuid)

**Index** :

- `idx_batches_started` (16 kB) : CREATE INDEX idx_batches_started ON payroll.import_batches USING btree (started_at DESC)
- `idx_batches_status` (16 kB) : CREATE INDEX idx_batches_status ON payroll.import_batches USING btree (status)
- `import_batches_batch_uuid_key` (16 kB) : CREATE UNIQUE INDEX import_batches_batch_uuid_key ON payroll.import_batches USING btree (batch_uuid)
- `import_batches_pkey` (16 kB) : CREATE UNIQUE INDEX import_batches_pkey ON payroll.import_batches USING btree (batch_id)

### Table `payroll.import_log`

**Commentaire** : Log détaillé alertes import (non bloquant)

**Estimation lignes** : -1

**Taille** : 32 kB

**Contraintes** :

- `import_log_alert_type_check` (CHECK) : CHECK ((alert_type = ANY (ARRAY['conversion_failed'::text, 'null_value'::text, 'out_of_range'::text, 'format_error'::text, 'constraint_violation'::text])))
- `import_log_pkey` (PRIMARY KEY) : PRIMARY KEY (log_id)

**Index** :

- `idx_import_log_alert_type` (8192 bytes) : CREATE INDEX idx_import_log_alert_type ON payroll.import_log USING btree (alert_type)
- `idx_import_log_run` (8192 bytes) : CREATE INDEX idx_import_log_run ON payroll.import_log USING btree (run_id)
- `import_log_pkey` (8192 bytes) : CREATE UNIQUE INDEX import_log_pkey ON payroll.import_log USING btree (log_id)

### Table `payroll.import_runs`

**Commentaire** : Historique des imports (traçabilité)

**Estimation lignes** : -1

**Taille** : 32 kB

**Contraintes** :

- `import_runs_import_mode_check` (CHECK) : CHECK ((import_mode = ANY (ARRAY['fast_track'::text, 'detection'::text, 'manual'::text])))
- `import_runs_status_check` (CHECK) : CHECK ((status = ANY (ARRAY['running'::text, 'completed'::text, 'failed'::text, 'cancelled'::text])))
- `import_runs_pkey` (PRIMARY KEY) : PRIMARY KEY (run_id)

**Index** :

- `idx_import_runs_file` (8192 bytes) : CREATE INDEX idx_import_runs_file ON payroll.import_runs USING btree (source_file)
- `idx_import_runs_started` (8192 bytes) : CREATE INDEX idx_import_runs_started ON payroll.import_runs USING btree (started_at DESC)
- `import_runs_pkey` (8192 bytes) : CREATE UNIQUE INDEX import_runs_pkey ON payroll.import_runs USING btree (run_id)

### Table `payroll.imported_payroll_master`

**Commentaire** : Aucun

**Estimation lignes** : 7,735

**Taille** : 3944 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `id` | bigint | NO | nextval('payroll.imported_payr | - |
| 2 | `N de ligne ` | integer | YES | - | - |
| 3 | `Categorie d'emploi` | text | YES | - | - |
| 4 | `code emploi` | text | YES | - | - |
| 5 | `titre d'emploi` | text | YES | - | - |
| 6 | `date de paie ` | date | NO | - | - |
| 7 | `matricule ` | text | YES | - | - |
| 8 | `employé ` | text | YES | - | - |
| 9 | `categorie de paie ` | text | YES | - | - |
| 10 | `code de paie ` | text | YES | - | - |
| 11 | `desc code de paie ` | text | YES | - | - |
| 12 | `poste Budgetaire ` | text | YES | - | - |
| 13 | `desc poste Budgétaire ` | text | YES | - | - |
| 14 | `montant ` | numeric | YES | - | - |
| 15 | `part employeur ` | text | YES | - | - |
| 16 | `Mnt/Cmb` | text | YES | - | - |
| 17 | `source_file` | text | YES | - | - |
| 18 | `source_row_number` | integer | YES | - | - |
| 19 | `imported_at` | timestamp without time zone | YES | CURRENT_TIMESTAMP | - |

**Contraintes** :

- `imported_payroll_master_pkey` (PRIMARY KEY) : PRIMARY KEY (id)

**Index** :

- `idx_ipm_code_de_paie` (224 kB) : CREATE INDEX idx_ipm_code_de_paie ON payroll.imported_payroll_master USING btree ("code de paie ") WHERE ("code de paie " IS NOT NULL)
- `idx_ipm_date_de_paie` (184 kB) : CREATE INDEX idx_ipm_date_de_paie ON payroll.imported_payroll_master USING btree ("date de paie ")
- `idx_ipm_employe` (248 kB) : CREATE INDEX idx_ipm_employe ON payroll.imported_payroll_master USING btree ("employé ") WHERE ("employé " IS NOT NULL)
- `idx_ipm_matricule` (232 kB) : CREATE INDEX idx_ipm_matricule ON payroll.imported_payroll_master USING btree ("matricule ") WHERE ("matricule " IS NOT NULL)
- `idx_ipm_source_file` (232 kB) : CREATE INDEX idx_ipm_source_file ON payroll.imported_payroll_master USING btree (source_file)
- `idx_payroll_master_code` (80 kB) : CREATE INDEX idx_payroll_master_code ON payroll.imported_payroll_master USING btree ("code de paie ")
- `idx_payroll_master_date_matricule` (344 kB) : CREATE INDEX idx_payroll_master_date_matricule ON payroll.imported_payroll_master USING btree ("date de paie " DESC, "matricule ", id)
- `idx_payroll_master_employe_trgm` (336 kB) : CREATE INDEX idx_payroll_master_employe_trgm ON payroll.imported_payroll_master USING gin ("employé " gin_trgm_ops)
- `idx_payroll_master_matricule` (88 kB) : CREATE INDEX idx_payroll_master_matricule ON payroll.imported_payroll_master USING btree ("matricule ")
- `idx_payroll_master_source` (72 kB) : CREATE INDEX idx_payroll_master_source ON payroll.imported_payroll_master USING btree (source_file, imported_at)
- `imported_payroll_master_pkey` (536 kB) : CREATE UNIQUE INDEX imported_payroll_master_pkey ON payroll.imported_payroll_master USING btree (id)

### Table `payroll.kpi_snapshot`

**Commentaire** : Aucun

**Estimation lignes** : -1

**Taille** : 48 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `period` | character varying(20) | NO | - | Période au format YYYY-MM (ex: 2025-01) |
| 2 | `period_id` | uuid | YES | - | FK vers pay_periods (optionnel) |
| 3 | `data` | jsonb | NO | - | KPI pré-calculés en JSONB |
| 4 | `calculated_at` | timestamp with time zone | NO | CURRENT_TIMESTAMP | Date de calcul |
| 5 | `row_count` | integer | NO | 0 | Nombre de lignes source |

**Contraintes** :

- `kpi_snapshot_pkey` (PRIMARY KEY) : PRIMARY KEY (period)

**Index** :

- `idx_kpi_snapshot_calculated` (16 kB) : CREATE INDEX idx_kpi_snapshot_calculated ON payroll.kpi_snapshot USING btree (calculated_at)
- `kpi_snapshot_pkey` (16 kB) : CREATE UNIQUE INDEX kpi_snapshot_pkey ON payroll.kpi_snapshot USING btree (period)

### Table `payroll.pay_periods`

**Commentaire** : Aucun

**Estimation lignes** : 0

**Taille** : 584 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `period_id` | uuid | NO | uuid_generate_v4() | - |
| 2 | `pay_date` | date | NO | - | - |
| 3 | `pay_day` | integer | NO | - | - |
| 4 | `pay_month` | integer | NO | - | - |
| 5 | `pay_year` | integer | NO | - | - |
| 6 | `period_seq_in_year` | integer | NO | - | - |
| 7 | `status` | character varying(20) | NO | 'ouverte'::character varying | - |
| 8 | `created_at` | timestamp with time zone | NO | CURRENT_TIMESTAMP | - |
| 9 | `closed_at` | timestamp with time zone | YES | - | - |
| 10 | `closed_by` | uuid | YES | - | - |

**Contraintes** :

- `ck_pay_periods_pay_day` (CHECK) : CHECK (((pay_day >= 1) AND (pay_day <= 31)))
- `ck_pay_periods_period_seq` (CHECK) : CHECK (((period_seq_in_year >= 1) AND (period_seq_in_year <= 53)))
- `ck_pay_periods_pay_month` (CHECK) : CHECK (((pay_month >= 1) AND (pay_month <= 12)))
- `pay_periods_pkey` (PRIMARY KEY) : PRIMARY KEY (period_id)
- `uq_pay_periods_year_seq` (UNIQUE) : UNIQUE (pay_year, period_seq_in_year)
- `uq_pay_periods_date` (UNIQUE) : UNIQUE (pay_date)

**Index** :

- `idx_pay_periods_date` (16 kB) : CREATE INDEX idx_pay_periods_date ON payroll.pay_periods USING btree (pay_date)
- `idx_pay_periods_status` (72 kB) : CREATE INDEX idx_pay_periods_status ON payroll.pay_periods USING btree (status)
- `idx_pay_periods_year` (72 kB) : CREATE INDEX idx_pay_periods_year ON payroll.pay_periods USING btree (pay_year)
- `pay_periods_pkey` (296 kB) : CREATE UNIQUE INDEX pay_periods_pkey ON payroll.pay_periods USING btree (period_id)
- `uq_pay_periods_date` (16 kB) : CREATE UNIQUE INDEX uq_pay_periods_date ON payroll.pay_periods USING btree (pay_date)
- `uq_pay_periods_year_seq` (16 kB) : CREATE UNIQUE INDEX uq_pay_periods_year_seq ON payroll.pay_periods USING btree (pay_year, period_seq_in_year)

### Table `payroll.payroll_transactions`

**Commentaire** : Fait paie (partitionnÃ© par annÃ©e sur pay_date)

**Estimation lignes** : 3,352

**Taille** : 0 bytes

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `transaction_id` | bigint | NO | - | - |
| 2 | `employee_id` | integer | NO | - | - |
| 3 | `pay_date` | date | NO | - | - |
| 4 | `pay_day` | integer | YES | - | - |
| 5 | `pay_month` | integer | YES | - | - |
| 6 | `pay_year` | integer | YES | - | - |
| 7 | `period_seq_in_year` | integer | YES | - | - |
| 8 | `pay_code` | character varying(50) | NO | - | - |
| 9 | `amount_cents` | bigint | NO | - | Montant en cents (prÃ©cision, Ã©vite arr |
| 10 | `import_batch_id` | integer | YES | - | - |
| 11 | `source_file` | character varying(500) | YES | - | - |
| 12 | `source_row_no` | integer | YES | - | - |
| 13 | `created_at` | timestamp with time zone | YES | CURRENT_TIMESTAMP | - |
| 14 | `created_by` | character varying(100) | YES | CURRENT_USER | - |

**Contraintes** :

- `payroll_transactions_amount_cents_check` (CHECK) : CHECK ((amount_cents <> 0))
- `pk_payroll_transactions` (PRIMARY KEY) : PRIMARY KEY (transaction_id, pay_date)

**Index** :

- `idx_payroll_code` (0 bytes) : CREATE INDEX idx_payroll_code ON ONLY payroll.payroll_transactions USING btree (pay_code)
- `idx_payroll_date` (0 bytes) : CREATE INDEX idx_payroll_date ON ONLY payroll.payroll_transactions USING btree (pay_date)
- `idx_payroll_employee` (0 bytes) : CREATE INDEX idx_payroll_employee ON ONLY payroll.payroll_transactions USING btree (employee_id)
- `idx_payroll_employee_date` (0 bytes) : CREATE INDEX idx_payroll_employee_date ON ONLY payroll.payroll_transactions USING btree (employee_id, pay_date)
- `idx_payroll_period` (0 bytes) : CREATE INDEX idx_payroll_period ON ONLY payroll.payroll_transactions USING btree (pay_year, pay_month)
- `pk_payroll_transactions` (0 bytes) : CREATE UNIQUE INDEX pk_payroll_transactions ON ONLY payroll.payroll_transactions USING btree (transaction_id, pay_date)

### Table `payroll.payroll_transactions_2024`

**Commentaire** : Partition annÃ©e 2024

**Estimation lignes** : 0

**Taille** : 56 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `transaction_id` | bigint | NO | - | - |
| 2 | `employee_id` | integer | NO | - | - |
| 3 | `pay_date` | date | NO | - | - |
| 4 | `pay_day` | integer | YES | - | - |
| 5 | `pay_month` | integer | YES | - | - |
| 6 | `pay_year` | integer | YES | - | - |
| 7 | `period_seq_in_year` | integer | YES | - | - |
| 8 | `pay_code` | character varying(50) | NO | - | - |
| 9 | `amount_cents` | bigint | NO | - | - |
| 10 | `import_batch_id` | integer | YES | - | - |
| 11 | `source_file` | character varying(500) | YES | - | - |
| 12 | `source_row_no` | integer | YES | - | - |
| 13 | `created_at` | timestamp with time zone | YES | CURRENT_TIMESTAMP | - |
| 14 | `created_by` | character varying(100) | YES | CURRENT_USER | - |

**Contraintes** :

- `payroll_transactions_amount_cents_check` (CHECK) : CHECK ((amount_cents <> 0))
- `payroll_transactions_2024_pkey` (PRIMARY KEY) : PRIMARY KEY (transaction_id, pay_date)

**Index** :

- `payroll_transactions_2024_employee_id_idx` (8192 bytes) : CREATE INDEX payroll_transactions_2024_employee_id_idx ON payroll.payroll_transactions_2024 USING btree (employee_id)
- `payroll_transactions_2024_employee_id_pay_date_idx` (8192 bytes) : CREATE INDEX payroll_transactions_2024_employee_id_pay_date_idx ON payroll.payroll_transactions_2024 USING btree (employee_id, pay_date)
- `payroll_transactions_2024_pay_code_idx` (8192 bytes) : CREATE INDEX payroll_transactions_2024_pay_code_idx ON payroll.payroll_transactions_2024 USING btree (pay_code)
- `payroll_transactions_2024_pay_date_idx` (8192 bytes) : CREATE INDEX payroll_transactions_2024_pay_date_idx ON payroll.payroll_transactions_2024 USING btree (pay_date)
- `payroll_transactions_2024_pay_year_pay_month_idx` (8192 bytes) : CREATE INDEX payroll_transactions_2024_pay_year_pay_month_idx ON payroll.payroll_transactions_2024 USING btree (pay_year, pay_month)
- `payroll_transactions_2024_pkey` (8192 bytes) : CREATE UNIQUE INDEX payroll_transactions_2024_pkey ON payroll.payroll_transactions_2024 USING btree (transaction_id, pay_date)

### Table `payroll.payroll_transactions_2025`

**Commentaire** : Partition annÃ©e 2025

**Estimation lignes** : 3,352

**Taille** : 856 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `transaction_id` | bigint | NO | - | - |
| 2 | `employee_id` | integer | NO | - | - |
| 3 | `pay_date` | date | NO | - | - |
| 4 | `pay_day` | integer | YES | - | - |
| 5 | `pay_month` | integer | YES | - | - |
| 6 | `pay_year` | integer | YES | - | - |
| 7 | `period_seq_in_year` | integer | YES | - | - |
| 8 | `pay_code` | character varying(50) | NO | - | - |
| 9 | `amount_cents` | bigint | NO | - | - |
| 10 | `import_batch_id` | integer | YES | - | - |
| 11 | `source_file` | character varying(500) | YES | - | - |
| 12 | `source_row_no` | integer | YES | - | - |
| 13 | `created_at` | timestamp with time zone | YES | CURRENT_TIMESTAMP | - |
| 14 | `created_by` | character varying(100) | YES | CURRENT_USER | - |

**Contraintes** :

- `payroll_transactions_amount_cents_check` (CHECK) : CHECK ((amount_cents <> 0))
- `payroll_transactions_2025_pkey` (PRIMARY KEY) : PRIMARY KEY (transaction_id, pay_date)

**Index** :

- `payroll_transactions_2025_employee_id_idx` (56 kB) : CREATE INDEX payroll_transactions_2025_employee_id_idx ON payroll.payroll_transactions_2025 USING btree (employee_id)
- `payroll_transactions_2025_employee_id_pay_date_idx` (56 kB) : CREATE INDEX payroll_transactions_2025_employee_id_pay_date_idx ON payroll.payroll_transactions_2025 USING btree (employee_id, pay_date)
- `payroll_transactions_2025_pay_code_idx` (40 kB) : CREATE INDEX payroll_transactions_2025_pay_code_idx ON payroll.payroll_transactions_2025 USING btree (pay_code)
- `payroll_transactions_2025_pay_date_idx` (40 kB) : CREATE INDEX payroll_transactions_2025_pay_date_idx ON payroll.payroll_transactions_2025 USING btree (pay_date)
- `payroll_transactions_2025_pay_year_pay_month_idx` (40 kB) : CREATE INDEX payroll_transactions_2025_pay_year_pay_month_idx ON payroll.payroll_transactions_2025 USING btree (pay_year, pay_month)
- `payroll_transactions_2025_pkey` (120 kB) : CREATE UNIQUE INDEX payroll_transactions_2025_pkey ON payroll.payroll_transactions_2025 USING btree (transaction_id, pay_date)

### Table `payroll.payroll_transactions_2026`

**Commentaire** : Partition annÃ©e 2026

**Estimation lignes** : 0

**Taille** : 56 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `transaction_id` | bigint | NO | - | - |
| 2 | `employee_id` | integer | NO | - | - |
| 3 | `pay_date` | date | NO | - | - |
| 4 | `pay_day` | integer | YES | - | - |
| 5 | `pay_month` | integer | YES | - | - |
| 6 | `pay_year` | integer | YES | - | - |
| 7 | `period_seq_in_year` | integer | YES | - | - |
| 8 | `pay_code` | character varying(50) | NO | - | - |
| 9 | `amount_cents` | bigint | NO | - | - |
| 10 | `import_batch_id` | integer | YES | - | - |
| 11 | `source_file` | character varying(500) | YES | - | - |
| 12 | `source_row_no` | integer | YES | - | - |
| 13 | `created_at` | timestamp with time zone | YES | CURRENT_TIMESTAMP | - |
| 14 | `created_by` | character varying(100) | YES | CURRENT_USER | - |

**Contraintes** :

- `payroll_transactions_amount_cents_check` (CHECK) : CHECK ((amount_cents <> 0))
- `payroll_transactions_2026_pkey` (PRIMARY KEY) : PRIMARY KEY (transaction_id, pay_date)

**Index** :

- `payroll_transactions_2026_employee_id_idx` (8192 bytes) : CREATE INDEX payroll_transactions_2026_employee_id_idx ON payroll.payroll_transactions_2026 USING btree (employee_id)
- `payroll_transactions_2026_employee_id_pay_date_idx` (8192 bytes) : CREATE INDEX payroll_transactions_2026_employee_id_pay_date_idx ON payroll.payroll_transactions_2026 USING btree (employee_id, pay_date)
- `payroll_transactions_2026_pay_code_idx` (8192 bytes) : CREATE INDEX payroll_transactions_2026_pay_code_idx ON payroll.payroll_transactions_2026 USING btree (pay_code)
- `payroll_transactions_2026_pay_date_idx` (8192 bytes) : CREATE INDEX payroll_transactions_2026_pay_date_idx ON payroll.payroll_transactions_2026 USING btree (pay_date)
- `payroll_transactions_2026_pay_year_pay_month_idx` (8192 bytes) : CREATE INDEX payroll_transactions_2026_pay_year_pay_month_idx ON payroll.payroll_transactions_2026 USING btree (pay_year, pay_month)
- `payroll_transactions_2026_pkey` (8192 bytes) : CREATE UNIQUE INDEX payroll_transactions_2026_pkey ON payroll.payroll_transactions_2026 USING btree (transaction_id, pay_date)

### Table `payroll.stg_imported_payroll`

**Commentaire** : Staging import (temporaire, nettoyÃ© aprÃ¨s validation)

**Estimation lignes** : 3,352

**Taille** : 720 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `stg_id` | integer | NO | - | - |
| 2 | `matricule_raw` | character varying(100) | YES | - | - |
| 3 | `employe_raw` | character varying(500) | YES | - | - |
| 4 | `date_paie_raw` | character varying(50) | YES | - | - |
| 5 | `categorie_paie_raw` | character varying(200) | YES | - | - |
| 6 | `montant_raw` | character varying(50) | YES | - | - |
| 7 | `matricule_clean` | character varying(50) | YES | - | - |
| 8 | `nom_norm` | character varying(255) | YES | - | - |
| 9 | `prenom_norm` | character varying(255) | YES | - | - |
| 10 | `employee_key` | character varying(255) | YES | - | - |
| 11 | `pay_date` | date | YES | - | - |
| 12 | `pay_code` | character varying(50) | YES | - | - |
| 13 | `amount_cents` | bigint | YES | - | - |
| 14 | `is_valid` | boolean | YES | true | - |
| 15 | `validation_errors` | ARRAY | YES | - | - |
| 16 | `import_batch_id` | integer | YES | - | - |
| 17 | `source_row_no` | integer | YES | - | - |
| 18 | `created_at` | timestamp with time zone | YES | CURRENT_TIMESTAMP | - |

**Index** :

- `idx_stg_batch` (40 kB) : CREATE INDEX idx_stg_batch ON payroll.stg_imported_payroll USING btree (import_batch_id)
- `idx_stg_employee_key` (56 kB) : CREATE INDEX idx_stg_employee_key ON payroll.stg_imported_payroll USING btree (employee_key)
- `idx_stg_valid` (40 kB) : CREATE INDEX idx_stg_valid ON payroll.stg_imported_payroll USING btree (is_valid)

## 📋 Tables du schéma `public`

| Table | Lignes (est.) | Taille | Commentaire |
|-------|---------------|--------|-------------|
| `alembic_version` | -1 | 24 kB | - |

### Table `public.alembic_version`

**Commentaire** : Aucun

**Estimation lignes** : -1

**Taille** : 24 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `version_num` | character varying(32) | NO | - | - |

**Contraintes** :

- `alembic_version_pkc` (PRIMARY KEY) : PRIMARY KEY (version_num)

**Index** :

- `alembic_version_pkc` (16 kB) : CREATE UNIQUE INDEX alembic_version_pkc ON public.alembic_version USING btree (version_num)

## 📋 Tables du schéma `reference`

| Table | Lignes (est.) | Taille | Commentaire |
|-------|---------------|--------|-------------|
| `budget_posts` | -1 | 48 kB | - |
| `pay_code_mappings` | -1 | 32 kB | - |
| `pay_codes` | -1 | 72 kB | RÃ©fÃ©rentiel codes de paie |
| `sign_policies` | -1 | 24 kB | - |

### Table `reference.budget_posts`

**Commentaire** : Aucun

**Estimation lignes** : -1

**Taille** : 48 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `post_id` | integer | NO | nextval('reference.budget_post | - |
| 2 | `code` | text | NO | - | - |
| 3 | `description` | text | YES | - | - |
| 4 | `category` | text | YES | 'general'::text | - |
| 5 | `is_active` | boolean | YES | true | - |
| 6 | `created_at` | timestamp with time zone | YES | now() | - |

**Contraintes** :

- `budget_posts_pkey` (PRIMARY KEY) : PRIMARY KEY (post_id)
- `budget_posts_code_key` (UNIQUE) : UNIQUE (code)

**Index** :

- `budget_posts_code_key` (16 kB) : CREATE UNIQUE INDEX budget_posts_code_key ON reference.budget_posts USING btree (code)
- `budget_posts_pkey` (16 kB) : CREATE UNIQUE INDEX budget_posts_pkey ON reference.budget_posts USING btree (post_id)

### Table `reference.pay_code_mappings`

**Commentaire** : Aucun

**Estimation lignes** : -1

**Taille** : 32 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `mapping_id` | integer | NO | nextval('reference.pay_code_ma | - |
| 2 | `source_column_name` | character varying(255) | NO | - | - |
| 3 | `source_value` | character varying(255) | YES | - | - |
| 4 | `pay_code` | character varying(20) | NO | - | - |
| 5 | `priority` | integer | YES | 100 | - |
| 6 | `active` | boolean | NO | true | - |
| 7 | `created_at` | timestamp with time zone | NO | CURRENT_TIMESTAMP | - |

**Contraintes** :

- `pay_code_mappings_pkey` (PRIMARY KEY) : PRIMARY KEY (mapping_id)

**Index** :

- `idx_pay_code_mappings_pay_code` (8192 bytes) : CREATE INDEX idx_pay_code_mappings_pay_code ON reference.pay_code_mappings USING btree (pay_code)
- `idx_pay_code_mappings_source` (8192 bytes) : CREATE INDEX idx_pay_code_mappings_source ON reference.pay_code_mappings USING btree (source_column_name)
- `pay_code_mappings_pkey` (8192 bytes) : CREATE UNIQUE INDEX pay_code_mappings_pkey ON reference.pay_code_mappings USING btree (mapping_id)

### Table `reference.pay_codes`

**Commentaire** : RÃ©fÃ©rentiel codes de paie

**Estimation lignes** : -1

**Taille** : 72 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `pay_code_id` | integer | NO | - | - |
| 2 | `pay_code` | character varying(50) | NO | - | - |
| 3 | `pay_code_desc` | character varying(255) | YES | - | - |
| 4 | `pay_code_type` | character varying(20) | YES | - | - |
| 5 | `is_active` | boolean | YES | true | - |
| 6 | `created_at` | timestamp with time zone | YES | CURRENT_TIMESTAMP | - |

**Contraintes** :

- `pay_codes_pay_code_type_check` (CHECK) : CHECK (((pay_code_type)::text = ANY ((ARRAY['earning'::character varying, 'deduction'::character varying, 'tax'::character varying, 'benefit'::character varying, 'other'::character varying])::text[])))
- `pay_codes_pkey` (PRIMARY KEY) : PRIMARY KEY (pay_code_id)
- `pay_codes_pay_code_key` (UNIQUE) : UNIQUE (pay_code)

**Index** :

- `idx_pay_codes_active` (16 kB) : CREATE INDEX idx_pay_codes_active ON reference.pay_codes USING btree (is_active)
- `idx_pay_codes_type` (16 kB) : CREATE INDEX idx_pay_codes_type ON reference.pay_codes USING btree (pay_code_type)
- `pay_codes_pay_code_key` (16 kB) : CREATE UNIQUE INDEX pay_codes_pay_code_key ON reference.pay_codes USING btree (pay_code)
- `pay_codes_pkey` (16 kB) : CREATE UNIQUE INDEX pay_codes_pkey ON reference.pay_codes USING btree (pay_code_id)

### Table `reference.sign_policies`

**Commentaire** : Aucun

**Estimation lignes** : -1

**Taille** : 24 kB

**Colonnes** :

| # | Colonne | Type | Nullable | Défaut | Commentaire |
|---|---------|------|----------|--------|-------------|
| 1 | `policy_id` | integer | NO | nextval('reference.sign_polici | - |
| 2 | `pay_code` | character varying(20) | NO | - | - |
| 3 | `employee_sign` | smallint | NO | - | - |
| 4 | `employer_sign` | smallint | NO | - | - |
| 5 | `description` | text | YES | - | - |
| 6 | `active` | boolean | NO | true | - |
| 7 | `created_at` | timestamp with time zone | NO | CURRENT_TIMESTAMP | - |

**Contraintes** :

- `ck_sign_policies_employer_sign` (CHECK) : CHECK ((employer_sign = ANY (ARRAY['-1'::integer, 1])))
- `ck_sign_policies_employee_sign` (CHECK) : CHECK ((employee_sign = ANY (ARRAY['-1'::integer, 1])))
- `sign_policies_pkey` (PRIMARY KEY) : PRIMARY KEY (policy_id)
- `uq_sign_policies_pay_code` (UNIQUE) : UNIQUE (pay_code)

**Index** :

- `sign_policies_pkey` (8192 bytes) : CREATE UNIQUE INDEX sign_policies_pkey ON reference.sign_policies USING btree (policy_id)
- `uq_sign_policies_pay_code` (8192 bytes) : CREATE UNIQUE INDEX uq_sign_policies_pay_code ON reference.sign_policies USING btree (pay_code)

## 👁️ Vues

| Schéma | Vue | Définition (extrait) |
|--------|-----|----------------------|
| `core` | `v_employees_enriched` |  SELECT e.employee_id,     e.employee_key,     e.matricule_norm,     e.matricule_raw,     e.nom_norm... |
| `payroll` | `v_imported_payroll` |  SELECT id,     TRIM(BOTH FROM "N de ligne "::text) AS numero_ligne,     TRIM(BOTH FROM "Categorie d... |
| `payroll` | `v_imported_payroll_compat` |  SELECT e.matricule_raw AS "matricule ",     e.nom_complet AS "employÃ© ",     t.pay_date AS "date d... |
| `payroll` | `v_nouveaux_par_batch` |  WITH batches_avec_date AS (          SELECT DISTINCT ib.batch_id,             ib.filename,         ... |

## 🔧 Fonctions et Procédures

| Schéma | Routine | Arguments | Retour | Langage |
|--------|---------|-----------|--------|----------|
| `core` | `compute_employee_key` | p_matricule text, p_nom text | character varying | plpgsql |
| `core` | `immutable_unaccent` | text | text | plpgsql |
| `core` | `update_timestamp` |  | trigger | plpgsql |
| `core` | `update_updated_at_column` |  | trigger | plpgsql |
| `payroll` | `auto_calc_period_seq` |  | trigger | plpgsql |
| `payroll` | `check_pay_date_consistency` |  | trigger | plpgsql |
| `payroll` | `check_transaction_pay_date` |  | trigger | plpgsql |
| `payroll` | `ensure_period` | p_date date | uuid | plpgsql |
| `payroll` | `get_stats_nouveaux_date` | p_pay_date date | TABLE(batch_id integer, pay_da | plpgsql |
| `public` | `armor` | bytea | text | c |
| `public` | `armor` | bytea, text[], text[] | text | c |
| `public` | `cash_dist` | money, money | money | c |
| `public` | `crypt` | text, text | text | c |
| `public` | `date_dist` | date, date | integer | c |
| `public` | `dearmor` | text | bytea | c |
| `public` | `decrypt` | bytea, bytea, text | bytea | c |
| `public` | `decrypt_iv` | bytea, bytea, bytea, text | bytea | c |
| `public` | `digest` | text, text | bytea | c |
| `public` | `digest` | bytea, text | bytea | c |
| `public` | `encrypt` | bytea, bytea, text | bytea | c |
| `public` | `encrypt_iv` | bytea, bytea, bytea, text | bytea | c |
| `public` | `float4_dist` | real, real | real | c |
| `public` | `float8_dist` | double precision, double precision | double precision | c |
| `public` | `gbt_bit_compress` | internal | internal | c |
| `public` | `gbt_bit_consistent` | internal, bit, smallint, oid, internal | boolean | c |
| `public` | `gbt_bit_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_bit_picksplit` | internal, internal | internal | c |
| `public` | `gbt_bit_same` | gbtreekey_var, gbtreekey_var, internal | internal | c |
| `public` | `gbt_bit_union` | internal, internal | gbtreekey_var | c |
| `public` | `gbt_bool_compress` | internal | internal | c |
| `public` | `gbt_bool_consistent` | internal, boolean, smallint, oid, intern | boolean | c |
| `public` | `gbt_bool_fetch` | internal | internal | c |
| `public` | `gbt_bool_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_bool_picksplit` | internal, internal | internal | c |
| `public` | `gbt_bool_same` | gbtreekey2, gbtreekey2, internal | internal | c |
| `public` | `gbt_bool_union` | internal, internal | gbtreekey2 | c |
| `public` | `gbt_bpchar_compress` | internal | internal | c |
| `public` | `gbt_bpchar_consistent` | internal, character, smallint, oid, inte | boolean | c |
| `public` | `gbt_bytea_compress` | internal | internal | c |
| `public` | `gbt_bytea_consistent` | internal, bytea, smallint, oid, internal | boolean | c |
| `public` | `gbt_bytea_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_bytea_picksplit` | internal, internal | internal | c |
| `public` | `gbt_bytea_same` | gbtreekey_var, gbtreekey_var, internal | internal | c |
| `public` | `gbt_bytea_union` | internal, internal | gbtreekey_var | c |
| `public` | `gbt_cash_compress` | internal | internal | c |
| `public` | `gbt_cash_consistent` | internal, money, smallint, oid, internal | boolean | c |
| `public` | `gbt_cash_distance` | internal, money, smallint, oid, internal | double precision | c |
| `public` | `gbt_cash_fetch` | internal | internal | c |
| `public` | `gbt_cash_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_cash_picksplit` | internal, internal | internal | c |
| `public` | `gbt_cash_same` | gbtreekey16, gbtreekey16, internal | internal | c |
| `public` | `gbt_cash_union` | internal, internal | gbtreekey16 | c |
| `public` | `gbt_date_compress` | internal | internal | c |
| `public` | `gbt_date_consistent` | internal, date, smallint, oid, internal | boolean | c |
| `public` | `gbt_date_distance` | internal, date, smallint, oid, internal | double precision | c |
| `public` | `gbt_date_fetch` | internal | internal | c |
| `public` | `gbt_date_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_date_picksplit` | internal, internal | internal | c |
| `public` | `gbt_date_same` | gbtreekey8, gbtreekey8, internal | internal | c |
| `public` | `gbt_date_union` | internal, internal | gbtreekey8 | c |
| `public` | `gbt_decompress` | internal | internal | c |
| `public` | `gbt_enum_compress` | internal | internal | c |
| `public` | `gbt_enum_consistent` | internal, anyenum, smallint, oid, intern | boolean | c |
| `public` | `gbt_enum_fetch` | internal | internal | c |
| `public` | `gbt_enum_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_enum_picksplit` | internal, internal | internal | c |
| `public` | `gbt_enum_same` | gbtreekey8, gbtreekey8, internal | internal | c |
| `public` | `gbt_enum_union` | internal, internal | gbtreekey8 | c |
| `public` | `gbt_float4_compress` | internal | internal | c |
| `public` | `gbt_float4_consistent` | internal, real, smallint, oid, internal | boolean | c |
| `public` | `gbt_float4_distance` | internal, real, smallint, oid, internal | double precision | c |
| `public` | `gbt_float4_fetch` | internal | internal | c |
| `public` | `gbt_float4_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_float4_picksplit` | internal, internal | internal | c |
| `public` | `gbt_float4_same` | gbtreekey8, gbtreekey8, internal | internal | c |
| `public` | `gbt_float4_union` | internal, internal | gbtreekey8 | c |
| `public` | `gbt_float8_compress` | internal | internal | c |
| `public` | `gbt_float8_consistent` | internal, double precision, smallint, oi | boolean | c |
| `public` | `gbt_float8_distance` | internal, double precision, smallint, oi | double precision | c |
| `public` | `gbt_float8_fetch` | internal | internal | c |
| `public` | `gbt_float8_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_float8_picksplit` | internal, internal | internal | c |
| `public` | `gbt_float8_same` | gbtreekey16, gbtreekey16, internal | internal | c |
| `public` | `gbt_float8_union` | internal, internal | gbtreekey16 | c |
| `public` | `gbt_inet_compress` | internal | internal | c |
| `public` | `gbt_inet_consistent` | internal, inet, smallint, oid, internal | boolean | c |
| `public` | `gbt_inet_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_inet_picksplit` | internal, internal | internal | c |
| `public` | `gbt_inet_same` | gbtreekey16, gbtreekey16, internal | internal | c |
| `public` | `gbt_inet_union` | internal, internal | gbtreekey16 | c |
| `public` | `gbt_int2_compress` | internal | internal | c |
| `public` | `gbt_int2_consistent` | internal, smallint, smallint, oid, inter | boolean | c |
| `public` | `gbt_int2_distance` | internal, smallint, smallint, oid, inter | double precision | c |
| `public` | `gbt_int2_fetch` | internal | internal | c |
| `public` | `gbt_int2_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_int2_picksplit` | internal, internal | internal | c |
| `public` | `gbt_int2_same` | gbtreekey4, gbtreekey4, internal | internal | c |
| `public` | `gbt_int2_union` | internal, internal | gbtreekey4 | c |
| `public` | `gbt_int4_compress` | internal | internal | c |
| `public` | `gbt_int4_consistent` | internal, integer, smallint, oid, intern | boolean | c |
| `public` | `gbt_int4_distance` | internal, integer, smallint, oid, intern | double precision | c |
| `public` | `gbt_int4_fetch` | internal | internal | c |
| `public` | `gbt_int4_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_int4_picksplit` | internal, internal | internal | c |
| `public` | `gbt_int4_same` | gbtreekey8, gbtreekey8, internal | internal | c |
| `public` | `gbt_int4_union` | internal, internal | gbtreekey8 | c |
| `public` | `gbt_int8_compress` | internal | internal | c |
| `public` | `gbt_int8_consistent` | internal, bigint, smallint, oid, interna | boolean | c |
| `public` | `gbt_int8_distance` | internal, bigint, smallint, oid, interna | double precision | c |
| `public` | `gbt_int8_fetch` | internal | internal | c |
| `public` | `gbt_int8_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_int8_picksplit` | internal, internal | internal | c |
| `public` | `gbt_int8_same` | gbtreekey16, gbtreekey16, internal | internal | c |
| `public` | `gbt_int8_union` | internal, internal | gbtreekey16 | c |
| `public` | `gbt_intv_compress` | internal | internal | c |
| `public` | `gbt_intv_consistent` | internal, interval, smallint, oid, inter | boolean | c |
| `public` | `gbt_intv_decompress` | internal | internal | c |
| `public` | `gbt_intv_distance` | internal, interval, smallint, oid, inter | double precision | c |
| `public` | `gbt_intv_fetch` | internal | internal | c |
| `public` | `gbt_intv_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_intv_picksplit` | internal, internal | internal | c |
| `public` | `gbt_intv_same` | gbtreekey32, gbtreekey32, internal | internal | c |
| `public` | `gbt_intv_union` | internal, internal | gbtreekey32 | c |
| `public` | `gbt_macad8_compress` | internal | internal | c |
| `public` | `gbt_macad8_consistent` | internal, macaddr8, smallint, oid, inter | boolean | c |
| `public` | `gbt_macad8_fetch` | internal | internal | c |
| `public` | `gbt_macad8_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_macad8_picksplit` | internal, internal | internal | c |
| `public` | `gbt_macad8_same` | gbtreekey16, gbtreekey16, internal | internal | c |
| `public` | `gbt_macad8_union` | internal, internal | gbtreekey16 | c |
| `public` | `gbt_macad_compress` | internal | internal | c |
| `public` | `gbt_macad_consistent` | internal, macaddr, smallint, oid, intern | boolean | c |
| `public` | `gbt_macad_fetch` | internal | internal | c |
| `public` | `gbt_macad_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_macad_picksplit` | internal, internal | internal | c |
| `public` | `gbt_macad_same` | gbtreekey16, gbtreekey16, internal | internal | c |
| `public` | `gbt_macad_union` | internal, internal | gbtreekey16 | c |
| `public` | `gbt_numeric_compress` | internal | internal | c |
| `public` | `gbt_numeric_consistent` | internal, numeric, smallint, oid, intern | boolean | c |
| `public` | `gbt_numeric_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_numeric_picksplit` | internal, internal | internal | c |
| `public` | `gbt_numeric_same` | gbtreekey_var, gbtreekey_var, internal | internal | c |
| `public` | `gbt_numeric_union` | internal, internal | gbtreekey_var | c |
| `public` | `gbt_oid_compress` | internal | internal | c |
| `public` | `gbt_oid_consistent` | internal, oid, smallint, oid, internal | boolean | c |
| `public` | `gbt_oid_distance` | internal, oid, smallint, oid, internal | double precision | c |
| `public` | `gbt_oid_fetch` | internal | internal | c |
| `public` | `gbt_oid_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_oid_picksplit` | internal, internal | internal | c |
| `public` | `gbt_oid_same` | gbtreekey8, gbtreekey8, internal | internal | c |
| `public` | `gbt_oid_union` | internal, internal | gbtreekey8 | c |
| `public` | `gbt_text_compress` | internal | internal | c |
| `public` | `gbt_text_consistent` | internal, text, smallint, oid, internal | boolean | c |
| `public` | `gbt_text_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_text_picksplit` | internal, internal | internal | c |
| `public` | `gbt_text_same` | gbtreekey_var, gbtreekey_var, internal | internal | c |
| `public` | `gbt_text_union` | internal, internal | gbtreekey_var | c |
| `public` | `gbt_time_compress` | internal | internal | c |
| `public` | `gbt_time_consistent` | internal, time without time zone, smalli | boolean | c |
| `public` | `gbt_time_distance` | internal, time without time zone, smalli | double precision | c |
| `public` | `gbt_time_fetch` | internal | internal | c |
| `public` | `gbt_time_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_time_picksplit` | internal, internal | internal | c |
| `public` | `gbt_time_same` | gbtreekey16, gbtreekey16, internal | internal | c |
| `public` | `gbt_time_union` | internal, internal | gbtreekey16 | c |
| `public` | `gbt_timetz_compress` | internal | internal | c |
| `public` | `gbt_timetz_consistent` | internal, time with time zone, smallint, | boolean | c |
| `public` | `gbt_ts_compress` | internal | internal | c |
| `public` | `gbt_ts_consistent` | internal, timestamp without time zone, s | boolean | c |
| `public` | `gbt_ts_distance` | internal, timestamp without time zone, s | double precision | c |
| `public` | `gbt_ts_fetch` | internal | internal | c |
| `public` | `gbt_ts_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_ts_picksplit` | internal, internal | internal | c |
| `public` | `gbt_ts_same` | gbtreekey16, gbtreekey16, internal | internal | c |
| `public` | `gbt_ts_union` | internal, internal | gbtreekey16 | c |
| `public` | `gbt_tstz_compress` | internal | internal | c |
| `public` | `gbt_tstz_consistent` | internal, timestamp with time zone, smal | boolean | c |
| `public` | `gbt_tstz_distance` | internal, timestamp with time zone, smal | double precision | c |
| `public` | `gbt_uuid_compress` | internal | internal | c |
| `public` | `gbt_uuid_consistent` | internal, uuid, smallint, oid, internal | boolean | c |
| `public` | `gbt_uuid_fetch` | internal | internal | c |
| `public` | `gbt_uuid_penalty` | internal, internal, internal | internal | c |
| `public` | `gbt_uuid_picksplit` | internal, internal | internal | c |
| `public` | `gbt_uuid_same` | gbtreekey32, gbtreekey32, internal | internal | c |
| `public` | `gbt_uuid_union` | internal, internal | gbtreekey32 | c |
| `public` | `gbt_var_decompress` | internal | internal | c |
| `public` | `gbt_var_fetch` | internal | internal | c |
| `public` | `gbtreekey16_in` | cstring | gbtreekey16 | c |
| `public` | `gbtreekey16_out` | gbtreekey16 | cstring | c |
| `public` | `gbtreekey2_in` | cstring | gbtreekey2 | c |
| `public` | `gbtreekey2_out` | gbtreekey2 | cstring | c |
| `public` | `gbtreekey32_in` | cstring | gbtreekey32 | c |
| `public` | `gbtreekey32_out` | gbtreekey32 | cstring | c |
| `public` | `gbtreekey4_in` | cstring | gbtreekey4 | c |
| `public` | `gbtreekey4_out` | gbtreekey4 | cstring | c |
| `public` | `gbtreekey8_in` | cstring | gbtreekey8 | c |
| `public` | `gbtreekey8_out` | gbtreekey8 | cstring | c |
| `public` | `gbtreekey_var_in` | cstring | gbtreekey_var | c |
| `public` | `gbtreekey_var_out` | gbtreekey_var | cstring | c |
| `public` | `gen_random_bytes` | integer | bytea | c |
| `public` | `gen_random_uuid` |  | uuid | c |
| `public` | `gen_salt` | text, integer | text | c |
| `public` | `gen_salt` | text | text | c |
| `public` | `gin_extract_query_trgm` | text, internal, smallint, internal, inte | internal | c |
| `public` | `gin_extract_value_trgm` | text, internal | internal | c |
| `public` | `gin_trgm_consistent` | internal, smallint, text, integer, inter | boolean | c |
| `public` | `gin_trgm_triconsistent` | internal, smallint, text, integer, inter | "char" | c |
| `public` | `gtrgm_compress` | internal | internal | c |
| `public` | `gtrgm_consistent` | internal, text, smallint, oid, internal | boolean | c |
| `public` | `gtrgm_decompress` | internal | internal | c |
| `public` | `gtrgm_distance` | internal, text, smallint, oid, internal | double precision | c |
| `public` | `gtrgm_in` | cstring | gtrgm | c |
| `public` | `gtrgm_options` | internal | void | c |
| `public` | `gtrgm_out` | gtrgm | cstring | c |
| `public` | `gtrgm_penalty` | internal, internal, internal | internal | c |
| `public` | `gtrgm_picksplit` | internal, internal | internal | c |
| `public` | `gtrgm_same` | gtrgm, gtrgm, internal | internal | c |
| `public` | `gtrgm_union` | internal, internal | gtrgm | c |
| `public` | `hmac` | bytea, bytea, text | bytea | c |
| `public` | `hmac` | text, text, text | bytea | c |
| `public` | `int2_dist` | smallint, smallint | smallint | c |
| `public` | `int4_dist` | integer, integer | integer | c |
| `public` | `int8_dist` | bigint, bigint | bigint | c |
| `public` | `interval_dist` | interval, interval | interval | c |
| `public` | `oid_dist` | oid, oid | oid | c |
| `public` | `pgp_armor_headers` | text, OUT key text, OUT value text | SETOF record | c |
| `public` | `pgp_key_id` | bytea | text | c |
| `public` | `pgp_pub_decrypt` | bytea, bytea, text | text | c |
| `public` | `pgp_pub_decrypt` | bytea, bytea | text | c |
| `public` | `pgp_pub_decrypt` | bytea, bytea, text, text | text | c |
| `public` | `pgp_pub_decrypt_bytea` | bytea, bytea, text | bytea | c |
| `public` | `pgp_pub_decrypt_bytea` | bytea, bytea | bytea | c |
| `public` | `pgp_pub_decrypt_bytea` | bytea, bytea, text, text | bytea | c |
| `public` | `pgp_pub_encrypt` | text, bytea | bytea | c |
| `public` | `pgp_pub_encrypt` | text, bytea, text | bytea | c |
| `public` | `pgp_pub_encrypt_bytea` | bytea, bytea, text | bytea | c |
| `public` | `pgp_pub_encrypt_bytea` | bytea, bytea | bytea | c |
| `public` | `pgp_sym_decrypt` | bytea, text | text | c |
| `public` | `pgp_sym_decrypt` | bytea, text, text | text | c |
| `public` | `pgp_sym_decrypt_bytea` | bytea, text, text | bytea | c |
| `public` | `pgp_sym_decrypt_bytea` | bytea, text | bytea | c |
| `public` | `pgp_sym_encrypt` | text, text, text | bytea | c |
| `public` | `pgp_sym_encrypt` | text, text | bytea | c |
| `public` | `pgp_sym_encrypt_bytea` | bytea, text | bytea | c |
| `public` | `pgp_sym_encrypt_bytea` | bytea, text, text | bytea | c |
| `public` | `set_limit` | real | real | c |
| `public` | `show_limit` |  | real | c |
| `public` | `show_trgm` | text | text[] | c |
| `public` | `similarity` | text, text | real | c |
| `public` | `similarity_dist` | text, text | real | c |
| `public` | `similarity_op` | text, text | boolean | c |
| `public` | `strict_word_similarity` | text, text | real | c |
| `public` | `strict_word_similarity_commutator_op` | text, text | boolean | c |
| `public` | `strict_word_similarity_dist_commutator_op` | text, text | real | c |
| `public` | `strict_word_similarity_dist_op` | text, text | real | c |
| `public` | `strict_word_similarity_op` | text, text | boolean | c |
| `public` | `time_dist` | time without time zone, time without tim | interval | c |
| `public` | `ts_dist` | timestamp without time zone, timestamp w | interval | c |
| `public` | `tstz_dist` | timestamp with time zone, timestamp with | interval | c |
| `public` | `unaccent` | text | text | c |
| `public` | `unaccent` | regdictionary, text | text | c |
| `public` | `unaccent_init` | internal | internal | c |
| `public` | `unaccent_lexize` | internal, internal, internal, internal | internal | c |
| `public` | `uuid_generate_v1` |  | uuid | c |
| `public` | `uuid_generate_v1mc` |  | uuid | c |
| `public` | `uuid_generate_v3` | namespace uuid, name text | uuid | c |
| `public` | `uuid_generate_v4` |  | uuid | c |
| `public` | `uuid_generate_v5` | namespace uuid, name text | uuid | c |
| `public` | `uuid_nil` |  | uuid | c |
| `public` | `uuid_ns_dns` |  | uuid | c |
| `public` | `uuid_ns_oid` |  | uuid | c |
| `public` | `uuid_ns_url` |  | uuid | c |
| `public` | `uuid_ns_x500` |  | uuid | c |
| `public` | `word_similarity` | text, text | real | c |
| `public` | `word_similarity_commutator_op` | text, text | boolean | c |
| `public` | `word_similarity_dist_commutator_op` | text, text | real | c |
| `public` | `word_similarity_dist_op` | text, text | real | c |
| `public` | `word_similarity_op` | text, text | boolean | c |

## 🗂️ Tables partitionnées

### payroll.idx_payroll_code

**Stratégie** : 

**Partitions** :

- `payroll_transactions_2024_pay_code_idx` : 
- `payroll_transactions_2025_pay_code_idx` : 
- `payroll_transactions_2026_pay_code_idx` : 

### payroll.idx_payroll_date

**Stratégie** : 

**Partitions** :

- `payroll_transactions_2024_pay_date_idx` : 
- `payroll_transactions_2025_pay_date_idx` : 
- `payroll_transactions_2026_pay_date_idx` : 

### payroll.idx_payroll_employee

**Stratégie** : 

**Partitions** :

- `payroll_transactions_2024_employee_id_idx` : 
- `payroll_transactions_2025_employee_id_idx` : 
- `payroll_transactions_2026_employee_id_idx` : 

### payroll.idx_payroll_employee_date

**Stratégie** : 

**Partitions** :

- `payroll_transactions_2024_employee_id_pay_date_idx` : 
- `payroll_transactions_2025_employee_id_pay_date_idx` : 
- `payroll_transactions_2026_employee_id_pay_date_idx` : 

### payroll.idx_payroll_period

**Stratégie** : 

**Partitions** :

- `payroll_transactions_2024_pay_year_pay_month_idx` : 
- `payroll_transactions_2025_pay_year_pay_month_idx` : 
- `payroll_transactions_2026_pay_year_pay_month_idx` : 

### payroll.payroll_transactions

**Stratégie** : RANGE (pay_date)

**Partitions** :

- `payroll_transactions_2024` : FOR VALUES FROM ('2024-01-01') TO ('2025-01-01')
- `payroll_transactions_2025` : FOR VALUES FROM ('2025-01-01') TO ('2026-01-01')
- `payroll_transactions_2026` : FOR VALUES FROM ('2026-01-01') TO ('2027-01-01')

### payroll.pk_payroll_transactions

**Stratégie** : 

**Partitions** :

- `payroll_transactions_2024_pkey` : 
- `payroll_transactions_2025_pkey` : 
- `payroll_transactions_2026_pkey` : 

## 🔐 Privilèges (échantillon)

| Type | Schéma | Objet | Bénéficiaire | Privilège |
|------|--------|-------|--------------|----------|
| TABLE | public | alembic_version | payroll_owner | INSERT |
| TABLE | public | alembic_version | payroll_owner | SELECT |
| TABLE | public | alembic_version | payroll_owner | UPDATE |
| TABLE | public | alembic_version | payroll_owner | DELETE |
| TABLE | public | alembic_version | payroll_owner | TRUNCATE |
| TABLE | public | alembic_version | payroll_owner | REFERENCES |
| TABLE | public | alembic_version | payroll_owner | TRIGGER |
| TABLE | public | alembic_version | payroll_owner | MAINTAIN |
| TABLE | public | alembic_version | payroll_app | SELECT |
| TABLE | core | budget_posts | payroll_user | INSERT |
| TABLE | core | budget_posts | payroll_user | SELECT |
| TABLE | core | budget_posts | payroll_user | UPDATE |
| TABLE | core | budget_posts | payroll_user | DELETE |
| TABLE | core | budget_posts | payroll_user | TRUNCATE |
| TABLE | core | budget_posts | payroll_user | REFERENCES |
| TABLE | core | budget_posts | payroll_user | TRIGGER |
| TABLE | core | budget_posts | payroll_user | MAINTAIN |
| TABLE | core | budget_posts | payroll_app | INSERT |
| TABLE | core | budget_posts | payroll_app | SELECT |
| TABLE | core | budget_posts | payroll_app | UPDATE |
| TABLE | core | budget_posts | payroll_app | DELETE |
| TABLE | core | budget_posts | payroll_ro | SELECT |
| TABLE | core | employee_job_history | payroll_user | INSERT |
| TABLE | core | employee_job_history | payroll_user | SELECT |
| TABLE | core | employee_job_history | payroll_user | UPDATE |
| TABLE | core | employee_job_history | payroll_user | DELETE |
| TABLE | core | employee_job_history | payroll_user | TRUNCATE |
| TABLE | core | employee_job_history | payroll_user | REFERENCES |
| TABLE | core | employee_job_history | payroll_user | TRIGGER |
| TABLE | core | employee_job_history | payroll_user | MAINTAIN |
| TABLE | core | employee_job_history | payroll_app | INSERT |
| TABLE | core | employee_job_history | payroll_app | SELECT |
| TABLE | core | employee_job_history | payroll_app | UPDATE |
| TABLE | core | employee_job_history | payroll_app | DELETE |
| TABLE | core | employee_job_history | payroll_ro | SELECT |
| TABLE | core | employees | postgres | INSERT |
| TABLE | core | employees | postgres | SELECT |
| TABLE | core | employees | postgres | UPDATE |
| TABLE | core | employees | postgres | DELETE |
| TABLE | core | employees | postgres | TRUNCATE |
| TABLE | core | employees | postgres | REFERENCES |
| TABLE | core | employees | postgres | TRIGGER |
| TABLE | core | employees | postgres | MAINTAIN |
| TABLE | core | employees | payroll_app | INSERT |
| TABLE | core | employees | payroll_app | SELECT |
| TABLE | core | employees | payroll_app | UPDATE |
| TABLE | core | employees | payroll_app | DELETE |
| TABLE | core | employees | payroll_ro | SELECT |
| TABLE | core | job_categories | payroll_user | INSERT |
| TABLE | core | job_categories | payroll_user | SELECT |

## ✅ Résumé

- **Tables** : 23
- **Colonnes** : 249
- **Contraintes** : 49
- **Index** : 92
- **Clés étrangères** : 0
- **Vues** : 4
- **Fonctions** : 278
- **Partitions** : 21
- **Privilèges** : 268

