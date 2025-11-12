# 🔧 CORRECTION : Valeur négative dans le graphique

## ❌ PROBLÈME

Votre graphique affiche **-538402.22** (négatif) au lieu d'un montant positif.

## 🔍 EXPLICATION

Dans la vue `v_payroll_par_periode`, la colonne `total_net` utilise cette règle:
- **Si `categorie_paie = 'Gains'`** → garde le signe (positif)
- **Sinon** (déductions, taxes, etc.) → **inverse le signe** (multiplie par -1)

Donc `total_net` peut être **négatif** si les déductions sont supérieures aux gains.

---

## ✅ SOLUTIONS

### Solution 1 : Utiliser `total_employe` au lieu de `total_net` (RECOMMANDÉ)

**Pour voir les salaires bruts (positifs):**

1. **Dans Metrics**, supprimez `SUM(total_net)`
2. **Ajoutez** `SUM(total_employe)` à la place
3. **Recréez le chart**

**`total_employe`** = somme brute des montants employé (toujours positif)

---

### Solution 2 : Utiliser la valeur absolue de `total_net`

**Pour voir le montant net en valeur absolue:**

1. **Dans Metrics**, vous ne pouvez peut-être pas faire ABS directement
2. **Solution alternative**: Utiliser `total_employe` (voir Solution 1)

---

### Solution 3 : Utiliser `total_combine` (salaires bruts + part employeur)

**Pour voir le coût total:**

1. **Dans Metrics**, remplacez par `SUM(total_combine)`
2. Cela affichera les salaires combinés (employé + employeur)

---

## 🎯 QUELLE MÉTRIQUE CHOISIR?

| Métrique | Ce qu'elle montre | Signe |
|----------|-------------------|-------|
| `total_net` | Net après déductions (selon règle métier) | Peut être négatif |
| `total_employe` | Salaire brut employé (avant déductions) | Toujours positif |
| `total_employeur` | Part employeur (cotisations, etc.) | Toujours positif |
| `total_combine` | Total employé + employeur | Toujours positif |

---

## 📋 ACTION IMMÉDIATE

**Pour votre graphique d'évolution des salaires:**

### Option A : Salaires bruts (recommandé)
- **Metric**: `SUM(total_employe)`
- ✅ Montrera les salaires bruts versés aux employés

### Option B : Coût total employeur
- **Metric**: `SUM(total_combine)`
- ✅ Montrera le coût total (employé + cotisations employeur)

---

## 🔧 COMMENT CHANGER

1. **Dans Metrics**, cliquez sur `SUM(total_net)`
2. **Supprimez-le** (X ou bouton supprimer)
3. **Ajoutez** `total_employe`
4. **Sélectionnez** l'agrégation **SUM**
5. **Recréez le chart**

---

## 💡 COMPRÉHENSION

**Pourquoi `total_net` est négatif?**

- `total_net` = Gains - Déductions (avec inversion de signe pour les déductions)
- Si les déductions sont > gains → résultat négatif
- C'est normal selon la logique métier, mais pour un graphique d'évolution, vous voulez probablement voir les **salaires bruts** (`total_employe`)

---

**Recommandation: Utilisez `SUM(total_employe)` pour avoir des valeurs positives!**





