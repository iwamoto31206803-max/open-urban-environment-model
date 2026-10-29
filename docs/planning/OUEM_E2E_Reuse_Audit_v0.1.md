# Existing E2E architecture audit — OUEM v0.2 Phase 1

Status: **static audit and implementation proposal**, 2026-10-28; baseline main
`76689c049b71226aed952c66da27db69c1fdeef0` (PR #104 merged).
Apply the [Development Principles](../OUEM_Development_Principles_v0.1.md).
No refactoring, model run, new dependency, environment repair or acceptance decision.

> The Phase 1 proposal below is historical. See the
> [Final Refactoring Audit](#final-refactoring-audit--v02-completion) for the
> post-PR #109 implementation and completion recommendation.

## Recommendation and first reuse target

First move the evaluation rectangle to an adjacent area **within the same existing
Building/Terrain/Envelope coverage**, keeping EPSG:6677, 1 m voxels, source-H
profile, optical/observer assumptions and engine pin. Reuse the prepared Standard
and Envelope; do not rerun acquisition/Converter merely to move the ROI.
Add a small experimental run configuration and remove scene-size assumptions from
the Building/Terrain and solar stages. A general source framework, new regional
copies and a mandatory all-stage orchestrator are unnecessary for this target.

## Actual execution path and boundaries

```mermaid
flowchart LR
  G[CityGML ZIP + fixed Converter] --> H[source-H Native / Standard / Consumer]
  T[Raw DEM + Native manifest] --> S[Standard Terrain]
  C[CHMv2 acquisition + evidence] --> E[Height Envelope]
  S --> E
  H --> V[Actual VoxCity Building + Terrain grid]
  S --> V
  V --> P[Canopy at saved centres / TREE integration]
  E --> P
  P --> B[Current / No-Canopy direct solar + controls]
  B --> O[NPY / GeoTIFF / PNG / reports]
  O --> Q[Separate local QGIS visualization]
```

This is a manually sequenced pipeline, not one existing CLI. All model stages use
the OUEM venv; GIS child Python is separate. Each stage below already accepts
explicit input/output paths and requires provenance or new output locations.

| Stage / actual entry | Inputs → outputs; implemented boundary |
|---|---|
| [Terrain acquisition](../../src/ouem/acquire/tokyo_tama_dem.py), then `ouem-accept-terrain` / `ouem-standardize-terrain` | Fixed Tama tile → Raw / Native manifest → unchanged-grid Standard TIFF + manifest; [procedure](../Terrain_Acquisition_PoC_v0.1.md). Existing Standard reused in this PoC. |
| [Building](../../src/ouem/real_komae_source_h.py), `python -m ouem.real_komae_source_h` | `--zip --converter --terrain --study-area --artifact-root --run-dir`; two LoD2 members + fixed binary → Native/Standard GPKG, receipts, Consumer and Terrain diagnostics; [procedure/results](../experiments/real_komae_source_h/README.md). |
| [CHMv2](../../src/ouem/acquire/meta_chmv2.py), `python -m ouem.acquire.meta_chmv2` | `--study-area --raw-dir --work-dir`, optional local index/tiles → EPSG:3857 crop + acquisition record. This record alone is not the HAG/DEM evidence bridge. |
| [Envelope](../../src/ouem/height_envelope.py), `python -m ouem.height_envelope` | CHM/acquisition/source-evidence + Terrain/manifest/acceptance + study area → absolute top/bottom, validity state, manifest; `--cr --resolution --dem-sampling` already exist. [Contract](../CHM_Height_Envelope_PoC_v0.1.md). |
| [Voxels](../../src/ouem/real_komae_voxel.py), `python -m ouem.real_komae_voxel` | `--building-manifest --terrain --study-area --artifact-root --run-dir`; fresh Consumer, actual engine rasterization/ground/voxelization → centres/grid/ROI, IDs/segments, raw/effective ground/D0, voxels, GIS diagnostics/report. [Procedure/results](../experiments/real_komae_voxel/README.md). |
| [Solar](../../src/ouem/real_komae_solar.py), `python -m ouem.real_komae_solar` | `--base-run --envelope-run --study-area --artifact-root --run-dir`; fresh validation, public Voxelizer and solar API → paired voxels, masks, direct maps, categories, statistics, controls and GIS output. [Procedure/results](../experiments/real_komae_solar/README.md). |
| GIS delivery | `export_outputs` / `export` above write exact-affine EPSG:4326 GeoTIFFs, GeoJSON/PNG. Later QGZ/aerial comparisons came from ignored `data/work/real-komae-visual/inspection-20261028-01/` scripts and saved project, **not a tracked reusable CLI**. Old `komae_canopy_qgis_export` consumes a different legacy integration schema and is not a drop-in substitute. |

Local PR97/98/99 report JSONs were inspected: each records COMPLETED; source-H
eligibility/acceptance remain unestablished/unverified. No input hashes were
revalidated and no historical success was reproduced by this audit. The owning
RESULTS retain full measurements and execution evidence; they are not duplicated here.

The accepted v0.1 lane remains separate: Converter GPKG/4979 Native → Standard →
[versioned Adapter](../OUEM_VoxCity_Adapter_v0.1.md) / A3. The experimental
source-H candidate manifests are not added to its whitelist. Envelope is not full
Standard Canopy; fixed direct solar is exploratory B1, not scientifically validated
exposure or annual assessment. Standards, Acceptance and Phase 5 gates stay unchanged.

## Extents: input coverage, analysis and actual computation

The [study-area YAML](../../config/study_areas/komae_09LD3451.yaml) describes the
400×300 m preparation/selection area, not the current solar ROI. `ROI` and `DOMAIN`
are separate globals in [canopy_shadow_poc.py](../../src/ouem/canopy_shadow_poc.py)
(lines 27–28): 64×64 m evaluation and a 128×128 m projected reference with 32 m
margin. The real voxel runner imports these constants only, not that older model.
VoxCity defines the actual geographic lattice from transformed rectangle corners;
saved centres, affine u/v vectors, orientation and ROI mask are authoritative.
The projected rectangle and engine parallelogram are not identical geometries.

**Proposed minimum:** analysis bounds + context buffer (default 32 m) derive a
projected computation reference; save the actual engine domain separately as
output metadata. Context is the surrounding occluder region within that domain,
not a third independent configurable rectangle. Keep input coverage/preparation
extent separate and require it to cover all needed samples/objects. Do not change
canonical study-area selection simply to move analysis bounds; full buildings
must remain uncut and the all-Standard ID mapping must stay traceable.

If asymmetric/manual context later proves necessary, an explicit domain override
is an alternative, not part of the first target. Domain coverage does not prove
shadow sufficiency: the existing known-height directional bound and ROI-crop
controls are not expanded-domain convergence. Retain UNVERIFIED when exterior
coverage is unknown. Rotated/nonrectangular ROI masks are outside the first target
because `solar_pair` currently requires a rectangular centre-index crop.

## Configuration candidates and retained constraints

| Priority / code evidence | Minimum change or deliberate retention |
|---|---|
| **P0: analysis/domain** — `real_komae_voxel.prepare_buildings/execute_model/run`, ROI/DOMAIN imports and ROI-module watch | Pass a validated experiment extent specification throughout selection/QA/grid creation. Validate finite ordered bounds, ROI containment and input coverage; include config bytes/hash in provenance. Do not extend or silently repurpose the accepted `StudyArea` contract. |
| **P0: run binding** — solar `BASE_REPORT_SHA`, `ENVELOPE_SHA`, `preflight` | Accept explicit expected report/Envelope hashes in reviewed run config; retain schema, status, all dependency hashes, fresh Consumer, source semantics and engine checks. Path-only or `allow-unpinned` bypass is not equivalent. Baseline config must bind the existing identities exactly. |
| **P0: grid shape** — solar `[128,128,27]`, `np.indices((128,128))`, segments allocation, Envelope `(300,400)`, export `origin+128*u`, fixed TIFF/section dimensions | Derive dimensions/affine/section extent from validated grid/arrays and Envelope metadata. Preserve 1 m and fixed base-grid Z within each pair; if trees exceed occupied Z capacity, fail as now. Automatic vertical expansion needs a separate decision. |
| **P0: identity and paths** — existing CLI path arguments / `Watch` confinement | Reuse arguments; config references existing study-area and manifests, input roots, output parents and run IDs. No auto-discovery/download/overwrite. Paths under the artifact root and absolute paths inside old evidence need consistent resolution. |
| **P0: scene eligibility** — voxel requires selected/owned Buildings; solar requires TREE, ROI reduction and nonempty statistics masks | A different rectangle may legitimately have no canopy effect or no Buildings, yet current PoC completion fails. Decide whether the first reuse target must satisfy these scene prerequisites or should report a valid zero-effect case; do not silently weaken the baseline assertions. Keep strict NoData/coverage rejection. |
| **P1: solar conditions** — `AZIMUTH/ELEVATION/DNI`, repeated calls in `solar_pair`, plot scales | One condition object can feed all five calls, metadata, halo check and plots. First adjacent run keeps the baseline conditions. Expose only validated ranges; changing sun changes context requirements, not just an image title. |
| **Retain first:** EPSG:6677/4326, 1 m, .3 contributor threshold, rounding/ground rules, 2 m roof budget, 3 m exploratory bottom flag | These span adapter/engine semantics or validated scope, not incidental region strings. Do not turn them into arbitrary knobs. Other CRS/resolution is future work requiring broader tests/contracts review. |
| **Retain first:** CR=.60, k=.6, LAD=1, requested observer 1.5 m / no roofs; source-H 6697/6668/6695 | Scientific/model assumptions must be declared and held fixed for behavior comparison. Configuration exposure is not approval of alternative assumptions or physical DEM+1.5 m observations. |
| **P2 only:** Building `MEMBERS`, Converter SHA/options; Tama URL/tile/hash; different CHM release | Existing two members and coverage may suffice for an adjacent rectangle. New tile/release/binary support is conditional on coverage failure, not needed preemptively. Do not parameterize mandatory identity checks into optional validation. |
| **P1 GIS:** local visualization run paths, fixed display bounds/ROI frames, 128 indexing, fixed sun labels/QGIS layout | If reusable PNG/QGZ is in the next completion criteria, promote only the needed read-only export path and derive scene values from grid/statistics. GeoTIFF delivery already exists; aerial download and general styling framework are unnecessary. |

A small JSON run config (stdlib, no new parser dependency), referencing the
existing study-area YAML, is the recommended option. Its loader must reject
duplicate/unknown keys and nonfinite bounds; the existing small YAML loader is
not a general strict experiment-config validator. CLI overrides alone are a
viable smaller alternative if few fields suffice; mixing independent defaults
across stages is the risk. Record resolved settings once and require both stages
to agree. Exact filename/schema and whether QGZ automation is required need review.

## Complexity and smallest work sequence

1. **P0 baseline and config boundary:** preserve an immutable baseline checkout/input
   locator chain before editing watched source files; add strict extent/input-binding
   validation and a baseline config without changing algorithms. Existing reports
   watch implementation files as inputs: editing those files at their recorded paths
   can invalidate old report verification. Do not “fix” old reports/hashes. Use intact
   historical locators or explicitly reviewed new runs for comparison.
2. **P0 voxel + solar connection:** thread config through existing functions/CLIs,
   remove fixed dimensions, generalize GIS affine/plot bounds. Reuse one validated
   actual-grid description. Keep old default/explicit baseline invocation available
   with its fail-closed identity checks; new run identities are separately recorded.
3. **P0 validation, then authorized adjacent E2E:** compare baseline and translated
   case as below; update existing stage READMEs for config use. No new Komae clone.
4. **P1 only if required:** small read-only visualization entry using saved outputs;
   QGIS stays a separate existing GIS child. Lightweight stage coordination can
   follow proven repetition, not precede extent reuse.

The main coupling is runners serving as utility libraries: voxel/solar import
`write/digest/distribution` from the Building runner, provenance from broad
`komae_integration`, and voxel constants from canopy-only code. Isolate extent
ownership now; extract other utilities only if it simplifies these changes.
Repeated array/affine writes merit a small helper if both consumers need it.
Independent Consumer, scalar voxel/segment checks and provenance validation are
intentional cross-checks, not duplicate logic to delete. Legacy CMD cleanup is
not on the critical path; no new wrapper/plugin framework is proposed.

## Regression, new-area verification and decisions

Keep existing [source-H](../../tests/test_real_komae_source_h.py),
[voxel](../../tests/test_real_komae_voxel.py), [solar](../../tests/test_real_komae_solar.py)
and synthetic/Consumer/accepted-lane regressions. They cover internal xlinks/H,
NoData/CRS, owner/ground/rounding/segments, pair priority, shared observers/sign
and crop controls. Gaps: alternate extents end-to-end, non-square grid export,
valid alternative report binding, rejected settings, both stages consuming one
resolved config, and positive full preflight beyond the current wrong-hash test.

Before real runs, add translated synthetic and non-square fixtures; catch stale
ROI globals, wrong pixel-centre/flip/transpose mapping, altered masks, forged
provenance, NoData/coverage loss, empty/zero-effect scenes and trees exceeding base Z. Keep nearest sampling,
full geometry, engine pin, D0/ground, IDs and TREE-only case difference invariant.
Then run focused suites and full pytest in the OUEM venv. Baseline comparison
requires exact numeric arrays/masks/IDs/centres (NaNs equal), H retention and
solar results under unchanged settings, with any unavoidable environment tolerance
explicitly reviewed. New report/file hashes may differ from timestamps/code paths;
never confuse semantic reproducibility with byte equality or relax source hashes.

For an **authorized future** real smoke, a candidate is the ROI translated 64 m
west (touching the current ROI), with the same size/margin, within the present
preparation bounds. Verify actual Building/DEM/Envelope coverage first; this is
not a claim those samples have been checked. Generate new runs, rerun Consumer
and all input guards, inspect retained boundary buildings, grid/ID/vertical and
pair diagnostics, observer masks, solar sign, ROI statistics and GIS XY/Z.
Do not expect the new area's cell values to equal the old ROI. Evaluate halo
bounds anew; expanded-domain convergence, if authorized, is a separate test.

Confirm before implementation: JSON config vs minimal CLI; whether the target
requires QGZ or only existing GeoTIFF/PNG; ROI/context selection and response to
insufficient halo/Z coverage; treatment of legitimate zero-effect/empty scenes.
No scientific assumption, major dependency or
formal contract change is necessary for the recommended first target. Broader
CRS/source/resolution support and physical observer/optical changes require the
user's explicit decision and evidence; this audit does not authorize them.

Runtime check was static only: `.venv/pyvenv.cfg` still records Python 3.11.9;
its referenced executable now exists (unlike the PR104 observation), but import,
engine metadata and actual interpreter health were not tested. No environment
repair or model/test execution occurred. This document records a plan, not a new
execution or Acceptance result.

## Final Refactoring Audit — v0.2 completion

Static review, 2026-10-29; main
`d8e480692d4457a7a0b6dacf30144ed1c635c6c6` (PR #109 merged).
**No Must finding: no refactoring is required before v0.2 completion for the
demonstrated existing-input/rectangle-reuse scope.** This is not a claim of
general input support, scientific validation or formal acceptance. Apply P3/P4/P5:
retain useful trust boundaries; avoid a cleanup campaign after successful reuse.

Inspected current source/imports/callers, CLI branches, tests, CI and the owning
[real-data verification record](../experiments/real_komae_solar/README.md#phase-3c-shared-z-real-data-verification--2026-10-29-jst).
Earlier Phase 1 P0 gaps are now implemented/verified there: strict JSON and saved
settings/receipt, dynamic horizontal dimensions, and separately approved shared Z.
No runtime test/model, dataset rehash, dependency installation or code change was
performed by this final audit; execution results belong to their dated records.

### Current ownership and dependency assessment

| Owner | Actual responsibility / boundary |
|---|---|
| [e2e_config.py](../../src/ouem/e2e_config.py): `RunConfig`, `Extent`, `configured_arguments` | Strict settings/input bindings and contained reference extent; per-run submitted/runnable copies; exclusive run reservation and exact-config Voxel receipt. Persistence here serves the same reproducibility boundary, not a model orchestrator. |
| [real_komae_voxel.py](../../src/ouem/real_komae_voxel.py): `execute_model`, `run`, `export_outputs` | Fresh source-H Consumer, actual engine grid/centres, whole Building supports, DEM/ground/D0 and public voxelization; scalar QA; base artifacts/report. It does not integrate Canopy or change Standard. |
| [real_komae_solar.py](../../src/ouem/real_komae_solar.py): `preflight`, `integrate_canopy`, `shared_grid`, `solar_pair`, `run`, `export` | Rebind/revalidate base and Envelope; public TREE generation plus scalar interval/case invariants; shared upper Z; paired direct solar/controls/observers; own artifacts/report. Base files/receipt stay immutable. |
| Existing consumers / adapters / evidence helpers | `Watch` and strict JSON belong to source-H validation; footprint/ID/relative-height helpers come from the existing adapter; Envelope sampling/semantics stay in `height_envelope`. Reuse does not bypass the accepted adapter's v0.1 manifest gate. |

The current Voxel runner no longer imports `canopy_shadow_poc` for ROI/domain.
Configured extents belong to `e2e_config`; retained legacy defaults are explicit.
Remaining avoidable coupling is utility ownership: config/Voxel/Solar import
`digest/write/distribution` from the Building runner (digest is itself re-exported
from the source-H Standardizer). Voxel/Solar import `environment/voxcity_provenance`
from broad `komae_integration`, whose imports include `komae_contained.PocBlocked`.
These imports do not execute Converter or contained E2E, but make current imports
depend on historical runner organization. No import-time performance claim was measured.

### Candidate evaluation

Must = completion blocker; Should = preferred next relevant maintenance, not a
v0.2 gate; Defer = act only when a concrete change justifies it; No change = retain.
Targets below name the current functions; no extraction is authorized by this audit.

| Priority / target | Concrete issue and minimal proposal | Benefit, scope and regression risk |
|---|---|---|
| **Should** — `e2e_config`/Voxel/Solar utility imports; `real_komae_source_h.write/distribution`, Standardizer `digest`, `komae_integration.environment/voxcity_provenance` | Non-model helpers pull in Building ingestion/Standardization and historical contained-runner dependencies. On the next support-code change, give only these helpers a narrow neutral owner; assess existing leaves before adding one. Move definitions, do not copy them or introduce a runner base class. Preserve old public imports by aliases if compatibility requires them. | Reduces unrelated import/change blast radius. Small helper bodies but several importers, pin constants and watched source identities: **moderate** integration/provenance risk. Inventory legacy callers, bind the new helper owner in implementation watches, preserve exact formatting/exclusive-write and PEP 610/RECORD semantics, then run affected tests and full pytest. Do not combine with physics changes. |
| **Defer** — Voxel `export_outputs`, Solar `export` | Same geographic affine (`origin+n_u*u`, reversed-u rows, v columns), NPY save/readback and 2D TIFF plumbing are implemented twice. If either exporter needs modification, extract only the common calculation/write primitive. | One XY convention reduces future drift; **moderate** GIS risk. Preserve distinct Voxel tags/finite-value expectations and Solar NaN/NoData policy. Test non-square/translated centres, dtype, mask, affine/readback and shared-Z sections; do not build a generic exporter or change container identities gratuitously. |
| **Defer** — Solar `preflight`, `integrate_canopy`, `solar_pair` | These are long but ordered domain operations: source binding → grid/ground → Envelope; intervals → public API → scalar QA; paired solar → controls. Split a named subphase only when changing that subphase makes the boundary useful. | May ease focused edits; **moderate/high** validation-order risk. No scene-manager/context hierarchy or broad movement of algorithms now. Keep public generation separate from its scalar oracle; retain explicit shape/D0/observer and case checks. |
| **Defer** — both `run` functions; `RunConfig.prepare/seal_voxel` | Stage preparation precedes runner try/finally; Voxel receipt sealing follows the completed report write. A preparation/write/seal failure can leave a partial run or completed model report without a receipt. Solar still rejects missing/mismatched receipts; this is an observability gap, not a fail-open route. Before changing lifecycle code, add failure-injection tests, then improve only exception context/failure recording if needed. | Clearer failure diagnosis without weakening exclusive no-resume behavior. **Moderate** evidence/status risk; test preparation, export, report write, engine recheck and seal failure ordering. Do not merge both runners into a generic lifecycle framework merely because finally blocks look alike. |
| **Defer** — Voxel imports `json`/`ROI`; Solar legacy `PR98_report`/message labels; `real_komae_*` names | AST confirms the two imports have no internal loaded use; repository caller search found no need for the Voxel ROI re-export. Some configured-mode diagnostics still say PR98. Remove tiny dead imports or clarify human-readable labels when touching the owner; retain machine keys/module CLI names unless compatibility is reviewed. | Minor clarity gain, **low** code but nonzero source-hash/import compatibility risk. No standalone cosmetic PR or mass rename. Lack of an in-repository caller alone does not justify deleting public paths. |
| **No change** — Consumer/`Watch`; Voxel `audit_voxels`; Solar `preflight/integrate_canopy` scalar/identity rechecks | Re-reading at generation, consumption and public-function boundaries serves freshness and independent engine verification. Shared ground/DEM/base oracle calls are deliberate producer-consumer reuse; TREE oracle stays distinct from public API generation. | Preserves P5 reliability. Removing passes, caching away hashes or deriving expected masks from the generated mask would hide corruption. Keep coherent rehash/tamper and allocation/rounding tests; do not count intentional verification as waste to eliminate. |
| **No change** — `RunConfig.load/capture/prepare/model_sha`, `confined`, `Watch.resolve` | Saved settings and receipt fix mutable-source-config loss. Path checks differ intentionally: output/config locators can name not-yet-created paths, while watched inputs must exist and be frozen. Keep the small explicit two-stage handoff and strict branches. | Clear reproducibility ownership. Blindly merging validators could alter path/existence semantics; no optional hashes, global config singleton, new orchestrator or alternate parser is needed. Preserve saved-config-after-delete and exact-binding tests. |
| **No change** — legacy CLI branches, old canopy PoCs, accepted Adapter entry | Legacy fixed pins/shape checks apply to their historical invocation, not configured reuse. Older canopy modules still have tests/sensitivity callers. Experimental source-H uses the explicit candidate Consumer and selected pure adapter helpers; `adapt_standard_to_voxcity` still rejects non-v0.1 manifests. | These are compatibility/evidence and formal boundaries, not proven dead routes. Keep source-H eligibility, Standard/Adapter/Acceptance and scientific constants unchanged. No removal/whitelist expansion or regional-copy replacement is warranted for v0.2 completion. |
| **Defer** — `tests/test_e2e_config.complete_scene`, test-module helper imports | E2E/vertical tests import authored scene/source-chain helpers from other test modules; a test-file reorganization can break fixture discovery. Use a small test-only fixture owner only when several tests actually need to move; keep independent expected geometry/placement definitions independent of production. | Improves test organization when needed; **low/moderate** fixture-discovery risk. Do not consolidate all fixtures or rewrite tests during a runtime helper move. Add fresh-process CLI help/dispatch smoke before moving entrypoint imports. |

### Regression sufficiency and remaining gaps

The four focused suites protect invalid/duplicate settings and every input hash,
saved settings after source-file editing/deletion, exclusive IDs/receipt binding,
translated/non-square grids and affine/NoData, actual Consumer/source-chain E2E,
ID/ground/rounding, coherently rehashed grid/occupancy tampering, shared-Z prefixes,
TREE priority, public allocator undercapacity, injected bad API output, paired
solar masks/sign/crop and saved shared metadata. See
[config tests](../../tests/test_e2e_config.py),
[Voxel tests](../../tests/test_real_komae_voxel.py),
[Solar tests](../../tests/test_real_komae_solar.py) and
[shared-Z tests](../../tests/test_shared_vertical_domain.py).
This is a useful regression net for bounded helper/extraction work, not proof of
complete coverage. Success integration mostly calls Python `run` directly; failure
injection for the complete persistence/finalization chain is the main uncovered
area before a lifecycle refactor. CI's [pytest workflow](../../.github/workflows/pytest.yml)
is configured for the full suite on Windows/Ubuntu Python 3.12; it does not replace the local
Windows Python 3.11.9/QGIS/real-input evidence or establish scientific accuracy.

For any later code refactor: freeze original source bytes/locators first; keep
input hashes, receipts and independent oracles; run the focused suites and full
OUEM-venv pytest plus affected legacy/accepted-lane tests. For GIS/physics/lifecycle
changes, require their specific failure/coordinate checks and semantic array
comparison. A new real A/B replay needs separate authorization, new Run IDs and
prefix/upper-air/2D comparison under the existing procedure; never rewrite old
hashes after moving a helper. This audit did not rerun tests or revalidate datasets.

**Completion recommendation:** accept the current bounded execution structure;
no pre-completion cleanup PR is necessary. If subsequent maintenance warrants a
first refactor, address only the utility-dependency row, preserving compatibility
imports and evidence; leave exporter/lifecycle/test reorganization for their own
demonstrated need. No large architecture, new settings or dependencies are proposed.
