# Open Urban Environment Model (OUEM)

**オープン都市環境モデル**

OUEM prepares reproducible 3D urban environment models from geospatial data
and explores human-scale environmental assessment using external engines.
Phase A covers model construction; Phase B covers solar/shade and green view.
The [concept and architecture](docs/OUEM_Concept_Architecture_v0.2.md) defines
these phases and their variants.

## Current milestone

**B1 Technical E2E Milestone reached for the bounded Komae A/B experiments.**
Prepared Building, Terrain and estimated Canopy reach configuration-driven
VoxCity voxels, Current / No-Canopy / Difference direct irradiance and QGIS-ready
styles/projects. The [closeout](docs/status/B1_TECHNICAL_MILESTONE_CLOSEOUT.md)
distinguishes the original PR #97–99 PoC, v0.2 reuse/shared Z, v0.3 GIS/GUI work,
and PR #119–121 parameter, synthetic-physics and real-geometry diagnostics.

B1's full scientific validation is **deferred**. Next development is B2 green
view, which is **not implemented or started by this closeout**; its shared
geometry/observer uncertainties remain in the
[deferred validation backlog](docs/planning/OUEM_B1_Deferred_Validation_Backlog.md).

B2 has [CPU synthetic characterization](docs/experiments/b2_gvi/B2_CPU_GVI_Synthetic_Characterization_v0.1.md)
following the [VoxCity GVI API audit](docs/planning/OUEM_B2_VoxCity_GVI_API_Audit_v0.1.md).
The [minimal Technical E2E](docs/planning/OUEM_B2_Minimal_Technical_E2E_Design_v0.1.md)
remains proposed; real-data GVI has not started. See the
[B2 deferred backlog](docs/planning/OUEM_B2_Deferred_Validation_Backlog.md).

| Available experimental workflow | Start here |
|---|---|
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

The [Building acceptance record](experiments/a1_e2e_pilot/README.md),
[A2 Terrain record](docs/acceptance/OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md)
and [A3 Adapter record](docs/acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md)
remain unchanged. Standard Building and Terrain remain **PROVISIONAL**;
Standard Canopy remains **DRAFT**. A2/A3 in these implementation records mean
Terrain/Adapter, distinct from the conceptual National Baseline/GSI-LiDAR variants.

## Documentation Guide

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
