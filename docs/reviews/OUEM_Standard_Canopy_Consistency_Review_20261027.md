# Standard Canopy contract consistency review — 2026-10-27

## Executive Summary

**Review judgement: CONDITIONAL PASS for consistency of the explicitly limited
experimental path, not acceptance of complete Standard Canopy or Phase 5 entry.**
No current CONTRACT CONFLICT was established within the declared height-envelope
PoC scope. The [Canopy DRAFT](../OUEM_Standard_Canopy_v0.1_Draft.md) §§8–9A
explicitly defer polygons/coverage while permitting CHM + DEM + CR experiments.
That exception explains the partial implementation; it does not remove the
complete Standard's three-part representation or its acceptance gates.

The main gaps are unimplemented polygon/coverage/ID contracts, incompatible
state *meanings* that must never be merged by numeric code, and incomplete
generalization beyond the frozen all-valid Komae experiment. Scientific source
accuracy, surveyed canopy presence/absence, spatial CR calibration and real
Building/canopy collision acceptance remain unverified. Existing engine-specific
rounding and observer limitations belong downstream, not in a universal Standard.

## Baseline, authority and evidence method

Checked on 2026-10-27 against fetched main
`0d1612108f379005acab5f8daa35af4177c5f6d3`. GitHub reports [PR #77](https://github.com/iwamoto31206803-max/open-urban-environment-model/pull/77)
merged at that commit. Work is on a separate review branch.
Engine-specific findings refer to VoxCity 1.7.0, unchanged pin
`fa212656305328a9a657973bae26f352bfe813bc`, as recorded in Phase 2–4.

Authority follows [Concept v0.2](../OUEM_Concept_Architecture_v0.2.md), especially
§§3–5, and the [documentation governance](../OUEM_Documentation_Governance_v0.1.md).
The Standard Canopy document remains **PROPOSED / DRAFT**. The
[Canopy Current State](../status/CANOPY_CURRENT_STATE.md), dated to its own earlier
main, remains an informational entry point. The [experiment index](../experiments/voxcity_canopy_shadow/README.md)
separates historical proposals and subsequent results. The status note in
[Phase A design](../Phase_A_Implementation_Design_v0.1.md) prevents interpreting
old scaffold statements as current implementation status.

This review inspected existing documents, source and test assertions. It did
**not** rerun Python tests, regenerate data, repeat a local hash audit or perform
new experiments/acceptance. References to successful runs and actual data below
are attributed to their existing records, not newly executed results. In
particular, [Phase 4B](../experiments/voxcity_canopy_shadow/PHASE4B_CANOPY_PRESENCE_AND_COVERAGE_AUDIT.md)
§§6/8 and the [Completion Gate](../experiments/voxcity_canopy_shadow/PHASE4_COMPLETION_GATE_REVIEW_20261027.md)
§2 contain the historical data/hash/test evidence and its limits.

## Item-by-item assessment

Classifications describe the compared scope: CONSISTENT, DOCUMENTATION GAP,
EXPERIMENTAL DEVIATION, CONTRACT CONFLICT, UNVERIFIED and NOT IMPLEMENTED.
Multiple labels distinguish working partial behavior from missing full-contract
capabilities. NOT IMPLEMENTED is not evidence of a contradiction in an explicitly
deferred design. A candidate in the DRAFT is not a ratified requirement.

| ID / review item | DRAFT requirement or candidate | Current code and evidence | Classification / consequence |
|---|---|---|---|
| R1 Polygon + top Z + bottom Z | §§2/8/9A: complete bundle retains polygons plus absolute top/bottom; limited vertical-only PoC allowed | [Height Envelope](../../src/ouem/height_envelope.py) `generate` emits two Z TIFFs, validity TIFF and its own manifest; [tests](../../tests/test_height_envelope.py) `test_absolute_envelope_cr_changes_and_zero_is_valid` and [3D verification](../verification/OUEM_Height_Envelope_3D_Visualization_Komae_20261026.md) cover the partial output | CONSISTENT with §9A; EXPERIMENTAL DEVIATION from complete packaging; NOT IMPLEMENTED for canonical polygons/verified coverage. A visualization GeoPackage is not accepted source canopy polygons |
| R2 Native → Standard → Adapter | §1: Native preserves source semantics; Standard owns absolute-Z fusion; Adapter owns engine conversion | [Native](../../src/ouem/native/canopy/__init__.py), [Standardize](../../src/ouem/standardize/canopy/__init__.py), [Model](../../src/ouem/model/canopy/__init__.py) contain namespace docstrings only. [Envelope](../../src/ouem/height_envelope.py) performs direct guarded acquisition/Terrain fusion; [shadow PoC](../../src/ouem/canopy_shadow_poc.py) owns experimental conversion | CONSISTENT responsibility direction; EXPERIMENTAL DEVIATION in bypassing unimplemented lifecycle stages; NOT IMPLEMENTED full Native/Standard Canopy interfaces. [Current State](../status/CANOPY_CURRENT_STATE.md) already states this |
| R3 Absolute height calculation | §5: HAG metres, compatible absolute DEM, versioned CR; top=G+H, bottom=G+H(1−CR), finite ordered results | [Envelope](../../src/ouem/height_envelope.py) `validate_sources`/`calculate`; [tests](../../tests/test_height_envelope.py) formula/CR-change, fail-closed semantics and incompatible-vertical-name cases; [PoC semantic gates](../CHM_Height_Envelope_PoC_v0.1.md) | CONSISTENT arithmetic/declaration checks; UNVERIFIED scientific HAG/DEM ground equivalence and independent vertical accuracy. The bridge verifies declarations and byte integrity, not scientific truth |
| R4 GridSpec / CRS / centres | §3: explicit deterministic projected grid; Komae candidate 1m; preserve canonical 0.5m Terrain; outward-round candidate extent | [Envelope](../../src/ouem/height_envelope.py) `GridSpec` is EPSG:6677-only, rejects unaligned bounds instead of rounding, uses north-up cell centres. [Grid test](../../tests/test_height_envelope.py) `test_exact_komae_grid_centres_and_half_metre_dem_sampling`; [shadow loader](../../src/ouem/canopy_shadow_poc.py) fixes 400×300 at 1m | CONSISTENT aligned Komae profile; EXPERIMENTAL DEVIATION in narrower generic extent/CRS support; DOCUMENTATION GAP for future profile behavior. No nationwide 1m rule or arbitrary AOI guarantee |
| R5 CHM/DEM resampling | §3: CHM nearest candidate; initial DEM nearest, bilinear comparison before finalization | [Envelope](../../src/ouem/height_envelope.py) `sample_raster` transforms centres to source CRS and uses inverse-affine floor/effective mask; non-nearest rejected. [Tests](../../tests/test_height_envelope.py) grid, EPSG:3857 lookup, masks and outside cases. [Sensitivity](../../src/ouem/canopy_shadow_sensitivity.py) `subdivide` repeats each 1m sample into four 0.5m children | CONSISTENT initial sampling; NOT IMPLEMENTED masked bilinear comparison. Phase 3 replication is not fresh 0.5m source sampling or that comparison; DOCUMENTATION GAP on mask precedence (below) |
| R6 State / NoData / coverage / presence | §6 proposed classes combine assessed coverage, polygon presence and height validity; codes unratified | [Envelope](../../src/ouem/height_envelope.py) `STATE_BITS`/`calculate`/`write_verified`; [Phase 4B](../experiments/voxcity_canopy_shadow/PHASE4B_CANOPY_PRESENCE_AND_COVERAGE_AUDIT.md) §§2–5; [state fixtures](../../tests/test_canopy_presence_semantics.py) | EXPERIMENTAL DEVIATION: validity bitset is a different schema, not a Standard class implementation. CONSISTENT no missing-to-zero behavior; NOT IMPLEMENTED assessed coverage/presence; UNVERIFIED ecological absence/presence. No numeric-code crosswalk is safe |
| R7 Polygon acquisition / ID / rasterization | §§3–4/9: accepted source geometry, stable IDs, union mask with centre/tie rule, repair/area/small-object diagnostics, coverage footprint | Namespace-only Canopy packages above; [Current State](../status/CANOPY_CURRENT_STATE.md) and [Phase 4B](../experiments/voxcity_canopy_shadow/PHASE4B_CANOPY_PRESENCE_AND_COVERAGE_AUDIT.md) report no accepted presence source. Existing [envelope tests](../../tests/test_height_envelope.py) concern rasters, not this contract | NOT IMPLEMENTED. Stable-ID, serialization, tie/repair rules remain design decisions; UNVERIFIED surveyed footprint. There is no polygon acceptance test to cite; existing raster fixtures do not substitute |
| R8 Replaceable CR | §5/SC-23–27: versioned interface; 0.60 candidate, no ecological default; future class/spatial models | [Envelope](../../src/ouem/height_envelope.py) `CrownRatioModel`, `ConstantCR`, `generate`; [tests](../../tests/test_height_envelope.py) synthetic spatial/class replacement and invalid model cells; [PoC CR scope](../CHM_Height_Envelope_PoC_v0.1.md) | CONSISTENT interface and constant implementation; UNVERIFIED real class/spatial input lineage, calibration and applicability. CLI only constructs `constant_cr_v0.1`; synthetic extensibility is not acceptance of a spatial model |
| R9 Provenance / hashes / manifest | §§5/7/9: source meaning, input/output hashes, GridSpec, algorithm identity; final canonical schema unresolved | [Envelope](../../src/ouem/height_envelope.py) `validate_sources`, `implementation_identity`, `generate`; [acquisition](../../src/ouem/acquire/meta_chmv2.py); [tests](../../tests/test_height_envelope.py) semantics fail-closed, deterministic outputs, input mutation and protected-artifact cases | CONSISTENT partial PoC schema/bridge, no assumption of legacy provenance compatibility. NOT IMPLEMENTED full polygon/coverage/model-source canonical schema. Fingerprint equality alone does not establish same implementation/environment (below) |
| R10 VoxCity / TREE meaning | §§1–2/9: relative conversion, grid adaptation and voxelization downstream; internal optical properties unset | [Shadow](../../src/ouem/canopy_shadow_poc.py) `relative_grids`, `build_pair`, `irradiance`; [sensitivity](../../src/ouem/canopy_shadow_sensitivity.py) `geometry`; [Phase 2 tests](../../tests/test_canopy_shadow_poc.py), [Phase 3 tests](../../tests/test_canopy_shadow_sensitivity.py), [Phase 4A fixtures](../../tests/test_canopy_observer_geometry.py) and [results](../experiments/voxcity_canopy_shadow/PHASE4A_OBSERVER_GEOMETRY_AND_VERTICAL_CONTRACT.md) | CONSISTENT Adapter responsibility; EXPERIMENTAL DEVIATION in height-driven occupancy without accepted presence polygons; UNVERIFIED arbitrary physical observers and calibrated optics. TREE is model occupancy, not source truth |
| R11 Building/canopy collision | §2/SC-01–10: permit canonical 2D overlap, resolve 3D downstream | [Phase 4A fixtures](../../tests/test_canopy_observer_geometry.py) `test_flat_building_and_tree_share_ground_and_building_overwrites_tree`, precision and ground-reorigin cases; [Phase 5 plan](../experiments/voxcity_canopy_shadow/PHASE5_INTEGRATION_PLAN_v0.1_Draft.md); current shadow runners use zero Building IDs/heights | CONSISTENT architectural boundary and synthetic characterization; NOT IMPLEMENTED real common-grid A/B/C integration/overwrite accounting; UNVERIFIED selected real Building Z and collision outcomes. Engine behavior is not a universal Standard policy |
| R12 QA / reproducibility / acceptance | §7: structural, semantic, polygon, coverage and rerun QA; distinct synthetic, real Standard and downstream gates | [Envelope tests](../../tests/test_height_envelope.py) readback/publication/determinism; [Phase 2 results](../experiments/voxcity_canopy_shadow/PHASE2_RESULTS_20261027.md), [Phase 3 results](../experiments/voxcity_canopy_shadow/PHASE3_RESULTS_20261027.md), [Phase 4B audit](../experiments/voxcity_canopy_shadow/PHASE4B_CANOPY_PRESENCE_AND_COVERAGE_AUDIT.md), [Completion Gate](../experiments/voxcity_canopy_shadow/PHASE4_COMPLETION_GATE_REVIEW_20261027.md) | CONSISTENT bounded technical QA; NOT IMPLEMENTED complete Standard Canopy acceptance checks; UNVERIFIED field accuracy, real missing-data analysis, adjacency and generic coverage. COMPLETED is not formal acceptance |

## Important differences and evidence boundaries

### State crosswalk is semantic, not numeric

| DRAFT §6 candidate | Height Envelope `ouem-height-envelope-poc/v0.1` | Safe interpretation |
|---|---|---|
| 0: verified coverage, no canopy polygon | 0 is unused in completed calculated states | No absence mapping exists without accepted polygon/assessment evidence |
| 1: polygon present and heights valid | 1: numerically valid, including CHM=0 or positive height collapsed to zero Float32 depth | Same number does not imply same meaning; numeric validity supplies no polygon/presence evidence |
| 2: canopy present, height/terrain missing | Bit 2: CHM missing; bit 4: DEM missing | Source-specific errors can combine; neither asserts canopy present |
| 3: canopy present, invalid/inconsistent height | Bits 8/16: CHM/DEM invalid; bit 128: model/Float32 invalid | Candidate class 3 is not an envelope class or a valid/error combination |
| 255: outside verified assessment coverage | Bits 32/64: outside CHM/DEM raster support | Raster support is not surveyed assessment coverage; envelope 255 is not an assigned outside class |

Top/bottom use -9999 for all nonvalid heights; state stores the reasons. State
TIFF has no NoData tag: its storage mask is valid even at error cells. Use exact
`state==1`, not `bool(state)`, `state!=0` or the state storage mask. Error-bit
counts overlap, so do not sum them as disjoint populations. Per-source priority
is outside before missing before invalid; errors from the other source remain.
These are [existing implementation](../../src/ouem/height_envelope.py) facts,
characterized by [Phase 4B fixtures](../../tests/test_canopy_presence_semantics.py).

State alone cannot distinguish CHM positive from zero; top==bottom alone also
cannot recover that distinction. The fixture with CHM=1e-8m at DEM=10m remains
state=1 but has Float32 zero depth. Another fixture retains positive depth at
CHM=0.1m but rounds to no TREE at both tested voxel sizes. Preserve source values,
effective masks, support, input identities and conversion diagnostics separately.
The existing Komae audit reported all samples valid; real missing/outside behavior
is not established by that population. Synthetic missing cases are separate evidence.

The DRAFT allows structurally accurate partial missing bundles (§6); the current
[shadow loader](../../src/ouem/canopy_shadow_poc.py) checks **the whole 400×300
envelope before ROI cropping** and rejects every nonvalid state. This is an
explicit narrower analysis eligibility policy, not a Standard requirement to
discard partial data. The envelope itself can complete with zero valid cells.
A future partial-coverage Adapter requires reviewed occluder/observer policies.

### Absolute Z, HAG and model geometry

The [envelope semantic gate](../../src/ouem/height_envelope.py) checks a COMPLETED
acquisition, hash-bound HAG/metres declarations, source statement/snapshot,
named compatibility reviewer, DEM manifest/tags and hash-identified Terrain
acceptance. This verifies integrity and declared review, not authentic authorship,
scientific correctness or measured agreement of CHM's ground with the DEM.
Source-declared T.P. remains source-declared. The [PoC human review checklist](../CHM_Height_Envelope_PoC_v0.1.md)
and the bridge identities/declarations cited in [Phase 2](../experiments/voxcity_canopy_shadow/PHASE2_RESULTS_20261027.md)
must not be promoted to independent survey validation.

The engine consumes relative T=Ztop−D and B=Zbottom−D after a single DEM
subtraction and row flip. In the building-free case, D0=min(D), ground index
g=Q_s(D−D0)+1, and TREE faces are D0+(g+lo/hi)×s. Here Q_s is the pinned
Float32/half-up path and lo/hi are rounded relative crown limits, including
the tested thin-crown expansion. Actual public-map ray Z is
D0+(g+int(h/s)+0.5)×s, not generally D+h. These are engine-specific findings in
[Phase 4A](../experiments/voxcity_canopy_shadow/PHASE4A_OBSERVER_GEOMETRY_AND_VERTICAL_CONTRACT.md),
not offsets to apply to canonical elevations. Approximately +s ground-layer
effects and rounding must not be corrected by altering the Standard top/bottom.

[Building Current State](../status/BUILDING_CURRENT_STATE.md) and the
[unresolved Building diagnosis](../research/OUEM_Komae_Building_Vertical_Geometry_Diagnosis.md)
retain the roughly 37m source/converter hypothesis. Changing Canopy semantics
or subtracting a guessed offset cannot resolve it. [Building](../OUEM_Standard_Building_v0.1.md),
[Terrain](../OUEM_Standard_Terrain_v0.1.md) and the
[accepted Building Adapter](../OUEM_VoxCity_Adapter_v0.1.md) remain unchanged.

### Documentation and provenance precision

Three explanation gaps are actionable without changing design:

- The DRAFT's future-tense §9A and the [Height Envelope document](../CHM_Height_Envelope_PoC_v0.1.md)
  initial no-Terrain/no-real-run notes describe their dated baselines. Later real
  envelope/shadow evidence exists in the linked verification/Phase 2–4 records;
  these are chronological differences, not proof that current code is absent.
- DRAFT §3's outward-rounded grid is a candidate. `GridSpec` instead accepts
  aligned Komae bounds and rejects nonalignment; the shadow runner is still more
  tightly profile-bound. General rounding, other projected CRSs and arbitrary
  AOI masking are not accepted capabilities of this implementation.
- PoC sampling prose should identify effective Rasterio `read_masks()` precedence.
  `sample_raster` does not independently reconcile a contradictory valid explicit
  mask versus a declared NoData pixel. [Phase 4B](../experiments/voxcity_canopy_shadow/PHASE4B_CANOPY_PRESENCE_AND_COVERAGE_AUDIT.md)
  §3 already records this limit; a future source policy must decide how to reject
  or reconcile contradictory metadata rather than assume both were checked.

The [envelope manifest](../../src/ouem/height_envelope.py) uses its own versioned
schema, not `canopy.manifest.json` or legacy CHM handoff semantics. It stores
implementation identity separately from `reproducibility_sha256`; that stable
fingerprint includes input hashes/configuration/QA/output records but does not
itself hash the separate implementation/environment block. Compare those fields
as well. Full manifest bytes include time/paths and are not promised identical.
The [determinism test](../../tests/test_height_envelope.py) verifies repeated
synthetic TIFF/fingerprint identity in its tested environment, not universal
cross-GDAL or cross-version byte reproducibility. Future externally sourced CR
inputs require their own identities, grid/mask rules and dependency evidence;
synthetic class-model replacement alone does not establish those controls.
Publication also depends on filesystem support: existing hard-link success and
the sandbox denial are separate recorded environments in the PoC document;
publication/readback fixtures do not guarantee every Windows storage location.

## Proposed follow-up, not adopted changes

These categories are independent of the Completion Gate's class A/B/C labels.
No proposal below edits the DRAFT, code or a historical record in this PR.

| Category / proposal | Owning role and required next action |
|---|---|
| A — Explanation/reference only: R1–R2, R6, R9–R12 | In a separately reviewed DRAFT addendum, link the implemented partial PoC and newer evidence; explicitly contrast validity bits with candidate presence classes and distinguish technical completion from acceptance. Add dated context/link around old no-real-run notes without rewriting their recorded results |
| A — Explanation/reference only: R4–R5 | State the strict aligned EPSG:6677 execution profile and effective-mask behavior in implementation-facing guidance. Explain that Phase 3 replication is neither bilinear comparison nor new observations |
| A — Navigation | Optionally add a link from Current State to this review in a later navigation PR if it becomes an agreed reference. This review already links Current State; no status refresh is warranted by unchanged implementation/gates |
| B — Standard design decisions: R1, R6–R7 | Decide polygon sources and Native contract, stable IDs/repair/serialization, independent assessment coverage, presence evidence and exact state datatype/encoding/error priority. Do not adopt PoC codes by coincidence or invent absence from CHM |
| B — Standard design decisions: R3–R5, R8–R9, R12 | Decide accepted semantic-review strength, regional grid/extent policy, masked DEM interpolation, CR input/provenance contract and evidence criteria, canonical manifest schema and structural versus real-data acceptance criteria. Avoid arbitrary universal ecological thresholds |
| B — Adapter interface decisions: R10–R11 | Specify retention of source validity/support and conversion loss, eligibility of partially missing bundles, collision/observer masks and model outputs. Keep particular VoxCity rounding, optical values, conditioning and observation-height restrictions engine-specific |
| C — Implementation/verification additions: R1–R2, R7 | Implement and test actual Native/Standard polygon and coverage path only after the corresponding decisions; include boundary-centre ties, overlaps, tiny-object loss, IDs and polygon/CHM disagreements |
| C — Implementation/verification additions: R3–R5, R8–R9 | Add the reviewed DEM sampling comparison; verify source-specific mask contradictions and cross-AOI boundaries; validate external class/spatial CR dependencies and sensitivity before acceptance. Scientific compatibility/accuracy needs evidence beyond the bridge |
| C — Implementation/verification additions: R10–R12 | For Phase 5, retain source sidecars, count Float32 depth collapse/rounded loss/expansion and pre/post Building overwrite, verify raw/effective DEM/D0/common geometry and actual observer/mask parity; test selected real Building identities and halo. These are proposed additions, not completed work |

No production-code fix is established as mandatory to preserve the existing
guarded all-valid canopy-only PoC. This finding is not a general clean bill for
unknown-data fusion: exporting only TREE/relative 0/0 loses source distinctions,
and relaxing strict guards without retained state/coverage is unacceptable.
If future evidence contradicts declared source semantics, generation must block;
do not weaken the Standard to fit plausible-looking output.

## Phase 5 impact and final judgement

The [existing Completion Gate](../experiments/voxcity_canopy_shadow/PHASE4_COMPLETION_GATE_REVIEW_20261027.md)
remains **CONDITIONAL PASS for the canopy-only milestone**, with Phase 5 execution
blocked pending its class A items. This review neither changes that decision nor
closes a class A item. [Phase 5 DRAFT](../experiments/voxcity_canopy_shadow/PHASE5_INTEGRATION_PLAN_v0.1_Draft.md)
still requires selected Building bytes/Z evidence, common grid/ground policy,
observer interpretation and source/overlap/mask policy before implementation.

Independent polygons and surveyed coverage can stay deferred only for the
explicitly height-driven limited experiment; they remain required before complete
Standard Canopy acceptance. They are not prerequisites invented by this review
for repeating the already bounded experiment. The proposed integration must
instead preserve their absence as unknown and never use TREE loss to revise
source presence. Any future claim of full Standard conformity without those
capabilities would be a CONTRACT CONFLICT, not the present §9A exception.

**Final review judgement: CONDITIONAL PASS**, subject to keeping the partial
schema/semantics explicit and obtaining separate decisions/evidence for the
identified B/C work. Standard Canopy remains Draft and unaccepted. No scientific
accuracy, full Canopy implementation or Phase 5 approval is declared. Submit this
single new review for independent review; all existing specifications, Current
State, code, tests, Gate and acceptance/experiment records remain unchanged.
