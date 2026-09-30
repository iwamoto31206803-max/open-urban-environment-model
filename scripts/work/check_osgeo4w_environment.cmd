@echo off
setlocal

rem Run this file in its own process. OSGeo4W changes remain scoped here and
rem never select the Python used to run an OUEM module.
if not defined OUEM_QGIS_ROOT set "OUEM_QGIS_ROOT=C:\Program Files\QGIS 3.44.14"
set "OSGEO_ENV=%OUEM_QGIS_ROOT%\bin\o4w_env.bat"
set "QGIS_PYTHON=%OUEM_QGIS_ROOT%\bin\python.exe"

if not exist "%OSGEO_ENV%" (
  echo [ERROR] OSGeo4W environment script was not found: "%OSGEO_ENV%"
  echo         Set OUEM_QGIS_ROOT to the installed QGIS directory and retry.
  exit /b 1
)

call "%OSGEO_ENV%" >nul
if errorlevel 1 (
  echo [ERROR] Failed to initialize the OSGeo4W GIS environment.
  exit /b 1
)

where ogr2ogr >nul 2>&1
if errorlevel 1 (
  echo [ERROR] ogr2ogr is not available in the OSGeo4W GIS environment.
  exit /b 1
)

echo [OK] ogr2ogr:
where ogr2ogr
echo [INFO] GDAL:
gdalinfo --version
if errorlevel 1 exit /b 1

if not exist "%QGIS_PYTHON%" (
  echo [ERROR] QGIS Python was not found: "%QGIS_PYTHON%"
  exit /b 1
)
echo [INFO] OSGeo4W active Python:
"%QGIS_PYTHON%" --version
if errorlevel 1 exit /b 1
"%QGIS_PYTHON%" -c "from osgeo import ogr, osr; print('[OK] osgeo.ogr / osgeo.osr: import OK')"
if errorlevel 1 (
  echo [ERROR] The OSGeo4W Python cannot import osgeo.ogr and osgeo.osr.
  exit /b 1
)

echo [OK] OSGeo4W GIS environment check passed.
exit /b 0
