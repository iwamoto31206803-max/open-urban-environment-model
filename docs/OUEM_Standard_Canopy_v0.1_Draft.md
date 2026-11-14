# OUEM Standard Canopy v0.1 — Draft

**Status:** PROPOSED / DRAFT — design only; not an accepted Standard contract or implementation.
**Scope:** Provider-independent canopy geometry for the initial Komae end-to-end PoC, with future CHM-source interchangeability.
**Authority:** [OUEM Concept & Architecture v0.2](OUEM_Concept_Architecture_v0.2.md) takes precedence. This draft does not modify accepted Building, Terrain, or VoxCity Adapter contracts.

## 1. Purpose and architecture

Represent canopy horizontal extent and vertical envelope independently of Meta/WRI CHMv2, LiDAR-derived CHM, and any specific analysis engine. The flow is Raw → Native → OUEM Standard → Engine/Analysis Adapter → VoxCity. Acquisition does not itself establish Standard acceptance. The CHMv2 AOI crop is an acquisition artifact, not a Standard Canopy raster.

Native retains source-specific height semantics, original grids, polygon provenance, masks, and acquisition evidence. Standardization validates source meaning and combines canopy extent, CHM, and compatible bare-earth terrain into canonical absolute-Z outputs. VoxCity-specific resampling, relative heights, collision policy, and voxelization belong to the Adapter. Preserve the existing `komae_canopy.py` experimental workflow; do not treat it as the Standardizer.

## 2. Proposed output bundle

| Candidate artifact | Semantics | Status |
| --- | --- | --- |
| `canopy.gpkg` | Original accepted canopy polygons and stable IDs; single trees and contiguous canopy allowed | Proposed |
| `canopy_top_z.tif` | Canopy top **absolute elevation** in metres | Concept requirement; packaging proposed |
| `canopy_bottom_z.tif` | Canopy bottom **absolute elevation** in metres | Concept requirement; packaging proposed |
| `canopy_state.tif` | Explicit coverage / presence / height-validity classification | Proposed, encoding unresolved |
| `canopy.manifest.json` | CRS, vertical semantics, source/algorithm provenance, hashes, GridSpec, QA | Proposed |

The three core representations in Concept v0.2 are canopy polygons, top-Z raster, and bottom-Z raster. A separate state raster is a candidate encoding of the mandatory missing-versus-absent distinction, **not** a previously approved Concept requirement. Source polygons must remain available unchanged; rasterization must not silently replace them.

A generic 3D surface mesh may be derived from Standard top/bottom; VoxCity voxels are Adapter outputs. LAD and transmissivity are **unset**, not zero. Building/canopy 2D overlaps are permitted; 3D collision resolution is downstream.

## 3. Coordinates and grid

- Use the study-area projected horizontal CRS; Komae profile: EPSG:6677, metres.
- Top and bottom are absolute elevations with explicitly recorded vertical reference, not HAG. Horizontal EPSG alone does not establish vertical reference.
- Do not relabel vertical coordinates or assume a transformation. Ground DEM and height inputs must have validated compatible semantics; unresolved vertical-reference status blocks accepted absolute-Z generation.
- Komae **candidate execution profile**: north-up, unrotated 1 m grid, aligned to integer-metre EPSG:6677 boundaries; extent outward-rounded to cell boundaries. This is **not** a nationwide fixed-resolution Standard.
- Record a deterministic GridSpec (CRS, resolution, bounds, affine transform, width/height, alignment, cell-centre convention). All output rasters must match it exactly.
- Retain accepted Standard Terrain v0.1 at its native 0.5 m grid; sample it onto the Canopy execution grid without modifying its canonical artifact. Terrain v0.1 itself does not resample.
- CHM candidate resampling: nearest neighbour, preserving source masks/NoData. Terrain candidate: nearest neighbour for reproducible initial PoC, compare against bilinear with explicit masked-neighbour rules before finalizing.
- Polygon-to-mask candidate: a cell is canopy-present if its centre is inside the accepted polygon union; define boundary-centre tie behaviour and test it before implementation acceptance. Track rasterization area difference and lost small polygons.
- Do not claim seamless adjoining AOI outputs solely from common grid alignment; source coverage, clipping, and boundary handling also require QA.

## 4. Canopy polygon and coverage contract

Accept Polygon/MultiPolygon and contiguous canopy without individual-tree segmentation. Candidate metadata: deterministic `ouem_id`, nullable `source_id` when the source lacks one, mandatory `source_dataset` and dataset provenance. The exact stable-ID generation rule, polygon validity repair policy, and serialization rules are unresolved.

Multiple overlapping source polygons may be preserved. For the presence mask, candidate rule is their union; report overlap diagnostics. Do not silently merge the source geometries.

An explicit **coverage footprint** is required conceptually to distinguish surveyed absence from unassessed space. Its storage format and relationship to canopy polygons are unresolved. Missing polygon outside known coverage **must not** imply no canopy.

## 5. Height semantics and crown-base model

For a valid canopy cell `i` with terrain absolute elevation `G_i`, CHM height above ground `H_i`, and crown ratio `CR_i`:

```text
Z_top[i]    = G[i] + H[i]
Z_bottom[i] = G[i] + H[i] * (1 - CR[i])
crown_depth[i] = Z_top[i] - Z_bottom[i]
```

The source must explicitly establish that CHM is a height-above-ground quantity in metres. A source name, raster CRS, or plausible values alone do not prove that meaning. Record provenance and source hashes. In particular, the Meta/WRI CHMv2 acquisition output and its provenance must be bridged/validated explicitly; do not assume compatibility with the legacy `komae_canopy.py` provenance schema.

**CR model interface:** versioned, replaceable estimation algorithm with recorded inputs, parameters, applicability, and per-output provenance. Initial Komae **candidate** is `constant_cr_v0.1`, `CR=0.60`, corresponding to legacy bottom HAG = 0.40 × tree height. This is a continuity choice, not an empirically validated ecological default or a permanent Standard requirement. Later models may be class-based or spatially varying without changing the Standard top/bottom contract.

Candidate CR domain: `0 < CR <= 1`. A canopy-present cell with invalid, missing, negative, or zero height is not automatically declared canopy-absent. Minimum-tree-height thresholds, if used by analysis, are configurable and documented; do not silently apply the legacy 3 m cutoff to Standard.

For valid cells, require finite `G`, `H`, `CR`, and `G <= Z_bottom <= Z_top`. Distinguish top-height evidence from inferred bottom-height evidence. Do not infer unobserved bottom as measured.

## 6. State, NoData, and uncertainty

Candidate semantic classes:

| Candidate code | Meaning |
| --- | --- |
| 0 | Within verified coverage, no canopy polygon |
| 1 | Canopy polygon present, valid top/bottom heights |
| 2 | Canopy present, required height or terrain missing |
| 3 | Canopy present, invalid or inconsistent height |
| 255 | Outside verified assessment coverage / unassessed |

These **numeric codes are not ratified**. Define datatype, NoData sentinel, priority when errors overlap, and exact coverage-boundary handling before implementation. Both top/bottom must be NoData wherever height is not valid. Never substitute zero for unknown; zero-height or thresholded vegetation must not silently erase presence.

A Standard bundle may represent partially missing canopy height accurately and still pass structural QA; its suitability for a particular VoxCity analysis is a separate Adapter acceptance decision. Any imputation is explicit, versioned, and provenance-bearing rather than a silent mutation of canonical observations.

## 7. QA and acceptance gates

**Mandatory structural/semantic checks:** declared horizontal CRS; verified vertical-reference compatibility; source height meaning; grid shape/affine/CRS identity; polygon geometry validity and IDs; coverage footprint; mask and NoData propagation; finite values; top >= bottom >= ground for valid cells; CR range and provenance; source and output SHA-256; deterministic rerun evidence.

**Diagnostics:** polygon overlap; polygon-to-raster area delta; small polygon loss; CHM/polygon disagreement; canopy cells with missing/invalid CHM or DEM; elevation and crown-depth distributions; sampling method and source pixel sizes; AOI-boundary consistency.

**Distinct gates:** (1) contract/unit tests on synthetic data, (2) Komae real-data Standard Canopy acceptance with frozen input identities, (3) downstream Standard Building/Terrain/Canopy → VoxCity integration and environmental-analysis acceptance. Passing one gate does not imply passing another. Existing Building and Terrain acceptance remains unchanged. Vertical-offset concerns in cross-layer fusion must be tested explicitly, not silently compensated.

## 8. Komae candidate PoC profile

- AOI: `config/study_areas/komae_09LD3451.yaml` (EPSG:6677; x=-23600..-23200, y=-40800..-40500; 400 × 300 m).
- Canopy grid candidate: 1 m, 400 × 300 cells when the AOI is used exactly.
- CHM candidate: Meta/WRI CHMv2, from the separately audited AOI acquisition; source crop is EPSG:3857, not a canonical Standard raster.
- Terrain: accepted Komae Standard Terrain (0.5 m, EPSG:6677, source-declared T.P.), subject to verified compatible source semantics.
- CR candidate: constant 0.60.
- **Full Standard acceptance dependency (deferred):** identify and accept a canopy polygon source and verified coverage footprint. This is **not** a blocker for the limited CHM + DEM + CR height-envelope PoC. CHM-derived polygons require an explicit separate provenance-bearing generation step; CHM alone must not silently be promoted to an independent polygon source.
- No CHMv2-vs-LiDAR comparison is required before this end-to-end PoC. Source interchangeability is a contract objective; comparative performance assessment is deferred.

## 9. Open decisions and validation plan

1. Canopy polygon source, acquisition/Native contract, coverage footprint, stable IDs.
2. Exact raster state encoding, NoData sentinel, and outside-coverage semantics.
3. Cell-centre-on-boundary tie rule and tiny-polygon diagnostics.
4. Terrain nearest-vs-bilinear comparison and masked interpolation behaviour.
5. CR=0.60 sensitivity, zero/low-height treatment, and later class/spatial CR evidence.
6. Exact provenance schema, hashing, deterministic serialization, and output naming.
7. Vertical compatibility gate and cross-layer building/terrain/canopy offset checks.
8. Downstream VoxCity canopy Adapter behaviour on missing data and 3D overlap.
9. Thresholds for structural QA vs real-data acceptance; no arbitrary universal tree-height cutoff.
10. Derived mesh format and future LAD/transmissivity model (out of v0.1 scope).


## 9A. Deferred polygon integration and phased execution (design review note)

**Decision (2026-10-25):** Retain canopy polygons and coverage semantics as required capabilities of the complete Standard Canopy architecture, but **defer acquisition/generation of real Komae canopy polygons**. Their absence does **not** block the next CHM + DEM + CR vertical-envelope PoC.

**Immediate next phase (height-envelope PoC, not full Standard acceptance):** Verify CHMv2 height semantics and masks, sample CHM and the accepted Terrain to a documented candidate GridSpec, derive cellwise absolute top/bottom Z using a versioned configurable CR model, record provenance and QA, and inspect integration feasibility with the existing experimental VoxCity canopy path. A synthetic canopy mask may be used for focused unit tests; no real polygon or asserted survey coverage is required for this limited experiment.

**Future required phase:** Establish a polygon-generation/acquisition route, Native Canopy Polygon input contract, polygon/CHM combination, surveyed-coverage footprint, presence-versus-absence semantics, and end-to-end acceptance. CHM-derived polygons may be considered if generated as an explicit versioned, provenance-bearing artifact; they are not independent validation of the CHM.

**Acceptance boundary:** A height-envelope-only PoC output is explicitly **experimental/partial** and must not be labelled accepted complete Standard Canopy. Do not fabricate canopy presence, surveyed absence, or coverage from the CHM. Do not change the Concept v0.2 canonical three-part representation or silently weaken its polygon requirement.

## 10. Design decision register

The statuses below distinguish the Concept baseline, explicitly selected candidate decisions, and assistant-proposed details. No item in this document constitutes a formally accepted implementation.

| IDs | Subject | Status |
| --- | --- | --- |
| SC-01–SC-10 | Polygon + absolute top/bottom, source-neutrality, provenance, missing-vs-absent, Adapter boundary | Concept-derived principles; concrete packaging proposed |
| SC-11 | Cell-centre rasterization, preserve source polygon | **User-selected candidate** |
| SC-12 | CHM nearest; validate DEM resampling | **User-selected candidate** |
| SC-13 | Cellwise absolute top/bottom from CHM + terrain | **User-selected candidate** |
| SC-14 | Standard owns absolute Z and CR; Adapter owns voxelization | **User-selected candidate** |
| SC-15–SC-18 | Polygon metadata/overlap, state, QA, missing-data acceptance | Proposed; not yet formally ratified |
| SC-19–SC-22 | Independent GridSpec, Komae 1 m alignment, DEM resampling | Proposed; not yet formally ratified |
| SC-23–SC-27 | Replaceable CR model, candidate 0.60, QA and sensitivity | Proposed with user endorsement of **extensibility**; numeric default not formally ratified |

## 11. Related existing contracts

- [Concept & Architecture v0.2](OUEM_Concept_Architecture_v0.2.md)
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
