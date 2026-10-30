# Canopy Current State

Last checked: **2026-10-30**, main baseline
`53c5067d72c62631fdbfd949077faedaab604316` (PR #121 merged).
This [informational entry point](../OUEM_Documentation_Governance_v0.1.md)
reflects code and existing records; no new processing, accuracy validation or
acceptance is declared.

## Current milestone: B1 technical E2E closeout

The exploratory Komae path combines source-H Building, Standard Terrain and an
estimated Meta CHMv2 Height Envelope on the actual VoxCity grid, then compares
Current / No-Canopy direct irradiance. Configured A/B reuse, shared upper Z and
GIS/QGZ/GUI verification are recorded in the [B1 technical closeout](B1_TECHNICAL_MILESTONE_CLOSEOUT.md).
Full scientific validation is deferred to the [backlog](../planning/OUEM_B1_Deferred_Validation_Backlog.md);
B2 remains unimplemented. Original PoC
[PR #99 procedure](../experiments/real_komae_solar/README.md) and
[executed results](../experiments/real_komae_solar/RESULTS.md) own the methods,
metrics, input/output identities and boundary diagnostics.

It reuses [PR #97 source-H Building](../experiments/real_komae_source_h/README.md)
([results](../experiments/real_komae_source_h/RESULTS.md)) and
[PR #98 Building/Terrain voxels](../experiments/real_komae_voxel/README.md)
([results](../experiments/real_komae_voxel/RESULTS.md)). The
[Building Current State](BUILDING_CURRENT_STATE.md) distinguishes this
experimental lane from the accepted v0.1 path.

## Implemented Canopy preparation and meaning

| Component | Owning reference |
|---|---|
| CHMv2 source COG/index acquisition and AOI crop | [Acquisition procedure and evidence](../Meta_CHMv2_AOI_Acquisition_PoC.md); [implementation](../../src/ouem/acquire/meta_chmv2.py) |
| HAG + source-declared Terrain → absolute crown top/bottom and validity state | [Height Envelope contract](../CHM_Height_Envelope_PoC_v0.1.md); [implementation](../../src/ouem/height_envelope.py); [earlier 3D verification](../verification/OUEM_Height_Envelope_3D_Visualization_Komae_20261026.md) |
| Saved engine-centre sampling, TREE integration and paired direct solar | [Real-city implementation](../../src/ouem/real_komae_solar.py); [regression tests](../../tests/test_real_komae_solar.py) |

Envelope **state=1 means valid computation, not confirmed canopy presence**.
PR #99 candidates require covered, unmasked, finite top/bottom with valid state
and positive crown depth. NoData, outside coverage and valid zero height remain
separate. Neither CHM/TREE presence nor absence independently establishes real
trees. The [presence audit](../experiments/voxcity_canopy_shadow/PHASE4B_CANOPY_PRESENCE_AND_COVERAGE_AUDIT.md)
and [tests](../../tests/test_canopy_presence_semantics.py) retain this distinction.

Canopy is sampled at PR #98's saved actual centres, not matched by array index
to the older EPSG:6677 north-up grid. Public voxelization gives BUILDING priority;
Current with TREE removed equals No-Canopy and the saved Building/Terrain base
plus verified shared upper AIR. Grid, D0, Building occupancy, ground, ROI and
observations remain common **within each pair**, not across different A/B runs.
Numerical placement and pair checks do not validate estimated crowns above roofs.

## Unresolved validation and acceptance

[Standard Canopy](../OUEM_Standard_Canopy_v0.1_Draft.md) remains **DRAFT**.
Canonical polygon acquisition, full Native / Standard Canopy production and its
formal acceptance remain incomplete; the Canopy namespaces are placeholders.
The implemented Envelope route does not complete that proposed lifecycle.
Source-H eligibility remains **NOT_ESTABLISHED**, mixed-lane Formal Acceptance
**NOT_VERIFIED**, and Phase 5 A1–A4 **OPEN**.

The [Completion Gate](../experiments/voxcity_canopy_shadow/PHASE4_COMPLETION_GATE_REVIEW_20261027.md)
proposes CONDITIONAL PASS for the canopy-only milestone; the
[Phase 5 plan](../experiments/voxcity_canopy_shadow/PHASE5_INTEGRATION_PLAN_v0.1_Draft.md)
remains Draft. Earlier statements that mixed integration was unimplemented
refer to that earlier baseline. PR #97–#99 supply subsequent exploratory
implementation and technical checks, without closing the recorded approval gates.

Independent canopy presence, XY/time alignment, local HAG/ground accuracy,
constant crown-ratio and optical assumptions remain unverified or uncalibrated.
Strong modeled attenuation is not measured canopy benefit. The
[observer audit](../experiments/voxcity_canopy_shadow/PHASE4A_OBSERVER_GEOMETRY_AND_VERTICAL_CONTRACT.md)
explains why shared API ray origins do not establish exact physical DEM+1.5m
observations. Voxel surface/rounding errors are distinct from source-H conversion.
The [PR #121 saved-geometry diagnosis](../experiments/real_komae_solar/B1_GEOMETRY_OBSERVER_PHASE2.md)
quantifies actual observer offsets and cross-extent D0 rounding; its consistency
checks are not physical crown or observer-height validation.
General halo sufficiency remains unverified: PR #99's known-height directional
check and cropped controls do not establish expanded-domain convergence or
coverage of unknown exterior objects. No annual/global solar or heat result is
established. Detailed limits belong to the linked RESULTS.

## Reproduction and earlier experiments

Use the [configured Solar procedure](../experiments/real_komae_solar/README.md#configurable-reuse)
after its upstream Building/Terrain and Envelope prerequisites. The original
PR #99 invocation remains historical. Reuse requires files and provenance, not a historical PASS;
source hashes, engine identity and runtime requirements are in the owning records.
This documentation refresh did not rerun models or recheck local artifact hashes.

The [canopy-only experiment index](../experiments/voxcity_canopy_shadow/README.md)
retains Phase 2 execution, Phase 3 sensitivity and Phase 4 audits. Older
[komae_canopy.py](../../src/ouem/komae_canopy.py) uses separate provenance and
threshold assumptions; it is not the current Envelope or a full Standardizer.
These earlier experiments and tests remain evidence of their recorded conditions.
