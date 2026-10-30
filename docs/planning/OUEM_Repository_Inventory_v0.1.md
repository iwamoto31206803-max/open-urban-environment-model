# OUEM Repository Inventory v0.1

Checked **2026-10-30**, main **`19368049831e43a4c5fb3149824ae0533dcee3db`**
([PR #126](https://github.com/iwamoto31206803-max/open-urban-environment-model/pull/126)
merged, confirmed through GitHub and fetched Git). Status: **read-only inventory**.
The [Cleanup Plan](OUEM_Repository_Cleanup_Plan_v0.1.md) proposes separate future
PRs; neither document authorizes cleanup, scientific changes or new execution.
Only these two new documents are added. Counts below describe the baseline,
excluding the two additions, ignored local data, `.git` history and caches.

## Method and authority

The inventory uses `git ls-files`, `git ls-tree -r -l`, AST parsing of tracked
Python, `rg`, CLI declarations, batch contents, tests, Markdown links, CI YAML
and installed distribution metadata. It does not import project modules or
execute their CLIs. AST edges include absolute/relative imports and local imports
inside functions; file-path loads, runpy and subprocess routes were separately
read. These establish recorded references, not an exhaustive runtime call graph.
No pytest, acquisition, simulator, GIS subprocess or GUI was run. No ignored-data
tree census, full historical blob audit, secret scan or external URL check is
claimed. Unknown external/dynamic use remains Unknown, never “unused.”

Owners reviewed: [AGENTS](../../AGENTS.md),
[Development Principles](../OUEM_Development_Principles_v0.1.md),
[README](../../README.md), [Concept v0.2](../OUEM_Concept_Architecture_v0.2.md),
[Phase A design/current-status note](../Phase_A_Implementation_Design_v0.1.md),
[runtime architecture](../architecture.md), [processing model](../processing_model.md),
[work runbook](../../scripts/work/README.md),
[proposed documentation governance](../OUEM_Documentation_Governance_v0.1.md),
[B1 closeout](../status/B1_TECHNICAL_MILESTONE_CLOSEOUT.md),
[B2 closeout](../status/B2_TECHNICAL_MILESTONE_CLOSEOUT.md), and the
[B1](OUEM_B1_Deferred_Validation_Backlog.md) /
[B2](OUEM_B2_Deferred_Validation_Backlog.md) deferred backlogs.
The [20261027 inventory](../experiments/voxcity_canopy_shadow/REPOSITORY_INVENTORY_20261027.md)
and [B1 housekeeping audit](OUEM_B1_Closeout_Housekeeping_Audit_20261030.md)
remain their dated records; this is the post-B2 repository-wide baseline.
Technical closeout is not scientific validation or Formal Acceptance. Existing
contract, Acceptance and backlog states are not changed or reevaluated here.

## Tracked size and structure

Git blob bytes, not Windows working-copy bytes (which may have CRLF), disk
allocation or Git history size:

| Area | Files | Blob bytes | Structure / contents |
|---|---:|---:|---|
| Root | 5 | 17,631 | `.gitignore`, `AGENTS.md`, `LICENSE`, `README.md`, `pyproject.toml` |
| `.github/` | 1 | 555 | One `workflows/pytest.yml` |
| `config/` | 2 | 1,690 | One study-area YAML; one experimental RunConfig JSON |
| `data/` | 15 | 3 | `.gitkeep` markers only |
| `docs/` | 90 | 2,045,438 | 82 Markdown, 5 JSON evidence/handoff, 3 PNG evidence |
| `experiments/` | 1 | 3,425 | `a1_e2e_pilot/README.md`, original Building acceptance owner |
| `scripts/` | 24 | 111,948 | Root marker; `work/` README, 8 Python, 14 CMD |
| `src/ouem/` | 68 | 764,560 | All Python; 17 `__init__.py`, including both real implementations and scaffolding |
| `tests/` | 61 | 585,427 | 53 top-level test Python files, 5 integration Python files, 3 fixture assets |
| **Total** | **267** | **3,530,677** | **134 Python files** across source/tests/scripts |

Source subtrees: 33 files directly in `src/ouem/`, `acquire/` 3,
`adapters/` 5, `consumers/` 3, `model/` 4, `native/` 11, `standardize/` 9.
Docs: 21 direct references, `acceptance/` 5, `development/` 1,
`experiments/` 37, `local_handoff/` 1, `planning/` 12, `research/` 2,
`reviews/` 5, `status/` 4, `verification/` 2. The four status owners are
Building, Canopy and the two B1/B2 closeouts. Directory location alone does not
determine authority or whether an experiment is still used.

## Classification and source responsibilities

Primary role and proposed treatment are separate dimensions. **Core / Active**
does not mean universally accepted; **Experimental / Active** includes retained,
tested compatibility paths. **Diagnostic / Utility** can have live production
callers. **Historical / Evidence** means preserve the record. **Candidate for
Consolidation** and **Candidate for Retirement** are review overlays, not actions.
**Unknown** labels the unresolved dependency/use aspect even when the file's
original role is documented. All candidates map to plan IDs C01–C09 below.

Paths in this table are under `src/ouem/` unless otherwise stated. The named
groups cover the major source responsibilities, including compatibility paths.

| Primary role / group | Files and responsibility | Evidence of references / dependencies; treatment |
|---|---|---|
| Core / Active: runtime and area | [runtime.py](../../src/ouem/runtime.py), [study_area.py](../../src/ouem/study_area.py) | `komae_integration`, acquisition/Height Envelope/Standardizers and `test_runtime` / `test_study_area` use them. Runtime leak detection and deliberately limited YAML parsing are explicit behavior; do not replace them as cosmetic cleanup. |
| Core / Active: accepted Building ingestion | `native/building/plateau.py`, `_plateau_gdal_worker.py`, namespace `__init__.py` | Console/module CLI and PLATEAU CMD; `standardize.building` imports GIS runtime/decoding helpers from `plateau`; `test_plateau_building` and `test_standard_building` cover the workers. Worker execution is by file path in a GIS child, not an ordinary import-only graph. |
| Core / Active: accepted Building/Adapter | `standardize/building/__init__.py`, `__main__.py`, `_gdal_worker.py`; `adapters/voxcity/__init__.py`, `__main__.py` | Five-console-entry table below; [Building](../OUEM_Standard_Building_v0.1.md) / [Adapter](../OUEM_VoxCity_Adapter_v0.1.md) owners and pilot/A3 records. Source-H adapters/diagnostics reuse selected ID/geometry functions, without extending the accepted manifest whitelist. Preserve boundaries. |
| Core / Active: Terrain path | `native/terrain/` and `standardize/terrain/` implementations/dispatchers; `terrain_local_acceptance.py` | Console CLIs, `terrain_komae_local_acceptance.cmd`, `test_standard_terrain` / `test_terrain_local_acceptance`, [Terrain contract](../OUEM_Standard_Terrain_v0.1.md). Native SHA helper is also imported by broader integration code. |
| Experimental / Active: acquisition and raster Envelope | `acquire/meta_chmv2.py`, `acquire/tokyo_tama_dem.py`, [height_envelope.py](../../src/ouem/height_envelope.py) | Documented acquisition/Envelope module CLIs, `test_meta_chmv2_acquisition`, `test_tokyo_tama_dem_acquisition`, `test_height_envelope`, presence tests; B1 Solar imports Envelope sampling. HAG provenance, source coverage and masks must not be merged into generic “vegetation present” flags. |
| Experimental / Active: source-H chain | `native/building/provenance.py`, `source_h.py`, `source_h_geometry.py`, `source_h_lod2.py`; `standardize/building/source_h.py`, `source_h_geometry.py`; `consumers/source_h_standard.py`, `_source_h_geometry.py` | `real_komae_source_h`, Voxel/Solar, synthetic adapters and source-H tests import these owners. `Watch` is reused by B2/GIS. Independent WKB/consumer checks are intentional trust boundaries, not automatically duplicate work. Source-H eligibility remains NOT_ESTABLISHED. |
| Experimental / Active: synthetic source-H/engine controls | `adapters/source_h_synthetic.py`, `source_h_synthetic_voxel.py`, `synthetic_building_solar.py` | `test_source_h_synthetic_25d`, `test_source_h_synthetic_voxel`, `test_synthetic_building_solar`, documented opt-in integration scripts. Real A/B execution does not replace these synthetic controls. |
| Experimental / Active: configured B1 | [e2e_config.py](../../src/ouem/e2e_config.py), `real_komae_source_h.py`, `real_komae_voxel.py`, `real_komae_solar.py` | README/config JSON/real source-H→Voxel→Solar guides, respective tests, shared-Z and configuration tests. Configuration uses `real_komae_source_h.digest/write`; Voxel/Solar also import its distribution helper and `komae_integration.environment/voxcity_provenance`. C03/C04 ownership candidates, not dead modules. |
| Experimental / Active: legacy contained/CHM lane | [komae_integration.py](../../src/ouem/komae_integration.py), `komae_contained.py`, `komae_preflight.py`, `komae_canopy.py` | Runbook/CMD workflows, `test_komae_integration`, `test_komae_repair_acceptance`, `test_komae_canopy`; delayed imports between integration/contained/preflight. Numerous diagnostics and B1/B2 still import the integration module. C03/C05; wholesale removal would break known paths. |
| Experimental / Active: earlier canopy controls | `canopy_shadow_poc.py`, `canopy_shadow_sensitivity.py` | Their tests plus `test_canopy_observer_geometry` / `test_canopy_presence_semantics`, and the canopy experiment index. Earlier standalone cases remain independently useful; not superseded merely by later Building+Terrain real runs. |
| Experimental / Active: B2 | [b2_gvi.py](../../src/ouem/b2_gvi.py) | B2 guide/closeout and `test_b2_gvi`; imports `Watch`, B1-specific `gis_visualization.inspect_run`, and integration metadata helpers. Explicitly consumes completed B1 runs; this is not already a general Voxel-only/B2 reader. |
| Diagnostic / Utility: saved-result GIS and geometry | `gis_visualization.py`, `gis_display.py`, `gis_project.py`, `b2_gvi_qgis.py`, `b1_geometry_diagnostics.py` | README/guides, same-purpose tests. `inspect_run` is called by B1 geometry diagnostics and B2. `gis_project` loads `gis_display.py` by file path; standalone GIS tests also load files. B1 seven-layer and B2 eight-layer A/B presentation contracts differ. C07; dynamic/external use remains U02. |
| Diagnostic / Utility: Komae investigation/export | `komae_adapter_diagnostics.py`, `komae_adapter_geometry_steps.py`, `komae_crs_repair_evaluation.py`, `komae_geometry_provenance.py`, `komae_height_diagnostics.py`, `komae_vertical_provenance.py`, `komae_vertical_exploratory.py`, `komae_repair_qgis_export.py`, `komae_canopy_qgis_export.py` | Corresponding tests, runbook/CMD entries and cross-imports: geometry provenance is reused by several diagnostics; canopy export reuses repair export. These inspect/export different historical products, not replacements for current Solar/B2 rasters. C05/C06 only after contract review. |
| Diagnostic / Utility: external feasibility probes | `plateau_converter_probe.py`, `gdal_citygml_feasibility.py` | Dedicated tests; Converter audit/experimental records and source-H integration smoke reference them. These can inspect/build/use external tools under opt-in conditions. No probe was executed here; they are not proven retirement candidates. |
| Core / Active: namespace scaffolding | Root/acquire/adapters/native/standardize/consumers namespace files; `model/{__init__,building/__init__,canopy/__init__,terrain/__init__}.py`, `native/canopy/__init__.py`, `standardize/canopy/__init__.py` | Thirteen one-line source namespace files remain. `tests/test_import.py` explicitly dynamically imports the Phase A names. Model/Canopy placeholders do not establish implemented Canopy lifecycle or alternative analysis runners, but are not automatically disposable empty files. |

### Entry points and runtime crossings

[pyproject.toml](../../pyproject.toml) declares these exact console mappings:

| Installed command | Owner |
|---|---|
| `ouem-plateau-buildings` | `ouem.native.building.plateau:main` |
| `ouem-standardize-buildings` | `ouem.standardize.building:main` |
| `ouem-accept-terrain` | `ouem.native.terrain:main` |
| `ouem-standardize-terrain` | `ouem.standardize.terrain:main` |
| `ouem-adapt-voxcity` | `ouem.adapters.voxcity:main` |

Module CLIs also include `ouem.acquire.*`, `ouem.height_envelope`,
`ouem.komae_integration` (preflight/run), `ouem.real_komae_*`,
`ouem.gis_visualization`, `ouem.b2_gvi` and the diagnostic modules listed above.
They run in ordinary Windows `.venv/Scripts/python.exe` (`.venv/bin/python`
for authorized Cloud work). The GIS-only files `gis_display.py`, `gis_project.py`
and `b2_gvi_qgis.py` are documented as direct files under **existing GIS Python**,
without installing OUEM into it. Native/Standard Building workers receive job
and result JSON through a separate GIS subprocess. A local console load is not
visible as a normal import caller.

AST found 34 source `if __name__ == '__main__'` guards, 8 in work Python scripts
and 7 in tests. Four additional package `__main__.py` dispatchers contain a
three-line call-through. This is syntactic entry information, not a count of
public supported CLIs: it also includes workers and opt-in test tools.

Key dependency paths read from source, not executed:

```text
accepted Building CLI -> GISRuntime -> _plateau_gdal_worker.py (GIS child)
Standard Building CLI -> same runtime helpers -> _gdal_worker.py (GIS child)
contained run -> komae_integration -> scripts/work/voxcity_komae_a3_acceptance.py
configured B1 -> e2e_config + source-H Consumer -> real_komae_voxel -> real_komae_solar
B2 -> saved B1 inspect_run + Watch -> public VoxCity CPU generic -> own rasters
Solar QGZ / B2 QGZ -> separate GIS Python -> referenced original rasters
```

Here `komae_integration.A3_SCRIPT` is a literal live path, used in its subprocess
command and input fingerprint set. A module move or script replacement affects
both execution and provenance. Import aliases alone cannot preserve an old
file's byte hash. The producer/consumer/synthetic expected-value independence
is a separate dependency to protect, beyond the Python graph.

## Work scripts: all 22 executable helpers

The work README (852 physical lines) is an active accepted/legacy operations
owner with a current closeout route, not just an archive. `scripts/.gitkeep` is
the other tracked script-tree marker. Table paths are under `scripts/work/`.

| Helpers | Classification / evidence | Uncertainty or cleanup implication |
|---|---|---|
| `plateau_komae_local_acceptance.cmd`, `terrain_komae_local_acceptance.cmd` | Core / Active operations; runbook, accepted Building/Terrain records and `test_plateau_building`, `test_standard_terrain`, `test_terrain_local_acceptance` inspect behavior. | Runtime contamination checks, quoting, cwd and exit propagation are observable contracts; retain. |
| `capture_gis_runtime.py`, `gis_runtime_check.py`, `ouem_runtime_check.py` | Diagnostic / Utility, active; called by the PLATEAU CMD and documented runtime capture/check steps. | Generated `.runtime/` snapshot is ignored, not interchangeable with these tracked helper sources. U03/U04. |
| `voxcity_komae_a3_acceptance.py` | Experimental / Active execution dependency and historical A3 oracle; integration subprocess, canopy export command checks, `runpy.run_path` in `test_voxcity_adapter` / `test_komae_canopy`. | 376 lines of engine/grid/ID checking live outside `src`; C05 is a high-risk location/ownership candidate, not a deletion. |
| `preflight_komae.cmd`, `run_komae_contained_poc.cmd`, `run_komae_contained_e2e.cmd`, `run_komae_meta_chm_e2e.cmd` | Experimental / Active compatibility/operations; dispatch to integration preflight/run flags; runbook and contained/repair/canopy tests. | No direct filename test was found for preflight CMD, but it has documented manual use. Fresh external invocation remains U03. |
| `diagnose_komae_adapter_content.cmd`, `diagnose_komae_adapter_geometry_steps.cmd`, `diagnose_komae_building_heights.cmd`, `diagnose_komae_geometry_provenance.cmd`, `diagnose_komae_vertical_exploratory.cmd`, `evaluate_komae_adapter_crs_repairs.cmd` | Diagnostic / Utility; matching module CLIs, tests and runbook sections. | Candidate for Consolidation C06 only after distinguishing extra argument validation, env handling, cwd/quoting and status semantics. Repeated wrapper shape is not proof of interchangeable behavior. |
| `export_komae_adapter_repair_qgis.cmd`, `export_komae_canopy_qgis.cmd` | Diagnostic / Utility; corresponding export modules/tests/runbook. | Historical vector/inspection exports differ from current raster/QGZ products. Current GIS helper does not prove either exporter obsolete. |
| `diagnose_komae_dem_coverage.py` | Diagnostic / Utility; runbook and file-path load in `test_komae_contained`. | Independent coverage oracle; retain. A normal import-only scan would miss its test reference. |
| `diagnose_voxcity_building_ids.py`, `diagnose_voxcity_id11.py`, `diagnose_voxcity_id37_overlap.py` | Historical / Evidence + Diagnostic; original A3 acceptance and prior inventories cite them; direct argparse CLIs, accepted Standard defaults, fixed IDs/overlap conditions. | **Unknown current external/manual use (U01)**. Conditional Candidate for Retirement **review** C06: narrow/temporary historical purpose, no tracked automated caller found. No safe retirement is established; retain sources/citations pending evidence and a separate deprecation decision. |

## Tests, documents and root policy

The 53 `tests/test_*.py` files cover accepted paths, source-H validation,
experimental B1/B2 and independent diagnostics. Pytest parametrization means
file/function counts are not case counts. `test_import.py` checks namespace
imports; runtime/Windows launcher tests include subprocess and byte/text checks.
`test_e2e_config` and shared-Z tests import authored fixtures across test modules;
reorganizing files can break those references (C08). Synthetic optics and geometry
oracles must not be merged into the production routine they are meant to check.

`tests/integration/` contains four explicit opt-in `run_*_smoke.py` files
(Converter/source-H, synthetic 2.5D, voxel and Solar) plus
`source_h_25d_fixture.py`. Their run names are outside default `test_*.py`
collection; their documented direct commands and local inputs remain separate
from routine CI claims. Three tracked fixture assets are `.gitattributes`,
`expected.json`, `two_buildings.gml` (23,554 bytes). The attributes enforce LF
for GML/JSON, important to frozen hashes on Windows.

| Document/config group | Classification, responsibility and refs |
|---|---|
| Concept v0.2 / inherited v0.1; Phase A design/current-status note; Building/Terrain/Adapter contracts | Core / Active reference, subject to each formal/provisional/historical status. README/AGENTS route here. Do not merge apparently overlapping scopes into a new contract. |
| Development Principles, AGENTS, governance proposal, architecture, processing model, Windows setup | Core / Active operations/design guidance; governance remains proposed and setup versions are dated observations. Runtime boundary text appears in several owners for different purposes; C01 navigation, not silent policy replacement. |
| `docs/status/` 4, B1/B2 backlogs, parameter/GVI audits, minimal E2E and reuse/GIS planning | Current navigation / Experimental / Active planning, with dated evidence. B1 has 12 deferred IDs, B2 7; current inventory changes none. Historical inventories are not current usage attestations. |
| `docs/experiments/real_komae_{source_h,voxel,solar}/`, `b2_gvi/` | Active reproduction guides plus Historical / Evidence results, hashes and failures. The Solar guide spans 821 lines/chronological stages; C01 can improve a current-route/contents section without splitting old anchors or repeating QA tables. |
| `docs/experiments/voxcity_canopy_shadow/`, `plateau_converter/`, `research/`, `reviews/`, `verification/` | Historical / Evidence and retained diagnostic/method owners; current tests and later results still cite them. Phase 5 draft/open gates remain distinct from subsequently demonstrated exploratory technical execution. |
| `docs/acceptance/` 5 and `experiments/a1_e2e_pilot/README.md` | Historical / Evidence with continuing acceptance authority within recorded datasets/conditions. The Terrain correction is additive evidence; old dataset names must not be globally rewritten. |
| `docs/local_handoff/komae_test_standard.tif.provenance.json` | Historical / Evidence; cited by acquisition inventory. Its corresponding external raster/source footprint was not established by that record; current availability/use remains Unknown U07. A JSON filename containing “standard” does not establish Standard acceptance. |
| `config/study_areas/komae_09LD3451.yaml`, `config/experiments/komae_e2e.json` | Core area definition / Experimental active example. `study_area` parses the constrained YAML; `e2e_config` validates explicit relative locators/hashes and saved snapshots. Example JSON binds dated local source-H/Terrain/Envelope paths, not a portable dataset bundled with Git. |
| Root `.gitignore`, `pyproject.toml`, `README.md`, `AGENTS.md`, `LICENSE` | Core / Active package, data policy and navigation. LICENSE explicitly says none selected: not disposable generated boilerplate, and selection requires a separate user decision. No root dependency lock, requirements file, tox/setup config is tracked. |

### Navigation check

A bounded inline Markdown link/heading scan, excluding fenced examples, examined
86 tracked Markdown files: **982 local links, zero missing targets, zero unmatched
heading candidates**; **146 external links were not network-checked**. A graph
following only local Markdown links from root README reaches **81 of 82 docs
Markdown files**. The remaining file is
[OUEM_GIS_Output_Visualization_Audit_v0.1.md](OUEM_GIS_Output_Visualization_Audit_v0.1.md).
This identifies a concrete C01 navigation candidate, not proof it has no readers:
plain-text paths, direct GitHub access, external bookmarks and dynamic references
are outside the graph. No existing links were changed in this task.

## Dependencies, environments and CI

The package declares Python >=3.10, build `setuptools>=68`, and seven runtime
dependencies: numpy>=1.24, rasterio>=1.3, geopandas>=1.0, shapely>=2.0,
pyproj>=3.6, scipy>=1.10, and VoxCity at Git commit
**`fa212656305328a9a657973bae26f352bfe813bc`**. Current local distribution metadata
records VoxCity 1.7.0 and matching PEP 610 origin/commit. This scan did not repeat
the installed-source RECORD integrity audit or exercise engine compatibility.

Observed `.venv` metadata: NumPy 2.4.6, Rasterio 1.4.4, GeoPandas 1.2.0,
Shapely 2.2.0, pyproj 3.7.2, SciPy 1.17.1, Matplotlib 3.11.2, Numba 0.68.0,
affine 3.0.1, pytest 9.1.1. Project source imports Matplotlib/Numba/affine, but
these are not separate direct entries in pyproject; availability currently
depends on the installed dependency graph. Pytest is installed explicitly by CI.
This is a dependency-declaration/visibility candidate C02, **not an observed
missing-package failure**, and no pin/update/new dependency is proposed in this PR.

Windows OUEM execution uses the ordinary-terminal `.venv`, recorded as Python
3.11.9 by B1/B2 evidence. QGIS/OSGeo4W Python is separately managed: the accepted
runtime/runbook mentions 3.12.14; the later workstation/B2 record reports
3.12.15, QGIS 4.2.3 / GDAL 3.13.3. Dated observations are not conflicting new
minimum versions. No fresh GIS runtime health check was performed. GIS workers,
Console file loads, `python-qgis.bat`, the ignored runtime snapshot and the
external Converter remain host prerequisites U02/U04; a Git clone cannot supply
these or real datasets. Do not solve duplication by merging Python environments.

[`.github/workflows/pytest.yml`](../../.github/workflows/pytest.yml) is the only
tracked CI definition. It triggers pull requests to main and workflow_dispatch,
uses contents:read, checkout@v4/setup-python@v5, Ubuntu/Windows latest runners,
Python **3.12**, `python -m pip install . pytest`, then `python -m pytest -q -ra`.
There is no tracked dedicated QGIS/GPU/real-data job, dependency lock or explicit
version matrix beyond those two OSes. The GIS tests use conditional skips when
qgis/osgeo are unavailable; ordinary CI is not equivalent to separately recorded
GIS save/reopen/GUI evidence. The declared Python 3.10 floor is not exercised by
the tracked matrix; minimum-version compatibility remains unverified here.
Latest Actions results, branch protection and
external workflows were not queried (U05); no claim of a new green CI run is made.

## Data, generated assets and reproducibility risks

The formal data layout remains Raw → Native → Standard → Model → Output, with
`data/work/` a non-authoritative side workspace. `git ls-tree` shows **only 15
markers** under `data/`, not source datasets. `.gitignore` excludes lifecycle/work
files except marker paths, venv/caches, `.env*`, local YAML and
`scripts/work/.runtime/`, plus common geospatial formats/sidecars. `git check-ignore
-v` confirms representative B2 TIFF/QGZ, GIS snapshot, venv and pytest-cache paths
are ignored. Ignore rules do not untrack already tracked evidence or fixtures.

No tracked NPY/NPZ, GeoTIFF, GeoPackage, QGZ/QML, ZIP, bytecode or log was found.
No tracked blob is >=1 MiB. The largest is the cited 405,213-byte Height Envelope
verification PNG; the two other PNGs and the four Converter evidence JSONs are
documented historical evidence, not accidental outputs. The fifth docs JSON is
the local handoff record. The GML fixture is intentionally tracked despite the
global geospatial ignore pattern. No safe generated-file deletion is established.
QGZ/QML/NPY/JSON/log extensions are not all globally excluded: newly generated
copies outside ignored data/work can still be accidentally staged (C09).

Fixed source identities/paths are visible in `real_komae_source_h.CLI_SHA`,
Solar's `BASE_REPORT_SHA` / `ENVELOPE_SHA` fallback and the E2E JSON example;
configured calls resolve explicit bindings instead. ID diagnostic defaults point
at accepted Komae datasets. Some diagnostic CLIs confine output to an existing
run family; this is deliberate provenance/overwrite protection, not merely
inflexible path handling. The Converter probe has Windows tool-discovery paths.
Do not replace historical hashes, root-relative topology or run IDs globally.

The recorded B1 shared-Z and B2 output locations are listed in their closeouts.
Their Current arrays, receipts/configs/reports, input snapshots, output hashes,
executed-source references and QGZ relative topology are protected evidence.
This inventory did not rehash/replay them or label ignored data expendable.
Reproducibility risk also includes byte changes to watched code when extracting
helpers, conflating scalar/model/serialized hashes, swapping validation for the
producer being validated, and losing Windows quoting/exit/encoding behavior.

## Consolidation, retirement and Unknown register

Concrete consolidation overlays: C01 document navigation; C02 environment/CI
visibility; C03 shared engine provenance in a broad runner; C04 file/JSON helper
ownership; C05 the substantial A3 work script and orchestrator boundaries;
C06 CMD/manual diagnostics; C07 GIS write/read primitives; C08 fixture ownership;
C09 generated-asset policy checks. See the plan for per-candidate dependencies,
risk, testing, acceptance and rollback. These are maintenance opportunities,
not findings that the computations are incorrect.

An exact top-level AST-function comparison (functions spanning >=5 physical
lines) found the same `sha256` body in `acquire/meta_chmv2.py` and `komae_canopy.py`.
It does not establish that all hashing/writing code is equivalent. For example,
`digest` in the A3 script hashes array bytes, repair evaluation hashes serialized
values, the Standardizer hashes files, and `Watch` hashes/stamps frozen bindings.
Their failure/path/serialization/NoData semantics must remain distinct. Size alone
is not a reason to split a cohesive contract module.

Largest source observations: `komae_integration.py` **782 lines** (runtime,
provenance, guarded output lifecycle, subprocess stages, repeat checks and CLI),
Adapter `__init__.py` **525**, Solar **466**, vertical provenance **438**,
CRS repair **427**, height diagnostics **417**, Voxel **404**. Integration has
callers in B1/B2 and many diagnostics; splitting it is not a standalone filename
cleanup. `test_komae_integration.py` is **723** lines and is regression evidence,
not a test-removal target. Line counts include blanks/comments, not complexity.

| Unknown ID | What is known / what is not established | Required before changing/removing |
|---|---|---|
| U01 | Three historical building-ID diagnostic CLIs/citations exist; no tracked automatic caller was found. Current human/external use is unknown. | Ask owners, inspect external launch instructions and frozen evidence; design an explicit replacement/deprecation or retain. No deletion based on absence of grep hits. |
| U02 | File-path loads are visible in `gis_project._helper`, `tests/test_gis_*`, `test_b2_gvi_qgis`; runpy loads A3. External Console/automation paths, runtime resolution and users are not exhaustively discoverable. | Inventory intended GIS/CLI invocations, then separate-runtime/fresh-process compatibility checks; do not label these modules unused. |
| U03 | CMD dispatch, validation and several Windows tests are present; fresh execution of every wrapper, association and external scheduler use was not tested. | Compare command contracts, path spaces/metacharacters, cwd/env and exits; collect usage evidence. |
| U04 | Package/PEP 610 metadata and dated runtime records exist; fresh GIS/Converter availability, all transitive resolution and clean-machine portability are unverified. | Record actual environments and supported boundaries without installing/updating anything under the cleanup label. |
| U05 | Tracked CI YAML is known; current remote check outcomes, repository rules and external CI are unverified. | Inspect those settings/statuses read-only before suggesting changes; do not equate local historical pytest with CI/GUI coverage. |
| U06 | Actual lifecycle/work outputs are ignored and closeouts bind selected runs; complete ignored-data ownership/storage/history is not inventoried. | A separate authorized data/provenance inventory before any local artifact/cache pruning or relocation. |
| U07 | Legacy CHM handoff JSON and its acquisition-inventory citation are tracked; source raster lineage/coverage/current external use is not established. | Trace actual raster/hash/source and owner before any retirement or claim of Standard equivalence. |

The only conditional retirement-review group identified here is U01/C06; **no
file is established safe to retire**. Placeholders, old CLI branches, accepted
workers, probes, tests, evidence images/JSON and local datasets are retained.
Historical “not implemented”/failure statements must remain scoped to their
dates; later B1/B2 technical success does not resolve science or rewrite them.
