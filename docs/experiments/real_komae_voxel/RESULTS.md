# Real Komae Building + Terrain VoxCity — 2026-10-28

Status: **COMPLETED technical experiment**. Actual pinned VoxCity public APIs
generated a 128×128×27 3D class array from the real PR #97 source-H Building
and existing Standard Terrain. Fresh Consumer, input integrity, grid/ID/ground,
whole-array scalar voxel and source roof-segment checks passed. Canopy and
solar were not executed. Source-H eligibility remains NOT_ESTABLISHED, formal
acceptance NOT_VERIFIED and Phase 5 A1–A4 OPEN.

Run: `data/work/real-komae-voxel/run-20261028-04/`.
[Commands, methods and PR #99 reuse](README.md). Windows 10.0.26300 AMD64,
repository OUEM venv Python 3.11.9. Elapsed run time 57.95 s. No OSGeo4W or GIS
Python was used. VoxCity 1.7.0 / commit
`fa212656305328a9a657973bae26f352bfe813bc` was verified by the existing PEP 610
origin and installed source RECORD check (136 files); this is not an independent
upstream-tree comparison. No dependency or engine source was modified.

## Inputs and preflight

Building:
`data/work/real-komae-source-h/run-20261028-04/standard/standard.gpkg` and its
adjacent candidate v0.2 manifest/receipt, with the actual Raw→Converter→Native
chain. Fresh Consumer **PASS**, 173 buildings, 32,689 vertex occurrences; full
artifact set rehashed at use and completion. No reliance on a historical PASS.

Terrain:
`data/work/terrain-reproducibility/komae-20261026-01/generated/standard.tif`
and its manifest, EPSG:6677, Float32, north-up 0.5 m, NoData −9999. Its
source-declared Tama T.P. is explicitly compared to Building source-declared
EPSG:6695 H. Source/Standard bytes remain unchanged. This checks declared
compatibility and numerical alignment, not independent datum realization.

Study area: `config/study_areas/komae_09LD3451.yaml`,
`[-23600,-40800,-23200,-40500]`, EPSG:6677. Existing ROI/halo definitions were
loaded directly from `canopy_shadow_poc.py` without invoking its processing:

| Scope | EPSG:6677 bounds | Extent |
| --- | --- | --- |
| Evaluation ROI | `[-23320,-40760,-23256,-40696]` | 64×64 m |
| Computation domain | `[-23352,-40792,-23224,-40664]` | 128×128 m; 32 m halo |

Building and Terrain horizontal extents overlap; ROI/domain lie inside the
study area. All 16,384 actual computation-centre DEM samples were covered,
valid and finite. No interpolation, filling, source-grid modification or
outside extrapolation occurred.

## Actual engine grid and saved model

The actual VoxCity grid is **uv_m/SOUTH_UP**, axis 0 approximately north,
axis 1 approximately east; no transpose/flip is inserted between engine
rasterization and voxelization. SW lon/lat origin is
`[139.5755044737887,35.63204476258324]`. Per-index steps are:

```text
u = [-2.8945527427470587e-08, 9.013698669181103e-06] degrees
v = [ 1.1040875268262413e-05, 2.3565512627209694e-08] degrees
centre(i,j) = origin + (i+0.5)*u + (j+0.5)*v
```

Nominal mesh is 1 m; actual horizontal adjusted meshes are
1.0000931801 / 1.0000932372 m. Axis 0 true azimuth is −0.150208117°.
Exact extent is reconstructed by origin, 128u, 128v, and their sum; the
independently transformed projected NE is not assumed to define that corner.
All actual centre lon/lat and easting/northing arrays are saved. This is not
the previous EPSG:6677 regular projected grid. The projected ROI membership
mask selects 4,096 actual cells, separate from the 16,384 computation cells.

| Output | Result |
| --- | ---: |
| 3D shape / dtype | 128×128×27 / int8 |
| Total class voxels | 442,368 |
| Building (−3) | 34,802 |
| Ground/subsurface (−1) | 46,882 |
| Common Bareland surface (1) | 16,384 |
| Air (0) | 344,300 |
| Building horizontal columns | 3,746 |
| Intersecting / retained Buildings | 41 / 41 |
| Outside actual computation domain | 132 |
| Buildings crossing computation boundary | 16 |
| Overlapping multi-building engine cells | 0 |

All 41 selected geographic supports are valid. Numeric IDs retain the mapping
from all 173 canonical IDs, including gaps. Whole source Building geometries
remain in unchanged Standard; complete derived footprints and source/OUEM/engine
IDs are saved without clipping. Rasterization naturally covers only cells of
the computation domain. All returned engine IDs/footprints match their inputs;
no engine overlap ID merging or lost/no-cell Building was allowed. The
owner-grid/height fixed point stabilized in two rasterization calls.

Of the 41 selected Buildings, 37 whole footprints lie inside DEM bounds and
4 extend outside those bounds; those 4 also cross the computation boundary.
Their complete footprints are retained, but effective ground is estimated only
from covered **computation-grid owner cells**. Full external-footprint DEM
coverage and external terrain/building voxels are not claimed. Inventory and
boundary/coverage fields for every source Building are in `report.json`.

## Vertical and geometry diagnostics

| Quantity (m) | Min | Median | Max |
| --- | ---: | ---: | ---: |
| Raw sampled Terrain H | 19.586000 | 22.865499 | 24.504999 |
| Engine-conditioned absolute ground | 19.586000 | 22.870001 | 24.504999 |
| Conditioning change (effective − raw) | −0.319425 | 0 | 0.561471 |
| Surface upper edge − effective ground | 0.501001 | 0.927469 | 1.500000 |
| Surface upper edge − raw Terrain | 0.380001 | 0.932501 | 2.032000 |
| Building segment upper edge − source roof H | 0.196291 | 0.658521 | 1.413052 |

Per-building source roof H ranges 26.389709–44.944079 m; effective owner ground
20.334909–23.932000 m; derived relative height 2.669989–21.240259 m. Source
geometry bottom − effective ground is −0.439424–0.027409 m. Source roof H
equals effective owner ground + relative height within 1e-9 m. No datum
conversion, H offset, source-height adjustment or ground snapping was applied.

VoxCity's existing `process_grid` averages raw DEM within each owner ID and
re-normalizes its minimum. This engine-required MODEL conditioning is saved
separately from the raw samples and unchanged Standard DEM. Here
**D0_raw = D0_effective = 19.586000442504883 m**; equality is measured, not
assumed in code. D_eff is conditioned ground − D0_effective. Installed Numba
rounds float32 D_eff, retains the surface layer at g−1 and starts grounded
Building at g. Nominal voxel H edges are D0_effective+k, centres add 0.5 m.
The measured surface/roof offsets include the retained surface layer and
rounding. In particular the 2.032 m surface-to-raw maximum includes local
conditioning, and is not an H transformation error or an applied correction.

All 442,368 actual engine classes/indices match the independent scalar-rule
oracle. Every Building cell starts immediately above the generated surface;
missing, floating/buried or clipped columns: **0**. Independent whole-footprint
cell intersections match every engine segment and contributor ID. Maximum
source roof-segment error 1.413052 m passes the 2 m voxel discretization budget;
that budget is distinct from exact source H retention. No anomalous overlap
or Building loss was detected. Tests separately require engine ID remapping
to fail rather than silently accepting merged source identities.

Local `plan.png` and `section.png` were visually inspected. The plan shows the
same grid for Terrain, IDs and heights with the evaluation mask marked; the
section shows the conditioned ground, retained surface layer, Buildings and
air. GeoTIFF array and coordinate readbacks passed. QGIS 2D/3D visual acceptance
was not performed; these images are technical diagnostics, not formal acceptance.

## Reusable evidence and limits

`grid.json`, twelve numeric/boolean NPY arrays, sparse segment/contributor JSON,
whole-footprint EPSG:4326 GeoJSON with per-building height/ground/ID fields,
five exact-affine EPSG:4326 GeoTIFFs, plan/section PNGs, report and local results
are saved under the run directory. All arrays reload exactly with pickle
disabled. Each GeoTIFF has reversed-u rows and v columns; its pixel centres
match the engine, without a false regular EPSG:6677 affine. Inputs and output
fingerprints are recorded in the report. Large/generated artifacts are ignored
and are not committed.

| Evidence | SHA-256 |
| --- | --- |
| Input Standard Building | `a23829bbcb689a3e830535b7654f0c5b892554b0ad26e0222eaf146e5b9aca3c` |
| Input Standard Terrain | `0afb6d1706b97bd39c8c93ff8feb580094fe585f567e2de1f2081c082602f90a` |
| grid.json | `bfc9ed90daec82c1caccdd635adf45ea7e4c33114da70bc089036743a9e80b19` |
| voxels.npy | `015ba23186093d6fedc9f7ee7bd2b683965dfb4da7f1404d02adbb666aee0561` |
| building_ids.npy | `95cb1a7e3c3bc73e4e2f7450a2991803b0e5e93dc313bddb1b4619f76a64b575` |
| terrain_H.npy | `2754e8c05ae60c8be312f98f347d26dcb83e3fc47c8fb6f08aba9d444a793a9f` |
| Completed report.json | `9af5854c6838ecf14af09e0315ca09c77756af5a962f4f473d4eb4a7ffe6eb64` |

The 2.5D roof proxy does not reproduce all LoD2 roof/wall geometry. A common
Bareland surface is not observed land cover. Source-declared vertical semantics
are not surveyed accuracy; observation-date alignment is unverified. The 32 m
halo is a retained initial geometry domain; solar sufficiency must be checked
for PR #99 conditions. No Canopy, Solar or heat evaluation, profile eligibility,
formal acceptance or Phase 5 gate change is included.

Earlier runs remain FAILED: `01` checked projected-geographic validity before
domain selection and rejected one invalid projected footprint outside the
computation domain (none of the 41 selected supports needs repair). `02`
generated voxels but detected implementation-file changes during development
and rejected completion. Runs `03` and final `04` both completed. The final
run refines scalar QA at the float32 half-cell rounding boundary; an actual
engine boundary test verifies that refinement. All 12 saved arrays and the
exact grid are byte-identical between the two completed runs. Comparison:
`data/work/real-komae-voxel/repeat-array-comparison.json`, SHA-256
`51541e765c17251269c77c3bd1cadb03f5a012e9fa4b0be2d8ac074d8c09ffab`.

## Tests

New focused suite: **9 passed, 5 warnings** (5.94 s), using authored fixtures
and actual public VoxCity calls: centre sampling/CRS/orientation, DEM boundary
and NoData failure, D0_effective differing from D0_raw, scalar surface/building
placement, source ID remapping failure, full boundary footprint preservation,
sloped DEM voxel generation, NPY/GeoTIFF readback and exact GeoTIFF XY mapping,
plus actual-engine float32 rounding just below a half-cell tie.
Warnings are Rasterio/Affine PendingDeprecationWarnings.

Final full command: `.venv/Scripts/python.exe -m pytest -q -ra --tb=short`.
Result: **887 passed, 5 skipped, 259 warnings in 205.07 s**, no failures.
The five skips concern Windows symlink privilege / Developer Mode (WinError
1314 or unavailable privilege). Warnings are Rasterio/Affine matrix-operation
PendingDeprecationWarnings and the existing source-H stat/fstat diagnostic.
Log: `data/work/real-komae-voxel/pytest-final.log`. Existing synthetic source-H
2.5D, VoxCity voxel and solar regression tests passed. The whole suite used
the ordinary Windows OUEM venv outside the known sandbox hard-link restriction;
no publication safeguard was weakened. Cloud/Linux validation was not run.
