@echo off
setlocal
for %%I in ("%~dp0..\..") do set "REPO_ROOT=%%~fI"
set "VENV_PYTHON=%REPO_ROOT%\.venv\Scripts\python.exe"

echo === 1/2 OSGeo4W GIS environment ===
rem cmd /d /c prevents o4w_env.bat from leaking its PATH/Python into this launcher.
cmd /d /c ""%~dp0check_osgeo4w_environment.cmd""
if errorlevel 1 exit /b 1

echo.
echo === 2/2 OUEM Python environment ===
if not exist "%VENV_PYTHON%" (
  echo [ERROR] The repository-local OUEM Python environment does not exist:
  echo         "%VENV_PYTHON%"
  echo         Run "%~dp0setup_ouem_venv.cmd" first, then retry.
  exit /b 1
)

"%VENV_PYTHON%" -c "import ouem" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] The ouem package is not installed in "%VENV_PYTHON%".
  echo         Run "%~dp0setup_ouem_venv.cmd" first, then retry.
  exit /b 1
)

echo [OK] Using OUEM Python: "%VENV_PYTHON%"
"%VENV_PYTHON%" -m ouem.native.building.plateau %*
exit /b %errorlevel%
