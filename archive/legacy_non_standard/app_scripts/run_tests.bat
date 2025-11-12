@echo off
REM Run pytest using the workspace virtualenv python
set PY="%~dp0..\.venv\Scripts\python.exe"
IF NOT EXIST %PY% (
  echo Interpreter venv introuvable: %PY%
  echo Execute: python -m venv .venv && .\.venv\Scripts\pip.exe install -r requirements.txt
  exit /b 1
)

%PY% -m pytest -q
