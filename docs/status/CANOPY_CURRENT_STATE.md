# Canopy Current State

Current documentation checkpoint: **2026-11-19**, through merged PR #203
(`18d7cc272af5fca948239f4702297509954e72e8`).
This is a review of repository code, GitHub execution reports and historical
evidence, **not** a new local execution or independent rereading of the private
`comparison.json` bytes. This [informational entry point](../OUEM_Documentation_Governance_v0.1.md)
does not change formal data contracts, scientific validation or acceptance.

## Roadmap M1: bounded Meta CHM → VoxCity TREE technical checkpoint

The following is a **limited technical success, not overall M1 or Standard Canopy
acceptance**. The record concerns the single saved Komae PR #99
Building+Terrain+Meta scene and its actual engine centres; it does not
establish that the Meta predictions are field-correct.

| Checkpoint | Evidence and attained scope |
|---|---|
| Frozen source/run identity | [#195](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/195): an independent 88-file copy passed identity checks against the pinned PR #99 reference; this is not new source accuracy validation. |
| Logical Meta canopy presence → engine centres | [#196 / PR #197](https://github.com/iwamoto31206803-max/open-urban-environment-model/pull/197): synthetic two-stage mapping, preserving source-modelled PRESENT/ABSENT/UNKNOWN independently of height validity. |
| Actual saved-tree diagnostic | [#198 / PR #199](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/198): source CHM → historical north-up EPSG:6677 Envelope grid → saved `uv_m/SOUTH_UP` VoxCity centres, compared with **previously saved** TREE; no new voxelization in this step. |
| Common input → new TREE | [#200 / PR #201](https://github.com/iwamoto31206803-max/open-urban-environment-model/pull/201): complete-validity Meta fields and compatible absolute top/bottom Z reach the existing public VoxCity voxelization through `integrate_common_canopy`; synthetic placement and Building priority checks. |
| Real new-TREE full-array comparison | [#202 / PR #203](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/202): Codex reports one GEEKOM-A6 run against the independent copy, and **MATCH** against stored Current, No-Canopy and TREE mask at every voxel of each 128×128×27 array, with **0 differences** both scene-wide and inside the 64×64 ROI. |

In the frozen 128×128 scene, **16,384** sampled centres had source-supported,
source-valid and absolute-Z-valid data: Meta-modelled PRESENT **11,741**,
modelled ABSENT **4,643**, UNKNOWN **0**. New and saved TREE each had
**11,175 occupied columns / 95,735 voxels**. The saved 64×64 evaluation ROI had
PRESENT **3,842**, ABSENT **254**, UNKNOWN **0**, and matching TREE
**3,742 columns / 34,632 voxels**. The **566** scene and **100** ROI
model-positive columns without final TREE remain `UNRESOLVED` *in this
diagnostic*; historical PR #99 separately attributes 566 fully suppressed
candidate columns to Building precedence, but the new diagnostic did not
independently establish column-by-column cause.

This establishes reproducible output for **one complete-validity Meta profile**
with the **same underlying VoxCity engine and historical source/height inputs**.
It does not show arbitrary-domain/UNKNOWN support, a source-neutral GSI
producer, an accepted Native/Standard Canopy implementation, broad-area transfer,
independent ecological accuracy, or calibrated Solar/GVI physics. Formal
Standard Canopy remains **DRAFT**; design/inventory issues
[#178](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/178),
[#179](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/179),
[#183](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/183) and
[optional geometry/raster PoC #184](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/184)
remain open, and do not become automatically completed by #202.

The executable diagnostic owner is
[`komae_saved_tree_comparison.py`](../../src/ouem/komae_saved_tree_comparison.py);
the public-engine consumer remains
[`real_komae_solar.py`](../../src/ouem/real_komae_solar.py).
See #202 for the local execution record and exact hashes; retained experimental
outputs and source manifests are **not** replaced by this status summary.

## Earlier milestone: B1 technical E2E closeout

The exploratory Komae path combines source-H Building, Standard Terrain and an
estimated Meta CHMv2 Height Envelope on the actual VoxCity grid, then compares
Current / No-Canopy direct irradiance. Configured A/B reuse, shared upper Z and
GIS/QGZ/GUI verification are recorded in the [B1 technical closeout](B1_TECHNICAL_MILESTONE_CLOSEOUT.md).
Full scientific validation is deferred to the [backlog](../planning/OUEM_B1_Deferred_Validation_Backlog.md).
At the PR #121 checkpoint B2 was not yet implemented; the later
[B2 technical closeout](B2_TECHNICAL_MILESTONE_CLOSEOUT.md) confirms bounded
Komae CPU green-view E2E, with scientific validation deferred. Original PoC
[PR #99 procedure](../experiments/real_komae_solar/README.md) and
[executed results](../experiments/real_komae_solar/RESULTS.md) own the methods,
metrics, input/output identities and boundary diagnostics.

It reuses [PR #97 source-H Building](../experiments/real_komae_source_h/README.md)
([results](../experiments/real_komae_source_h/RESULTS.md)) and
[PR #98 Building/Terrain voxels](../experiments/real_komae_voxel/README.md)
([results](../experiments/real_komae_voxel/RESULTS.md)). The
[Building Current State](BUILDING_CURRENT_STATE.md) distinguishes this
experimental lane from the accepted v0.1 path.

## Relationship to later municipality and Mixed-LoD work

The [Kunitachi source preflight](../planning/OUEM_Kunitachi_Data_Source_Preflight_v0.1.md)
records CHMv2 coverage/reading only; no Kunitachi Height Envelope, TREE voxel,
Solar or GVI execution is established. The [Candidate B Mixed-LoD T5 closeout](../experiments/real_komae_source_h/MIXED_LOD_CANDIDATE_B_T5_4_CLOSURE.md)
was a Building + experimental Terrain model **without Canopy at the T5 checkpoint**.
Its [E0 shadow test](../experiments/real_komae_source_h/MIXED_LOD_CANDIDATE_B_E0_SHADOW.md)
was synthetic-only at that earlier stage. Subsequently,
[STEP 2-C1](../experiments/real_komae_source_h/STEP2C1_EXPERIMENTAL_HEIGHT_ENVELOPE.md)
generated a Candidate B experimental Height Envelope and
[STEP 2-C2](../experiments/real_komae_source_h/STEP2C2_REAL_CANOPY_INTEGRATION.md)
created a real saved Current/No-Canopy pair. The same model reached
[direct Solar](../experiments/real_komae_source_h/STEP2C3_REAL_SOLAR.md)
and [CPU weighted first-TREE view index](../experiments/real_komae_source_h/STEP2C4_REAL_GVI.md)
with common saved observer positions and EPSG:6677 registration.
These are **experimental technical E2E** results, not verified crown presence,
calibrated optics, field GVI, approved terrain integration or formal acceptance.
Neither track supersedes the bounded B1/B2 evidence or changes the draft
Standard Canopy/acceptance state.

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
Source-polygon profiles still require review of original polygon geometry
and IDs where such source data are admitted; a derived polygon is **optional**
for the CHM/raster-first analysis path under Concept v0.3. Full Native / Standard
Canopy production and formal acceptance remain incomplete; the Canopy
namespaces are placeholders.
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
