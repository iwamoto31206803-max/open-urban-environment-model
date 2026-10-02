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
for the conceptual baseline and implementation contracts respectively. The
[OUEM Standard Building v0.1](docs/OUEM_Standard_Building_v0.1.md) defines the
coordinate, geometry, PLATEAU source, and minimum metadata contract for
standardized buildings.

## PLATEAU Building Provider v0.1

A1 uses **PLATEAU GIS Converter GUI output as its technical ingestion
boundary**. Direct GDAL/OGR conversion of the tested CityGML exposed the layer
as `3D PolyhedralSurface`, but individual geometries became
`POLYHEDRALSURFACE Z EMPTY`. Converter output retained real `MULTIPOLYGON Z`
geometry, so direct CityGML conversion is not an OUEM A1 processing path.

The manual and OUEM steps are:

1. obtain PLATEAU CityGML;
2. convert it with PLATEAU GIS Converter GUI to a GeoPackage using settings
   that retain 3D geometry;
3. pass that GeoPackage to OUEM building ingest;
4. create and automatically validate OUEM Native Building; and
5. inspect position, visible geometry, height, and form in QGIS 3D View.

The successful Komae PoC produced `data/native/building/komae.gpkg` with layer
`building`, 3,637 features, 3D Multi Polygon geometry, EPSG:4979, retained Z,
and `measuredHeight` and other source attributes. Source and Native Building
counts matched at 3,637. This count records this Komae acceptance dataset only;
features in unrelated layers of the intermediate GeoPackage are not included.

Run ingest from the separate OUEM runtime after completing the GIS runtime
stage documented in [`scripts/work/README.md`](scripts/work/README.md):

```shell
ouem-plateau-buildings /path/to/converter-output.gpkg \
  --output data/native/building/komae.gpkg \
  --gis-runtime scripts/work/.runtime/plateau_komae_gis.json
```

The command runs from the repository-local OUEM Python environment
(`.venv/Scripts/python.exe` on Windows). GDAL, OGR, PDAL, and other native GIS
tools remain the responsibility of a separate OSGeo4W/QGIS environment. The
GIS acceptance stage records what child processes need in `--gis-runtime`;
OUEM Python never runs inside the GIS shell, and GIS Python is used only for the
standalone child worker. OUEM is not installed into GIS Python, and the OUEM
venv does not need `osgeo`. The confirmed local combination is QGIS 4.2.3,
GDAL 3.13.3, and GIS Python 3.12.14 with OUEM Python 3.11.9; these are observed
acceptance versions rather than package-wide requirements. Ingest copies the
resolved building layer without clipping, reprojection, geometry repair, or
dimensional reduction and preserves all source attributes. It rejects empty or
2D geometry, undefined CRS, zero features, missing `measuredHeight`, feature
loss, or field loss. A SHA-256 receipt enables reuse, and a manifest records
source provenance and validation results. The concise run summary reports
input/output counts, geometry type, CRS, Z and non-empty counts, and fields.

Manual visual acceptance checks Building footprints and attributes in QGIS 2D
View, then uses geometry Z in QGIS 3D View. The accepted data showed building
height and form without artificial renderer extrusion.

PLATEAU GIS Converter automation, direct CityGML parsing/conversion, Standard
Building generation, study-area filtering, VoxCity, terrain, LiDAR/CHM,
canopy, solar/shade, and GVI processing are outside this minimal A1 ingest.

This environment boundary also applies to future Tokyo LiDAR and CHM work:
PDAL/GDAL/OGR execution belongs to the GIS environment, while reusable OUEM
orchestration and domain logic belong to the project-local Python venv. See
[`scripts/work/README.md`](scripts/work/README.md) for the complete local setup
and acceptance commands.

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
After installing the project in editable mode, run the smoke test with:

```shell
python -m pip install -e .
python -m pytest
```

No OUEM repository license has yet been selected. See [`LICENSE`](LICENSE) for
the current licensing notice.
