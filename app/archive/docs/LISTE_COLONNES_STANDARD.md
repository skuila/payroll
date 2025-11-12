# 📋 STANDARDISATION DES COLONNES EXCEL

## ✅ RECOMMANDATION : Utiliser les noms normalisés directement

Vous pouvez **standardiser** votre fichier Excel en utilisant directement les noms normalisés dans les en-têtes. Le système accepte **les deux formats**.

---

## 📊 FORMAT STANDARD (Recommandé)

Utilisez ces noms exacts dans votre fichier Excel :

1. **numero_ligne**
2. **categorie_emploi**
3. **code_emploi**
4. **titre_emploi**
5. **date_paie**
6. **matricule**
7. **nom_employe**
8. **categorie_paie**
9. **code_paie**
10. **description_code_paie**
11. **poste_budgetaire**
12. **description_poste_budgetaire**
13. **montant_employe**
14. **part_employeur**
15. **montant_combine**

### ✅ Avantages :
- ✅ Pas d'espaces dans les noms
- ✅ Pas d'accents à gérer
- ✅ Format cohérent et standardisé
- ✅ Compatible avec la base de données
- ✅ Plus facile à maintenir

---

## 📊 FORMAT ANCIEN (Compatibilité)

Si vous préférez garder les anciens noms Excel (avec espaces et accents), c'est aussi supporté :

1. **N de ligne**
2. **Categorie d'emploi**
3. **code emploi**
4. **titre d'emploi**
5. **date de paie**
6. **matricule**
7. **employé**
8. **categorie de paie**
9. **code de paie**
10. **desc code de paie**
11. **poste Budgetaire**
12. **desc poste Budgétaire**
13. **montant ** (avec espace en fin)
14. **part employeur**
15. **Mnt/Cmb**

---

## 🔄 MAPPING AUTOMATIQUE

Le système détecte automatiquement le format utilisé et applique le mapping si nécessaire :

| Format Excel (ancien) | → | Format Standard (base) |
|-----------------------|---|------------------------|
| `N de ligne` | → | `numero_ligne` |
| `Categorie d'emploi` | → | `categorie_emploi` |
| `code emploi` | → | `code_emploi` |
| `titre d'emploi` | → | `titre_emploi` |
| `date de paie` | → | `date_paie` |
| `matricule` | → | `matricule` |
| `employé` | → | `nom_employe` |
| `categorie de paie` | → | `categorie_paie` |
| `code de paie` | → | `code_paie` |
| `desc code de paie` | → | `description_code_paie` |
| `poste Budgetaire` | → | `poste_budgetaire` |
| `desc poste Budgétaire` | → | `description_poste_budgetaire` |
| `montant ` | → | `montant_employe` |
| `part employeur` | → | `part_employeur` |
| `Mnt/Cmb` | → | `montant_combine` |

---

## 💡 RECOMMANDATION FINALE

**Utilisez le FORMAT STANDARD** (noms normalisés) dans vos fichiers Excel :
- Plus propre
- Plus facile à maintenir
- Compatible directement avec la base
- Pas besoin de mapping dans la plupart des cas

**Aucune modification de code n'est nécessaire** - le système détecte automatiquement le format et fonctionne avec les deux !

---

## 📝 Exemple de fichier Excel standardisé

Vos en-têtes de colonnes devraient être :

```
numero_ligne | categorie_emploi | code_emploi | titre_emploi | date_paie | matricule | nom_employe | categorie_paie | code_paie | description_code_paie | poste_budgetaire | description_poste_budgetaire | montant_employe | part_employeur | montant_combine
```

C'est tout ! Simple et standardisé. 🎯






