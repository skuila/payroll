@echo off
REM DEPRECATION STUB - Please use the canonical launcher: launch_payroll.py
echo ==============================================================
echo This launcher has been deprecated and archived.
echo Use the canonical launcher instead:
echo    python launch_payroll.py %*
echo Archived original available at: ..\archive\disabled_launchers\LAUNCH_PAYROLL.bat
echo ==============================================================

REM Forward arguments to canonical launcher for compatibility
python launch_payroll.py %*
exit /b %ERRORLEVEL%