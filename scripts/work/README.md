# Windows local acceptance workflow

These launchers keep the **OSGeo4W GIS environment** separate from the
**OUEM Python venv**. Run them from Explorer, Command Prompt, or the VS Code
terminal; no command copied from chat is required.

## After every `git pull`

1. Run `setup_ouem_venv.cmd`. It creates the standard `.venv` at the repository
   root when needed and installs the checkout in editable mode.
2. Run `plateau_komae_local_acceptance.cmd` with the same PLATEAU CLI arguments
   required by the acceptance case. Arguments are forwarded unchanged to
   `ouem.native.building.plateau`.

For example, a saved shortcut or terminal invocation can append the input and
output options used by the current Komae case to
`plateau_komae_local_acceptance.cmd`; the launcher itself always selects
`.venv\Scripts\python.exe`.

The acceptance launcher first starts `check_osgeo4w_environment.cmd` in an
isolated child Command Prompt. That check initializes QGIS/OSGeo4W and verifies
`ogr2ogr`, GDAL, the bundled Python, and `osgeo.ogr`/`osgeo.osr`. When it ends,
the launcher runs OUEM using the repository venv—not QGIS Python. The current
default is `C:\Program Files\QGIS 3.44.14`; set `OUEM_QGIS_ROOT` only when QGIS
is installed elsewhere. QGIS 4.x is not required.

`check_osgeo4w_environment.cmd` can also be run by itself to diagnose the GIS
installation. Future PDAL/GDAL/OGR provider launchers should use the same
isolated-check/native-command pattern and return to `.venv` for `ouem.*` code.
