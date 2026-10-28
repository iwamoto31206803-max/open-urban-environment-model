# Open Urban Environment Model (OUEM)

**オープン都市環境モデル**

OUEM prepares reproducible 3D urban environment models from geospatial data
and explores human-scale environmental assessment using external engines.
Phase A covers model construction; Phase B covers solar/shade and green view.
The [concept and architecture](docs/OUEM_Concept_Architecture_v0.2.md) defines
these phases and their variants.

## Current milestone

An **exploratory real-city End-to-End PoC is complete for a small Komae area**:
real PLATEAU source-H Building and Standard Terrain were integrated with an
estimated Meta CHMv2 Height Envelope on one actual VoxCity grid, followed by
Current / No-Canopy direct-solar comparison using public VoxCity APIs.

| Experimental step | Procedure | Executed evidence |
|---|---|---|
| PR #97: CityGML → fixed Converter → source-H Native / Standard / Consumer | [Building preparation](docs/experiments/real_komae_source_h/README.md) | [H retention and Terrain checks](docs/experiments/real_komae_source_h/RESULTS.md) |
| PR #98: Building + Terrain → actual VoxCity voxels | [Voxel integration](docs/experiments/real_komae_voxel/README.md) | [Grid, IDs and vertical diagnostics](docs/experiments/real_komae_voxel/RESULTS.md) |
| PR #99: estimated Canopy + paired direct solar | [Three-element PoC](docs/experiments/real_komae_solar/README.md) | [Solar comparison and limitations](docs/experiments/real_komae_solar/RESULTS.md) |

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

For the real-city PoC, follow PR #97 → #98 → #99 procedures above. Actual inputs,
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
