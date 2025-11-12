@echo off
REM ============================================================
REM LANCEUR STANDARDISE PAYROLL ANALYZER
REM Version: 1.0 - Configuration automatique garantie
REM ============================================================

cd /d "%~dp0"

REM Configuration Python Path (obligatoire)
set PYTHONPATH=%~dp0..
set PYTHONUNBUFFERED=1

REM Lancement avec sortie visible
echo ============================================================
echo PAYROLL ANALYZER - Lancement
echo ============================================================
echo.
echo Configuration:
echo   Repertoire: %CD%
echo   PYTHONPATH: %PYTHONPATH%
echo.

python payroll_app_qt_Version4.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================================
    echo ERREUR: L'application s'est terminee avec une erreur
    echo Code: %ERRORLEVEL%
    echo ============================================================
    pause
) else (
    echo.
    echo Application fermee normalement
)

