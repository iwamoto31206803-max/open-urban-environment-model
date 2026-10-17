@echo off
setlocal
cd /d "%~dp0\..\.." || exit /b 2
if "%~1"=="" (
  echo Usage: scripts\work\export_komae_repair_qgis.cmd EXISTING-RUN-ID
  exit /b 2
)
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Repository .venv Python not found.
  exit /b 2
)
".venv\Scripts\python.exe" -B "scripts\work\export_komae_repair_qgis.py" "%~1"
exit /b %ERRORLEVEL%
