@echo off
chcp 65001 >nul

set "PYTHON_CMD=C:\Python314\python.exe"
if not exist "%PYTHON_CMD%" (
    set "PYTHON_CMD=py -3"
    %PYTHON_CMD% -V >nul 2>&1
    if errorlevel 1 (
        set "PYTHON_CMD=python"
    )
)

echo ================================================================================
echo UNIFICATION DES MOTS DE PASSE POSTGRESQL
echo ================================================================================
echo.
cd /d "%~dp0"
call "%PYTHON_CMD%" unify_passwords.py
echo.
echo ================================================================================
echo Appuyez sur une touche pour fermer...
echo ================================================================================
pause

