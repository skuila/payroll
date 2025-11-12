# Legacy non standard scripts

Ces scripts ont été archivés car ils utilisaient des connexions PostgreSQL manuelles (`psycopg.connect`, `create_engine`, lecture directe d'`os.getenv`).

Ils sont conservés à titre de référence uniquement. Pour toute nouvelle automatisation, utiliser le module `app.config.connection_standard` et les helpers `get_connection()`, `run_sql()`, `run_select()`.

Scripts déplacés :
- compare_excel_db.py
- export_db_info.py
- fix_password_and_test.py
- get_db_structure.py
- inspect_database.py
- list_all_tables_columns.py
- reset_payroll_app_password.py
- show_database_structure.py
- test_and_save.py
- test_db_simple.py
- test_db_working.py
- test_excel_db_direct.py
- test_real_connection.py
- unify_passwords.py
- verify_unified_setup.py
