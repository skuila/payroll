# ⚡ FICHE RAPIDE : CRÉATION DES 5 DATASETS

## 📋 RÉSUMÉ EN 5 ÉTAPES PAR DATASET

Pour **chaque** dataset (répéter 5 fois):

1. **Data** → **Datasets** → **+ Dataset**
2. **Choisir**: Database + Schema `payroll` + Table `v_payroll_XXX`
3. **Columns** → Marquer les dates comme **Is temporal** ✅
4. **Vérifier** les NUMERIC sont bien NUMERIC
5. **Save** avec le nom `v_payroll_XXX`

---

## 📝 LISTE DES 5 DATASETS À CRÉER

| # | Dataset | Table | Colonnes DATE | Colonnes NUMERIC |
|---|---------|-------|---------------|------------------|
| 1 | `v_payroll_detail` | `v_payroll_detail` | `date_paie`, `mois_paie`, `annee_paie` | `montant_employe`, `part_employeur`, `montant_combine`, `net` |
| 2 | `v_payroll_par_periode` | `v_payroll_par_periode` | `date_paie`, `mois_paie`, `annee_paie` | `total_employe`, `total_employeur`, `total_combine`, `total_net` |
| 3 | `v_payroll_par_budget` | `v_payroll_par_budget` | `date_paie`, `mois_paie` | `total_employe`, `total_employeur`, `total_combine`, `total_net` |
| 4 | `v_payroll_par_code` | `v_payroll_par_code` | `date_paie`, `mois_paie` | `total_employe`, `total_employeur`, `total_combine`, `total_net` |
| 5 | `v_payroll_kpi` | `v_payroll_kpi` | `date_min`, `date_max` | `total_employe`, `total_employeur`, `total_combine`, `total_net`, `nb_*` |

---

## ✅ CHECKLIST RAPIDE

Pour chaque dataset, cocher:

- [ ] Dataset créé avec le bon nom
- [ ] Colonnes DATE marquées "Is temporal"
- [ ] Colonnes NUMERIC bien en NUMERIC
- [ ] Dataset sauvegardé

---

## 🔧 SI PROBLÈME

**Type incorrect?**
→ Columns → Cliquer sur la colonne → Changer le type → Save

**Colonnes manquantes?**
→ Menu (3 points) → Sync columns from source

---

**Guide détaillé**: Voir `GUIDE_CREATION_MANUEL_DATASETS.md`





