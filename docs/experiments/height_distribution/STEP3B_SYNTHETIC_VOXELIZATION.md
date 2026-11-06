# STEP 3-B — Synthetic Distributed-Height Voxelization

2026-11-06. **PASS / COMPLETED_SYNTHETIC_ONLY / EXPERIMENTAL** for the accepted
cases below, with explicit input rejections retained as **BLOCKED**.
`terrain_integration_ready=false`, `scientific_validation=NOT_VERIFIED`,
`formal_acceptance=NOT_VERIFIED`. No real-data or environmental result is claimed.
Full Windows/Ubuntu CI evidence for the PR is recorded in its description.

## Baseline and audit

Based on main `2a0585dd821ca8c783f7565c83fb3b363b1611e5` after PR #162 merged.
Reviewed [STEP 3-A implementation](../../../src/ouem/synthetic_height_distribution.py),
[self-contained tests](../../../tests/test_synthetic_height_distribution.py),
[record](STEP3A_SYNTHETIC_HEIGHT_DISTRIBUTION.md),
[T4-B1](../../../src/ouem/candidate_b_t4b1.py),
[T4-B2](../../../src/ouem/candidate_b_t4b2.py),
[T5](../../../src/ouem/candidate_b_t5.py),
[real voxel ground/occupancy QA](../../../src/ouem/real_komae_voxel.py) and
[H0](../../planning/OUEM_H0_Height_Distribution_Design_Audit_v0.1.md).
The existing Standard/Adapter and representative-height path remain unchanged.
The H0 table's stage numbering is historical; this is current **STEP 3-B**.

Installed public API: `voxcity.generator.voxelizer.Voxelizer(1., "Standard")`
`.generate_combined(height, segments, ids, land_cover, dem, tree, print_class_info=False)`.
VoxCity **1.7.0**, commit **fa212656305328a9a657973bae26f352bfe813bc**;
Numba path required by this bounded profile, CPU **2 threads** during calls
(previous thread setting restored afterward). No engine private rounding or
flattening function is called by the adapter/oracle.

| Audited fixed API behavior | Consequence / independent check |
|---|---|
| `height_grid` determines allocation, segments determine occupied intervals | Require height equal to the maximum segment high in every cell; no NaN reaches engine replacement logic |
| DEM first subtracts raw minimum, then `process_grid` averages nonzero owner IDs and subtracts the new minimum | Independently compute absolute owner means using existing `effective_ground`; D0 is **minimum conditioned absolute ground**, not necessarily raw DEM minimum |
| All segments in a cell use its single owner-conditioned ground | Explicit owner choice required for competition; retain every contributing building and face separately |
| Numba receives relative DEM as Float32 | Compare actual `process_grid` against independent ground, including Float32 identity; test rounding-sensitive DEM |
| `g = int(Float32(G−D0)+.5)+1` at 1 m | Surface at `g−1`; first grounded building at `g`, not the surface layer |
| `start=g+int(low+.5)`, `stop=g+int(high+.5)` | Positive half values round upward, stop exclusive; disjoint intervals retain AIR gaps, overlapping intervals form a union |
| `Nz=ceil(max(height + conditioned_relative_dem))+1` with tree=0 | Audit every surface and integer stop against Nz **before** execution; do not assume consistent height/segments alone guarantee capacity |
| NumPy slice writes can truncate at capacity | Reject clipping risk; never modify engine rounding or silently pad height_grid |

The installed `generator/voxelizer.py` and `geoprocessor/raster/core.py` were
read directly. Fixed code paths do no horizontal flip in `generate_combined`.
This synthetic adapter passes the explicit Derived row/column arrays unchanged
(north-up grid rows southward, columns eastward); no new geographic resampling,
VoxCity geodetic grid construction or Solar/GVI direction mapping is established.

## Adapter input and vertical profile

[Implementation](../../../src/ouem/synthetic_height_voxel.py) is a separate
experimental adapter. It replays the existing STEP 3-A procedure against the
recorded source geometries, grid and provenance before trusting a Derived.
Identity/state/top/grid/procedure edits fail closed. This intentionally requires
the current synthetic procedure/environment identity, rather than serving as a
general persisted-Derived reader. No new geometry algorithm is implemented.

The 1 m EPSG:6677 grid and the DEM array share shape and row/column registration.
The caller explicitly declares the same **arbitrary synthetic vertical datum**
as the Derived; T.P. or another datum is rejected. Original DEM and Derived are
copied/retained and hashed. The owner rule is fixed: a single source owns its
cell; competing sources require explicit cell→contributing-source selections.
Numeric IDs are assigned by sorted source_id. No highest-roof owner heuristic.

For each contributing building-cell summary, initial continuous extrusion is:

```text
low = 0
high = absolute_top_z − owner_conditioned_absolute_ground_z
```

The building-cell top is STEP 3-A's maximum of its **known, method-supported**
face contributions. All faces, including lower/unsupported faces, remain in the
Derived provenance; they are not interpreted as separate cavities or solids.
Each contributing building yields an interval, even when another building owns
the cell. All use that cell owner's ground, exactly as the fixed API does.
Every contributing building top must be known and above that ground. Unknown
summaries, nonpositive high, invalid intervals and quantized-empty intervals
block execution. No fill, ground adjustment or D0 redefinition is performed.

`representative` is a separately requested constant absolute top per source,
using the same STEP 3-A geometry, footprint and grid. It is not a fallback for
centre. Distributed methods reject representative-top arguments. All methods
use identical DEM/ownership. Tiny valid roof supports still produce a full
occupied voxel column: coverage and original support remain recorded, rather
than claiming subvoxel geometry accuracy.

An independent scalar oracle is built from inputs **before** calling Voxelizer.
It allocates expected GROUND=-1, surface=1, BUILDING=-3 and AIR=0, computes
integer intervals without using engine output or engine discretization helpers,
then compares the entire int8 volume. Reuses only existing `effective_ground`
and installed-engine provenance verification. T4-B2's ownership/ground/capacity
conditions inform QA; its continuous-occupancy assertion is not applied to
disjoint fixtures. Input arrays and the deep-copied public API arguments are
hashed before/after calls. Changed handoff arrays are rejected by rebuilding
the adapter inputs from the retained Derived and DEM.

## Executed comparison

Windows OUEM venv: Python **3.11.9**, NumPy **2.4.6**, Shapely **2.2.0**,
Numba **0.68.0**. No dependencies installed or changed. Both invocations used
the same STEP 3-A authored demonstration, flat absolute DEM Z=2, owner ID=1.
Class counts below list **BUILDING / GROUND / AIR / surface**. Shapes use the
original two grid axes followed by Z. Distinct capacities are compared by
explicitly padding BUILDING masks with AIR above each output solely for QA.

| Case / method | Shape | Class counts (−3 / −1 / 0 / 1) |
|---|---|---|
| Flat, all three | 2×2×9 | 32 / 0 / 0 / 4 |
| Slope, representative | 2×2×19 | 72 / 0 / 0 / 4 |
| Slope, centre | 2×2×17 | 54 / 0 / 10 / 4 |
| Slope, cell_max | 2×2×19 | 62 / 0 / 10 / 4 |
| Step, representative / cell_max | 1×2×8 | 14 / 0 / 0 / 2 |
| Step, centre | 1×2×8 | 9 / 0 / 5 / 2 |
| Partial, representative / cell_max | 1×1×11 | 10 / 0 / 0 / 1 |
| Partial, centre | 1×1×10 | 9 / 0 / 0 / 1 |
| Thin eave, representative / cell_max | 1×1×10 | 8 / 0 / 1 / 1 |
| Roof hole, representative only | 3×3×9 | 72 / 0 / 0 / 9 |

Flat voxels are identical across all three methods. Slope centre→cell_max
changes **8 voxels / 4 columns**, representative→centre **18 / 4**,
representative→cell_max **10 / 3**. Step centre→cell_max changes **5 / 1**;
partial centre→cell_max **1 / 1**. Representative and cell_max match for the
step, partial and thin-eave authored cases.

For slope `Z=10+2x+3y`, centre tops in north-to-south row-major order remain
`[15.5,17.5,12.5,14.5]`, cell_max `[18,20,15,17]`. Subtract ground 2, round high,
then add anchor g=1: centre stops `[15,17,12,14]`, cell_max `[17,19,14,16]`.
The step's centre highs are `[2,7]` and cell_max highs `[7,7]`.

Thin-eave **centre is BLOCKED** (`TOP_UNKNOWN`); cell_max retains coverage .1,
top Z=10.2 and high=8.2. Roof-hole **centre and cell_max are BLOCKED** because
one footprint cell has no roof top. The independently requested representative
model has its own explicit constant top; it does not resolve those unknowns.
Expected input rejections are enumerated separately; unexpected rejection or
partial output failure cannot publish a completed root manifest.

## Ground, intervals, rounding and capacity

Independent authored occupancy fixtures, not inferred from top-only roofs:

| Fixture | Effective ground / D0 / indices | Output and QA |
|---|---|---|
| Raw DEM `[10,14,13]`, IDs `[1,1,0]`, high `[8,8,0]` | Ground `[12,12,13]`, D0=12 (raw min=10), surface `[0,0,1]`, anchors `[1,1,2]` | 1×3×9; classes 16 / 1 / 7 / 3 |
| DEM=10, intervals `[0,2]`, `[4,6]` | D0=10, anchor=1, occupied `[1,3)` and `[5,7)` | 1×1×7; classes 4 / 0 / 2 / 1; AIR gap preserved |
| DEM `[2,4]`, IDs `[1,2]`, high `[2,20]` | D0=2, anchors `[1,3]`, stops `[3,23]` | 1×2×23; classes 22 / 2 / 20 / 2 |

Additional pytest fixtures verify overlapping intervals `[0,4]` and `[2,6]`
occupy exactly layers 1..6, explicit competing owner choices retain all sources,
and intervals from both buildings use the selected owner ground. DEM
`[10,10.49999999]` with different owners becomes Float32 relative `[0,.5]`:
surface `[0,1]`, whereas a Float64-only oracle would incorrectly give `[0,0]`.

High values `2.999999, 3, 3.000001, 3.499999, 3.5, 3.500001` occupy
`3,3,3,3,4,4` layers, respectively. No rounding rule is changed.
Explicit capacity failure: raw DEM `[0,.5]`, IDs `[0,1]`, height `[0,.5]`,
segment `[0,.5]` in the second cell gives `Nz=ceil(.5+.5)+1=2`, but that
cell's anchor=2 and rounded high=1 need stop=3. **BLOCKED before Voxelizer**.
Mismatched height_grid/segment high (both smaller and larger), explicit level
limits and sub-half-layer vanished intervals are also rejected.

QA reports `D0 + stop − target_top_Z`: the **upper edge** of the highest occupied
voxel. This includes the one-layer surface-to-building anchor convention. For
flat/integer cases the upper-edge difference is +1 m; slope centre and partial
cell_max reach +1.5 m; thin support is approximately +.8 m. These are not pure
nearest-rounding errors or evidence of physical roof bias. The lower edge of
the highest layer is one metre lower. T4-B2's historical `D0+last_index` roof
diagnostic and this explicit upper-edge diagnostic must not be conflated. No
offset is applied to make the diagnostics zero. Cases with noninteger relative
ground additionally include its Float32/rounding error.

## Artifacts, provenance and reproducibility

```powershell
.venv/Scripts/python.exe -m ouem.synthetic_height_voxel --run-dir data/work/step3b-synthetic/final-c
.venv/Scripts/python.exe -m ouem.synthetic_height_voxel --run-dir data/work/step3b-synthetic/final-d
```

Each run performs **18** accepted public Voxelizer calls, plus three recorded
expected input rejections. About **8 s** wall time per complete CLI invocation
in this environment, including imports/JIT. All **164 files**, including **90
NPY arrays**, match byte-for-byte across independent processes. Reproduction
scope is this installed environment; no cross-platform byte identity is claimed.
Old synthetic runs were not overwritten. All generated data remain ignored.

| Identity | SHA256 |
|---|---|
| Root manifest, both final runs | `7ea442d42a2e44d1fafb0787c1babb9aa9c47e0b1e5ca7a0bc6001316ecc01ac` |
| Comparison JSON | `6ad07960cb72a9f9ed46fc428943be66f800bbf78f9eee928c82523423659832` |
| Full relative-path→file-SHA inventory (canonical JSON) | `48801dbba3e7916da69a51b412477a7fc6b8693160541151027f20a3af2884f3` |
| Experimental adapter | `bd126d10f157d05b258e23fbf00f7041d10de9ca42de3d53b0c6436e846615c7` |
| STEP 3-A implementation, unchanged | `43bc89a67a4b6a29e34315ac882e20ad21d1a072589c118619e40a3b6601271d` |
| Installed VoxCity source-content identity | `33e2bfdbc8a677f53154e8cd16295603819c68cf9f24c7a4cdfeb196bcbcd0bd` |

Each method saves `height.npy`, `segments.json`, `ids.npy`, `dem.npy`,
`effective_ground.npy`, `voxels.npy`, full `metadata.json` and `qa.json`.
Manifests record input array dtype/shape/content SHA, full Derived and source
identities, explicit ownership/representative choices, helper implementation
SHAs, runtime/settings, engine pin and output file SHA. Repeated serialized
values are read back before a completed manifest is written. NPY never uses
pickle. The root manifest hashes child manifests and comparison; child manifests
hash every method artifact. Failed saves leave no completed manifest at that
level; failed overall acceptance leaves no completed root manifest.

Reused engine provenance verifier establishes PEP 610 VCS origin and checks all
**136** installed Python sources against package RECORD hashes. It does **not**
independently compare bytes to the upstream Git tree. Identity/source-state,
datum, DEM and handoff edits, changed results before saving, engine corruption
and partial writes are exercised by rejection tests.

## Tests, limits and STEP 3-C handoff

[New tests](../../../tests/test_synthetic_height_voxel.py): **31**, self-contained,
no Candidate B fixture imports. Public engine output is checked against manual
per-cell counts/endpoints and the independent input-derived integer oracle.

```powershell
.venv/Scripts/python.exe -m pytest -q -ra tests/test_synthetic_height_voxel.py tests/test_synthetic_height_distribution.py tests/test_candidate_b_t4b1.py tests/test_candidate_b_t4b2.py
```

**68 passed, 5 warnings, 15.94 s**, no failures or skips. Warnings are existing
Rasterio Affine PendingDeprecationWarnings. Includes all 25 STEP 3-A tests and
existing T4 synthetic audits; does not invoke saved Candidate B processing.
Full local pytest is not run; unchanged GitHub Actions Windows/Ubuntu full
regression remains the merge gate, with pip cache and `--durations=30` preserved.

Verified scope: small 1 m planar synthetic roofs, fixed explicit ownership,
continuous grounded top extrusions and separately authored multiple intervals,
pinned Numba API. Profile limits: at most 4096 horizontal cells, positive IDs
at most 4096, default at most 512 Z levels. Capacity/quantization failures remain
BLOCKED; no automatic padding, minimum-height rescue or unknown-height fill.
VoxCity classes are anonymous: source/segment provenance must accompany arrays.

STEP 3-C can use the saved validated synthetic pairs after explicitly agreeing
method, owner, unknown-support policy, coordinate-axis semantics and observation
conditions. It must preserve the DEM, D0, ID and index conventions and distinguish
upper voxel edge from source top. This experiment does not choose a formal
centre/max rule, infer cavities from roofs, accept real roof accuracy or define
future GSI processing. No real PLATEAU/T5, Canopy, Solar or GVI was processed;
no old run, Standard/Adapter, scientific assumption, Acceptance, engine code,
dependency or CI configuration was changed. Those connections remain
**NOT_VERIFIED**.
