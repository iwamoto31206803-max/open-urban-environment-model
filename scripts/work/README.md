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
`data\raw\building\plateau_komae`. The script changes to the repository root,
checks the active `ogr2ogr` and Python installations, and runs the provider
with repository-relative study-area, Native, and Standard paths.

The expected workstation setup currently combines OSGeo4W for GDAL/OGR/PDAL
with a VS Code Python virtual environment for ordinary project work. The script
deliberately tests `osgeo.ogr` and `osgeo.osr` in the **currently active
Python**. It stops with a visible explanation if that Python cannot import the
bindings, even when OSGeo4W's `ogr2ogr` is available. It does not alter
`PATH`, `PYTHONPATH`, activate another environment, or otherwise hide a GDAL
and Python compatibility issue.
