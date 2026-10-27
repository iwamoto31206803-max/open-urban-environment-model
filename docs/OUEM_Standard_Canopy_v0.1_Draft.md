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
