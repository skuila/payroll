@echo off
REM =====================================================
REM SCRIPT D'ADMINISTRATION - CRÉATION DES VUES KPI DURABLES
REM =====================================================
REM Ce script utilise les comptes administrateur pour créer
REM les vues KPI harmonisées de façon permanente.
REM =====================================================

echo.
echo =====================================================
echo ADMINISTRATION - CRÉATION DES VUES KPI DURABLES
echo =====================================================
echo.

REM Configuration
set ADMIN_USER=postgres
REM Ne pas stocker le mot de passe en clair dans ce fichier. Définissez la variable d'environnement ADMIN_PASSWORD avant d'exécuter.
if "%ADMIN_PASSWORD%"=="" (
    echo WARNING: ADMIN_PASSWORD non défini — définir la variable d'environnement ADMIN_PASSWORD avant d'exécuter ce script
    set ADMIN_PASSWORD=__SET_AT_DEPLOY__
)
set DATABASE=payroll_db
set SQL_FILE=scripts\admin_create_kpi_views.sql

echo [1/3] Vérification de l'environnement...
psql --version >nul 2>&1
if errorlevel 1 (
    echo ❌ psql non trouvé dans le PATH
    echo 🔧 Assurez-vous que PostgreSQL est installé et dans le PATH
    goto :error
)
echo ✅ psql disponible

echo.
echo [2/3] Exécution du script d'administration...
echo 🔐 Connexion avec le compte administrateur...
echo 📄 Exécution du script: %SQL_FILE%

set PGPASSWORD=%ADMIN_PASSWORD%
psql -h localhost -U %ADMIN_USER% -d %DATABASE% -f %SQL_FILE%
if errorlevel 1 (
    echo ❌ Échec de l'exécution du script
    goto :error
)
echo ✅ Script d'administration exécuté avec succès

echo.
echo [3/3] Vérification des vues créées...
set PGPASSWORD=%ADMIN_PASSWORD%
psql -h localhost -U %ADMIN_USER% -d %DATABASE% -c "SELECT table_schema, table_name FROM information_schema.views WHERE table_schema = 'paie' ORDER BY table_name;"
if errorlevel 1 (
    echo ❌ Erreur lors de la vérification
    goto :error
)

echo.
echo =====================================================
echo 🎉 ADMINISTRATION TERMINÉE AVEC SUCCÈS
echo =====================================================
echo ✅ Schéma paie créé avec les droits administrateur
echo ✅ 7 vues KPI harmonisées créées
echo ✅ Permissions lecture seule accordées à payroll_app
echo ✅ Alias rétro-compatibles configurés
echo ✅ Documentation et commentaires ajoutés
echo.
echo 🔗 Les vues sont maintenant disponibles pour l'API
echo 📊 Test: SELECT * FROM paie.v_kpi_periode LIMIT 5;
echo =====================================================
goto :end

:error
echo.
echo =====================================================
echo ❌ ÉCHEC DE L'ADMINISTRATION
echo =====================================================
echo 🔧 Vérifiez les éléments suivants:
echo    - PostgreSQL est installé et accessible
echo    - Le compte postgres existe avec le bon mot de passe
echo    - La base payroll_db existe
echo    - Vous avez les droits administrateur
echo =====================================================
exit /b 1

:end
pause
