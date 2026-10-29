# GIS-ready Output & Visualization Design Audit v0.1

Status: **Design proposal**, 2026-10-29; inspected main
`d43fecac70d484f88825453daaf17c4fa6949cd1` (PR #111 merged).
No implementation, settings, model runs, contracts or Acceptance changes.
Apply [P3/P4/P5/P6](../OUEM_Development_Principles_v0.1.md): preserve numerical
evidence; make results and their owners discoverable; add only a presentation step.

## 1. Evidence and ownership

| Basis | What this audit establishes |
|---|---|
| [Voxel](../../src/ouem/real_komae_voxel.py): `execute_model`, `export_outputs`, `run` | Base-grid construction, output semantics and serialization from code. |
| [Solar](../../src/ouem/real_komae_solar.py): `sample_canopy`, `integrate_canopy`, `solar_pair`, `export`, `run` | Shared Z, paired results, masks, controls and export from code. |
| [RunConfig](../../src/ouem/e2e_config.py): `prepare`, `capture`, `seal_voxel`, `model_sha` | Frozen configuration and Voxel-to-Solar receipt; not a GIS styling API. |
| [PR #98 results](../experiments/real_komae_voxel/RESULTS.md), [PR #99 results](../experiments/real_komae_solar/RESULTS.md), [Phase 3C record](../experiments/real_komae_solar/README.md#phase-3c-shared-z-real-data-verification--2026-10-29-jst) | Historical execution evidence. A compatibility and B completion, including 40 delivered TIFF checks, were recorded; this audit does not rerun those validations. |

Read-only local spot check: Phase 3C A's `voxel/` and `solar/` files exist and
their reports list COMPLETED and the inventory below. Historical visualization
`data/work/real-komae-visual/inspection-20261028-01/` also retains `REPORT.md`,
`qgis_project.py`, `qgis-final-check.json` and `komae_pr99_spatial_inspection.qgz`.
That report records separate GIS Python, EPSG:6677 project display, 22 valid
layers, six themes and one layout. Its code has fixed local paths/extents; this
is a local PR #99 precedent, **not** a supported configurable-E2E QGZ generator.
No fresh hash verification, QGIS opening, rendering, pytest or model run was
performed here. Local files are ignored evidence, not supplied by a Git clone.

## 2. Current output inventory

Names below are stage-relative. `UV` means `(n_u,n_v)`; `UVZ` adds the vertical
class dimension. Dimensions come from actual grid metadata, not a fixed 128².
Every named array is saved as pickle-disabled `.npy`; listed TIFFs are single-band
UV deliveries. NPY is computational evidence, not a directly styled GIS layer.

| Producer / files | Role, meaning and units | Shape / QGIS use |
|---|---|---|
| Voxel: `voxels.npy` | Base model: 0 air, −1 subsurface, −3 Building, 1 common Bareland surface (not observed land cover). | UVZ; no direct 3D GIS delivery. |
| Voxel: `building_ids`, `building_heights` (`.npy`, `.tif`) | Identity/geometry diagnostics: last-wins owner ID (0 none), relative height in m. IDs do not identify each anonymous 3D class voxel or every overlapping contributor. | UV; TIFF directly usable. |
| Voxel: `terrain_H`, `effective_ground_H` (`.npy`, `.tif`); `effective_dem.npy`, `ground_indices.npy` | Sampled source H and conditioned absolute ground H in m; effective DEM is ground minus D0 (m); ground indices are integer surface-transition indices. | UV; first two TIFFs directly usable. |
| Voxel: `centre_lon.npy`, `centre_lat.npy`, `centre_x.npy`, `centre_y.npy`, `roi_mask` (`.npy`, `.tif`) | Coordinate evidence in degrees / EPSG:6677 m; ROI membership boolean. | UV; only ROI has TIFF. |
| Voxel: `whole_building_footprints.geojson`, `building_segments.json` | Full, uncut 2D footprints with source/OUEM/engine IDs and H/ground attributes; sparse `(i,j)` owner/contributor IDs and relative `[bottom,top]` segments in m. | GeoJSON lon/lat (local file declares CRS84), directly usable; JSON is reconstruction/QA evidence. Original 3D source geometry stays in Standard. |
| Solar: `current_voxels.npy`, `no_canopy_voxels.npy`, `tree_mask.npy` | Model pair and boolean TREE occupancy (class −2). No-Canopy removes only TREE; base prefix and D0 retained, shared upper air allowed. | UVZ, potentially taller than Voxel base; not direct GIS layers. |
| Solar: `canopy_top_H`, `canopy_bottom_H`, `envelope_state`, `canopy_candidate`, `canopy_missing`, `canopy_outside` (`.npy`, `.tif`) | Sampled absolute H (m), numeric source state, and boolean masks. Candidate = valid state 1 and finite top>bottom; not verified tree presence or final TREE occupancy. Below-ground exclusion/Building priority/rounding are separate QA. | UV; TIFF directly usable. Successful current preflight requires full valid coverage; missing/outside masks are then false. |
| Solar: `solar_current`, `solar_no_canopy`, `solar_difference` (`.npy`, `.tif`) | Primary B1 results, W/m²; difference = No-Canopy − Current, additional modeled attenuation due to canopy. | UV; TIFF directly usable, excluded observers NaN. |
| Solar: `solar_terrain_control`, `building_solar_reduction` (`.npy`, `.tif`) | Diagnostic control with Buildings removed but conditioned ground retained; control − No-Canopy, W/m². Not an independent physical bare-terrain scenario. | UV; TIFF directly usable, same excluded observers. |
| Solar: `shadow_categories`, `observer_valid`, `observer_index_k`, `roi_mask` (`.npy`, `.tif`) | Categorical obstruction relationship, common non-Building observer mask, integer `ground_indices+1`, ROI membership. Codes explained below. | UV; TIFF directly usable. Index values at excluded columns are not valid observations. |
| Solar: `cropped_current.npy`, `cropped_no_canopy.npy` | Boundary QA: separate API calculations after removing outside-ROI occluders; W/m². Not slices of full-domain solar results. | ROI bounding subarray, not full UV; no TIFF in the demonstrated buffered runs. |
| Both: `grid.json`, `report.json`, `RESULTS.md`; Solar: `statistics.json` | Grid/conditions/QA/provenance, status and output hashes, local summary; Solar statistics include ROI/outside-ROI and halo diagnostics. | JSON/Markdown, no direct spatial layer. |
| Voxel: `plan.png`, `section.png`; Solar: `solar_comparison.png`, `section.png` | Index-space quicklooks and nominal index-edge H sections. | PNG, no GIS georeferencing; not substitutes for TIFF. |
| Run root: `submitted-config.json`, `run-config.json`, `voxel-receipt.json` | Exact submitted bytes, runnable saved config (relocated root locator), completed Voxel report/config binding. | Evidence, not visualization settings. |

Per demonstrated run: **12 Voxel NPY + 5 TIFF; 20 Solar NPY + 15 TIFF**.
No QML, QGZ or new GeoPackage is produced by these runners. Existing Standard
GeoPackages remain inputs; their contracts are not presentation contracts.
Both exporters enumerate files into report `outputs` before writing `report.json`
and local `RESULTS.md`; those two are not self-covered by that list. Voxel's
receipt binds its report; Solar records that source report identity. A new
visualization must hash its source reports itself and preserve all old bytes.

## 3. Coordinates, validity and display hazards

The model starts with EPSG:6677 analysis bounds plus context; VoxCity constructs
the actual lon/lat grid. UV is SOUTH_UP, approximately north/east, nominal 1 m;
adjusted horizontal mesh and orientation are recorded. Cell centres are
`origin+(i+0.5)*u_step+(j+0.5)*v_step`. Projected centres come from an explicit
4326→6677 transform. Source DEM/Envelope sampling uses those centres.

TIFF maps `raster[row,col] = uv[n_u-1-row,col]`. Its EPSG:4326 affine has column
step `v`, row step `-u`, corner `origin+n_u*u`. Both off-axis terms must be
retained. This is an exact geographic affine, **not** a regular EPSG:6677
north-up raster or exactly one metre in angular units. Display in an EPSG:6677
QGIS project by coordinate transformation; never assign 6677 to these TIFFs,
transpose them, or align them with source north-up rasters by array index.
ROI is the saved cell-centre mask; its projected reference rectangle and the
actual engine domain are distinct. A domain outline must use actual engine
corners, not pretend that the projected context rectangle is the exact lattice.

Voxel TIFFs declare no NoData; all sampled ground is required finite, and ID 0,
height 0 and mask 0 are meaningful. Solar exports set NoData=NaN **only** for
floating arrays containing NaN; boolean masks become uint8 without NoData.
Building-excluded irradiance is NaN, not zero sun. Source NoData/state and final
observer validity have different meanings; do not hide every zero or mask cell.

`shadow_categories`: 0 neither incremental Building nor canopy reduction;
1 Building reduction only; 2 additional canopy reduction only; 3 both;
4 excluded Building observer. Threshold is the existing `1e-9 W/m²` check.
Code 0 does not prove full sun; terrain/control effects remain. Categories are
relationships to controls, not observed tree labels or a binary canopy shadow.
Absolute H declarations, conditioned ground, quantized observer indices and
physical surveyed heights must not be conflated; see the
[retained science/observer limits](../experiments/real_komae_solar/README.md#outputs-and-limits).

Main usability gaps: many QA layers without a result-first ordering; units and
categories mostly outside TIFF metadata; auto-stretch makes paired maps visually
incomparable; no reusable style/project handoff or saved ROI outline. PNG plots
are useful quicklooks but do not solve these GIS navigation issues.

## 4. Recommended presentation artifacts (proposal)

Keep the model run immutable. Write a separate, new ignored visualization
directory referencing its existing TIFF/GeoJSON and JSON evidence; no automatic
download, model rerun, resampling or copying all data into another container.
Proposed owner/entry (not implemented): `src/ouem/gis_visualization.py`,
`python -m ouem.gis_visualization --run-root PATH --output NEW_DIRECTORY`, with
`tests/test_gis_visualization.py`. Both stages are located through the saved run
binding, not supplied as an arbitrary pair of TIFF directories.

| Format | Role and decision |
|---|---|
| GeoTIFF | **Reuse unchanged.** Primary continuous results and mask/category layers already exist. No projected export is needed for QGIS viewing; any later warped derivative must be separately labeled and tested. |
| QML | First increment: reusable explicit band-1 styles, names/units/notes, masks and category labels; load styles manually from the visualization directory. No reliance on writing same-stem sidecars into frozen run directories. |
| JSON | One small presentation manifest: source run/report/config/grid identities, relative layer paths + hashes, roles/units/case/difference sign, mask meaning, exact style stops/ranges/interpolation/opacity, style version/hash and generator/runtime identity. Reference scientific conditions/QA in existing reports instead of duplicating their full schema. This is presentation provenance, not a new Standard or RunConfig field. |
| QGZ | Valuable second increment: one-click layer groups/themes for Current / No-Canopy / Difference and QA, common extent/scale, EPSG:6677 project, ROI/actual-domain outlines and relative sources. Reopen validation required. QGZ preserves project settings, not a portable embedded copy of all input rasters. |
| GeoPackage | **Defer evaluation-point export until a real need (e.g. B2).** Existing footprints are already readable GeoJSON; do not convert every raster cell to a polygon/point. Optional project outlines can be a tiny separate GeoJSON, not a reason for a new vector framework. |

Suggested styles (display decisions, not changes to numerical results): Current
and No-Canopy share a fixed sequential dark-to-light ramp, band 1, 0 to the
recorded `sun.flat_horizontal_W_m2` (currently about 458.86 W/m²). Use explicit
five stops at 0/25/50/75/100% of that bound, linear color interpolation, no
per-layer min/max or quantile stretch. Difference uses the same magnitude range
and five-stop white-to-purple ramp, labeled “No-Canopy − Current (W/m²)”. Store
exact numeric stops/RGBA and limits in JSON and QML; rounded legends must not
replace the numeric upper bound. NoData transparent; show excluded observers
with a separate gray `observer_valid=0` overlay/legend. Valid zero remains visible
and distinct from exclusion. Unexpected out-of-range values are flagged, not
silently normalized away (retain the model tolerance).

Use exact palettes for category codes 0–4 (neutral/blue/green/purple/gray), no
continuous interpolation; candidate 1 translucent green, 0 transparent, labeled
“estimated positive-depth candidate”. Treat missing/outside separately. Use
nearest-neighbour raster display to inspect cells, with smoothing disabled for
categories/masks; this is independent of color interpolation. Present ROI and
context distinctly; keep outside-ROI values visible as context, not ROI statistics.

QML alone preserves layer presentation but not source grouping, shared map
extent, ROI overlays or comparison themes. QGZ offers those usability gains at
the cost of GIS-runtime, path and version testing. Official QGIS documentation
describes [portable layer styles](https://docs.qgis.org/3.40/en/docs/user_manual/introduction/general_tools.html#storing-styles-in-a-file-or-a-database),
[project contents/path failures](https://docs.qgis.org/3.40/en/docs/user_manual/introduction/project_files.html)
and [raster rendering modes](https://docs.qgis.org/3.40/en/docs/pyqgis_developer_cookbook/raster.html#renderer).
These are versioned API/design references, not proof of compatibility with the
local QGIS 4.2.3 recorded above; validate that installed version separately.

## 5. Minimal implementation candidates and priority

Priorities below concern the next visualization increment, not defects blocking
v0.2. [Final refactoring audit](OUEM_E2E_Reuse_Audit_v0.1.md#final-refactoring-audit--v02-completion)
still applies; do not bundle the deferred cleanup into visualization work.

| Priority / owner | Smallest change and benefit | Evidence/test impact and risk |
|---|---|---|
| **Must**: new presentation entry point, existing export/readback and config owners remain unchanged | One discoverable, read-only run→new visualization-directory operation; validate completed bound Voxel/Solar pair, saved config/receipt, grid/masks and hashes of consumed files; reject missing/mismatched inputs, unsafe output overlap or overwrite. Record reports/selected layers/styles in the presentation manifest. Keeps failures attributable to presentation rather than model QA. | New focused presentation tests; moderate provenance/path risk. It checks saved evidence, does not rerun Consumer/claim fresh model acceptance. Require only data actually consumed; original Raw/Converter need not be available merely to view saved results. |
| **Must**: same presentation owner + existing Solar usage guide | Generate QML + manifest for primary three maps, categories, observer/candidate/ROI masks. One small `src/ouem/` module with `python -m` entry is sufficient; no additional CMD or framework. Read constants from saved report; keep existing exporters untouched. | Highest initial user value for low scope; QML compatibility/NoData risk. Static style tests plus separate existing-QGIS load/render confirmation; input hashes unchanged. Add usage/README link only when implemented. |
| **Should**: same entry point, later optional GIS child | Generate QGZ, relative paths, groups/themes and tiny ROI/domain outline; share the already-defined styles. Avoid print-layout/imagery automation initially. | Moderate integration/version/path risk; reopen, relocation and layer/theme tests in actual GIS runtime. No influence on analysis tests or inputs. |
| **Defer**: Voxel/Solar exporters | Unify duplicate affine/export helpers, add unit tags, projected derivatives, general result catalog, point GPKG/B2 styles or voxel 3D GIS conversion only on demonstrated need. | Would touch implementation watch hashes or introduce geometry/mask risk; not needed to style present TIFFs. Preserve independent QA. |
| **No change**: RunConfig, model/Consumer/Standard/Adapter and historical exporters | Keep scientific settings, actual cells, D0/observer rules, shared Z, masks, numerical arrays and legacy paths. | Existing formal boundaries and historical source hashes stay valid; no source evidence rewrites. |

Existing [canopy GIS export](../../src/ouem/komae_canopy_qgis_export.py) and
[repair GIS export](../../src/ouem/komae_repair_qgis_export.py) consume older
acceptance/repair evidence schemas; they are not current Solar style owners.
Reuse useful file-integrity/child-runtime patterns, not their legacy dependency
chains. Historical local QGIS code is a reference for palettes/themes/reopen
checks, not a new runtime dependency or script to execute unreviewed.

Maintain the [runtime boundary](../architecture.md): OUEM venv reads evidence
and can emit simple QML/XML + JSON without importing QGIS. Optional project
creation uses existing explicitly selected OSGeo4W/QGIS Python as an isolated
child with file/JSON input and separate errors, never imports OUEM or merges
environments. A single entry point may retain its narrow GIS-worker branch in
the same module if needed; do not add a generic worker protocol. Do not handcraft
QGZ XML to avoid using the supported project API. Missing GIS runtime must not
break analysis or be repaired automatically. No macros/plugins/network basemap
are required. Save supported QGIS version and distinguish portable checks from
Windows GIS checks; QML-only generation still requires a real QGIS load test.

## 6. B2 boundary and first-increment acceptance

[Concept B1/B2](../OUEM_Concept_Architecture_v0.2.md#7-phase-bv01からの継承)
defines intended evaluation, not an existing B2 output in these runners.
Common future information: run/provenance link, metric identity/unit, scenario,
spatial support/CRS, observation validity, analysis extent, display settings.
Share these plain metadata meanings now; defer schema hierarchies, output base
classes and evaluation algorithms. B1 irradiance ramps cannot be applied to
green-view values. B2 must decide and declare fraction versus percentage,
viewpoint/support/height and validity when implemented. A point GPKG would need
stable point IDs, explicit geometry CRS, metric and valid/null fields; a raster
needs its own cell transform/mask. Point-to-area interpolation is a new analytical
choice, not a visualization default. Do not export hypothetical B2 layers now.

**Recommend QML + one presentation JSON first; QGZ as a second small increment.**
The first increment is accepted when a user can find the entry point/usage,
load the three existing maps plus masks/categories, apply the supplied styles,
and compare with consistent units/ranges. It need not regenerate any model.

1. Synthetic asymmetric/non-square saved runs: verify source pair/config/receipt
   binding, fail on tampered TIFF/report/grid or missing files, no overwrite, and
   source-byte invariance. Do not weaken upstream Consumer or hash checks.
2. Check pixel-centre correspondence and reverse-u affine, preserved NaN/valid
   zero and category 0–4 handling; assert exact QML/JSON stops, units and sign.
   Existing [Voxel tests](../../tests/test_real_komae_voxel.py),
   [configuration/non-square tests](../../tests/test_e2e_config.py),
   [Solar tests](../../tests/test_real_komae_solar.py) and
   [shared-Z tests](../../tests/test_shared_vertical_domain.py) retain analysis
   responsibility; run relevant and full OUEM pytest when code is introduced.
3. Separate existing-QGIS check on saved A/B results (no new analysis): correct
   EPSG:6677 project display, Identify values against source cells, shared scale,
   excluded observer legend, ROI/context distinction and input hash invariance.
   Save version and preview; record missing runtime as unverified, not PASS.
4. For later QGZ: reopen all layers/styles/themes, verify relative paths after
   moving a copied test bundle with preserved topology; QGZ alone is insufficient.
   Ensure visible common extent, distinct ROI/domain outlines and optional QA.

Rendering confirms usability and spatial presentation only. Numerical/geometric
QA remains with producer tests and run evidence; independent scientific validity,
general boundary sufficiency, source-H eligibility and Formal Acceptance remain
unestablished. No style choice closes those questions.
