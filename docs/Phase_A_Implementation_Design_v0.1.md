# OUEM Phase A Implementation Design v0.1

**Status:** Initial implementation scaffold

**Scope:** Phase A — 3D Urban Environment Model Construction

**Conceptual baseline:** [OUEM Concept & Architecture v0.1](OUEM_Concept_Architecture_v0.1.md)

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

PLATEAU CityGML          → PLATEAU Native Building → Standard Building
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

> **PROVISIONAL:** GeoPackage plus PolyhedralSurface is technically usable for
> the current PLATEAU test, but it is not established as OUEM's permanent
> internal building format. This contract may be revised after the A1
> end-to-end VoxCity test.

| Property | Standard Building v0.1 candidate |
| --- | --- |
| Container | GeoPackage |
| Geometry | 3D building geometry; PolyhedralSurface where supported |
| Coordinates | Projected CRS appropriate to the study area |
| Horizontal unit | metre |
| Vertical unit | metre |

Minimum common metadata:

| Field | Meaning |
| --- | --- |
| `ouem_id` | Stable OUEM feature identifier |
| `source_id` | Identifier in the source data |
| `source_dataset` | Source dataset/provenance reference |
| `source_lod` | Source level of detail |
| `measured_height` | Measured height in metres, nullable |

Every dataset must have an explicit CRS, an explicit interpretation of Z,
valid 3D building geometry, and retained source provenance. Provider-specific
attributes need not be copied into Standard Building.

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

This design deliberately does **not** implement PLATEAU conversion or mesh
discovery, building clipping, Tokyo LiDAR or Meta CHM processing,
canopy-bottom estimation, Crown Ratio models, VoxCity installation/execution,
voxelization, solar/shade analysis, or green-view analysis. Those operations
require subsequent implementation and validation work after these boundaries
are established.
