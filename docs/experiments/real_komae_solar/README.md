# Real Komae three-element direct-solar PoC

Bounded exploratory integration on the actual PR #98 grid.
[Executed results](RESULTS.md). No new Standard, eligibility, acceptance,
Phase 5 gate or generic model framework.

The [E2E architecture audit](../../planning/OUEM_E2E_Reuse_Audit_v0.1.md) records
the preceding static plan. Configurable reuse is implemented below; the legacy
invocation remains available with its historical input bindings.

Run in an ordinary Windows terminal using the repository OUEM venv:

```powershell
.venv\Scripts\python.exe -m ouem.real_komae_solar `
  --run-dir data/work/real-komae-solar/<new-run-id> `
  --base-run data/work/real-komae-voxel/run-20261028-04 `
  --envelope-run data/work/height-envelope/komae-exploratory-20261026-01 `
  --artifact-root C:/dev `
  --study-area config/study_areas/komae_09LD3451.yaml
```

Create the output parent first. Outputs require a new directory; no overwrite,
resume, download or reconstruction fallback. In this legacy invocation the exact
PR #98 report and existing Envelope manifest are SHA-pinned. Missing/mismatched inputs stop.
See [upstream reproduction](../real_komae_voxel/README.md) if prerequisites
need regeneration: a new upstream identity requires explicit review and a new
pin, not relabeling old artifacts as successful.

## Reuse and quality gates

### Configurable reuse

Use `python -m ouem.real_komae_solar --config PATH.json` with the exact JSON used
by the new Voxel stage. The [Voxel procedure](../real_komae_voxel/README.md#configurable-reuse-v02-phase-2)
defines its fields, path base, expected input hashes, new run directories and
locally produced report receipt. No code edit or new fixed report SHA is needed
for a different covered rectangle. Legacy CLI arguments retain the old pins;
config mode accepts only its own completed Voxel handoff, not an arbitrary base
directory with a past PASS. All input-chain/Consumer/engine checks remain required.

Grid dimensions, Envelope source dimensions, exact-affine TIFFs and sections now
derive from validated metadata/arrays. The engine grid is still uv_m/SOUTH_UP,
1 m nominal, with source EPSG:6677 and exact-affine EPSG:4326 GIS delivery. NaN
continues to identify excluded observers. Both cases use one shared Z extent
under the [Phase 3B policy](#shared-vertical-domain-phase-3b); D0 and all base
occupied indices stay unchanged. Occupied clipping remains an error.

The same fixed sun, DNI, CR, k/LAD, observer and ground rules apply. Successful
reports distinguish technical calculation and detected canopy effect. This change
does **not** admit empty Buildings/TREE or zero ROI effect as PoC success; existing
scene-eligibility assertions remain strict and need separate review to broaden.
Context sufficiency uses the configured buffer plus the existing directional
bound/crop diagnostics; the old 32 m comparison is retained as a labeled reference.
General exterior sufficiency remains UNVERIFIED. No new real-data Voxel/Solar run,
QGZ automation, physical-observer correction or formal acceptance is claimed.

### QML + manifest visualization

After both **configured** stages complete, use the ordinary OUEM venv to create
presentation files separately from immutable run evidence:

```powershell
New-Item -ItemType Directory -Force data/work/gis-visualization
.venv\Scripts\python.exe -m ouem.gis_visualization `
  --run-root data/work/configurable-e2e/komae-baseline-01 `
  --output data/work/gis-visualization/komae-baseline-01
```

Substitute your actual run root and a new output directory; create its parent
first. There is no overwrite/resume. Output must be outside the run. Required:
saved `run-config.json`, `submitted-config.json`, `voxel-receipt.json`, both
completed reports/grids, Solar statistics and Building reduction NPY,
seven layer NPY/TIFF pairs, and Voxel
centre lon/lat, ROI and Building ID arrays. These must remain at their recorded
run/artifact-root location. Original Raw, Converter and engine installation are
not needed just to view saved results. Missing/mismatched consumed files stop;
there is no reconstruction or fresh Consumer/model execution. This entry point
does not accept legacy PR #98/#99 run directories without configured handoff.

Output: seven `.qml` files (`solar_current`, `solar_no_canopy`,
`solar_difference`, `shadow_categories`, `observer_valid`, `canopy_candidate`,
`roi_mask`) and `manifest.json`. The manifest maps source keys to relative
paths/hashes and records meanings, units, scenarios, exact color stops, QML hashes,
grid references and generator/runtime identities. Keep the directory topology
with its referenced run. A partial failed export has no completed manifest;
retry in a new directory. Local hashes detect mismatches, not coordinated
rewriting or authenticated execution. Source report validation claims remain
historical; presentation validation is not new Acceptance.

In QGIS, add the referenced **original Solar GeoTIFFs**, then for each layer use
**Layer Properties → Symbology → Style → Load Style…** and select the matching
QML (from the separate output directory). Use project CRS EPSG:6677 for metric
display; keep TIFF CRS EPSG:4326 and its exact affine unchanged. QML styles do not
load data, set project extent or generate QGZ. Use a common extent/scale manually.
Show `observer_valid` above irradiance to mark excluded Building columns gray;
NaN remains transparent and valid zero opaque. ROI is a translucent cell fill,
not a vector boundary. Candidate green is estimated positive crown depth,
not final TREE occupancy or confirmed tree presence.

Current/No-Canopy share the recorded horizontal irradiance bound and dark-to-light
five-stop ramp; Difference is **No-Canopy − Current**, white-to-purple, W/m².
Categories 0–4 use exact colors; no interpolation between category codes.
Nearest-neighbour cell display and fixed stops prevent dynamic auto-stretch.
Colors are display choices, not scientific thresholds. This command never
rewrites, reprojects or resamples TIFFs. Existing
[raster/observer and boundary limits](#outputs-and-limits) still apply.

**QML/XML generation and synthetic validation are implemented; QGIS loading and
display are NOT_VERIFIED by this implementation's tests.** The manifest records
that state explicitly. Existing QGIS may be used separately for a load/Identify/
visual comparison check, recording version and evidence outside the frozen run.
No QGIS/OSGeo4W imports, installation or child process is needed by this command;
the [runtime separation](../../architecture.md) remains unchanged. See
[visualization source](../../../src/ouem/gis_visualization.py) and
[tests](../../../tests/test_gis_visualization.py) for ownership and checks.
Subsequent [QGIS verification](#phase-1-qgis-display-verification--2026-10-29-jst)
loaded the styles but found provider-grid/alpha issues; it is not full display acceptance.

### Retained validation

1. Verify the bound Voxel COMPLETED report (PR #98 in legacy mode), all recorded source/output hashes and engine
   PEP 610/RECORD provenance. Rerun Consumer and bind the same source identities.
   Recheck saved centres/CRS, ROI, source DEM samples, conditioned ground/D0,
   ground indices, Building segments and saved voxels using PR #98 helpers.
2. Verify Envelope input/output hashes, retained raw CHMv2 tile, acquisition,
   source statement snapshot and limited review. Reuse `validate_sources` for
   HAG/metre/DEM/vertical provenance. Require matching Terrain and CR=0.60.
3. Feed existing nearest `sample_raster` the saved engine x/y centres. Keep
   numerical state, NoData/missing, outside and candidate masks separate.
   This full-coverage PoC stops on any invalid/missing/outside sample rather
   than inferring absence. State 1 means valid computation only. Candidates
   require valid finite top>bottom: positive estimated crown depth, not confirmed
   trees. Source Envelope rasters are read only.
4. Subtract unchanged engine-conditioned absolute ground from crown H for the
   public API. Below-ground intervals are excluded/counted, never shifted or
   clamped. `Voxelizer.generate_combined` generates TREE before BUILDING
   priority. Its allocation can add Building+tree heights. Determine the shared
   vertical size from actual placement rules, retain the base as a prefix, and
   remove only unused allocator air above that size. Reject insufficient public
   allocation or any unexpected occupied voxel outside the shared domain.
   No custom voxel generator is presented as VoxCity.
5. Independently audit every TREE interval and thin-crown expansion. Require
   no TREE in original Building/ground/surface and Current with TREE replaced
   by air to equal the bound base plus upper air (PR #98 in legacy mode).
   Keep IDs, DEM, D0, origin, rotation and ROI.
6. Use actual public solar API with PR #96's artificial azimuth 135°, elevation
   35°, DNI 800 W/m², requested height 1.5 m, roofs excluded, tree k=0.6 and
   LAD=1.0. Both primary cases share observers and geometry; difference is
   No-Canopy−Current. Three additional diagnostic API calls remove Building
   while retaining conditioned ground, and crop each original lattice to ROI
   with identical Z/D0 to measure outside-ROI effects. No resampling occurs.

## Outputs and limits

Local ignored outputs: Current/No-Canopy classes; TREE/candidate/state/missing/
outside masks; sampled H; direct solar/difference and Building obstruction
control; common observer mask/indices; cropped boundary controls; ROI mask;
unchanged grid; statistics/report JSON; PNG plan/section and local results.
NPYs have exact pickle-disabled readback. NaN denotes excluded Building
observers, not zero irradiance. Full-domain 2D arrays also have exact-affine
EPSG:4326 GeoTIFFs, reversed-u rows and v columns, for QGIS. No false regular
EPSG:6677 affine or older projected-array index alignment is used.

CR=0.60 is an estimated constant crown ratio. Meta CHMv2 is modeled HAG, with
uncertain local ground/height, XY displacement, false canopy over structures
and observation-date alignment. Positive height/state do not establish tree
presence/absence. Uncalibrated homogeneous k/LAD and the API's <1% transmission
cutoff can produce exact zero. Strong modeled attenuation is not measured
urban exposure or canopy benefit. No diffuse/global/reflected radiation,
weather/time series, annual or heat assessment is implemented.

Actual nominal observer centre is D0_effective+g+1.5 m: common across cases,
not verified physical 1.5 m above source ground. TREE edge errors include the
surface layer and rounding, not an H transformation.

Halo review uses full source AOI maximum Building/Envelope H plus 2 m edge
allowance, the lowest ROI observer, sun elevation and actual sunward exit
distance. Directional sufficiency is conditional on known source heights;
unknown taller exterior objects/different suns remain unverified. Cropping
shows effects of outside-ROI objects, not expanded-domain convergence.
No QGIS/formal acceptance, survey accuracy or ecological validation is claimed.

## Shared vertical domain (Phase 3B)

Building-only generation is unchanged. Solar integration determines
`n_z = max(base_n_z, nonempty_TREE_end, max_nonbuilding_observer_index + 1)`.
TREE endpoints use the installed kernel's existing rules: `g=round(D_eff)+1`,
`lo/hi=int(kernel_precision(relative_H)+0.5)`, including thin-crown expansion,
then occupy `[g+lo,g+hi)`. Empty rounded intervals do not enlarge the domain.
The observer remains `g+int(1.5)=g+1`; any extra observer layer contains air,
not a moved surface or a new physical observation-height definition. No fixed
height margin, regional constant, D0 change or source-H correction is applied.

The public Voxelizer still creates all occupied classes. Its allocator uses
`ceil(max(building_height+D_eff+tree_height))+1`, which can both overallocate and,
at rounding ties, underallocate relative to actual placement endpoints. Reject
underallocation rather than padding already clipped TREE. Pad only unoccupied
upper air as needed; crop only verified unoccupied allocator air. Independently
check every TREE interval and require No-Canopy to equal the complete base plus
upper air, Current with TREE removed to equal No-Canopy, and no TREE in original
Building/Ground/Surface. Invalid inputs, absent TREE/effect, capacity failures
and unexpected occupied output remain fail-closed.

Solar `grid.json` records the shared shape and `vertical_domain` with the base
shape, unchanged D0, required TREE/observer endpoints and added layer count;
Voxel `grid.json` and its receipt remain untouched. The QA field
`no_canopy_equals_base_plus_upper_air` replaces the historical PR98-specific name.
XY centres/affine/ROI/IDs and all ground indices stay fixed. Both full and cropped
solar cases use the same shared Z and existing observer/optics/sun rules.

Compare new 3D outputs to history over `:base_n_z`, then verify that the new
No-Canopy tail is all air and Current's additional occupancy is TREE only.
Unexpanded synthetic scenes retain exact arrays, including 2D solar results;
expanded synthetic scenes preserve occupied prefixes and GIS/observer invariants.
No Phase 3B real-data A/B run has been performed; the dated verification below
retains its original success/failure. Replaying historical implementation watch
sets requires original source bytes, available at pre-change
[`ac9a6ae`](https://github.com/iwamoto31206803-max/open-urban-environment-model/tree/ac9a6ae9502955808d4a1621abead3beaa36d58a),
or retained local snapshots; do not rewrite old hashes. Scientific/Acceptance
and context-sufficiency limitations above are unchanged. A new real B run needs
separate authorization; the synthetic tests do not establish its success.

Windows OUEM venv verification: **90 related tests passed**; full pytest
**968 passed, 5 skipped, 293 warnings** (Windows symlink privileges;
Rasterio/Affine pending deprecation and existing stat/fstat diagnostic).
Fifteen fitting-scene synthetic arrays, including paired solar/observer maps,
matched the pre-change implementation exactly. Original PR #107 run files and
source bytes were preserved; ignored evidence/snapshots are under
`data/work/shared-vertical-domain/phase3b-20261029-01/`.

## Phase 3 real-data reuse verification — 2026-10-29 JST

Historical verification before Phase 3B; the following results are not a new run.

**A reproduced the historical result exactly; B completed Voxel but failed
Canopy integration on the retained Z-capacity check, before solar calculation.**
This establishes baseline reproducibility and configurable horizontal reuse,
but does not establish a completed adjacent-rectangle three-element E2E.
No implementation, model condition, input or historical RESULTS was changed.

Executed from merged PR #106 main
[`77f95f05`](https://github.com/iwamoto31206803-max/open-urban-environment-model/tree/77f95f05eb1a9b8e99f2d550abb7c987f2000e30),
ordinary Windows OUEM venv Python 3.11.9. VoxCity 1.7.0 / pinned commit above
passed PEP 610 and installed-source RECORD checks (136 sources). Both runs had
the same environment, prepared inputs, source-H/ground/TREE rules, 1 m nominal
resolution, CR/optics and fixed sun/observer conditions. Only analysis bounds
and Run ID differed between A/B configurations; context was 32 m.

| Item | A | B (64 m west) |
|---|---|---|
| Analysis bounds, EPSG:6677 | [-23320,-40760,-23256,-40696] | [-23384,-40760,-23320,-40696] |
| Context reference bounds | [-23352,-40792,-23224,-40664] | [-23416,-40792,-23288,-40664] |
| Voxel / Solar status | COMPLETED / COMPLETED | COMPLETED / FAILED at Canopy.Z |
| Stage elapsed seconds, Voxel / Solar | 46.07 / 44.71 | 44.99 / 40.95 to failure |
| Saved base shape / ROI cells | 128×128×27 / 4,096 | 128×128×18 / 4,096 |
| Selected Buildings / owner cells | 41 / 3,746 | 22 / 2,461 |
| Building / ground / surface voxels | 34,802 / 46,882 / 16,384 | 21,641 / 46,223 / 16,384 |
| Raw Terrain H range, m | 19.586–24.505 | 20.120–25.263 |
| Envelope candidate columns, domain | 11,741 | 11,547 |
| Saved TREE voxels | 95,735 | Not produced |
| ROI observers / reduction cells | 3,722 / 3,471 | Not calculated |
| ROI mean Current / No-Canopy / reduction, W/m² | 2.251779 / 427.916993 / 425.665214 | Not calculated |

Before model execution, fresh Consumer PASS and 178 watched identities were
checked, including source chains, Envelope/raw CHM/evidence, historical outputs
and current implementation snapshots. Both domains fit the unchanged Study Area;
all 16,384 actual cell centres per domain had valid Terrain and Envelope samples.
Full boundary footprints were retained: 4 selected in A and 2 in B extend beyond
the DEM bounds, as separately recorded diagnostics. DEM is required at actual
computation centres; no outside sample was filled or extrapolated. This retains
the original boundary policy, including the same 4 A footprints recorded in PR #98.
Historical implementation identities were checked against preserved original
bytes, without replacing hashes/locators in old reports.

A versus PR #98/#99: all **12 Voxel + 20 Solar NPY arrays** matched exactly in
shape, dtype and values (NaNs included). Grid metadata values, centre/ROI/ID/
ground/class/TREE/observer arrays agreed. All **5 Voxel + 15 Solar GeoTIFFs**
matched in values, CRS, affine, shape, dtype, NoData and masks. This is numeric
and spatial equality, not a claim of identical timestamps/report hashes or TIFF
container bytes. Independent post-B preflight and all recorded input/output
hashes passed; A's complete 68-file run inventory was unchanged after B.

B's fresh Consumer, ID/contributor, scalar voxel, roof/ground, actual-centre and
Envelope coverage checks passed. Its building-derived base upper edge is
H=38.120001 m (D0=20.120001 m, 18 layers). Existing scalar TREE placement rules
require up to index 26 / H=46.120001 m; source canopy top reaches 44.955002 m.
Read-only diagnosis found **5,804 overflow columns**, including 2,691 in ROI,
and 18,663 potential TREE voxels above the base. These are scalar diagnostics,
not saved API TREE results. The public API generation was stopped by
`Canopy.Z: occupied voxel exceeds fixed PR98 Z extent; no clipping`; no occupied
voxel was clipped, no Z correction/expansion or relaxed gate was attempted.
This is a scene-triggered implementation capacity failure, not a missing-input,
XY-grid, empty-scene or zero-solar-effect result. B has no Current/No-Canopy maps
or Solar/TREE statistics; its failed report and partial artifacts are retained.

GIS validation against every saved cell centre passed for A's 20 rasters and
B's 5 Voxel rasters: exact EPSG:4326 affine, reversed-u rows, v columns and
excluded-observer NaN masks. B Solar GIS was not generated. A retains the halo
diagnosis: isotropic 32 m bound insufficient (known-height reach 39.1801 m plus
2 m margin); conditional directional bound passes (45.8419 m minimum exit).
ROI-only cropping increases irradiance in 861 cells. Exterior sufficiency is
still UNVERIFIED; B's solar/halo calculation was not reached.

Local evidence is ignored under
`data/work/e2e-reuse-verification/phase3-20261029-01/`:

- `A.json`, `B.json`: submitted configurations based on the existing
  [input-binding example](../../../config/experiments/komae_e2e.json).
- `outputs/komae-a-20261029-01/` and `outputs/komae-b-20261029-01/`: exact
  submitted bytes, runnable `run-config.json`, Voxel receipt and stage reports;
  successful stages also retain arrays, GeoTIFFs and plan/section PNGs.
- `preflight-04.json`, `baseline-comparison.json`, `A-validation.json`,
  `a-preservation-before-b.json`, `verification.json` and logs: identities,
  comparisons, independent post-run checks and B Z diagnosis. Earlier preflight
  helper attempts are retained; their duplicate-watch-key, UTF-8 decoding and
  overly strict whole-footprint containment checks were corrected only in the
  ignored audit helper, before any model run.

`verification.json` SHA-256:
`1b4643a4749e305ce26201835a2ac0b7d01ae73f65ac2af74de3d335b1ba8e1c`.
The recorded CLI sequence was, for each label A then B:

```powershell
$work = 'data/work/e2e-reuse-verification/phase3-20261029-01'
# Set $label to A or B and $id to the corresponding run ID above.
.venv\Scripts\python.exe -m ouem.real_komae_voxel --config "$work/$label.json"
.venv\Scripts\python.exe -m ouem.real_komae_solar --config "$work/outputs/$id/run-config.json"
```

For repetition, preserve these directories and choose a new output parent/Run ID
with the same reviewed input bindings and bounds; do not rerun into them. Saved
settings, implementation snapshots and reports retain the actual identities.
Related configuration/Voxel/Solar synthetic regressions: **62 passed, 37 warnings**
(Rasterio/Affine pending deprecation). Full pytest was not repeated: tracked
changes are this execution record only, with no implementation change.

Next priority is a separately reviewed shared vertical-domain policy covering
both Building and Canopy while preserving D0, existing occupied voxels, source H
and paired-case invariants, followed by a newly authorized B run. No claim is
made that 26 layers alone resolves every condition or that B would then pass.
CHMv2 presence/height/age/CR/optics, physical observer height, survey datum accuracy
and expanded-domain convergence remain unvalidated. Acceptance, source-H
eligibility and Phase 5 gates remain unchanged.

## Phase 3C shared-Z real-data verification — 2026-10-29 JST

**A historical compatibility PASS; B technical E2E COMPLETED; scientific validity
and Formal Acceptance not established.** Executed merged PR #108 main
[`a2c2bd0`](https://github.com/iwamoto31206803-max/open-urban-environment-model/tree/a2c2bd0954a2afdda79dbc75a4661cae09f4809b).
No implementation or historical result was changed. PR #107's B failure above
remains a failure of that recorded run, rather than being relabeled successful.

Same PR #107 Building/Terrain/Envelope bindings and parameters: A bounds
`[-23320,-40760,-23256,-40696]`, B `[-23384,-40760,-23320,-40696]`, EPSG:6677;
32 m context, nominal 1 m resolution. Preflight checked 281 watched identities,
fresh Consumer PASS, fixed VoxCity 1.7.0 commit/136 source RECORD checks and the
ordinary Windows OUEM venv Python 3.11.9. All four stage environment records
agree. Both domains fit the Study Area and have 16,384 valid actual-centre DEM
and Envelope samples; boundary footprints follow the unchanged policy above.
Historical source identities use preserved original bytes, not rewritten hashes.

| Quantity | A | B |
|---|---:|---:|
| Voxel / Solar status | COMPLETED / COMPLETED | COMPLETED / COMPLETED |
| Base shape → shared shape | 128×128×27 → 128×128×27 | 128×128×18 → 128×128×26 |
| Added upper layers | 0 | 8 |
| Public allocator layers / required TREE end index | 35 / 27 | 35 / 26 |
| D0 H, m (unchanged from PR #107 base) | 19.586000 | 20.120001 |
| Selected Buildings / owner cells | 41 / 3,746 | 22 / 2,461 |
| TREE voxels / TREE above old base Z | 95,735 / 0 | 87,384 / 18,663 |
| Domain / ROI valid observers | 12,638 / 3,722 | 13,923 / 3,930 |
| ROI mean Current / No-Canopy, W/m² | 2.251779 / 427.916993 | 37.427839 / 412.624758 |
| ROI mean reduction, W/m² | 425.665214 | 375.196919 |
| ROI reduction cells / Building-shadow cells | 3,471 / 251 | 3,355 / 396 |
| Elapsed Voxel / Solar seconds | 46.08 / 44.93 | 45.03 / 44.55 |

A versus PR #107 A: **12 Voxel + 20 Solar NPY arrays** match exactly in shape,
dtype and values, including TREE, observers and all 2D/cropped/control solar
maps (NaNs included). There is no 2D irradiance difference or Z extension.
All **5 Voxel + 15 Solar GeoTIFFs** match values, CRS, affine, dimensions, dtype,
NoData and masks. Original grid fields agree; Solar metadata additionally
records `vertical_domain`. New reports/timestamps/hashes are distinct evidence.

B's Building-only **12 NPY arrays and 5 GeoTIFFs** match PR #107 B exactly.
No-Canopy's first 18 layers equal that base; its extra 8 layers are all air.
Current with TREE removed equals No-Canopy over the complete 26-layer domain;
additional occupancy is TREE only. Independent scalar interval checks match
every saved TREE voxel, including the 18,663 formerly out-of-base voxels.
Required TREE end is 26, within the actual allocator's 35 layers; only verified
unoccupied allocator air is removed. No TREE clipping or missing interval was
accepted. B retained 3 below-effective-ground exclusions and 40 thin-crown
expansions under the existing rules, without height correction.

Post-run verification reloaded saved configs, checked all recorded input/output
hashes and fresh Consumer, reconstructed base ground/ID/voxel rules, and checked
the first walkable transition in both cases against original ground indices.
Observer indices remain `g+1`, with identical finite masks and difference signs;
irradiance increase cells are zero in both runs. All **40 delivered GeoTIFFs**
match the authoritative cell centres and reversed-u/v mapping in EPSG:4326;
they are not regular EPSG:6677 north-up arrays. A's complete 68-file inventory
is unchanged after B; all 97 PR #107 run files remain hash-identical.

Context diagnostics remain limited: A/B known-height horizontal reach is
39.1801/36.9893 m plus the existing 2 m margin, so the isotropic 32 m test fails.
Conditional directional tests pass (minimum exits 45.8419/45.8416 m); ROI-only
cropping increases irradiance in 861/875 cells. Exterior shadow sufficiency is
**UNVERIFIED**, with no enlarged-domain run. B's different statistics reflect a
different scene under the same true sun/optics rules, not a requirement to match
A. Estimated CHMv2/CR/height/age, uncalibrated optics, physical observer height
and survey datum accuracy remain unvalidated. Formal status is unchanged.

Ignored evidence root:
`data/work/shared-vertical-domain/phase3c-20261029-01/`.
Submitted configs are `A.json`/`B.json`; run IDs are
`komae-a-3c-20261029-01` / `komae-b-3c-20261029-01` beneath `outputs/`.
Each run retains submitted bytes, runnable `run-config.json`, receipt, reports,
arrays, TIFFs and plan/section PNGs. `preflight.json`,
`A-historical-comparison.json`, `A-validation.json`, `A-inventory-before-B.json`,
`historical-inventory-before.json`, `verification.json`, logs and implementation
snapshots retain the bindings and independent checks. `verification.json` SHA-256:
`db0b833ee0fe889035ac92b6feb5987184fa7503c02db2475e0878686c26bac9`.

Recorded commands (A then B, with the matching `$label` and `$id` above):

```powershell
$work = 'data/work/shared-vertical-domain/phase3c-20261029-01'
.venv\Scripts\python.exe -m ouem.real_komae_voxel --config "$work/$label.json"
.venv\Scripts\python.exe -m ouem.real_komae_solar --config "$work/outputs/$id/run-config.json"
```

These directories are occupied evidence: repetition needs new reviewed Run IDs
and output paths, never overwrite. Related shared-Z/configuration/Voxel/Solar
synthetic regressions: **90 passed, 39 warnings** (Rasterio/Affine pending
deprecation). Full pytest was not repeated because this PR changes only this
verification record and main's implementation was unchanged. No acquisition,
Converter, Standard generation, parameter adjustment or additional model scene
was executed. This establishes technical compatibility/containment for A/B only.

## Phase 1 QGIS display verification — 2026-10-29 JST

**QML loading/settings PASS; exact source-cell Identify FAIL; basic GUI display
confirmed in the unlocked follow-up below.
Defer production QGZ generation pending the display issues below.** Verified
PR #113 on merged main `a5e2e3b98dc34f8bdc564c11a288496ddb07cdf9`.
Reused existing A/B QML/manifests under
`data/work/gis-visualization/phase1-20261029-02/{a,b}/`; no regeneration, model
execution, scientific changes or product-code fixes. Source model results remain
unchanged; these are presentation-path findings.

Environment: existing OSGeo4W **QGIS 4.2.3, GDAL 3.13.3, Qt 6.11.0,
GIS Python 3.12.15 / NumPy 2.5.4**. Executable:
`C:/Users/iwahi/AppData/Local/Programs/OSGeo4W/bin/python3.exe`, launched through
existing `bin/python-qgis.bat`. GIS child imports no OUEM; repository venv
Python 3.11.9 only orchestrated evidence/hash checks. No environment was installed
or merged. Child-local `GDAL_PAM_ENABLED=NO` prevented source-side metadata writes.

Both cases loaded all seven original QML files. Loaded renderer stops, numeric
bounds, labels and per-class alpha exactly matched their manifests. Current and
No-Canopy share 0–458.86114908083687 W/m²; Difference has the same range,
white-to-purple ramp and W/m² legend suffix. Original arrays satisfy
`Difference = No-Canopy − Current` exactly, with common NaN masks. API renders
show opaque valid zero and transparent irradiance NoData, with the separate gray
observer overlay. These checks concern presentation of returned values;
provider/source substitutions below prevent a universal cell-validity PASS.
Candidate and ROI alpha are 96/255 and 64/255. The category renderer retains all
five discrete entries; A/B data contain 0,1,2,4, so code 3 was checked
in the loaded palette/legend, not as an observed scene cell. EPSG:6677 temporary
projects reopened with seven valid EPSG:4326 layers each. All original TIFF
affines and full TIFF↔reversed-u NPY values remained exact.

### Display issues and proposed minimum follow-up (not applied)

1. **Provider grid differs from source grid.** For both 128×128 source rasters,
   QGIS exposes a 115-row × 141-column provider view. At all 16,384 saved original
   centres per layer, band-1 Identify gave the following mismatches (numeric
   differences or source-finite versus provider-missing). Thus ordinary QGIS
   Identify cannot be advertised as exact original-cell inspection. The observed
   view is consistent with a north-up virtual warp; GDAL documents that behavior
   for [automatic warped VRTs](https://gdal.org/en/stable/api/gdalwarp_cpp.html).
   This is display/provider sampling, not modified source H or Solar arrays.

   | Layer | A mismatches | B mismatches |
   |---|---:|---:|
   | solar_current | 215 | 317 |
   | solar_no_canopy | 115 | 47 |
   | solar_difference | 221 | 321 |
   | shadow_categories | 125 | 88 |
   | observer_valid | 73 | 30 |
   | canopy_candidate | 46 | 63 |
   | roi_mask | 0 | 0 |

   Keep source-cell validation against original affine/NPY/GDAL reads; document
   the distinction from QGIS provider/render cells. Decide how exact-cell
   inspection should be exposed before extending the user-facing claim. Do not
   relabel TIFF CRS, silently warp original evidence or change model geometry.

2. **QML clears provider alpha for integer layers.** QGIS adds an alpha band to
   its integer provider view (two bands versus one physical TIFF band). Before
   styling, renderer alpha is band 2; original QML sets it to −1. Categories and
   observer masks consequently render an opaque fringe outside valid provider
   coverage. Diagnostic-only in-memory restoration of the detected default alpha
   removed 22,162 A / 22,160 B pixels per affected 1600² render. Candidate/ROI
   previews did not change because their zero class is already transparent.
   Minimum candidate: preserve the detected valid provider alpha when applying
   styles in a GIS-aware loading step; do not globally hard-code band 2 for
   genuine single-band providers. Standalone-QML handling needs a compatibility
   test/explicit alpha-selection instruction. This does not fix issue 1.

No production QML/generator/analysis code was changed. Follow up with the narrow
alpha-handling change and a defined source-cell inspection policy, then recheck
both cases before treating QGZ delivery as ready. Neither finding establishes
scientific error or scientific validity of the modeled results.

Evidence (ignored): `data/work/gis-visualization/qgis-display-20261029-01/`.
`complete-api/api-verification.json` holds 229,376 Identify comparisons and render
samples; `alpha-diagnostic.json` separates the uninstalled diagnostic from the
original-QML renders. `complete-api/{a,b}/overview-labelled.png` are API-rendered
comparisons, **not GUI screenshots**; `inspection.qgz` files are temporary
verification projects, not a new export feature. QGIS GUI started, but Windows
was locked; UI input stopped and no usable GUI map screenshot was obtained.
At that point GUI legend interaction/Identify remained unverified; the unlocked
follow-up below records the subsequent GUI checks. No human acceptance is claimed.
All **152 protected files** (136 A/B run files + 16 QML/manifest files) remained
SHA-256 identical; no new source sidecars. `summary.json` SHA-256:
`c4de7e03ec96d5a747f8fdd717920c183ff25fc4663d38a6ef34fb4a08b12dfd`.

### Unlocked GUI follow-up — 2026-10-29 JST

After the user unlocked Windows, actual QGIS GUI display was checked using the
same temporary A/B projects and original loaded styles. Current, No-Canopy and
Difference were switched in both cases; Difference legends showed
0–458.861149 W/m². The A category legend retained five discrete entries, and B
candidate/ROI overlays were visibly translucent. Project status showed EPSG:6677.
Representative B GUI Identify returned **0** for a black valid cell and
**No data** for a gray Building-excluded cell. Nearest saved NPY cells at the
rounded GUI coordinates were respectively `[64,67]` = 0 and `[110,82]` = NaN.
This limited GUI spot check does not replace or overturn the full source-centre
API mismatch counts above, nor resolve the provider-alpha issue.

Twelve actual GUI screenshots and `verification.json` are saved under
`qgis-display-20261029-01/gui-unlocked/`, separate from the API previews. The
earlier locked-state evidence/summary is retained unchanged. All 152 protected
original files were rehashed and remain unchanged; temporary view toggles were
not saved over the inspection projects. No product fix or model run was made.
GUI verification JSON SHA-256:
`336b00bcea5d5b76f4b8132e396d479e9e940bb6cf1e8226e3aaf6281866e6e0`.
Basic GUI usability is now observed; exact-cell display acceptance and scientific
validation are not established. Production QGZ generation remains deferred.

### Raster provider investigation — 2026-10-29

**The change occurs during QGIS GDAL-provider initialization, before QML or
project reprojection.** Additional read-only tests on A/B Current (Float64/NaN)
and candidate (Byte/no NoData) reproduced the provider view with
`GDALAutoCreateWarpedVRT(source, None, None, GRA_NearestNeighbour, 0.2)`.
Both direct rasterio and direct GDAL retain 128×128, one band, EPSG:4326 and
the original rotated affine, with exact NPY correspondence. The in-memory GDAL
VRT has 115 rows × 141 columns and the same bounds as QGIS; its band-1 values
at **all 65,536 original centres** match QGIS Identify, including missing values.
This experimentally localizes the change to the provider's virtual north-up
sampling path; it does not establish a line-by-line audit of installed QGIS C++.

For A, original longitude/latitude pixel steps are approximately
`1.10408753e-5` / `-9.01369867e-6` degrees, with nonzero off-diagonal terms.
The VRT uses square angular pixels `1.00837351e-5` degrees and zero off-diagonal
terms. Suggested bounds/resolution therefore produce 141×115 rather than
128×128. Choosing project CRS EPSG:6677 cannot undo this earlier provider warp.
Nearest-neighbour on that new grid can select adjacent source cells; this is
not confined to the outer boundary or caused solely by NaN:

| Case/layer | Mismatch within outer two source rows/columns | Interior mismatch |
|---|---:|---:|
| A Current | 14 | 201 |
| B Current | 19 | 298 |
| A candidate | 21 | 25 |
| B candidate | 1 | 62 |

An exact reference method is now verified: use saved lon/lat centres, apply the
**inverse original GDAL geotransform**, take containing pixel `(floor(row),
floor(col))`, and read original band 1. Every centre maps to original raster
`[127-i,j]` and hence NPY `[i,j]` in these runs. For a projected query, first
transform EPSG:6677 XY to lon/lat with explicit axis order; reject points outside
the original inverse-transform bounds and retain NaN separately from zero.
Do not use provider width/height/extent to infer original indices. This can be a
small GIS-side inspection action referencing original files, without model changes.

| Option | Accuracy / usability | Scope, reproducibility and QGZ |
|---|---|---|
| A: change loading | No verified standard GDAL-provider switch preserving this rotated source grid was found; merely omitting QML does not help. | A custom provider would add disproportionate maintenance/version risk; defer. |
| B: explicit display derivative | Predictable documented display grid, but resampling cannot preserve every original cell/value. | Additional files, transform/resampling/mask hashes and tests; compatible with QGZ, unnecessary initially. Never overwrite originals. |
| C: separate display and exact inspection | Keep current visual layers; original-file lookup gives exact source values and indices. Users must see which grid a value refers to. | **Recommend first.** One narrow GIS-side lookup plus provenance links; QGZ can attach it later. No new analysis or universal output framework. |

Alpha investigation confirms one physical Byte band versus two provider bands;
before/after QML alpha remains 2→−1. Float64/NaN remains one band and −1→−1.
The previous in-memory alpha restoration proves the fringe fix independently
of source-cell mismatch. Proposed GIS loading sequence: capture the provider's
valid default alpha band (verify its alpha interpretation), load QML, then restore
that band if appropriate. For a genuine single-band/no-alpha provider retain −1.
Do not hard-code 2 or mark numeric class 0 NoData. This is verified only with
QGIS 4.2.3/GDAL 3.13.3; other releases require their own smoke test.

Recommended next scope: GIS-side style application and exact-source inspection;
keep `gis_visualization.py`'s numerical outputs/manifest identities intact unless
a narrowly reviewed metadata reference is needed. Leave RunConfig, Voxel/Solar,
Standard/Adapter and original QML unchanged in this investigation. Tests should
cover rotated/non-square grids, translated bounds, source versus provider
indices, NaN/zero, outside points, and provider alpha present/absent. A/B acceptance:
all original-centre exact lookups equal original NPY, loaded styles retain intended
alpha without fringe, and source hashes remain unchanged. QGZ can proceed after
these checks plus actual GUI lookup/legend checks, with provider Identify clearly
labeled as display-grid sampling rather than original-cell truth.

Ignored evidence: `data/work/gis-visualization/provider-investigation.py`,
`investigation.json` (GIS child), `investigation-direct.json` (OUEM rasterio
cross-check). No derivative was written: the diagnostic VRT existed in memory.
All 152 protected files remain unchanged. No product code, dependencies, model
runs or environments changed; documentation checks replace pytest for this PR.
