# 📋 RÉSUMÉ EXÉCUTIF - INCOHÉRENCES DÉTECTÉES

## 🎯 24 PROBLÈMES CRITIQUES IDENTIFIÉS

### ❌ PROBLÈMES MAJEURS

1. **Références à table inexistante** (3 erreurs)
   - Les vues SQL utilisent `payroll.employees` au lieu de `core.employees`
   - Les vues référencent `e.categorie_emploi` et `e.poste_budgetaire` mais ces colonnes n'existent pas dans `core.employees`

2. **Incohérences de noms de colonnes** (21 erreurs)
   - Les vues ont `periode_paie` mais l'API attend parfois `periode`
   - Les vues ont `cout_employeur_pnl` mais le contrat standard demande `cout_total`
   - Plusieurs colonnes standard manquantes dans différentes vues

---

## 🔍 ORIGINE DES DONNÉES

**D'après l'analyse du code** :
- `categorie_emploi` vient des fichiers Excel : colonne "Categorie d'emploi"
- `poste_budgetaire` vient des fichiers Excel : colonne "Poste Budgetaire"
- Ces données sont dans les **transactions** (pas dans les employés eux-mêmes)
- Un employé peut avoir différentes catégories/postes selon les périodes

**Solution** : Extraire ces données depuis `payroll.payroll_transactions` ou les tables de staging, pas depuis `core.employees`.

---

## ✅ ACTIONS IMMÉDIATES REQUISES

### 1. Corriger les JOINs dans `admin_create_kpi_views.sql`

**Lignes à modifier** : 88, 139

```sql
-- REMPLACER
LEFT JOIN payroll.employees e ON t.employee_id = e.employee_id

-- PAR
LEFT JOIN core.employees e ON t.employee_id = e.employee_id
```

### 2. Extraire categorie_emploi et poste_budgetaire depuis les transactions

Au lieu de :
```sql
COALESCE(e.categorie_emploi, 'Non défini') as categorie_emploi
```

Utiliser :
```sql
-- Si dans payroll_transactions, extraire depuis là
-- Sinon, depuis une table de staging ou référence
```

### 3. Harmoniser les noms de colonnes

Ajouter des alias dans toutes les vues :
- `periode` (alias de `periode_paie`)
- `cout_total` (alias de `cout_employeur_pnl` où nécessaire)

---

## 📊 FICHIERS À MODIFIER

1. ✅ `scripts/admin_create_kpi_views.sql` - CORRIGER JOINs et colonnes
2. ✅ `api/routes/kpi.py` - Vérifier utilisation des colonnes
3. ⚠️ `core.employees` - Ne PAS ajouter categorie_emploi/poste_budgetaire (ce sont des attributs transactionnels)

---

## 📖 DOCUMENTATION COMPLÈTE

Voir le rapport détaillé : `RAPPORT_COHERENCE_COLONNES.md`

---

## 🔧 SCRIPT DE VÉRIFICATION

Ré-exécuter après corrections :
```cmd
python scripts\verification_coherence_complete.py
```

Objectif : `✅ Aucun problème détecté - Tout est cohérent!`

