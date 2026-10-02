@echo off
setlocal

rem Two-stage local acceptance helper. Never mix GIS and OUEM Python runtimes.
for %%I in ("%~dp0..\..") do set "REPO_ROOT=%%~fI"
set "RUNTIME_FILE=%REPO_ROOT%\scripts\work\.runtime\plateau_komae_gis.json"
set "OUEM_PYTHON=%REPO_ROOT%\.venv\Scripts\python.exe"
set "CONVERTER_GPKG=%~2"

if /I "%~1"=="gis" goto :gis
if /I "%~1"=="ouem" goto :ouem
goto :usage

:gis
echo === Stage 1: OSGeo4W / QGIS GIS runtime ===
echo Run this stage only in the QGIS/OSGeo4W command environment.
where ogr2ogr || exit /b 2
where ogrinfo || exit /b 2
ogr2ogr --version || exit /b 2
python --version || exit /b 2
python -c "from osgeo import ogr, osr; print('osgeo.ogr and osgeo.osr import OK')" || exit /b 2
python "%REPO_ROOT%\scripts\work\capture_gis_runtime.py" "%RUNTIME_FILE%" || exit /b 2
echo.
echo GIS stage complete. Close this shell before running the OUEM stage.
echo Next, open a normal Command Prompt or VS Code terminal and run:
echo   scripts\work\plateau_komae_local_acceptance.cmd ouem D:\path\to\converted.gpkg
exit /b 0

:ouem
echo === Stage 2: repository-local OUEM runtime ===
echo Do not run this stage in the QGIS/OSGeo4W command environment.
pushd "%REPO_ROOT%" || exit /b 2
if "%CONVERTER_GPKG%"=="" goto :input_missing
if not exist "%RUNTIME_FILE%" goto :runtime_missing
if not exist "%OUEM_PYTHON%" goto :venv_missing
"%OUEM_PYTHON%" --version || goto :ouem_error
"%OUEM_PYTHON%" -c "import ouem; print('OUEM package import OK')" || goto :ouem_missing
"%OUEM_PYTHON%" -m ouem.native.building.plateau "%CONVERTER_GPKG%" ^
  --output data\native\building\komae.gpkg ^
  --gis-runtime "%RUNTIME_FILE%"
set "RUN_EXIT=%ERRORLEVEL%"
popd
exit /b %RUN_EXIT%

:runtime_missing
echo ERROR: GIS runtime snapshot not found. Run the GIS stage first.
popd
exit /b 2

:input_missing
echo ERROR: Pass the PLATEAU GIS Converter GeoPackage to the OUEM stage.
echo Example: plateau_komae_local_acceptance.cmd ouem D:\path\to\converted.gpkg
popd
exit /b 2

:venv_missing
echo ERROR: Repository-local venv not found: %OUEM_PYTHON%
echo Create it from a normal Python terminal, then install with:
echo   .venv\Scripts\python.exe -m pip install -e .
popd
exit /b 2

:ouem_missing
echo ERROR: OUEM is not installed in the repository-local venv.
echo Run: .venv\Scripts\python.exe -m pip install -e .
popd
exit /b 2

:ouem_error
echo ERROR: Repository-local OUEM Python could not run.
popd
exit /b 2

:usage
echo Usage:
echo   In QGIS/OSGeo4W shell: plateau_komae_local_acceptance.cmd gis
echo   Then in normal shell: plateau_komae_local_acceptance.cmd ouem converter.gpkg
exit /b 2
