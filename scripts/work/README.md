# Windows local acceptance helpers

Files in this directory are temporary, user-facing operational helpers for
local experiments and acceptance runs. Stable reusable logic belongs under
`src/ouem`, and accepted conclusions belong under `docs`.

## Runtime boundary

The Komae workflow keeps two independently managed runtimes:

- **QGIS/OSGeo4W** owns GDAL/OGR, `osgeo`, and future native tools such as
  PDAL.
- Repository-local **`.venv`** owns OUEM orchestration and portable Python.

OUEM is not installed into QGIS Python, and `osgeo` is not installed into the
OUEM venv. Never start `.venv\Scripts\python.exe` from OSGeo4W Shell. GIS
Python is used only as a child-process worker through a file/argument contract.

## Komae PLATEAU acceptance workflow

### 1. Manual preprocessing

Display the instructions with:

```bat
scripts\work\plateau_komae_local_acceptance.cmd manual
```

Open the PLATEAU Building CityGML in PLATEAU GIS Converter GUI, select maximum
LOD and settings that retain 3D/Z geometry, and export the GeoPackage to:

```text
data\converted\building\plateau_komae\53393465_bldg_6697_op_convert.gpkg
```

This is external/manual **converted** data, not OUEM Native Building. The
helper does not automate or launch the GUI.

### 2. Capture the GIS child runtime

In **OSGeo4W Shell**, run:

```bat
scripts\work\plateau_komae_local_acceptance.cmd gis
```

This runs the main-branch GIS runtime check and writes the ignored runtime
snapshot used by the ingest child process. Close OSGeo4W Shell afterward.

### 3. Run OUEM ingest

In a **new ordinary Windows cmd or VS Code terminal**, install the current
checkout and run:

```bat
.venv\Scripts\python.exe -m pip install -e .
scripts\work\plateau_komae_local_acceptance.cmd ouem
```

The OUEM stage rejects inherited QGIS/OSGeo4W variables, verifies the exact
repository `.venv` interpreter, runs the automated tests, and ingests the
Converter GeoPackage. With no second argument it uses the canonical converted
path shown above. An explicit GeoPackage path remains supported:

```bat
scripts\work\plateau_komae_local_acceptance.cmd ouem D:\another\converted.gpkg
```

The provider resolves a unique Building layer. If there are zero or multiple
candidates, it fails with available layer names and asks for an explicit layer.
Pass one as the optional third argument:

```bat
scripts\work\plateau_komae_local_acceptance.cmd ouem data\converted\building\plateau_komae\53393465_bldg_6697_op_convert.gpkg bldg:Building
```

The helper checks the locally verified Komae Building count of 3637. This is
pilot acceptance metadata, not a general provider requirement. It does not
compare that count with unrelated layers in the intermediate GeoPackage.

Python 3.11.9 is the accepted local OUEM runtime but not a package-wide
minor-version lock; `pyproject.toml` remains authoritative. The confirmed GIS
runtime is QGIS 4.2.3, GDAL 3.13.3, and GIS Python 3.12.14.

The runtime snapshot records the GIS output encoding. OUEM captures GIS child
streams as bytes and decodes them explicitly, avoiding cp932/UTF-8 reader-thread
failures on Japanese Windows.

## Manual QGIS acceptance

After ingest passes, open `data\native\building\komae.gpkg` in QGIS:

1. confirm Building footprints in 2D View;
2. inspect `measuredHeight` and related attributes;
3. open QGIS 3D View using geometry Z; and
4. confirm height and three-dimensional form without artificial extrusion.

The successful Komae PoC contained 3,637 Building features, 3D Multi Polygon
geometry, EPSG:4979, and retained Z and source attributes.
