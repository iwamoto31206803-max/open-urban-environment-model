# OUEM Standard Terrain v0.1

**Status:** PROVISIONAL pending Komae real-data acceptance and downstream adapter validation

**Scope:** The Phase A Komae bare-earth terrain elevation surface. This is not
a nationwide provider-normalization or model-engine contract.

## 1. Representation and quantity

Standard Terrain is a single-band GeoTIFF raster of **bare-earth terrain
elevation**, not DSM surface height. Its sample type is Float32. Horizontal
coordinates and elevations are in metres.

| Property | v0.1 requirement |
| --- | --- |
| Horizontal CRS | EPSG:6677, JGD2011 / Japan Plane Rectangular CS IX |
| Bands | one terrain-elevation band |
| Sample type | Float32 |
| Grid | north-up and unrotated |
| Standard NoData | `-9999.0` |

EPSG:6677 describes only the horizontal CRS. It supplies no vertical datum or
vertical-reference meaning.

## 2. Grid and values

An already compliant source retains its dimensions, affine transform, extent,
pixel size, and every valid Float32 elevation exactly. In particular, the
Tokyo reference tile retains its 0.50 m grid. Standardization neither
reprojects nor resamples v0.1 input. A non-EPSG:6677 raster fails explicitly;
a future contract must define deterministic reprojection and resampling before
such input can be accepted.

The source must declare a finite NoData value. Source masked cells become
`-9999.0`, and `-9999.0` is declared as the output GeoTIFF NoData value. Source
sentinels are never interpreted as elevations; valid values are not altered.

## 3. Vertical reference

Vertical reference is mandatory semantic provenance, separate from horizontal
CRS. `vertical_reference_status` is exactly one of `verified`,
`source-declared`, or `unresolved`. Verified and source-declared values require
both a reference name and evidence/source. Unresolved requires both fields to
be null.

The Tokyo 23-ku 0.5 m DEM source profile used for Komae is recorded as
**source-declared T.P. (Tokyo Peil / Tokyo Bay mean sea level)**. This is a
provider declaration, not an OUEM independent survey or benchmark comparison,
so its status is not `verified`. The evidence is Tokyo Metropolitan Government
official source metadata declaring JGD2011, Plane Rectangular CS IX, and
elevation relative to Tokyo Bay mean sea level; the official release relating
the 23-ku point cloud, ground data, and 0.5 m grid DEM; and the Bureau of
Construction documentation identifying Tokyo Bay mean sea level as T.P.:

- [Tokyo Metropolitan Government Open Data Portal](https://portal.data.metro.tokyo.lg.jp/)
- [Release: 区部の3次元点群データを公開](https://www.metro.tokyo.lg.jp/information/press/2024/10/2024103126)
- [東京都公共基準点・水準基標について](https://www.kensetsu.metro.tokyo.lg.jp/jimusho/tech/04-kijyun/kijyunsetu)

This source-specific declaration does not make T.P. a default for Standard
Terrain or other DEM providers. OUEM does not infer T.P., orthometric height,
ellipsoidal height, or a vertical EPSG identifier from EPSG:6677. Unresolved
status remains valid and does not prevent terrain standardization. Numerical
combination of unresolved Terrain with Building Z or other vertical data is
prohibited until compatible verified or source-declared semantics have been
established; that compatibility check and any fusion are outside this version.

## 4. Native acceptance decision

The lifecycle remains `RAW → NATIVE → STANDARD → MODEL → OUTPUT`. Because the
Tokyo source is already a GeoTIFF with the required raster semantics, Native
acceptance does not create a meaningless byte-for-byte copy. It validates the
source and writes an OUEM-controlled Native JSON manifest. The manifest pins
the RAW file by absolute path and SHA-256, records structural/statistical and
vertical-reference metadata, and is the only accepted input to the
Standardizer. Loading it revalidates both the fingerprint and raster metadata.
Thus RAW is not called Standard and the semantic boundary remains auditable.

## 5. Provenance and validation

The Standard GeoTIFF has an adjacent `*.tif.manifest.json`. It identifies the
provider and source dataset, RAW path and fingerprint, Native manifest,
source/output CRS and resolution, source/Standard NoData, output fingerprint,
vertical reference fields, processing statement, implementation/schema
version, cell statistics, and grid/elevation preservation checks. Processing
timestamps are audit metadata and are not part of the deterministic raster
fingerprint.

MODEL remains a later engine-specific representation. Standard Terrain v0.1
is not claimed to be VoxCity-ready, and this contract implements no VoxCity
adapter, vertical transformation, data fusion, or model-grid resampling.
