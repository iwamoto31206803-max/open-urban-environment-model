# B1 Real-Data Geometry and Observer Diagnostics — Phase 2

Status: **Read-only diagnostics completed; scientific accuracy UNVERIFIED.**
Inspected main `a7b5766` (PR #120 merged). Basis:
[parameter audit](../../planning/OUEM_B1_VoxCity_Parameter_Baseline_Audit_v0.1.md),
[synthetic sanity verification](B1_PHYSICAL_SANITY_PHASE1.md), and
[Phase 3C execution evidence](README.md#phase-3c-shared-z-real-data-verification--2026-10-29-jst).
No Voxel/Solar API was executed on A/B; no parameters, Standard, contract,
Acceptance, historical report or Run was changed. Reading Standard XYZ and
reconstructing expected intervals are diagnostics, not model regeneration.

## 1. Evidence, data structure and reproduction

Existing run root prefix:
`data/work/shared-vertical-domain/phase3c-20261029-01/outputs/`.
A: `komae-a-3c-20261029-01`; B: `komae-b-3c-20261029-01`.
Each retains `run-config.json`, `submitted-config.json`, `voxel-receipt.json`,
`voxel/` and `solar/` reports, arrays, TIFFs and statistics.
ROI: A `[-23320,-40760,-23256,-40696]`, B `[-23384,-40760,-23320,-40696]`,
EPSG:6677; 32 m context. Shared shapes: A 128×128×27; B 128×128×26.
Saved provenance identifies VoxCity 1.7.0 commit
`fa212656305328a9a657973bae26f352bfe813bc`; diagnostics use Python 3.11.9,
NumPy 2.4.6, rasterio 1.4.4 and pyproj 3.7.2 in the OUEM venv.
The reader imports no VoxCity simulation API. Recorded Consumer PASS is verified
as historical evidence; no fresh Consumer/eligibility/Acceptance is asserted.

| Artifact / path relative to repository unless noted | CRS / resolution / axes | Values, missingness and provenance |
|---|---|---|
| `data/work/terrain-reproducibility/komae-20261026-01/generated/standard.tif` and `.manifest.json` | EPSG:6677, 0.5 m north-up, 600×800 | Float32 H [m], NoData -9999; Tokyo Tama 0.50 m ground grid 09LD3451, source-declared T.P. |
| `data/work/real-komae-source-h/run-20261028-04/standard/standard.gpkg` and `.manifest.json` | EPSG:6677 XY; EPSG:6695 declared vertical, gravity-related H [m] | Actual XYZ BLOBs retain source-H (`identity_H`), PLATEAU 2025 source LoD2. No ellipsoidal conversion; geodetic compatibility is not survey accuracy. |
| `data/work/meta_chmv2_komae_committed_audit_20261025/chmv2_aoi.tif` | EPSG:3857, native projected spacing ~1.194329 m, 313×414 | UInt8 CHMv2 estimated height [m], zero valid, NoData=None plus raster mask. Web-Mercator spacing is not ground-distance accuracy. Acquisition/evidence bindings remain in Envelope manifest. |
| `data/work/height-envelope/komae-exploratory-20261026-01/generated/{canopy_top_z,canopy_bottom_z,height_envelope_state}.tif` and manifest | EPSG:6677, 1 m north-up, 300×400 | Float32 top/bottom H, NoData -9999; CR=0.60, top=DEM+CHM, bottom=DEM+0.40 CHM at Envelope pixel centres. State uint8: valid=1, other values bitwise error flags, no NoData; state=1 is not tree presence. |
| Per-run `voxel/{terrain_H,effective_ground_H,effective_dem,ground_indices,building_ids,building_heights,centre_lon,centre_lat,centre_x,centre_y,roi_mask}.npy` | Actual VoxCity u/v SOUTH_UP centres, nominal 1 m; H arrays absolute except D_eff and relative heights | Terrain sampled at actual centres; effective ground conditioned to per-owner mean; D_eff=H_eff−D0. IDs: 0 means no building, positive IDs bind source/OUEM IDs. ROI boolean. Full 16,384 DEM samples finite in each run. |
| `voxel/{voxels.npy,building_segments.json,whole_building_footprints.geojson}` and report | Base 3D u/v/up array; whole footprints EPSG:4326 | Class 0 AIR, -1 subsurface, 1 unobserved Bareland surface, -3 Building. Segments/contributors and selected-building inventory retain identities; class array alone has no per-building ID. |
| `solar/{current_voxels,no_canopy_voxels,tree_mask}.npy`, `grid.json` | Shared 3D u/v/up, z edge H=D0+k×1 m; centre adds 0.5 m | Int8 classes plus -2 TREE; boolean TREE mask. NoData is not a voxel class. Current minus TREE exactly equals No-Canopy, including shared upper AIR. |
| `solar/{canopy_top_H,canopy_bottom_H,envelope_state,canopy_candidate,canopy_missing,canopy_outside}.npy` | Saved actual-centre samples from Envelope, not directly aligned source raster indices | Float64 loaded samples and boolean masks; positive depth + valid state/mask defines candidate. Both runs have state=1 everywhere, but thousands of valid zero-depth cells. |
| `solar/{observer_index_k,observer_valid,roi_mask,solar_current,solar_no_canopy,solar_difference}.npy` and `statistics.json` | 2D u/v; index k is dimensionless, irradiance W/m² | Valid observer mask excludes buildings. Stored k exists even on excluded columns; those indices are not physical observations. Solar NaN excludes, numeric zero is valid complete attenuation; Difference=No-Canopy−Current. |
| Existing per-run 2D GeoTIFFs and new diagnostic TIFFs | EPSG:4326 rotated affine at saved centres; nominal actual horizontal spacing ~1.000093 m | TIFF[row,col]=NPY[nu−1−row,col]. Do not align by index with EPSG:6677 north-up data. Existing solar float NaNs have NoData=NaN; IDs/masks have valid zero. QGIS Identify may use a virtual display grid; exact original-cell lookup remains separate. |

`gis_visualization.inspect_run` checks frozen config/receipt/report/grid/2D
handoffs. The new [read-only diagnostic owner](../../../src/ouem/b1_geometry_diagnostics.py)
then authenticates every delivered output (including 3D), reads actual Standard
XYZ, checks footprint fractions, reconstructs expected intervals and samples
existing CHM/DEM. No acquisition, Converter, allocator, solar or write-to-source
path is invoked. Missing required arrays stop without regeneration. No upstream
file was unavailable in this inspection.

Local diagnostic root **R**:
`data/work/b1-geometry-diagnostics/phase2-20261030-01/` (ignored).
Each `R/a/` and `R/b/` contains `diagnostics.json`, `cells.csv` (all cell indices,
XY/lon/lat, flags and H), `building_segments.csv`, `buildings.csv`, 17 diagnostic
GeoTIFFs, `diagnostic_maps.png` and `representative_sections.png`.
Files are not formal Standard/GIS deliveries. CSV retains excluded-column values
with `valid=False`; observer TIFFs mask those columns to NaN.

```powershell
# Choose a NEW output directory; the CLI refuses reuse or output within the Run.
.venv/Scripts/python.exe -m ouem.b1_geometry_diagnostics `
  --run-root data/work/shared-vertical-domain/phase3c-20261029-01/outputs/komae-a-3c-20261029-01 `
  --output data/work/b1-geometry-diagnostics/<new-diagnostic-id>/a
# Repeat for B, with a separate new /b output. No model execution.
```

## 2. Terrain and actual observers

Quantiles below refer to **ROI & observer_valid**, not building columns.
Values are min / median / max, metres; CSV retains full precision.

| Quantity | A (3,722 observers; 374 ROI exclusions) | B (3,930 observers; 166 ROI exclusions) |
|---|---|---|
| Original DEM H | 19.586000 / 22.669500 / 23.955000 | 21.231001 / 23.090000 / 24.976000 |
| Effective ground H | Same as original DEM on these non-building columns | Same as original DEM on these non-building columns |
| Voxel surface upper H | 20.586000 / 23.586000 / 24.586000 | 22.120001 / 24.120001 / 26.120001 |
| Observer centre H | 22.086000 / 25.086000 / 26.086000 | 23.620001 / 25.620001 / 27.620001 |
| Observer − original DEM | **2.001001 / 2.485001 / 3.000000** | **2.001001 / 2.390001 / 3.000000** |
| Observer − effective ground | Same distribution as above | Same distribution as above |
| Observer − voxel surface | 1.500000 / 1.500000 / 1.500000 | 1.500000 / 1.500000 / 1.500000 |
| Surface − effective ground | 0.501001 / 0.985001 / 1.500000 | 0.501001 / 0.890001 / 1.500000 |
| Observer − DEM, p05 / p95 | 2.051001 / 2.952000 | 2.054001 / 2.945551 |

Full-domain valid observers number 12,638 / 13,923; median DEM offsets are
2.470001 / 2.439001 m. The separate 3,746 / 2,461 building-owner columns have
ground-conditioning changes (H_eff−H_DEM) of −0.319425…+0.561471 m /
−0.529323…+0.561471 m. Their hypothetical stored observer heights are excluded
from Solar and all observer statistics above; they must not be plotted as valid
roof/interior exposure points.

Actual ground/surface indices, saved observer k and first walkable transitions
agree at every valid column in both cases. With nominal 1 m cells:

```text
D_eff = H_eff − D0
g = int(float32(D_eff) + 0.5) + 1        # positive, Numba rounding path
surface_upper_H = D0 + g
observer_k = g + int(1.5 / 1) = g + 1
observer_centre_H = D0 + observer_k + 0.5
```

Thus surface-rounding residual plus the retained surface layer contributes
about 0.5–1.5 m above effective ground; the requested 1.5 m adds to that surface.
This explains the ~2–3 m DEM offsets without invoking a vertical-datum shift.
An equal uniform translation of all observers and occluders would leave ray
visibility unchanged. An absolute +1 m residual alone is therefore not a measured
Solar error; relative rounding, terrain/support differences and shape/priority
approximations matter. Their Solar sensitivity is not measured in this phase.

**D0 dependence:** A D0=19.5860004425; B D0=20.1200008392 m. In the common
context area, inverse-affine matching finds 8,192 A centres inside B. Among
6,235 pairs with both observers valid and *exactly equal sampled DEM*, matched
centres differ by at most 0.000950 m. Observer H_A−H_B is −0.534000397 m
(2,485 pairs) or +0.465999603 m (3,750 pairs). Example: A(0,0)/B(0,64) H is
23.086000443/23.620000839 m. `R/overlap-D0.json` records this calculation.
These are near-coincident, not identical centres. The non-building effective
grounds equal their sampled DEM, so changing D0 changes the rounding phase.
**Within-run Current/No-Canopy observers match; cross-run A/B are not necessarily
the same physical-height experiment.** This is a documented quantization concern,
not permission to change D0 or observer physics.

Representative ROI points, EPSG:6677 XY (rounded), with evidence in `R/{a,b}/cells.csv`:

| Point | XY [m] | DEM / effective H | Surface H | k / observer H | DEM offset |
|---|---|---|---|---|---|
| A(37,95), minimum offset | −23256.500, −40754.500 | 21.084999 | 21.586000 | 3 / 23.086000 | 2.001001 |
| A(39,91), maximum offset | −23260.500, −40752.500 | 22.086000 | 23.586000 | 5 / 25.086000 | 3.000000 |
| B(52,63), minimum offset | −23352.500, −40739.500 | 23.618999 | 24.120001 | 5 / 25.620001 | 2.001001 |
| B(44,50), maximum offset | −23365.500, −40747.500 | 22.620001 | 24.120001 | 5 / 25.620001 | 3.000000 |

## 3. Building representation

| Check | A | B |
|---|---:|---:|
| Selected buildings / occupied owner cells | 41 / 3,746 | 22 / 2,461 |
| Whole footprints crossing computation domain | 16 | 5 |
| Relative-height minimum / maximum [m] | 2.669989 / 21.240259 | 2.046862 / 12.346167 |
| Segment voxel-top − source-H top, min / median / max [m] | 0.196291 / 0.658521 / 1.413052 | 0.335433 / 0.992862 / 1.874481 |
| Source XYZ min/max versus saved source-H inventory | Exactly equal for all 41 | Exactly equal for all 22 |
| Standard normalized footprint versus saved whole footprint, maximum projected Hausdorff [m] | 2.33e-9 | 2.33e-9 |
| Cell contributor mismatch at >0.3 footprint fraction | 0 / 16,384 checked cells | 0 / 16,384 checked cells |
| Building interval / ID support mismatch, unexpected gaps, TREE in non-air reference | 0 | 0 |
| Cells with multiple accepted contributors | 0 | 0 |

The discrepancy is consistent with ground/surface rounding plus rounded relative
building height; the segment begins immediately above the voxel surface with no
unexplained gap. Cell occupancy is intersection-fraction rasterization, not a
point-footprint equivalence. Sub-threshold geometric contact between footprints
was not independently surveyed. Whole shapes remain uncut; finite computation
cells truncate boundary objects, without modifying their source geometry.

Examples (full source/OUEM IDs are in `buildings.csv` and `building_segments.csv`):
A id12 is shortest; id75 (`bldg_aa680eae-dbbd-426c-9d7a-1f5efaaab316`) is tallest
and crosses the boundary. B id86 is shortest; id28
(`bldg_9cb35e09-2efd-4b3d-9546-4c85cf9b5b01`) is tallest. These are rankings,
not judgments of implausibility. Largest top discrepancies occur at A(16,35),
owner69, XY≈(−23316.500,−40775.500), +1.413052 m; B(24,52), owner78,
XY≈(−23363.500,−40767.500), +1.874481 m (`cells.csv`, `building_top_error`).

This is **2.5D**: unioned positive-area source projections and one maximum-H roof
proxy with grounded segments. Sloped roofs, overhangs, under-building openings,
facades and actual interior voids are not faithfully represented. Original LoD2
XYZ remains unchanged in Standard; agreement of maxima/footprints does not prove
full 3D fidelity. Source geometry-bottom minus effective ground reaches −0.439424 m
(A id68) / −0.367632 m (B id59); no survey benchmark establishes whether that is
terrain/surface semantics, date/measurement error or a physical offset.

## 4. Canopy representation

At **Envelope source-pixel centres**, the same existing CHM/DEM exactly reproduce
saved Float32 top/bottom in both runs (0 mismatches). CR=0.60 thickness residual
is within ±2.68e-6 m (Float32 arithmetic). CHM ranges 0–23 m, median 13/10 m
over each full domain; estimated crown depth reaches ~13.8 m. Actual-centre DEM
minus Envelope-centre DEM ranges −0.488…+0.576 m (A), −0.741…+1.089 m (B).
This is a different sampling support, not a changed source raster or H transform.

| Quantity, whole computation domain unless specified | A | B |
|---|---:|---:|
| Valid state=1 cells / positive-depth candidates | 16,384 / 11,741 | 16,384 / 11,547 |
| Valid zero-depth cells | 4,643 | 4,837 |
| Candidates excluded below effective ground | 0 | 3 |
| Thin intervals expanded / vanished by rounding alone | 12 / 0 | 40 / 0 |
| TREE columns / voxels | 11,175 / 95,735 | 11,196 / 87,384 |
| Building-priority removed TREE voxels / fully removed columns | 3,078 / 566 | 2,272 / 348 |
| Surviving TREE columns above building-owner columns | 498 | 491 |
| TREE in ground/surface/Building, unexplained interval mismatch / disconnected columns | 0 / 0 | 0 / 0 |
| ROI valid: actual top − Envelope top, min / median / max [m] | 0.196001 / 0.982000 / 1.792002 | 0.106001 / 0.884001 / 1.868002 |
| ROI valid: actual bottom − Envelope bottom, min / median / max [m] | 0.032001 / 1.004002 / 1.989000 | 0.065001 / 0.955000 / 1.971001 |
| ROI valid: actual crown thickness − continuous depth, min / median / max [m] | −0.600002 / 0 / +0.799999 | −0.800001 / 0 / +0.800001 |

Pre-priority interval endpoints and post-priority surviving endpoints are
separate fields. Both first include the engine surface-layer/rounding behavior;
the latter can additionally lose its lower part to Building. Actual bottom
residual reaches **+8.567 m** at A(1,107), owner169, XY≈(−23244.500,−40790.500):
Envelope bottom 26.019001 H, surviving TREE bottom 34.586000 H. B(102,76),
owner28, XY≈(−23339.501,−40689.500): bottom 28.700001→37.120001 H, +8.420 m.
Both are context points. This is Building priority, not an 8 m datum conversion
error; whether estimated vegetation should exist there is independently unverified.

B's three below-ground exclusions are context cells (85,11), (109,29), (115,41).
Their Envelope bottoms 24.570000, 24.893999, 24.736000 H are below actual sampled
DEM/effective ground 24.650000, 24.990999, 24.796000 H by ~0.080, 0.097, 0.060 m.
All have CHM=1 m and continuous depth ~0.6 m. They remain excluded without
height adjustment. Nearest sampling at different centre grids explains this
numerical relation; real vegetation/ground truth is not established.

Thin positive crowns can be represented by one whole metre. B(126,30), context,
XY≈(−23385.500,−40665.500), has CHM=1 m, continuous [25.361000,25.961000] H;
its interval expands to [25.120001,26.120001] H. Bottom error −0.240999 m is
the documented thin-crown rule, not penetration into ground (surface=25.120001).
Largest adjacent top step is +6.987003 m at A(115,54) / B(115,118) across v;
the next is −6.971998 m at A(109,11) / B(109,75) across u. Same physical source
feature occurs in the overlapping contexts. These are review candidates, not
proven CHM artifacts or implementation discontinuities.

## 5. Prioritized issues and limits

Categories: **A** implementation inconsistency; **B** known approximation or
discretization; **C** source accuracy/uncertainty; **D** not yet decidable.

| Priority / category | Evidence and potential B1 effect | Next action (not performed) |
|---|---|---|
| P1 / B | ROI observer DEM offsets ~2–3 m; `observer_minus_dem.tif`, quantiles/points above. Both cases have exact 1.5 m offset only from voxel surface. Shadow reach/exposure differs from a DEM+1.5 m interpretation. | Agree physical observer definition before any code change or sensitivity run; keep existing evidence separate. |
| P1 / B | D0-dependent rounding yields ±~0.5 m A/B observer differences even at matching DEM support; `R/overlap-D0.json`. Cross-extent Solar comparisons mix scene/domain and vertical-grid phase effects. | Design a controlled comparison with explicit physical observation heights and geometry; do not reset D0 or call earlier A/B a fixed-height field experiment. |
| P1 / B,C | Building top error up to 1.874481 m and TREE top error near 2 m; 2.5D roof proxy/grounded supports, CR geometry and priority truncation. Relative geometry can change shadow lengths and optical path lengths; absolute offsets alone do not quantify that change. | Review sections and independent geometry; separate quantization sensitivity from input-shape validity before modifying rules. |
| P2 / B,C | B's 3 below-ground exclusions and 40 thin expansions; differing sampling supports can exceed a 0.6 m crown depth. `cells.csv` below/thin flags and points above. | Assess centre-support and thin-crown policy in a separately scoped test, without snapping inputs. |
| P2 / C,D | 498/491 surviving crown columns over building-owned cells; bottom truncation up to 8.567/8.420 m; ~7 m adjacent top steps. Occupancy priority is correct, ecological presence is unverified. | Compare independent vegetation/roof observations and source age; do not interpret positive candidates as verified trees. |
| P2 / D | Source-declared T.P./EPSG:6695 compatibility, estimated CHMv2/CR, physical tree base and true surface heights lack independent survey evidence. | Obtain appropriate external checks only with separate authorization; no datum correction inferred here. |
| P2 / B,D | 16/5 boundary buildings and finite context; earlier 32 m isotropic bounds fail. Preserved Solar masks/difference agree, but exterior-shadow sufficiency and field accuracy remain unverified. | Retain context warnings; design convergence/field-validation work separately. |
| No A identified in tested invariants | All 21 stored-array checks zero; source-H extrema, source-pixel formulas and 32,768 footprint-cell contributor checks agree. | No production-code correction justified by this inspection. This is bounded consistency evidence, not proof that no implementation defect exists. |

## 6. Spatial outputs, preservation and tests

`diagnostic_maps.png` contains six indexed plan maps with the actual ROI outline;
axes are u/v, not a projected north-up substitute. Red ROI outline and colour
bars are present. `representative_sections.png` shows minimum/median/maximum
ROI DEM-offset observer sections, with source/effective ground, canopy envelopes,
Building (gray), TREE (green), surface (yellow), subsurface (brown) and valid
observer centres (red). Figures for A/B were inspected as PNGs. QGIS GUI display
of the **new diagnostic TIFFs** was NOT_VERIFIED; no QGZ was updated.

Each source inventory is rehashed after its diagnostics. After B, an additional
combined check verified **164 unique existing files**, including all **136 Run
files (68 per location)** and shared upstream records/data; no missing upstream
file or changed hash/size was found. The check also read all **34 new diagnostic
GeoTIFFs**, confirming saved UV-to-TIFF values, EPSG:4326 and NaN masks (valid
zeros retained). `R/post-B-verification.json` records the preserved identities;
diagnostic JSONs record exact original source hashes and diagnostic source hash.
`R/spatial-verification.json` additionally checks every diagnostic TIFF affine
against its original Solar affine and all 16,384 geographic centres per case;
maximum longitude/latitude arithmetic residuals are 2.84e-14 / 7.11e-15 degrees.
Hashes show consistency, not authenticated execution or scientific correctness.

| Local evidence under R | SHA-256 |
|---|---|
| `post-B-verification.json` | `f9de8af97a3137b22d800279e778ea543229ef5270a49c0e4f489a597552bf79` |
| `overlap-D0.json` | `ecc25e93d4d8df2d24d5fa67b9b97ae255f57cfd22aa62c0a4fc099f044aeda0` |
| `spatial-verification.json` | `0c75dac6fdfe6e2cbe1d8565584e5c47988f6d51ccf030b46fc036a9b547ee52` |
| `full-pytest.log` | `ab0d1c20dcd5592f7c5855d53cbad7d5d51df3d53aa59a991a07d588c6d75842` |

Unit cases cover non-square arrays, observer/surface offsets, thin/vanished and
below-ground intervals, Building priority, corrupted occupancy/observer/shape,
footprint fractions, shifted sampling support and rejection of output reuse.
**9 unit tests passed**; **86 related tests passed (25 warnings, 30.17 s)**.
Full pytest: **1,020 passed, 9 skipped, 298 warnings in 473.48 s**.
Skips: four isolated-GIS-runtime tests and five Windows symlink-privilege tests.
Warnings: rasterio affine deprecations (including three new synthetic raster
fixtures) and the existing source-H stat/fstat diagnostic UserWarning.
Reproduction (use a NEW unused temporary directory):

```powershell
.venv/Scripts/python.exe -m pytest -q -ra tests/test_b1_geometry_diagnostics.py
.venv/Scripts/python.exe -m pytest -q -ra --basetemp data/work/<new-short-test-temp>
```

Full regression uses the same OUEM venv with per-command approval review to
allow existing NTFS hardlink tests and a short temporary path, as in Phase 1;
no persistent environment/security setting is changed. Read-only diagnosis
emitted a Shapely `ops.transform` deprecation warning per location, not a geometry
failure. The completed local `full-pytest.log` retains actual warning/skip details.
No real-data simulation, independent field measurement or formal status change
is part of this report. Inputs needed for the performed numerical checks were
available; physical accuracy, dates, true crown/roof interiors and exterior
objects remain UNVERIFIED rather than reconstructed by assumption.
