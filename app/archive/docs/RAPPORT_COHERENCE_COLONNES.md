# 📋 RAPPORT DE VÉRIFICATION - COHÉRENCE DES COLONNES

**Date** : 2025-01-XX  
**Script** : `scripts/verification_coherence_complete.py`

## 🎯 RÉSUMÉ EXÉCUTIF

**24 problèmes critiques** détectés entre l'application, la base de données et les KPI/API.

---

## ❌ PROBLÈMES CRITIQUES

### 1. **Références à la mauvaise table `payroll.employees`**

**Problème** : Les vues SQL référence `payroll.employees` au lieu de `core.employees`

**Fichiers concernés** :
- `scripts/admin_create_kpi_views.sql` (lignes 88, 139)

**Impact** : Les vues ne peuvent pas fonctionner car `payroll.employees` n'existe pas.

**Correction nécessaire** :
```sql
-- AVANT (incorrect)
LEFT JOIN payroll.employees e ON t.employee_id = e.employee_id

-- APRÈS (correct)
LEFT JOIN core.employees e ON t.employee_id = e.employee_id
```

---

### 2. **Colonnes manquantes dans `core.employees`**

**Problème** : Les vues utilisent `e.categorie_emploi` et `e.poste_budgetaire` mais ces colonnes n'existent pas dans `core.employees`.

**Colonnes actuelles de `core.employees`** :
- employee_id
- employee_key
- matricule_norm
- matricule_raw
- nom_norm
- prenom_norm
- nom_complet
- statut
- source_system
- created_at, updated_at, created_by, updated_by

**Colonnes manquantes** :
- ❌ `categorie_emploi`
- ❌ `poste_budgetaire`

**Vues affectées** :
- `paie.v_kpi_par_categorie_emploi` (ligne 73)
- `paie.v_kpi_par_poste_budgetaire` (ligne 124)

**Solutions possibles** :
1. **Ajouter les colonnes à `core.employees`** (si les données viennent des employés)
2. **Faire un JOIN avec une autre table** (si les données viennent d'ailleurs)
3. **Extraire depuis `payroll_transactions`** (si ces infos sont dans les transactions)

---

### 3. **Incohérences de noms de colonnes dans les vues**

#### 3.1. Colonne `periode` vs `periode_paie`

**Problème** : Les vues définissent `periode_paie` mais l'API attend parfois `periode`.

**Vues concernées** :
- `paie.v_kpi_periode` : a `periode_paie`, manque `periode`
- `paie.v_kpi_par_categorie_emploi` : a `periode_paie`, manque `periode`
- `paie.v_kpi_par_code_paie` : a `periode_paie`, manque `periode`
- `paie.v_kpi_par_poste_budgetaire` : a `periode_paie`, manque `periode`
- `paie.v_kpi_par_employe_periode` : a `periode_paie`, manque `periode`

**Usage dans l'API** (`api/routes/kpi.py`) :
- Ligne 139 : utilise `periode_paie` (correct)
- Ligne 121 : utilise `date_paie as periode` (conflit)

**Solution** : Les vues doivent avoir les deux colonnes :
```sql
TO_CHAR(pay_date, 'YYYY-MM') as periode_paie,
TO_CHAR(pay_date, 'YYYY-MM') as periode,  -- Alias pour compatibilité
```

---

#### 3.2. Colonne `cout_total` vs `cout_employeur_pnl`

**Problème** : Mélange de noms pour le coût total employeur.

**État actuel** :
- `paie.v_kpi_periode` : a `cout_employeur_pnl`, manque `cout_total`
- `paie.v_kpi_par_poste_budgetaire` : a `cout_total` ✅

**Usage dans l'API** :
- Ligne 126 : utilise `cout_employeur_pnl as cout_total_employeur`
- Ligne 144 : utilise `cout_employeur_pnl`
- Ligne 186 : utilise `cout_employeur_pnl as cout_total_employeur`
- Ligne 266 : utilise `cout_total as cout_total_employeur`

**Solution** : Harmoniser toutes les vues pour avoir `cout_total` et ajouter un alias :
```sql
cout_total,
cout_total as cout_employeur_pnl  -- Alias pour compatibilité API
```

---

#### 3.3. Colonnes manquantes dans `v_kpi_par_code_paie`

**Problème** : La vue `paie.v_kpi_par_code_paie` n'a pas le contrat de colonnes standard.

**Colonnes manquantes** :
- ❌ `periode` (a seulement `periode_paie`)
- ❌ `date_paie`
- ❌ `gains_brut`
- ❌ `net_a_payer`
- ❌ `nb_employes` (a `nb_employes_concernes` mais pas `nb_employes`)
- ❌ `cout_total`

**Colonnes actuelles** :
- periode_paie
- code_paie
- categorie_paie
- libelle_paie
- montant_total
- montant_moyen
- montant_min
- montant_max
- nb_transactions
- nb_employes_concernes
- part_employeur_total

**Solution** : Ajouter les colonnes standard ou créer des alias.

---

#### 3.4. Colonnes manquantes dans `v_kpi_par_employe_periode`

**Problème** : La vue a des noms de colonnes différents du contrat standard.

**Colonnes actuelles** :
- periode_paie (manque `periode`)
- date_paie ✅
- employe_id
- matricule
- nom_prenom
- gains (devrait être `gains_brut`)
- deductions (devrait être `deductions_net`)
- net ✅
- part_employeur ✅
- nb_transactions

**Colonnes manquantes** :
- ❌ `periode` (alias de `periode_paie`)
- ❌ `gains_brut` (a `gains`)
- ❌ `net_a_payer` (a `net`)
- ❌ `nb_employes` (pourrait être 1)
- ❌ `cout_total`

**Usage dans l'API** (`api/routes/kpi.py` ligne 311-321) :
```python
COALESCE(matricule, MD5(nom_prenom)) as employee_key,
nom_prenom as nom dirigeant_employe,
categorie_emploi,  # ← Manque dans la vue!
titre_emploi,      # ← Manque dans la vue!
poste_budgetaire,  # ← Manque dans la vue!
net,               # ✅ OK
cout_total         # ← Manque dans la vue!
```

---

#### 3.5. Colonnes manquantes dans `v_kpi_par_categorie_emploi`

**Colonnes manquantes** :
- ❌ `periode` (a seulement `periode_paie`)
- ❌ `date_paie`
- ❌ `cout_total`

---

### 4. **Incohérences dans l'API**

**Fichier** : `api/routes/kpi.py`

#### 4.1. Utilisation de `periode_paie` vs `periode`

- Ligne 139 : `periode_paie as periode` ✅
- Ligne  Медведь : utilise directement `periode_paie` dans WHERE ❌

#### 4.2. Utilisation de `cout_employeur_pnl` vs `cout_total`

- Ligne 126 : `cout_employeur_pnl as cout_total_employeur` ✅
- Ligne 144 : `cout_employeur_pnl` ✅
- Ligne 266 : `cout_total as cout_total_employeur` ⚠️ (incohérent)

#### 4.3. Utilisation de colonnes inexistantes

- Ligne 311-315 : L'API utilise `categorie_emploi`, `titre_emploi`, `poste_budgetaire` depuis `v_kpi_par_employe_periode` mais ces colonnes n'existent pas dans cette vue.

---

## 📊 TABLEAU RÉCAPITULATIF

| Vue | periode | date_paie | gains_brut | net_a_payer | nb_employes | cout_total | Statut |
|-----|---------|-----------|------------|-------------|-------------|------------|--------|
| `paie.v_kpi_periode` | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ⚠️ |
| `paie.v_kpi_par_categorie_emploi` | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `paie.v_kpi_par_code_paie` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `paie.v_kpi_par_poste_budgetaire` | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| `paie.v_kpi_par_employe_periode` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

**Légende** :
- ✅ Colonne présente
- ❌ Colonne manquante
- ⚠️ Partiellement conforme

---

## 🔧 PLAN DE CORRECTION RECOMMANDÉ

### Étape 1 : Corriger les références aux tables

1. **Corriger `admin_create_kpi_views.sql`** :
   - Remplacer toutes les références `payroll.employees` par `core.employees`

### Étape 2 : Résoudre le problème des colonnes manquantes

**Option A** : Ajouter `categorie_emploi` et `poste_budgetaire` à `core.employees`

```sql
ALTER TABLE core.employees 
ADD COLUMN IF NOT EXISTS categorie_emploi VARCHAR(100),
ADD COLUMN IF NOT EXISTS poste_budgetaire VARCHAR(100);
```

**Option B** : Extraire depuis `payroll_transactions` via un JOIN avec une table de staging ou de référence

### Étape 3 : Harmoniser les noms de colonnes dans toutes les vues

Ajouter les alias manquants dans toutes les vues :

```sql
-- Exemple pour v_kpi_periode
SELECT
    TO_CHAR(pay_date, 'YYYY-MM') as periode_paie,
    TO_CHAR(pay_date, 'YYYY-MM') as periode,  -- Alias
    TO_CHAR(pay_date, 'YYYY-MM-DD') as date_paie,
    -- ... autres colonnes ...
    cout_total,
    cout_total as cout_employeur_pnl  -- Alias pour compatibilité
FROM ...
```

### Étape 4 : Compléter les vues manquantes

- `v_kpi_par_code_paie` : Ajouter toutes les colonnes du contrat standard
- `v_kpi_par_employe_periode` : Ajouter `categorie_emploi`, `titre_emploi`, `poste_budgetaire`, `cout_total`

### Étape 5 : Vérifier l'API

Uniformiser l'utilisation des noms de colonnes dans `api/routes/kpi.py` :
- Utiliser `cout_total` partout (pas `cout_employeur_pnl`)
- Utiliser `periode` comme alias partout
- Vérifier que toutes les colonnes utilisées existent dans les vues

---

## ✅ VALIDATION POST-CORRECTION

Après corrections, ré-exécuter :
```cmd
python scripts\verification_coherence_complete.py
```

Le script doit retourner : `✅ Aucun problème détecté - Tout est cohérent!`

---

## 📌 NOTES IMPORTANTES

1. **Ne pas casser la rétro-compatibilité** : Ajouter des alias plutôt que renommer directement
2. **Tester chaque vue** après modification : `SELECT * FROM paie.v_kpi_XXX LIMIT 1;`
3. **Vérifier les requêtes API** après chaque modification de vue
4. **Documenter les changements** dans un fichier de migration

---

## 🔍 VUES À INSPECTER MANUELLEMENT

1. Vérifier d'où viennent `categorie_emploi` et `poste_budgetaire` :
   - Sont-ils dans les fichiers Excel originaux ?
   - Sont-ils dans `payroll_transactions` ?
   - Sont-ils dans une autre table de référence ?

2. Vérifier la logique métier :
   - Un employé peut-il avoir plusieurs catégories d'emploi ?
   - Un employé peut-il avoir plusieurs postes budgétaires ?
   - Ces informations changent-elles dans le temps ?

