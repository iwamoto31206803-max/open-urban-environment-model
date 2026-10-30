# B2 CPU GVI Synthetic Characterization v0.1

2026-10-30. Status: **Executed synthetic CPU characterization; no real-data
Technical E2E, scientific validation or Acceptance**. Baseline main
`0d441b5a8d9ba338d6377c8d4a3eedf33a093968` (PR #123 merged).
The [static audit](../../planning/OUEM_B2_VoxCity_GVI_API_Audit_v0.1.md)
and [E2E proposal](../../planning/OUEM_B2_Minimal_Technical_E2E_Design_v0.1.md)
remain dated source/design evidence. This report owns subsequent CPU observations;
it does not adopt B2-D01–D05 or revise their scientific assumptions.

## Reproduction and controls

Ordinary Windows PowerShell, repository `.venv/Scripts/python.exe`, Python
3.11.9, Windows-10-10.0.26300-SP0; VoxCity 1.7.0, NumPy 2.4.6,
Numba 0.68.0, Matplotlib 3.11.2, pytest 9.1.1. No dependency update.
The test fixture verifies PEP 610 commit
`fa212656305328a9a657973bae26f352bfe813bc` and all 136 installed Python
sources against RECORD through the existing `voxcity_provenance` helper.
This is installation integrity, not independent upstream-tree verification.
Installed source anchors/hashes are those in audit section 1 (R/V/G).
Numba uses two CPU threads, restoring the prior count afterward.

```powershell
.venv/Scripts/python.exe -m pytest tests/test_b2_gvi_synthetic.py -q -ra -s
.venv/Scripts/python.exe -m pytest tests/test_b2_gvi_synthetic.py tests/test_b1_physical_sanity.py -q -ra
.venv/Scripts/python.exe -m pytest -q -ra
git diff --check
```

All arrays are authored in memory as small int8 u/v/z grids. AIR=0, TREE=-2,
Building=-3, positive support=1. Targets=(-2,), inclusion=True; k=0.5,
LAD=1.0 and mesh=1 m unless stated. No generator, real data, saved B1 Run,
Voxel, Solar, GIS or GPU/Taichi runtime is used by the new tests. No simulator
source edits, own tracer, production B2 module or CLI. The existing B1
synthetic tests informed provenance/thread control and independent-oracle style;
their solar box-intersection implementation is not reused as a GVI oracle.

Expected values and absolute tolerance **1e-12**, relative tolerance zero,
were encoded before the first execution. The independent oracle is Python
`math.exp` with hand-specified chord lengths: full axial cell m, centre-to-face
m/2, diagonal full cell sqrt(2)*m. It calls no VoxCity function. Predictions
of branch behavior are source-informed; numeric expectations are independent.
These regression tolerances are not scientific accuracy criteria.

## Single-observer measurements

The exported `voxcity.simulator.visibility.view.compute_vi_generic` is the
first experiment route. The private `_trace_ray_inclusion_masks` is additionally
called directly with masks from `_prepare_masks_for_vi`, to isolate the actual
fast trace from public-wrapper fallback. It is an engine under test, never an
oracle. No exceptions are suppressed in this direct route.

Axial scene: shape (8,4,5), integer origin (1,1,2), direction +u, TREE at
(3,1,2). Deep crown fills u=3:7; distant moves TREE to u=6. Building or
positive surface at (2,1,2) blocks it. Inside origin=(3,1,2); above=(1,1,3).
The trace centres these integer origins by adding 0.5.

| Condition | Independent expected score | Measured generic / direct fast |
|---|---:|---:|
| No TREE | 0 | 0 / 0 |
| One TREE, L=1 m | 0.393469340287367 | 0.393469340287367 / same |
| Four-cell crown, same first chord | 0.393469340287367 | 0.393469340287367 / same |
| More distant TREE, same first chord | 0.393469340287367 | 0.393469340287367 / same |
| Building before TREE | 0 | 0 / 0 |
| Positive non-target surface before TREE | 0 | 0 / 0 |
| Start inside TREE, L=0.5 m | 0.221199216928595 | 0.221199216928595 / same |
| Origin one cell higher than TREE | 0 | 0 / 0 |
| k=0 or LAD=0 | 0 | 0 / 0 |
| k=1,LAD=1 or k=0.5,LAD=2; L=1 | 0.632120558828558 | 0.632120558828558 / same |
| mesh=2 m; L=2 m | 0.632120558828558 | 0.632120558828558 / same |
| k=4.6,LAD=1,L=1 | 0.989948164255366 | 0.989948164255366 / same |
| k=4.61,LAD=1,L=1; exp(-4.61)<0.01 | 0 (cutoff) | 0 / 0 |

All listed comparisons pass the stated tolerance. Thus ordinary first-TREE
scores follow `1-exp(-k*LAD*L)` in these cases, including the starting cell;
adding crown cells behind that target does not increase the result. This is
not binary hit counting or full-crown integration. The cutoff introduces a
discontinuity, not monotonic saturation. Equality exactly at T=0.01 is untested.

Six axial directions in an empty (4,4,4) domain all return zero on exit in
both traces. A four-ray point case in (6,5,5) has one +u target, one -v building,
one -u side exit and one +z exit. Generic returns **0.0983673350718416**,
equal to `(1-exp(-0.5))/4`: blocked/escaped rays remain in the denominator.

### Measured fast/generic disagreement

Shape (5,5,5), origin (1,1,2), direction (1,1,0), TREE=(2,2,2).
The centred ray traverses the target diagonal for sqrt(2) m. Both traces give
**0.506931308604760**, agreeing with `1-exp(-0.5*sqrt(2))`.
Adding Building at **(1,2,2)**, a zero-length corner-side contact, gives:

| Generic | Direct fast trace | Absolute difference |
|---:|---:|---:|
| 0 | 0.506931308604760 | 0.506931308604760 |

This is an executed disagreement. Source interpretation: generic checks both
side neighbours at a tie, while fast advances +u first and misses the +v-only
side cell. Neither is established as the physically preferred tangency rule.
Axis-aligned and the unobstructed exact-diagonal examples agree; these do not
prove general equivalence or exhaust near-tie/3D/fastmath behavior.

## Public full-grid API

Real `get_view_index` calls use `VoxCity`, `VoxelGrid`, `GridMetadata`, with
unused companion grids=None; no external data are needed for this entry point.
Domain=(6,3,5), support z=0 everywhere, TREE plane u=3,z=2 across v=0:3.
Grid sampling: one azimuth 0 degrees (+u), one elevation 0 degrees, equal
weights, explicit k/LAD/targets/inclusion, OBJ off. Coordinates stay u/v;
non-square output shape=(6,3), dtype=float64 is checked against entire arrays.

| Requested height m | Origin z index / centre m | Measured full-map result |
|---:|---|---|
| 0, 0.9 | 1 / 1.5 | 18 finite zeros |
| 1, 1.5 | 2 / 2.5 | Each v column: [0.393469340287367, same, same, 0.221199216928595, 0, 0]; sum=4.20482171337208 |
| 2 | 3 / 3.5 | 18 finite zeros |
| 9 | 10 / 10.5, outside array | 18 finite zeros, **not NaN** |

These match the independently authored arrays; height uses integer truncation
above the z=1 transition, not an arbitrary physical observer plane. The height=9
result is an observed capacity/validity limitation, not a physically valid view.
A separate four-azimuth (0/90/180/270), one-elevation public call with a single
TREE at (3,1,2) returns **0.0983673350718416** at (1,1), matching the all-ray mean.

Mask scene=(6,3,5), otherwise positive z=0 support, no TREE. Authored exceptions:
(0,0) all AIR; (1,0) water support=7; (2,0) negative support=-1;
(3,0) Building z=0:2; (4,0) positive code 14. With roofs=False, exactly
(0,0),(1,0),(2,0),(3,0) are NaN (14 finite zeros). Roofs=True admits (3,0),
leaving three NaNs (15 finite zeros). Code 14 remains finite zero. Entire
value/mask arrays match, rather than only comparing aggregate counts.

### Execution-path failure and diagnostic separation

The first run assumed public fast completion: **8 failed, 31 passed,
32 warnings in 39.11 s**. All eight failures were path assertions, despite
numerically correct fallback maps. A subsequent isolated diagnostic captured
the original exception: Numba `TypingError`, containing
`getitem(array(bool, 1d, C), UniTuple(int64 x 3))`. The public fast kernel is
entered, fails, and generic completes. These facts are measured with delegating
spies; source interpretation is that the wrapper supplies a 1D placeholder for
the unused allowed mask, while Numba type-checks the exclusion trace's 3D access.
The simulator source and algorithm are not patched.

The final tests explicitly assert this observed exception and generic completion
for fast=True calls. They are fallback regressions, **not fast-map successes**.
Direct fast trace tests above do execute the actual fast trace successfully.
An additional diagnostic calls the actual fast map with an explicitly shaped
unused boolean mask (6,3,5); its TREE-plane map agrees with the analytic array.
This bypasses the public wrapper only for diagnosis and is not a proposed OUEM
production workaround. Results apply to the recorded package/runtime versions;
fallback behavior in other environments remains unverified.

Matplotlib selects Agg before importing View. The public API's actual plotting
and show run, with no show mock. Each call verifies creation of a figure, closes
only newly created figures in finally, and checks the previous figure set and
input array bytes are preserved. Expected warnings are recorded, not suppressed:
`set_bad` pending deprecation and non-interactive Agg `show`. No OBJ/image file
is exported; headless execution/cleanup is verified, visual styling is not.

## Validation and limits

Final focused run (B2 plus B1 physical sanity): **49 passed, 36 warnings in
16.40 s**; B2 contributes 42 tests, no skips. The 36 warnings are 18 each of
the View colormap deprecation and Agg show warning described above.
Full suite: **1 failed, 1061 passed, 9 skipped, 334 warnings in 653.10 s**.
Failure: existing `test_komae_repair_qgis_export.py::test_cli_prints_path_and_areas`,
GeoPackage `DataSourceError: unable to open database file` beneath the long
sandbox temporary path. Isolated rerun with a short repository temporary path:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_komae_repair_qgis_export.py::test_cli_prints_path_and_areas -q -ra --basetemp=.b2-test-temp
```

**1 passed in 4.97 s**. This supports a temporary-path/environment issue;
the exact GDAL/SQLite cause is not established. No unrelated code was changed,
and the full suite is not relabeled all-pass. Nine skips: four require isolated
GIS/QGIS Python; five require unavailable Windows symlink privilege. Other
warnings are existing rasterio affine deprecations and a source-H stat-clock
diagnostic. An earlier full run using the initial path assertions was interrupted
after the fallback failure was diagnosed; only the completed final run supplies
the totals above. `git diff --check` and seven new-document local links pass.
Synthetic regression success is not permission to compute real-data GVI.

Metric definition, backend policy, physical observation plane and Technical E2E
transition await user review. CPU/GPU execution comparison is **Deferred /
Unverified**; the audit's GPU score/start-cell/precision/axis differences are
static leads, not a measured backend discrepancy. See the
[B2 backlog](../../planning/OUEM_B2_Deferred_Validation_Backlog.md).
Existing B1 backlog and formal Acceptance history are unchanged.
