# Contexte — Duplication x9 du total net par employé

## Symptôme
- Le total net par employé est multiplié par 9 dans l’UI (DataTables), alors que la base retourne des montants corrects.

## Causes probables
1) Explosion de cardinalité: JOIN non agrégée sur `paie.stg_paie_transactions` (ancienne requête UI).
2) Multi-initialisation DataTables: la même table se recharge plusieurs fois (duplication des lignes).

## Requête correcte (UI)
- Net depuis `payroll.payroll_transactions` agrégé par matricule (CTE `agg`).
- `stg` agrégée séparément (MAX par matricule) pour Catégorie/Titre uniquement, puis `LEFT JOIN` sur le matricule normalisé.

## Pipeline DataTables attendu (natif)
- ajax natif: `ajax: function(req, cb){ cb({ data: rows }) }`
- `stateSave: false`, `destroy: true`, rechargement via `dt.ajax.reload()`
- Footer et exports: somme sur la donnée numérique (pas le texte formaté)

## Vérifications (voir `verify_cte.sql`)
- Comparer total DB vs footer UI sur la même date.
- Contrôler `nb_lignes_stg` pour détecter une explosion de jointure (ex: 9 lignes pour un matricule/date).
- Confirmer la base active (current_database).

## Fichiers inclus
- `web/tabler/employees.html`
- `web/tabler/js/datatables-helper.js`
- `payroll_app_qt_Version4.py`
- `verify_cte.sql`

## Résumé de la solution proposée
- Côté SQL UI: conserver la CTE `agg` (net par matricule) et joindre une `stg` pré-agrégée (MAX par matricule). Ne jamais sommer avec `stg` non agrégée.
- Côté DataTables: utiliser l’ajax natif, désactiver `stateSave`, éviter les `rows.add()`/`clear()` manuels; recharger uniquement par `dt.ajax.reload()`.
- Anti-cache: versionner les includes et recharger `index.html` avec un paramètre temporel pour s’assurer que la bonne version est servie.


