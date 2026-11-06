# Building Current State

Current documentation review: **2026-11-06**, main
`529d842dfc2af82843bdcd4bfa888e79dbff6328` (through PR #160 merged).
This is a documentation/code/evidence review, not a new real-data execution.
The original B1 technical results remain the dated PR #121 evidence, not a
new execution or acceptance decision.
This [informational entry point](../OUEM_Documentation_Governance_v0.1.md)
reflects code and existing execution records, not a new run or acceptance decision.

Subsequent synthetic work, based on main
`2864c61cfbf9fa0a993fdc67abe7cedf7a528be3` (PR #161 merged):
[STEP 3-A height distribution](../experiments/height_distribution/STEP3A_SYNTHETIC_HEIGHT_DISTRIBUTION.md)
compares per-cell centre and clipped-roof maximum absolute Z, retaining all face
and building contributions. This is synthetic-only, before VoxCity; method
adoption, STEP 3-B connection and scientific/formal acceptance remain unverified.

Following that checkpoint, [STEP 3-B synthetic voxelization](../experiments/height_distribution/STEP3B_SYNTHETIC_VOXELIZATION.md),
based on main `2a0585dd821ca8c783f7565c83fb3b363b1611e5` (PR #162 merged),
checks the pinned public Voxelizer against independent integer intervals for
representative/centre/cell-max inputs. This remains synthetic-only: unresolved
ownership, tops and capacity are rejected; real-data and environmental connections
and scientific/formal acceptance are unverified. The linked record owns evidence.

[STEP 3-C synthetic Solar/Shadow](../experiments/height_distribution/STEP3C_SYNTHETIC_SOLAR_SHADOW.md)
follows main `e15dba7f45147eb8d23f48959c28e79a417666be` (PR #163 merged).
It compares representative/centre/cell-max roofs using common nonbuilding
observers and explicit north-up/API-axis conversion. Binary shadow and horizontal
direct solar have separate synthetic evidence; real-data applicability and
scientific/formal acceptance remain unverified. No STEP 2 saved data is changed.

[STEP 4-0 real LoD2 audit](../experiments/height_distribution/STEP4_0_REAL_LOD2_ACCEPTANCE_AUDIT.md),
based on main `3db0154d6d008f5d2f5487910beabea14b46f313`, rechecks existing
Mixed-LoD source semantics and unique Raw/Native/Standard face correspondence
read-only. Real-data audit execution is separate from STEP 4-A eligibility:
footprint/vertical input conditions remain unresolved, with no real height
distribution or environmental processing and no formal acceptance.

The subsequent [STEP 4-A four-sample PoC](../experiments/height_distribution/STEP4A_REAL_LOD2_ROOF_DISTRIBUTION.md),
based on main `171f2afcef50405597465dfe2a91cf2c731b5ff1`, adopts GroundSurface XY
only as a local provisional presence rule and derives absolute source-H tops.
Centre-unsupported cells remain unknown; raw projections and all face contributions
are retained. This does not verify HAG, engine integration or scientific/formal acceptance.

[STEP 4-B real LoD2 voxelization](../experiments/height_distribution/STEP4B_REAL_LOD2_VOXELIZATION.md)
connects those four saved cell-max distributions to the pinned public Voxelizer
using per-building numerical anchors, with exact independent occupancy QA and
reproducibility. Sloped/stepped roofs produce varying column heights; full-cell
boundary inflation and the surface-layer offset are quantified. Real DEM/HAG,
scientific validation and formal acceptance remain unverified.

[STEP 4-B2 saved-Terrain PoC](../experiments/height_distribution/STEP4B2_REAL_LOD2_TERRAIN_VOXELIZATION.md)
replaces those numerical anchors with sampled Candidate B DEM and owner-conditioned
ground for the same four roofs. Technical execution/oracle comparison passes;
sub-0.5m local terrain relief rounds to a single surface layer at 1m resolution.
Vertical status remains CONDITIONAL; HAG/scientific/formal gates stay unverified
and terrain_integration_ready remains false.

## Current milestone: B1 technical E2E closeout

A small-area Komae path reaches Building + Terrain + estimated Canopy voxels,
configured A/B reuse, paired direct solar and QGIS projects. The
[B1 technical closeout](B1_TECHNICAL_MILESTONE_CLOSEOUT.md) links implementation,
execution and GIS/GUI verification; full scientific validation is deferred in the
[backlog](../planning/OUEM_B1_Deferred_Validation_Backlog.md). B2 had not yet
been implemented at the PR #121 checkpoint; subsequent [B2 technical closeout](B2_TECHNICAL_MILESTONE_CLOSEOUT.md)
records a bounded Komae CPU green-view E2E, not scientific validation.
The original three PoC stages retain separate historical evidence:

| Stage / implementation | Procedure and evidence |
|---|---|
| [PR #97 source-H preparation](../../src/ouem/real_komae_source_h.py): real CityGML, fixed Converter, Native / Standard, independent Consumer | [Procedure](../experiments/real_komae_source_h/README.md); [geometry, all-H retention and Terrain checks](../experiments/real_komae_source_h/RESULTS.md) |
| [PR #98 voxelization](../../src/ouem/real_komae_voxel.py): Building + Terrain on the actual engine grid | [Procedure](../experiments/real_komae_voxel/README.md); [IDs, ground and voxel diagnostics](../experiments/real_komae_voxel/RESULTS.md) |
| [PR #99 mixed direct solar](../../src/ouem/real_komae_solar.py): estimated Canopy added with Building priority and common observers | [Procedure](../experiments/real_komae_solar/README.md); [paired results and limits](../experiments/real_komae_solar/RESULTS.md) |

Source-H Native uses compound EPSG:6697. Standardization transforms only XY
from EPSG:6668 to EPSG:6677 and retains every H without passing it to PROJ or
using EPSG:4979. Original Standard geometry remains complete; the engine uses
a derived 2.5D footprint/roof proxy. Source H, conditioned engine ground/D0 and
voxel discretization are distinct quantities. Exact engine centres and orientation
are reused downstream; geographic GeoTIFF indices are not the older projected
north-up grid. Methods and numerical budgets belong to the linked records.

## Subsequent upstream experiments (2026-11-06 review)

The [Kunitachi 2 km preflight](../planning/OUEM_Kunitachi_Data_Source_Preflight_v0.1.md)
verified selected Raw Building and DEM/CHMv2 coverage, but did **not** create
Kunitachi Native / Standard / VoxCity or B1/B2 runs. The preflight rectangle
extends outside city boundaries, and building LoD/neighboring-provider coverage
remains a separate transfer decision.

The [Mixed-LoD Raw selection](../experiments/real_komae_source_h/MIXED_LOD_SELECTOR_POC.md)
and [Candidate B T5 closeout](../experiments/real_komae_source_h/MIXED_LOD_CANDIDATE_B_T5_4_CLOSURE.md)
record an independent experimental chain: 31 LoD1 Setagaya-attribute buildings
and 32 LoD2 Komae-attribute buildings from the Komae distribution, with all 63
represented in the expanded VoxCity domain. This is a **cross-municipality test**,
not proof of a mixed-LoD sample wholly inside Komae, multi-provider integration,
or a replacement for the existing Source-H B1/Canopy runners. The
[Candidate B E0 test](../experiments/real_komae_source_h/MIXED_LOD_CANDIDATE_B_E0_SHADOW.md)
used synthetic shadows only at that historical checkpoint. The subsequent
[STEP 2-A real building-only shadow](../experiments/real_komae_source_h/STEP2A_BUILDING_SHADOW_E2E.md),
[STEP 2-C2 real Canopy pair](../experiments/real_komae_source_h/STEP2C2_REAL_CANOPY_INTEGRATION.md),
[STEP 2-C3 direct Solar](../experiments/real_komae_source_h/STEP2C3_REAL_SOLAR.md)
and [STEP 2-C4 weighted first-TREE view index](../experiments/real_komae_source_h/STEP2C4_REAL_GVI.md)
now establish a bounded **experimental technical E2E** using the same saved
127x127 model and registered evaluation ROI. The earlier
[E1 design](../planning/OUEM_Candidate_B_E1_Minimal_Shadow_Design.md)
remains historical planning, not the current implementation gate.
The representative building-height proxy, conditional T.P. inheritance,
source eligibility, scientific accuracy and formal acceptance remain unresolved;
the original accepted A2/A3 boundaries are unchanged.

## Accepted v0.1 remains a separate path

[Standard Building](../OUEM_Standard_Building_v0.1.md) and
[Standard Terrain](../OUEM_Standard_Terrain_v0.1.md) remain **PROVISIONAL**.
The existing path uses Converter GeoPackage ingestion via
[plateau.py](../../src/ouem/native/building/plateau.py), the
[Building standardizer](../../src/ouem/standardize/building/__init__.py) and the
[v0.1 Adapter](../OUEM_VoxCity_Adapter_v0.1.md). Its accepted Native CRS label
is EPSG:4979; the Standardizer transforms the horizontal component while retaining
numeric Z interpreted as T.P. The label alone does not resolve the source datum.
The source-H candidate v0.2 manifests do not enter that Adapter's whitelist.

The [A1 Building record](../../experiments/a1_e2e_pilot/README.md),
[A3 Adapter record](../acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md)
and [contained E2E record](../acceptance/OUEM_Komae_Contained_E2E_Acceptance_20261018.md)
retain their dataset-specific scope. They do not accept the new mixed solar lane.
Existing Building/Standard/Adapter regressions remain necessary alongside the
[source-H](../../tests/test_source_h_consumer.py) and
[real-city](../../tests/test_real_komae_solar.py) tests.

## Open issues and approval boundaries

Source-H eligibility is **NOT_ESTABLISHED**, human review / Formal Acceptance
of the experimental lane **NOT_VERIFIED**, and Phase 5 A1–A4 remain **OPEN**.
The [Completion Gate](../experiments/voxcity_canopy_shadow/PHASE4_COMPLETION_GATE_REVIEW_20261027.md)
and [Phase 5 draft plan](../experiments/voxcity_canopy_shadow/PHASE5_INTEGRATION_PLAN_v0.1_Draft.md)
are unchanged. Common-grid, ground, ID, overlap and observer checks have now
been implemented and executed in the bounded PoC; their technical success does
not supply gate approval or complete the plan's acceptance requirements.

Independent vertical-datum realization, surveyed geometry/height accuracy and
observation-date alignment remain unverified. The earlier
[Building vertical diagnosis](../research/OUEM_Komae_Building_Vertical_Geometry_Diagnosis.md)
is **UNRESOLVED** for its historical data chain. The new source-H correspondence
does not retrospectively explain that diagnosis or justify a constant Z offset.
See [Canopy Current State](CANOPY_CURRENT_STATE.md) for presence, optical,
observer and finite-domain limitations of mixed solar.

## Reproduction and historical context

Follow the stage procedures above with actual source files, manifests, receipts,
hashes and the pinned engine identified in the results. Missing/mismatched inputs
must stop processing; new upstream identities need review. Keep the
[OUEM and GIS runtimes separate](../architecture.md); use the
[runbook](../../scripts/work/README.md) for accepted-path operations.

Earlier absence checks for `data/native/building/komae.gpkg` and
`data/standard/building/komae.gpkg` described those historical paths only.
PR #97–#99 records identify separate experimental run artifacts; neither a
historical acceptance nor this summary guarantees current local availability.
This refresh did not rerun processing or revalidate local artifact hashes.

The [source-H foundation](../Source_H_Building_Provenance_Foundation_v0.1.md),
[Native ingestion](../Source_H_Native_Building_Ingestion_v0.1.md),
[Standardizer](../Source_H_Standard_Building_v0.1.md) and
[Consumer](../Source_H_Standard_Consumer_Validation_v0.1.md) own their interfaces.
Earlier [synthetic 2.5D](../Source_H_Synthetic_25D_Adapter_v0.1.md),
[voxel](../Source_H_Synthetic_Voxelization_v0.1.md) and
[solar](../Source_H_Synthetic_Solar_v0.1.md) results remain regression evidence.
Their synthetic-only scope and older pending statements describe those stages,
not the limit of today's experimental implementation.
