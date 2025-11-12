# Test de la page Employés

## Méthode 1 : Script de test dédié

**Dans PowerShell :**
```powershell
python test_employees_correct.py
```

La page employés s'ouvrira automatiquement après 0.5 seconde.

---

## Méthode 2 : Application complète

**1. Lancer l'application principale :**
```powershell
python payroll_app_qt_Version4.py
```

**2. Dans l'application :**
- Cliquez sur l'icône **👤 Employés** dans la barre d'outils en haut
- OU utilisez le menu latéral pour accéder à la page Employés

---

## Vérifications

### ✅ Si tout fonctionne :
- La page employés s'affiche
- Un tableau DataTables apparaît
- Les employés sont listés avec leurs informations

### ❌ Si le tableau est vide :

**Ouvrez la console développeur :**
1. Dans l'application, appuyez sur **F12**
2. Allez dans l'onglet **Console**
3. Cherchez les messages préfixés `[Employees]`

**Messages attendus :**
```
[Employees] Script chargé
[Employees] DOMContentLoaded
[Employees] QWebChannel disponible, connexion...
[Employees] AppBridge connecté
[Employees] Date initialisée: YYYY-MM-DD
[Employees] SQL pour date: YYYY-MM-DD
[Employees] loadTable() appelée
[Employees] DataTables disponible
[Employees] Initialisation DataTable avec AppBridge
[Employees] DataTable initialisée avec succès
[Employees] Affichage: X lignes, total: XXXXX
```

**Si vous voyez une erreur :**
- Notez le message d'erreur exact
- Vérifiez que la base de données contient des données pour la date sélectionnée

---

## Données de test

**Vérifier s'il y a des employés dans la DB :**

Dans psql :
```sql
-- Connexion
psql -U payrollanalyzer_user -d payrollanalyzer_db

-- Vérifier les périodes disponibles
SELECT DISTINCT pay_date 
FROM payroll.payroll_transactions 
ORDER BY pay_date DESC 
LIMIT 10;

-- Compter les employés pour une période
SELECT COUNT(DISTINCT employee_id) 
FROM payroll.payroll_transactions 
WHERE pay_date = '2025-08-28';  -- Ajustez la date

-- Voir un échantillon d'employés
SELECT 
  e.nom_complet,
  e.matricule_norm,
  SUM(t.amount_cents)/100.0 AS total
FROM payroll.payroll_transactions t
JOIN core.employees e ON e.employee_id = t.employee_id
WHERE t.pay_date = '2025-08-28'  -- Ajustez la date
GROUP BY e.nom_complet, e.matricule_norm
LIMIT 5;
```

Si aucune donnée n'existe, vous devez d'abord importer des fichiers de paie.

---

## En cas de problème persistant

Envoyez-moi :
1. Les messages de la console `[Employees]`
2. Les erreurs JavaScript (en rouge)
3. La date de paie sélectionnée
4. Le résultat de la requête SQL de vérification ci-dessus

