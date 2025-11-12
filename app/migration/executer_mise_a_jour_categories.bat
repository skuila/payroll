@echo off
echo ============================================================
echo   Mise à jour des catégories et titres d'emploi
echo ============================================================
echo.

REM Trouver psql
set PSQL_PATH=
if exist "C:\Program Files\PostgreSQL\15\bin\psql.exe" (
    set PSQL_PATH=C:\Program Files\PostgreSQL\15\bin\psql.exe
) else if exist "C:\Program Files\PostgreSQL\14\bin\psql.exe" (
    set PSQL_PATH=C:\Program Files\PostgreSQL\14\bin\psql.exe
) else (
    echo ❌ psql non trouvé
    pause
    exit /b 1
)

echo ✅ Exécution de la migration...
echo.

REM Use PAYROLL_DB_PASSWORD environment variable if set, otherwise leave PGPASSWORD unchanged
if defined PAYROLL_DB_PASSWORD (
    set PGPASSWORD=%PAYROLL_DB_PASSWORD%
)
"%PSQL_PATH%" -h localhost -U postgres -d payroll_db -f migration\016_mise_a_jour_categories_titres.sql

if errorlevel 1 (
    echo.
    echo ❌ Erreur lors de l'exécution
    pause
    exit /b 1
)

echo.
echo ✅ Migration terminée avec succès
pause

