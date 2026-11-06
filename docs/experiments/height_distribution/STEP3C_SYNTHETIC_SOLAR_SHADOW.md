# STEP 3-C — Synthetic Height Distribution Solar / Shadow

2026-11-06. **COMPLETED_SYNTHETIC_ONLY / EXPERIMENTAL**.
**Binary shadow: PASS. Horizontal direct solar: PASS.** These are bounded
technical results; `terrain_integration_ready=false`, scientific validation and
formal acceptance **NOT_VERIFIED**. Real-data applicability remains unverified.
The PR description owns the completed Windows/Ubuntu CI results.

## Audit and implementation boundary

Base: current main `e15dba7f45147eb8d23f48959c28e79a417666be` (PR #163 merged).
Reviewed [STEP 3-A](STEP3A_SYNTHETIC_HEIGHT_DISTRIBUTION.md),
[STEP 3-B](STEP3B_SYNTHETIC_VOXELIZATION.md), their implementations/tests,
[Candidate B shadow](../../../src/ouem/candidate_b_shadow.py),
[Candidate B solar](../../../src/ouem/candidate_b_solar.py),
[B1 solar](../../../src/ouem/real_komae_solar.py) and the
[B2 observer diagnostic](../../../src/ouem/b2_gvi.py).
Installed VoxCity `models.py`, `utils/orientation.py`, `solar/radiation.py`,
`solar/kernels.py` and `common/raytracing.py` were read before connection.

[New experimental adapter](../../../src/ouem/synthetic_height_solar.py):
reuse STEP 3-A `derive`, STEP 3-B `prepare/execute/save_result` and its independent
integer oracle; reuse Candidate B `shadow.calculate/counts` and B2's
`observers/roi_window` geometry helpers (no GVI execution). Solar calls the same
public `get_direct_solar_irradiance_map` used by B1/Candidate B. The existing B1
`direct_solar_at_saved_grid` wrapper assumes EPSG:4326 metadata and its saved
geographic axes, so it is not applied to these projected north-up arrays.
Only a minimal `VoxCity`/`GridMetadata` boundary is added; no new physics or ray
engine, Standard/Adapter contract or roof geometry algorithm.

Engine: VoxCity **1.7.0**, pinned commit
`fa212656305328a9a657973bae26f352bfe813bc`. Runtime: Windows OUEM venv,
Python **3.11.9**, NumPy **2.4.6**, Numba **0.68.0**, PyProj **3.7.2**.
CPU **2 threads** during kernels, prior thread setting restored. No dependency,
engine or CI change. Child manifests reuse PEP 610/installed RECORD verification
(136 source files); this does not independently compare the upstream Git tree.

## Scene, frame and sun

All three authored scenes use EPSG:6677 bounds `[-12,-12,12,12]`, **24×24**
1 m cells, row 0 north, increasing row south, increasing column east. One
`source_id=synthetic-building`, footprint `[-2,-2,2,2]` (16 building columns),
numeric ID 1, no owner choices, raw/effective ground Z=2, **D0=2**, no TREE.
Absolute Z is an arbitrary synthetic datum, not T.P. Fixed footprint/DEM/IDs/
ownership/ground/D0/grid are checked across all three methods.

| Scene | Authored roof absolute Z | Representative top |
|---|---|---:|
| Flat | 8 | 8 |
| Slope, south higher | `9.05 − .75(y+2)` | 9.05 |
| Step | 6 for `y >= .25`; 9 for `y <= .25`, with both closed faces retained on the seam | 9 |

The slope's .05 offset deliberately produces **genuinely unequal original Z
capacities**, while keeping simple independent integer endpoint expectations.
These are new small synthetic scenes with surrounding air, not modifications
of STEP 3-A/B source data or saved runs. Unknown roof support and competing
owners are rejected; no centre-to-representative fallback is allowed.

The API requires axis 0 **north**, axis 1 east, axis 2 up. A rotation alone cannot
represent the input's axis-0 reflection while preserving east. At the I/O boundary
the public orientation helper explicitly flips **all** horizontal grids and the
voxel volume to south-up; returned maps are flipped back. Metadata is
`GridMetadata('EPSG:6677', (-12,-12,12,12), 1.)`, `rotation_angle=0` in the API
frame. There is no geographic relabelling, hidden azimuth adjustment or change
to the stored north-up arrays.

The synthetic true-north reference is the natural origin `[0,0]` →
`[139.833333333333°,36°]`. PROJ/Geod independently verifies the central grid
meridian's true bearing is **0°**. Four-corner meridian convergence is at most
**0.000078238°**, below the declared **.001°** diagnostic bound. A fixed tangent-
frame sun referenced at this origin is used; no per-cell geographic convergence
correction is applied. Other locations/frames are rejected rather than
automatically rotated. This approximation/definition is synthetic-only, not a
general real-city true-azimuth transform.

Main sun: **true-reference azimuth 180°, elevation 45°, DNI=800 W/m²**.
API sunward vector is approximately `[-.707106781,0,+.707106781]` (north/east/up);
the stored north-up grid vector is `[+.707106781,0,+.707106781]` (south/east/up).
Rays point **toward the sun**, so building shadows lie north. At this elevation
unobstructed horizontal direct irradiance is `800 sin(45°)` =
**565.685424949238 W/m²**, not DNI itself.

## Common Z and observers

Every original public Voxelizer volume first passes STEP 3-B's input, ownership,
ground, rounding, clipping/capacity and whole-volume independent oracle checks.
Only then is AIR added to the greatest of the three original depths:

| Scene | Original representative / centre / cell_max Z | Common Z |
|---|---|---:|
| Flat | 7 / 7 / 7 | 7 |
| Slope | 9 / 8 / 9 | 9 (centre gains one AIR layer) |
| Step | 8 / 8 / 8 | 8 |

All original layers are byte-identical; added layers are zero/AIR, with no
BUILDING/GROUND/surface changes or cutting. Original-versus-shared evaluation
is checked where depth differs; an additional three-AIR-layer control on the
representative model is also unchanged. Capacity failures from STEP 3-B cannot
reach this extension stage. Original/shared before/after SHA identities are
saved. Solar/API boundary arguments (including zero canopy grids and metadata)
are also checked for mutation.

Each scene has **560 nonbuilding observers**, 16 excluded building columns.
Surface index=0. The existing first AIR-over-surface transition and integer
view height are retained without height correction:

| Experiment | Requested API height | k | Absolute observer centre Z | Height above effective ground |
|---|---:|---:|---:|---:|
| Binary shadow, independent STEP 2-A-style experiment | 0 m | 1 | 3.5 m | 1.5 m |
| Horizontal direct solar, B1-style experiment | 1.5 m | 2 | 4.5 m | 2.5 m |

The ray tracer receives integer index coordinates and internally adds .5, so
these are actual cell-centre ray origins, not merely display coordinates.
All model indices, valid masks, absolute XYZ and surfaces must agree; origins
must be AIR, all buildings excluded. Invalid indices remain −1 and invalid
XYZ/solar values NaN; missing values never become zero. No roof observers.

Binary kernel uses `hit_values=(0,-1,1)`, exclusion mode, no roofs: output
**0 shadow / 1 sun / 255 excluded**. Direct API uses `hit_values=(0,)`, exclusion
mode, no roofs, requested height 1.5, `tree_k=.6`, `tree_lad=1.`; these optical
settings are fixed but inactive without TREE. Direct output is horizontal
**W/m²**, no diffuse/reflection/time integration. Negative/nonfinite valid
intensities, unexpected masks or values outside zero/unobstructed irradiance
are rejected (absolute numerical tolerance **1e-9 W/m²**, no relative tolerance).
Binary shadow is not used as a canopy attenuation metric or as the solar map.

## Independent geometry and results

At 45° the north shadow intercept for a roof column is its north face Y plus
its **upper voxel edge Z minus observer Z**. Touch-only corner rays at the
limit have no positive-volume building traversal. Four-cardinal tests on the
single flat building require the expected north/south/west/east shadow location
and length: **20 binary shadow cells**, **16 direct-zero cells** for each sun
azimuth 180/0/90/270°. Omitting the explicit axis reflection is detected.

[New self-contained tests](../../../tests/test_synthetic_height_solar.py) also
compare **every cell** in all three scenes/methods against hand-calculated
intercepts; expected masks do not come from the public Solar output. Slope
centre upper edges north→south are `[7,8,9,10]`, cell_max `[8,9,9,10]`.
The step's first high row starts at Y=0 for centre, Y=1 for cell_max. Together
with observer Z, these determine the masks without implementing a new ray engine.

The open-space ROI is `[-6,2,6,10]`, **8×12 = 96 observers**, immediately north
of the building. Full **24×24** ray calculations precede extraction. ROI top-left
centre is `[-5.5,9.5]`, bottom-right `[5.5,2.5]`; north-up registration and actual
centres are saved. All main-condition shadows fall in this ROI.

| Scene / method | Binary shadows (domain fraction of 560) | ROI shadow fraction of 96 | Solar zero cells | Domain mean direct W/m² | ROI mean direct W/m² |
|---|---:|---:|---:|---:|---:|
| Flat, all three | 20 (3.5714%) | 20.8333% | 16 | 549.522984 | 471.404521 |
| Slope representative | 24 (4.2857%) | 25% | 20 | 545.482374 | 447.834295 |
| Slope centre | 12 (2.1429%) | 12.5% | 8 | 557.604205 | 518.544973 |
| Slope cell_max | 16 (2.8571%) | 16.6667% | 12 | 553.563594 | 494.974747 |
| Step representative | 24 (4.2857%) | 25% | 20 | 545.482374 | 447.834295 |
| Step centre | 16 (2.8571%) | 16.6667% | 12 | 553.563594 | 494.974747 |
| Step cell_max | 20 (3.5714%) | 20.8333% | 16 | 549.522984 | 471.404521 |

Flat results are identical for all three models. Signed solar difference is
**destination − source**, with exclusion NaNs retained:

| Scene / comparison | Binary 0→1 / 1→0 | Changed solar cells (increase / decrease) | ROI mean delta W/m² |
|---|---:|---:|---:|
| Slope representative→centre | 12 / 0 | 12 (12 / 0) | +70.710678 |
| Slope representative→cell_max | 8 / 0 | 8 (8 / 0) | +47.140452 |
| Slope centre→cell_max | 0 / 4 | 4 (0 / 4) | −23.570226 |
| Step representative→centre | 8 / 0 | 8 (8 / 0) | +47.140452 |
| Step representative→cell_max | 4 / 0 | 4 (4 / 0) | +23.570226 |
| Step centre→cell_max | 0 / 4 | 4 (0 / 4) | −23.570226 |

Domain changed-cell counts are the same; domain-mean deltas use 560 rather
than 96 observations (e.g. centre→cell_max **−4.040610 W/m²**). Individual
changed-cell deltas are ±565.685424949238 W/m². Solar increases from lowering
the representative roof and decreases from cell maxima have the expected
blocking geometry; neither sign is treated as an error. Binary and solar
changed counts happen to agree in these examples but affect different rows,
because their observer heights differ. They are not cellwise-equivalent metrics.

The building has 10 m clearance to domain boundaries. Highest known upper edge
is Z=9 (flat), Z=10 (slope/step); lowest observer Z=3.5 gives maximum 45° reach
5.5/6.5 m, within that margin. Outside-domain space is synthetic open air.
Unknown external occluders, other sun angles and real context completeness
are not verified by this design.

## Artifacts and reproducibility

```powershell
.venv/Scripts/python.exe -m ouem.synthetic_height_solar --run-dir data/work/step3c-synthetic/final-e
.venv/Scripts/python.exe -m ouem.synthetic_height_solar --run-dir data/work/step3c-synthetic/final-f
```

Both independent processes completed binary **PASS** and direct **PASS**.
All **174 files**, including **135 NPY arrays**, are byte-identical. Scope is
the recorded local environment, not cross-platform byte reproducibility.

| Identity | SHA256 |
|---|---|
| Root manifest, both runs | `45f887ea2726bb97ecd174d94b981f9034c5090fce517196977e57f3d6ed5fd8` |
| Report | `34c91a47d74fbdda3ae0b51eb6e0e7a70e1895fda7a7f12174e93390db0046ae` |
| Relative-path→file-SHA canonical inventory | `97b24d5dcbfd5097cd79ca62ea3ea00af750e2bd0ac918307c1cd598c647d653` |
| Experimental adapter | `465b38c0bb2adb264375f795d7f1fa7600bf76ca7b9f14b749a0217a9af28494` |

Every method retains the STEP 3-B inputs/voxelizer QA and engine/implementation
identities, original voxels, shared voxels, full-domain binary and solar maps,
ROI binary/solar arrays. Per scene: centres, ROI, both observer indices/valid/
XYZ/surface/actual-height arrays and signed pairwise solar differences. Full
contributions remain in the input metadata. Root report records settings,
frame audit, invariants, context, domain/ROI summaries and pairwise transitions.
Root manifest hashes all artifacts; child manifests preserve input array and
source identities and the engine source-content SHA. Generated files stay ignored.

Arrays and JSON are read back; JSON is verified in a temporary file before
publication. Root manifest is published last. A separate durable binary-stage
report and all three scenes' binary artifacts precede any Solar connection
attempt. Injected Solar failure therefore returns **binary PASS / direct BLOCKED**
with no completed root manifest. Missing/overlapping/all-building scenes,
observer displacement, input mutation, invalid intensities, partial writes and
failed root-manifest publication are rejected. An orphan completed voxelizer
child manifest does not establish completion of Solar/Shadow.

## Validation and handoff

The 23 new tests are self-contained, import no Candidate B test fixtures and use the
existing kernels only for the subject under test, not to manufacture expected
results. Focused command:

```powershell
.venv/Scripts/python.exe -m pytest -q -ra tests/test_synthetic_height_solar.py tests/test_synthetic_height_voxel.py tests/test_synthetic_height_distribution.py tests/test_candidate_b_shadow.py tests/test_candidate_b_solar.py
```

**107 passed, 2 warnings, 54.76 s**, no failures or skips. Warnings are existing
Rasterio Affine PendingDeprecationWarnings. Includes STEP 3-A/B and affected
Candidate B shadow/solar synthetic regressions. Full local pytest is not run;
unchanged Windows/Ubuntu CI is the full regression gate,
with pip cache, `--durations=30` and existing assertions/conditions preserved.

Before real-data application, agree roof method/unknown policy and ownership,
validate actual grid/true-north conversion at that location, common DEM/D0,
coordinate registration and observer height interpretation, and supply a
sun-dependent context bound. Preserve scientific/Acceptance gates. This
experiment does not accept real roof geometry, site solar accuracy, arbitrary
frames/terrain/angles, complex cavities or a formal height-distribution schema.
No real PLATEAU/T5, Canopy or GVI processing, old run modification, Standard/
Adapter/engine change or replacement of the representative-height model occurred.
