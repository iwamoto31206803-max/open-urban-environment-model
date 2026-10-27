# VoxCity Canopy Shadow PoC — documentation index

These numbered phases are exploratory canopy-shadow milestones, separate from
OUEM's formal implementation/acceptance milestones. Start with the
[Phase 4 Completion Gate](PHASE4_COMPLETION_GATE_REVIEW_20261027.md) for the
combined decision and the [repository inventory](REPOSITORY_INVENTORY_20261027.md)
for document/code roles. The Gate verdict remains **CONDITIONAL PASS**; Phase 5
integration is blocked until its class A pre-start conditions close.

## Phase map

| Phase / principal documents | Status, verified scope and important limits |
|---|---|
| 0–1: [Results](RESULTS.md), [API review](API_REVIEW.md), [initial Adapter proposal](MINIMAL_ADAPTER_PROPOSAL.md) | **Historical** API/design snapshot. Its “not implemented” statements describe that investigation; the initial proposal is not the current formal specification. |
| 2: [Usage](PHASE2_USAGE.md), [real-data results](PHASE2_RESULTS_20261027.md) | **Experimental** Height Envelope → voxel and canopy-free/with-canopy CPU direct irradiance comparison. Nominal observer height is not exact physical DEM+1.5m; no Standard Canopy acceptance. |
| 3: [API and method](PHASE3_API_AND_METHOD.md), [sensitivity results](PHASE3_RESULTS_20261027.md) | **Experimental** 1m/0.5m isotropic voxel and observer-height sensitivity. Cross-size effects combine geometry, horizontal sampling and actual ray heights. |
| 4A: [Observer geometry and vertical-coordinate proposal](PHASE4A_OBSERVER_GEOMETRY_AND_VERTICAL_CONTRACT.md) | **Experimental / Draft proposal** API fixtures and Z correspondence. Recommends existing ground-map option C; arbitrary physical origins remain unvalidated. |
| 4B: [Canopy presence and coverage audit](PHASE4B_CANOPY_PRESENCE_AND_COVERAGE_AUDIT.md) | **Experimental / Draft diagnostics** state-flow fixtures and read-only Komae audit. CHM zero, NoData, coverage and TREE occupancy do not establish canopy absence/presence. |
| Phase 4 Completion Gate: [Review](PHASE4_COMPLETION_GATE_REVIEW_20261027.md), [inventory](REPOSITORY_INVENTORY_20261027.md) | **Experimental review**, CONDITIONAL PASS for closing the canopy-only work. Existing records stay frozen; class A input/grid/observer/state decisions remain pre-start requirements. |
| 5: [Integration plan v0.1](PHASE5_INTEGRATION_PLAN_v0.1_Draft.md) | **Draft**, not implemented by these navigation changes. Defines common-ground A/B/C requirements and acceptance gates; it does not authorize integration or resolve Building Z evidence. |

## Authority and related evidence

- [Concept v0.2](../../OUEM_Concept_Architecture_v0.2.md) is the **Formal** upper-level
  design; [v0.1](../../OUEM_Concept_Architecture_v0.1.md) is the **Historical**
  baseline with inherited B1/B2 details.
- [Standard Building](../../OUEM_Standard_Building_v0.1.md) and
  [Standard Terrain](../../OUEM_Standard_Terrain_v0.1.md) remain **Provisional**;
  the [Formal Building Adapter](../../OUEM_VoxCity_Adapter_v0.1.md) has its own
  bounded contract. [Standard Canopy](../../OUEM_Standard_Canopy_v0.1_Draft.md)
  remains **Draft**.
- [Height Envelope PoC](../../CHM_Height_Envelope_PoC_v0.1.md),
  [CHMv2 acquisition](../../Meta_CHMv2_AOI_Acquisition_PoC.md) and
  [3D visualization verification](../../verification/OUEM_Height_Envelope_3D_Visualization_Komae_20261026.md)
  are **Experimental** evidence with their own scope. Early environment notes
  describe the date of that work, not the absence of later real-data results.
- [Windows execution runbook](../../../scripts/work/README.md) also preserves
  legacy workflows. Use Phase 2's usage document for this Height Envelope-based
  shadow experiment; legacy canopy processing is a separate experimental path.
  [Root Documentation Guide](../../../README.md#documentation-guide) links the
  formal acceptance records and development environment.

The Gate and inventory are dated audit snapshots. This later navigation index
adds links without rewriting their historical findings, acceptance decisions,
input hashes or unresolved conditions. Merged documentation is not new dataset
acceptance or scientific accuracy validation.
