# B1 Closeout Repository Housekeeping Audit

Static audit, **2026-10-30**, main `53c5067d72c62631fdbfd949077faedaab604316`
(PR #121 merged). Apply [P3/P4/P5/P6](../OUEM_Development_Principles_v0.1.md).
Conclusion: **update current navigation; retain runtime code/tests/evidence. No
source refactor, deletion or move is needed for the B1 technical closeout.**
Scientific work is deferred in the [backlog](OUEM_B1_Deferred_Validation_Backlog.md);
the [milestone summary](../status/B1_TECHNICAL_MILESTONE_CLOSEOUT.md) is not formal acceptance.

## 1. Inventory and method

`git ls-tree -r -l origin/main` supplies tracked blob counts/sizes at the baseline,
not local working-tree allocation or full Git-history size. Static AST imports,
Python/CMD entries, subprocess/runpy/dynamic import references, tests, docs,
config and CI were inspected. Filename search supports, but does not establish,
an unused-code conclusion. No model/engine, dataset regeneration or cleanup ran.

| Baseline area | Tracked files | Blob bytes | Role |
|---|---:|---:|---|
| Root | 5 | 15,740 | README, AGENTS, package metadata, ignore rules, license placeholder |
| `.github` | 1 | 555 | Windows/Ubuntu Python 3.12 full pytest workflow |
| `config` | 2 | 1,690 | Study Area YAML and experimental E2E JSON example |
| `data` | 15 | 3 | Directory markers only; actual local data/results ignored |
| `docs` | 80 | 1,920,845 | Contracts, concepts, planning, status, reviews, experiments and verification |
| `experiments` | 1 | 3,425 | Original Building pilot/acceptance evidence |
| `scripts` | 24 | 111,735 | Directory marker plus work README, 8 Python and 14 CMD helpers |
| `src/ouem` | 66 | 732,656 | Source/contract/provider/runner/diagnostic namespaces and logic |
| `tests` | 58 | 560,349 | 55 Python files, small fixture/marker assets |
| **Total** | **252** | **3,346,998** | **129 Python files** across source/tests/scripts |

Docs include 34 experiment assets, 7 planning docs, 5 acceptance records, 5
reviews, 2 status docs and the other reference/verification/development owners.
These are baseline counts; this PR adds the three requested Markdown owners,
not duplicate inventories or binary evidence. Detailed CSV/AST/reference/link
outputs stay ignored under
`data/work/repository-cleanup-audit/b1-closeout-20261030-01/`.

The pre-change local Markdown scan found **863 links with no missing local
targets/heading fragments**; 139 external links were not network-checked.
Code fences were excluded, heading slugs checked; this is a bounded scanner,
not a complete Markdown renderer or external URL availability guarantee.
The final post-change check and actual changed-file scope are recorded below.

### Large/generated asset check

No tracked file is ≥1 MiB. Largest is the **405,213-byte** documented Height
Envelope verification PNG. The three tracked PNGs (that image plus earlier
canopy-only Phase 2/3 figures) are cited experiment evidence. The **23,554-byte**
`tests/fixtures/plateau_converter/two_buildings.gml` is a deliberate regression
fixture. No tracked NPY/NPZ, GeoTIFF, GeoPackage, QGZ, ZIP, bytecode, log or
temporary output was found. No large Git-history scan or cleanup was attempted.
Historical evidence images are retained, not classed as accidental outputs.

`.gitignore` excludes data lifecycle/work outputs, venv/caches, runtime snapshots,
secrets and common large GIS files. QGZ/QML/JSON are not globally excluded, so
keep generated projects/styles under ignored work directories and inspect staged
files. No new ignore pattern, fixture untracking or local deletion is warranted.

## 2. Classification and action

**対応必須 / Required** = stale current entry or misleading boundary to correct
in this PR. **対応推奨 / Recommended** = useful documented maintenance, not a new
completion gate. **現状維持 / Retain** = needed current/reproduction asset.
**将来検討 / Future review** = separate decision when a concrete need appears.

| Class / target | Evidence, dependency and risk | Decision |
|---|---|---|
| **Required — root README** | Current milestone emphasized v0.2; generation-only NOT_VERIFIED could hide separately completed QGIS 4.2.3 helper/QGZ GUI evidence. Module table lacked GIS helper/project and geometry-diagnostic owners. | Link technical closeout/backlog/current owners, distinguish receipt status from independent display checks, state B2 unimplemented. Keep detailed procedures/results at existing owners. |
| **Required — Building/Canopy Current State** | Last checked PR #99. Canopy's base equality omitted added upper AIR; "common D0/observations" needed a within-pair qualifier after PR #121 cross-domain diagnosis. Reproduction still foregrounded original PR #99. | Refresh date/full main commit and current links; correct shared-Z/pair wording, route to configured procedure. Do not edit old results, source-H eligibility, Standard or Gate status. |
| **Recommended — work Runbook entry** | Accepted/legacy commands coexist with current configured B1/GIS instructions elsewhere. File is still operational, not disposable. | Add only a short route to closeout; preserve all existing CLI commands, safety conditions, anchors and historical fixed-commit references. |
| **Retain — contracts, Concept and Acceptance** | Formal/provisional/draft roles and history already explicit. Phase A design has a current-status note; Concept v0.2 retains v0.1 B2 detail. | No content/status change. Documentation Governance stays proposed; AGENTS and adopted Principles remain sufficient and concise. |
| **Retain — PR #97–121 reports/plans and earlier canopy/vertical records** | Original PoC, B failure, shared-Z completion, provider warp, helper GUI and later QGZ completion are date-scoped observations. Older "not yet" text can be correct for its baseline. | Preserve historical reports. New navigation explains succession; do not replace dates/hashes/results or apply old failure labels to newer runs. |
| **Recommended, later — long Solar guide** | It owns current commands plus successive historical GIS investigations; apparent NOT_VERIFIED statements occur before later explicitly scoped GUI/QGZ records. | Current closeout provides latest evidence links. If navigation becomes hard, add an in-file contents/current-summary entry, preserving anchors and chronology; no new parallel runbook or split now. |
| **Future review — small utility ownership** | `e2e_config`/Voxel/Solar import `write/distribution/digest` through Building runner/standardizer; engine metadata helpers live in broad `komae_integration`. Diagnostic reader reuses `gis_visualization.inspect_run`. | Follow [PR #110 audit](OUEM_E2E_Reuse_Audit_v0.1.md#final-refactoring-audit--v02-completion) only when a real B2/shared-helper change needs it. A move changes watched implementation identities; preserve old bytes/import compatibility and test freshness/receipts. No neutral framework or extraction now. |
| **Future review — exporter/reader overlap** | Geographic affine and saved-array readback appear in Voxel, Solar and downstream checks. Independent hashes/oracles have a different trust purpose from serialization. | Extract only a demonstrated shared primitive when changing its owner; retain independent validation, mask policies and scalar-vs-engine checks. No wholesale deduplication. |
| **Future review — historical dataset-specific diagnostics and probes** | Three standalone ID scripts have no static inbound code/test reference but still have direct CLI behavior and frozen A3 citations; two Converter/GDAL probes have their own tests/docs. Missing static callers alone is not removal evidence. | No delete candidate is proven safe. See script review below; inventory old environments, CLI semantics, external users and evidence preservation before a separate retirement PR. |
| **Retain — source-H synthetic and legacy canopy regressions** | Their tests independently cover ingestion, coordinates/H, pin/ground/ID and sensitivity/orientation behavior. Some earlier helpers remain imported by later tests. | A newer real-run success does not replace these tests. No experimental-test purge or fixture centralization. |
| **Retain — config and ignored evidence** | Strict RunConfig and Study Area are distinct; saved run copies/receipts fix mutable external-config loss. Actual centres/relative topology govern GIS reuse. | No schema/config/path rewrite. Preserve submitted settings and input/output hashes; missing local files must not be inferred from a prior PASS. |
| **Future review — distribution/license decision** | Root LICENSE explicitly says no OUEM license selected; upstream VoxCity and data provenance are separate. | Retain existing statement; selection needs the user's explicit decision, not a housekeeping edit. |

## 3. Script dependency and retirement review

All **22 executable work helpers** were considered. They are not the current
configured B1 entry point; that lives in `src/ouem` with documented `python -m`
CLIs. Python wrappers are not automatically unnecessary: argument handling,
cwd/runtime boundaries and subprocess exit propagation are observable behavior.

| Helpers (under `scripts/work/`) | Actual owner / references / tests | Class and loss/risk if removed |
|---|---|---|
| `capture_gis_runtime.py`, `gis_runtime_check.py`, `ouem_runtime_check.py` | Called by `plateau_komae_local_acceptance.cmd`; runtime/acceptance Runbook; separate GIS/OUEM processes | **Retain**. Removing loses explicit runtime checks/capture; no equivalent proven replacement. |
| `plateau_komae_local_acceptance.cmd`, `terrain_komae_local_acceptance.cmd` | Native/Standard acceptance modules; `test_plateau_building`, `test_standard_terrain`, `test_terrain_local_acceptance`; Building/Terrain records | **Retain** accepted-path execution/validation and Windows quoting/exit behavior. |
| `voxcity_komae_a3_acceptance.py` | `komae_integration.A3_SCRIPT` subprocess; `komae_canopy_qgis_export` command validation; adapter/canopy tests use read/runpy | **Retain**. Live runtime dependency and recorded A3 oracle, despite historical name; removal breaks current legacy callers and tests. |
| `preflight_komae.cmd`, `run_komae_contained_poc.cmd`, `run_komae_contained_e2e.cmd`, `run_komae_meta_chm_e2e.cmd` | `komae_preflight`, `komae_contained`, `komae_integration`, `komae_canopy`; associated module/launcher tests and Runbook | **Retain** separate accepted/contained/older-CHM lanes. No direct filename test found for preflight launcher, but it has manual documented CLI use; not deletion proof. |
| `diagnose_komae_adapter_content.cmd`, `diagnose_komae_adapter_geometry_steps.cmd`, `diagnose_komae_building_heights.cmd`, `diagnose_komae_geometry_provenance.cmd`, `diagnose_komae_vertical_exploratory.cmd`, `evaluate_komae_adapter_crs_repairs.cmd` | Corresponding `komae_adapter_diagnostics`, `komae_adapter_geometry_steps`, `komae_height_diagnostics`, `komae_geometry_provenance`, `komae_vertical_exploratory`, `komae_crs_repair_evaluation`; dedicated tests inspect/execute launchers | **Future review** of wrapper consolidation only. Direct module CLIs are candidate alternatives, but cwd, arity, quoting, venv selection and exit propagation must be preserved/tested before removal. |
| `export_komae_adapter_repair_qgis.cmd`, `export_komae_canopy_qgis.cmd` | Same-named export modules, dedicated tests and Runbook | **Retain / future wrapper review**. Different historical vector/inspection semantics from current Solar TIFF/QGZ; not superseded merely by `gis_project`. |
| `diagnose_komae_dem_coverage.py` | Independent coverage oracle; `test_komae_contained.py:176` loads by file path; Runbook direct Python command | **Retain**. Its CMD was already removed in Step 1; Python diagnostic has no complete equivalent replacement. Do not repeat that deletion or lose independent boundary classification. |
| `diagnose_voxcity_building_ids.py`, `diagnose_voxcity_id11.py`, `diagnose_voxcity_id37_overlap.py` | Manual `main` entry points replay pinned A3 internals with fixed dataset IDs/overlap settings; named in A3 acceptance record and 20261027 inventory; no direct automated test or inbound runtime reference found | **Future review**, not immediate deletion. Would lose historical ID/overlap investigative mechanisms and external/manual command compatibility; verify a replacement or explicit historical preservation plan, not just Git history. |

The prior local PR #100/102 audit copies still exist under
`data/work/repository-cleanup-audit/`. Their shared Draft-only `docs/maintenance/`
files are **not on this main**; no merge or permanent classification is assumed.
The five old ARCHIVE suggestions were rechecked: the three ID scripts above plus
[`gdal_citygml_feasibility`](../../src/ouem/gdal_citygml_feasibility.py) and
[`plateau_converter_probe`](../../src/ouem/plateau_converter_probe.py).
The latter retain `test_gdal_citygml_feasibility.py` /
`test_plateau_converter_probe.py`, standalone entry points and source-investigation
records. They are not imported by the current configured E2E for simulation,
but their historical validation function has not been shown replaceable.

## 4. B2 reuse and regression boundary

| Existing owner | Candidate reuse / limitation | Protect when later changing |
|---|---|---|
| `study_area`, `e2e_config` | Extent/input identity and frozen handoff patterns; existing schema is Voxel/Solar-specific, not automatically B2 configuration | `test_study_area`, `test_e2e_config`; no silent new config keys |
| Source-H Consumer / `Watch`, source geometry and adapter pure helpers | Path/hash/CRS/H/ID validation and footprint derivation | Source-H/accepted-contract tests, independent geometry readers; do not expand v0.1 whitelist |
| `height_envelope`, saved Voxel/Solar grid/classes | Existing geometry, source sampling/masks, IDs, centres/D0 and shared Z | Envelope/presence, real Voxel/Solar/shared-Z, synthetic physics and geometry diagnostics; B2 viewpoint/metric semantics still require design |
| `gis_visualization.inspect_run`, `gis_display`, `gis_project` | Read-only integrity, exact-cell and isolated GIS process/style patterns | GIS tests, alpha/CRS/affine/NoData/reopen behavior; current manifest/layers/units are B1-specific, not a B2 result contract |
| `AGENTS`, Principles, runtime architecture and CI | On-demand owners, smallest sufficient change, pinned engine and isolated GIS runtime | CI full suite on Windows/Ubuntu 3.12; local Windows/QGIS evidence is separate from CI and field validation |

`native/canopy`, `standardize/canopy`, `model/{building,terrain,canopy}` and other
docstring-only namespaces are scaffolds, not unused implementations or B2
algorithms. No B2 runner/config/tests were found in source. OpenEarthMap/land-cover
ideas do not become current observed land cover; minimal bareland in voxel runs
remains an unobserved modeling input. No new abstraction/placeholder removal is
justified merely by planning B2.

## 5. Scope, validation and next maintenance

This PR adds three purpose-specific Markdown owners (technical status, deferred
science and this maintenance audit), updates root README/two Current States, and
adds one Runbook route. **No Python, test, CMD, config, dependency, contract,
Acceptance, Gate, historical RESULT/verification record or existing data artifact
is changed, moved or deleted.** Whole-repository source/test ownership and runtime
paths remain intact. Current local A/B snapshot/receipt/voxel/observer/solar files,
QGZs and recent diagnostic evidence were checked for presence only; no fresh
simulation, Consumer, byte rehash, GUI or scientific validation is claimed.

Static results and full tracked-file inventory are in ignored `inventory.json`,
`tracked-files.csv`, `static_inventory.py` and `availability.json` under the
audit directory above. Post-change scan: **919 local links, zero missing or
case-mismatched tracked targets/heading fragments**; the same 139 external URLs
were not network-checked. `validation.json` records the scan and comparison of
141 protected source/test/config/acceptance/policy files (LF-normalized text),
all unchanged. `git diff --check` passes; the diff contains **seven Markdown
files only**, three added and four updated (proposed tracked total: 255).

| Updated entry | Lines before → after | Characters before → after (LF normalized) |
|---|---|---|
| Root README | 140 → 151 | 9,918 → 10,940 |
| Building Current State | 88 → 91 | 5,742 → 5,988 |
| Canopy Current State | 84 → 92 | 5,364 → 6,081 |
| Work Runbook | 848 → 852 | 48,967 → 49,180 |

No pytest/model was run: documentation-only changes, no import/runtime or CLI
modification. Prior PR #121 tests remain dated evidence, not this PR's test run.

No follow-up code cleanup is a prerequisite for B2 planning. If later needed,
first consider one bounded utility-ownership or wrapper-equivalence PR from the
rows above: enumerate callers and independent tests, preserve implementation
snapshots/old hashes, test failure/receipt/Windows quoting behavior and run the
full suite. Keep physics, scientific definitions, data contracts and broader
retirement decisions in separately authorized work. No deletion is recommended
on the basis of a missing string reference or the existence of Git history.
