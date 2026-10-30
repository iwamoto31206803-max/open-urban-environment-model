# B1 Technical E2E Milestone Closeout

Checked **2026-10-30**, main `53c5067d72c62631fdbfd949077faedaab604316`
(PR #121 merged). **The bounded Komae B1 Technical E2E Milestone is complete.**
Full B1 scientific validation is deferred at the user's direction; B2 development
is next, but is not implemented or authorized for implementation by this document.
This is a technical status summary, not an Acceptance record or precision standard.

## Scope and completion evidence

The demonstrated scope is prepared Komae Building/Terrain/estimated Canopy,
nominal 1 m VoxCity cells, existing input coverage and two configured rectangular
A/B scenes under one artificial sun condition. The original PR #97–99 PoC,
PR #106–109 reuse/shared-Z work and PR #113–118 GIS work are distinct evidence
stages; this closeout does not relabel their historical outcomes.

| Technical completion condition | Implementation / execution evidence | Boundary |
|---|---|---|
| Existing data can be transformed into VoxCity inputs using documented rules | [Source-H preparation](../experiments/real_komae_source_h/README.md), [H/Terrain results](../experiments/real_komae_source_h/RESULTS.md); [Voxel procedure](../experiments/real_komae_voxel/README.md) and [original results](../experiments/real_komae_voxel/RESULTS.md); [Envelope contract](../CHM_Height_Envelope_PoC_v0.1.md) | Source-H XY conversion retains H; whole Building footprints/roof proxies become 2.5D. Estimated raster Envelope is not the full proposed Standard Canopy lifecycle. |
| Fixed-condition direct irradiance executes using pinned VoxCity CPU calculation and default optics | [Solar procedure](../experiments/real_komae_solar/README.md), [parameter audit, PR #119](../planning/OUEM_B1_VoxCity_Parameter_Baseline_Audit_v0.1.md), [synthetic sanity, PR #120](../experiments/real_komae_solar/B1_PHYSICAL_SANITY_PHASE1.md) | Horizontal direct irradiance only; default values and synthetic agreement do not establish physical calibration. |
| Current / No-Canopy / Difference are generated and viewable in GIS | [A/B reuse and shared-Z completion](../experiments/real_komae_solar/README.md#phase-3c-shared-z-real-data-verification--2026-10-29-jst); [QML/manifest](../experiments/real_komae_solar/README.md#qml--manifest-visualization); [helper GUI smoke](../experiments/real_komae_solar/README.md#gis-helper-gui-smoke-2026-10-29-after-pr-116); [QGZ creation/reopen/GUI](../experiments/real_komae_solar/README.md#qgz-project-generation) | A/B verified with QGIS 4.2.3. Ordinary provider Identify is a display-grid query, not exact original-cell lookup. |
| Inputs, conditions and outputs are traceable | [Saved configuration and Voxel handoff](../../src/ouem/e2e_config.py); producer/Consumer hashes, manifests, preserved submitted configuration, receipt, reports, grid/centres and output identities in the above records | Hash/receipt consistency is not authenticated execution or data accuracy. Cloning Git supplies neither local data nor an eligible run. |
| Limitations and future work remain visible | [Saved geometry/observer diagnostics, PR #121](../experiments/real_komae_solar/B1_GEOMETRY_OBSERVER_PHASE2.md); [deferred backlog](../planning/OUEM_B1_Deferred_Validation_Backlog.md) | Scientific checks, acceptance and applicability remain separate decisions. |

The five conditions above are met **for this technical scope**. PR #107's recorded
B Z-capacity failure remains a historical failure; shared-Z completion in later
runs does not rewrite it. Metrics, input hashes, figures, commands and individual
test results remain in their owning records rather than being copied here.

## Current state and acceptance boundaries

| Area | Implemented / execution-confirmed | Still unverified or unimplemented |
|---|---|---|
| Phase A accepted v0.1 | Dataset-bounded [Building pilot](../../experiments/a1_e2e_pilot/README.md), [A2 Terrain](../acceptance/OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md), [A3 Adapter/voxel](../acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md), [contained E2E](../acceptance/OUEM_Komae_Contained_E2E_Acceptance_20261018.md) | These do not accept the experimental mixed source-H B1 lane, all of VoxCity, B2, or nationwide operation. Implementation A2/A3 labels differ from conceptual national variants. |
| Building and Terrain | Both Standard contracts remain **PROVISIONAL**. Accepted v0.1 ingestion/Adapter and separate experimental source-H Native/Standard/Consumer are implemented | Source-H eligibility **NOT_ESTABLISHED**; mixed-lane Formal Acceptance **NOT_VERIFIED**. The v0.1 Adapter manifest whitelist is unchanged. Surveyed geometry/datum accuracy is not established. |
| Height Envelope / Canopy | CHMv2 acquisition/crop, estimated top/bottom/state, actual-centre sampling and TREE integration executed. Positive crown depth and masks are checked; Building has occupancy priority | Standard Canopy remains **DRAFT**; Native/Standard Canopy namespaces are placeholders. Canonical canopy polygons, ecological presence, CR and optical calibration are not accepted/verified. |
| A/B Voxel / Solar | Configured rectangle and Run-ID reuse; actual shared grid, D0/Building/Ground preservation, paired observers, positive modeled canopy effect and GIS results recorded | Scope is existing prepared coverage/conditions. Physical observer heights and D0 rounding affect interpretation; within-run paired observers do not imply identical physical observation heights across A/B. |
| GIS | QML/manifest generation, alpha-safe application, exact source-cell lookup, QGZ generation, separate-process reopening and actual A/B GUI checks recorded | Other QGIS versions and real-bundle GUI relocation are unverified. QGZ references TIFFs rather than embedding data. New Phase 2 diagnostic TIFFs were numerically checked, not separately GUI-accepted. |
| PR #119–121 | Installed-default ledger; independent synthetic direction/shadow/attenuation checks; saved real geometry/observer consistency diagnostics | No field radiation validation, true crown/roof validation or new scientific acceptance. See backlog for the distinction between known approximation and unverified accuracy. |
| Next B2 | [Concept v0.2](../OUEM_Concept_Architecture_v0.2.md) and inherited [B2 design in v0.1](../OUEM_Concept_Architecture_v0.1.md#7-b2-----green-view-assessment) define the reference direction | No OUEM B2 analysis runner, settings or result contract is implemented. Existing generic model/Canopy namespaces are not B2 functionality. |

Phase 5 A1–A4 remain **OPEN** under the existing
[gate review](../experiments/voxcity_canopy_shadow/PHASE4_COMPLETION_GATE_REVIEW_20261027.md)
and [draft integration plan](../experiments/voxcity_canopy_shadow/PHASE5_INTEGRATION_PLAN_v0.1_Draft.md).
Closing this technical milestone does not approve them, finalize a Standard,
adopt the proposed Documentation Governance, or establish scientific accuracy.

## Defaults versus external experimental conditions

Pinned engine: VoxCity **1.7.0**, commit
`fa212656305328a9a657973bae26f352bfe813bc`; no dependency update.

| Condition | Meaning |
|---|---|
| `tree_k=0.6`, `tree_lad=1.0`, requested `view_point_height=1.5 m`, `include_building_roofs=False` | OUEM explicitly supplies values equal to the active CPU API defaults. Actual observer placement follows voxel-surface/index conventions, not a guaranteed DEM+1.5 m. |
| Azimuth 135°, elevation 35°, DNI 800 W/m² | Required external inputs explicitly fixed by OUEM; **not VoxCity defaults**, actual weather or a documented date/time event. |
| Nominal 1 m, EPSG:6677 analysis reference, 32 m context, CR=0.60 Envelope | Existing scene/input choices; actual VoxCity centres and geographic TIFF affine remain authoritative. CR is crown geometry, not k/LAD or the unused fallback trunk ratio. |

## Preserved evidence and transition to B2

The [Solar guide](../experiments/real_komae_solar/README.md) owns reproducible
commands and local evidence paths: original PoC, Phase 3C configured A/B runs,
GIS/helper/QGZ records and PR #119–121 diagnostics. Selected saved configuration,
receipt, 3D/observer/Solar files and A/B QGZ paths exist locally at this check;
the [housekeeping audit](../planning/OUEM_B1_Closeout_Housekeeping_Audit_20261030.md)
records the static availability method. **No new model run or full data rehash
was performed by this closeout.** PR #121's immutability verification remains
its own dated evidence, not a fresh closeout certification.

For later reuse, require actual inputs/manifests and frozen run bindings; use
new output IDs, preserve original bytes and source-implementation references,
and keep OUEM and GIS Python separate. Never repair a historical hash after
moving code or treat a newer result as the older execution.

Next B2 planning should begin with the Concept owners and
[shared/deferred issue IDs](../planning/OUEM_B1_Deferred_Validation_Backlog.md),
then assess reuse of saved classes/IDs/centres/masks, input provenance and GIS
helpers. A B1 solar observer convention, transmission model or scalar QA must
not silently become a B2 definition. No common output framework, new green-view
algorithm or preparatory refactor is introduced here. Deferred B1 science is
preserved for an explicitly scoped restart, not a new gate blocking all B2 work.
