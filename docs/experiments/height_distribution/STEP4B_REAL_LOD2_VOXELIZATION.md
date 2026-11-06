# STEP 4-B — Real LoD2 Distributed-Height Voxelization

2026-11-06. Baseline main **cebf7b96599cf72d54bb325a1c86eea5aaef1e1b**
(PR #166 merged). **Technical execution PASS / Geometric numerical QA PASS**.
The four fixed real PLATEAU LoD2 samples produced actual int8 3D building
volumes through the pinned public VoxCity API, with complete independent
occupancy-oracle agreement. Roof slopes/steps survive as different column
heights. This is a numerical-anchor extrusion experiment, not real DEM/HAG
integration or scientific height validation.

`terrain_integration_ready=false`, `scientific_validation=NOT_VERIFIED`,
`formal_acceptance=NOT_VERIFIED`. No Solar/Shadow/GVI/Canopy was executed.

## Main result

| Sample | Volume shape (row, col, Z) | Building columns | BUILDING voxels | Distinct occupied column heights (m) |
|---|---|---:|---:|---|
| F: flat reference | 6×15×4 | 39 | 78 | 2 |
| S: sloped roof | 15×26×10 | 261 | 1933 | 3, 4, 6, 7, 8, 9 |
| M: multiple roof faces | 14×16×9 | 122 | 752 | 3, 4, 5, 6, 7, 8 |
| C: complex outline | 12×12×9 | 82 | 510 | 4, 6, 7 |

Totals: **504 building columns, 3273 BUILDING voxels**, 3451 AIR voxels,
848 minimal surface voxels (class 1), no GROUND (-1) or TREE (-2) voxels.
GROUND is absent because the constant numerical ground is D0 itself; the
surface occupies layer 0 and no layers below D0 are allocated.
All 4 diagnostic PNGs were visually inspected. They juxtapose source cell_max H,
voxel upper-edge H, a deterministic maximum-range roof section, and the actual
BUILDING occupancy section. F stays flat; S/M/C retain spatially varying roofs.

## B0: immutable real input and numeric anchors

[STEP 4-A](STEP4A_REAL_LOD2_ROOF_DISTRIBUTION.md) run:
`data/work/step4a-roof-distribution/final-c/`.

| Pinned artifact | SHA256 |
|---|---|
| STEP 4-A manifest | `f73e65073ed823b9155cc75a93a4cfdbc314fb9a0f1859f4d635ec5e71a952bd` |
| STEP 4-A report | `c9f3315795dfa8ebba2d3d96a0fd89b8814e0301569da2c19c2f5151e9a9a9f1` |
| STEP 4-0 manifest | `14498ba34826c2b68c2a22c29da6fcbeb8bc696e20b68f799d8a8cca0a41a852` |
| STEP 4-0 report | `71de561a0644352654c4d30814259f3d42b1d31a18b9c1591652be88c1b3565e` |

The [limited real adapter](../../../src/ouem/real_roof_voxel.py) reuses
`real_roof_distribution.load_samples()` for the read-only Raw/Native/Standard
chain and exact RoofSurface/GroundSurface correspondence. All saved STEP 4-A
manifest outputs are SHA-checked; its historical input SHA/size/path identities
must agree with that chain. The roofs are **not regenerated**. GeoTIFFs are
reopened to check EPSG:6677, Affine, shape, float64/uint8 dtype, NaN/255/no-NoData
policy and finite/valid masks. JSON roundtrip differences in list/tuple
representation are compared canonically, without numerical tolerance changes.

| Sample | source_id | ouem_id |
|---|---|---|
| F | `bldg_09532951-4dab-457d-b1c6-56d509900d1b` | `oub-c56cb020-c11c-5f9c-a37f-73018266a333` |
| S | `bldg_040379e5-dffb-40b6-a392-6396158211f5` | `oub-664a9132-cf36-52a5-96f5-577e78c91e59` |
| M | `bldg_2bd71700-a145-46ff-b14f-ad60394ff253` | `oub-cb250497-c12d-5fcc-9dca-e82c8b051398` |
| C | `bldg_2d5a9713-b02f-4903-9164-c5653e03494d` | `oub-10894413-4369-5131-ac0d-78ee9d234016` |

The source grid bounds/phase/axes are unchanged from STEP 4-A: global integer
1 m origin phase, north-up row southward/column eastward, per-building halo.
Each sample has one GroundSurface and respectively 1/69/30/12 RoofSurface faces.
All original face rings, projections, intersections and contributions remain
referenced/copied, with original source H values. No geometry repair occurs.

| Sample | GroundSurface vertex H range (m) | anchor_H (m) | cell_max H−anchor range (m) |
|---|---|---:|---|
| F | 24.888792–24.888792 | 24.888792 | 2.197008–2.197008 |
| S | 24.877753–24.877753 | 24.877753 | 2.716399–8.806847 |
| M | 24.607191–24.607191 | 24.607191 | 3.052809–7.772809 |
| C | 24.821855–24.821855 | 24.821855 | 3.557545–7.181545 |

`anchor_H = min(all original GroundSurface vertex H)`; all 504 cell_max building
cells are KNOWN and positive above it. The **99 centre TOP_UNKNOWN cells remain
a saved STEP 4-A limitation**; centre is never passed to Voxelizer or filled.
The source declaration remains EPSG:6697 (XY 6668 / vertical 6695), with Standard
XY-only conversion to 6677 and H unchanged. Actual realization/epoch/accuracy
remain NOT_VERIFIED. No external DEM is sampled/subtracted; historical Terrain
files are hashed only as existing provenance. These anchors are not certified
representative ground or HAG.

B0 requires all four inputs/anchors/grids to pass before any B1 execution.
Its PASS record is saved separately within the same run, then B1 proceeds
automatically. Missing data yields NOT_EXECUTED; inconsistent inputs BLOCKED.
No new gate framework or formal Standard/Adapter rule is introduced.

## B1: public Voxelizer and independent occupancy

Reuses [STEP 3-B](STEP3B_SYNTHETIC_VOXELIZATION.md)'s independent scalar integer
oracle, argument immutability checks and public API call. The small extracted
`synthetic_height_voxel.execute_arrays()` core owns numeric API execution only;
the existing synthetic `execute()` retains its Derived/profile validation.
Real inputs carry their own `ouem-real-lod2-cell-max-numeric-anchor-voxel/v0.1`
profile, source/grid/vertical metadata and fixed single-source owner mapping.
No synthetic datum or synthetic Derived identity is assigned to real data.

VoxCity **1.7.0**, commit **fa212656305328a9a657973bae26f352bfe813bc**,
public `Voxelizer(1., "Standard").generate_combined(height, segments, ids,
land_cover, dem, tree, print_class_info=False)`; Numba path, CPU 2 threads
(previous setting restored). `height` is float64, `segments` an object array
of explicit `[0, relative_height]` intervals, `ids` int32 1 inside/0 outside,
DEM float64 constant anchor over the entire grid. Land cover is minimal class 1;
tree height is zero. No horizontal transpose/flip/resampling is performed.

The installed API was inspected again: height controls Z allocation; segments
control actual occupied intervals; the DEM is reduced by its raw minimum before
owner averaging. For constant ground the engine's relative DEM is exactly zero,
so `D0=anchor_H`, surface index 0, building start index 1. Scalar independent
oracle (constructed before engine execution) computes:

```text
Nz = ceil(max(relative_height)) + 1
start = 1
stop = 1 + floor(relative_height + 0.5)       # exclusive
BUILDING = [start, stop)
uppermost voxel lower H = anchor_H + stop - 1
uppermost voxel upper H = anchor_H + stop
```

The complete 3D class array must match exactly, with nonempty intervals and
every stop <= Nz. No capacity padding/height inflation or clipping correction
is used. Fixed rounding conventions are unchanged.

An initial B1 preflight stopped because the older absolute-mean helper produced
3.55e−15–7.11e−15 m artificial relief when averaging repeated decimal constants.
The engine subtracts the raw constant first and obtains exact zero. The oracle
now uses the exact constant-ground invariant for constant DEMs only; other DEMs
retain the existing owner-ground calculation. A decimal-anchor regression
checks this against the public API. Strict Float32 ground identity, capacities
and full-volume comparisons remain intact; no assertion was weakened and no
input value was changed. `final-a/` remains BLOCKED with no completed manifest.

## Quantization and horizontal shape approximation

| Sample | Voxel upper edge − source roof H (m) | Uppermost voxel lower edge − roof H (m) |
|---|---|---|
| F | +0.802992 | −0.197008 |
| S | +0.509082 to +1.496786 | −0.490918 to +0.496786 |
| M | +0.502188 to +1.496571 | −0.497812 to +0.496571 |
| C | +0.557588 to +1.442455 | −0.442412 to +0.442455 |

The near ±0.5 m lower-edge discrepancy is rounding. The upper edge adds the
one-layer surface/start convention; it must not be reported as pure ±0.5 m roof
accuracy or silently shifted downward. Source cell_max H is saved unmodified.
Submetre slopes become plateaus/steps; quantization preserves their coarse
variation, not the exact planar surface or measured building volume.

| Sample | Original footprint area (m²) | Used roof support area (m²) | Full-column area (m²) | Extra vs footprint | Smallest positive roof fraction |
|---|---:|---:|---:|---|---:|
| F | 23.2635234563 | 23.2635234563 | 39 | 15.7364765437 m² / 67.64% | 0.0000311058 |
| S | 220.1300691624 | 220.1300690006 | 261 | 40.8699308376 m² / 18.57% | 0.0000454407 |
| M | 97.0156999948 | 97.0156999943 | 122 | 24.9843000052 m² / 25.75% | 0.000970038 |
| C | 65.2570512368 | 65.2570512368 | 82 | 16.7429487632 m² / 25.66% | 0.000294904 |

This user-authorized full-square-column approximation enlarges the horizontal
support, especially the narrow F footprint. Tiny original roof/footprint
differences remain numerical residuals, not a claim of physical gaps/eaves.
Coverage arrays and all original geometries remain available for later policy
review. Top-only data is extruded continuously: no roof thickness, cavities,
piloti, internal structure or watertight-solid reconstruction is inferred.

## Reproducible outputs and validation

```powershell
.venv/Scripts/python.exe -m ouem.real_roof_voxel --distribution-run data/work/step4a-roof-distribution/final-c --audit-run data/work/step4-0-roof-audit/audit-final-e --artifact-root C:/dev --output-dir data/work/step4b-roof-voxel/final-b
.venv/Scripts/python.exe -m ouem.real_roof_voxel --distribution-run data/work/step4a-roof-distribution/final-c --audit-run data/work/step4-0-roof-audit/audit-final-e --artifact-root C:/dev --output-dir data/work/step4b-roof-voxel/final-c
.venv/Scripts/python.exe -m pytest -q -ra tests/test_real_roof_voxel.py tests/test_synthetic_height_voxel.py tests/test_real_roof_distribution.py tests/test_synthetic_height_distribution.py
```

Two independent CLI processes produced **83 byte-identical files**, including
40 NPY arrays and 4 diagnostic PNGs. **118 watched input/code identities remained
unchanged**. All NPY arrays are reread (including NaN identity), JSON is reread
before atomic publication, copied source records are SHA-verified. API arrays
and original handoff arrays remain unchanged. The root completed manifest is
last, only after all four executions/saves and final input checks. An injected
partial save failure cannot publish completion. Outputs stay ignored/outside Git.

| Identity | SHA256 |
|---|---|
| Final manifest | `5f1b0e1c11414889aa2ee305faf74989da65d590130bf85a0b61128ecf2662e9` |
| Final report | `5a615675276402bd10563a29cf8b74aff4768bf1c34187d8ac0707e862ed7646` |
| Canonical relative-path→SHA inventory | `f7414ff4c591f968ab714181f04d73b533df8814f999d667d0eba0a86775ba44` |
| Real adapter | `72440b660403b93657c832bad2ea68dc96cdcdec23e0e0ad892f29fadaea2d85` |
| Shared voxel module | `47621959cc1405e6fcf31fb4cd867412d96218b048162c16046bfe903aba9d0c` |
| Installed VoxCity source content | `33e2bfdbc8a677f53154e8cd16295603819c68cf9f24c7a4cdfeb196bcbcd0bd` |

Engine provenance is verified by PEP610 origin/commit/version and 136 installed
source RECORD hashes, not an independent comparison to upstream Git bytes.
Windows OUEM venv: Python 3.11.9, NumPy 2.4.6, Numba 0.68.0, Shapely 2.2.0.
Per building: voxels, height/IDs/constant DEM, source top/state/coverage/fraction,
voxel upper/lower-H arrays, segments, metadata, QA, engine/runtime, original
inputs/source-faces/projections/contribution records and diagnostic image.

[12 independent new tests](../../../tests/test_real_roof_voxel.py) cover anchor,
invalid heights/unknowns/grids, JSON roundtrip, decimal-ground invariant,
hand-counted occupancy/rounding, capacity, immutable handoff, reproducibility,
missing-data/SHA failures and partial saves. Existing STEP 3-B, 4-A and 3-A
regressions were run: **83 passed, no skips/warnings, 17.91 s**. Initial syntax
and JSON-representation errors were fixed/retested; no tests were weakened.
No local full pytest was run. Unchanged Windows/Ubuntu GitHub Actions is the
full-regression gate; completed counts are recorded in the Draft PR.

## Next real-DEM step

The real cell_max→public Voxelizer connection is technically demonstrated for
this limited constant-anchor profile. Real DEM integration still requires
explicit vertical-reference compatibility, owner-conditioned ground/D0,
positive segment heights and source-grid sampling QA. The constant anchors
must not be substituted for actual terrain or promoted to verified HAG.
Horizontal boundary inflation and vertical surface-layer offset need an
explicit downstream interpretation before environmental assessment.
Formal Standard/Adapter contracts, accepted representative models, VoxCity,
dependencies/CI and old Raw/Native/Standard/T5/STEP 2/3/4-A runs are unchanged.
AGENTS adds only the requested short conditional-continuation rule.
