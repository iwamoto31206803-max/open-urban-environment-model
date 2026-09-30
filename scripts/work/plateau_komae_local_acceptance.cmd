@echo off
setlocal

rem OUEM local acceptance helper -- not a formal processing record.
rem Run from any directory. Optionally pass the PLATEAU dataset directory.

for %%I in ("%~dp0..\..") do set "REPO_ROOT=%%~fI"
pushd "%REPO_ROOT%" || goto :repo_error

set "DATASET_DIR=data\raw\building\plateau_komae"
if not "%~1"=="" set "DATASET_DIR=%~1"

echo === OUEM Komae PLATEAU local acceptance ===
echo Repository:  %CD%
echo Dataset:     %DATASET_DIR%
echo.

echo [1/4] Locate ogr2ogr
where ogr2ogr
if errorlevel 1 goto :environment_error
echo.

echo [2/4] Report GDAL/OGR version
ogr2ogr --version
if errorlevel 1 goto :environment_error
echo.

echo [3/4] Report the active Python version
python --version
if errorlevel 1 goto :environment_error
echo.

echo [4/4] Verify that this same Python imports GDAL's OGR and OSR bindings
python -c "from osgeo import ogr, osr; print('osgeo.ogr and osgeo.osr import OK')"
if errorlevel 1 goto :python_gdal_error
echo.

echo Environment checks passed. Running:
echo python -m ouem.native.building.plateau "%DATASET_DIR%" ^
echo   --study-area config\study_areas\komae_09LD3451.yaml ^
echo   --native-dir data\native\building\komae ^
echo   --output data\standard\building\komae.gpkg
echo.

python -m ouem.native.building.plateau "%DATASET_DIR%" ^
  --study-area config\study_areas\komae_09LD3451.yaml ^
  --native-dir data\native\building\komae ^
  --output data\standard\building\komae.gpkg
set "RUN_EXIT=%ERRORLEVEL%"
echo.
if not "%RUN_EXIT%"=="0" echo Provider failed with exit code %RUN_EXIT%.
popd
exit /b %RUN_EXIT%

:python_gdal_error
echo.
echo ERROR: The active Python cannot import osgeo.ogr and osgeo.osr.
echo OSGeo4W ogr2ogr and the VS Code virtual environment may be using separate runtimes.
echo This helper will not modify PATH or PYTHONPATH. Resolve or document the real
echo workstation compatibility before changing the provider.
popd
exit /b 2

:environment_error
echo.
echo ERROR: An environment check failed. Review the command output above.
popd
exit /b 2

:repo_error
echo ERROR: Could not enter repository root "%REPO_ROOT%".
exit /b 2
