# OUEM Standard Canopy v0.1 — Draft

**Status:** PROPOSED / DRAFT — design only; not an accepted Standard contract or implementation.
**Scope:** Source-profile-aware canopy horizontal evidence, absolute-Z envelopes and optional geometry exports for the initial Komae PoC and future CHM-source interchangeability.
**Authority:** [OUEM Concept & Architecture v0.3](OUEM_Concept_Architecture_v0.3.md) takes precedence. This draft does not modify accepted Building, Terrain, or VoxCity Adapter contracts. The 2026-10-25 and 2026-11-11 decisions below remain dated history; §14 records the later v0.3 alignment.

## 1. Purpose and architecture

Represent canopy horizontal presence evidence and vertical envelopes in a source-profile-aware, engine-independent way: a modelled CHM/segmentation raster may be the horizontal basis, while an accepted source polygon remains the horizontal basis when such input exists. The flow is Raw → Native → OUEM Standard → Engine/Analysis Adapter → VoxCity. Acquisition does not itself establish Standard acceptance. The CHMv2 AOI crop is an acquisition artifact, not a Standard Canopy raster.

Native retains source-specific height semantics, original grids, original polygons where supplied, masks, and acquisition evidence. Standardization validates source meaning and combines horizontal presence evidence with compatible height and bare-earth terrain for canonical absolute-Z envelopes, retaining independent validity and provenance. VoxCity-specific resampling, relative heights, collision policy, and voxelization belong to the Adapter. **Derived 2D polygons and generic 3D meshes are optional external geometry outputs, not mandatory steps between CHM and VoxCity.** Preserve the existing `komae_canopy.py` experimental workflow; do not treat it as the Standardizer.

## 2. Proposed logical data and output bundle

This section describes **logical information first**, not an adopted file schema or a requirement to materialize every intermediate. The horizontal basis depends on the source profile. Separate source-modelled presence, source/assessment validity, independent ecological survey coverage (if any), height validity and DEM validity; do not collapse them into one flag or one numeric code.

| Candidate representation | Semantics | Applicability and status |
| --- | --- | --- |
| Horizontal presence evidence + assessment domain | Explicitly reproducible modelled present/absent/unknown for CHM/mask profiles; original polygons and their source assessment evidence for polygon profiles | **Common logical requirement; storage/serialization unresolved** |
| `canopy_top_z.tif` | Canopy top **absolute elevation** in metres, with datum and validity | Concept requirement; filename/packaging proposed |
| `canopy_bottom_z.tif` | Canopy bottom **absolute elevation** in metres, with inferred-base provenance | Concept requirement; filename/packaging proposed |
| `canopy.manifest.json` | Source profiles, CRS/GridSpec, model/height/coverage evidence, rights, parameters, SHA and QA | Proposed metadata packaging |
| Optional presence/assessment raster(s), e.g. `canopy_state.tif` | One possible durable rendering of separate logical state axes | **Optional materialization; encoding and filename unresolved** |
| Source `canopy.gpkg` (when supplied) | Retained accepted original canopy polygons and IDs | Source-polygon profile only; no synthetic replacement |
| Derived 2D polygon / generic 3D mesh | On-demand GIS/visualization/other-model outputs, with own QA and source links | **Optional outputs, not the VoxCity input gate** |

A modelled CHM presence rule can be reconstructed from retained source samples, effective masks, sampling conditions and decision rules without always writing a separate raster file. A derived polygon is not an independently surveyed polygon or independent evidence of presence. VoxCity voxels are Adapter-specific outputs; LAD and transmissivity remain **unset**, not zero. Building/canopy 2D overlaps are permitted; 3D collision handling is downstream.

## 3. Coordinates and grid

- Use the study-area projected horizontal CRS; Komae profile: EPSG:6677, metres.
- Top and bottom are absolute elevations with explicitly recorded vertical reference, not HAG. Horizontal EPSG alone does not establish vertical reference.
- Do not relabel vertical coordinates or assume a transformation. Ground DEM and height inputs must have validated compatible semantics; unresolved vertical-reference status blocks accepted absolute-Z generation.
- Komae **candidate execution profile**: north-up, unrotated 1 m grid, aligned to integer-metre EPSG:6677 boundaries; extent outward-rounded to cell boundaries. This is **not** a nationwide fixed-resolution Standard.
- Record a deterministic GridSpec (CRS, resolution, bounds, affine transform, width/height, alignment, cell-centre convention). All output rasters must match it exactly.
- Retain accepted Standard Terrain v0.1 at its native 0.5 m grid; sample it onto the Canopy execution grid without modifying its canonical artifact. Terrain v0.1 itself does not resample.
- CHM candidate resampling: nearest neighbour, preserving source masks/NoData. Terrain candidate: nearest neighbour for reproducible initial PoC, compare against bilinear with explicit masked-neighbour rules before finalizing.
- **Source-polygon profile only:** a polygon-to-mask candidate labels a cell present when its centre is inside the accepted polygon union; define boundary tie behaviour and quantify area differences/lost small polygons. **CHM/mask profiles do not require polygonization before raster analysis.**
- Do not claim seamless adjoining AOI outputs solely from common grid alignment; source coverage, clipping, and boundary handling also require QA.

## 4. Horizontal presence evidence and coverage contract

- **CHM / segmentation profile:** preserve source values, masks, inference provenance and assessment domain. The modelled presence decision is a separately traceable interpretation, which may be computed when needed from supported valid samples. It does not establish independently surveyed canopy existence or absence.
- **Source-polygon profile:** retain accepted Polygon/MultiPolygon and contiguous canopy, without requiring individual-tree segmentation. Original geometries and identifiers remain available unchanged; validate source geometry and source IDs at admission to Standard. Candidate metadata include deterministic `ouem_id`, nullable `source_id` and mandatory dataset provenance; exact stable-ID and repair rules remain unresolved.
- **Overlap and footprint:** source polygon overlaps may be retained, with a candidate union mask for analysis and documented overlap diagnostics. Independently surveyed ecological coverage (where evidenced), model-assessment domain, raster-source spatial support, modelled absence, and unassessed/unknown areas must remain distinguishable. A missing polygon or CHM NoData cell is not proof of canopy absence.
- **Derived geometry export:** optional polygonization of the modelled-present raster uses explicitly recorded source/GridSpec/algorithm and its own QA. The exported geometry never replaces a source polygon and is not required for VoxCity analysis.

## 5. Height semantics and crown-base model

For a valid canopy cell `i` with terrain absolute elevation `G_i`, CHM height above ground `H_i`, and crown ratio `CR_i`:

```text
Z_top[i]    = G[i] + H[i]
Z_bottom[i] = G[i] + H[i] * (1 - CR[i])
crown_depth[i] = Z_top[i] - Z_bottom[i]
```

The source must explicitly establish that CHM is a height-above-ground quantity in metres. A source name, raster CRS, or plausible values alone do not prove that meaning. Record provenance and source hashes. In particular, the Meta/WRI CHMv2 acquisition output and its provenance must be bridged/validated explicitly; do not assume compatibility with the legacy `komae_canopy.py` provenance schema.

**CR model interface:** versioned, replaceable estimation algorithm with recorded inputs, parameters, applicability, and per-output provenance. Initial Komae **candidate** is `constant_cr_v0.1`, `CR=0.60`, corresponding to legacy bottom HAG = 0.40 × tree height. This is a continuity choice, not an empirically validated ecological default or a permanent Standard requirement. Later models may be class-based or spatially varying without changing the Standard top/bottom contract.

Candidate CR domain: `0 < CR <= 1`. A canopy-present cell with invalid, missing, negative, or zero height is not **generally** declared canopy-absent; presence and height validity are distinct axes. The Meta CHMv2 **model-specific** effective-valid `H=0` interpretation in §14 is not an independent ecological absence claim and must not be generalized to GSI mask-positive/height-missing cells. Minimum-tree-height thresholds, if used by analysis, are configurable and documented; do not silently apply the legacy 3 m cutoff to Standard.

For valid cells, require finite `G`, `H`, `CR`, and `G <= Z_bottom <= Z_top`. Distinguish top-height evidence from inferred bottom-height evidence. Do not infer unobserved bottom as measured.

## 6. State, NoData, and uncertainty

**The logical information is multi-axis; no universal numeric state schema is adopted here.**

| Logical axis | What must remain distinguishable |
| --- | --- |
| Source support / native validity | In-source coverage, effective source mask, invalid/NoData, outside-source and unprocessed |
| Modelled presence / assessment | Modelled present, modelled absent, unknown or not assessed, with model identity and decision rule |
| Independent ecological assessment | Surveyed coverage/presence/absence **only when independently supported**; otherwise NOT_VERIFIED |
| Height and terrain validity | Numeric HAG availability/physical meaning, independent DEM validity, compatible absolute top/bottom-Z availability |
| Engine occupancy / analysis validity | TREE voxel presence, building overwrite, observer/context/halo and whether B1/B2 analysis is valid; owned by Adapter, **not** ecological absence |

**Historical unratified codes from the earlier polygon-first proposal:** 0=inside verified survey coverage/no polygon; 1=polygon with valid heights; 2=polygon with missing heights; 3=polygon with inconsistent heights; 255=outside verified survey coverage. These were **never adopted** and must **not** be treated as the current raster-profile state encoding or as interchangeable with Height Envelope's numeric-validity `state==1`. Exact datatype, numeric codes, NoData and materialized file count remain separate decisions.

Where an absolute top/bottom is invalid it must not silently be fabricated as zero height. A Standard candidate may preserve partial height evidence and still pass relevant structural QA, while the Adapter must separately decide and document whether a particular model/analysis can proceed. Any imputation is separately versioned and provenance-bearing.

## 7. QA and acceptance gates

**Common structural and semantic QA for the applicable profile:** horizontal CRS/GridSpec/affine, supported source meaning and effective masks, model assessment domain versus surveyed coverage, height/DEM/absolute-Z compatibility, missing-versus-modelled-absent, finite values and `top >= bottom >= ground` where valid, CR provenance, model/source identities, rights, hashes and deterministic rerun evidence.

**Conditional geometry QA:** if original polygons are the accepted horizontal basis, validate their IDs and geometries on Standard admission. If derived 2D polygons/3D meshes are generated or used, check their own shape, holes, areas, boundary/quantization effects, vertical compatibility and source links. **Optional geometry export QA must never be a prerequisite for the CHM/raster → VoxCity analysis lane.**

**Adapter QA:** voxel dimensions, actual engine centres/orientation, D0/effective ground, rounding/thin crowns, Building precedence and pre-/post-overwrite TREE diagnostics, data/context/halo uncertainty and observers. Distinguish modelled source absence from an empty TREE voxel and from analysis-invalid/unknown regions.

**Distinct gates:** (1) synthetic logical/contract tests, (2) bounded real-input technical checks only after authorization, (3) separately reviewed Native/Standard Canopy contract/data acceptance, and (4) downstream Building/Terrain/Canopy → VoxCity technical/analysis acceptance. Success in one gate is not scientific field validation (Roadmap M3) nor approval for the other gates. Existing Building and Terrain acceptance remains unchanged; vertical-offset concerns are not silently compensated.

## 8. Komae candidate PoC profile

- AOI: `config/study_areas/komae_09LD3451.yaml` (EPSG:6677; x=-23600..-23200, y=-40800..-40500; 400 × 300 m).
- Canopy grid candidate: 1 m, 400 × 300 cells when the AOI is used exactly.
- CHM candidate: Meta/WRI CHMv2, from the separately audited AOI acquisition; source crop is EPSG:3857, not a canonical Standard raster.
- Terrain: accepted Komae Standard Terrain (0.5 m, EPSG:6677, source-declared T.P.), subject to verified compatible source semantics.
- CR candidate: constant 0.60.
- **Complete Standard Canopy acceptance (deferred):** independently review a source-profile-appropriate horizontal evidence/assessment domain, compatible absolute top/bottom-Z, provenance/rights, NoData and structural QA. A **polygon source is required only for an original-polygon-based profile**, not for CHM/raster-first input. The current Height Envelope PoC remains experimental; Meta-derived polygons, if exported, are additional model geometry and cannot stand in for independent source polygons or ecological survey coverage.
- No CHMv2-vs-LiDAR comparison is required before this end-to-end PoC. Source interchangeability is a contract objective; comparative performance assessment is deferred.

## 9. Open decisions and validation plan

1. Source-profile horizontal evidence acceptance and assessment-domain documentation, including original polygons if the source supplies them.
2. Reproducible modelled presence/unknown rule and source-specific validity, independent height/DEM validity, and provenance; exact output packaging and numeric codes remain unresolved.
3. Terrain nearest-vs-bilinear comparison and masked interpolation behaviour.
4. CR=0.60 sensitivity, zero/low-height treatment, later spatial CR and resulting TREE rounding.
5. Vertical compatibility, building/terrain/canopy offset checks and real engine-grid correspondence.
6. Required versus optional on-disk materialization, output names, hashes and deterministic serialization, without mandatory geometry conversion.
7. Native/Standard/Adapter data contracts, full Canopy Standard acceptance, unknown/halo policy and source rights.
8. **Optional geometry export only:** polygon ID/component connectivity, cell-centre boundary ties, hole/area QA, and deferred generic 3D mesh format/LAD/transmissivity. No arbitrary universal tree-height cutoff.

## 9A. Deferred polygon integration and phased execution (design review note)

**Historical decision note:** The text below preserves the 2026-10-25 polygon-first plan as it stood then. The later, formally adopted [Concept v0.3](OUEM_Concept_Architecture_v0.3.md) supersedes its **universal polygon requirement**; consult §14 for the current candidate workflow. This annotation does not rewrite the archived execution evidence.

**Decision (2026-10-25):** Retain canopy polygons and coverage semantics as required capabilities of the complete Standard Canopy architecture, but **defer acquisition/generation of real Komae canopy polygons**. Their absence does **not** block the next CHM + DEM + CR vertical-envelope PoC.

**Immediate next phase (height-envelope PoC, not full Standard acceptance):** Verify CHMv2 height semantics and masks, sample CHM and the accepted Terrain to a documented candidate GridSpec, derive cellwise absolute top/bottom Z using a versioned configurable CR model, record provenance and QA, and inspect integration feasibility with the existing experimental VoxCity canopy path. A synthetic canopy mask may be used for focused unit tests; no real polygon or asserted survey coverage is required for this limited experiment.

**Future required phase:** Establish a polygon-generation/acquisition route, Native Canopy Polygon input contract, polygon/CHM combination, surveyed-coverage footprint, presence-versus-absence semantics, and end-to-end acceptance. CHM-derived polygons may be considered if generated as an explicit versioned, provenance-bearing artifact; they are not independent validation of the CHM.

**Acceptance boundary:** A height-envelope-only PoC output is explicitly **experimental/partial** and must not be labelled accepted complete Standard Canopy. Do not fabricate canopy presence, surveyed absence, or coverage from the CHM. Do not change the Concept v0.2 canonical three-part representation or silently weaken its polygon requirement.

## 10. Design decision register

The statuses below distinguish the Concept baseline, explicitly selected candidate decisions, and assistant-proposed details. No item in this document constitutes a formally accepted implementation.

| IDs | Subject | Status |
| --- | --- | --- |
| SC-01–SC-10 | Historical polygon-first proposal, absolute top/bottom, provenance, missing-vs-absent, Adapter boundary | Historical proposed SC register; **horizontal basis superseded by Concept v0.3**; packaging unratified |
| SC-11 | Cell-centre rasterization, preserve source polygon | **User-selected candidate** |
| SC-12 | CHM nearest; validate DEM resampling | **User-selected candidate** |
| SC-13 | Cellwise absolute top/bottom from CHM + terrain | **User-selected candidate** |
| SC-14 | Standard owns absolute Z and CR; Adapter owns voxelization | **User-selected candidate** |
| SC-15–SC-18 | Polygon metadata/overlap, state, QA, missing-data acceptance | Proposed; not yet formally ratified |
| SC-19–SC-22 | Independent GridSpec, Komae 1 m alignment, DEM resampling | Proposed; not yet formally ratified |
| SC-23–SC-27 | Replaceable CR model, candidate 0.60, QA and sensitivity | Proposed with user endorsement of **extensibility**; numeric default not formally ratified |

## 11. Related existing contracts

- [Concept & Architecture v0.3](OUEM_Concept_Architecture_v0.3.md) (current formal upper concept); [v0.2](OUEM_Concept_Architecture_v0.2.md) (historical)
- [Standard Terrain v0.1](OUEM_Standard_Terrain_v0.1.md)
- [Standard Building v0.1](OUEM_Standard_Building_v0.1.md)
- [Standard-to-VoxCity Building Adapter v0.1](OUEM_VoxCity_Adapter_v0.1.md)

**Non-goals of this document-only PR:** no code, no dataset generation, no test-result claims, no changes to accepted contracts, no declaration that Komae Standard Canopy has been accepted.

## 12. Implementation status and evidence (informational, 2026-10-27)

Checked against main `8ab89df1041077fa549e76df29d130718afe72b8`, after PR #78.
This section closes documentation gaps identified by the [consistency review](reviews/OUEM_Standard_Canopy_Consistency_Review_20261027.md);
it adds no design decision or acceptance. This DRAFT retains design requirements
and candidates; [Canopy Current State](status/CANOPY_CURRENT_STATE.md) is the
entry point for current implementation, evidence and open issues under the
[documentation governance](OUEM_Documentation_Governance_v0.1.md).

**Implemented and technically verified, within Experimental scope:**
[Meta CHMv2 AOI acquisition](Meta_CHMv2_AOI_Acquisition_PoC.md),
[CHM + Terrain + CR Height Envelope generation](CHM_Height_Envelope_PoC_v0.1.md),
and the limited canopy-only VoxCity shadow PoC. The
[Phase 2-4 index](experiments/voxcity_canopy_shadow/README.md) links real-data
A/B direct-irradiance results, voxel/observer sensitivity, and Phase 4A/4B
geometry/state verification. These are partial experimental results, not
implementation or acceptance of complete Standard Canopy.

**Not implemented or accepted as a complete Standard path:** formal canopy
polygon acquisition/generation and ID management; independent assessment
coverage; the full Native -> Standard Canopy lifecycle; ratified Canopy state
encoding; complete Standard Canopy acceptance; and real-data Building/canopy
integration. A derived visualization geometry is not accepted source canopy
polygons or assessment coverage.

**State meanings remain separate.** Section 6 codes are unratified candidates.
Height Envelope uses an experimental bitset for numeric validity, missing,
invalid and outside-raster-support conditions; it is not compatible with those
candidate presence/coverage classes. Its `state=1` does **not** mean canopy
presence. Raster support is not verified assessment coverage. CHM=0 and TREE=0
are not evidence of canopy absence; NoData must not become zero/absence. See
[Phase 4B](experiments/voxcity_canopy_shadow/PHASE4B_CANOPY_PRESENCE_AND_COVERAGE_AUDIT.md)
for the source-validity, coverage, height-estimate, presence and occupancy axes.

**Implementation limits, not universal Standard choices:**

- The PoC uses aligned EPSG:6677 grids and rejects unaligned bounds; it does not
  implement the full general GridSpec candidates in section 3.
- Phase 3's 0.5m case subdivides retained 1m samples; it adds no source information
  and is not a DEM bilinear-sampling comparison. Current sampling uses the
  effective source mask; contradictory mask/NoData reconciliation remains open
  as described in the consistency review.
- `constant_cr_v0.1` with CR=0.60 is a configurable PoC choice, not a general
  ecological standard; future class/spatial models remain unaccepted.
- The Height Envelope manifest is an experimental schema, not the complete
  Standard Canopy manifest. See the implementation document for its interface
  and provenance limits.
- VoxCity rounding, ground conditioning, actual observer positions and TREE
  occupancy are engine-specific Adapter concerns. The [Phase 4A findings](experiments/voxcity_canopy_shadow/PHASE4A_OBSERVER_GEOMETRY_AND_VERTICAL_CONTRACT.md)
  do not establish universal Standard geometry rules or resolve Building Z.

Section 9A's initial next-step wording and earlier PoC environment/run notes
remain records of their dates; the links above identify subsequent work without
rewriting that history. The [Completion Gate](experiments/voxcity_canopy_shadow/PHASE4_COMPLETION_GATE_REVIEW_20261027.md)
and [Phase 5 Integration Plan DRAFT](experiments/voxcity_canopy_shadow/PHASE5_INTEGRATION_PLAN_v0.1_Draft.md)
retain their existing entry conditions and unresolved issues. This addendum
neither closes those gates nor changes this document's DRAFT status.

## 13. Roadmap M1: source-neutral height input boundary (design proposal, 2026-11-11)

**Historical design note (2026-11-11):** references below to Concept v0.2's mandatory polygon bundle reflect that earlier date; current formal Concept v0.3 and §14 replace that assumption, without changing source-specific evidence safeguards.

**Status: REVIEW PROPOSAL, not an accepted Standard/API or a new SC decision.**
This note records the design direction discussed in [Roadmap M1-Plan-A #178](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/178) and [M1-Plan-B #179](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/179). The [integrated roadmap](planning/OUEM_Integrated_Roadmap_v0.1.md), Concept v0.2 and sections 2–9A above retain their authority. The detailed source-neutral input contract, file schema and real-data acceptance remain **unapproved**.

### 13.1 Why a shared upstream boundary is useful

- **Current temporary baseline — Meta/WRI CHMv2.** Continue consuming the existing estimated height raster *without a new canopy-classification transformation* in the bounded Height Envelope experiments. The user's reasons for treating Meta as temporary are **reference-date freshness and uncertain future updates**, not an established failure of its visual canopy representation. Exact reference epoch and future-update policy require separate source verification. Keep the historic CHMv2 acquisition/evidence gate and accepted experiment artifacts unchanged.
- **Future production candidate — GSI imagery + point clouds.** The independent [OUEM Canopy Segmentation project](https://github.com/iwamoto31206803-max/ouem-canopy-segmentation/blob/main/docs/PROJECT_CHARTER.md) owns the **RGB model's 2D canopy probabilities/masks and model-specific inference contract**; its [OUEM handoff](https://github.com/iwamoto31206803-max/ouem-canopy-segmentation/blob/main/docs/OUEM_HANDOFF.md) is not yet a frozen interface. **OUEM itself** owns GSI imagery acquisition/georeferencing and large-area tiling, point-cloud/terrain processing, geospatial joining of the 2D predictions with heights, derived CHM, polygonization, 3D conversion and environmental assessment.
- **Intermediate target.** First construct a reproducible GSI-derived **canopy-height raster candidate** with retained mask/probability/point-height evidence; do not require direct 3D reconstruction inside the segmentation repository. Neither this future target nor readiness of the segmentation model is a prerequisite for continuing the Meta-based experimental path.

The proposed **source-neutral HAG/CHM candidate boundary is upstream of the complete Standard Canopy**, within the source-specific Native/derived-input preparation and evidence-validation workflow. It is not a replacement for the Concept's canonical **canopy polygons + absolute top-Z + absolute bottom-Z**, and does not create an automatically accepted Standard layer. In particular, the existing height-only PoC can remain technically useful while complete Standard Canopy acceptance stays **NOT ACHIEVED**.

### 13.2 Logical input axes (proposals, not an adopted schema)

| Axis | Required meaning to preserve across both routes |
| --- | --- |
| Height quantity | Numeric **height above local ground in metres** (HAG candidate), plus the actual source quantity/method (Meta estimated canopy height, point-derived surface height, vegetation-filtered height, etc.). Metres and HAG alone do **not** prove equal physical quantities. Preserve original height values and source/DEM evidence. |
| Horizontal/vertical alignment | Source grid, CRS/transform/GSD, output GridSpec, aggregation/resampling choices, compatible DEM/ground datum and their identities. Height-to-absolute-Z conversion remains blocked if vertical semantics are not justified. |
| Support and validity | Distinguish source spatial support, masked/NoData/invalid height values, GSI image/inference validity, and outside/unprocessed areas. **Valid HAG=0 is not missing** and does not prove absence. |
| Canopy-presence evidence | Meta has **no independently classified canopy-presence mask** in this route. GSI supplies **model-estimated** probability/mask with threshold and model identity; predicted background is not surveyed absence. Never infer confirmed presence or absence solely from height or TREE occupancy. |
| Assessment coverage | Distinguish geometric source footprint, usable samples/predictions and actual **canopy assessment coverage**. A rectangular footprint or image valid mask is not proof of independently verified ecological absence. |
| Time, rights, provenance | Preserve source/release and its documented reference epoch (or UNKNOWN), imagery acquisition date and point-cloud survey date **separately**, source/weight/output rights, model/config/input SHA and any temporal mismatch. Derived outputs must link to retained upstream information. |

Do not flatten these axes into one boolean, one numeric state code or one CHM value. Section 6's proposed Standard state codes and the existing Height Envelope **height-validity bitset** remain distinct and unratified relative to one another.

### 13.3 Two preparation routes, one reusable numerical core

1. **Meta profile (existing experimental route):** preserve source CHM pixel values, masks, acquisition records and independently reviewed HAG/DEM compatibility bridge. The existing `height_envelope.validate_sources()` is intentionally **Meta CHMv2-specific**, requiring hash-bound acquisition and accepted Terrain evidence. Do not weaken it, invent a Meta record for GSI, or silently apply canopy-presence thresholds to the original Meta raster.
2. **GSI profile (future OUEM-owned producer):** georeference the Segmentation probability/mask, derive **raw point-cloud-based height candidate(s)** with explicit ground normalization, point selection and per-cell quality, and perform a versioned mask–height fusion. Preserve raw source HAG, inference probability/mask and disagreement diagnostics. Where the model predicts no canopy but raw point-height is positive, the *derived* canopy-height layer may exclude that cell under a reviewed rule; **do not rewrite raw height to zero**. A predicted canopy cell with missing point-height remains **estimated presence / unknown height**.
3. **Reusable core (candidate):** after source-specific meaning, provenance, GridSpec and vertical checks, reuse the current `height_envelope.sample_raster()`, `calculate()` and replaceable Crown Ratio model where applicable: `Z_top=DEM+HAG`, `Z_bottom=DEM+HAG*(1-CR)`. This is a design for extraction/reuse, **not a claim that the present CLI accepts GSI**. Current code restricts the initial grid to aligned EPSG:6677, nearest sampling, and requires valid source evidence; do not broaden those gates by implication.
4. **Complete Standard / Adapter later:** preserve source-specific polygon derivation and IDs, assessment coverage, source-vs-derived evidence and top/bottom validity. A CHM-derived polygon is an explicitly derived geometry, **not an independent oracle**. Only a separately approved complete Standard contract may ratify polygons, coverage and state encoding. Adapter separately decides TREE occupancy/rounding, building overlap, occluder-domain missingness and analysis validity. The existing guarded voxel path rejects nonvalid Height Envelope cells and must not be changed to fill unknown with background.

### 13.4 Proposed minimal synthetic contract tests before any real GSI processing

| Synthetic condition | Expected invariant |
| --- | --- |
| Valid Meta positive/zero HAG versus masked/outside HAG | Preserve numeric zero versus missing; provenance and old Height Envelope math; no automatic ecological classification |
| GSI mask positive with valid / missing / zero point height | Keep inferred presence distinct from height validity; do not fabricate 0 m for missing height |
| GSI mask negative with positive point height | Retain raw height; record conflict and derived fusion decision |
| Missing GSI RGB/inference extent with valid point height | Canopy class remains unassessed, not known absent |
| Displaced imagery and point-cloud grids | Fail shape-only alignment; require explicit CRS/affine/cell and resampling evidence |
| Different image/point epochs or incompatible height/ground references | Preserve separate epochs; BLOCK unsupported absolute-Z conversion rather than relabel coordinates |
| Missing occluder-domain data at voxel handoff | Preserve current guarded BLOCK; defer any partial-validity Adapter policy to separate review |

**Next review decision:** whether to describe an explicit *source-neutral HAG candidate input contract* (logical fields first), retain source-specific evidence validators, and implement only a small synthetic geometry/evidence compatibility fixture before any GSI data acquisition or new real processing. Thresholds, point-cloud methodology, segmentation acceptance, polygon IDs and formal Standard/Adapter acceptance remain open.

**Documentation/acceptance boundary:** this section changes no existing implementation, old results, source hashes, Concept requirement, accepted Terrain/Building/Adapter contract, experimental Height Envelope output schema, or formal Canopy acceptance status.

## 14. Roadmap M1: raster-first canopy and optional geometry exports (current proposal, 2026-11-14)

**Status: Concept v0.3's responsibility split is formally adopted; this section remains a proposed Standard/PoC implementation detail, NOT a ratified Canopy Standard or dataset acceptance.** This supersedes the mandatory-polygon reading of the dated §9A and §13 notes. See [Concept v0.3](OUEM_Concept_Architecture_v0.3.md), [design review #186](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/186), [bounded PoC Issue #184](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/184), and [Phase 4B](experiments/voxcity_canopy_shadow/PHASE4B_CANOPY_PRESENCE_AND_COVERAGE_AUDIT.md).

### 14.1 Meta modelled-presence interpretation (source-specific)

Keep original Meta CHMv2 height values, source masks and acquisition identities unchanged. For effective-valid finite sampled CHM **H>0 m** indicates **Meta-modelled PRESENT**, **H=0 m** indicates **Meta-modelled ABSENT**, and masked/NoData/negative/invalid/outside samples are **UNKNOWN**. These are explicitly **model-derived** labels, not field-observed presence or surveyed absence; the rule must be revisited for each source release. Never derive these classes from Height Envelope `state==1`, `top>bottom`, a `TREE==0` voxel or a made-up rectangle-wide survey footprint.

The prior Phase 4B audit reported 120,000 valid 1m cells (40,789 positive, 79,211 zero) on the full Komae Height Envelope grid, and 3,842 positive / 254 zero within the earlier 64m ROI. These **historical model-value counts** are not new execution results or independent ecological validation. An effective CHM sample can have known modelled presence even if DEM validity prevents absolute-Z generation.

### 14.2 Two independent consumers of common canopy evidence

**Main analysis lane:** source-specific Native/height validation → common modelled horizontal evidence, height/HAG, assessment and DEM validity, compatible absolute top/bottom Z → Adapter sampling and TREE voxelization → B1/B2. Reuse existing Height Envelope numerical methods where compatible. Adapter owns engine grid/centres, D0, rounding, building priority, halo, missing-data guard and downstream analysis validity. Raster-first processing **must not require any 2D polygon or 3D mesh generation or persistence**. Logical presence/unknown must be reproducible from retained inputs and method; separate file materialization is a future packaging decision.

**Independent optional geometry export lane:** the same evidence may produce derived 2D canopy polygons for GIS/other models, and later a generic 3D mesh for visualization/exchange. For the **optional** 2D PoC, consider 1m EPSG:6677 north-up GridSpec, cell-centre source sampling, positive-cell polygonization, candidate **4-neighbour connectivity**, no arbitrary cleanup or inherited 3m cutoff, and exact positive-mask raster roundtrip. Validate small/diagonal components, holes, area and boundaries, original source linkage and reproducible output hashes. Any original accepted canopy polygon remains a source input, not a derived replacement. **3D mesh implementation is deferred until a concrete need exists.**

GSI remains a separately gated producer: RGB modelled 2D inference and point-cloud-based height candidate require georeferencing, compatible ground/vertical evidence, alignment, fused canopy semantics and source-specific QA. A positive point height alone is not a canopy CHM; a positive segmentation cell with unknown height remains presence-estimated/height-unknown. The existing `canopy_height_candidate.py` seam is synthetic-only, not a production GSI pipeline.

### 14.3 Proposed next gates, kept separate

1. **Synthetic-first:** Meta modelled present/absent/unknown, CHM-vs-DEM validity, original source values and GridSpec, GSI conflict cases, existing Height Envelope/voxel regressions; do not add a polygon precondition to this technical lane.
2. **Separate optional exporter QA:** if implemented, test 4-neighbour, diagonal-only adjacency, holes, ID/area/provenance and polygon→raster roundtrip. Exporter acceptance is not prerequisite to raster/TREE acceptance.
3. **Real Komae only after explicit authorization:** on the previously defined 64m × 64m ROI `(-23320, -40760, -23256, -40696)`, independently verify pinned raw and derived input identities; compare **old vs new input paths on the same actual engine centres/grid, DEM, CR, building/voxel policy, observer/halo and missing guards**, with pre-/post-building TREE diagnostics. Historical Phase 2 ROI counts are not automatically the expected counts for a different integrated scene. No download or overwrite; expansion to 400×300m requires separate review.
4. **Independent acceptance:** M1 limited technical success, complete Standard Canopy/Data/Adapter acceptance, research M3 field accuracy and distribution/licensing remain distinct decisions. Missing source evidence or vertical compatibility may remain BLOCKED even if synthetic checks pass.

**Not changed:** accepted Building/Terrain/Building Adapter contracts, source CHM, Height Envelope math/state/manifest, historic experiments, Phase 4A/4B/B1/B2 evidence, external Segmentation repo, and all existing dataset acceptance records.
