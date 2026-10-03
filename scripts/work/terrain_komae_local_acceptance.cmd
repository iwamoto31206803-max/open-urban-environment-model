@echo off
setlocal
for %%I in ("%~dp0..\..") do set "REPO=%%~fI"
set "PYTHON=%REPO%\.venv\Scripts\python.exe"
set "SOURCE=%REPO%\data\raw\terrain\komae\09LD3451.tif"
if not "%~1"=="" set "SOURCE=%~f1"

if not exist "%PYTHON%" (echo ERROR: repository venv not found: %PYTHON%& exit /b 2)
if not exist "%SOURCE%" (echo ERROR: developer-local DEM not found: %SOURCE%& exit /b 2)
pushd "%REPO%" || exit /b 2
"%PYTHON%" -m pytest -q || goto failed
"%PYTHON%" -m ouem.native.terrain "%SOURCE%" ^
  --output data\native\terrain\komae_09LD3451.json ^
  --provider "Tokyo Metropolitan Government" ^
  --source-dataset "Tokyo 0.50 m bare-earth DEM tile 09LD3451" ^
  --vertical-reference-status unresolved || goto failed
"%PYTHON%" -m ouem.standardize.terrain data\native\terrain\komae_09LD3451.json ^
  --output data\standard\terrain\komae_09LD3451.tif ^
  --study-area config\study_areas\komae_09LD3451.yaml || goto failed
popd
exit /b 0
:failed
popd
echo Terrain Komae acceptance: FAIL
exit /b 1
