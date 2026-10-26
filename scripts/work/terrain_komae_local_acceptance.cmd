@echo off
setlocal DisableDelayedExpansion
for %%I in ("%~dp0..\..") do set "REPO=%%~fI"
set "PYTHON=%REPO%\.venv\Scripts\python.exe"
if not exist "%PYTHON%" (echo ERROR: repository venv not found: %PYTHON%& exit /b 2)
pushd "%REPO%" || exit /b 2
"%PYTHON%" -m ouem.terrain_local_acceptance %*
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%
