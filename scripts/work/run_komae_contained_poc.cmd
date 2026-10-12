@echo off
setlocal
cd /d "%~dp0\..\.." || exit /b 2
if "%~1"=="" (
  echo Usage: scripts\work\run_komae_contained_poc.cmd NEW-RUN-ID
  exit /b 2
)
if not "%~2"=="" (
  echo ERROR: Expected only a new run ID. Use the Python CLI for custom input paths.
  exit /b 2
)
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Repository .venv Python not found.
  exit /b 2
)
".venv\Scripts\python.exe" -B -m ouem.komae_integration run --contained-poc ^
  --native-building "data\native\building\komae.gpkg" ^
  --native-terrain "data\native\terrain\komae_09LD3451.json" ^
  --reference-standard-building "data\standard\building\komae.gpkg" ^
  --study-area "config\study_areas\komae_09LD3451.yaml" ^
  --gis-runtime "scripts\work\.runtime\plateau_komae_gis.json" ^
  --run-dir "data\work\integration\%~1" ^
  --meshsize 1 --expected-buildings 92 --expected-native-buildings 3637
exit /b %ERRORLEVEL%
