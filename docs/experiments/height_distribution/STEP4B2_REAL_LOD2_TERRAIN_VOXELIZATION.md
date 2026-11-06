# STEP 4-B2 — Real LoD2 Distributed Height + Saved Terrain

2026-11-06. Baseline main **99fc3a3d44bf85fdf60b783f4570dffc46008591**
(PR #167 merged). **Technical execution PASS / Geometric numerical QA PASS**.
The four fixed F/S/M/C buildings were voxelized using their unchanged saved
cell_max roof H and the saved Candidate B 0.5 m DEM. Full 3D class arrays match
the independent scalar oracle. Vertical status remains **CONDITIONAL**;
scientific validation/formal acceptance **NOT_VERIFIED**, terrain integration
ready **false**. No real-data Solar/Shadow/GVI/Canopy processing occurred.

**Important shape limit:** each small domain has <0.5 m DEM relief. At 1 m
vertical resolution, all surface indices round to **0**. This connects real
numerical terrain heights and changes building occupancy, but does not produce
visibly undulating ground surfaces in these four voxel volumes.

## Actual model changes

| Sample | Shape (row, col, Z) | Building columns | B1 → Terrain BUILDING voxels | Effective building ground H (m) | New D0 (m) |
|---|---|---:|---:|---:|---:|
| F | 6×15×4 | 39 | 78 → 78 | 25.022615384 | 24.889999390 |
| S | 15×26×10 | 261 | 1933 → 1907 | 25.006348657 | 24.704000473 |
| M | 14×16×9 | 122 | 752 → 743 | 24.698237685 | 24.496000290 |
| C | 12×12×9 | 82 | 510 → 499 | 24.945158563 | 24.690000534 |

Horizontal support stays **504 columns**; BUILDING count changes **3273→3227**.
S/M/C lose one occupied layer in 26/9/11 columns. All models retain their roof
height variation; source roof H is not adjusted to the terrain. All outputs have
848 surface voxels in total, no GROUND (-1)/TREE (-2); ground below D0 is not
allocated. The full-cell-column boundary approximation is inherited from
[B1](STEP4B_REAL_LOD2_VOXELIZATION.md), with unchanged footprint/roof coverage.

## Inputs, sampling and conditional vertical profile

[Adapter](../../../src/ouem/real_roof_terrain_voxel.py) reuses B1's read-only
4-A/4-0 input loader, fixed source_id/ouem_id and RoofSurface/GroundSurface chain.
All B1 outputs are also pinned/read-only; its saved voxel volume is checked
against the existing independent oracle, without rerunning B1's Voxelizer.

| Saved artifact | SHA256 |
|---|---|
| 4-A `final-c/manifest.json` | `f73e65073ed823b9155cc75a93a4cfdbc314fb9a0f1859f4d635ec5e71a952bd` |
| B1 `final-b/manifest.json` | `5f1b0e1c11414889aa2ee305faf74989da65d590130bf85a0b61128ecf2662e9` |
| B1 report | `5a615675276402bd10563a29cf8b74aff4768bf1c34187d8ac0707e862ed7646` |
| Candidate B `t5-23-02/report.json` | `1a4c3ed60bebcb92b00f5a28dbb52ceea78fd4b9eb4893cb87445dc17080695f` |
| `t5-23-02/t5-2/terrain.tif` | `ead7545fb2b50aaad9958aa8db647708a8ceba04f719ac6e8400150a17bb36a2` |

The DEM is EPSG:6677, Float32, 254×254, affine
`[0.5,0,-22588,0,-0.5,-39811]`, NoData −32767, domain
`[-22588,-39938,-22461,-39811]`. All **848** cells (including halos) have finite,
unmasked in-bounds DEM samples. No T3-only 100 m raster, new acquisition or
Terrain generation is used.

Existing `height_envelope.sample_raster()` supplies nearest/containing-pixel
samples by inverse-affine **floor**. Each 1 m target centre lies on 0.5 m source
pixel boundaries: ties select east/south, source-centre offsets **X=−0.25 m,
Y=+0.25 m**. The selected source row/column is saved; an independent direct pixel
lookup checks values/masks exactly. No interpolation, snapping or offset occurs.
These are 4-A's north-up 1 m row/column grids, not T5's geodetic 127×127 engine
centres. Arrays reach Voxelizer without axis reversal/transposition.

Building declaration: original EPSG:6697 (XY 6668 / H 6695), Standard XY→6677
with H unchanged. DEM: existing T5 **CONDITIONAL**, T.P. inheritance
**INFERRED_FROM_SOURCE_LINEAGE**, a working assumption. Realization, measurement
epoch and accuracy remain unverified on both sides; EPSG:6677 is not evidence of
vertical agreement. The adapter accepts only this explicit conditional profile,
rejects conflicting/unsupported declarations, and applies no H/DEM correction.

All four original GroundSurface vertex H ranges are constant (values in B1).
Sampled building-cell DEM minus that H is:

| Sample | Raw DEM H over entire grid (m) | Building DEM − GroundSurface H (m) | Roof H − effective ground H (m) |
|---|---|---|---|
| F | 24.889999–25.093000 | +0.088207 to +0.176209 | 2.063185–2.063185 |
| S | 24.704000–25.100000 | +0.012246 to +0.222247 | 2.587803–8.678251 |
| M | 24.496000–24.882000 | −0.059191 to +0.162809 | 2.961762–7.681762 |
| C | 24.690001–25.075001 | +0.023144 to +0.197144 | 3.434241–7.058241 |

All heights are positive/finite; differences are numerical evidence, not HAG
certification or a measured source-accuracy comparison. B2-0 checks all four
before any dependent engine execution and saves a conditional PASS preflight.

## Execution, integer ground and absolute-H comparison

Reuses `synthetic_height_voxel.execute_arrays()` and its pre-engine scalar
occupancy oracle unchanged. Public VoxCity **1.7.0**, fixed commit
**fa212656305328a9a657973bae26f352bfe813bc**, CPU Numba 2 threads. A single owner
ID=1 per independent building uses mean sampled DEM under every positive-area
building column, including partial coverage cells. Nonbuilding DEM is retained.
`effective_ground` and `D0=min(effective_ground)` follow the fixed rules;
Float32 relative DEM, integer surface/start/stop and allocated capacity are
checked against the engine. Height equals max segment high; initial segment is
`[0, roof_H-effective_ground_H]`. No cavities/piloti are inferred.

```text
ground_index = floor(float32(effective_ground−D0) + 0.5)
start = ground_index + 1
stop = start + floor(relative_height + 0.5)       # exclusive
surface lower H = D0 + ground_index
building bottom H = D0 + start
roof voxel upper H = D0 + stop
```

Capacity is the unmodified engine allocation; all intervals are nonempty and
within Nz. Strict input/argument immutability and full class-array equality
pass. No height inflation or extra capacity masks a bad input.

| Sample | Voxel upper edge − roof H (m) | Uppermost voxel lower edge − roof H (m) | New upper H − B1 upper H (m) |
|---|---|---|---|
| F | +0.804199 | −0.195801 | +0.001207 |
| S | +0.198839 to +1.196608 | −0.801161 to +0.196608 | −1.173753 to −0.173753 |
| M | +0.305891 to +1.294439 | −0.694109 to +0.294439 | −1.111191 to −0.111191 |
| C | +0.257279 to +1.239338 | −0.742721 to +0.239338 | −1.131854 to −0.131854 |

Roof reconstruction error combines ground quantization, segment rounding and
the surface/start-layer offset. Unlike constant-anchor B1, the uppermost lower
edge can deviate beyond ±0.5 m because the conditioned ground also rounds down.
All surface lower H equals each new D0; the unquantized DEM/effective arrays
retain the real numerical terrain variation. No values are shifted to improve
agreement. Different D0/Nz arrays are **not** compared by Z index: comparison
uses absolute-H column interval edges and interval symmetric-difference volume
(F/S/M/C **0.094176 / 116.698819 / 36.130533 / 32.624132 m³**), not truth error.
Building bottoms move by respectively +0.001207/−0.173753/−0.111191/−0.131854 m.

## Outputs and reproducibility

```powershell
.venv/Scripts/python.exe -m ouem.real_roof_terrain_voxel --distribution-run data/work/step4a-roof-distribution/final-c --audit-run data/work/step4-0-roof-audit/audit-final-e --b1-run data/work/step4b-roof-voxel/final-b --t5-run data/work/terrain-candidate-b/t5-23-02 --artifact-root C:/dev --output-dir data/work/step4b2-roof-terrain/final-a
# Repeat in a separate process with --output-dir data/work/step4b2-roof-terrain/final-b
.venv/Scripts/python.exe -m pytest -q -ra tests/test_real_roof_terrain_voxel.py tests/test_real_roof_voxel.py tests/test_synthetic_height_voxel.py tests/test_real_roof_distribution.py
```

Both runs PASS: **99 byte-identical files** (56 NPY, 39 JSON, 4 PNG), with **206
watched input/code identities unchanged**. NPY/JSON are reread, copied original
face/projection/contribution records are SHA-verified. All four diagnostic images
show sampled/conditioned terrain, absolute-H roof/ground sections and actual 3D
class sections. No saved input/old run is overwritten. The completed manifest
is last, after every building save and input check; failures cannot publish it.

| Identity | SHA256 |
|---|---|
| Final manifest | `9f564e7d2e06c74301fdcf3670d6f60e2a531e628cfb36de882d8dec6f286817` |
| Final report | `20cf80af2f915a8eea3aca2432ffa23f938fc9c2485be5c276adcce4739cea7b` |
| Canonical relative-path→SHA inventory | `a4bb15ade85d060d83bb21d8832f555d7a29f291d1f86df37651a4cc1076c5e9` |
| Terrain adapter | `ff0ee281fafb2c509a6549c117b6f872e9fc28d02b70a7e873a305e7d21b56b7` |
| B1 shared saver (optional diagnostic callback only) | `9bb390ffa3a963cd2808bb6935ac720ac7634824f0e6ccc365bfc368979e3f85` |

Environment: Windows OUEM venv, Python 3.11.9 / NumPy 2.4.6 / Numba 0.68.0 /
Shapely 2.2.0. Engine PEP610/RECORD provenance matches B1; limitation remains no
independent upstream Git-tree byte comparison. Outputs include sampled DEM,
effective ground, source pixel indices, original/reconstructed roof H, surface
and building-bottom H, volumes, segments, IDs, coverage, original references,
QA/comparison, runtime/engine provenance and diagnostics. They remain outside Git.

[Four new independent tests](../../../tests/test_real_roof_terrain_voxel.py)
exercise hand-counted owner ground/D0/3D occupancy and differing-D0 absolute-H
comparison, half-metre boundary sampling/NoData/outside, vertical/height/handoff
rejection, reproducibility, missing data/SHA and partial failure. Existing B1,
3-B and 4-A tests retained: **62 passed, no skips/warnings, 19.19 s**. Initial
fixture use of Rasterio's `from_origin` emitted two Affine deprecation warnings;
explicit equivalent Affine construction removed that fixture warning without
changing checks. Full local pytest was not run. Unchanged Windows/Ubuntu full
CI (pip cache, `--durations=30`) is the technical gate; results are in the Draft PR.

The limited real-DEM numeric connection is established. Actual vertical datum
agreement, HAG and physical roof/terrain/environmental accuracy are not verified.
The 1 m terrain flattening, owner mean ground and full-column footprint expansion
must be considered before any later environmental use. Formal Terrain acceptance
is unchanged; no scientific or terrain-integration gate is released.
