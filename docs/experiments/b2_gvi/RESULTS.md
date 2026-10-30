# B2 Phase 3 — Komae A/B CPU Technical E2E results

2026-10-30. **Bounded Technical E2E executed**: preserved B1 Current Voxel →
public VoxCity CPU generic API → geographic rasters → QGIS all-cell diagnostics,
saved project, separate-process reopen and observed GUI. This is not scientific
validation, photograph agreement, CPU/GPU comparison or Formal Acceptance.
Base main `a19943a3e8b3af7ffde0989bc8fc4f922d9f55e0` includes merged PR #124; the new implementation and tests
are carried by PR #125. See [usage](README.md) and the
[deferred backlog](../../planning/OUEM_B2_Deferred_Validation_Backlog.md).

## Actual input geometry and scope correction

Inputs are the completed `komae-a-3c-20261029-01` and
`komae-b-3c-20261029-01` directories under
`data/work/shared-vertical-domain/phase3c-20261029-01/outputs/`.
Consumed Current is `solar/current_voxels.npy`, bound to each Solar report;
the receipt binds the Voxel report and frozen configuration. Saved centres,
grid/CRS, masks, control arrays and all delivered output hashes pass inspection.
All **68 original files/site (136 total)** are protected before/after the run
and checked again after QGIS display. Five configuration input identities/site
also pass. No model regeneration or source-data transformation occurs.

**The request's 128×128 evaluation description conflicts with the saved runs.**
Both full computation domains are 128×128; the B1 evaluation mask is 64×64
(4,096 cells), u/v `[32:96,32:96]`, surrounded by 32 m context. We preserve that
existing scope and deliver full 128×128 rasters plus the extracted 64×64 ROI.
Nothing is cropped before the full CPU calculation. No new exterior context or
128×128 evaluation region is invented. An initial clarification was unnecessarily
framed as an authorization requirement; retaining the instructed existing B1
geometry does not itself change scientific assumptions.

| Input/check | A | B |
|---|---:|---:|
| Full shape, int8 u/v/up | 128×128×27 | 128×128×26 |
| TREE voxels (−2) | 95,735 | 87,384 |
| Building voxels (−3) | 34,802 | 21,641 |
| Subsurface (−1) / AIR (0) / Bareland surface (1) | 46,882 / 248,565 / 16,384 | 46,223 / 254,352 / 16,384 |
| Full valid / invalid observers | 12,638 / 3,746 | 13,923 / 2,461 |
| Full valid origins in TREE | 333 | 716 |
| Origin z-index range | 2–7 | 2–7 |
| Origin centre H range (m, saved D0 convention) | 22.086000443–27.086000443 | 22.620000839–27.620000839 |
| Canopy missing / outside cells | 0 / 0 | 0 / 0 |
| D0 effective H (m) | 19.586000442504883 | 20.1200008392334 |

Classification contains only −3/−2/−1/0/1; no code 14 or unknown class. All
ground arrays are finite. GVI surface masks/indexes independently match the B1
saved observers; no selected observer is outside Z or in an opaque class.
Starting in TREE is allowed by the audited API and separately counted, not
silently removed. Physical pedestrian-plane accuracy remains unverified.

The saved horizontal basis is geographic EPSG:4326, layout `uv_m/SOUTH_UP`,
u approximately north / v approximately east; projected reference EPSG:6677.
No array transpose or new north-up projected grid is substituted.

| Spatial item | A | B |
|---|---|---|
| Origin lon,lat | 139.5755044737887, 35.63204476258324 | 139.57479785778636, 35.63204324817326 |
| EPSG:6677 full bounds | [−23352,−40792,−23224,−40664] | [−23416,−40792,−23288,−40664] |
| EPSG:6677 evaluation bounds | [−23320,−40760,−23256,−40696] | [−23384,−40760,−23320,−40696] |

B lies west of A; their evaluation rectangles share an edge. Their context
domains overlap. Different D0/grid phase and finite domains prevent treating
overlapping results as a validated common-observer scientific comparison.

## Conditions and feasibility

Name: **CPU weighted first-TREE view index**. Explicit mode=None,
hit_values=(−2,), inclusion=True, fast_path=False, tree_k=0.5, tree_lad=1.0,
view_point_height=1.5 m, grid N_azimuth=120 / N_elevation=20,
elevation_min/max=−30/+30 degrees, roofs=False, OBJ off. Equal per-ray weights
and local u-axis sampling phase are inherited. No GPU/Taichi import or execution.

Ordinary Windows OUEM venv Python 3.11.9; VoxCity 1.7.0 pinned commit
`fa212656305328a9a657973bae26f352bfe813bc`, 136 installed Python sources
matching RECORD, as in PR #124. NumPy 2.4.6, Numba 0.68.0, Matplotlib 3.11.2,
CPU threads=2 (16 logical CPUs). Agg runs the API's real plot/show; only new
figures are closed and prior figure state is checked. No dependency update.

Before full execution, each 16×16 subset had 256 valid observers and the same
2,400 directions. Its values are discarded as evaluation evidence. The estimate
adds first-call wall time to repeat cost × full/subset valid-observer ratio ×
XY diameter ratio 8; it is a heuristic, not a guaranteed upper bound.

| Measurement | A | B |
|---|---:|---:|
| Subset first / repeat wall seconds | 4.880 / 0.095 | 0.141 / 0.104 |
| Repeat process CPU seconds / average cores | 0.188 / 1.97 | 0.219 / 2.10 |
| Subset sampled peak working set | 326.59 MiB | 286.50 MiB |
| Estimated full seconds | 42.40 | 45.53 |
| Feasible under recorded 600 s / 2 GiB probe limits | yes | yes |
| Final full public-API wall seconds | 5.463 | 4.740 |
| Full process CPU seconds / average cores | 8.766 / 1.60 | 9.391 / 1.98 |
| Full sampled peak working set | 286.96 MiB | 286.31 MiB |
| Cast directions (valid observers × 2,400) | 30,331,200 | 33,415,200 |

Timings include API JIT/cache loading, map calculation and Agg plotting; imports,
preflight hashing and raster export are excluded. Memory is current process RSS
sampled every 0.1 s (start/end included), not a guaranteed system-wide peak.
These are local observations, with full pytest/GUI work overlapping parts of the
execution, not an isolated performance benchmark. First-call timings do not
establish a pure cold-JIT measurement or general scale limit.

While the scope wording was being checked, independent full-domain checkpoint
calculations completed in A 4.579 s / B 4.900 s and generated full rasters. Final
runner results match those checkpoint NPY arrays exactly, including all NaNs.
This is repeated CPU consistency, not independent scientific validation.

## Values and geographic diagnostics

| Scope / statistic | A | B |
|---|---:|---:|
| Full finite / NaN | 12,638 / 3,746 | 13,923 / 2,461 |
| Full zero / positive | 63 / 12,575 | 26 / 13,897 |
| Full mean / median | 0.0970507683 / 0.1009396906 | 0.1229294268 / 0.1149977866 |
| Full min / max | 0 / 0.2557754022 | 0 / 0.2568487249 |
| Evaluation finite / NaN | 3,722 / 374 | 3,930 / 166 |
| Evaluation zero / positive | 12 / 3,710 | 0 / 3,930 |
| Evaluation mean / median | 0.1096442425 / 0.1103577663 | 0.1266523008 / 0.1202894269 |
| Evaluation p05 / p95 | 0.0783014740 / 0.1366302852 | 0.0823594078 / 0.1928547228 |
| Evaluation min / max | 0 / 0.2557754022 | 0.0330772685 / 0.2557754022 |

All finite values are in 0–1, with exact mask agreement and no repair/clamping.
All missing index cells are NaN-designated NoData, not zero. Score meaning is
the PR #124 first-TREE weighted chord; full crown depth, binary canopy visibility
and photograph-based green-view fraction have not been substituted.

Full and evaluation GeoTIFFs are Float64 EPSG:4326. Full output affine equals
the existing B1 Solar affine exactly; `TIFF[row,col]=UV[127-row,col]`. ROI pixels
are extracted after computation and use the full affine translated by (32,32).
Full-cell centre comparisons to original B1 centres have maximum longitude error
2.842170943040401e−14 degrees, latitude error 7.105427357601002e−15 degrees
for both sites. These are floating evaluation residuals, not geographic accuracy.
All-cell raster values/masks match NPY in OUEM and independently via GDAL in
existing GIS Python. No analytical reprojection/resampling occurs.

Original-file GIS helper samples (physical full-TIFF row/column):

| Site | Valid zero | ROI positive | ROI NoData |
|---|---|---|---|
| A | (127,0): 0 | (95,32): 0.14788198790328977 | (73,79): null |
| B | (127,126): 0 | (95,32): 0.13450648553675465 | (95,51): null |

All six returned the expected UV index, value and valid/nodata status.
This is the existing original-file helper, not QGIS provider Identify.

## QGIS and local evidence

Separate QGIS Python 3.12.15 / QGIS 4.2.3-Belém do Pará / GDAL 3.13.3
created `qgis/project.qgz`, `project.json`, `overview.png` and two ROI outlines.
The B2 helper has four layers/site, independent of Solar's seven-layer contract.
Separate-process reopen passes all eight references/CRS/ranges/alpha/visibility.

**GUI observed:** final project opened without missing-layer repair; B appears
west of A, red saved-ROI outlines share an edge, spatial value variation is
visible, excluded columns appear gray, exterior is white, and the A legend is
dimensionless 0–1 with project EPSG:6677. Both sites use the same ramp, verified
on reopen. No opaque rotated-grid fringe was observed. Layer-tree expansion
was not saved; the QGZ hash and all 136 protected B1 file hashes remain unchanged.
No photo/field-accuracy interpretation follows from the display.

Ignored evidence root: **`data/work/b2-gvi-phase3-20261030-01/`**.

- `a/`, `b/`: full `view_index.tif`, `evaluation_view_index.tif`, NPY/mask/index
  outputs, frozen settings, preflight and final reports.
- `benchmark-a/`, `benchmark-b/`: preflight, settings, resource/timing receipts.
- `qgis/`: relative-reference project, rendered PNG, receipts/ROI outlines.
- `gui-final-overview.jpg`, `gui-final-legend.jpg`, `gui-verification.json`:
  actual desktop observation and post-display source immutability checks.
- `spatial-check.json`, `gis-spot-check.json`, `repeat-check.json`:
  centre, exact original-cell and repeated-CPU checks.
- `full-api-a/`, `full-api-b/`, `full-domain-preview/`: preliminary full-domain
  checkpoints and display, superseded as final delivery by `a/`,`b/`,`qgis/`.
- `executed-b2_gvi.py`, `executed-b2_gvi_qgis.py`, commands/scripts and logs:
  local implementation/evidence snapshots; no large artifacts committed to Git.

| Final file SHA-256 | A | B |
|---|---|---|
| `report.json` | `76b537bb9004db57d5cbc23cd7041b77708142e28eff1d7eb960d54b196e39ef` | `a29cda81daae1dfe48e1b5f65e91ec1aa1e50d06a126c5dc7bf62672c5688083` |
| Full `view_index.tif` | `84a6dee1641928250154d09afce89fa4e26e18fcd7d412bcaa3835458ed1c64e` | `d5c42641bed4a238f27c93643762701d6a070c4566bac76ad79c4183b8185ba3` |
| `evaluation_view_index.tif` | `0e56c06a363f8393b01f2145c8365dc9268d2c613b7ecfcb0264b1a0665162e6` | `31688395f0d8a9e566ea08f050395438b5906ab950d3e1da295ccd47cf35e3a7` |

QGZ SHA-256: `7cd1f94da1f15df88124e93ba3ce480e78cd2a82b0708a06896f76bc7bd0856a`.
Receipts retain complete source/output identities, grids/affines and runtime
conditions; the table is a navigation aid. Git cloning does not supply the inputs.

## Tests, failures and limitations

Focused OUEM tests (new B2 handoff/export + GIS reference checks + PR #124
characterization): **60 passed, 1 GIS-only skipped, 38 warnings in 25.38 s**.
The same isolated GIS test is separately covered with existing QGIS Python:
**3 tests passed in 2.780 s**, one existing GDAL/OSR future-default warning.
Six real original-file spot checks pass with a similar GDAL warning.
Full suite, same OUEM venv with ordinary local permissions:
**1080 passed, 10 skipped, 336 warnings in 555.88 s**.

```powershell
.venv/Scripts/python.exe -m pytest -q -ra --basetemp=data/work/b2t-full
```

The short ignored base keeps Windows fixture paths manageable. Five skips require
unavailable Windows symlink privilege; five require isolated GIS/QGIS Python.
The new B2 GIS test is separately covered above; the four unchanged B1 GIS-only
tests were not rerun in GIS Python for this task. Warnings are 38 View/Agg
warnings plus existing rasterio affine deprecations and a source-H stat-clock
diagnostic. No final test failures. Logs remain under the local evidence root.

During development the RSS helper initially needed an explicit 64-bit Windows
handle signature; it was corrected before CPU benchmarking. The first GIS test
reached save/reopen but failed temporary cleanup with WinError 32 due to retained
QGIS references; explicit project/render reference release fixed it, and reruns
passed. A normal sandbox GIS launcher initially returned Access denied; existing
GIS runtime execution succeeded with the ordinary local-runtime permission scope.

The first sandbox full-suite attempt was interrupted after multiple unrelated
fixture failures. A targeted diagnostic confirmed NTFS `os.link` WinError 5
in an existing CHM acquisition synthetic fixture, even with a short repository
temporary path. The full suite was then rerun with the same OUEM interpreter
under ordinary local permissions. No approval/security setting or fixture policy
was changed, and no unrelated production code was repaired for these failures.

Unchanged open questions include CPU/GPU execution comparison, cutoff equality,
fast/generic tangency, public-fast portability, physical observation height,
source canopy/building accuracy, sampling/metric meaning and finite-domain
exterior sufficiency. Origins in TREE and overlapping full-domain results need
explicit interpretation in future comparisons. The authorized provisional CPU
profile is used only for this Technical E2E; no backlog row is closed, no formal
contract is changed, and no B1 Acceptance or historical result is rewritten.
