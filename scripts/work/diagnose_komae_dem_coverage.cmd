@echo off
setlocal
cd /d "%~dp0\..\.." || exit /b 2
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: repository .venv Python not found.
  exit /b 2
)
".venv\Scripts\python.exe" -B scripts\work\diagnose_komae_dem_coverage.py
exit /b %ERRORLEVEL%
