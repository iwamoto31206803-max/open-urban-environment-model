# OUEM Standard-to-VoxCity Building Adapter v0.1 (A3)

**Integration pin:** VoxCity **1.7.0**, commit
`fa212656305328a9a657973bae26f352bfe813bc`.

## Architecture and responsibility boundary

The Phase A flow is `RAW → NATIVE → STANDARD → VOXCITY ADAPTER → VOXCITY`.
Standard Building remains the canonical absolute 3D, EPSG:6677 artifact with
`ouem_id` and source provenance. Standard Terrain remains the canonical
absolute elevation grid. This versioned, engine-specific adapter alone creates
VoxCity's 2D footprint, relative `height`, `min_height`, and numeric ID. It does
not mutate either Standard input or redesign either schema.

## Input and output contract

Both adjacent accepted manifests are mandatory: Standard Building v0.1 and
Standard Terrain v0.1. Both data layers must be EPSG:6677. The deterministic
output is EPSG:6677 GeoJSON with 2D geometry and properties `ouem_id`,
`voxcity_id`, `id`, `height`, and `min_height`. `voxcity_id` is the explicit
OUEM mapping field; `id` is the field consumed by VoxCity and has the identical
positive value. GeoJSON is directly readable as the
GeoDataFrame accepted by VoxCity's
`create_building_height_grid_from_gdf_polygon`. The adjacent JSON manifest pins
both inputs by SHA-256 and records AOI, mesh size, CRS handling, methods,
per-building diagnostics, warnings, and output SHA-256. Absolute paths are
audit identities; identical invocation paths and bytes produce identical files.

`ouem_id` is never replaced. Numeric IDs are assigned after lexically sorting
unique `ouem_id` values, then numbering from 1. This produces an explicit,
positive, unique, reproducible bijection independent of feature/ filesystem
order.

## Height, ground, and `min_height`

For building *b* the adapter uses

`height(b) = max(absolute geometry Z) - G_eff_abs(b)`, where
`G_eff_abs(b) = mean(raw VoxCity DEM grid cells where building_id_grid == id(b))`.

The adapter calls the pinned VoxCity local-GeoTIFF DEM rasterizer and building
rasterizer at the requested mesh size. It does not select arbitrary source DEM
pixels from the vector footprint. VoxCity's `process_grid` assigns that same
mean to all cells of an ID before voxelization. The manifest records grid shape,
sample count/range, geometry bottom, top, mean
ground and derived height so slope-induced roof error can be audited. Neither
`maxZ-minZ`, `measuredHeight`, nor one arbitrary DEM point is canonical.

For ordinary Komae buildings `min_height` is exactly `0.0`. Geometry bottom is
diagnostic only. No elevated-building semantics are inferred.

## Vertical compatibility gate

Fusion runs only if Building declares absolute T.P. and Terrain is `verified`
or `source-declared` T.P. `unresolved`, absent, or different references fail
before geometry processing. No datum is inferred from EPSG:6677.

## Running and acceptance

```console
ouem-adapt-voxcity standard-building.gpkg standard-terrain.tif \
  --output work/voxcity-buildings.geojson --meshsize 1 \
  --gis-runtime work/gis-runtime.json
pytest -q
python scripts/work/voxcity_komae_a3_acceptance.py \
  standard-building.gpkg standard-terrain.tif \
  --adapter-output work/voxcity-buildings.geojson \
  --gis-runtime work/gis-runtime.json --meshsize 1 \
  --expected 111 --report work/voxcity-e2e.json
```

Standard→Adapter acceptance requires 111 output features; valid 2D footprints;
unique canonical and numeric IDs; a bijection; positive heights; all normal
`min_height == 0`; complete Terrain coverage; EPSG:6677; vertical PASS; complete
manifest fields; and byte-identical reruns. The pinned-engine runner checks that
VoxCity produces nonempty height/ID grids, calls `Voxelizer.generate_combined`,
finds building voxels for every mapped ID, and reruns are array-identical. It
checks `processed ground + relative height ≈ absolute Standard roof`; normalized
voxel Z is shifted back by the raw DEM minimum and must agree within twice the
mesh size (rounding at ground and roof). The runner intentionally fails on another
reported VoxCity version. Commit verification must be performed by the
acceptance environment (`git rev-parse HEAD`) because installed Python packages
do not reliably expose a commit.

For visual acceptance, load the Standard Terrain, Standard Building, adapter
GeoJSON and `*.manifest.json` in QGIS. Style footprints by `voxcity_id` and
height; inspect representative low/high and largest
`ground_sample_max_abs-ground_sample_min_abs` buildings in 2D and 3D. Compare
the absolute roof target (`z_top_abs`) with `ground_eff_abs + height`, and check
both ends of sloped footprints against Terrain. Preserve the QGIS project plus
screenshots and the E2E report beside the frozen acceptance data. These checks
are required before declaring Komae A3 accepted and are designed to reveal
floating/sunken placement.

## Known limitations

This narrow adapter supports Komae, north-up EPSG:6677 Terrain and ordinary
grounded buildings only. It does not transform CRS, clip or repair geometry,
infer elevated structures, or provide vegetation/solar/thermal integration.
Buildings assigned no VoxCity building-grid cell fail rather than silently
using a nearest point. A feature-level
relative height necessarily yields roof variation over slopes in VoxCity; the
recorded terrain range makes that limitation measurable. Real-data and pinned
engine execution require the local frozen artifacts and external GIS/VoxCity
environments and cannot be substituted by unit fixtures.
