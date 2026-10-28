# Real Komae Building + Terrain + Canopy solar PoC — 2026-10-28

Status: **COMPLETED exploratory three-element PoC**. Real source-H Building,
real Terrain and the existing estimated Height Envelope were integrated on
the exact PR #98 grid, and actual public VoxCity solar APIs completed Current /
No-Canopy comparison. Technical geometry, class invariance, observer and
difference-sign checks passed. Source-H eligibility, formal acceptance and
Phase 5 gates are unchanged.

Final run: `data/work/real-komae-solar/run-20261028-02/`.
[Reproduction/methods](README.md). Ordinary Windows OUEM venv Python 3.11.9;
no GIS Python. E2E elapsed 44.74 s. Fixed VoxCity 1.7.0 commit
`fa212656305328a9a657973bae26f352bfe813bc`, PEP 610 and installed source RECORD
checked before/after; no engine/dependency changes.

## Preflight and grid

PR #98 report SHA
`9af5854c6838ecf14af09e0315ca09c77756af5a962f4f473d4eb4a7ffe6eb64`
matched actual bytes, COMPLETED and Consumer PASS. All recorded input/output
hashes were checked, Consumer rerun on real source-H files, and actual saved
centres/CRS, ROI, DEM samples, effective ground/D0, ground indices, segments
and Building/ground voxels revalidated. Input immutability: **PASS**.

Envelope manifest SHA
`6121cbf732f8ece9553013be2483203f08faf9a8d364136a919c184b46738d68`, all three
rasters and every recorded source input were checked, including retained raw
CHMv2 tile, acquisition/crop, HAG source snapshot and limited review. Existing
semantic validation confirmed HAG metres plus the **same** source-declared
Tama T.P. DEM, no offset, CR=0.60. Hashes/declarations are not independent
survey accuracy, source/reviewer authentication or ecological validation.

Unchanged grid: 128×128×27, nominal 1 m, uv_m/SOUTH_UP;
D0_effective=19.586000442504883 m, axis rotation −0.150208117°;
adjusted horizontal mesh approximately 1.000093 m. ROI reference bounds:
`[-23320,-40760,-23256,-40696]`, 4,096 cells; computation bounds:
`[-23352,-40792,-23224,-40664]`, EPSG:6677. Actual saved centre coordinates,
origin/steps/ROI and IDs are reused, not the older projected-grid indices.
`grid.json` is byte-identical to PR #98.

## Canopy and voxel results

All 16,384 actual-centre samples were finite/covered and valid state 1.
NoData/invalid/outside: 0. State 1 is valid computation, not presence. Candidates
require valid/unmasked/finite top>bottom: positive **estimated** crown depth.

| Quantity | Result |
| --- | ---: |
| Positive-depth candidate columns | 11,741 |
| Valid zero-depth columns, not TREE candidates | 4,643 |
| Below-effective-ground intervals excluded | 0 |
| TREE columns after Building priority | 11,175 |
| TREE voxels | 95,735 |
| Potential TREE voxels suppressed by BUILDING | 3,078 |
| Candidate columns fully suppressed by BUILDING | 566 |
| Thin crowns expanded by existing engine rule | 12 |
| Positive candidates disappearing after rounding | 0 |

Public `Voxelizer.generate_combined` allocated 128×128×35 because its allocator
adds Building and tree heights. All layers above original Z=27 were verified
air before removal. **No occupied voxel was clipped**: both saved cases retain
the exact 128×128×27 grid. This connection removes redundant allocator air,
not geometry, and is not a custom voxel generator.

No-Canopy is Current with TREE replaced by air, **byte-identical to PR #98
voxels.npy**. Building (34,802 voxels), subsurface (46,882), surface (16,384),
Building IDs, DEM/effective ground/D0, origin and ROI remain unchanged.
Current air: 248,565 voxels. TREE in original Building/ground/surface: **0**.
All TREE intervals match a scalar reference after actual public API execution.

TREE bottom-edge minus source Envelope H: 0.013000–1.989000 m; top edge:
0.047998–1.916002 m. These include surface layer, rounding and thin-crown
rules, not H conversion or offsets. Relative API inputs subtract existing
conditioned ground; no ground snapping or source adjustment. Estimated TREE
above roofs may remain: priority does not validate those predictions physically.

## Fixed direct-solar comparison

Actual `get_direct_solar_irradiance_map` uses PR #96 conditions: true azimuth
135°, elevation 35°, DNI 800 W/m²; flat horizontal reference 458.861149 W/m².
Both cases share rotation and observers. k=0.6/LAD=1.0 are homogeneous and
**uncalibrated**. Roofs excluded. Actual nominal origin H is D0_effective+g+1.5,
not established as physical 1.5 m above source ground.

Common domain ground mask: 12,638 observers; 3,746 Building columns excluded.
ROI: **3,722 shared observers**, 374 Building columns excluded. API finite
masks match exactly; NaN is not zero solar.

| ROI statistic | Result |
| --- | ---: |
| Mean Current direct irradiance | 2.251779 W/m² |
| Mean No-Canopy direct irradiance | 427.916993 W/m² |
| Mean reduction (No-Canopy − Current) | 425.665214 W/m² |
| Canopy-related reduction cells | 3,471 / 3,722 (93.2563%) |
| Maximum reduction | 458.861149 W/m² |
| Building-obstructed cells (separate Terrain control) | 251 |
| Further reduction in fully Building-shaded cells | 0 |
| Irradiance increase cells | 0 |

Current range: 0–163.300337 W/m²; No-Canopy: 0–458.861149 W/m². The Building
control removes BUILDING while keeping conditioned ground and original
observers, separating Building obstruction from Terrain. The relation map
distinguishes Building shade, additional canopy attenuation, both and excluded
columns. Where Building already blocks the direct beam, TREE has no additional
effect; zero incremental reduction does not mean canopy absence.

Outside ROI: 8,916 shared observers; mean Current 58.695366, No-Canopy
308.377748, reduction 249.682383 W/m²; 5,067 reduction cells. These are separate
domain/halo diagnostics, not pooled into ROI. Sign tolerance 1e-9 W/m² is an
arithmetic budget, not scientific accuracy.

Strong modeled attenuation reflects the dense positive-height envelope and
assumed optical depth; transmission below 1% is cut to zero by the API. It is
**not measured canopy benefit or validated urban irradiance**. Meta CHMv2
local height/ground errors, false canopy over structures, XY/date alignment,
constant CR and optics remain unresolved. No parameter tuning was performed
to achieve this reduction. No weather, annual/global or heat result is claimed.

## Boundary diagnosis

Full source AOI maximum Building/Envelope H: 47.520199 m; plus 2 m edge
allowance: 49.520199 m. Lowest ROI observer: 22.086000 m. At 35°, conservative
horizontal reach is **39.180096 m**. Therefore **32 m is not an isotropically
sufficient halo bound**.

For this southeast sun, minimum sunward exit distance from ROI observers is
45.841918 m. Known-source height bound plus 2 m horizontal margin fits that
directional distance. This is conditional on available AOI heights; unknown
taller exterior objects remain possible. General exterior sufficiency is
**UNVERIFIED**; no expanded-domain convergence run, and different/lower suns
require a new check.

Cropping the original lattice to ROI (same Z/D0/observers) removes outside-ROI
occluders and raises Current irradiance in **861 cells**, up to 458.861149 W/m².
The two crop controls show why outside-ROI objects matter. They neither replace
the main grid nor establish absence of influence beyond its outer boundary.

## Artifacts, evidence and tests

Saved: voxel cases, TREE/sampling masks, sampled H/state, direct/difference
and Building-control maps, common observer mask/indices, cropped controls,
ROI, unchanged grid, statistics/report JSON, GeoTIFFs, plan/section PNG and
local results. NPYs passed exact pickle-disabled readback. GeoTIFFs use exact
engine EPSG:4326 affine, reversed-u rows, v columns. Plan/section inspected;
QGIS visual/formal acceptance not performed. Large/generated artifacts remain
ignored and are not committed.

| Evidence | SHA-256 |
| --- | --- |
| Current voxels | `c7ff44c47e3c85fd8b8c6908f1a9325bc0c81549eeb2a67069054fa66190728e` |
| No-Canopy = PR #98 voxels | `015ba23186093d6fedc9f7ee7bd2b683965dfb4da7f1404d02adbb666aee0561` |
| Unchanged grid.json | `bfc9ed90daec82c1caccdd635adf45ea7e4c33114da70bc089036743a9e80b19` |
| Current solar | `2b4a41176158fc0751a5c9f1fa1a59b665c4c8f851b405784fed8951af2efa03` |
| No-Canopy solar | `31be1dac90137c87dc74de8759fc51e0572e2dd0b274f51a103a5102cc83703d` |
| Difference | `45456faafe453386a00c3719097b733399fc24475d42446b6170829e04f852f8` |
| statistics.json | `7fd98de0a8f6bd69545d6423186b8d8c195a90ffdd02199b97df2899646cbee6` |
| report.json | `0fb30cf5f500dd726a3b1032ce0a9fb51bb9d84488bdc417a63cf15bdeecbdc2` |

Run `01` also completed; final `02` adds the full-AOI conservative halo bound,
explicit ground-index check and complete scene metadata. No scientific
parameters changed. Final run is the primary record; synthetic tests remain
separate from real-data evidence.

Focused suite: **10 passed, 15 warnings** (5.97 s): saved-centre sampling/CRS,
state/zero height/NoData, below-ground exclusion and fixed-Z failure, actual
TREE placement/Building priority, paired invariance, actual solar common
mask/origins/sign/crop control, and rejecting an unbound past success report.
Warnings are existing Rasterio/Affine PendingDeprecationWarnings.

Full command: `.venv/Scripts/python.exe -m pytest -q -ra --tb=short`.
Result: **897 passed, 5 skipped, 274 warnings in 198.92 s**, no failures.
Skips are Windows symlink privilege/Developer Mode cases (WinError 1314 or
unavailable privilege). Warnings are Rasterio/Affine PendingDeprecationWarnings
and the existing source-H stat/fstat clock diagnostic. PR #94–#98 synthetic/
real-integration regression tests passed. Log:
`data/work/real-komae-solar/pytest-full.log`. The suite used ordinary Windows
OUEM venv outside the known sandbox hard-link limitation, without weakening
publication safeguards. Cloud/Linux and formal QGIS acceptance were not run.
