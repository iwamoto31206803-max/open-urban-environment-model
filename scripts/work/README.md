# Local work files

Files in this directory are temporary, user-facing operational helpers for
local experiments and acceptance runs. They are not core processing logic,
normative specifications, or formal processing records.

Stable reusable processing logic belongs under `src/ouem`; generally useful,
maintained launchers belong in the formal `scripts` structure. Important
findings and accepted project decisions belong under `docs`.

## Komae PLATEAU local acceptance

`plateau_komae_local_acceptance.cmd` is a readable Windows walkthrough for the
first local PLATEAU Building Provider acceptance run. Run it from Command
Prompt, optionally passing the provider dataset directory as its first
argument:

```bat
scripts\work\plateau_komae_local_acceptance.cmd D:\path\to\plateau-dataset
```

With no argument, it expects source data at
`data\raw\building\plateau_komae`. Before the first run after `git pull`, open
an OSGeo4W/QGIS command environment, change to the repository, and create the
standard repository-local OUEM environment:

```bat
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
scripts\work\plateau_komae_local_acceptance.cmd
```

The script changes to the repository root, checks the GIS tools and both Python
environments, and runs the provider with repository-relative study-area,
Native, and Standard paths. A different dataset directory may be passed as the
first argument.

The environment boundary is deliberate:

- the active **OSGeo4W/QGIS GIS environment** owns GDAL, OGR, PDAL, and other
  native GIS tools; and
- `.venv\Scripts\python.exe` is the **OUEM Python environment** and owns the
  installed `ouem` package and Python orchestration code.

The script captures the active GIS Python for the small standalone OGR worker,
then launches OUEM with `.venv\Scripts\python.exe`. It does not install OUEM
into OSGeo4W Python, require `osgeo` in `.venv`, or alter `PATH`/`PYTHONPATH` to
hide a compatibility issue. QGIS 3.44.14 with GDAL 3.13.3 has passed these
environment checks; QGIS 4.x is not required.

This same responsibility boundary should be retained when Tokyo LiDAR and CHM
work is integrated: PDAL/GDAL/OGR operations belong to the GIS environment,
while orchestration and OUEM package logic belong to the project-local venv.
