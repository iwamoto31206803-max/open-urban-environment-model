# B1 VoxCity Parameter Baseline Audit v0.1

Status: **Audit and experiment proposal**, not scientific validation or Acceptance.
Inspected main `e4dbce720feb02f580270fdb7f1c793b04733681` (PR #118 merged).
No analysis, parameter change or new run was performed. Apply
[Development Principles P3–P5](../OUEM_Development_Principles_v0.1.md).

## 1. Runtime, evidence and source references

Read-only inspection used the ordinary Windows `.venv/Scripts/python.exe`:
Python 3.11.9, VoxCity 1.7.0, NumPy 2.4.6, Numba 0.68.0, rasterio 1.4.4,
pyproj 3.7.2. [pyproject.toml:18](../../pyproject.toml#L18) pins VoxCity to
`fa212656305328a9a657973bae26f352bfe813bc`; installed PEP 610 metadata records
the same Git origin, requested revision and commit. All 136 installed Python
sources match their SHA-256 RECORD entries. This checks installation integrity,
not an independent comparison with the upstream Git tree; see
[`voxcity_provenance()`](../../src/ouem/komae_integration.py#L151).

Source shorthand below uses **installed code**, not an inferred library default:

| Ref | File / owning functions (line numbers in inspected version) |
|---|---|
| S | [real_komae_solar.py](../../src/ouem/real_komae_solar.py): constants 27; `sample_canopy` 30–44; `integrate_canopy` 47–140; `solar_pair` 149–261; `preflight` 264 onward; `export` 379–393. |
| V | [real_komae_voxel.py](../../src/ouem/real_komae_voxel.py): `effective_ground` 51; `audit_voxels` 60–99; `prepare_buildings` 102; `raster_buildings` 121–150; `execute_model` 153–263. |
| E / C | [height_envelope.py](../../src/ouem/height_envelope.py): `ConstantCR` 89; `sample_raster` 181; `calculate` 213–243. [e2e_config.py](../../src/ouem/e2e_config.py): `RunConfig` 79 onward, snapshots/receipts 156 onward. |
| R | `.venv/Lib/site-packages/voxcity/simulator/solar/radiation.py`: `get_direct_solar_irradiance_map` 18–93. |
| K | Same package, `simulator/solar/kernels.py`: `compute_direct_solar_irradiance_map_binary` 11–92. |
| T | Same package, `simulator/common/raytracing.py`: `calculate_transmittance` 6; `trace_ray_generic` 11–156. |
| O | Same package, `utils/orientation.py`: `direction_to_axis_vector` 72–111. |
| Z | Same package, `generator/voxelizer.py`: `Voxelizer.__init__` 126–145; `generate_combined` 158 onward; `_voxelize_kernel` 40 onward. Ground conditioning: `geoprocessor/raster/core.py`, `process_grid` 48–92. |

Installed-source SHA-256 anchors for the active solar calculation:

| File | SHA-256 |
|---|---|
| R | `a05289164e306ac1a9d5c7fe22ad1b264eab84e82848441664610d28ef6f0c05` |
| K | `59b5bac159f41a841879089aa7385a9a0b72e8511dfbeff4773d21a9daa8b631` |
| T | `549e6a0a3c028e1fb638f9294f92afa0080d568580426440c97262ba263e24d7` |

Historical evidence is the [Phase 3C A/B record](../experiments/real_komae_solar/README.md#phase-3c-shared-z-real-data-verification--2026-10-29-jst),
with local runs under `data/work/shared-vertical-domain/phase3c-20261029-01/outputs/`
(`komae-a-3c-20261029-01` and `komae-b-3c-20261029-01`). Both saved Voxel/Solar
reports say COMPLETED; Voxel records Consumer technical PASS and Numba enabled.
This audit rehashed their selected current implementation/config-loader and
Building-manifest/Terrain/Envelope-manifest bindings: 5 Voxel and 6 Solar
identities per location match. It did **not** rerun Consumer, validate every
transitive input/output, or rerun the historical numerical comparisons.

The [official CPU API reference](https://voxcity.readthedocs.io/en/latest/autoapi/voxcity/simulator/solar/radiation/index.html)
agrees with the installed top-level signature and horizontal-direct meaning;
its short API description does not expose all `kwargs` defaults. The
[official solar tutorial](https://voxcity.readthedocs.io/en/latest/examples/demo_solar.html)
explicitly illustrates k=0.6, LAD=1.0 and height=1.5, but uses EPW/global-solar
entry points: example weather/time values are not defaults of OUEM's CPU call.
No discrepancy was identified for the active signature/these three values.
The documentation is `latest`, not a version-pinned proof; other APIs were not
exhaustively compared. In particular, the [GPU API](https://voxcity.readthedocs.io/en/latest/autoapi/voxcity/simulator_gpu/solar/integration/ground/index.html)
is a separate implementation and is not used here.

## 2. Actual calculation path

`RunConfig → real_komae_voxel.execute_model → Voxelizer.generate_combined`
produces the base Building/Terrain scene. Solar then samples the existing
Height Envelope at saved actual centres, integrates TREE using the same public
allocator and preserves D0/base occupancy while allocating shared upper air.
`solar_pair → get_direct_solar_irradiance_map → compute_direct_solar_irradiance_map_binary
→ trace_ray_generic → calculate_transmittance` is the active CPU ray path.

Relevant signatures in R/K/T/Z:

```python
get_direct_solar_irradiance_map(voxcity, azimuth_degrees_ori,
    elevation_degrees, direct_normal_irradiance, show_plot=False, **kwargs)
compute_direct_solar_irradiance_map_binary(voxel_data, sun_direction,
    view_point_height, hit_values, meshsize, tree_k, tree_lad, inclusion_mode,
    include_building_roofs=False)
trace_ray_generic(voxel_data, origin, direction, hit_values, meshsize,
    tree_k, tree_lad, inclusion_mode=True)
calculate_transmittance(length, tree_k=0.6, tree_lad=1.0)
Voxelizer(voxel_size, land_cover_source, trunk_height_ratio=None,
    voxel_dtype=np.int8, max_voxel_ram_mb=None)
Voxelizer.generate_combined(building_height_grid_ori, building_min_height_grid_ori,
    building_id_grid_ori, land_cover_grid_ori, dem_grid_ori, tree_grid_ori,
    canopy_bottom_height_grid_ori=None, **kwargs)
```

S makes **five** direct-API calls: Current and No-Canopy on the full domain;
a terrain-only diagnostic retaining conditioned ground and original observers;
and two ROI-cropped calls for the context diagnostic. There is no active EPW,
calendar/time-to-sun calculation, diffuse/global irradiance, reflection, GPU,
annual integration or slope-normal irradiance calculation. An older
[`canopy_shadow_poc.py`](../../src/ouem/canopy_shadow_poc.py) timestamp is not the
date of the current real-data A/B sun condition.
RunConfig exposes extent/context and input/output bindings, not sun, optical or
observer knobs; the latter remain constants/explicit calls in S. This audit
neither adds configuration keys nor proposes silently passing new `kwargs`.

## 3. Parameter ledger

OUEM value prefixes: **X** explicit argument/constant; **D** inherited default;
**U** upstream data/derived geometry; **I** library-internal rule, not a supported
OUEM configuration option. “Required” means the API supplies no default;
“N/A” means outside this path; **UNKNOWN** means not established by evidence.
Baseline policies below are proposals for a later authorized experiment.

| Parameter | VoxCity Default | OUEM Current | Source | Category | Effect | Baseline Policy | Verification |
|---|---|---|---|---|---|---|---|
| Sun azimuth | Required | X 135°, clockwise from true north | S:27,160–173; R:18–46; O:105–111 | Sun | Sunward ray and opposite shadow direction | Fix as artificial external condition | Cardinal-shadow and rotation oracle; saved vector |
| Sun elevation | Required | X 35° | S:27; R:18–24 | Sun | Shadow reach, horizontal irradiance factor | Fix, not an inferred date | Flat-scene height/tan(elevation) diagnostic |
| DNI | Required | X 800 W/m² | S:27; R:62–63 | Radiation | Linear scale of horizontal direct result | Fix external condition | Unobstructed ceiling = 800 sin(35°) = 458.861149 W/m² |
| Date/time, EPW, actual weather | N/A to this API | Not supplied; actual-weather correspondence UNKNOWN | R:18–63; S:242–244 | External conditions | Would define a different experiment | Do not invent a timestamp; agree separately if needed | Trace active API, not older demo timestamps |
| `tree_k` | 0.6 | X 0.6, equals default | R:36; S:173,189; T:6–7 | Canopy optics | Exponential extinction | Adopt default explicitly | Check recorded optics; analytic exp(-k·LAD·length) |
| `tree_lad` | 1.0 | X 1.0, equals default | R:37; S:173,189; T:6–7 | Canopy optics | Homogeneous path attenuation | Adopt default explicitly; no calibration claim | Homogeneous-crown path-length oracle; species/season UNKNOWN |
| TREE transmission cutoff | Internal T < 0.01 | I same; opaque hit yields exact zero | T:64–68; K:87 | Ray method | Discontinuity at low transmission | Preserve, document as numerical rule | Values immediately either side of cutoff |
| Building/ground obstruction | Internal allowed `(0,)`, exclusion False in R | I AIR passes; TREE attenuates; other intersected classes opaque | R:48–60; T:64–86 | Occlusion | Buildings/terrain stop direct beam | Preserve | Solid wall and conditioned-ground controls |
| `inclusion_mode` | Helper default True; R overrides False | I False, supplied by R | R:49; T:11 | Ray method | Inverts hit-set meaning | Keep public wrapper behavior | Inspect wrapper and call, not helper default alone |
| Ray stepping / domain exit | Internal DDA; axis EPS 1e-10, tie EPS 1e-12; clear beyond finite grid | I unchanged | T:23–30,90–156 | Ray method | Cell path lengths, boundary omissions | Preserve; boundary sufficiency unverified | Axis/tie rays and larger-context convergence later |
| `view_point_height` | 1.5 m | X 1.5, equals default | R:32; K:26,76; S:154,245–247 | Observer | int(height/meshsize) offset, then voxel-centre origin | Keep for compatibility; physical interpretation needs review | Compare saved k and nominal H, not DEM+1.5 assumption |
| `include_building_roofs` | False | X False | R:38; K:64–91; S:173 | Observer | Excludes building-roof observers | Adopt default | Finite mask exactly `building_ids == 0` |
| Grid rotation | 0° when extras absent | U actual `axis0_true_azimuth_deg`, explicitly passed in scene extras | R:41–46; V:232–241; S:160–171 | Orientation | True-north to array-axis mapping | Preserve derived rotation; do not reset to zero | Independent direction formula in S:216–219 |
| Voxel `meshsize` | Required scene metadata; no universal default | X nominal isotropic 1 m | Z:126; S:163; V:128,186 | Resolution | Geometry rounding, observer and path lengths | Maintain 1 m | Metadata, centres and ground-index QA |
| Horizontal centres / actual spacing | Derived by grid generation | U VoxCity actual lon/lat centres; A/B about 1.000093 m | V:153–178,232–246 | Geometry | Cell placement differs from exact projected 1 m grid | Preserve, record actual grid | Saved projected/geographic centres and affine |
| Building representation / ownership | Required prepared grids | U whole footprints, maximum source-H top, 2.5D grounded segments; X overlapping_footprint=True | V:102–150 | Building geometry | Roof proxy and overlap ownership affect shadow | Retain existing prepared data/rules | Owner/ID, segment and top-height scalar QA |
| Ground / D0 | Internal per-building mean, minimum-normalized DEM | U actual sampled Terrain, owner-conditioned ground; unchanged D0 | Z:182–183; V:51–99 | Vertical geometry | Changes surface and relative object positions | Preserve, distinguish source and effective ground | Raw/effective H, surface indices, D0 |
| Ground/surface rounding | Internal round-to-nearest + one surface layer | I Numba float32 DEM; `g=int(D_eff+0.5)+1` | Z:56; V:65–95 | Vertical geometry | Surface upper edge is D0+g, not D0+D_eff | Preserve | Explicit index-edge and source-H comparison |
| Canopy H / Crown Ratio | No CR parameter in this direct-solar API | U existing Meta CHMv2 estimate; CR=0.60; top=DEM+CHM, bottom=DEM+(1-CR)CHM | E:89–99,230–232; existing Envelope manifest | Canopy geometry | Crown depth/path length; not optical k/LAD | Retain prepared envelope | Provenance/CR identity; independent geometry evidence still needed |
| `trunk_height_ratio` | `None` resolves to 11.76/19.98 | D constructor default but inactive where explicit bottom grid supplied | Z:126–145,186,195; S:47–140 | Canopy geometry | Fallback crown bottom only | Do not replace CR with this unrelated default | Confirm explicit bottom argument in allocator |
| Canopy sampling / presence | Caller supplies tree grid | U nearest actual-centre samples; state=1 AND finite/unmasked AND top>bottom | S:30–44; E:181 | Input validity | State=1 alone can have zero height | Preserve fail-closed coverage and positive-height rules | State/NoData/zero-height tests |
| TREE placement / priority | Rounded intervals; explicit bottom optional; Building overwrites TREE | U H minus effective ground; float32 rounding on Numba path; thin positive interval may extend down one cell; below-ground excluded; BUILDING first | Z:60–86; S:47–140 | Voxel geometry | Occupancy and shadow path lengths | Preserve, no clipping or H correction | Scalar intervals, exclusions, no TREE/non-air overlap |
| Shared vertical capacity | Allocator derives height from supplied grids | U max(base Z, required TREE end, required observer capacity), D0 unchanged | Z:191; S:47–146 | Domain | Prevents missing TREE/observers | Preserve guard and upper-air policy | Prefix occupancy, allocator-capacity and shared-shape QA |
| Numba / dtype / RAM limit | Numba when available; int8; max_voxel_ram_mb=None | D Numba enabled in A/B; int8; no explicit RAM cap | Z:9–12,126–145,197–210; saved Voxel model | Execution | float32 geometry branch versus fallback; memory | Keep recorded backend/version | Record backend and compare scalar rounding |
| Analysis ROI / context | Caller-defined | X A/B 64×64 m; 32 m context, 128×128 horizontal cells | C:47–110; saved configs | Evaluation/domain | Sampling and missing exterior occluders | Keep existing rectangles, no sufficiency claim | ROI centres, Study Area/input coverage, halo diagnostics |
| Result QA threshold | No corresponding physical default | X 1e-9 W/m² for sign/effect tests | S:194–215 | QA | Reduction counts and success gate | Preserve, not a measured detection limit | Masked sign/range; existing positive-ROI-effect guard |
| Halo safety allowances | No API default | X source top +2 m rounding bound; +2 m reach margin | S:226–258 | QA | Conservative known-height bound only | Preserve diagnostics, not physical parameters | Compare isotropic and directional tests; exterior UNKNOWN |
| Plot/OBJ defaults | show_plot=False; magma, vmin=0, vmax=DNI; obj_export=False | X show_plot=False; D OBJ off; engine display defaults inactive | R:24,33–35,65–90 | Presentation | No numerical irradiance effect | Keep separate from QML display range | GIS styles use horizontal ceiling, not engine's inactive DNI vmax |

For optical units, T implements `exp(-tree_k*tree_lad*length)` with length in
metres. The code does not declare/validate physical units or species calibration:
the product must have reciprocal-length units for physical interpretation;
standard LAD interpretation is leaf area/volume. Numerical defaults alone do not
establish that the estimated CHMv2 crown volume has those physical properties.

Observer detail: K chooses the first bottom-up walkable AIR/TREE transition above
a permitted surface; it rejects water (7/8/9) and negative supporting classes with
roofs disabled. OUEM supplies uniform land-cover surface class 1, so this is not
a land-cover-aware water mask. With 1 m cells, saved ground transition g gives
ray index `g+1` and nominal centre H `D0+g+1.5` (T adds 0.5). This is 1.5 m above
the voxel surface upper edge, **not necessarily 1.5 m above original/effective
DEM**. Changing the physical observation definition is a later decision.

## 4. Current / No-Canopy conditions

| Item | Shared or different? | Evidence / interpretation |
|---|---|---|
| Sun, DNI, k/LAD, requested height, roofs, rotation | Identical explicit call parameters | S:164–178,188–189; saved `statistics.json` sun/optics/observer sections. |
| Domain, resolution, shared Z, D0, ground/surface, Building IDs/occupancy | Shared | S:155–158; No-Canopy must equal Current with TREE replaced by AIR over the complete shape. |
| Canopy | Only TREE occupancy removed in No-Canopy | Corresponding CanopyGrid metadata becomes zero when TREE absent; R reads voxel classes, not that metadata, for attenuation. |
| Observers / ROI | Common original non-building columns; same k; same ROI | S:153–176; finite output mask must equal the common mask in both cases; shared-Z tests also inspect observer transitions. |
| Difference | `No-Canopy − Current`, W/m² | S:193–200; nonnegative within QA tolerance; excluded observers stay NaN, valid complete shadow is numeric zero. |
| Building diagnostic | `Terrain-control − No-Canopy` | S:179–193; removes buildings but retains building-conditioned ground and common original observers; not a regenerated natural bare-earth scenario. |
| Shadow categories | 0 neither incremental effect, 1 building only, 2 additional canopy only, 3 both, 4 excluded building column | S:232–236; “both” means positive diagnostic reductions, not two separately proven complete shadows. |
| ROI vs exported data | Outputs include full context; ROI statistics apply `ROI & valid` | S:199–215; outside-ROI statistics separate. Export preserves NaNs, writes float NoData=NaN when present; integer zero is valid. |
| GIS arrangement | Shared original affine, EPSG:4326, TIFF[row,col]=NPY[nu-1-row,col] | S:379–393; SOUTH_UP u/v arrays are not EPSG:6677 north-up arrays. QGIS display warp/Identify is not an exact source-cell oracle. |

No unintended parameter difference was found in this code path or the inspected
saved condition records. That is a static/historical finding, not a new pairwise
execution. Existing saved numerical comparisons are owned by the Phase 3C record.

## 5. Proposed default-based baseline (next authorized experiment)

**No physical-default change is needed to k=0.6, LAD=1.0, requested height=1.5
or roofs=False: OUEM already explicitly passes these CPU defaults.** Keep them
explicit so a future library change cannot silently redefine the experiment.
Retain A/B inputs, CR=0.60 geometry, 1 m resolution, source-H rules, D0, shared-Z,
32 m context and masks. Do not substitute the constructor's fallback trunk ratio.

Use A `[-23320,-40760,-23256,-40696]` and B
`[-23384,-40760,-23320,-40696]` in EPSG:6677, with existing frozen config/input
bindings from Phase 3C. Their saved shared shapes are 128×128×27 and 128×128×26.
First comparison case should retain artificial azimuth 135°, elevation 35° and
DNI 800 W/m²; those are required external inputs, not VoxCity defaults or a
known meteorological event. With unchanged implementation/backend, compare
actual centres, masks, occupied indices, paired NPYs and GIS values against the
saved runs, distinguishing fresh evidence from historical reports.

This audit does not authorize that execution. A dated/weather-based case would
need an agreed timestamp/timezone, location, weather/DNI provenance and a choice
of supported API; it is a separate experiment, not a correction inferred here.
Lower-attenuation sensitivity cases or no-canopy/zero-extinction analytical
controls also need separate scope. The existing runner requires a positive ROI
canopy reduction; do not relax that gate to make a null-control scene “pass”.

## 6. Initial B1 diagnostic checklist

Priority **Must** precedes a physical-interpretation claim; **Should** is a
subsequent sensitivity/completeness check. These are proposed checks, not new
acceptance gates or results of this audit.

| Priority / item | Likely failure or ambiguity | Check / existing regression owner |
|---|---|---|
| Must — sun azimuth / shadow direction | North/east swap, grid-rotation sign or erroneous +180° | Observer-to-sun ray must be sunward; shadow opposite. [Cardinal/rotation tests](../../tests/test_canopy_shadow_poc.py#L58) cover signs; compare a mapped isolated occluder. O's generic from-direction wording must not override R's actual call. |
| Must — elevation / shadow length | Wrong units, origin height, or interpreting a sloping scene with a flat formula | Isolated flat wall: reach=(top−observer H)/tan(elevation), allow explicit voxel discretization. Then inspect real cross-sections; do not fit a Z correction. |
| Must — building geometry | Roof-max 2.5D proxy mistaken for complete LoD2 occlusion, ownership overlap | Check source top/footprint, owner cells, conditioned ground and scalar occupied intervals; [Voxel tests](../../tests/test_real_komae_voxel.py). Report representation limits. |
| Must — canopy shape | CR proxy, zero CHM/state=1, below-ground exclusion or thin-crown expansion misread as observation | Review sampled top/bottom, candidate/exclusion counts and sections; [sampling/priority tests](../../tests/test_real_komae_solar.py#L14), [rounding tests](../../tests/test_shared_vertical_domain.py#L59). Seek independent crown evidence later. |
| Must — canopy attenuation | k/LAD confused with CR; strong model reduction treated as measured canopy performance | Known length through homogeneous TREE: exp(-0.6×1.0×length), with exact-zero cutoff below 0.01 and opaque obstruction distinguished. Analytic attenuation/cutoff-specific oracle is a next test/experiment, not established by real-run success. |
| Should — voxel resolution | Sub-cell geometry/paths and nominal-vs-actual XY spacing bias | Start with fixed 1 m baseline. Inspect edge-cell rounding; a later resolution study needs its own scope and comparable observers. |
| Must — axes / raster / GIS | SOUTH_UP u/v, row reversal or QGIS virtual warp creates false mismatch | Check saved actual centres, inverse source affine and NPY correspondence; use [gis_display.lookup](../../src/ouem/gis_display.py), not provider width/Identify as original indices. |
| Must — observer / masks | DEM+1.5 mistaken for D0+g+1.5, observer shifts after shared-Z extension, roofs or water silently included | Inspect H and first walkable transitions in both scenarios; [shared-Z observer tests](../../tests/test_shared_vertical_domain.py#L102). Quantify source/effective/surface offsets before deciding on physical-height changes. |
| Must — pair / difference | Different observers/settings, subtraction reversed, valid zero converted to missing | Whole-array non-TREE equality, identical masks and k, no increased irradiance under added occluders; [pair tests](../../tests/test_real_komae_solar.py#L71). Check categories against both incremental diagnostics. |
| Must — ROI / context / NoData | Missing external shadows, treating NaN as zero, canopy-free target cell incorrectly expected to have zero canopy effect | Keep ROI/context separate, trace shadows along direction across candidate-free cells; validate masks and boundary patterns. Known-height/crop diagnostics do not prove exterior coverage. |

Phase 3C records already report known-height reach about 39.18/36.99 m plus a
2 m margin: the isotropic 32 m tests fail, conditional directional tests pass,
and exterior-occluder sufficiency remains UNVERIFIED. Preserve that distinction;
larger-domain convergence is a future authorized experiment, not implied here.

## 7. Unknowns, next work and validation of this audit

UNKNOWN: empirical k/LAD and season/species validity; independent crown bottom
and CHMv2 accuracy/age; surveyed vertical alignment; physical pedestrian-height
interpretation; occluders beyond input/domain coverage; correspondence to actual
date/weather; scientific error bounds. None is resolved by QGIS display, a
default value or technical A/B completion. No formal contract/status is changed.

Recommended order: (1) review this default/external/upstream split and observer
meaning; (2) authorize the unchanged A/B numerical baseline comparison if needed;
(3) add/run small independently specified direction, length, attenuation and
cutoff oracles; (4) agree separate observer-height, weather, optical-sensitivity
or context-convergence experiments only where evidence warrants them. Existing
sign/common-mask/rounding tests provide regression protection, not scientific
calibration. No general parameter framework is proposed.

Audit validation: read-only source/signature, metadata/RECORD and selected saved
binding checks; repository link/line-reference and diff checks. No pytest was
run: this is documentation-only and relevant tests execute synthetic VoxCity
calculations, outside this task's no-analysis scope. No Voxel/Solar run, Consumer
rerun, GIS rendering or scientific verification was performed. Only this audit
document is added; existing evidence and authoritative specifications remain intact.
