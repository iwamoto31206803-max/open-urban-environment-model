@echo off
setlocal
for %%I in ("%~dp0..\..") do set "REPO_ROOT=%%~fI"
set "VENV_PYTHON=%REPO_ROOT%\.venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
  echo [INFO] Creating the repository-local OUEM Python environment at "%REPO_ROOT%\.venv"...
  py -3 -m venv "%REPO_ROOT%\.venv"
  if errorlevel 1 (
    echo [ERROR] Could not create .venv. Install Python 3.10 or later and ensure the py launcher is available.
    exit /b 1
  )
)

echo [INFO] Installing OUEM into the repository-local environment...
"%VENV_PYTHON%" -m pip install -e "%REPO_ROOT%"
if errorlevel 1 (
  echo [ERROR] OUEM installation failed.
  exit /b 1
)

"%VENV_PYTHON%" -c "import ouem; print('[OK] OUEM Python venv and ouem package are ready')"
exit /b %errorlevel%
