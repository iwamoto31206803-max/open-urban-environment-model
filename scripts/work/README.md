# Windows local acceptance helpers

The Komae helper deliberately has two invocations; it never starts OUEM's
virtual-environment Python from OSGeo4W Shell.

1. In **OSGeo4W Shell**, run
   `scripts\work\plateau_komae_local_acceptance.cmd gis`.
2. Close that shell. In a **new ordinary Windows cmd or VS Code terminal**, run
   `scripts\work\plateau_komae_local_acceptance.cmd ouem`.

The GIS stage verifies `ogr2ogr` and the `osgeo` bindings with QGIS Python. The
OUEM stage rejects inherited QGIS/OSGeo4W variables, verifies the exact
repository `.venv` interpreter, imports OUEM, and runs the automated tests.

Create the venv with `py -m venv .venv` and install with
`.venv\Scripts\python.exe -m pip install -e .`. Python 3.11.9 is the accepted
local runtime, but is not a package-wide minor-version lock; `pyproject.toml`
remains the authority for supported Python versions.

`--gis-python`, where supported by a provider, is a **subprocess bridge**. It
selects a GIS worker interpreter and must not replace `sys.executable`, activate
QGIS in the parent, or run OUEM inside QGIS Python. Exchange data through files
or a documented serialization protocol, and propagate only the minimum GIS
environment to the child process.
