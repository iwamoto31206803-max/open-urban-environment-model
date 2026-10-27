# Phase 4 repository inventory — 2026-10-27

Read with [Completion Gate](PHASE4_COMPLETION_GATE_REVIEW_20261027.md) and
[Phase 5 plan](PHASE5_INTEGRATION_PLAN_v0.1_Draft.md). Baseline:
`56059467dde052ad95c8a666f18acb660c7622a4` (merged PR #74).

## Inventory method and role boundaries

Baseline tracked files: **38 Markdown, 82 Python (including tests/namespace
markers), 15 Windows CMD launchers**. Local ignored datasets/run copies and
installed upstream source are excluded from these counts. Each baseline file
in these categories appears below; no file was moved, deleted or merged.
The three new audit documents are the only additions and are cross-linked.

Formal means an authoritative concept/contract/acceptance record within its
stated scope, not that every contract is FINAL or that every file under
acceptance has formal approval. Experimental records retain frozen evidence;
Historical means a dated snapshot, not permission to discard it. A primary role
is selected per document; the scope column records mixed status.

Dxx references below describe **baseline inline Markdown link edges** (code
fences excluded), not all plain-text mentions, external URLs, or runtime calls.
No missing relative file target was found at baseline. A separate static heading-
slug check flags two inherited B1/B2 anchors in Concept v0.2; live GitHub rendering
was not tested, so these are CLARIFY risks rather than confirmed working anchors.
Source in/out links are
listed before these audit additions; a new inventory link does not mean the
baseline was already indexed. Non-Markdown outgoing file targets are included.

## Documentation inventory

| ID / file | Purpose | Primary role | Baseline inbound / outbound references | Freshness, scope and duplication/conflict | Action |
|---|---|---|---|---|---|
| D01 [AGENTS.md](../../../AGENTS.md) | Development authority / runtime / Git instructions | Operational | In: none; Out: none | Current contributor rules; not an acceptance artifact | KEEP |
| D02 [README.md](../../../README.md) | Project entry / canonical lifecycle and commands | Operational | In: D19, D30; Out: `LICENSE`, `config/study_areas/komae_09LD3451.yaml`, D04, D05, D06, D07, D09, D10, D11, D13, D16, D18, D19, D37, D38 | Current formal links; historical 23-ku Raw example and no Phase 2-4 index can mislead discovery | CLARIFY |
| D03 [docs/CHM_Height_Envelope_PoC_v0.1.md](../../CHM_Height_Envelope_PoC_v0.1.md) | Standalone envelope usage and evidence/QA boundary | Experimental | In: D27, D36; Out: D06, D07, D08, D09, D10, D19, `src/ouem/acquire/meta_chmv2.py` | Owns numeric state schema; initial no-real-data environment note is historical, later runs exist | CLARIFY |
| D04 [docs/Meta_CHMv2_AOI_Acquisition_PoC.md](../../Meta_CHMv2_AOI_Acquisition_PoC.md) | Acquisition recipe / actual source metadata / audit replay | Experimental | In: D02; Out: D06, D19, D31 | Owns pixel/mask preservation and source identity; not HAG/presence acceptance | KEEP |
| D05 [docs/OUEM_Concept_Architecture_v0.1.md](../../OUEM_Concept_Architecture_v0.1.md) | Historical concept and inherited B1/B2 detail source | Historical | In: D02, D06, D11; Out: none | v0.2 explicitly inherits selected details; not safe to delete/archive wholesale | KEEP |
| D06 [docs/OUEM_Concept_Architecture_v0.2.md](../../OUEM_Concept_Architecture_v0.2.md) | Registered upper conceptual design, decisions 01-36 | Formal | In: D02, D03, D04, D08, D32; Out: D05, D07, D09, D10, D11, D13, D16, D37 | Does not amend contracts; A1/A2/A3 naming differs; 2 inherited B1/B2 heading anchors need review | CLARIFY |
| D07 [docs/OUEM_Standard_Building_v0.1.md](../../OUEM_Standard_Building_v0.1.md) | Provider-independent absolute-Z Building contract | Formal | In: D02, D03, D06, D08, D11, D26, D32; Out: D16, D37 | PROVISIONAL contract with bounded Komae acceptance; retained Native Z interpretation is explicit | KEEP |
| D08 [docs/OUEM_Standard_Canopy_v0.1_Draft.md](../../OUEM_Standard_Canopy_v0.1_Draft.md) | Proposed full polygon/height/presence contract | Draft | In: D03, D27; Out: D06, D07, D09, D10 | Unratified state numbers and coverage; not Height Envelope validity bits | KEEP |
| D09 [docs/OUEM_Standard_Terrain_v0.1.md](../../OUEM_Standard_Terrain_v0.1.md) | Canonical Terrain grid/value/NoData/vertical contract | Formal | In: D02, D03, D06, D08, D11, D15, D26, D32; Out: D10, D12, D13, D15, D16 | PROVISIONAL; canonical 0.5m preserved; Tama correction is additive | KEEP |
| D10 [docs/OUEM_VoxCity_Adapter_v0.1.md](../../OUEM_VoxCity_Adapter_v0.1.md) | Accepted Building engine boundary and pin | Formal | In: D02, D03, D06, D08, D09, D26, D32; Out: none | Building-only EPSG:4326/precise rasterization; not the canopy EPSG:6677 experimental grid | KEEP |
| D11 [docs/Phase_A_Implementation_Design_v0.1.md](../../Phase_A_Implementation_Design_v0.1.md) | Lifecycle and original scaffold boundaries | Historical | In: D02, D06, D32; Out: D05, D07, D09, D13, D16, D37 | Current-status note owns interpretation; old pending sections are not current inventory | KEEP |
| D12 [docs/Terrain_Acquisition_PoC_v0.1.md](../../Terrain_Acquisition_PoC_v0.1.md) | Single Tama tile acquisition / SHA / limits | Experimental | In: D09, D14, D15, D38; Out: D13, D15, D18, D19, D38 | Connects to unchanged Native/Standard; not automatic formal reacceptance | KEEP |
| D13 [docs/acceptance/OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md](../../acceptance/OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md) | Original A2 formal dataset acceptance | Formal | In: D02, D06, D09, D11, D12, D14, D15, D30, D32, D38; Out: none | Frozen data/hash conditions; never silently update provider history or expected hashes | KEEP |
| D14 [docs/acceptance/OUEM_A2_Terrain_Reproducibility_Verification_20261026.md](../../acceptance/OUEM_A2_Terrain_Reproducibility_Verification_20261026.md) | Technical real-data reproducibility record | Experimental | In: D36; Out: D12, D13, D15, D16, D38 | Filed under acceptance but technical PASS proposal; formal approval pending in its text | KEEP |
| D15 [docs/acceptance/OUEM_A2_Terrain_Source_Provenance_Correction_20261026.md](../../acceptance/OUEM_A2_Terrain_Source_Provenance_Correction_20261026.md) | Additive source correction to original A2 | Formal | In: D09, D12, D14, D38; Out: D09, D12, D13, D16, D38 | Tama byte identity / source-declared T.P.; does not reverify prior outputs | KEEP |
| D16 [docs/acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md](../../acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md) | Original A3 Building/Terrain voxel acceptance | Formal | In: D02, D06, D07, D09, D11, D14, D15, D30, D32; Out: none | 111-building frozen paths without input hashes; not authority for a new Phase 5 identity | KEEP |
| D17 [docs/acceptance/OUEM_Komae_Contained_E2E_Acceptance_20261018.md](../../acceptance/OUEM_Komae_Contained_E2E_Acceptance_20261018.md) | Bounded 92-building local E2E review | Formal | In: D30, D32; Out: none | Reviewed evidence PASS; artifact acceptance field remains PENDING_LOCAL_REVIEW | KEEP |
| D18 [docs/architecture.md](../../architecture.md) | Normative Windows runtime process boundary | Operational | In: D02, D12, D19, D30; Out: none | Runtime versions elsewhere are observations, not competing minimums | KEEP |
| D19 [docs/development/OUEM_Windows_Development_and_Remote_Setup_20261025.md](../../development/OUEM_Windows_Development_and_Remote_Setup_20261025.md) | Accepted local environment observations | Operational | In: D02, D03, D04, D12, D30, D32; Out: D02, D18, D38 | Environment-only acceptance, frozen versions/tests; not data/E2E acceptance | KEEP |
| D20 [docs/experiments/voxcity_canopy_shadow/API_REVIEW.md](API_REVIEW.md) | Phase 0 pinned API evidence / locations | Historical | In: D21, D22, D28; Out: D21, D28 | Fixed source investigation; later fractional-origin and fast/slow findings in Phase 4A | LINK / INDEX |
| D21 [docs/experiments/voxcity_canopy_shadow/MINIMAL_ADAPTER_PROPOSAL.md](MINIMAL_ADAPTER_PROPOSAL.md) | Phase 0-1 not-yet-implemented proposal | Historical | In: D20, D22, D28; Out: D20, D28 | Superseded for implementation by Phase 2, still audit history; no deletion/move now | ARCHIVE CANDIDATE |
| D22 [docs/experiments/voxcity_canopy_shadow/PHASE2_RESULTS_20261027.md](PHASE2_RESULTS_20261027.md) | Real canopy-only A/B technical results | Experimental | In: D25; Out: D20, D21, D23, `docs/experiments/voxcity_canopy_shadow/images/phase2_komae_direct_20261027.png` | Frozen code/input/output hashes; model observer about 2-3m, not physical 1.5m | KEEP |
| D23 [docs/experiments/voxcity_canopy_shadow/PHASE2_USAGE.md](PHASE2_USAGE.md) | Frozen 1m runner instructions / gates | Operational | In: D22; Out: none | Owns CLI reproduction; not a common future generic Adapter contract | KEEP |
| D24 [docs/experiments/voxcity_canopy_shadow/PHASE3_API_AND_METHOD.md](PHASE3_API_AND_METHOD.md) | Resolution and observer sensitivity method | Experimental | In: D25, D26; Out: none | Owns 2x2 nearest replication and tested map-origin lattice; review with Phase 4A | KEEP |
| D25 [docs/experiments/voxcity_canopy_shadow/PHASE3_RESULTS_20261027.md](PHASE3_RESULTS_20261027.md) | Four real-data sensitivity case results | Experimental | In: D26; Out: D22, D24, `docs/experiments/voxcity_canopy_shadow/images/phase3_komae_sensitivity_20261027.png` | Composite resolution/observer effect; single ordered timing not a benchmark | KEEP |
| D26 [docs/experiments/voxcity_canopy_shadow/PHASE4A_OBSERVER_GEOMETRY_AND_VERTICAL_CONTRACT.md](PHASE4A_OBSERVER_GEOMETRY_AND_VERTICAL_CONTRACT.md) | Observer APIs / proposed Z contract / recommendation C | Experimental | In: none; Out: D07, D09, D10, D24, D25 | Not an accepted Standard contract; arbitrary fractional origins remain blocked; no baseline inbound MD link | LINK / INDEX |
| D27 [docs/experiments/voxcity_canopy_shadow/PHASE4B_CANOPY_PRESENCE_AND_COVERAGE_AUDIT.md](PHASE4B_CANOPY_PRESENCE_AND_COVERAGE_AUDIT.md) | State/presence audit and proposed Phase 5 diagnostics | Experimental | In: none; Out: D03, D08 | Owns factorized evidence and conversion-loss gates; no baseline inbound MD link | LINK / INDEX |
| D28 [docs/experiments/voxcity_canopy_shadow/RESULTS.md](RESULTS.md) | Phase 0-1 decision snapshot (not latest results) | Historical | In: D20, D21; Out: D20, D21 | Title collides with local RESULTS.md; retained verbatim historical no-implementation statements | LINK / INDEX |
| D29 [docs/planning/OUEM_Data_Acquisition_and_Preparation_Design_v0.1_Draft.md](../../planning/OUEM_Data_Acquisition_and_Preparation_Design_v0.1_Draft.md) | Proposed acquisition/preparation responsibilities | Draft | In: none; Out: none | No baseline inline inbound link; not an implemented universal catalog | LINK / INDEX |
| D30 [docs/planning/OUEM_Data_Acquisition_and_Reproducibility_Inventory_20261025.md](../../planning/OUEM_Data_Acquisition_and_Reproducibility_Inventory_20261025.md) | Dated acquisition and local rerun gap inventory | Historical | In: D32; Out: `LICENSE`, D02, `config/study_areas/komae_09LD3451.yaml`, D13, D16, D17, D18, D19, `docs/local_handoff/komae_test_standard.tif.provenance.json`, D32, D34, D35, D37, `pyproject.toml`, D38 | Predates Tama confirmation/acquisition; preserve snapshot and point readers to newer recipes | LINK / INDEX |
| D31 [docs/planning/OUEM_Source_Catalog_and_Acquisition_Recipes_v0.1_Draft.md](../../planning/OUEM_Source_Catalog_and_Acquisition_Recipes_v0.1_Draft.md) | Source Catalog / Recipe candidates | Draft | In: D04; Out: none | Not ratified manifest/catalog schemas; local data are not globally reproducible automatically | KEEP |
| D32 [docs/planning/OUEM_v0.2_Implementation_Inventory_20261025.md](../../planning/OUEM_v0.2_Implementation_Inventory_20261025.md) | Dated broad implementation gap inventory | Historical | In: D30; Out: D06, D07, D09, D10, D11, D13, D16, D17, D19, D30, D34, D35, D37 | Before acquisition/envelope/solar changes; do not use its Not Implemented rows as current status | LINK / INDEX |
| D33 [docs/processing_model.md](../../processing_model.md) | Short runtime boundary diagram / processing explanation | Operational | In: none; Out: none | Overlaps architecture.md; future consolidation only with retained redirects/links | CONSOLIDATION CANDIDATE |
| D34 [docs/research/OUEM_Komae_Building_Vertical_Geometry_Diagnosis.md](../../research/OUEM_Komae_Building_Vertical_Geometry_Diagnosis.md) | Unresolved source-to-Standard Building Z investigation | Experimental | In: D30, D32, D38; Out: none | Approx. 37m discrepancy is a hypothesis; matched source-chain evidence not established here | CLARIFY |
| D35 [docs/research/OUEM_VoxCity_1.7.0_Canopy_Contract_Verification.md](../../research/OUEM_VoxCity_1.7.0_Canopy_Contract_Verification.md) | Early pinned-source and synthetic canopy verification | Historical | In: D30, D32; Out: `pyproject.toml` | Real-data-unresolved statements date to 2026-10-18; later Phase 2-4 evidence is separate | LINK / INDEX |
| D36 [docs/verification/OUEM_Height_Envelope_3D_Visualization_Komae_20261026.md](../../verification/OUEM_Height_Envelope_3D_Visualization_Komae_20261026.md) | QGIS evidence / 40,789 cell geometry verification | Experimental | In: none; Out: D03, D14, `docs/verification/images/OUEM_Height_Envelope_3D_Komae_20261026.png`, `src/ouem/height_envelope.py` | Stored GUI evidence, not a new display or scientific crown acceptance; no baseline inbound MD link | LINK / INDEX |
| D37 [experiments/a1_e2e_pilot/README.md](../../../experiments/a1_e2e_pilot/README.md) | Building Native/Standard local acceptance | Formal | In: D02, D06, D07, D11, D30, D32; Out: none | 3,637 Native / 111 intersecting Standard; manual converter boundary and observed Z preservation | KEEP |
| D38 [scripts/work/README.md](../../../scripts/work/README.md) | Human runbook for Windows helpers / boundaries | Operational | In: D02, D12, D14, D15, D19, D30; Out: D12, D13, D15, D34 | Long operational history; commands include accepted and experimental paths; future index by role | LINK / INDEX |

### Consolidation priorities (recommendations, not executed changes)

1. **LINK / INDEX first:** use the Gate/plan as the Phase 4 review entry, rather
   than treating Phase 0 RESULTS.md as latest. A future README/runbook index may
   link here; README is unchanged in this PR. All Phase 2-4 frozen records stay.
2. **CLARIFY later:** README's legacy `tokyo_23ku_dem_050m` example needs an
   explicit pointer to Tama acquisition/correction, not movement/deletion of old
   Raw. Verify/correct the two inherited B1/B2 heading fragments in a separate
   Concept-owned link-only follow-up. Height Envelope's initial no-real-data note and old planning inventories
   are dated environment/status snapshots. Building vertical diagnosis remains
   unresolved until chosen-dataset evidence exists; do not edit it to imply a fix.
3. **CONSOLIDATION CANDIDATE:** architecture.md owns runtime separation;
   processing_model.md can later become a concise linked explanation. Repeated
   pin/grid/formula summaries in experiments are deliberate frozen context, not
   competing contracts to be rewritten into a single latest result.
4. **ARCHIVE CANDIDATE:** Phase 0-1 proposal can later be indexed as historical
   superseded design; retain the path or a redirect and original evidence. Do
   not archive v0.1 Concept wholesale: inherited B1/B2 details remain referenced.

## Code and test inventory

Cxx IDs identify baseline Python files. Dependency edges below are static AST
internal imports (plus explicitly inspected child-process edges), **not proof
that every imported branch ran**. Launchers are separately mapped to modules.
External engine calls for the canopy path are Voxelizer.generate_combined and
CPU get_direct_solar_irradiance_map; Phase 4A tests also inspect internal tracing.
The accepted worker process boundary and CLI wrappers are not duplicate imports.

Actions: KEEP preserves a responsibility; FREEZE preserves experimental protocol
and hash-bound reproduction; REUSE CANDIDATE requires compatibility checks;
REFACTOR CANDIDATE requires a separate versioned change with frozen baseline
reproduction. No REMOVE CANDIDATE is justified solely by low apparent call count.

| ID / path | Responsibility / entry | Role | Current internal references | Phase 5 reuse / duplication / reproducibility impact | Action |
|---|---|---|---|---|---|
| C01 [scripts/work/capture_gis_runtime.py](../../../scripts/work/capture_gis_runtime.py) | Capture configured GIS executable/runtime receipt | Utility | In: none statically; Out: no internal import | Operational record creation, not dataset validation | KEEP |
| C02 [scripts/work/diagnose_komae_dem_coverage.py](../../../scripts/work/diagnose_komae_dem_coverage.py) | Standalone DEM coverage diagnostic | Utility | In: none statically; Out: C14, C27 | Called by .cmd; overlap with height diagnostics is a future common-read utility candidate | REFACTOR CANDIDATE |
| C03 [scripts/work/diagnose_voxcity_building_ids.py](../../../scripts/work/diagnose_voxcity_building_ids.py) | Dataset-specific ID/overlap diagnostic | Utility | In: none statically; Out: C14 | Referenced by frozen A3 record despite no Python inbound import; historical evidence dependency | FREEZE |
| C04 [scripts/work/diagnose_voxcity_id11.py](../../../scripts/work/diagnose_voxcity_id11.py) | Dataset-specific ID/overlap diagnostic | Utility | In: none statically; Out: C14 | Referenced by frozen A3 record despite no Python inbound import; historical evidence dependency | FREEZE |
| C05 [scripts/work/diagnose_voxcity_id37_overlap.py](../../../scripts/work/diagnose_voxcity_id37_overlap.py) | Dataset-specific ID/overlap diagnostic | Utility | In: none statically; Out: C14 | Referenced by frozen A3 record despite no Python inbound import; historical evidence dependency | FREEZE |
| C06 [scripts/work/gis_runtime_check.py](../../../scripts/work/gis_runtime_check.py) | GIS process runtime check | Utility | In: none statically; Out: no internal import | Executed only in GIS stage; not OUEM import runtime | KEEP |
| C07 [scripts/work/ouem_runtime_check.py](../../../scripts/work/ouem_runtime_check.py) | OUEM venv runtime check | Utility | In: none statically; Out: C09, C43 | Delegates ouem.runtime; do not combine interpreter environments | KEEP |
| C08 [scripts/work/voxcity_komae_a3_acceptance.py](../../../scripts/work/voxcity_komae_a3_acceptance.py) | Historical A3 voxel acceptance driver (subprocess CLI) | Utility | In: C27 (subprocess); Out: C14, C21 | Imported by integration through command path; formal record references it; do not fold into canopy runner | FREEZE |
| C09 [src/ouem/__init__.py](../../../src/ouem/__init__.py) | Namespace marker; no processing implementation | Utility | In: C07, C19, C20, C22, C24, C25, C26, C27, C28, C29, C30, C31, C54, C57, C58, C59, C60, C62, C63, C64, C65, C66, C67, C68, C69, C70, C71, C72, C79, C82; Out: no internal import | Retain architecture scaffold; empty file does not justify deleting package | KEEP |
| C10 [src/ouem/acquire/__init__.py](../../../src/ouem/acquire/__init__.py) | Namespace marker; no processing implementation | Utility | In: C73, C80; Out: no internal import | Retain architecture scaffold; empty file does not justify deleting package | KEEP |
| C11 [src/ouem/acquire/meta_chmv2.py](../../../src/ouem/acquire/meta_chmv2.py) | Aligned acquisition/crop, file_record/hash/raster metadata; python -m | Experimental | In: C18, C54, C73; Out: C51 | Reuse mask/value/hash gates; generic utility extraction changes supporting-module hashes | REUSE CANDIDATE |
| C12 [src/ouem/acquire/tokyo_tama_dem.py](../../../src/ouem/acquire/tokyo_tama_dem.py) | One-tile Raw acquisition/verification; python -m | Experimental | In: C52, C80; Out: C41 | Reuse verified Raw recipe only; no new terrain algorithm | KEEP |
| C13 [src/ouem/adapters/__init__.py](../../../src/ouem/adapters/__init__.py) | Namespace marker; no processing implementation | Utility | In: C20, C24, C26, C29, C60, C64, C70, C82; Out: no internal import | Retain architecture scaffold; empty file does not justify deleting package | KEEP |
| C14 [src/ouem/adapters/voxcity/__init__.py](../../../src/ouem/adapters/voxcity/__init__.py) | Building footprint/ID/mean-ground and height contract; ouem-adapt-voxcity | Formal | In: C02, C03, C04, C05, C08, C15, C20, C23, C24, C26, C27, C28, C29, C31, C60, C61, C63, C64, C66, C70, C81, C82; Out: no internal import | Candidate normalization/ID derivation; geographic grid not interchangeable with Phase 2 projected grid | KEEP |
| C15 [src/ouem/adapters/voxcity/__main__.py](../../../src/ouem/adapters/voxcity/__main__.py) | Thin python -m entry to package main | Utility | In: none statically; Out: C14 | Same contract and tests as parent; retain compatibility path | KEEP |
| C16 [src/ouem/canopy_shadow_poc.py](../../../src/ouem/canopy_shadow_poc.py) | Fixed 1m adapter/runner + independent voxel QA; python -m | Experimental | In: C17, C54, C55, C56; Out: C18, C27 | Freeze Phase 2: strict all-valid gate, 1m crop metadata, fixed sun/optics; no generic mutable API | FREEZE |
| C17 [src/ouem/canopy_shadow_sensitivity.py](../../../src/ouem/canopy_shadow_sensitivity.py) | 1m/0.5m geometry, memory and observer sensitivity; python -m | Experimental | In: C53, C54, C56; Out: C16, C27 | Imports Phase 2 helpers; parallel geometry audit intentional; Phase 5 can reuse only validated pieces | FREEZE |
| C18 [src/ouem/height_envelope.py](../../../src/ouem/height_envelope.py) | GridSpec, semantic gate, samples, CR and state arithmetic; python -m | Experimental | In: C16, C54, C57; Out: C11, C51 | Reuse source-bound validation, preserve Float32/state contract and code hashes | REUSE CANDIDATE |
| C19 [src/ouem/komae_adapter_diagnostics.py](../../../src/ouem/komae_adapter_diagnostics.py) | Adapter contract/content diagnostic replay; python -m | Utility | In: C20, C24, C25, C59; Out: C09, C27 | Reusable evidence reading, not proof of new integration | REUSE CANDIDATE |
| C20 [src/ouem/komae_adapter_geometry_steps.py](../../../src/ouem/komae_adapter_geometry_steps.py) | Normalization/repair step provenance; python -m | Utility | In: C24, C60; Out: C09, C13, C14, C19, C25, C27 | Shares footprint evidence; preserve exact accepted geometry path | KEEP |
| C21 [src/ouem/komae_canopy.py](../../../src/ouem/komae_canopy.py) | Legacy thresholded CHM conversion / scenario_arrays | Experimental | In: C08, C61; Out: no internal import | 3m cutoff and old HAG schema differ from Height Envelope; do not auto-connect | FREEZE |
| C22 [src/ouem/komae_canopy_qgis_export.py](../../../src/ouem/komae_canopy_qgis_export.py) | Legacy canopy/Building QGIS export; python -m | Experimental | In: C62, C66; Out: C09, C25, C27, C29 | Not the Height Envelope visualization generator or accepted Canopy | FREEZE |
| C23 [src/ouem/komae_contained.py](../../../src/ouem/komae_contained.py) | 92-building contained selection and source preservation | Experimental | In: C27, C63; Out: C14, C27 | Historical dataset protocol; cannot assume its subset is Phase 5 ROI | FREEZE |
| C24 [src/ouem/komae_crs_repair_evaluation.py](../../../src/ouem/komae_crs_repair_evaluation.py) | Historical candidate CRS geometry repairs; python -m | Experimental | In: C29, C64, C70, C82; Out: C09, C13, C14, C19, C20, C25, C27 | Do not substitute alternatives for accepted repair; tests compare to formal path | FREEZE |
| C25 [src/ouem/komae_geometry_provenance.py](../../../src/ouem/komae_geometry_provenance.py) | Native/Standard/Converter transition diagnosis; python -m | Utility | In: C20, C22, C24, C26, C29, C30, C31, C65, C71; Out: C09, C19, C27, C45 | Candidate chosen-Building source-chain audit; needs actual local artifacts | REUSE CANDIDATE |
| C26 [src/ouem/komae_height_diagnostics.py](../../../src/ouem/komae_height_diagnostics.py) | DEM sampling/ground/height diagnosis; python -m | Utility | In: C66; Out: C09, C13, C14, C25, C27, C29 | Candidate effective-ground checks; diagnostic sampling must match selected grid | REUSE CANDIDATE |
| C27 [src/ouem/komae_integration.py](../../../src/ouem/komae_integration.py) | Legacy orchestration, run guards, voxcity_provenance; python -m | Utility | In: C02, C16, C17, C19, C20, C22, C23, C24, C25, C26, C28, C29, C30, C31, C53, C54, C55, C56, C59, C60, C61, C62, C63, C64, C65, C66, C67, C68, C69, C70, C71, C72; Out: C09, C14, C23, C28, C39, C41, C43, C51 | Runtime child A3_SCRIPT; pin helper is reused by canopy tests/runners; separate extraction only with compatibility | REFACTOR CANDIDATE |
| C28 [src/ouem/komae_preflight.py](../../../src/ouem/komae_preflight.py) | OUEM/GIS runtime and Native preflight | Utility | In: C27, C68; Out: C09, C14, C27, C39, C49 | Read-only checks reusable; accepted runtime rules remain | REUSE CANDIDATE |
| C29 [src/ouem/komae_repair_qgis_export.py](../../../src/ouem/komae_repair_qgis_export.py) | Frozen repair-evidence QGIS export; python -m | Utility | In: C22, C26, C30, C31, C70; Out: C09, C13, C14, C24, C25, C27 | Source-protective diagnostic export; not a building source repair | KEEP |
| C30 [src/ouem/komae_vertical_exploratory.py](../../../src/ouem/komae_vertical_exploratory.py) | Candidate external Converter vertical investigation; python -m | Experimental | In: C71; Out: C09, C25, C27, C29, C31, C45 | Unresolved source hypothesis; do not apply diagnostic candidate as correction | FREEZE |
| C31 [src/ouem/komae_vertical_provenance.py](../../../src/ouem/komae_vertical_provenance.py) | Read CityGML/Converter/Standard matched Z; python -m | Utility | In: C30, C72; Out: C09, C14, C25, C27, C29, C45 | Candidate input-evidence gate; no transformation approval inferred | REUSE CANDIDATE |
| C32 [src/ouem/model/__init__.py](../../../src/ouem/model/__init__.py) | Namespace marker; no processing implementation | Utility | In: none statically; Out: no internal import | Retain architecture scaffold; empty file does not justify deleting package | KEEP |
| C33 [src/ouem/model/building/__init__.py](../../../src/ouem/model/building/__init__.py) | Namespace marker; no implementation | Utility | In: none statically; Out: no internal import | Architecture scaffold, not accepted model logic | KEEP |
| C34 [src/ouem/model/canopy/__init__.py](../../../src/ouem/model/canopy/__init__.py) | Namespace marker; no implementation | Utility | In: none statically; Out: no internal import | Do not count as complete Standard Canopy | KEEP |
| C35 [src/ouem/model/terrain/__init__.py](../../../src/ouem/model/terrain/__init__.py) | Namespace marker; no implementation | Utility | In: none statically; Out: no internal import | Do not count as Terrain Adapter | KEEP |
| C36 [src/ouem/native/__init__.py](../../../src/ouem/native/__init__.py) | Namespace marker; no processing implementation | Utility | In: none statically; Out: no internal import | Retain architecture scaffold; empty file does not justify deleting package | KEEP |
| C37 [src/ouem/native/building/__init__.py](../../../src/ouem/native/building/__init__.py) | Namespace marker; no processing implementation | Utility | In: C74; Out: no internal import | Retain architecture scaffold; empty file does not justify deleting package | KEEP |
| C38 [src/ouem/native/building/_plateau_gdal_worker.py](../../../src/ouem/native/building/_plateau_gdal_worker.py) | Native GDAL inspection/copy worker | Formal | In: C74, C39 (worker); Out: no internal import | Frozen provider semantics and worker boundary; real acceptance separate | KEEP |
| C39 [src/ouem/native/building/plateau.py](../../../src/ouem/native/building/plateau.py) | Converter GPKG ingest orchestration; ouem-plateau-buildings | Formal | In: C27, C28, C45, C74, C76; Out: no internal import | Calls _plateau_gdal_worker in GIS child; no source Z correction | KEEP |
| C40 [src/ouem/native/canopy/__init__.py](../../../src/ouem/native/canopy/__init__.py) | Namespace marker; no implementation | Utility | In: none statically; Out: no internal import | Canopy native contract unresolved | KEEP |
| C41 [src/ouem/native/terrain/__init__.py](../../../src/ouem/native/terrain/__init__.py) | Raw-linked Native Terrain manifest; ouem-accept-terrain | Formal | In: C12, C27, C42, C49, C52, C57, C63, C67, C68, C77, C80; Out: no internal import | Reuse provenance/input checks; original bytes remain canonical | KEEP |
| C42 [src/ouem/native/terrain/__main__.py](../../../src/ouem/native/terrain/__main__.py) | Thin python -m entry to package main | Utility | In: none statically; Out: C41 | Same contract and tests as parent; retain compatibility path | KEEP |
| C43 [src/ouem/runtime.py](../../../src/ouem/runtime.py) | Separate OUEM/GIS runtime validation | Utility | In: C07, C27, C75; Out: no internal import | Reusable checks; no GIS runtime merge | KEEP |
| C44 [src/ouem/standardize/__init__.py](../../../src/ouem/standardize/__init__.py) | Namespace marker; no processing implementation | Utility | In: C76; Out: no internal import | Retain architecture scaffold; empty file does not justify deleting package | KEEP |
| C45 [src/ouem/standardize/building/__init__.py](../../../src/ouem/standardize/building/__init__.py) | Native to Standard orchestration; ouem-standardize-buildings | Formal | In: C25, C30, C31, C46, C65, C76; Out: C39, C51 | Calls _gdal_worker; do not alter accepted geometry/Z to suit experiment | KEEP |
| C46 [src/ouem/standardize/building/__main__.py](../../../src/ouem/standardize/building/__main__.py) | Thin python -m entry to package main | Utility | In: none statically; Out: C45 | Same contract and tests as parent; retain compatibility path | KEEP |
| C47 [src/ouem/standardize/building/_gdal_worker.py](../../../src/ouem/standardize/building/_gdal_worker.py) | Horizontal-only transform, preserve Z, ID/geometry worker | Formal | In: C76, C45 (worker); Out: no internal import | No converter-source vertical verification; own runtime and tests | KEEP |
| C48 [src/ouem/standardize/canopy/__init__.py](../../../src/ouem/standardize/canopy/__init__.py) | Namespace marker; no implementation | Utility | In: none statically; Out: no internal import | No Standard Canopy standardizer exists here | KEEP |
| C49 [src/ouem/standardize/terrain/__init__.py](../../../src/ouem/standardize/terrain/__init__.py) | Grid/value-preserving Standard Terrain; ouem-standardize-terrain | Formal | In: C28, C50, C57, C67, C77; Out: C41, C51 | No engine resampling here; unchanged 0.5m canonical raster | KEEP |
| C50 [src/ouem/standardize/terrain/__main__.py](../../../src/ouem/standardize/terrain/__main__.py) | Thin python -m entry to package main | Utility | In: none statically; Out: C49 | Same contract and tests as parent; retain compatibility path | KEEP |
| C51 [src/ouem/study_area.py](../../../src/ouem/study_area.py) | StudyArea YAML loader and extent checks | Utility | In: C11, C18, C27, C45, C49, C54, C63, C73, C78; Out: no internal import | Reuse explicit extent, not proof of engine grid identity | KEEP |
| C52 [src/ouem/terrain_local_acceptance.py](../../../src/ouem/terrain_local_acceptance.py) | Check/run Native+Standard helper; python -m | Utility | In: C77, C79; Out: C12, C41 | PROCESSING_COMPLETED_PENDING_REVIEW is CLI completion, not independent QA/acceptance | KEEP |
| C53 [tests/test_canopy_observer_geometry.py](../../../tests/test_canopy_observer_geometry.py) | canopy observer geometry regression / characterization | Test | In: none statically; Out: C17, C27 | Imported targets are static references; synthetic tests do not establish real-data acceptance | FREEZE |
| C54 [tests/test_canopy_presence_semantics.py](../../../tests/test_canopy_presence_semantics.py) | canopy presence semantics regression / characterization | Test | In: none statically; Out: C09, C11, C16, C17, C18, C27, C51 | Imported targets are static references; synthetic tests do not establish real-data acceptance | FREEZE |
| C55 [tests/test_canopy_shadow_poc.py](../../../tests/test_canopy_shadow_poc.py) | canopy shadow poc regression / characterization | Test | In: none statically; Out: C16, C27 | Imported targets are static references; synthetic tests do not establish real-data acceptance | FREEZE |
| C56 [tests/test_canopy_shadow_sensitivity.py](../../../tests/test_canopy_shadow_sensitivity.py) | canopy shadow sensitivity regression / characterization | Test | In: none statically; Out: C16, C17, C27 | Imported targets are static references; synthetic tests do not establish real-data acceptance | FREEZE |
| C57 [tests/test_height_envelope.py](../../../tests/test_height_envelope.py) | height envelope regression / characterization | Test | In: none statically; Out: C09, C18, C41, C49 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C58 [tests/test_import.py](../../../tests/test_import.py) | import regression / characterization | Test | In: none statically; Out: C09 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C59 [tests/test_komae_adapter_diagnostics.py](../../../tests/test_komae_adapter_diagnostics.py) | komae adapter diagnostics regression / characterization | Test | In: none statically; Out: C09, C19, C27 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C60 [tests/test_komae_adapter_geometry_steps.py](../../../tests/test_komae_adapter_geometry_steps.py) | komae adapter geometry steps regression / characterization | Test | In: none statically; Out: C09, C13, C14, C20, C27 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C61 [tests/test_komae_canopy.py](../../../tests/test_komae_canopy.py) | komae canopy regression / characterization | Test | In: none statically; Out: C14, C21, C27 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C62 [tests/test_komae_canopy_qgis_export.py](../../../tests/test_komae_canopy_qgis_export.py) | komae canopy qgis export regression / characterization | Test | In: none statically; Out: C09, C22, C27 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C63 [tests/test_komae_contained.py](../../../tests/test_komae_contained.py) | komae contained regression / characterization | Test | In: none statically; Out: C09, C14, C23, C27, C41, C51 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C64 [tests/test_komae_crs_repair_evaluation.py](../../../tests/test_komae_crs_repair_evaluation.py) | komae crs repair evaluation regression / characterization | Test | In: none statically; Out: C09, C13, C14, C24, C27 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C65 [tests/test_komae_geometry_provenance.py](../../../tests/test_komae_geometry_provenance.py) | komae geometry provenance regression / characterization | Test | In: none statically; Out: C09, C25, C27, C45 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C66 [tests/test_komae_height_diagnostics.py](../../../tests/test_komae_height_diagnostics.py) | komae height diagnostics regression / characterization | Test | In: none statically; Out: C09, C14, C22, C26, C27 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C67 [tests/test_komae_integration.py](../../../tests/test_komae_integration.py) | komae integration regression / characterization | Test | In: none statically; Out: C09, C27, C41, C49 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C68 [tests/test_komae_preflight.py](../../../tests/test_komae_preflight.py) | komae preflight regression / characterization | Test | In: none statically; Out: C09, C27, C28, C41 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C69 [tests/test_komae_repair_acceptance.py](../../../tests/test_komae_repair_acceptance.py) | komae repair acceptance regression / characterization | Test | In: none statically; Out: C09, C27 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C70 [tests/test_komae_repair_qgis_export.py](../../../tests/test_komae_repair_qgis_export.py) | komae repair qgis export regression / characterization | Test | In: none statically; Out: C09, C13, C14, C24, C27, C29 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C71 [tests/test_komae_vertical_exploratory.py](../../../tests/test_komae_vertical_exploratory.py) | komae vertical exploratory regression / characterization | Test | In: none statically; Out: C09, C25, C27, C30 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C72 [tests/test_komae_vertical_provenance.py](../../../tests/test_komae_vertical_provenance.py) | komae vertical provenance regression / characterization | Test | In: none statically; Out: C09, C27, C31 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C73 [tests/test_meta_chmv2_acquisition.py](../../../tests/test_meta_chmv2_acquisition.py) | meta chmv2 acquisition regression / characterization | Test | In: none statically; Out: C10, C11, C51 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C74 [tests/test_plateau_building.py](../../../tests/test_plateau_building.py) | plateau building regression / characterization | Test | In: none statically; Out: C37, C38, C39 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C75 [tests/test_runtime.py](../../../tests/test_runtime.py) | runtime regression / characterization | Test | In: none statically; Out: C43 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C76 [tests/test_standard_building.py](../../../tests/test_standard_building.py) | standard building regression / characterization | Test | In: none statically; Out: C39, C44, C45, C47 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C77 [tests/test_standard_terrain.py](../../../tests/test_standard_terrain.py) | standard terrain regression / characterization | Test | In: none statically; Out: C41, C49, C52 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C78 [tests/test_study_area.py](../../../tests/test_study_area.py) | study area regression / characterization | Test | In: none statically; Out: C51 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C79 [tests/test_terrain_local_acceptance.py](../../../tests/test_terrain_local_acceptance.py) | terrain local acceptance regression / characterization | Test | In: none statically; Out: C09, C52 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C80 [tests/test_tokyo_tama_dem_acquisition.py](../../../tests/test_tokyo_tama_dem_acquisition.py) | tokyo tama dem acquisition regression / characterization | Test | In: none statically; Out: C10, C12, C41 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C81 [tests/test_voxcity_adapter.py](../../../tests/test_voxcity_adapter.py) | voxcity adapter regression / characterization | Test | In: none statically; Out: C14 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |
| C82 [tests/test_voxcity_post_crs_repair.py](../../../tests/test_voxcity_post_crs_repair.py) | voxcity post crs repair regression / characterization | Test | In: none statically; Out: C09, C13, C14, C24 | Imported targets are static references; synthetic tests do not establish real-data acceptance | KEEP |

### Windows helper launchers

These invoke existing workflows, not the new Phase 5 plan. No operational
script was executed by this audit; pytest exercises its covered contracts.

| Path | Invoked target / role | Current caller / duplication / reuse and impact | Action |
|---|---|---|---|
| [scripts/work/diagnose_komae_adapter_content.cmd](../../../scripts/work/diagnose_komae_adapter_content.cmd) | `ouem.komae_adapter_diagnostics` / Utility | Thin diagnostic launcher; do not fold accepted evidence transformation into runner | KEEP |
| [scripts/work/diagnose_komae_adapter_geometry_steps.cmd](../../../scripts/work/diagnose_komae_adapter_geometry_steps.cmd) | `ouem.komae_adapter_geometry_steps` / Utility | Thin diagnostic launcher; do not fold accepted evidence transformation into runner | KEEP |
| [scripts/work/diagnose_komae_building_heights.cmd](../../../scripts/work/diagnose_komae_building_heights.cmd) | `ouem.komae_height_diagnostics` / Utility | Thin diagnostic launcher; do not fold accepted evidence transformation into runner | KEEP |
| [scripts/work/diagnose_komae_dem_coverage.cmd](../../../scripts/work/diagnose_komae_dem_coverage.cmd) | `scripts/work/diagnose_komae_dem_coverage.py` / Utility | Thin diagnostic launcher; do not fold accepted evidence transformation into runner | KEEP |
| [scripts/work/diagnose_komae_geometry_provenance.cmd](../../../scripts/work/diagnose_komae_geometry_provenance.cmd) | `ouem.komae_geometry_provenance` / Utility | Thin diagnostic launcher; do not fold accepted evidence transformation into runner | KEEP |
| [scripts/work/diagnose_komae_vertical_exploratory.cmd](../../../scripts/work/diagnose_komae_vertical_exploratory.cmd) | `ouem.komae_vertical_exploratory` / Utility | Thin diagnostic launcher; do not fold accepted evidence transformation into runner | KEEP |
| [scripts/work/evaluate_komae_adapter_crs_repairs.cmd](../../../scripts/work/evaluate_komae_adapter_crs_repairs.cmd) | `ouem.komae_crs_repair_evaluation` / Utility | Thin diagnostic launcher; do not fold accepted evidence transformation into runner | KEEP |
| [scripts/work/export_komae_adapter_repair_qgis.cmd](../../../scripts/work/export_komae_adapter_repair_qgis.cmd) | `ouem.komae_repair_qgis_export` / Utility | Thin diagnostic launcher; do not fold accepted evidence transformation into runner | KEEP |
| [scripts/work/export_komae_canopy_qgis.cmd](../../../scripts/work/export_komae_canopy_qgis.cmd) | `ouem.komae_canopy_qgis_export` / Utility | Legacy canopy experiment/schema, not Height Envelope Phase 2-4 route; preserve old replay | FREEZE |
| [scripts/work/plateau_komae_local_acceptance.cmd](../../../scripts/work/plateau_komae_local_acceptance.cmd) | `ouem.native.building.plateau`, `ouem.standardize.building` / Utility | Operational helper; see scripts/work/README.md; preserve arguments/runtime boundary | KEEP |
| [scripts/work/preflight_komae.cmd](../../../scripts/work/preflight_komae.cmd) | `ouem.komae_integration` / Utility | Operational helper; see scripts/work/README.md; preserve arguments/runtime boundary | KEEP |
| [scripts/work/run_komae_contained_e2e.cmd](../../../scripts/work/run_komae_contained_e2e.cmd) | `ouem.komae_integration` / Utility | Same integration CLI as sibling but different run-ID validation/error handling; no line-count-only removal | REFACTOR CANDIDATE |
| [scripts/work/run_komae_contained_poc.cmd](../../../scripts/work/run_komae_contained_poc.cmd) | `ouem.komae_integration` / Utility | Same integration CLI as sibling but different run-ID validation/error handling; no line-count-only removal | REFACTOR CANDIDATE |
| [scripts/work/run_komae_meta_chm_e2e.cmd](../../../scripts/work/run_komae_meta_chm_e2e.cmd) | `ouem.komae_integration` / Utility | Legacy canopy experiment/schema, not Height Envelope Phase 2-4 route; preserve old replay | FREEZE |
| [scripts/work/terrain_komae_local_acceptance.cmd](../../../scripts/work/terrain_komae_local_acceptance.cmd) | `ouem.terrain_local_acceptance` / Utility | Operational helper; see scripts/work/README.md; preserve arguments/runtime boundary | KEEP |

### Non-Python configuration and compatibility boundaries

- [pyproject.toml](../../../pyproject.toml): five console scripts bind the formal
  Building/Terrain/Adapter package mains; pin remains unchanged. Canopy experiment
  CLIs use python -m and have no console-script promotion.
- [Komae YAML](../../../config/study_areas/komae_09LD3451.yaml): authoritative
  study extent/CRS, not automatic equivalence with VoxCity geodesic raster cells.
- `.gitignore` and local `data/work` receipts separate experiments from Git;
  ignored local copies/snapshots are not extra reusable modules to merge.

### Code consolidation candidates (not changes)

- **Preserve independent protocols:** build_pair vs build_isotropic, geometry
  checks, fixed-1m crop vs size-preserving wrapper, and scalar observer variants
  differ in audited behavior. Freeze Phase 2/3; a new Phase 5 module must not
  rewrite those byte-bound experiments to reduce apparent duplication.
- **Potential shared utility later:** pin/RECORD verification currently lives in
  broad komae_integration; hashing, metadata and guarded output publication occur
  across acquisition/Height Envelope. Extract only through versioned interfaces,
  retained old entry points and reproduction checks. Changes can affect module
  hashes, manifest fingerprints, newline-byte identity and test monkeypatches.
- **Launcher consolidation later:** contained_poc and contained_e2e share target
  arguments but have different Windows validation/security behavior. A deliberate
  wrapper consolidation needs compatibility tests, not deleting the older name.
- **No REMOVE CANDIDATE presently justified:** ID11/ID37 scripts look isolated in
  AST imports but are cited by the formal A3 record; marker packages are intended
  namespace boundaries. Retain those until a separately reviewed evidence audit.

## Audit additions and navigation

Only these three new documents are submitted: Gate review (decision/evidence),
this inventory (all roles/reference edges/candidates), and Phase 5 plan (required
implementation/acceptance gates). Their links form the new audit index; baseline
records are not edited to pretend these links always existed. A future root
README index is a separate, small follow-up after review.
