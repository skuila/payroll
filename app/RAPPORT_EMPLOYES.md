# RAPPORT TECHNIQUE – PAGE EMPLOYÉS

## 1. Résumé
- **Problème** : lécran employees.html (Tabler) naffiche aucun employé alors que core.employees contient 296 fiches.
- **Constat** : les requêtes utilisées par lUI se basent exclusivement sur payroll.payroll_transactions. Pour la période 2025-08-28, cette table ne contient plus aucune ligne.
- **Impact** : AppBridge.getEmployees() retourne une liste vide → la page reste vide avec un total net de 0.
- **Solution** : réimporter/restaurer les transactions manquantes ou adapter la logique pour afficher les fiches sans transactions.

## 2. Données mesurées
1. core.employees : 	otal_employees=296 (script .tmp_count_employees.py).
2. payroll.payroll_transactions : seules les dates 2025-11-10 et 2025-11-20 contiennent des transactions (.tmp_tx_dates.py).
3. Période 2025-08-28 : employees=0, 	otal_net=0.0 (.tmp_period_20250828.py).

## 3. Fichiers / responsabilités
- pp/web/tabler/employees.js : consomme la liste renvoyée par AppBridge.
- pp/payroll_app_qt_Version4.py (getEmployees) : joint payroll.pay_periods, payroll.payroll_transactions, core.employees. Sans transactions, aucun résultat.
- payroll.payroll_transactions / payroll.v_employee_period_summary : sources des données affichées.
- core.employees : contient 296 fiches mais nest pas interrogée directement pour lécran Tabler.

## 4. Cause racine
Suppression ou absence des transactions pour 2025-08-28 → la requête getEmployees ne trouve aucune ligne (JOIN internes). Le fait davoir 296 employés dans core.employees ne suffit pas : la page affiche uniquement ceux qui ont une paie dans la période sélectionnée.

## 5. Correction proposée
1. **Restaurer les transactions** de la période 2025-08-28 (réimport Excel, backup, ou annulation de la suppression). Lécran redeviendra fonctionnel dès que payroll.payroll_transactions contiendra des lignes pour cette date.
2. **Option UX** : modifier getEmployees pour utiliser un LEFT JOIN sur core.employees et indiquer quand une période ne possède pas de transactions (affichage dun message « aucune paie pour cette date »).
3. **Prévention** : ajouter un test qui vérifie quune période proposée dans lUI possède au moins une transaction.

## 6. Scripts utiles
- .tmp_count_employees.py : compte core.employees.
- .tmp_tx_dates.py : liste les dates présentes dans payroll.payroll_transactions.
- .tmp_period_20250828.py : calcule le nombre demployés et le total net dune date donnée.
- .tmp_check_page.py : vérifie la cohérence globale KPI/transactions.
