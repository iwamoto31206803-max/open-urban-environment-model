# OUEM Phase A Implementation Design v0.1

**Status:** Initial implementation scaffold

**Scope:** Phase A — 3D Urban Environment Model Construction

**Conceptual baseline:** [OUEM Concept & Architecture v0.1](OUEM_Concept_Architecture_v0.1.md)

> **Current-status note (2026-10-10):** This initial scaffold design is retained
> as historical context. Its pending/deferred statements, including Sections 5,
> 6a, and 10, do not describe all current implementation status. Native-to-Standard
> Building is implemented with [Komae local acceptance](../experiments/a1_e2e_pilot/README.md).
> Standard Terrain and the VoxCity adapter through voxel generation have
> [formal A2](acceptance/OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md) and
> [formal A3](acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md)
> Komae acceptance records. Follow the current linked contracts for behavior;
> Standard Building and Terrain remain PROVISIONAL. These implementation
> milestones use A2 for Terrain and A3 for the adapter, distinct from the
> conceptual variants below. Acceptance does not establish nationwide operation
> or downstream environmental simulations.

This document translates the existing conceptual baseline into repository and
data-boundary decisions. It does not replace or revise that baseline, and it
does not specify Phase B implementation.

## 1. Phase A scope and variants

The scaffold supports all three Phase A variants:

- **A1 Tokyo Reference** — the first end-to-end reference implementation;
- **A2 National Baseline** — a practical nationally scalable baseline; and
- **A3 GSI-LiDAR National Target** — a future national LiDAR-based target.

The architecture must also accept future providers without coupling model
preparation or external engines to any one source dataset.

## 2. Data lifecycle

```text
RAW → NATIVE → STANDARD → MODEL → OUTPUT
```

| Stage | Meaning |
| --- | --- |
| **RAW** | Original or near-original source data. |
| **NATIVE** | Source/provider-specific processed representation. Provider-specific information may remain here. |
| **STANDARD** | OUEM common representation independent of source provider. |
| **MODEL** | Analysis-ready representation generated from Standard data. |
| **OUTPUT** | Derived outputs intended for GIS use, validation, or downstream environmental assessment. |

The corresponding processing architecture is:

```text
Acquire → Native Processing → Standardization → Model Preparation
        → External Engine Adapter
```

Acquisition and Native Processing may understand provider conventions.
Standardization is the boundary that removes that obligation from downstream
components. Model Preparation consumes only Standard contracts. VoxCity is an
external 3D processing engine: its adapter receives prepared standardized
inputs and must not become a home for source-specific conversion.

Examples of interchangeable provider branches are:

```text
Tokyo LiDAR     → Tokyo Native CHM   → Standard CHM
Meta CHM        → Meta Native CHM    → Standard CHM
Future GSI LiDAR → GSI Native CHM    → Standard CHM

PLATEAU CityGML → GIS Converter 3D GeoPackage → PLATEAU Native Building
                                                   → Standard Building
Future GSI Building source → GSI Native Building   → Standard Building
```

Downstream model preparation and VoxCity adapters must not need to know which
provider produced a conforming Standard representation.

## 3. Repository responsibilities

| Location | Responsibility |
| --- | --- |
| `src/ouem/` | Portable processing logic, organized by lifecycle/component. |
| `scripts/` | Thin user-facing launchers and entry points. |
| `config/` | Parameters and versioned study-area definitions. |
| `data/` | Local RAW, NATIVE, STANDARD, MODEL, and OUTPUT lifecycle. |
| `docs/` | Architecture, contracts, and implementation decisions. |
| `tests/` | Automated validation and justified small fixtures. |

Shell, BAT, CMD, and PowerShell files should preferably invoke package code,
not contain core processing logic. Core processing should remain portable
where practical.

Native GIS runtimes and OUEM Python have a deliberate execution boundary.
GDAL, OGR, PDAL, and similar native GIS operations run in the OSGeo4W/QGIS
environment, while orchestration and reusable OUEM logic run from the
repository-local Python virtual environment (`.venv`) in a separate shell. A
narrowly scoped GIS worker may be launched only as a child process; it must not
require the `ouem` package to be installed in GIS Python. OUEM's venv must not
be launched from the OSGeo4W/QGIS shell. This keeps the same boundary usable
for later building, Tokyo LiDAR, and CHM providers without coupling OUEM's
Python dependencies to an OSGeo4W installation. The currently accepted local
combination is QGIS 4.2.3, GDAL 3.13.3, and GIS Python 3.12.14 with OUEM Python
3.11.9; these observations do not impose package-wide version requirements.
External GIS stdout and stderr are captured as bytes and decoded at the
boundary rather than implicitly with the OUEM process locale. This is required
because GDAL/GIS Python output can be UTF-8 while Japanese Windows defaults to
cp932.

The Python namespaces mirror the processing boundaries: `acquire`, `native`,
`standardize`, `model`, and `adapters`. Terrain, building, and canopy are kept
as explicit domains where applicable. Empty namespaces intentionally contain
no placeholder implementations.

## 4. Canonical Komae A1 extent

`config/study_areas/komae_09LD3451.yaml` is the authoritative definition of
the canonical OUEM analysis extent for the Komae A1 end-to-end pilot. It uses
EPSG:6677 and defines a 400 m × 300 m extent.

Input-provider tile systems **must not define the OUEM analysis extent**.
Tokyo LiDAR tiles, PLATEAU third-level meshes, Meta CHM tiles, and future GSI
tiles can overlap the canonical extent differently. Implementations will
select intersecting provider data, mosaic it where necessary, and clip the
result to the canonical extent. This work is deferred from this scaffold.

## 5. Standard Building v0.1 — PROVISIONAL

The provisional [OUEM Standard Building v0.1](OUEM_Standard_Building_v0.1.md)
defines provider-independent 3D building geometry. Its coordinate contract is:

- the study-area projected horizontal CRS, which is EPSG:6677 for Komae;
- horizontal coordinates in metres;
- Z coordinates expressed as absolute T.P. (Tokyo Peil) elevation in metres;
  and
- explicit CRS, Z interpretation, and source provenance.

The initial source profile is PLATEAU CityGML in EPSG:6697 (JGD2011 geographic
coordinates with T.P. elevation). Standardization projects the horizontal
coordinates while preserving the absolute T.P. interpretation of Z.

Container and container-specific geometry encoding remain implementation
choices. They must preserve the Standard Building coordinate and geometry
contract and will be validated during the A1 end-to-end VoxCity test.

For A1, PLATEAU GIS Converter GUI is the manual technical boundary between
CityGML and OUEM. Direct GDAL/OGR conversion was evaluated, but tested feature
geometry became `POLYHEDRALSURFACE Z EMPTY`. OUEM therefore ingests the
Converter's 3D GeoPackage as converted input and produces Native Building,
preserving `MULTIPOLYGON Z` geometry and source attributes without
reprojection or clipping. The separate Native-to-Standard command now treats
the accepted EPSG:4979 Native GeoPackage as its formal input, transforms its
EPSG:4326 horizontal component to EPSG:6677, explicitly preserves the retained
absolute T.P. Z, and selects buildings intersecting the canonical Komae extent
without clipping their geometry. The ingest command still does
not claim to produce Standard Building. Standard Building remains provisional
until A1 end-to-end VoxCity validation.

## 6. Standard CHM and tree-height-platform

OUEM intends to reuse the existing tree-height processing concept:

```text
source-specific CHM → Native CHM → Standard CHM
```

The current external `tree-height-platform` already provides working concepts
for Tokyo LiDAR processing, Meta CHM processing, Native CHM, Standard CHM, and
incremental processing. It is treated as an external/proven provider whose
Standard CHM output can later connect to OUEM. Its code is neither copied nor
refactored in this scaffold.

The current Standard CHM concept is:

- GeoTIFF with `Float32` values;
- height unit: metre;
- valid height values are greater than or equal to zero;
- NoData value: `-9999`;
- DEFLATE compression; and
- source CRS and resolution retained unless a downstream operation explicitly
  requires transformation.

## 6a. Standard Terrain v0.1 — PROVISIONAL

The provisional [OUEM Standard Terrain v0.1](OUEM_Standard_Terrain_v0.1.md)
defines the Komae bare-earth Float32 GeoTIFF contract. A lightweight Native
acceptance manifest validates and pins the unchanged RAW raster;
Standardization preserves its EPSG:6677 grid and valid elevations while
normalizing NoData. Horizontal EPSG:6677 is independent of vertical reference,
which is source-declared as T.P. for the Tokyo reference DEM based on Tokyo
Metropolitan Government metadata. Model
preparation and any VoxCity adapter remain deferred.

## 7. Incremental and restartable processing

Expensive geospatial processing should be incremental and restartable where
practical, especially for LiDAR and municipality-scale processing:

```text
input → check expected output → reuse valid existing output if appropriate
      → otherwise process → record result
```

Output validation must be stronger than mere file existence when practical.
The exact validation and recording rules belong to each future operation. No
workflow engine is introduced in v0.1.

## 8. Provenance

Future Standard datasets must retain enough provenance to identify at least:

- source/provider and source dataset;
- acquisition or download date where relevant;
- observation or reference date where known;
- license;
- processing method and version;
- CRS; and
- important processing parameters.

A lightweight, versionable manifest adjacent to or referencing a dataset is
sufficient for v0.1. A provenance database is intentionally not designed yet.

## 9. Data and Git policy

Git contains code, configuration, documentation, schemas/contracts,
manifests/provenance metadata, and justified small test fixtures. Large source
geospatial data and large Native, Standard, Model, or Output products belong
in local or external storage. Repository ignore rules cover typical point
cloud, raster, GML, GeoPackage, shapefile, and temporary products without
prohibiting intentional small fixtures or metadata.

## 10. Deferred implementation

This design deliberately does **not** implement PLATEAU GIS Converter
automation, direct CityGML parsing/conversion, Native-to-Standard Building,
model-domain building clipping, Tokyo LiDAR or Meta CHM processing,
canopy-bottom estimation, Crown Ratio models, VoxCity installation/execution,
voxelization, solar/shade analysis, or green-view analysis. Those operations
require subsequent implementation and validation work after these boundaries
are established.
