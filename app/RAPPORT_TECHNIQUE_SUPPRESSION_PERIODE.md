# RAPPORT TECHNIQUE : CORRECTION DE LA SUPPRESSION DE PÉRIODE

**Date :** 2025-11-13  
**Problème :** Erreur de contrainte de clé étrangère lors de la suppression d'une période  
**Fichier concerné :** `app/payroll_app_qt_Version4.py`

---

## 1. PROBLÈME IDENTIFIÉ

### 1.1 Erreur rencontrée

```
psycopg.errors.ForeignKeyViolation: UPDATE ou DELETE sur la table « employees » 
viole la contrainte de clé étrangère « fk_employee » de la table « payroll_transactions »

DETAIL: La clé (employee_id)=(1479) est toujours référencée à partir de la table « payroll_transactions ».
```

### 1.2 Contexte

L'erreur se produit lors de l'appel à la fonction `delete_period()` dans `app/payroll_app_qt_Version4.py` lors de la suppression de la période du 28 août 2025.

---

## 2. DESCRIPTION DU PROBLÈME

### 2.1 Architecture des contraintes

La table `payroll_transactions` possède une contrainte de clé étrangère :

```sql
CONSTRAINT fk_employee 
    FOREIGN KEY (employee_id) 
    REFERENCES core.employees(employee_id)
    ON DELETE RESTRICT
```

Cette contrainte avec `ON DELETE RESTRICT` empêche la suppression d'un employé s'il est référencé par des transactions.

### 2.2 Ordre de suppression actuel (INCORRECT)

Le code actuel tente de supprimer dans cet ordre :

1. ✅ Créer trace d'audit
2. ❌ **Supprimer les employés** (ligne 1025-1033)
3. ❌ **Supprimer les transactions** (ligne 1039-1042)
4. ✅ Supprimer la période

**Problème :** L'étape 2 tente de supprimer des employés qui sont encore référencés par des transactions (étape 3), ce qui viole la contrainte `fk_employee`.

---

## 3. RAISON DU PROBLÈME

### 3.1 Contrainte de clé étrangère

PostgreSQL empêche la suppression d'une ligne parente (employé) si des lignes enfants (transactions) la référencent encore. Avec `ON DELETE RESTRICT`, la suppression est bloquée immédiatement.

### 3.2 Logique métier

- Une période contient des transactions
- Les transactions référencent des employés
- Les employés peuvent avoir des transactions dans plusieurs périodes
- Pour supprimer une période, il faut :
  1. Supprimer les transactions de cette période
  2. Supprimer les employés qui n'ont plus aucune transaction (orphelins)
  3. Supprimer les données liées (imported_payroll_master, import_batches)
  4. Supprimer la période

---

## 4. FICHIERS À MODIFIER

### 4.1 Fichier principal

**Fichier :** `app/payroll_app_qt_Version4.py`  
**Fonction :** `delete_period(self, period_id: str)`  
**Lignes concernées :** 1023-1050

---

## 5. CODE ACTUEL (INCORRECT)

```python
# 2. Supprimer UNIQUEMENT les employés associés à cette période
# IMPORTANT: Faire AVANT de supprimer les transactions !
sql_delete_emp = """
    DELETE FROM core.employees 
    WHERE employee_id IN (
        SELECT DISTINCT employee_id 
        FROM payroll.payroll_transactions 
        WHERE pay_date = %(pay_date)s
    )
"""
self.provider.repo.run_query(sql_delete_emp, {"pay_date": pay_date})
print(f"  ✅ {count_employees} employés supprimés (liés à cette période uniquement)")

# 3. Supprimer les transactions
sql_delete_trans = (
    "DELETE FROM payroll.payroll_transactions WHERE pay_date = %(pay_date)s"
)
self.provider.repo.run_query(sql_delete_trans, {"pay_date": pay_date})
print(f"  ✅ {count_transactions} transactions supprimées")
```

**Problème :** Les employés sont supprimés avant les transactions, ce qui viole la contrainte.

---

## 6. CODE PROPOSÉ (CORRIGÉ)

### 6.1 Ordre de suppression correct

```python
# 2. Supprimer les transactions de cette période (AVANT les employés)
sql_delete_trans = (
    "DELETE FROM payroll.payroll_transactions WHERE pay_date = %(pay_date)s"
)
self.provider.repo.run_query(sql_delete_trans, {"pay_date": pay_date})
print(f"  ✅ {count_transactions} transactions supprimées")

# 3. Supprimer les données dans imported_payroll_master
sql_delete_imported = """
    DELETE FROM payroll.imported_payroll_master 
    WHERE date_paie = %(pay_date)s
"""
self.provider.repo.run_query(sql_delete_imported, {"pay_date": pay_date})
print("  ✅ Données supprimées dans imported_payroll_master")

# 4. Supprimer les batches d'import liés à cette période
sql_delete_batches = """
    DELETE FROM payroll.import_batches 
    WHERE pay_date = %(pay_date)s OR period_id = %(period_id)s
"""
self.provider.repo.run_query(sql_delete_batches, {
    "pay_date": pay_date,
    "period_id": period_id
})
print("  ✅ Batches d'import supprimés")

# 5. Supprimer les employés orphelins (qui n'ont plus aucune transaction)
sql_delete_emp = """
    DELETE FROM core.employees 
    WHERE employee_id NOT IN (
        SELECT DISTINCT employee_id 
        FROM payroll.payroll_transactions
        WHERE employee_id IS NOT NULL
    )
"""
result_emp = self.provider.repo.run_query(sql_delete_emp, {})
count_employees_deleted = result_emp if hasattr(result_emp, 'rowcount') else 0
print(f"  ✅ {count_employees_deleted} employés orphelins supprimés")
```

### 6.2 Code complet de la fonction (extrait modifié)

```python
def delete_period(self, period_id: str):
    """Supprime TOUT : période + transactions + employés + données liées (avec traçabilité)"""
    if not self.provider or not self.provider.repo:
        return json.dumps({"success": False, "error": "DB non disponible"})

    try:
        print(f"🗑️  Suppression COMPLÈTE de la période ID: {period_id}...")

        # Récupérer les infos de la période avant suppression
        sql_info = """
        SELECT pay_date::text, pay_year, pay_month, status, 
               period_seq_in_year, created_at, closed_at
        FROM payroll.pay_periods 
        WHERE period_id = %(period_id)s
        """
        info_result = self.provider.repo.run_query(
            sql_info, {"period_id": period_id}
        )

        if not info_result:
            return json.dumps({"success": False, "error": "Période introuvable"})

        pay_date = info_result[0][0]
        pay_year = info_result[0][1]
        pay_month = info_result[0][2]
        status = info_result[0][3]
        print(
            f"  📅 Période: {pay_date} (année: {pay_year}, mois: {pay_month}, statut: {status})"
        )

        # Compter avant suppression
        sql_count_trans = "SELECT COUNT(*) FROM payroll.payroll_transactions WHERE pay_date = %(pay_date)s"
        result_trans = self.provider.repo.run_query(
            sql_count_trans, {"pay_date": pay_date}
        )
        count_transactions = result_trans[0][0] if result_trans else 0

        # Compter UNIQUEMENT les employés liés à cette période
        sql_count_emp = """
            SELECT COUNT(DISTINCT employee_id) 
            FROM payroll.payroll_transactions 
            WHERE pay_date = %(pay_date)s
        """
        result_emp = self.provider.repo.run_query(
            sql_count_emp, {"pay_date": pay_date}
        )
        count_employees = result_emp[0][0] if result_emp else 0

        print(
            f"  📊 À supprimer: {count_transactions} transactions, {count_employees} employés"
        )

        # 1. Créer une trace dans la table d'audit
        try:
            sql_audit = """
            INSERT INTO payroll.deleted_periods_audit 
            (period_id, pay_date, pay_year, pay_month, status, 
             transactions_count, deleted_at, deleted_by)
            VALUES (%(period_id)s, %(pay_date)s, %(pay_year)s, %(pay_month)s, 
                    %(status)s, %(count)s, NOW(), 'user')
            """
            self.provider.repo.run_query(
                sql_audit,
                {
                    "period_id": period_id,
                    "pay_date": pay_date,
                    "pay_year": pay_year,
                    "pay_month": pay_month,
                    "status": status,
                    "count": count_transactions,
                },
            )
            print("  ✅ Trace d'audit créée")
        except Exception as audit_error:
            print(f"  ⚠️ Audit non disponible: {audit_error}")

        # 2. Supprimer les transactions de cette période (AVANT les employés)
        sql_delete_trans = (
            "DELETE FROM payroll.payroll_transactions WHERE pay_date = %(pay_date)s"
        )
        self.provider.repo.run_query(sql_delete_trans, {"pay_date": pay_date})
        print(f"  ✅ {count_transactions} transactions supprimées")

        # 3. Supprimer les données dans imported_payroll_master
        sql_delete_imported = """
            DELETE FROM payroll.imported_payroll_master 
            WHERE date_paie = %(pay_date)s
        """
        self.provider.repo.run_query(sql_delete_imported, {"pay_date": pay_date})
        print("  ✅ Données supprimées dans imported_payroll_master")

        # 4. Supprimer les batches d'import liés à cette période
        sql_delete_batches = """
            DELETE FROM payroll.import_batches 
            WHERE pay_date = %(pay_date)s OR period_id = %(period_id)s
        """
        self.provider.repo.run_query(sql_delete_batches, {
            "pay_date": pay_date,
            "period_id": period_id
        })
        print("  ✅ Batches d'import supprimés")

        # 5. Supprimer les employés orphelins (qui n'ont plus aucune transaction)
        sql_delete_emp = """
            DELETE FROM core.employees 
            WHERE employee_id NOT IN (
                SELECT DISTINCT employee_id 
                FROM payroll.payroll_transactions
                WHERE employee_id IS NOT NULL
            )
        """
        self.provider.repo.run_query(sql_delete_emp, {})
        print("  ✅ Employés orphelins supprimés")

        # 6. Supprimer la période de pay_periods
        sql_delete_period = (
            "DELETE FROM payroll.pay_periods WHERE period_id = %(period_id)s"
        )
        self.provider.repo.run_query(sql_delete_period, {"period_id": period_id})
        print("  ✅ Période supprimée de pay_periods")

        print(f"✅ Suppression TOTALE terminée: {pay_date}")

        return json.dumps(
            {
                "success": True,
                "deleted_count": count_transactions,
                "employees_deleted": count_employees,
                "pay_date": pay_date,
                "message": f"Période {pay_date}, {count_transactions} transactions et employés orphelins supprimés",
            }
        )

    except Exception as e:
        print(f"❌ Erreur delete_period: {e}")
        import traceback
        traceback.print_exc()
        return json.dumps({"success": False, "error": str(e)})
```

---

## 7. RÉSUMÉ DES MODIFICATIONS

### 7.1 Changements principaux

1. **Ordre inversé** : Suppression des transactions AVANT les employés
2. **Ajout de la suppression** de `imported_payroll_master`
3. **Ajout de la suppression** de `import_batches`
4. **Modification de la logique** : Suppression uniquement des employés orphelins (sans transactions)

### 7.2 Ordre final (CORRECT)

1. ✅ Créer trace d'audit
2. ✅ **Supprimer les transactions** (payroll_transactions)
3. ✅ **Supprimer les données importées** (imported_payroll_master)
4. ✅ **Supprimer les batches** (import_batches)
5. ✅ **Supprimer les employés orphelins** (core.employees)
6. ✅ **Supprimer la période** (pay_periods)

---

## 8. TESTS RECOMMANDÉS

### 8.1 Scénarios de test

1. **Test 1 : Suppression d'une période avec transactions**
   - Créer une période avec des transactions
   - Supprimer la période
   - Vérifier que les transactions sont supprimées
   - Vérifier que les employés orphelins sont supprimés

2. **Test 2 : Suppression d'une période avec employés partagés**
   - Créer deux périodes avec des transactions pour les mêmes employés
   - Supprimer une période
   - Vérifier que les employés ne sont PAS supprimés (ils ont encore des transactions)

3. **Test 3 : Suppression d'une période sans transactions**
   - Créer une période sans transactions
   - Supprimer la période
   - Vérifier que la suppression fonctionne

---

## 9. CONTRAINTES DE BASE DE DONNÉES

### 9.1 Contraintes concernées

```sql
-- Table: payroll.payroll_transactions
CONSTRAINT fk_employee 
    FOREIGN KEY (employee_id) 
    REFERENCES core.employees(employee_id)
    ON DELETE RESTRICT

-- Table: payroll.payroll_transactions
CONSTRAINT fk_import_batch 
    FOREIGN KEY (import_batch_id) 
    REFERENCES payroll.import_batches(batch_id)
    ON DELETE SET NULL
```

### 9.2 Impact

- `ON DELETE RESTRICT` : Empêche la suppression d'un employé référencé
- `ON DELETE SET NULL` : Permet la suppression d'un batch (met à NULL la référence)

---

## 10. FICHIERS RESPONSABLES

### 10.1 Fichier à modifier

- **Fichier :** `app/payroll_app_qt_Version4.py`
- **Fonction :** `delete_period(self, period_id: str)`
- **Lignes :** 1023-1050 (à remplacer)

### 10.2 Fichiers de référence

- **Schéma DB :** `app/migration/01_ddl_referentiel.sql` (lignes 218-221)
- **Repository :** `app/services/data_repo.py` (méthode `run_query`)

---

## 11. NOTES IMPORTANTES

1. **Transaction atomique** : Toutes les suppressions doivent être dans une transaction pour garantir la cohérence
2. **Employés orphelins** : Seuls les employés sans transactions sont supprimés
3. **Traçabilité** : La trace d'audit est créée avant toute suppression
4. **Gestion d'erreurs** : Les erreurs sont capturées et retournées en JSON

---

**Fin du rapport**

