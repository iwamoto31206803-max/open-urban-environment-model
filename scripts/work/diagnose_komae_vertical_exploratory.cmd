@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0\..\.." || exit /b 2
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Repository .venv Python not found.
  exit /b 2
)
set "OUEM_EXPLORATORY_RUN=%~1"
set "OUEM_EXPLORATORY_TARGET=%~2"
set "OUEM_EXPLORATORY_EXTRA=%~3"
".venv\Scripts\python.exe" -B -c "import os,re,sys; run=os.environ.get('OUEM_EXPLORATORY_RUN',''); target=os.environ.get('OUEM_EXPLORATORY_TARGET',''); extra=os.environ.get('OUEM_EXPLORATORY_EXTRA',''); reserved={'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}; sys.exit(0 if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',run) and run.upper() not in reserved and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}',target) and not extra else 2)"
if errorlevel 1 (
  echo ERROR: Supply an existing portable run ID and one ASCII building ID or prefix.
  exit /b 2
)
setlocal EnableDelayedExpansion
".venv\Scripts\python.exe" -B -m ouem.komae_vertical_exploratory "!OUEM_EXPLORATORY_RUN!" "!OUEM_EXPLORATORY_TARGET!"
exit /b !ERRORLEVEL!
