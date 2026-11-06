# STEP 4-A — Real LoD2 Absolute Roof-Top Distribution

2026-11-06. Baseline main **171f2afcef50405597465dfe2a91cf2c731b5ff1**
(PR #165 merged). **COMPLETED_EXPERIMENTAL** for the four fixed audited samples.

| Dimension | Result / boundary |
|---|---|
| Input technical eligibility | **PASS_LIMITED_FOUR_SAMPLE_PROFILE**; explicit roof semantics and unique face correspondence reverified |
| Absolute roof H geometry/numerics | **PASS**, centre and cell_max, no support interpolation |
| HAG / Voxelizer connection | **HAG NOT_CALCULATED / Voxelizer NOT_VERIFIED**; no DEM subtraction or engine execution |
| Scientific validity / Formal Acceptance | **NOT_VERIFIED**, `terrain_integration_ready=false` |

This success is geometric derivation of source-declared absolute H, not
measurement of real building height or proof of accuracy/datum realization.
The local GroundSurface footprint choice below is authorized only for STEP 4-A;
it does not change OUEM Standard/Adapter or retrospectively accept all 32 LoD2.

## Fixed audit and source chain

Reviewed [STEP 4-0 record](STEP4_0_REAL_LOD2_ACCEPTANCE_AUDIT.md),
[auditor](../../../src/ouem/lod2_roof_audit.py),
[STEP 3-A](STEP3A_SYNTHETIC_HEIGHT_DISTRIBUTION.md),
[3-B](STEP3B_SYNTHETIC_VOXELIZATION.md), [3-C](STEP3C_SYNTHETIC_SOLAR_SHADOW.md),
their code, `height_envelope.GridSpec`, and Mixed-LoD Raw/Native/Standard/Consumer.

The immutable STEP 4-0 run is
`data/work/step4-0-roof-audit/audit-final-e/`:

| Artifact | SHA256 |
|---|---|
| Audit `manifest.json` | `14498ba34826c2b68c2a22c29da6fcbeb8bc696e20b68f799d8a8cca0a41a852` |
| Audit `report.json` | `71de561a0644352654c4d30814259f3d42b1d31a18b9c1591652be88c1b3565e` |
| Standard manifest | `9789d443e0286ad0c5da57156d7ba10ed19adafba5e42cec068e9deeead0f789` |
| Standard GeoPackage | `954d01aad3004a0d2d69586036ef9961071064a39db4215d45577dee2f996f60` |
| Native GeoPackage | `1e2af898307e5f9bfbc4fbc86ab714dfad2557e2371ff98138171eb768ca7da7` |
| Original CityGML ZIP | `659fe9f96eb8a45b57e788b52d6e80edef154ddc3aa9b4f2c1ea117c61a5a555` |
| Member `udx/bldg/53393466_bldg_6697_op.gml` | `6128aa2a2bd637e51dbef89ee42bd54620eae6a2fab82b082149a4dc4924c0c9` |
| Candidate B T5 report | `1a4c3ed60bebcb92b00f5a28dbb52ceea78fd4b9eb4893cb87445dc17080695f` |

[Adapter](../../../src/ouem/real_roof_distribution.py) pins both audit artifacts,
rechecks all 41 historical input identities, and replays the existing read-only
Consumer chain: Raw selection, saved Converter outputs, Native and Standard.
No Converter, writer, Terrain diagnostic, Voxelizer or environmental API runs.
Historical DEM files are hashed as provenance only; no DEM is sampled/subtracted.
Raw→Native exact unique XYZ/ring matches and ordered Native→Standard XY/H matches
are checked again, and all four face mappings compared to the historical audit.
The four sample IDs come from that pinned report's deterministic categories:

| Label | source_id | ouem_id | Roof polygons / GroundSurface polygons |
|---|---|---|---:|
| F | `bldg_09532951-4dab-457d-b1c6-56d509900d1b` | `oub-c56cb020-c11c-5f9c-a37f-73018266a333` | 1 / 1 |
| S | `bldg_040379e5-dffb-40b6-a392-6396158211f5` | `oub-664a9132-cf36-52a5-96f5-577e78c91e59` | 69 / 1 |
| M | `bldg_2bd71700-a145-46ff-b14f-ad60394ff253` | `oub-cb250497-c12d-5fcc-9dca-e82c8b051398` | 30 / 1 |
| C | `bldg_2d5a9713-b02f-4903-9164-c5653e03494d` | `oub-10894413-4369-5131-ac0d-78ee9d234016` | 12 / 1 |

Only **112 explicitly identified RoofSurface polygons** enter evaluation.
Walls/Ground/unknown semantics cannot enter as roof. Face IDs, semantic surface
IDs, Native/Standard face indices, Standard XYZ rings, ZIP/member/manifest/audit
SHAs remain traceable. Source/license declarations and the STEP 4-0 recorded
licence-summary/resource-link discrepancies remain unchanged; no fresh source
acquisition, licence clearance or accuracy certification is implied.

## Limited input policy and kernel reuse

Building presence is the union of valid **GroundSurface XY projections**, adopted
provisionally here. Every GroundSurface polygon and the union are validated;
union must be a positive-area valid Polygon. Disconnected MultiPolygon is
BLOCKED, never reduced to the largest piece. These four each have one ground
polygon; multiple connected/disconnected inputs are covered by independent tests.

Actual roof support is **RoofSurface XY projection ∩ provisional footprint**.
Original roof projections, original ground projections, per-face intersections,
their unions, uncovered/outside areas and per-cell fractions are saved separately.
There is no snap, buffer, repair, filling, vertex-Z modification, representative
fallback or unsupported interpolation. Raster pixels with positive partial
support do not claim their entire square is covered by physical roof.

The unchanged STEP 3-A validation/intersection/centre/vertex-maximum loop was
extracted as **`sample_roofs()`**, returning only geometry/cell contributions.
Its synthetic `derive()` wrapper still supplies the synthetic profile/datum and
environment; real data **never passes through that wrapper**. The new real
wrapper has its own profile, actual environment, source identities and vertical
declaration. `_face`, `_z`, positive-area filtering, `covers` seam rule and
polygon-vertex maximum logic are unchanged; no triangulation engine was added.

Existing STEP 3-A analytic tests pass. An additional read-only comparison against
the six archived STEP 3-A cases verified equal canonical cell/source/grid data,
identities and comparison summaries; original archive SHA remains
`b924247829ab1559693b178a2fc18fb45bbfe8d61823607fac8a8b2bb7b2ca8f`.
Historical implementation SHA `43bc89a67a4b6a29e34315ac882e20ad21d1a072589c118619e40a3b6601271d`
is retained separately from the new shared-module SHA. It is not impersonated.
No old STEP 2/3/4-0 artifact was regenerated or overwritten.

## Grid and state registration

EPSG:6677, **1 m**, fixed global phase origin **(0,0)**. Each default domain is
floor/ceil of the combined original roof/footprint bounds, plus one whole-cell
halo. Top-left origins are integers; centres are integer+.5. Columns advance
east `[1,0]`, rows south `[0,-1]`, north-up Affine `[1,0,xmin,0,-1,ymax]`.
No half-cell shift, warping or T5 domain/grid regeneration.

| Label | Processing bounds `[xmin,ymin,xmax,ymax]` | Shape rows×cols |
|---|---|---:|
| F | `[-22583,-39851,-22568,-39845]` | 6×15 |
| S | `[-22569,-39836,-22543,-39821]` | 15×26 |
| M | `[-22535,-39924,-22519,-39910]` | 14×16 |
| C | `[-22578,-39832,-22566,-39820]` | 12×12 |

`footprint_fraction` and `roof_coverage_fraction` both use **full cell area** as
denominator. Roof coverage is the union, not the sum of overlapping faces.
All positive-area face contributions remain in each method's table, including
centre-unsupported candidates; only method-supported Z values enter its maximum.
Closed-set centre support can retain multiple faces on a seam. Boundary-only
line/point intersections create no support or building-presence contribution.

| State raster code | Cell meaning | Absolute-H raster |
|---|---|---|
| 0 NO_BUILDING | zero footprint-cell intersection area | NaN NoData |
| 1 KNOWN | BUILDING_PRESENT and method has supported top | finite Float64, including valid 0 |
| 2 TOP_UNKNOWN | BUILDING_PRESENT but method has no supported top | NaN NoData |
| 255 | reserved state NoData (not emitted in these complete grids) | separate from absence/unknown |

State 0 is a valid classification, not a masked state pixel. Fraction rasters
contain valid zero outside support/footprint. Top/difference rasters use NaN
NoData; the independent state rasters distinguish absence from unknown. Signed
comparison is **cell_max − centre** on mutually KNOWN cells only; all other
differences remain NoData. Cell records include row/col, centre XY, presence,
source/OUEM ID, method, value/null, validity/reason, fractions, partial support,
all contributions and JSON references to original XYZ/source/audit identities.

## Geometric and numerical results

| Sample | All cells / building / absent | Centre known / unknown (% of building) | cell_max known / unknown | Footprint boundary / partial roof cells | Numeric differing cells / max Δ m |
|---|---:|---:|---:|---:|---:|
| F | 90 / 39 / 51 | 24 / 15 (38.4615%) | 39 / 0 | 30 / 30 | 0 / 0 |
| S | 390 / 261 / 129 | 218 / 43 (16.4751%) | 261 / 0 | 70 / 72 | 218 / 4.267302 |
| M | 224 / 122 / 102 | 95 / 27 (22.1311%) | 122 / 0 | 48 / 49 | 93 / 3.176679 |
| C | 144 / 82 / 62 | 68 / 14 (17.0732%) | 82 / 0 | 35 / 37 | 64 / 2.526428 |

Totals: 848 processing cells, 504 building-present, 344 absent; centre 405 KNOWN
and **99 TOP_UNKNOWN**, cell_max 504 KNOWN. Those 99 cells are validity/support
differences, not numeric zero differences or filled centre heights. F has
constant height on shared support but still differs in boundary validity.

| Sample | Centre absolute H range m | cell_max absolute H range m | Used support area m² | Uncovered / outside-roof area m² |
|---|---|---|---:|---:|
| F | 27.085800–27.085800 | 27.085800–27.085800 | 23.2635234563 | 0 / 0 |
| S | 26.449288–33.666397 | 27.594152–33.684600 | 220.1300690006 | 1.617992e-7 / 2.550627e-6 |
| M | 27.647232–32.353658 | 27.660000–32.380000 | 97.0156999943 | 4.588219e-10 / 3.807146e-10 |
| C | 28.379400–31.921011 | 28.379400–32.003400 | 65.2570512368 | 0 / 1.658825e-7 |

Original roof/ground/intersection geometries and exact unrounded areas are in
`projections.json` and QA. These tiny differences are **numerical geometry
differences**, not certified missing roof or physical eaves. Partial-roof counts
can include tiny residuals inside otherwise full footprint cells; they are not
automatically treated as holes or zeroed by a threshold.

Independent centred least-squares plane equations (not the kernel's cross-product
normal) checked every supported face value and its centre/max support status.
Maximum Z discrepancy is **7.105428e-15 m**, within the **1e-8 m numerical budget**.
Each contribution remains within the original face-vertex mathematical Z range
within that same floating budget; maxima are not extrapolated from a whole cell
when support is partial. Tiny maximum overshoots at about 1e-12 m are retained,
not clamped by modifying source Z. This is numerical consistency, not precision
of the source survey. Summed union/footprint cell areas agree with their source
areas within **1e-7 m²** integration budget; this budget is not used to repair or
erase boundary differences. Known masks match finite-H masks exactly.

All four PNG diagnostic triptychs were visually inspected: centre/max share a
source-H colour scale, signed difference is separate; black outlines are ground
projection, red outlines original roof union. The outlines nearly coincide at
this scale, so micro-differences must be read from quantitative QA, not the image.
Cell painting beyond an outline indicates partial-cell support, not a buffered
roof. Blank top pixels preserve unknown/absence with separate state information.

## Vertical and integration boundary

Source declaration: compound EPSG:6697, horizontal EPSG:6668, vertical EPSG:6695.
Standard transforms XY only to EPSG:6677, retaining each H bit-for-bit. This run
evaluates those planar H values on the projected grid. No synthetic datum,
ellipsoidal-height substitution, DEM subtraction, D0 or owner-mean terrain is
introduced. Datum realization, epoch and physical accuracy remain unverified.

HAG is **NOT_CALCULATED**; Voxelizer connection **NOT_VERIFIED**. Future connection
requires an explicitly verified ground/vertical profile, model-grid registration,
ownership/rounding/capacity and unknown-support policy. North-up per-building
rasters are not implicitly the actual saved T5 cell centres. No unknown centre
may be replaced with representative height merely to enable a later engine run.

## Artifacts, reproducibility and validation

Windows OUEM venv: Python 3.11.9, NumPy 2.4.6, Shapely 2.2.0, Rasterio 1.4.4,
PyProj 3.7.2, Matplotlib 3.11.2. Reproduction from repo cwd, with the original
canonical saved-file layout and new output directories:

```powershell
.venv/Scripts/python.exe -m ouem.real_roof_distribution --audit-run data/work/step4-0-roof-audit/audit-final-e --artifact-root C:/dev --output-dir data/work/step4a-roof-distribution/final-c
.venv/Scripts/python.exe -m ouem.real_roof_distribution --audit-run data/work/step4-0-roof-audit/audit-final-e --artifact-root C:/dev --output-dir data/work/step4a-roof-distribution/final-d
.venv/Scripts/python.exe -m pytest -q -ra tests/test_real_roof_distribution.py tests/test_synthetic_height_distribution.py tests/test_lod2_roof_audit.py
```

Two independent real-data executions: **all 66 files byte-identical**, including
**36 GeoTIFFs and 4 PNGs**. All **47 watched inputs/code files** unchanged by
SHA/stat before/after (41 historical inputs, 2 audit artifacts, 4 current modules).

| Identity | SHA256 |
|---|---|
| Final root manifest | `f73e65073ed823b9155cc75a93a4cfdbc314fb9a0f1859f4d635ec5e71a952bd` |
| Final report | `c9f3315795dfa8ebba2d3d96a0fd89b8814e0301569da2c19c2f5151e9a9a9f1` |
| Relative-path→SHA canonical file inventory | `1111989b8fa076a548aad0d736bb234bbbac7d2e895a6e8b0464d6a1780f55f8` |
| Real adapter | `e5b2576c8ed2b1c6e0369922e9f3abf63f571f49f7d354eb2bc65a1f2856bce1` |
| Shared geometry module | `ee66f58d8de0b7bc09ecb317873b7663c2be8eaeaefcc4efc9f7eb35e7a46b54` |

Per sample: `centre_*` / `cell_max_*` top/state/roof-coverage/footprint-fraction
GeoTIFFs, `cell_max_minus_centre.tif`, both contribution tables, `inputs.json`,
keyed `source_faces.json`, `projections.json`, `qa.json`, `diagnostic.png`.
Custom projection JSON explicitly declares EPSG:6677; it is not mislabelled
RFC7946 geographic GeoJSON. Raster reopens verify CRS/Affine/shape/dtype/NoData,
units/quantity/vertical tags, all pixels/masks and four-corner cell coordinates.
Every JSON is reread before publication, and root manifest is last, after final
input-immutability checks. Failed runs cannot issue a completed manifest.
Outputs remain ignored; no dataset/generated artifact is committed.

[15 independent new tests](../../../tests/test_real_roof_distribution.py) cover
zero/NaN/absence, clipped-plane maxima, holes/seams/all contributions, micro
boundary preservation, multi-Ground unions, semantic/mapping/XYZ/footprint/grid
rejection, global grid phase, immutability, audit-pin failure, partial writes,
raster/JSON/PNG reread and reproducibility. Existing STEP 3-A and STEP 4-0 tests
are retained. Final focused result: **59 passed, no skips/warnings, 2.90 s**.
Initial extraction exposed an undefined wrapper-local `resolution` (14 failures
from one cause); it was corrected and all affected tests revalidated, without
changing assertions. An initial archive comparison used Python list/tuple
equality; canonical JSON comparison confirmed exact geometry data equivalence.

Full local pytest and local engine runs were not performed. Unchanged Windows/
Ubuntu full GitHub Actions, including STEP 3-B/C regressions, is the technical
gate; completed results are in the Draft PR. Pip cache, `--durations=30` and
existing acceptance conditions remain unchanged. Scientific/Formal gates and
the accepted representative model are not replaced by this limited PoC.
