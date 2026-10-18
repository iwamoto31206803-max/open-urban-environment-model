@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0\..\.." || exit /b 2
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Repository .venv Python not found.
  exit /b 2
)
set "OUEM_HEIGHT_RUN_ID=%~1"
set "OUEM_HEIGHT_EXTRA=%~2"
".venv\Scripts\python.exe" -B -c "import os,re,sys; s=os.environ.get('OUEM_HEIGHT_RUN_ID',''); extra=os.environ.get('OUEM_HEIGHT_EXTRA',''); reserved={'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}; sys.exit(0 if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',s) and s.upper() not in reserved and not extra else 2)"
if errorlevel 1 (
  echo ERROR: Supply exactly one existing portable run ID.
  exit /b 2
)
setlocal EnableDelayedExpansion
".venv\Scripts\python.exe" -B -m ouem.komae_height_diagnostics "!OUEM_HEIGHT_RUN_ID!"
exit /b %ERRORLEVEL%
