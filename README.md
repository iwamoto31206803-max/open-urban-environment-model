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

The current target is the **Komae Phase A pilot**. This repository implements
Standard Building and Terrain preparation plus the versioned A3
Standard-to-VoxCity Building adapter; engine execution remains an explicit
external acceptance stage.

## Local data layout and Phase A lifecycle

Local datasets are organized by processing stage:

```text
data/
├─ raw/        # provider/source data as acquired
├─ native/     # accepted OUEM Native contract artifacts
├─ standard/   # accepted OUEM Standard contract artifacts
├─ model/      # model/engine-ready representations
├─ output/     # model and analysis outputs
└─ work/       # non-authoritative, reproducible processing intermediates
```

The canonical pipeline is:

```text
raw
  ↓
OUEM ingest
  ↓
native
  ↓
OUEM standardization
  ↓
standard
  ↓
model
  ↓
output
```

The formal lifecycle is `raw → native → standard → model → output`. `work` is
not a formal lifecycle stage: it is a side workspace for non-authoritative,
reproducible technical intermediates needed to produce formal artifacts.

The current PLATEAU Building branch uses that side workspace as follows:

```text
raw
  │ external/manual processing
  ▼
work
  │ OUEM ingest
  ▼
native
  │ OUEM standardization
  ▼
standard
```

For PLATEAU, source CityGML belongs under `data/raw/building/plateau_komae/`,
while PLATEAU GIS Converter output belongs under
`data/work/building/plateau_komae/`. OUEM's accepted Native Building is under
`data/native/building/`, and Standard Building is under
`data/standard/building/`. The Converter output is an external/manual
processing intermediate, **not** OUEM Native Building.

The Komae Tokyo 0.5 m DEM source convention is
`data/raw/terrain/tokyo_23ku_dem_050m/komae/09LD3451.tif`. Terrain uses a validated Native manifest
rather than duplicating unchanged raster bytes, followed by Standard GeoTIFF
creation under `data/standard/terrain/`:

```shell
ouem-accept-terrain data/raw/terrain/tokyo_23ku_dem_050m/komae/09LD3451.tif \
  --output data/native/terrain/komae_09LD3451.json \
  --provider "Tokyo Metropolitan Government" \
  --source-dataset "Tokyo 0.50 m bare-earth DEM" \
  --vertical-reference-status source-declared \
  --vertical-reference "T.P." \
  --vertical-reference-source "Tokyo Metropolitan Government source metadata"
ouem-standardize-terrain data/native/terrain/komae_09LD3451.json \
  --output data/standard/terrain/komae_09LD3451.tif \
  --study-area config/study_areas/komae_09LD3451.yaml
```

See the [provisional Terrain contract](docs/OUEM_Standard_Terrain_v0.1.md).
EPSG:6677 is horizontal only; the Tokyo source declares T.P. separately.
Standard Terrain remains canonical rather than an engine-specific artifact.

Analysis-ready models and derived GIS products continue under `data/model/`
and `data/output/`. All local data locations are ignored by Git except for
directory markers; real datasets must not be committed. The canonical Komae
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
ouem-plateau-buildings data/work/building/plateau_komae/53393465_bldg_6697_op_convert.gpkg \
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

PLATEAU GIS Converter automation, direct CityGML parsing/conversion, LiDAR/CHM,
canopy, solar/shade, and GVI processing are outside this minimal A1 ingest.

## OUEM Standard Building v0.1 conversion

The separate `ouem-standardize-buildings` command consumes accepted Native
Building, selects complete buildings intersecting the configured study-area
rectangle, transforms the accepted EPSG:4979 Native coordinates' EPSG:4326
horizontal component to EPSG:6677, and preserves every Z as absolute T.P.
elevation without treating it as ellipsoidal height. Boundary-crossing buildings are
not clipped. It writes only the five Standard metadata fields and a validation
manifest; see the [provisional contract](docs/OUEM_Standard_Building_v0.1.md)
for the exact nullable mappings and deterministic ID rule. This milestone does
not include VoxCity or make the provisional contract final.

The Komae real-data local acceptance passed with 3,637 Native input buildings
and 111 study-area-selected Standard output buildings. The output was EPSG:6677
3D Multi Polygon, with required metadata, zero Z delta, and deterministic IDs
all passing. This is acceptance of the current conversion for the Komae dataset,
not general PLATEAU coverage or finalization of the provisional specification.
The detailed record is in
[`experiments/a1_e2e_pilot/README.md`](experiments/a1_e2e_pilot/README.md).

```shell
ouem-standardize-buildings data/native/building/komae.gpkg \
  --output data/standard/building/komae.gpkg \
  --study-area config/study_areas/komae_09LD3451.yaml \
  --gis-runtime scripts/work/.runtime/plateau_komae_gis.json
```

This environment boundary also applies to future Tokyo LiDAR and CHM work:
PDAL/GDAL/OGR execution belongs to the GIS environment, while reusable OUEM
orchestration and domain logic belong to the project-local Python venv. See
[`scripts/work/README.md`](scripts/work/README.md) for the complete local setup
and acceptance commands.

## Standard-to-VoxCity adapter

[VoxCity](https://github.com/kunifujiwara/VoxCity) remains an external upstream
engine; its source is not vendored. The A3 adapter targets exactly VoxCity
1.7.0 commit `fa212656305328a9a657973bae26f352bfe813bc`, combines both accepted
Standard inputs, and retains a deterministic `ouem_id`↔numeric-ID manifest.
The output exposes both the OUEM audit field `voxcity_id` and VoxCity's actual
consumer field `id` with equal positive values. Effective ground is computed
from the raw pinned-VoxCity DEM cells selected by its `building_id_grid`, and
the acceptance runner reaches `Voxelizer.generate_combined`.
See the [adapter contract and acceptance procedure](docs/OUEM_VoxCity_Adapter_v0.1.md).

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

On Windows, do not run the repository virtual environment from OSGeo4W Shell.
Native GIS tools and OUEM use separate processes and Python installations; see
the [runtime architecture](docs/architecture.md) and the reproducible
[local acceptance procedure](scripts/work/README.md).

No OUEM repository license has yet been selected. See [`LICENSE`](LICENSE) for
the current licensing notice.
