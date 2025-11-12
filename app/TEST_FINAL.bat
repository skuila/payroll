@echo off
chcp 65001 >nul
cls

rem ------------------------------------------------------------------
rem Localiser l'interpréteur Python
rem ------------------------------------------------------------------
set "PYTHON_CMD=C:\Python314\python.exe"
if not exist "%PYTHON_CMD%" (
    set "PYTHON_CMD=py -3"
    %PYTHON_CMD% -V >nul 2>&1
    if errorlevel 1 (
        set "PYTHON_CMD=python"
    )
)

cls
echo ================================================================================
echo TEST COMPLET - EXCEL vs BASE DE DONNÉES
echo ================================================================================
echo.
cd /d "%~dp0"

echo [1/3] Unification des mots de passe...
call "%PYTHON_CMD%" unify_passwords.py
echo.

echo [2/3] Vérification de la configuration...
call "%PYTHON_CMD%" verify_unified_setup.py
echo.

echo [3/3] Comparaison Excel vs DB...
call "%PYTHON_CMD%" compare_excel_db.py
echo.

echo ================================================================================
echo TEST TERMINÉ
echo ================================================================================
pause

