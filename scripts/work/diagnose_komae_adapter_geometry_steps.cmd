@echo off
setlocal
cd /d "%~dp0\..\.." || exit /b 2
if "%~1"=="" (
  echo Usage: scripts\work\diagnose_komae_adapter_geometry_steps.cmd EXISTING-RUN-ID [OUEM-ID]
  exit /b 2
)
if not "%~3"=="" (
  echo ERROR: Expected an existing run ID and optional OUEM ID.
  exit /b 2
)
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: Repository .venv Python not found.
  exit /b 2
)
if "%~2"=="" (
  ".venv\Scripts\python.exe" -B -m ouem.komae_adapter_geometry_steps "%~1"
) else (
  ".venv\Scripts\python.exe" -B -m ouem.komae_adapter_geometry_steps "%~1" "%~2"
)
exit /b %ERRORLEVEL%
