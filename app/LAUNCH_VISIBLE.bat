@echo off
echo ============================================================
echo LANCEMENT APPLICATION PAYROLL - MODE VISIBLE
echo ============================================================
echo.

cd /d "%~dp0"
set PYTHONPATH=%~dp0..
set PYTHONUNBUFFERED=1

echo Configuration:
echo   PYTHONPATH=%PYTHONPATH%
echo   Working Dir=%CD%
echo.

echo Lancement de l'application...
echo.

python payroll_app_qt_Version4.py
set EXIT_CODE=%ERRORLEVEL%

echo.
echo ============================================================
echo Application terminée avec code: %EXIT_CODE%
echo ============================================================
pause

