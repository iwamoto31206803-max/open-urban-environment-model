@echo off
setlocal
cd /d "%~dp0\..\.." || exit /b 2
if "%~1"=="" (
  echo Usage: scripts\work\diagnose_komae_adapter_content.cmd EXISTING-RUN-ID
  exit /b 2
)
if not "%~2"=="" (
  echo ERROR: Expected exactly one existing run ID.
  exit /b 2
)
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Repository .venv Python not found.
  exit /b 2
)
".venv\Scripts\python.exe" -B -m ouem.komae_adapter_diagnostics "%~1"
exit /b %ERRORLEVEL%
