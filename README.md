# Open Urban Environment Model (OUEM)

**オープン都市環境モデル**

OUEM prepares reproducible 3D urban environment models from geospatial data
and explores human-scale environmental assessment using external engines.
Phase A covers model construction; Phase B covers solar/shade and green view.
The [concept and architecture](docs/OUEM_Concept_Architecture_v0.2.md) defines
these phases and their variants.

## Project tracks (status review: 2026-11-06)

The bounded **Komae B1/B2 technical E2E** is already implemented and recorded;
scientific accuracy and full formal acceptance are separate questions. Recent
upstream work follows distinct tracks, not a replacement for the existing B1/B2 implementation:

| Track | Recorded evidence | Scope at this checkpoint |
|---|---|---|
| Komae B1/B2 environmental assessment | [B1 closeout](docs/status/B1_TECHNICAL_MILESTONE_CLOSEOUT.md), [B2 closeout](docs/status/B2_TECHNICAL_MILESTONE_CLOSEOUT.md) | Existing bounded real-data Solar and provisional CPU green-view outputs, GIS and checks; not field-calibrated results |
| Kunitachi transfer preparation | [2 km source preflight](docs/planning/OUEM_Kunitachi_Data_Source_Preflight_v0.1.md), [study-area configuration](config/study_areas/kunitachi_2km.yaml) | Building/DEM/CHM coverage examined; no Kunitachi Native/Standard/Envelope/Voxel/Solar/GVI E2E yet; the rectangle includes areas outside Kunitachi |
| Mixed-LoD Building experiment (Candidate B) | [T5-4 baseline](docs/experiments/real_komae_source_h/MIXED_LOD_CANDIDATE_B_T5_4_CLOSURE.md), [STEP 2-C2 canopy pair](docs/experiments/real_komae_source_h/STEP2C2_REAL_CANOPY_INTEGRATION.md), [STEP 2-C3 Solar](docs/experiments/real_komae_source_h/STEP2C3_REAL_SOLAR.md), [STEP 2-C4 GVI](docs/experiments/real_komae_source_h/STEP2C4_REAL_GVI.md) | Komae-distribution cross-municipality sample: 31 LoD1 Setagaya-attribute and 32 LoD2 Komae-attribute buildings; all 63 voxelized. Real saved-model Solar and weighted first-TREE view index have experimental technical E2E evidence, not scientific/formal acceptance. |

The earlier [Candidate B E1 design](docs/planning/OUEM_Candidate_B_E1_Minimal_Shadow_Design.md)
is historical planning, not the current execution status. Subsequent
[STEP 2-A building-only shadow](docs/experiments/real_komae_source_h/STEP2A_BUILDING_SHADOW_E2E.md)
and STEP 2-C2/C3/C4 reused existing VoxCity and B1/B2 calculation kernels.
The candidate remains experimental and does not expand Accepted v0.1.

## Current milestone

**B1 Technical E2E Milestone reached for the bounded Komae A/B experiments.**
Prepared Building, Terrain and estimated Canopy reach configuration-driven
VoxCity voxels, Current / No-Canopy / Difference direct irradiance and QGIS-ready
styles/projects. The [closeout](docs/status/B1_TECHNICAL_MILESTONE_CLOSEOUT.md)
distinguishes the original PR #97–99 PoC, v0.2 reuse/shared Z, v0.3 GIS/GUI work,
and PR #119–121 parameter, synthetic-physics and real-geometry diagnostics.

B1's full scientific validation is **deferred**; its shared geometry/observer
uncertainties remain in the
[deferred validation backlog](docs/planning/OUEM_B1_Deferred_Validation_Backlog.md).

B2 has [CPU synthetic characterization](docs/experiments/b2_gvi/B2_CPU_GVI_Synthetic_Characterization_v0.1.md)
following the [VoxCity GVI API audit](docs/planning/OUEM_B2_VoxCity_GVI_API_Audit_v0.1.md).
The [Komae A/B CPU Technical E2E](docs/experiments/b2_gvi/RESULTS.md) now has bounded
execution/GIS evidence using the provisional CPU weighted first-TREE view index;
the [B2 Technical Closeout](docs/status/B2_TECHNICAL_MILESTONE_CLOSEOUT.md)
records completion of this bounded milestone and the unresolved handoff.
Scientific validation remains unverified. The original
[minimal proposal](docs/planning/OUEM_B2_Minimal_Technical_E2E_Design_v0.1.md)
retains its dated design context. See the
[B2 deferred backlog](docs/planning/OUEM_B2_Deferred_Validation_Backlog.md).

**Candidate B STEP 2 technical E2E is also complete within its experimental scope.**
The saved 63-building Mixed-LoD voxel model and derived Canopy pair feed
[real direct Solar comparison](docs/experiments/real_komae_source_h/STEP2C3_REAL_SOLAR.md)
and [CPU weighted first-TREE view index](docs/experiments/real_komae_source_h/STEP2C4_REAL_GVI.md)
at the same saved observer locations and EPSG:6677 ROI cells.
`terrain_integration_ready=false`; scientific accuracy, observer eye height,
source datum realization and formal acceptance remain **NOT_VERIFIED**.
[STEP 3-A synthetic building-height distribution](docs/experiments/height_distribution/STEP3A_SYNTHETIC_HEIGHT_DISTRIBUTION.md)
compares centre and cell-maximum roof Z before engine connection, preserving the
current representative-height baseline. It establishes no real-data or formal acceptance.
[STEP 3-B synthetic voxelization](docs/experiments/height_distribution/STEP3B_SYNTHETIC_VOXELIZATION.md)
connects that Derived to the pinned public Voxelizer with independent occupancy,
owner-ground, rounding and capacity QA; unresolved inputs remain BLOCKED.
[STEP 3-C synthetic Solar/Shadow](docs/experiments/height_distribution/STEP3C_SYNTHETIC_SOLAR_SHADOW.md)
compares the three height models at common nonbuilding observers, with explicit
axis conversion and independent shadow geometry checks; scientific accuracy remains unverified.
[STEP 4-0 read-only real LoD2 audit](docs/experiments/height_distribution/STEP4_0_REAL_LOD2_ACCEPTANCE_AUDIT.md)
checks source roof semantics and face correspondence before real height-distribution
processing. The existing LoD2 population remains CONDITIONAL, not formally accepted.
[STEP 4-A absolute roof-top distribution](docs/experiments/height_distribution/STEP4A_REAL_LOD2_ROOF_DISTRIBUTION.md)
derives centre/cell-max absolute source H for the four fixed audited samples under
a provisional GroundSurface-footprint rule; HAG and engine connection remain unverified.
[STEP 4-B real LoD2 voxelization](docs/experiments/height_distribution/STEP4B_REAL_LOD2_VOXELIZATION.md)
generates four actual 3D building volumes from saved cell-max H with constant
numeric anchors; real DEM/HAG integration remains unverified.
[STEP 4-B2 saved-Terrain voxelization](docs/experiments/height_distribution/STEP4B2_REAL_LOD2_TERRAIN_VOXELIZATION.md)
places the same four roof distributions over saved Candidate B DEM in a conditional
numerical experiment; 1m terrain quantization and roof/occupancy changes are recorded.
[STEP 4-C real roof shadow comparison](docs/experiments/height_distribution/STEP4C_REAL_LOD2_SHADOW_COMPARISON.md)
compares max-roof representative versus distributed roofs under shared Terrain,
observers and sun; the four isolated-building sensitivity results remain experimental.

| Available experimental workflow | Start here |
|---|---|
| Saved B1 Current → CPU weighted first-TREE view index → GeoTIFF/QGIS | [B2 usage and actual ROI/context](docs/experiments/b2_gvi/README.md), [A/B results](docs/experiments/b2_gvi/RESULTS.md) |
| Existing-input rectangle/Run-ID reuse, Voxel then Solar | [JSON example](config/experiments/komae_e2e.json), [Voxel procedure](docs/experiments/real_komae_voxel/README.md#configurable-reuse-v02-phase-2), [Solar procedure](docs/experiments/real_komae_solar/README.md#configurable-reuse) |
| Completed-run QML/manifest, exact-cell inspection, QGZ generation | [GIS procedures and recorded A/B verification](docs/experiments/real_komae_solar/README.md#qml--manifest-visualization) |
| Saved-model observer/geometry diagnostics, without model execution | [Phase 2 diagnostic CLI and report](docs/experiments/real_komae_solar/B1_GEOMETRY_OBSERVER_PHASE2.md) |

These are bounded technical results. Formal acceptance of this source-H / mixed
solar lane is **NOT_VERIFIED**, source-H eligibility **NOT_ESTABLISHED**, and
Phase 5 A1–A4 remain **OPEN**. Scientific accuracy, nationwide applicability and
general solar-boundary sufficiency have not been established. Canopy is estimated,
and direct irradiance is modeled with assumed optics, not measured exposure.

## Accepted and experimental paths

| Path | Boundary and status |
|---|---|
| Accepted v0.1 Komae path | Converter GeoPackage → Native → Standard Building + Terrain → versioned VoxCity Building Adapter and voxel generation. Acceptance is limited to the recorded datasets and conditions. |
| Experimental source-H path | Fixed Converter retains source H; separate Native / Standard / Consumer and real-city runners reach mixed voxels and direct solar. It does not extend the accepted Adapter's manifest whitelist or acceptance scope. |
| Experimental Mixed-LoD Candidate B | Separate Raw selector / Converter bridge / Native / Standard / independent Consumer, experimental WARD_FIRST Terrain, 63-building VoxCity grid, derived Canopy, and same-observer Solar/GVI technical E2E. City-border sample using Komae distributed data; scientific validity, source eligibility and formal acceptance not established. |

The [Building acceptance record](experiments/a1_e2e_pilot/README.md),
[A2 Terrain record](docs/acceptance/OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md)
and [A3 Adapter record](docs/acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md)
remain unchanged. Standard Building and Terrain remain **PROVISIONAL**;
Standard Canopy remains **DRAFT**. A2/A3 in these implementation records mean
Terrain/Adapter, distinct from the conceptual National Baseline/GSI-LiDAR variants.

## Documentation Guide

Use the routes below for the bounded B1/B2 Technical E2E milestones and their
unverified scientific questions. Each linked record retains its own status and
scope; this guide adds no Acceptance or validation criteria.

| Information owner | Start here / responsibility |
|---|---|
| Architecture / Standards | [Concept and Architecture v0.2](docs/OUEM_Concept_Architecture_v0.2.md), [runtime architecture](docs/architecture.md) and the Standards below own design and contracts, subject to their stated status. [Development Principles](docs/OUEM_Development_Principles_v0.1.md) own development decisions. |
| Status / Closeout | [B1 Technical Closeout](docs/status/B1_TECHNICAL_MILESTONE_CLOSEOUT.md) and [B2 Technical Closeout](docs/status/B2_TECHNICAL_MILESTONE_CLOSEOUT.md) summarize milestone scope and link its evidence. Technical completion does not establish scientific validity. |
| Backlog | [B1 deferred validation](docs/planning/OUEM_B1_Deferred_Validation_Backlog.md) and [B2 deferred validation](docs/planning/OUEM_B2_Deferred_Validation_Backlog.md) own unresolved verification questions; these remain open within their recorded scope. |
| Experiments / RESULTS | [B1 Solar usage and evidence](docs/experiments/real_komae_solar/README.md), [B1 original results](docs/experiments/real_komae_solar/RESULTS.md), [B2 usage](docs/experiments/b2_gvi/README.md) / [results](docs/experiments/b2_gvi/RESULTS.md), and [Candidate B STEP 2 experiments](docs/experiments/real_komae_source_h/README.md) own execution conditions, numbers and provenance. Use the workflow table above and [Windows runbook](scripts/work/README.md) for operational entry points. |
| Planning | [Repository Inventory](docs/planning/OUEM_Repository_Inventory_v0.1.md) and [Cleanup Plan](docs/planning/OUEM_Repository_Cleanup_Plan_v0.1.md) record the reviewed baseline and proposed work. [GIS Output Visualization Audit](docs/planning/OUEM_GIS_Output_Visualization_Audit_v0.1.md) is a dated design proposal; implemented GIS procedures and evidence are in the Solar guide. |
| Acceptance | [Building pilot](experiments/a1_e2e_pilot/README.md) and [acceptance records](docs/acceptance/) own existing formal acceptance evidence and its limits. Closeouts and planning summaries do not extend that scope. |

Start with the [Building Current State](docs/status/BUILDING_CURRENT_STATE.md)
or [Canopy Current State](docs/status/CANOPY_CURRENT_STATE.md), then follow its
implementation, verification and acceptance links. Detailed metrics, hashes and
commands belong to those owning records.

| Reference | Role |
|---|---|
| [Documentation governance](docs/OUEM_Documentation_Governance_v0.1.md) | Proposed roles and update rules; summaries do not override contracts or acceptance. |
| [Concept v0.2](docs/OUEM_Concept_Architecture_v0.2.md), [historical v0.1](docs/OUEM_Concept_Architecture_v0.1.md), [Phase A implementation design](docs/Phase_A_Implementation_Design_v0.1.md) | Design context; read the implementation design's current-status note. |
| [Standard Building](docs/OUEM_Standard_Building_v0.1.md), [Standard Terrain](docs/OUEM_Standard_Terrain_v0.1.md), [VoxCity Building Adapter](docs/OUEM_VoxCity_Adapter_v0.1.md) | Existing contracts and accepted boundaries. |
| [Standard Canopy draft](docs/OUEM_Standard_Canopy_v0.1_Draft.md), [Height Envelope](docs/CHM_Height_Envelope_PoC_v0.1.md) | Full Canopy proposal and separate experimental raster contract. |
| [Canopy shadow experiment index](docs/experiments/voxcity_canopy_shadow/README.md) | Earlier canopy-only results, observer/presence audits and historical context. |
| [Completion Gate](docs/experiments/voxcity_canopy_shadow/PHASE4_COMPLETION_GATE_REVIEW_20261027.md), [Phase 5 draft plan](docs/experiments/voxcity_canopy_shadow/PHASE5_INTEGRATION_PLAN_v0.1_Draft.md) | Recorded gate and proposal; subsequent exploratory execution does not close approval conditions. |

## Data and reproduction

The formal lifecycle is `raw → native → standard → model → output` under
`data/`. `data/work/` is a side workspace for non-authoritative processing and
experiments; Converter output there is not already OUEM Native. Real datasets,
run artifacts and runtime snapshots remain outside Git. The shared study area
is [komae_09LD3451.yaml](config/study_areas/komae_09LD3451.yaml).

For prepared inputs, start with the experimental
[JSON example](config/experiments/komae_e2e.json) and
[configuration and Voxel procedure](docs/experiments/real_komae_voxel/README.md#configurable-reuse-v02-phase-2),
then the [Solar procedure](docs/experiments/real_komae_solar/README.md#configurable-reuse).
Run `python -m ouem.real_komae_voxel --config PATH.json`, then
`python -m ouem.real_komae_solar --config <run-root>/run-config.json` in the OUEM
venv below. Use a new Run ID and output directory; retain the saved configuration
and receipt. The guides own path resolution, hashes, coverage and failure rules.
CRS, resolution and scientific conditions remain fixed; configuration is not
support for arbitrary regions, data sources or model conditions.

For completed configured runs, generate QGIS styles and a presentation manifest
without rerunning analysis: `python -m ouem.gis_visualization --run-root PATH --output NEW_DIRECTORY`.
See [QML generation and application](docs/experiments/real_komae_solar/README.md#qml--manifest-visualization)
for required evidence, seven layers and manual QGIS loading. Generation validates
saved results; generation alone leaves GUI verification **NOT_VERIFIED**.
Separate A/B [helper GUI checks](docs/experiments/real_komae_solar/README.md#gis-helper-gui-smoke-2026-10-29-after-pr-116)
and [QGZ generation/reopen/GUI evidence](docs/experiments/real_komae_solar/README.md#qgz-project-generation)
are recorded for **QGIS 4.2.3**, not arbitrary QGIS versions or scientific accuracy.
For GIS-side alpha-safe styling and exact original-cell inspection, see
[GIS display helpers](docs/experiments/real_komae_solar/README.md#gis-display-compatibility-and-exact-lookup).
To open the saved comparison as a project, use the standalone GIS-Python
[QGZ generator and reopen check](docs/experiments/real_komae_solar/README.md#qgz-project-generation)
in `src/ouem/gis_project.py`; QGIS remains separate from the OUEM venv.

For input preparation, follow [source-H Building](docs/experiments/real_komae_source_h/README.md),
[Voxel](docs/experiments/real_komae_voxel/README.md) and [Solar](docs/experiments/real_komae_solar/README.md)
procedures in order. Actual inputs,
adjacent manifests, source evidence and matching hashes are required; a past PASS
or cloned repository does not supply missing data. New upstream artifacts require
the identity review described in those procedures.

Use the [Tama Terrain acquisition recipe](docs/Terrain_Acquisition_PoC_v0.1.md)
and [CHMv2 acquisition guide](docs/Meta_CHMv2_AOI_Acquisition_PoC.md) for source
preparation. The historical `tokyo_23ku_dem_050m` path remains in old records;
consult the [Terrain provenance correction](docs/acceptance/OUEM_A2_Terrain_Source_Provenance_Correction_20261026.md)
for its Tama source identity. EPSG:6677 is horizontal; vertical declarations
and numerical H retention do not independently prove surveyed datum accuracy.

## Development

Use the [Development Principles](docs/OUEM_Development_Principles_v0.1.md) for
shared development decisions and collaboration; [AGENTS.md](AGENTS.md) contains
daily Codex instructions. These do not change data contracts or acceptance.

For errors or changes in the experimental E2E, start with these owners; imports
show dependencies and the linked tests provide the corresponding regression checks.

| Processing responsibility | Owning module | Related tests |
|---|---|---|
| JSON validation, extents, saved configuration and stage handoff | [e2e_config](src/ouem/e2e_config.py) | [Configuration](tests/test_e2e_config.py) |
| Building/Terrain validation, actual grid, base voxels and GIS export | [real_komae_voxel](src/ouem/real_komae_voxel.py) | [Voxel](tests/test_real_komae_voxel.py) |
| Envelope sampling, shared Z, TREE integration, paired solar and GIS export | [real_komae_solar](src/ouem/real_komae_solar.py) | [Solar](tests/test_real_komae_solar.py), [shared vertical domain](tests/test_shared_vertical_domain.py) |
| Read-only saved-run verification, QML styles and presentation manifest | [gis_visualization](src/ouem/gis_visualization.py) | [Visualization](tests/test_gis_visualization.py) |
| GIS-runtime alpha-safe styling and exact source-cell lookup | [gis_display](src/ouem/gis_display.py) | [Display helper](tests/test_gis_display.py) |
| GIS-runtime QGZ creation and separate-process reopen check | [gis_project](src/ouem/gis_project.py) | [Project](tests/test_gis_project.py) |
| Read-only saved Building/TREE/ground/observer diagnostics | [b1_geometry_diagnostics](src/ouem/b1_geometry_diagnostics.py) | [Diagnostics](tests/test_b1_geometry_diagnostics.py) |

The [closeout housekeeping audit](docs/planning/OUEM_B1_Closeout_Housekeeping_Audit_20261030.md)
records retained historical paths and future maintenance candidates; no cleanup
or prerequisite refactor is required to declare this bounded technical milestone.

Use Python 3.10+ and the repository OUEM virtual environment. VoxCity 1.7.0 remains
pinned in [pyproject.toml](pyproject.toml); its source is not vendored.

```shell
python -m pip install -e .
python -m pytest -q -ra
```

On Windows, use `.venv/Scripts/python.exe` from an ordinary terminal. Keep
OUEM/VoxCity separate from QGIS/OSGeo4W Python; see the
[runtime architecture](docs/architecture.md), [execution runbook](scripts/work/README.md)
and [recorded Windows setup](docs/development/OUEM_Windows_Development_and_Remote_Setup_20261025.md).
The runbook and contracts own the accepted v0.1 CLI procedures.

No repository license has yet been selected; see [LICENSE](LICENSE).
