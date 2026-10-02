@echo off
setlocal
for %%I in ("%~dp0..\..") do set "REPO=%%~fI"
set "RUNTIME_FILE=%REPO%\scripts\work\.runtime\plateau_komae_gis.json"
set "OUEM_PYTHON=%REPO%\.venv\Scripts\python.exe"
set "SOURCE_LAYER=%~3"

if /I "%~1"=="manual" goto manual
if /I "%~1"=="gis" goto gis
if /I "%~1"=="ouem" goto ouem
goto usage

:manual
echo === Stage 1: manual PLATEAU GIS Converter preprocessing ===
echo 1. Open the Komae PLATEAU Building CityGML in PLATEAU GIS Converter GUI.
echo 2. Export a GeoPackage using maximum LOD to:
echo    data\converted\building\plateau_komae\53393465_bldg_6697_op_convert.gpkg
echo 3. Enable settings that retain 3D / Z geometry.
echo 4. Pass the resulting GeoPackage to the OUEM stage.
echo The GUI conversion is manual and is not run by this script.
exit /b 0

:gis
where ogr2ogr >nul 2>nul || (echo ERROR: ogr2ogr not found. Use OSGeo4W Shell.& exit /b 1)
python "%REPO%\scripts\work\gis_runtime_check.py" || exit /b 1
python "%REPO%\scripts\work\capture_gis_runtime.py" "%RUNTIME_FILE%" || exit /b 1
echo.
echo GIS runtime setup complete. Close this shell. Then open a new ordinary cmd and run:
echo   scripts\work\plateau_komae_local_acceptance.cmd ouem
exit /b 0

:ouem
if defined OSGEO4W_ROOT goto contaminated
if defined QGIS_PREFIX_PATH goto contaminated
if defined QGIS_PLUGINPATH goto contaminated
if defined GDAL_DATA goto contaminated
if defined PROJ_LIB goto contaminated
echo %PYTHONHOME% %PYTHONPATH% | findstr /I "qgis osgeo4w" >nul && goto contaminated
call :resolve_converter_gpkg "%~2"
if not exist "%CONVERTER_GPKG%" goto input_missing
if not exist "%RUNTIME_FILE%" goto runtime_missing
if not exist "%OUEM_PYTHON%" goto venv_missing
pushd "%REPO%" || exit /b 2
"%OUEM_PYTHON%" "%REPO%\scripts\work\ouem_runtime_check.py" --expected-python "%OUEM_PYTHON%" || goto ouem_failed
"%OUEM_PYTHON%" -m pytest || goto ouem_failed
if not "%SOURCE_LAYER%"=="" goto ouem_explicit_layer
"%OUEM_PYTHON%" -m ouem.native.building.plateau "%CONVERTER_GPKG%" ^
  --output data\native\building\komae.gpkg ^
  --expected-count 3637 ^
  --gis-runtime "%RUNTIME_FILE%"
goto ouem_done

:ouem_explicit_layer
echo Explicit source layer: %SOURCE_LAYER%
"%OUEM_PYTHON%" -m ouem.native.building.plateau "%CONVERTER_GPKG%" ^
  --output data\native\building\komae.gpkg ^
  --source-layer "%SOURCE_LAYER%" ^
  --expected-count 3637 ^
  --gis-runtime "%RUNTIME_FILE%"

:ouem_done
set "RUN_EXIT=%ERRORLEVEL%"
popd
exit /b %RUN_EXIT%

:resolve_converter_gpkg
set "CONVERTER_GPKG=%~1"
if not defined CONVERTER_GPKG set "CONVERTER_GPKG=%REPO%\data\converted\building\plateau_komae\53393465_bldg_6697_op_convert.gpkg"
if not "%CONVERTER_GPKG:~1,1%"==":" if not "%CONVERTER_GPKG:~0,1%"=="\" set "CONVERTER_GPKG=%REPO%\%CONVERTER_GPKG%"
for %%I in ("%CONVERTER_GPKG%") do set "CONVERTER_GPKG=%%~fI"
exit /b 0

:ouem_failed
popd
exit /b 1

:contaminated
echo ERROR: GIS runtime variables are present. Do not launch the OUEM venv from OSGeo4W Shell.
echo Close this shell and rerun the OUEM stage in a new ordinary cmd or VS Code terminal.
exit /b 1

:runtime_missing
echo ERROR: GIS runtime snapshot not found. Run the gis stage first.
exit /b 2

:input_missing
echo ERROR: Pass the PLATEAU GIS Converter GeoPackage to the OUEM stage.
echo Expected default: data\converted\building\plateau_komae\53393465_bldg_6697_op_convert.gpkg
echo Or pass another path: %~nx0 ouem D:\path\to\converted.gpkg [source-layer]
echo Repository-relative paths are resolved from: %REPO%
exit /b 2

:venv_missing
echo ERROR: repository venv not found. From an ordinary Windows cmd, run:
echo   py -m venv .venv
echo   .venv\Scripts\python.exe -m pip install -e .
exit /b 1

:usage
echo Usage: %~nx0 ^<manual^|gis^|ouem^> [converter.gpkg] [source-layer]
echo.
echo   manual  Show manual PLATEAU GIS Converter preprocessing instructions.
echo   gis     Run from OSGeo4W Shell. Uses only the QGIS/GIS runtime.
echo   ouem    Run from a NEW ordinary cmd or VS Code terminal. Uses only .venv.
echo           Defaults to data\converted\building\plateau_komae\53393465_bldg_6697_op_convert.gpkg.
echo           Relative paths are resolved from the repository root; quote paths containing spaces.
exit /b 2
