# OUEM Standard Building v0.1

**Status:** PROVISIONAL contract; Komae-specific implementation accepted

**Scope:** Provider-independent 3D building geometry

This document provisionally defines the coordinate and geometry contract for
OUEM Standard Building v0.1. Standardization from PLATEAU Native Building must
produce data that conforms to this contract before model preparation or
adapter code consumes it.

Contract maturity is separate from dataset-specific acceptance. The
[Building local acceptance record](../experiments/a1_e2e_pilot/README.md)
records the Komae Native-to-Standard conversion result. The subsequent
[formal A3 acceptance record](acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md)
accepts the frozen Komae Standard Building + Terrain integration through
VoxCity voxel generation. Neither result makes this contract FINAL or
establishes applicability to other municipalities or datasets.

## 1. Coordinate reference

| Property | Requirement |
| --- | --- |
| Horizontal CRS | Projected CRS of the study area |
| Komae horizontal CRS | EPSG:6677 |
| Horizontal unit | metre |
| Vertical coordinate | Absolute elevation |
| Vertical datum/reference | T.P. (Tokyo Peil), the mean-sea-level reference used by PLATEAU |
| Vertical unit | metre |

The CRS must be explicitly recorded with every Standard Building dataset. The
meaning of the geometry's Z coordinates must also be recorded explicitly; Z is
an absolute T.P. elevation in metres, not a height relative to the ground or to
an individual building.

## 2. Geometry

Standard Building contains 3D building geometry. A container-specific 3D
geometry encoding may be selected by the implementation, but it must preserve
the geometry's X, Y, and Z coordinates and their meanings from Section 1.

## 3. PLATEAU source profile

The upstream source profile is:

| Property | Value |
| --- | --- |
| Source | PLATEAU CityGML |
| Source CRS | EPSG:6697 |
| Source coordinate reference | JGD2011 geographic coordinates with T.P. elevation |

For A1, CityGML reaches OUEM through a manual PLATEAU GIS Converter GUI step.
The resulting 3D GeoPackage is converted data; OUEM ingests it to produce
Native Building. This
provisional Standard contract applies only to the later Native-to-Standard
step; the ingest command does not itself produce Standard Building.

Standardization transforms the horizontal coordinates from the source CRS to
the study-area projected CRS. It preserves the interpretation of source Z as
absolute T.P. elevation in metres.

The accepted OUEM Native Building GeoPackage is the formal input to
standardization. The accepted Komae dataset records its 3D layer as EPSG:4979,
as verified by Native ingest/acceptance, while its retained PLATEAU Z ordinate
continues to mean absolute T.P. elevation rather than WGS 84 ellipsoidal
height. The EPSG:6697 row above describes the upstream PLATEAU source profile,
not the CRS label of the accepted Native GeoPackage.

## 4. Minimum metadata

The following common feature metadata is retained in addition to dataset-level
coordinate reference and provenance metadata:

| Field | Meaning |
| --- | --- |
| `ouem_id` | Stable OUEM feature identifier |
| `source_id` | Identifier in the source data |
| `source_dataset` | Source dataset/provenance reference |
| `source_lod` | Source level of detail |
| `measured_height` | Measured height in metres, nullable |

Provider-specific attributes need not be copied into Standard Building.

## 5. A1 Native-to-Standard implementation

The implementation reads the already accepted PLATEAU Native Building
GeoPackage; it does not operate PLATEAU GIS Converter or repeat Native ingest.
It requires the accepted Native `building` layer in EPSG:4979 and transforms
its horizontal EPSG:4326 component to the study-area EPSG:6677 CRS. It does not
ask PROJ to interpret the Native Z as EPSG:4979 ellipsoidal height. Instead, it
records every absolute T.P. input Z, performs the horizontal-only operation,
then explicitly restores and compares every Z before writing a 3D GeoPackage
layer under `data/standard/building/`. The acceptance check requires a maximum
Z difference no greater than `1e-9` metre. It reopens the written GeoPackage
and repeats the 3D, coordinate-count, Z-value, and deterministic-ID checks so
the validation includes OGR serialization rather than only in-memory geometry.

Buildings are selected when their horizontally transformed geometry intersects
the closed rectangle in the study-area configuration. The complete transformed
geometry is written: it is **not** clipped to the rectangle. Thus a building
crossing the boundary remains a complete building. Domain clipping belongs to
later model preparation, not Standardization.

The PLATEAU mapping is deliberately narrow:

| Standard field | Native source |
| --- | --- |
| `ouem_id` | Deterministic rule below |
| `source_id` | Accepted Native Building `id`; empty or duplicate values fail conversion |
| `source_dataset` | Literal provenance value `PLATEAU CityGML` |
| `source_lod` | First available of `source_lod`, `lod`, `lodType`, or `lod_type`; otherwise null |
| `measured_height` | `measuredHeight` (or already-normalized `measured_height`); otherwise null |

No other PLATEAU attribute is copied. Missing nullable LoD or measured-height
values remain null rather than being inferred. The Converter/Native field is
not renamed or modified in its source GeoPackage; its value is copied into the
existing Standard `source_id` field. The Standardizer does not require a
PLATEAU-specific `gml_id` column. The stable ID is `oub-` followed
by UUIDv5 using the RFC 4122 URL namespace and this exact UTF-8 name:

```text
ouem-standard-building-v0.1|PLATEAU CityGML|<source_id>
```

It therefore does not depend on input feature order or a particular run. The
adjacent manifest records the operation, study area, Z meaning, selection
semantics, ID rule, and validation results. This implementation does not change
this specification's provisional status. Komae conversion and downstream
adapter acceptance are recorded separately in the evidence linked above.
