# Local work files

Files in this directory are temporary, user-facing operational helpers for
local experiments and acceptance runs. They are not core processing logic,
normative specifications, or formal processing records.

Stable reusable processing logic belongs under `src/ouem`; generally useful,
maintained launchers belong in the formal `scripts` structure. Important
findings and accepted project decisions belong under `docs`.

## Komae PLATEAU local acceptance

`plateau_komae_local_acceptance.cmd` covers the manual preprocessing and OUEM
ingest stages, plus a separate GIS-runtime setup. GIS setup and OUEM ingest
must run in separate shells; the script never starts OUEM's venv Python from an
OSGeo4W/QGIS shell.

First display and follow the manual preprocessing instructions:

```bat
scripts\work\plateau_komae_local_acceptance.cmd manual
```

Open the PLATEAU Building CityGML in PLATEAU GIS Converter GUI, select maximum
LOD and settings that retain 3D/Z geometry, export a GeoPackage, and keep its
path for OUEM ingest. The helper does not automate or launch the GUI.

Separately, in the **QGIS/OSGeo4W command environment**, capture the GIS child
runtime:

```bat
scripts\work\plateau_komae_local_acceptance.cmd gis
```

This verifies GDAL/OGR and `osgeo`, then writes an ignored local runtime snapshot
for GIS child processes. Close that shell. In a **normal Command Prompt or VS
Code terminal**, use the existing repository-local `.venv`, install the pulled
OUEM revision, and run the OUEM stage:

```bat
.venv\Scripts\python.exe -m pip install -e .
scripts\work\plateau_komae_local_acceptance.cmd ouem D:\path\to\converted.gpkg
```

If `.venv` does not exist, create it with the ordinary project Python selected
for OUEM (for example, through VS Code's **Python: Create Environment**), not
with OSGeo4W Python. No package-wide Python micro-version is prescribed. The
confirmed OUEM workstation currently uses Python 3.11.9.

The second argument is the GeoPackage produced manually by PLATEAU GIS
Converter. It is required; the script does not guess a local filename:

```bat
scripts\work\plateau_komae_local_acceptance.cmd ouem D:\path\to\converted.gpkg
```

The provider resolves the unique Building layer. If the GeoPackage has zero or
multiple Building candidates it fails with available layer names and requests
an explicit layer. Pass that layer as the optional third argument, for example
`... ouem converted.gpkg bldg:Building`. The helper also checks the locally
verified Komae Building count of 3637; this is pilot acceptance metadata, not
a general provider requirement.

The environment boundary is deliberate:

- the active **OSGeo4W/QGIS GIS environment** owns GDAL, OGR, PDAL, and other
  native GIS tools; and
- `.venv\Scripts\python.exe` is the **OUEM Python environment** and owns the
  installed `ouem` package and Python orchestration code.

The GIS stage captures the external executables, GIS Python, and the child
environment needed by the small standalone OGR worker. The later OUEM stage
launches `.venv\Scripts\python.exe` only from a normal shell. It does not install
OUEM into GIS Python or require `osgeo` in `.venv`. The current confirmed GIS
runtime is QGIS 4.2.3, GDAL 3.13.3, and Python 3.12.14. These versions document
the acceptance result; they are not package-wide minimum requirements.

The snapshot also records the GIS runtime's preferred output encoding. OUEM
captures GIS child-process streams as bytes and decodes them explicitly, so a
Japanese Windows OUEM locale such as cp932 cannot raise `UnicodeDecodeError`
when a GDAL or GIS Python child emits UTF-8 diagnostics.

The OUEM stage prints input/output feature counts, resolved layer, geometry
type, CRS, non-empty/Z geometry counts, reuse status, and preserved fields.
After it passes, open `data\native\building\komae.gpkg` in QGIS. Confirm the
building footprints in 2D View and inspect the attribute table. Then open QGIS
3D View using geometry Z and confirm height and form without adding artificial
renderer extrusion.

This same responsibility boundary should be retained when Tokyo LiDAR and CHM
work is integrated: PDAL/GDAL/OGR operations belong to the GIS environment,
while orchestration and OUEM package logic belong to the project-local venv.
