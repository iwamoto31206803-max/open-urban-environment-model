@echo off
setlocal
set "REPO=%~dp0..\.."

if /I "%~1"=="gis" goto gis
if /I "%~1"=="ouem" goto ouem
echo Usage: %~nx0 ^<gis^|ouem^>
echo.
echo   gis   Run from OSGeo4W Shell. Uses only the QGIS/GIS runtime.
echo   ouem  Run from a NEW ordinary cmd or VS Code terminal. Uses only .venv.
exit /b 2

:gis
where ogr2ogr >nul 2>nul || (echo ERROR: ogr2ogr not found. Use OSGeo4W Shell.& exit /b 1)
python "%REPO%\scripts\work\gis_runtime_check.py" || exit /b 1
echo.
echo GIS stage complete. Close this shell. Then open a new ordinary Windows cmd and run:
echo   scripts\work\plateau_komae_local_acceptance.cmd ouem
exit /b 0

:ouem
if defined OSGEO4W_ROOT goto contaminated
if defined QGIS_PREFIX_PATH goto contaminated
if defined QGIS_PLUGINPATH goto contaminated
if defined GDAL_DATA goto contaminated
if defined PROJ_LIB goto contaminated
echo %PYTHONHOME% %PYTHONPATH% | findstr /I "qgis osgeo4w" >nul && goto contaminated
set "OUEM_PYTHON=%REPO%\.venv\Scripts\python.exe"
if not exist "%OUEM_PYTHON%" (
  echo ERROR: repository venv not found. From an ordinary Windows cmd, run:
  echo   py -m venv .venv
  echo   .venv\Scripts\python.exe -m pip install -e .
  exit /b 1
)
"%OUEM_PYTHON%" "%REPO%\scripts\work\ouem_runtime_check.py" --expected-python "%OUEM_PYTHON%" || exit /b 1
"%OUEM_PYTHON%" -m pytest || exit /b 1
exit /b 0

:contaminated
echo ERROR: GIS runtime variables are present. Do not launch the OUEM venv from OSGeo4W Shell.
echo Close this shell and rerun the OUEM stage in a new ordinary cmd or VS Code terminal.
exit /b 1
