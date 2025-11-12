## datatables-fix (duplication ×9) — 2025-11-07

### Pourquoi
- La vue `paie.v_kpi_par_employe_mois` joignait directement `paie.stg_paie_transactions` par `source_file/source_row_no` puis agrégeait, provoquant une explosion de cardinalité (×9) et un net incorrect.
- Côté UI, des ré-initialisations pouvaient survenir en cas d’appels répétés, risquant des rechargements multiples.

### Ce qui a changé
1) SQL
- Vue `paie.v_kpi_par_employe_mois` réécrite avec deux CTE:
  - `agg`: agrégation EXCLUSIVE sur `payroll.payroll_transactions` par `(employee_id, pay_date)` pour calculer `gains_brut`, `deductions`, `net`, `part_employeur`.
  - `stg_agg`: agrégation séparée sur `paie.stg_paie_transactions` par `(matricule, date_paie)` pour les descripteurs (`nom_prenom`, `categorie_emploi`, `titre_emploi`, `poste_budgetaire`) via `MAX()`.
  - Jointure finale `agg ↔ stg_agg` sur `(date_paie, matricule)` via `core.employees` (mapping `employee_id` → `matricule_norm|matricule`).
  - Interdictions respectées: plus de jointure `source_file/source_row_no`, aucun `SUM()` après la jointure, pas de `GROUP BY` sur les colonnes `stg`.
  - Compatibilité: colonnes de sortie conservées (`periode_paie`, `date_paie`, `matricule`, `nom_prenom`, `categorie_emploi`, `titre_emploi`, `poste_budgetaire`, `gains_brut`, `deductions`, `net`, `part_employeur`, `cout_total`).

2) UI
- `web/tabler/js/datatables-helper.js`: ajout d’un registre d’instances pour empêcher la double init. Si la table existe déjà, on renvoie l’instance et on fait un `ajax.reload()` au lieu de ré-initialiser.
- `web/tabler/employees.js`: garde-fou `listenersBound` pour éviter d’attacher plusieurs fois les écouteurs; log `[Employees] init` affiché une seule fois.

### Comment tester

SQL (psql)
1. Vérifier cardinalité staging (ex. `2025-08-28`):
   ```sql
   SELECT matricule, COUNT(*) nb
   FROM paie.stg_paie_transactions
   WHERE date_paie = DATE '2025-08-28' AND COALESCE(is_valid, TRUE) = TRUE
   GROUP BY matricule
   ORDER BY nb DESC
   LIMIT 10;
   ```
   - Attendu: la vue finale ne multiplie pas les lignes; `stg_agg` fournit 1 ligne par `(matricule, date)`.

2. Total net cohérent:
   ```sql
   -- Contrôle vérité (transactions)
   WITH agg AS (
     SELECT employee_id, SUM(amount_cents)/100.0 AS net
     FROM payroll.payroll_transactions
     WHERE pay_date = DATE '2025-08-28'
     GROUP BY employee_id
   )
   SELECT SUM(net) FROM agg;

   -- Vue UI
   SELECT SUM(net) FROM paie.v_kpi_par_employe_mois
   WHERE date_paie = DATE '2025-08-28';
   ```
   - Attendu: les deux sommes sont égales.

UI
1. Ouvrir la page Employés dans l’appli.
2. Observer la console:
   - `[Employees] init` → 1 seule fois.
   - Chaque changement de période/filtre déclenche un seul reload (pas de rafale).
3. Footer total = total SQL de la date (pas de ×9).

### Fichiers modifiés
- `migration/014_unicite_matricule_et_vues_kpi.sql` (refactor `v_kpi_par_employe_mois`)
- `web/tabler/js/datatables-helper.js` (anti double init + reload propre)
- `web/tabler/employees.js` (écouteurs attachés une seule fois + log init)

### Impacts
- Zéro changement de nom de colonnes côté vue; compatibilité maintenue pour UI/exports/graphes.



