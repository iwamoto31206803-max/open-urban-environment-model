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

The provider command recursively discovers building GML below a downloaded
PLATEAU package (for example, `udx/bldg/*.gml`). It also accepts conservatively
named PLATEAU building files such as `*_bldg_*_op.gml` placed directly in the
provider dataset directory. It converts each accepted file to a restartable
Native GeoPackage and writes one Standard Building GeoPackage containing every
complete building geometry that intersects the canonical study-area extent:

```shell
ouem-plateau-buildings /path/to/plateau-package \
  --study-area config/study_areas/komae_09LD3451.yaml \
  --native-dir data/native/building/komae \
  --output data/standard/building/komae.gpkg \
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
acceptance versions rather than package-wide requirements. Native outputs retain CityGML fields and XYZ
geometry. A source fingerprint receipt beside each Native file enables reuse;
`--force` rebuilds them. Standard output contains only the common OUEM fields,
uses the study-area horizontal CRS, and retains source Z as absolute T.P.
elevation in metres. Selection does not clip a boundary-crossing building.

The run prints discovery, feature, intersection, reuse, and geometry-failure
counts. A `.manifest.json` file beside the Standard GeoPackage records source
files and CRS, target CRS, study area and extent, vertical semantics,
parameters, timestamp, counts, warnings, and errors. PLATEAU downloading,
VoxCity execution, DEM, LiDAR/CHM, canopy, solar/shade, and GVI processing are
outside this provider's scope.

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
