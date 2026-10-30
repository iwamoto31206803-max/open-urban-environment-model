# B2 Minimal Technical E2E Design v0.1

Status: **Proposal for review; no implementation or model execution.**
2026-10-30; baseline main `c73ef78853d0be242686923e0a9d35e225c0a774`
(PR #122 merged). Technical basis is the
[installed GVI API audit](OUEM_B2_VoxCity_GVI_API_Audit_v0.1.md), not a claim
that a GVI run has succeeded. Apply
[Development Principles](../OUEM_Development_Principles_v0.1.md) and
[AGENTS](../../AGENTS.md). [B1 is technically closed](../status/B1_TECHNICAL_MILESTONE_CLOSEOUT.md);
its [scientific backlog](OUEM_B1_Deferred_Validation_Backlog.md) remains deferred.

## 1. Target and decisions before implementation

Proposed first path:

```text
preserved completed Komae A/B B1 runs (Current shared-Z class array)
  → read-only evidence/hash/grid/observer checks
  → VoxCity public CPU get_view_index, explicit canopy-only settings
  → same-column 2D candidate index / valid mask / ROI
  → new NPY + geographic GeoTIFF + metadata
  → manual QGIS load/style and exact-source-cell spot checks
```

No new Voxel generation, data acquisition, source-H conversion, B1 Solar replay,
GPU backend, own ray tracer or generic scene/output framework is needed for this
bounded target. **Structural connection is supported by code/headers; actual GVI
runtime success and scientific metric compatibility are not yet verified.**

The [Concept v0.2](../OUEM_Concept_Architecture_v0.2.md) inherits
[v0.1 B2](../OUEM_Concept_Architecture_v0.1.md#7-b2-----green-view-assessment):
canopy-only visibility, horizontal 360°, explicit vertical sampling, not an
unqualified replacement for Japanese photograph-based green-view assessment.
The following choices must be reviewed rather than silently supplied by B1:

| Decision | Source fact / alternatives | Recommendation for a first technical case, subject to review |
|---|---|---|
| **B2-D01: metric meaning** | CPU target TREE scores first-chord `1−T`, not binary hit=1 or whole-crown extinction. GPU uses a different ordinary score. | First characterize the CPU API with small approved synthetic cases. If accepted for a technical PoC, name it **VoxCity CPU TREE-target view index (B2 candidate)**. Do not present it as a demonstrated implementation of literal binary canopy-ray fraction or validated primary GVI. If binary fraction is required, stop and investigate an existing suitable API/upstream clarification separately; do not fake it by changing k, remapping classes or writing a ray tracer. |
| **B2-D02: target / execution path** | `mode='green'` includes ground vegetation classes and overwrites targets; default fast path may silently fall back and differs at boundary handling. | Use mode=None, targets=(-2,), inclusion=True explicitly. Propose **fast_path=False** for a single auditable generic path; this is a declared deviation from the wrapper's execution default, not an already approved choice. Compare against fast=True in later synthetic characterization before claiming parity or optimizing. |
| **B2-D03: observation geometry** | Map height=1.5 follows the same voxel-surface/index rule as B1, approximately DEM+2–3 m here; no world-coordinate observer override. | For saved-geometry technical compatibility only, retain the map rule and label actual H/offsets. Do not call it DEM+1.5 m pedestrian accuracy. A different physical-height definition is a separate scientific decision (B1-V01/V02), not an implicit B2 adjustment. |
| **B2-D04: angular measure** | CPU grid defaults are 120×20, −30°…30°, equal per-ray weights; Fibonacci has a different angular measure; local u azimuth phase ignores scene rotation. | Explicitly propose the installed grid defaults for the first candidate, with local-frame phase and dimensionless weighting recorded. This is 360° horizontally, not full-sphere/camera/solid-angle equivalence. Confirm this interpretation before implementing or labeling the primary metric. |
| **B2-D05: boundary / technical claim** | Existing domains have 32 m context and finite shared Z; escaped inclusion rays score zero, without a per-ray unknown flag. | Permit only a clearly labeled **finite-saved-domain technical result**, with exterior sufficiency UNVERIFIED. Do not expand inputs/revoxelize without separate approval or transfer the Solar sun-direction bound to all view directions. |

These decisions do not amend the Concept or an accepted contract in this PR.
If their proposed profile is not accepted, the next task should be focused API
characterization/clarification, not production B2 implementation under ambiguous
metric semantics. Completing all deferred B1 science is not a prerequisite for
such a narrowly scoped technical investigation.

## 2. Existing A/B compatibility and evidence reader

Inspected saved paths are under
`data/work/shared-vertical-domain/phase3c-20261029-01/outputs/`:
`komae-a-3c-20261029-01` and `komae-b-3c-20261029-01`.
Read-only NPY header inspection confirms both `solar/current_voxels.npy` and
`solar/no_canopy_voxels.npy`: int8, A **128×128×27**, B **128×128×26**.
Recorded class/count metadata binds -3 Building, -2 TREE (Current), -1 ground,
0 AIR, 1 minimal Bareland. These match the CPU class semantics. No fresh GVI,
all-array corruption check or full data rehash occurred in this audit.

| Saved item / owner | Reuse supported by inspection | New check/limit for B2 |
|---|---|---|
| `run-config.json`, submitted config, receipt, reports; [gis_visualization.inspect_run](../../src/ouem/gis_visualization.py#L48) | Existing read-only configured B1 snapshot/receipt/2D/grid validation; [Watch](../../src/ouem/consumers/source_h_standard.py#L74) handles source identity/immutability | This inspector is deliberately B1/Solar-specific. Initially require completed B1 A/B runs; explicitly capture **3D classes, TREE mask, ground/observer arrays and all additional consumed files** against report outputs before loading. It is not already a generic Voxel-only/B2 validator, nor fresh Consumer acceptance. |
| Current/No-Canopy shared arrays | Existing TREE priority and non-TREE/base-prefix invariants can be checked without generation | Use saved Current directly, hash before/after. Optional No-Canopy control must share shape, D0, Building/Ground and origins; do not call `integrate_canopy` or `execute_model` to rebuild either. |
| `grid.json`, centres, ROI; [Voxel owner](../../src/ouem/real_komae_voxel.py#L232) | u/v/up SOUTH_UP, local u≈north/v≈east, nominal 1 m and saved geographic basis; source-H H remains separate from voxel rounding | A/B D0=19.586000443/20.120000839 m; true u azimuth≈−0.150208/−0.150620°. Inherit each saved grid, not one common A/B vertical reference or an EPSG:6677 north-up index grid. |
| `ground_indices`, `observer_index_k`, `observer_valid` | [PR #121](../experiments/real_komae_solar/B1_GEOMETRY_OBSERVER_PHASE2.md) checks first walkable transitions and B1 paired origins | Independently reconstruct the **GVI** surface search, check `0≤k<nz`, origin class, mask and actual H against the saved compatible rule before using the old mask. Do not impose DEM+1.5 m by arithmetic or change D0. Record origins in TREE as a distinct diagnostic; public CPU includes the starting voxel. |
| VoxCity dataclasses / [Solar scene-construction pattern](../../src/ouem/real_komae_solar.py#L149) | The map reads `voxcity.voxels.classes` and `meta.meshsize`; no engine-generation step is required to wrap saved classes | Construct a small scene using existing `VoxCity`, `VoxelGrid`, `GridMetadata` types; test any unused companion-field handling against the actual public API. Metadata does not replace Building/TREE occupancy. Do not call `solar_pair` just to obtain a scene: it computes Solar. |
| [Geometry diagnostics](../../src/ouem/b1_geometry_diagnostics.py) | Existing scalar/H/ground checks and read-only preservation patterns | Select only needed checks; do not run the complete diagnostic/plot pipeline as a hidden model-preparation requirement. Reuse does not validate physical geometry. |

A/B ROI bounds and 32 m context remain those in the saved configuration; no B2
ROI/context/resolution overrides are needed initially. Compute against the entire
saved domain, then use the ROI mask for statistics/display. CPU `get_view_index`
has no ROI computation mask; cropping to 64×64 before ray casting would discard
context and change the question. Approximate call-count work is N_valid×2,400
rays, not a measured runtime or a guarantee of acceptable performance.

## 3. Minimum proposed additions and settings

One owning module, **`src/ouem/b2_gvi.py`**, one focused test file,
**`tests/test_b2_gvi.py`**, one small experimental settings example,
**`config/experiments/komae_b2_gvi.json`**, and concise usage in the existing
experiment area are sufficient candidates. **None of these files is created by
this audit.** No new package/CLI framework or GIS dependency is required.

Proposed entry: `python -m ouem.b2_gvi --run-root PATH --settings PATH.json --output NEW_DIRECTORY`.
The B1 run path supplies immutable grid/data bindings; B2 settings supply only
the reviewed view profile. Strictly reject duplicate/unknown keys, nonfinite
numbers, non-positive/non-integer ray counts, invalid angles/targets and unsupported
options rather than inheriting the library's ignored-kwargs behavior.

The proposed profile fixes tree_k=0.5 and tree_lad=1.0 from **View** defaults,
height=1.5 and roofs=False with the declared surface semantics, explicit TREE-only
target/inclusion, grid 120×20 and elevation −30°…30°, plus the reviewed fast-path
choice. Do not inherit Solar's 0.6, azimuth/elevation/DNI, scalar success gate,
W/m² units or color ranges. CR=0.60 and source-H rules belong to the already
prepared geometry and are not new GVI optical settings. Grid sampling does not
need an independently configurable N_rays; reject/omit that inactive setting.

Keep Run ID/output selection minimal (e.g. a unique output-directory ID recorded
in the report), use exclusive output creation outside source runs, and save
the exact submitted B2 settings bytes plus SHA-256 inside each result. Later
editing the external settings file must not invalidate the earlier run's evidence.
Record base-run settings/receipt/report hashes instead of modifying the existing
B1 RunConfig schema or copying a mutable-path-only configuration pattern.

For the CPU API's unconditional plotting, select a noninteractive Matplotlib
backend **before** importing the View module and close only figures created by
the call. Passing `show_plot=False` does not suppress this function's plot.
Prove headless operation and cleanup in tests; do not patch the engine or conceal
plot/import failures as a successful numerical run.

## 4. Output, GIS and provenance

| Proposed new artifact | Meaning / required verification |
|---|---|
| `view_index.npy`, `view_index.tif` | Current candidate score, dimensionless 0–1, full `(nu,nv)` map. Field/legend must identify CPU TREE-target first-chord score until D01 is resolved; optional percent display must be explicit. No W/m² or Solar Difference field is implied. |
| `observer_valid.npy` / `.tif`, `roi_mask.npy` / `.tif` | Verified GVI origin validity and inherited evaluation membership; invalid points are NaN in the value raster, valid zero remains zero. Keep context cells distinct from evaluation statistics. |
| One run metadata/report JSON and frozen settings | Source run/receipt/report/output hashes, method ID, engine version/pin/source hashes, explicit resolved view settings, target codes, ray generation/weighting/local phase, runtime/backend, grid/affine/D0/origin indices/H convention, masks/ROI statistics, output identities, source immutability and boundary/scientific limitations. No new large manifest hierarchy. |
| Optional plan PNG / source-cell examples | Technical presentation/QA, with range/units/NoData clear; no field-accuracy assertion. |

Use the same **EPSG:4326 geographic affine at actual saved centres** as the source
Solar TIFFs. Its raster rows are reversed-u: `TIFF[row,col]=UV[nu−1−row,col]`;
derive from `origin + nu*u_step` with column v_step and row −u_step. Reuse the
validated affine returned by the B1 inspector or a small local write primitive,
with independent centre/value/mask roundtrip tests. Do not call Solar's whole
exporter (which expects other arrays and writes Solar-specific figures), reproject
the analytical raster or replace it with an EPSG:6677 regular affine.

First display can be **manual QGIS loading** of A/B value/mask/ROI TIFFs with a
dimensionless 0–1 scale, transparent NaN and a clearly named candidate metric;
use the existing isolated QGIS runtime/project CRS EPSG:6677. Existing
[`gis_display.apply_qml/lookup`](../../src/ouem/gis_display.py) mechanisms are
reusable for valid GVI styles/original TIFF inspection after testing. Ordinary
provider Identify remains a virtual-grid query.

**Do not directly reuse the B1 presentation writer/contract:**
[`gis_visualization`](../../src/ouem/gis_visualization.py) hardcodes seven Solar
layers, range source, units and even the QML legend W/m² suffix;
[`gis_project.inspect`](../../src/ouem/gis_project.py#L55) requires that specific
schema and exactly those layers. Minimal E2E needs no change to either contract.
Automatic GVI QML/QGZ support, reusable presentation adapters or vector/B2 tiers
can be considered later when an actual output need justifies them; do not build
a common Output Framework now. QGIS is never installed into the OUEM venv.

No-Canopy can first be a **synthetic control**: TREE-only targets with no TREE
should produce valid zeros. Optional real No-Canopy checks are a separately
declared diagnostic cost, not a requirement to copy B1 Current/No-Canopy/Difference
products. A zero-GVI scene is not automatically a technical failure; do not reuse
Solar's positive-canopy-reduction requirement or weaken that existing Solar rule.

## 5. Implementation sequence and technical checks (future authorized work)

| Order | Small work unit / tests | Evidence before progressing |
|---|---|---|
| 0 | Review D01–D05; authorize synthetic characterization or the agreed candidate implementation scope | Explicit metric name/formula, observer semantics, ray/weighting profile, execution-path and finite-domain label; no scientific assumption silently adopted. |
| 1 | Authored small, non-square/translated scenes through the **actual public CPU API**: no TREE, known first TREE chord, deeper crown, opaque Building in front, origin in TREE, surface/roof/invalid column, top/side escape, mask/capacity, generic versus fast corner cases | Preregister analytic expectations/tolerances before runs; distinguish API index from binary/angular-area expectations. Low-level point API may diagnose integer-index rays, but document its difference from automatic map observers. No independent production tracer. |
| 2 | Read-only A/B evidence reader and B2 settings/snapshot/output lifecycle; reuse helpers without restructuring existing owners | Tampered 3D/header/hash/config/receipt/grid rejected; missing arrays stop; reused/misplaced output rejected; exact settings recoverable after original editing/deletion; input bytes unchanged. |
| 3 | CPU candidate map and minimal NPY/GeoTIFF/report; no new Voxel or Solar execution | Shape and finite-mask checks against GVI observer oracle; actual k/H/capacity; 0–1/NaN/valid zero; deterministic profile; non-square affine/centres/row mapping and NoData roundtrip. Unexpected masks or scores must be investigated, not silently clamped/replaced. |
| 4 | Separately authorized A/B GVI runs on saved arrays, then manual GIS smoke | Reports bind exact sources/settings/API and outputs; both TIFFs load with correct units/range/NoData in QGIS; representative exact original-cell values/XY checked independently of provider Identify; original Run/QML/QGZ hashes unchanged. |

The initial Technical E2E is complete only when the agreed existing VoxCity API
actually runs, input immutability/provenance and array/GIS checks pass, and A/B
display is observed. If GUI is unavailable, record generated/API-checked outputs
separately and display **NOT_VERIFIED**, not a completed display claim. Run focused
tests and the full OUEM-venv pytest for implemented code; isolated GIS checks
remain separate from ordinary CI and scientific acceptance.

## 6. Deferred science and current verification limit

Carry forward B1-V01/V02 observer/D0 concerns; V03 resolution; V04/V05 CHM,
presence/CR/bottom; V06 2.5D geometry; V08 exterior coverage; V11 region transfer;
V12 resources. GVI angular weighting, first-chord metric meaning, optical/visual
interpretation, photographs/field reference, source dates and applicability are
B2-specific unresolved matters. B1's k/LAD radiation calibration is not a B2
visibility validation. No new precision criterion, field measurement, data
contract or Acceptance state is set here.

This design is source-based, not an implementation feasibility execution. The
current audit checked pin/metadata/RECORD, signatures/call paths, data headers,
existing contracts and Markdown references. It did not import/call the GVI API,
run tests/models, rehash the full A/B chain, initialize GPU/QGIS, add settings/code,
or modify saved evidence. The next user review determines implementation versus
additional characterization; neither begins automatically from this proposal.
