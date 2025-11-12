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
echo COMPARAISON EXCEL vs BASE DE DONNÉES
echo ================================================================================
echo.
cd /d "%~dp0"
call "%PYTHON_CMD%" compare_excel_db.py > comparison_result.txt 2>&1
type comparison_result.txt
echo.
echo ================================================================================
echo Résultats sauvegardés dans: comparison_result.txt
echo ================================================================================
pause

