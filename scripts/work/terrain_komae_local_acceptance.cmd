@echo off
setlocal
for %%I in ("%~dp0..\..") do set "REPO=%%~fI"
set "PYTHON=%REPO%\.venv\Scripts\python.exe"
set "SOURCE=%REPO%\data\raw\terrain\tokyo_23ku_dem_050m\komae\09LD3451.tif"
if not "%~1"=="" set "SOURCE=%~f1"

if not exist "%PYTHON%" (echo ERROR: repository venv not found: %PYTHON%& exit /b 2)
if not exist "%SOURCE%" (echo ERROR: developer-local DEM not found: %SOURCE%& exit /b 2)
pushd "%REPO%" || exit /b 2
"%PYTHON%" -m pytest -q || goto failed
"%PYTHON%" -m ouem.native.terrain "%SOURCE%" ^
  --output data\native\terrain\komae_09LD3451.json ^
  --provider "Tokyo Metropolitan Government" ^
  --source-dataset "Tokyo 0.50 m bare-earth DEM tile 09LD3451" ^
  --vertical-reference-status source-declared ^
  --vertical-reference "T.P. (Tokyo Peil / Tokyo Bay mean sea level)" ^
  --vertical-reference-source "Tokyo Metropolitan Government; Tokyo 23-ku point-cloud metadata: JGD2011, Plane Rectangular CS IX, elevation = Tokyo Bay mean sea level (https://portal.data.metro.tokyo.lg.jp/); 23-ku point-cloud and 0.5 m grid DEM release (https://www.metro.tokyo.lg.jp/information/press/2024/10/2024103126); Tokyo public control points and benchmarks, Tokyo Bay mean sea level as T.P. (https://www.kensetsu.metro.tokyo.lg.jp/jimusho/tech/04-kijyun/kijyunsetu)" || goto failed
"%PYTHON%" -m ouem.standardize.terrain data\native\terrain\komae_09LD3451.json ^
  --output data\standard\terrain\komae_09LD3451.tif ^
  --study-area config\study_areas\komae_09LD3451.yaml || goto failed
popd
exit /b 0
:failed
popd
echo Terrain Komae acceptance: FAIL
exit /b 1
