# Vue `payroll.v_emp_categories`

Cette vue alimente le camembert du dashboard (catégories d'emploi). Pour l'installer correctement :

1. **Exécuter la migration avec un superuser**
   ```powershell
   cd C:\Users\SZERTYUIOPMLMM\Desktop\APP
   "C:\Program Files\PostgreSQL\17\bin\psql.exe" "postgresql://postgres:TON_MDP@localhost:5432/payroll_db" -f app\migration\analytics_emp_categories.sql
   ```

2. **Vérifier les droits**
   ```powershell
   "C:\Program Files\PostgreSQL\17\bin\psql.exe" "postgresql://payroll_app:aq456*456@localhost:5432/payroll_db" -c "SELECT * FROM payroll.v_emp_categories LIMIT 1;"
   ```

3. **Dépendances**
   - La vue s'appuie sur `paie.v_employe_profil`, donc le rôle `payroll_app` doit avoir :
     ```sql
     GRANT USAGE ON SCHEMA paie TO payroll_app;
     GRANT SELECT ON ALL TABLES IN SCHEMA paie TO payroll_app;
     ```

4. **Fallback**
   - Si la vue n'existe pas ou si les droits sont manquants, `get_dashboard_charts` loggue un warning : *"Impossible d'accéder à payroll.v_emp_categories (exécuter app/migration/analytics_emp_categories.sql avec un superuser)"*.

