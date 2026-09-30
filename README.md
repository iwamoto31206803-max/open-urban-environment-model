# Open Urban Environment Model (OUEM)

**オープン都市環境モデル**

OUEM is an early-stage project for building reproducible 3D urban environment
models from open or otherwise available geospatial data and evaluating
human-scale environmental functions.

## Scope

- **Phase A — 3D Urban Environment Model Construction**
  - A1 — Tokyo Reference
  - A2 — National Baseline
  - A3 — GSI-LiDAR National Target
- **Phase B — Urban Environmental Assessment**
  - B1 — Solar & Shade Assessment
  - B2 — Green View Assessment

The current target is the **A1 Komae end-to-end pilot**. This repository
currently provides the Phase A architecture and package scaffold only; data
processing, model construction, VoxCity execution, and assessment capabilities
have not been implemented.

## Phase A data lifecycle

Phase A separates provider data from reusable downstream processing:

```text
RAW → NATIVE → STANDARD → MODEL → OUTPUT
```

`RAW` preserves source inputs, `NATIVE` holds provider-specific processing,
and `STANDARD` is OUEM's provider-independent boundary. Analysis-ready models
and derived GIS products follow in `MODEL` and `OUTPUT`. The canonical Komae
extent is defined in [`config/study_areas/komae_09LD3451.yaml`](config/study_areas/komae_09LD3451.yaml).

See the governing [Concept & Architecture v0.1](docs/OUEM_Concept_Architecture_v0.1.md)
and the [Phase A Implementation Design v0.1](docs/Phase_A_Implementation_Design_v0.1.md)
for the conceptual baseline and implementation contracts respectively.

## Relationship to VoxCity

[VoxCity](https://github.com/kunifujiwara/VoxCity) is intended to remain an
external upstream dependency and analysis engine. Its source is not vendored
or reproduced in OUEM. Future dependency selection and integration will follow
inspection of the upstream installation and API.

OUEM will focus on Japanese geospatial-data preparation, input adapters,
scenario configuration, orchestration, OUEM metrics, comparative scenarios,
post-processing, GIS output, and validation. Where reliable open-source
upstream functionality exists, the project should use it rather than duplicate
it.

## Development

The package skeleton uses a `src` layout and requires Python 3.10 or later.
The standard repository-local Python environment is `.venv` (on Windows its
interpreter is `.venv\Scripts\python.exe`). Create it and install OUEM in
editable mode before running Python modules:

```shell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe -m pytest
```

OUEM deliberately separates two execution environments. OSGeo4W/QGIS owns
native GIS executables and their bindings (GDAL, OGR, PDAL, and similar
tools), while `.venv` owns the `ouem.*` package and OUEM orchestration. OUEM
is not installed into the Python bundled with QGIS. A provider or pipeline
must launch native tools in an OSGeo4W-scoped process, then launch OUEM modules
with the explicit repository-local interpreter; it must not rely on whichever
`python` happens to be on `PATH`. This same boundary applies to future Tokyo
LiDAR and CHM processing.

Windows acceptance-test setup and launch instructions are self-contained in
[`scripts/work/README.md`](scripts/work/README.md). The checks are capability
based: the confirmed QGIS 3.44.14 / GDAL 3.13.3 combination is supported, and
QGIS 4.x is not required.

No OUEM repository license has yet been selected. See [`LICENSE`](LICENSE) for
the current licensing notice.
