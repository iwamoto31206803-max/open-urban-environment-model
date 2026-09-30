@echo off
setlocal

rem OUEM local acceptance helper -- not a formal processing record.
rem Run from any directory. Optionally pass the PLATEAU dataset directory.

for %%I in ("%~dp0..\..") do set "REPO_ROOT=%%~fI"
pushd "%REPO_ROOT%" || goto :repo_error

set "DATASET_DIR=data\raw\building\plateau_komae"
if not "%~1"=="" set "DATASET_DIR=%~1"
set "OUEM_PYTHON=%REPO_ROOT%\.venv\Scripts\python.exe"
set "GIS_PYTHON="

echo === OUEM Komae PLATEAU local acceptance ===
echo Repository:  %CD%
echo Dataset:     %DATASET_DIR%
echo.

echo [1/6] Locate ogr2ogr in the OSGeo4W / QGIS GIS environment
where ogr2ogr
if errorlevel 1 goto :environment_error
echo.

echo [2/6] Report GDAL/OGR version
ogr2ogr --version
if errorlevel 1 goto :environment_error
echo.

echo [3/6] Report the GIS environment Python version
python --version
if errorlevel 1 goto :environment_error
for /f "delims=" %%I in ('where python') do if not defined GIS_PYTHON set "GIS_PYTHON=%%I"
echo.

echo [4/6] Verify that GIS Python imports GDAL's OGR and OSR bindings
python -c "from osgeo import ogr, osr; print('osgeo.ogr and osgeo.osr import OK')"
if errorlevel 1 goto :python_gdal_error
echo.

echo [5/6] Locate the repository-local OUEM Python venv
echo Expected: %OUEM_PYTHON%
if not exist "%OUEM_PYTHON%" goto :venv_missing
"%OUEM_PYTHON%" --version
if errorlevel 1 goto :venv_error
echo.

echo [6/6] Verify that OUEM is installed in the repository-local venv
"%OUEM_PYTHON%" -c "import ouem; print('OUEM package import OK')"
if errorlevel 1 goto :ouem_missing
echo.

echo Environment checks passed. Running:
echo "%OUEM_PYTHON%" -m ouem.native.building.plateau "%DATASET_DIR%" ^
echo   --study-area config\study_areas\komae_09LD3451.yaml ^
echo   --native-dir data\native\building\komae ^
echo   --output data\standard\building\komae.gpkg ^
echo   --gis-python "%GIS_PYTHON%"
echo.

"%OUEM_PYTHON%" -m ouem.native.building.plateau "%DATASET_DIR%" ^
  --study-area config\study_areas\komae_09LD3451.yaml ^
  --native-dir data\native\building\komae ^
  --output data\standard\building\komae.gpkg ^
  --gis-python "%GIS_PYTHON%"
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

:venv_missing
echo.
echo ERROR: Repository-local OUEM venv was not found:
echo   %OUEM_PYTHON%
echo Create and install it from the repository root with:
echo   py -3.12 -m venv .venv
echo   .venv\Scripts\python.exe -m pip install -e .
popd
exit /b 2

:venv_error
echo.
echo ERROR: The repository-local OUEM Python could not run.
popd
exit /b 2

:ouem_missing
echo.
echo ERROR: The OUEM package is not installed in the repository-local venv.
echo Run: .venv\Scripts\python.exe -m pip install -e .
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
