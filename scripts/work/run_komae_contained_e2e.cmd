@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0\..\.." || exit /b 2
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Repository .venv Python not found.
  exit /b 2
)
rem Capture positional arguments once; keep delayed expansion off until validation.
set "OUEM_RUN_ID=%~1"
set "OUEM_EXTRA_ARG=%~2"
".venv\Scripts\python.exe" -B -c "import os,re,sys; s=os.environ.get('OUEM_RUN_ID',''); extra=os.environ.get('OUEM_EXTRA_ARG',''); reserved={'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}; sys.exit(0 if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',s) and s.upper() not in reserved and not extra else 2)"
if errorlevel 1 (
  echo ERROR: Supply one new portable run ID: 1-64 ASCII letters, digits, underscores or hyphens; no reserved Windows names.
  exit /b 2
)
rem Delayed expansion keeps the validated ID from being parsed as batch syntax.
setlocal EnableDelayedExpansion
if exist "data\work\integration\!OUEM_RUN_ID!" (
  echo ERROR: Run ID already exists.
  exit /b 2
)
".venv\Scripts\python.exe" -B -m ouem.komae_integration run --contained-poc ^
  --native-building "data\native\building\komae.gpkg" ^
  --native-terrain "data\native\terrain\komae_09LD3451.json" ^
  --reference-standard-building "data\standard\building\komae.gpkg" ^
  --study-area "config\study_areas\komae_09LD3451.yaml" ^
  --gis-runtime "scripts\work\.runtime\plateau_komae_gis.json" ^
  --run-dir "data\work\integration\!OUEM_RUN_ID!" ^
  --meshsize 1 --expected-buildings 92 --expected-native-buildings 3637
set "RUN_EXIT=%ERRORLEVEL%"
if exist "data\work\integration\!OUEM_RUN_ID!\integration-report.json" echo Report: "%CD%\data\work\integration\!OUEM_RUN_ID!\integration-report.json"
exit /b %RUN_EXIT%
