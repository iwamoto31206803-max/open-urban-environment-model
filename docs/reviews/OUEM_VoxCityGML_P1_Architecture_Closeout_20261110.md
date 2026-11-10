# VoxCityGML / PoC-P1 — Architecture crosswalk & technical closeout (review proposal)

- Reviewed: **2026-11-10**, main `b9cbbe9addf6353935295f807c0083f66e19d0a7` (PR #175 merged).
- **Status: DOCUMENTATION REVIEW / PROPOSED; NOT Formal Acceptance.** This is a bounded source/code/record crosswalk, **not** a fresh local-data, package, or scientific rerun. It neither approves VoxCityGML as a production Adapter nor amends the registered Concept, Standards, licenses, or historic acceptance.
- Evidence owners: [P1-0](../experiments/voxcitygml_p1/P1-0_REPORT.md), [P1-1a](../experiments/voxcitygml_p1/p1-1a/P1-1a_REPORT.md), [P1-1b](../experiments/voxcitygml_p1/p1-1b/P1-1b_REPORT.md), [P1-1c](../experiments/voxcitygml_p1/p1-1c/P1-1c_REPORT.md), [P1-2a specification](../experiments/voxcitygml_p1/p1-2a/P1-2a_EXPERIMENT_SPEC_DRAFT.md), and [P1-2b results](../experiments/voxcitygml_p1/p1-2b/P1-2b_REPORT.md). Their original scope/values/decisions remain authoritative for each historical run.

## 1. Why this work exists and what stays unchanged

OUEM's objective is not to build a 3D model for its own sake. It is to evaluate human-scale urban tree functions from terrain, buildings, and canopy, notably B1 (Current / No-Canopy solar and shade) and B2 (360° canopy view), with interpretable GIS products. See the registered [Concept v0.2](../OUEM_Concept_Architecture_v0.2.md), inherited [v0.1 B1/B2 design](../OUEM_Concept_Architecture_v0.1.md), and adopted [Development Principles](../OUEM_Development_Principles_v0.1.md).

The November design review recognized that the reusable OSS calculation/geometry engines are not OUEM's unique responsibility. OUEM's lasting contribution is Japanese-source integration, semantic/provenance/rights/uncertainty control, physically comparable scenarios, independent verification, and municipality-scale delivery. This **reuses**, rather than replaces, the existing:
`Raw → Native → OUEM Standard → Engine/Analysis Adapter → VoxCity / analyses` boundary.

Concept v0.2 already treats detailed 3D buildings as **Primary** and 2.5D upper-height rasters as lossy **Derived**. VoxCityGML made a direct LoD2 mesh/voxel route technically plausible; it did **not** retroactively replace the [accepted Building Adapter](../OUEM_VoxCity_Adapter_v0.1.md), remove the useful 2.5D route, or ratify a new Standard.

## 2. Five-module *functional* view and responsibility allocation

The five modules below are a **cross-cutting functional inventory**, not a requirement to split source packages into five projects. This captures the substance of the 2026-11-06 function inventory and 2026-11-07 architecture review; candidate handoffs are not automatically accepted interfaces.

| Functional module | OUEM owns | Candidate external reuse / verified boundary |
|---|---|---|
| **① Terrain preprocessing** | DEM/DTM acquisition and meaning, vertical reference, NoData, temporal/source evidence, cross-layer compatibility | Existing VoxCity ground/voxel handling; VoxCityGML CityGML TIN → terrain is a **candidate, not P1-verified**. No unexplained DEM re-anchoring of original building Z |
| **② Tree/canopy preprocessing** | Canopy XY/presence/coverage, CHM/HAG, absolute top/bottom Z, inferred crown-base provenance, uncertainty; canopy-segmentation is a separate upstream supplier | Reuse VoxCity top/bottom TREE voxel support; VoxCityGML 3D vegetation and `reapply_canopy` are **unverified for a complete OUEM counterfactual** |
| **③ Building preprocessing** | PLATEAU / future GSI source ingestion, full 3D Primary, LoD/IDs, XY/Z/temporal provenance, 2.5D Derived and audit | Keep existing 2.5D VoxCity path; P1 established **bounded** VoxCityGML LoD2 geometry/merge-only mesh handling for F/S/M/C. A general GSI→OBJ path remains a candidate |
| **④ 3D integration / voxelization** | Common spatial/vertical/grid contract, classes, provenance, overlaps, scenario invariance, memory/resource gates and QA | Reuse pinned VoxCity voxel/ray infrastructure; VoxCityGML private mesh voxelization **worked for four isolated buildings** but is sensitive to contact shell, resolution, grid phase and API pin |
| **⑤ Urban environmental analysis** | B1/B2 metric definitions, Current / No-Canopy design, common observer/conditions, scientific validation, GIS outputs and application limits | Reuse VoxCity calculation kernels; existing B1/B2 bounded E2E is separately documented. P1-2b executed **binary building-shadow only**, not full B1 solar, canopy or GVI |

**Practical division:**
- **VoxCityGML** is a candidate supplier of CityGML detailed geometry, mesh repair and 3D voxelization, **not** the owner of OUEM's data meaning or scientific acceptance. P1 used only narrowly controlled lower-level/private APIs, not its unrestricted high-level pipeline.
- **VoxCity 1.7.0** supplies the established 2.5D voxel and solar/visibility calculation routes and P1's shared `trace_ray_generic` kernel. It does not select authoritative Japanese sources or validate physical correctness.
- **OUEM** owns source/Standard↔engine identities, original absolute H versus engine-relative height, original masks/unknowns, scene-condition equality, rights/attribution, outputs and independent evidence. Avoid duplicating generic geometry/ray kernels without an evidenced need.

## 3. Direct 3D is an additional candidate, not a bypass of Standard

```text
                         OUEM source/meaning/ID/CRS/Z/QA
                                      |
               +----------------------+---------------------+
               |                                            |
  Audited PLATEAU detailed LoD2                   Footprint / distributed
               |                                 roof-height / future GSI
    VoxCityGML mesh → voxel (P1)                 existing 2.5D VoxCity
               +----------------------+---------------------+
                                      |
                        Shared bounded scene / VoxCity ray
                                      |
                    B1/B2 (subject to their own gates)
```

P1 specifically audited original CityGML member, source ID, `ouem_id`, polygon/ring and retained H against frozen Native/Standard evidence. The implementation did **not** demonstrate a formally compliant generic Adapter. Two future **unselected** Adapter designs remain:
1. **Standard-shape-led:** derive mesh/engine input from approved complete Standard geometry.
2. **Audited-Raw-reference-led:** use original CityGML only under a SHA/ID/LoD/Z/geometry-bound correspondence to the accepted Standard.

Unreviewed Raw cannot bypass Standard QA. Never silently re-anchor original absolute Z to a DEM, substitute unknown for absent, change north-up/south-up or D0, or infer that equal array shape establishes equal observer XYZ. Existing Building/Terrain Standards remain PROVISIONAL; Canopy Standard is DRAFT. Both the accepted v0.1 Adapter and separate source-H/Mixed-LoD experimental paths keep their previous boundaries.

## 4. Original draft plan versus completed P1 evidence

The original *unapproved* P1 draft used a different stage numbering. Do not treat the names as identical or retroactively rewrite old run reports:

| Original 2026-11-07 draft gate | As-executed evidence | Closeout reading |
|---|---|---|
| P1-0 source/environment/rights | #170; independent environment in #171 | Source/selected API execution established; license redistribution/commercial review conditional |
| P1-1a synthetic calibration | Focused synthetic tests #171–173; independent solid-angle interior sampling #173 | **Partly covered**, not a one-to-one realization of every original calibration gate |
| P1-1b F building | Executed as **P1-1a / #171** | F LoD2 source correspondence, merge-only watertight mesh and mesh-only voxel PASS |
| P1-2 S/M/C and A/B/C shadow | #172–173 geometry/voxel; #174 comparison design; **#175** matched shadow | Four-building technical PASS at saved 1 m XYZ/one sun; independent original-LoD2 ray/triangle **shadow** oracle not executed |
| P1-3 reproducibility/operations | Each bounded run's duplicate evidence; #175 independent 101-output comparison; #173 timing | Bounded reproducibility PASS; peak memory and comprehensive deployment/legal conditions not established |

In the **as-executed** nomenclature, P1-1a/1b/1c and P1-2a/2b are distinct stages. Do not name this review “P1-3”: the original specification reserved that label for reproducibility/operations.

Key [P1-2b](../experiments/voxcitygml_p1/p1-2b/P1-2b_REPORT.md) evidence: F/S/M/C all Gates 1–5 PASS; 5,088 saved valid observers, **10,176 A/B classification matches with zero mismatch** before computing C; no extra C-origin exclusion; independent two-run manifest and **101 output SHA matches**. Same 1 m observer XYZ and sun azimuth 180°/elevation 45°, same VoxCity DDA ray kernel. A=representative 2.5D, B=cellwise-top 2.5D, C=LoD2 solid-derived voxels. C is **not ground truth**. F's C shadow is 14 sampled 1 m² observer cells shorter than B's; the 1 m difference of their voxel upper faces is a major numerical explanation, **not** an accuracy claim. Refer to the original [results and figures](../experiments/voxcitygml_p1/p1-2b/P1-2b_REPORT.md#結果) rather than duplicating its tables.

Pinned P1 environment: Python 3.11.9, **VoxCityGML 0.3.0 / `19628c033b1cbbbdee80fe781f516672765d1eee`**, **VoxCity 1.7.0 / `fa212656305328a9a657973bae26f352bfe813bc`**; separate P1 venv, not installed into the existing accepted OUEM runtime. P1 calls private `_voxelize_building_solid`, which is an upgrade/maintenance risk. Original P1 local datasets/large NPY/env snapshots are **not in Git**; repo code/docs/manifests alone are not a runnable data bundle.

## 5. Decision register after P1

**Supported direction, not new formal approval:** retain both 2.5D and detailed-3D candidates; prefer tested OSS components over rebuilding general kernels. The existing objective, Standard boundary and Primary/Derived distinction (original review D-01–05) remain unchanged. P1 technically supports **continuing** the direct LoD2 evaluation candidate (D-04), not completing universal adoption (D-11) or approving schema changes (D-12).

**Still requires explicit design review:** which Standard↔VoxCityGML route (D-13), private API stability/alternative, formal vertical/terrain alignment and model class/ID transfer; complete rights/third-party notices for the intended use (D-14); source observation time alignment (D-15); LandUse/water/baseline ground changes (D-16); processing tiles/halo versus management third-level mesh (D-10).

**Separate future hypotheses, not established P1 results:** GSI point-cloud/OBJ route, RGB+LiDAR late fusion (D-06–08), CityGML/TIN/vegetation support, general building classes/holes/bridges, municipality-scale performance and validation.

## 6. Deferred validation and Canopy handoff

| Priority / trigger | Deferred question and acceptance boundary |
|---|---|
| **Before claiming a formally integrated detailed-3D Adapter** | Select and test Standard-shape vs audited Raw-reference; pin and audit source/ID/Z/LoD, compatibility, namespace/classes, library notices and runtime; show local data/hash reproducibility. No formal acceptance is implied by this document |
| **Before claiming independent real-shadow accuracy** | Validate ray intersections against original LoD2 triangles with independent geometry, physical observer/DEM alignment, voxel-grid/contact-shell/phase sensitivity; P1-1c solid-angle occupancy oracle is **not** a shadow-ray oracle |
| **Before broadening eligible geometry** | Representative hole/complex topology, nonmerge repair/fallback, missing ground, LoD/source heterogeneity and object coverage; four tested buildings had no actual holes |
| **Before resource/municipality-scale claims** | Measure full-run memory/cost and wider scene/halo/edge convergence, more resolutions, multiple suns, robust dependency reproducibility |
| **Before solar/GVI/canopy-scene claims on the P1 mesh route** | Integrate terrain, building and canopy at **one actual engine grid/vertical origin**, preserve classes/observer XYZ; remove **all canopy origins** for No-Canopy (including CityGML vegetation if used), not only CHM-derived TREE, while holding Building/Ground/land cover and conditions fixed; validate optical and GVI metric meaning separately |

At the close of P1-2b: **technical execution PASS within four isolated buildings**, `scientific_validation=NOT_VERIFIED`, `formal_acceptance=NOT_VERIFIED`, `terrain_integration_ready=false`. These are independent status axes. This review proposes **closing the bounded technical experiment**, **not** approving its production path. The next Canopy work can use the already functioning Height Envelope/voxel/B1/B2 experiments without waiting for detailed-3D formal adoption. Do not treat merging a documentation PR as changing any approval gate.

## 7. Source-draft provenance and document maintenance

This note **distills, rather than imports verbatim**, the original unapproved review materials. The archived copies were consulted outside Git. The identifiers below allow later exact matching, but hashes alone do not make a copy available from a Git clone. Their 2026-11-06/07 implementation status and proposed external API claims are **historical**, not a fresh upstream-version audit.

| Original local draft (unapproved) | SHA-256 |
|---|---|
| `OUEM_Function_Inventory_v0.1_DRAFT_20261106.md` | `93ec65f347ab898237c4dec3aacadd249ce9c8b572dd26616b46ad1b5d186421` |
| `OUEM_Architecture_Review_and_Design_Change_DRAFT_20261107.md` | `00431bb628f76c1272bd4651678de6c970bd0a8ba7b20983d22e38adb4b42321` |
| `OUEM_Architecture_Review_and_Design_Change_DRAFT_v0.2_20261107.md` | `ebb2df9deabe4d9f8cd6782b5c7da454b52c9b9fc64f3613da3547595da98502` |
| `OUEM_PoC_P1_Specification_DRAFT_v0.1_20261107.md` | `ccaa164c975ce6e03a4e32167ac71b858c7f2af6a0d86bad2d42c1f94336777e` |

No historical reports/manifests, source/tests, original archives, registered Architecture, Standards, approved Adapter, acceptance, or proposed Documentation Governance are modified. This single note owns the **review crosswalk**; the linked P1 records own numerical/execution evidence; [README](../../README.md) and [Building Current State](../status/BUILDING_CURRENT_STATE.md) are navigation only. Reconsider verbatim archival only if maintaining the condensed decision rationale proves insufficient.

**Documentation impact:** one new review note; two small navigational references; no runtime tests needed for this documentation-only change. Validate links/headers/diff and unchanged existing contract/evidence bytes before review.
