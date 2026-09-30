# OUEM Standard Building v0.1

**Status:** PROVISIONAL contract pending A1 end-to-end VoxCity validation

**Scope:** Provider-independent 3D building geometry

This document provisionally defines the coordinate and geometry contract for
OUEM Standard Building v0.1. Standardization from PLATEAU CityGML must produce
data that conforms to this contract before model preparation or adapter code
consumes it.

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

The source profile for the initial implementation is:

| Property | Value |
| --- | --- |
| Source | PLATEAU CityGML |
| Source CRS | EPSG:6697 |
| Source coordinate reference | JGD2011 geographic coordinates with T.P. elevation |

Standardization transforms the horizontal coordinates from the source CRS to
the study-area projected CRS. It preserves the interpretation of source Z as
absolute T.P. elevation in metres.

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
