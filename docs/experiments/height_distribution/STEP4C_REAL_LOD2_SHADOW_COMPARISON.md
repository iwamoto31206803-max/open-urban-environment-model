# STEP 4-C — Real LoD2 Roof Height Distribution Shadow Comparison

2026-11-06. Baseline main **69d7cd286da76dc1e3f6f9c780d4407525ca23d9**
(PR #168 merged). **Technical execution PASS / Binary shadow PASS** for the
four fixed real F/S/M/C buildings. This is an isolated-building sensitivity
experiment, not validation of actual shadows. Inherited vertical status remains
CONDITIONAL; scientific/formal validation NOT_VERIFIED and
`terrain_integration_ready=false`.

## Answer: how much does the shadow change?

A is a uniform absolute top equal to the **maximum saved cell_max H** for that
building. B is the saved cell_max distribution. The representative definition
is local to this experiment, not a Formal Standard or accepted-model replacement.
All areas below use 1 m² per nonbuilding observer cell; delta is **B−A**.

| Sample | Valid observers | A shadow (m²/cells) | B shadow (m²/cells) | Delta (m²/cells) | Changed | Shadow→sun | Sun→shadow | Shadow IoU |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| F, flat control | 577 | 26 | 26 | 0 | 0 | 0 | 0 | 1.000000 |
| S, sloped roof | 1845 | 192 | 118 | −74 | 74 | 74 | 0 | 0.614583 |
| M, multiple faces | 1558 | 98 | 53 | −45 | 45 | 45 | 0 | 0.540816 |
| C, complex outline | 1108 | 60 | 44 | −16 | 16 | 16 | 0 | 0.733333 |

Relative to A's shadow area, B reduces shadow by **38.54% / 45.92% / 26.67%**
for S/M/C. F's volumes and classifications match exactly. Difference maps show
shorter northern shadow frontiers for S/M/C, with no new B-only shadows. Since
A raises every column to the same maximum, B's occupied building volume is a
subset of A: this experiment measures sensitivity to that explicit upper-bound
comparison, not all possible representative-height policies. The four spatially
overlapping context domains are independent experiments; their areas must not
be summed as a citywide union.

## Reused inputs and numerical model

[Implementation](../../../src/ouem/real_roof_shadow.py) reuses the
[4-A](STEP4A_REAL_LOD2_ROOF_DISTRIBUTION.md) roof/face identity loader,
[B1](STEP4B_REAL_LOD2_VOXELIZATION.md) and
[B2](STEP4B2_REAL_LOD2_TERRAIN_VOXELIZATION.md) saved input/provenance checks,
the STEP 3-B public Voxelizer + independent whole-volume oracle, and
[STEP 3-C](STEP3C_SYNTHETIC_SOLAR_SHADOW.md)'s binary evaluation/orientation and
common-observer helpers. Candidate B `shadow.calculate()` calls the existing
VoxCity binary kernel. No new ray tracing, geometry algorithm, direct Solar,
Canopy or GVI calculation is added.

Pinned B2 run: `data/work/step4b2-roof-terrain/final-a/`:
manifest **9f564e7d2e06c74301fdcf3670d6f60e2a531e628cfb36de882d8dec6f286817**,
report **20cf80af2f915a8eea3aca2432ffa23f938fc9c2485be5c276adcce4739cea7b**.
All its output SHAs are checked and saved volumes compared to the numeric
oracle read-only. Earlier 4-A/B1/T5 pins and fixed source_id/ouem_id/face refs
are inherited; no raw PLATEAU or old experiment artifact is changed.

DEM remains `t5-23-02/t5-2/terrain.tif`, SHA256
**ead7545fb2b50aaad9958aa8db647708a8ceba04f719ac6e8400150a17bb36a2**,
0.5 m EPSG:6677. Existing inverse-affine floor sampling is unchanged, including
east/south selection on source pixel boundaries. Each original top/state/
coverage grid is embedded into the same integer-metre phase without resampling.
Original-window DEM samples and all 504 building columns are unchanged.
Owner-conditioned building ground matches B2 exactly for every building.

Only roof-top values differ between A/B. DEM, IDs, footprint/support/coverage,
source faces, owner rule, effective ground, D0, observation and sun are shared.
Intervals are `[0, chosen_absolute_H−owner_ground_H]`, finite and positive.
Both volumes pass full independent occupancy/capacity/input-immutability QA.
The inherited full-square-column approximation is retained. Source absolute H
is never adjusted; unknown centre-method values are not used or filled.

## Context, observers and true sun

All rays run over each complete context grid. Every nonbuilding cell is evaluated;
there is no pre-cropped ROI. Other real buildings are **omitted**, and Terrain
is transparent to this building-only kernel. Unknown outside-domain occluders
are not represented. The selected domains lie entirely in the saved DEM.

| Sample | Context bounds EPSG:6677 [xmin,ymin,xmax,ymax] | Shape | Requested margin (m) | Conservative 45° reach (m) | A/B D0 (m) | Representative H (m) |
|---|---|---|---:|---:|---:|---:|
| F | [−22588,−39859,−22560,−39837] | 22×28 | 8 | 2.5 | 24.485000610 | 27.085800 |
| S | [−22583,−39850,−22529,−39811] | 39×54 | 14 | 8.5 | 24.552999496 | 33.684600 |
| M | [−22548,−39937,−22506,−39897] | 40×42 | 13 | 7.5 | 24.336999893 | 32.380000 |
| C | [−22588,−39845,−22553,−39811] | 34×35 | 13 | 6.5 | 24.517999649 | 32.003400 |

Initial margin uses roof maximum minus lowest saved DEM plus rounding/context
allowances. DEM boundaries clip the requested margins, notably north of S.
After voxelization, the highest occupied upper edge minus the lowest observer Z
gives the conservative reach. The projected shadow bounding box stays at least
one cell inside each domain; **no shadows occur in the outer two-cell border**
for either model. No DEM extrapolation or silent boundary truncation is used.
Context expansion can lower D0 compared with cropped B2; D0 is common to A/B
and recomputed with the same fixed engine rule, not copied from a different grid.

Sun is **true azimuth 180° / elevation 45°**, rays toward the southern sun.
Input row increases south, column east; kernel axis 0 increases north. STEP 3-C's
explicit axis-0 reflection is applied to voxels/masks and reversed for outputs.
Unlike its synthetic natural-origin case, real grid north has a true bearing
of about **−0.145°**. The existing Candidate B convention passes that measured
local bearing to public `direction_to_axis_vector(180,45,bearing)`; true azimuth
stays 180°, not an implicitly altered sun condition. Geod independently checks
north/east orthogonality and corner-bearing ranges. Bearings for F/S/M/C are
−0.145247401/−0.145132436/−0.144941694/−0.145225853°. A single central bearing per
small domain is an explicit approximation; no per-cell convergence correction.
The sunward vector is approximately north/east/up = [−0.7071,−0.00179,+0.7071],
so shadows extend north and slightly east in projected coordinates.

Existing B2/3-C observer geometry is used at requested height **0 m**; this is
the existing binary convention, not physical DEM+0. For valid observers,
`index=surface_index+1`, actual absolute Z = `D0+index+0.5`. Actual height above
effective ground is F/M ≈1.001–2.000 m, S ≈1.003–2.000 m, C ≈1.001–2.000 m.
Indices, validity, XYZ and surface classes agree exactly across A/B; building
columns are excluded. No observer correction occurs. A/B original capacities
are equal here (F/S/M/C Nz=4/11/10/9). The comparison supports AIR-only extension;
original and common-capacity shadows match, and adding three more AIR layers
leaves every map unchanged.

## Saved evidence and reproducibility

```powershell
.venv/Scripts/python.exe -m ouem.real_roof_shadow --distribution-run data/work/step4a-roof-distribution/final-c --audit-run data/work/step4-0-roof-audit/audit-final-e --b1-run data/work/step4b-roof-voxel/final-b --t5-run data/work/terrain-candidate-b/t5-23-02 --b2-run data/work/step4b2-roof-terrain/final-a --artifact-root C:/dev --output-dir data/work/step4c-roof-shadow/final-c
# Repeat in a separate process with --output-dir data/work/step4c-roof-shadow/final-d
.venv/Scripts/python.exe -m pytest -q -ra tests/test_real_roof_shadow.py tests/test_synthetic_height_solar.py tests/test_real_roof_terrain_voxel.py
```

Both final runs PASS: **126 byte-identical files** (80 NPY, 42 JSON, 4 PNG).
All **310 watched input/code identities** remain unchanged. Numerical arrays
are reread with NaN-preserving identity, JSON is atomically reread/published,
and the completed manifest is last. Earlier unavailable inputs yield
NOT_EXECUTED; downstream execution failures cannot publish completion.

Per model: public voxels, AIR-padded voxels, height/IDs/DEM/segments, metadata,
oracle QA, engine/runtime and binary classification. Per building: source H,
coverage/fractions, source DEM pixel indices, shared observer index/valid/XYZ,
comparison map and one four-panel EPSG:6677-coordinate PNG. Original footprint
outline is red. All four figures were visually checked; final tick spacing was
adjusted for readability. Classification is 0 shadow / 1 sun / 255 excluded.
Comparison codes are 0 excluded / 1 common sun / 2 common shadow / 3 A-only
shadow / 4 B-only shadow. Encoding is also in the report. Changed-cell accounting
retains both transition directions, even when net area change is zero.

| Identity | SHA256 |
|---|---|
| Final manifest | `82488e2807a0cbc95cb528d25a38bc77a2e4a1c3181122a091f75c2ec7eb7c8e` |
| Final report | `c84599fdca7b20828702b314d1e1a863695567b30e3d670fcd23fddca4a4227e` |
| Canonical path→SHA inventory | `120513663eed7795bd26e75805d7d4145e1a1736443da815e099f476bf22014e` |
| Real shadow adapter | `c56aef67a83cdb9487efe71feb748a8e56af9e7d0894d7db0faae703d00ba897` |
| Shared 3-C helpers | `59888268557a3bd750c30958cece575c68d8c8a6468a04d7e9beb104c67f8a3c` |

VoxCity 1.7.0, commit fa212656305328a9a657973bae26f352bfe813bc, CPU Numba
2 threads; previous setting restored. Windows OUEM venv Python 3.11.9 / NumPy
2.4.6 / Numba 0.68.0 / PyProj 3.7.2. PEP610/RECORD engine provenance and its
upstream-comparison limitation are inherited unchanged from B2.

[Five independent new tests](../../../tests/test_real_roof_shadow.py) plus
existing 3-C/B2 regressions: **32 passed, no skips/warnings, 40.57 s**. They cover
flat equality/hand-counted shadows, ground/footprint controls, boundary rejection,
true/grid axes, no-net-area spatial changes, embedding, immutability and
reproducibility. Existing 3-C cardinal geometry checks also pass at all four
azimuths (20 binary-shadow cells each); common/extra AIR checks pass in each
real scene. No new shadow engine or relaxed tests. Full local pytest was not
run; unchanged Windows/Ubuntu CI is the full gate, recorded in the Draft PR.

The result establishes a numerical roof-representation effect for one sun
condition and one isolated-building setup. It does not establish actual shadow
accuracy, nearby-building interactions, terrain occlusion, scientific HAG or
vertical realization/epoch/precision. Existing acceptance and Terrain gates
remain unchanged; generated artifacts stay outside Git.
