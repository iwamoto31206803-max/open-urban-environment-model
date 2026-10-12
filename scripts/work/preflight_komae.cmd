@echo off
setlocal
rem Read-only Komae preflight launcher. No integration run is started.
cd /d "%~dp0\..\.." || exit /b 2
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Repository .venv Python not found.
  exit /b 2
)
echo Running Komae read-only preflight...
".venv\Scripts\python.exe" -B -m ouem.komae_integration preflight ^
  --native-building "data\native\building\komae.gpkg" ^
  --native-terrain "data\native\terrain\komae_09LD3451.json" ^
  --reference-standard-building "data\standard\building\komae.gpkg" ^
  --study-area "config\study_areas\komae_09LD3451.yaml" ^
  --gis-runtime "scripts\work\.runtime\plateau_komae_gis.json" ^
  --run-dir "data\work\integration\komae-20261012-001" ^
  --meshsize 1 --expected-buildings 111 --expected-native-buildings 3637
set "RESULT=%ERRORLEVEL%"
echo.
echo Preflight exit code: %RESULT%  (0=PASS, 2=BLOCKED)
exit /b %RESULT%
