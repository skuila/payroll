# Guide - Page Test DataTable

## ✅ Page créée : `teste.html`

Une nouvelle page DataTable native a été créée avec les colonnes :
- **Nom** de l'employé
- **Catégorie d'emploi**
- **Titre d'emploi**
- **Salaire net**

---

## 🚀 Comment y accéder

### Méthode 1 : Depuis l'accueil (recommandée)

**1. Lancez l'application :**
```powershell
python payroll_app_qt_Version4.py
```

**2. Dans le menu latéral gauche, cliquez sur :**
- **Test DataTable** (entre "Employés" et "Périodes")

---

### Méthode 2 : Script de test direct

```powershell
python test_page_teste.py
```

La page s'ouvrira automatiquement.

---

## 📊 Ce qui sera affiché

**Pour la période 2025-08-28 :**
- **295 employés** listés dans le tableau
- **Total de la masse salariale** : 538 402,22 $

**Exemple de données :**
```
Nom                    Catégorie        Titre                           Salaire net
Abdou, Annia          Soutien          Surveillants d'élèves            245,39 $
Adrienne, Terry       Soutien          Gardien/gardienne              1 252,20 $
Agasseau, Jessica     Soutien          Agent(e) de communication      1 574,16 $
...
```

---

## 🎯 Fonctionnalités

### ✅ Fonctionnalités disponibles :

1. **Recherche** : Cherchez un employé par nom, catégorie ou titre
2. **Tri** : Cliquez sur les en-têtes de colonnes pour trier
3. **Pagination** : Naviguez entre les pages (10, 25, 50, 100 lignes)
4. **Export** :
   - Excel (`.xlsx`)
   - CSV (`.csv`)
   - PDF (`.pdf`)
   - Impression
5. **Total dynamique** : Le pied de page affiche le total en temps réel

### 📅 Sélection de période :

- Utilisez le sélecteur de date en haut à droite
- Cliquez sur **Afficher** pour charger les données de cette période

---

## 🔧 Structure de la page

**Fichier** : `web/tabler/teste.html`

**Requête SQL utilisée :**
```sql
SELECT
  nom,
  categorie_emploi,
  titre_emploi,
  salaire_net
FROM (transactions + employés + staging)
WHERE pay_date = '2025-08-28'
ORDER BY nom
```

**Colonnes du tableau :**
1. Nom (chaîne)
2. Catégorie d'emploi (chaîne)
3. Titre d'emploi (chaîne)
4. Salaire net (monétaire, formaté en $ CAD)

---

## 🐛 En cas de problème

**Si le tableau est vide :**

1. Ouvrez la console (F12)
2. Regardez les messages `[Teste]`
3. Vérifiez que :
   - AppBridge est connecté
   - DataTables est chargé
   - La date sélectionnée contient des données

**Messages attendus dans la console :**
```
[Teste] Script charge
[Teste] DOMContentLoaded
[Teste] QWebChannel disponible, connexion...
[Teste] AppBridge connecte
[Teste] Derniere date: { rows: [['2025-08-28']] }
[Teste] Date initialisee: 2025-08-28
[Teste] SQL pour date: 2025-08-28
[Teste] DataTables disponible
[Teste] Initialisation DataTable
[Teste] DataTable initialisee avec succes
[Teste] Affichage: 295 lignes, total: 538402.22
```

**Si les données ne s'affichent pas :**
- Vérifiez que PostgreSQL est démarré
- Vérifiez que des données existent pour la date sélectionnée :
  ```powershell
  python verifier_donnees_employees.py
  ```

---

## 📝 Modifications possibles

**Pour ajouter une colonne :**

1. Modifiez la requête SQL dans `buildSql()`
2. Ajoutez la colonne dans la config DataTable :
   ```javascript
   { title: 'Nouvelle colonne', data: 4 }
   ```
3. Mettez à jour le `<thead>` du HTML

**Pour changer le nombre de lignes par défaut :**
```javascript
pageLength: 25  // au lieu de 10
```

**Pour désactiver l'export :**
```javascript
buttons: []  // au lieu de ['excelHtml5', 'csvHtml5', ...]
```

---

## ✅ Résumé

✓ Fichier créé : `web/tabler/teste.html`
✓ Lien ajouté dans le menu de l'accueil
✓ 4 colonnes : Nom, Catégorie, Titre, Salaire net
✓ DataTable natif avec recherche, tri, export
✓ Script de test : `test_page_teste.py`

**La page est prête à l'emploi ! 🎉**

