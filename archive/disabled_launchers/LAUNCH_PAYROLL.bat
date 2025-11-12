@echo off
REM ORIGINAL LAUNCH_PAYROLL.bat (archived)
REM Script de lancement unifié pour l'application Payroll
REM Configure automatiquement les variables d'environnement et lance l'application

echo ============================================
echo LANCEMENT UNIFIE DE L'APPLICATION PAYROLL
echo ============================================

REM Définir les variables d'environnement unifiées
set PAYROLL_DB_USER=payroll_unified
REM Les mots de passe ne doivent pas être codés en dur dans ce fichier.
REM Configurez un fichier local `.env` et exportez les variables d'environnement, ou définissez-les avant d'appeler ce script.
REM Exemple (Powershell): $env:PAYROLL_DB_PASSWORD = 'votre_mot_de_passe'
REM Les variables sensibles: PAYROLL_DB_PASSWORD et PAYROLL_DB_SUPERUSER_PASSWORD
set PAYROLL_DB_HOST=localhost
set PAYROLL_DB_PORT=5432
set PAYROLL_DB_NAME=payroll_db
set PAYROLL_DB_SUPERUSER=postgres
set APP_ENV=development
set PAYROLL_FORCE_OFFLINE=0
set USE_COPY=0

echo [OK] Variables d'environnement configurees (les mots de passe ne sont pas affichés ici)
echo Utilisation du role unifie: %PAYROLL_DB_USER%
echo Connexion PostgreSQL securisee
echo.
echo Lancement de l'application...
echo ============================================

REM Lancer l'application Python
python payroll_app_qt_Version4.py

REM Garder la fenêtre ouverte en cas d'erreur
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERREUR: L'application s'est terminee avec une erreur (code: %ERRORLEVEL%)
    pause
)
