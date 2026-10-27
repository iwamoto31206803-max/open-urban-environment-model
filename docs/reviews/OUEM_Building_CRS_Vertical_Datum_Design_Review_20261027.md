# Building CRS and vertical datum design review — 2026-10-27

## 1. Executive Summary

**Recommendation: Option B, an explicit source-height-preserving Native profile,
coexisting with a separately identified historical profile. Status: PROPOSED /
REQUIRES APPROVAL.** This document approves no coordinate contract, Standard
revision, implementation, data reinterpretation or acceptance. Phase 5 A1–A4
remain **OPEN**.

Baseline main **`98407a5c7114b5392b11661e66527bd3ac864d88`** was fetched and
PR [#83](https://github.com/iwamoto31206803-max/open-urban-environment-model/pull/83)
confirmed merged at that commit. Inspection date: 2026-10-27 JST.
Evidence is repository source/test inspection plus existing dated records;
there was no Converter build/install/run, real-data transformation or new test run.

[Standard Building v0.1](../OUEM_Standard_Building_v0.1.md) requires absolute
T.P. Z but its historical Native profile is labelled EPSG:4979. The
[source audit](OUEM_PLATEAU_GIS_Converter_Source_Audit_20261027.md) establishes that
the audited Converter's 6697→4979 branch **adds position-dependent geoid height**
and produces ellipsoidal-height numbers. The current Standardizer then preserves
those numbers and describes them as T.P. These paths are semantically incompatible
when joined in that configuration. Preserving numbers is not preserving their
declared vertical meaning.

Option B avoids introducing an unnecessary forward/inverse geoid operation for
source-declared T.P. data. It requires an explicit profile and provenance gate,
a reviewed Standardizer input branch and measured source/output correspondence.
It is **not** already supported end to end merely because generic Native ingest
can copy a 6697 layer. Existing accepted records/artifacts remain immutable,
scoped historical evidence; their actual datum is not reassigned by this review.

Reference basis: [Building Current State](../status/BUILDING_CURRENT_STATE.md),
[Raw acquisition #82](../experiments/voxcity_canopy_shadow/PHASE5_PLATEAU_ACQUISITION_20261027.md),
[vertical diagnosis](../research/OUEM_Komae_Building_Vertical_Geometry_Diagnosis.md),
[Phase 5 plan](../experiments/voxcity_canopy_shadow/PHASE5_INTEGRATION_PLAN_v0.1_Draft.md),
[Documentation Governance](../OUEM_Documentation_Governance_v0.1.md),
[Terrain](../OUEM_Standard_Terrain_v0.1.md),
[Building Adapter](../OUEM_VoxCity_Adapter_v0.1.md) and
[Height Envelope PoC](../CHM_Height_Envelope_PoC_v0.1.md).

## 2. Current Contract Inventory

H denotes source gravity-related elevation, h ellipsoidal height, and N the
Converter's selected geoid-model value. For Komae, H has **source-declared**
T.P. evidence; that does not establish independent survey accuracy, identical
realizations/epochs across sources or nationwide applicability.

| Stage | Horizontal coordinates / metadata | Z meaning, actual operation and ID/geometry boundary | Existing evidence / limit |
|---|---|---|---|
| Raw CityGML | Actual inspected source URI EPSG:6697; source tuple latitude, longitude, Z. Formal compound CRS includes gravity-related height | Read original H unchanged; geometry is multi-LoD, includes parts/surfaces/rings and gml:id. LoD0 zeros are a source representation, not measured ground | #82 directly inspected source; primary mesh 53393456 and neighboring 53393466 needed for initial halo. Historical release identity remains unverified |
| Converter 4979 output | Parser/transform swaps latitude/longitude to GIS longitude/latitude; output requested 4979 | For audited 6697 input, h=H+N(lon,lat), not source-H preservation. Vertex deduplication, selected-LoD filtering and surface/part grouping affect correspondence; source IDs can survive as id | #83 fixed-source call path, not a new executable test or proof of old settings |
| Converter 6697 / projected output | 6697 branch swaps XY and retains H; 6677/compound10170 branches project XY and retain H for geographic input | Numeric H-preserving candidate paths. GeoPackage BLOB/table/WKT consistency and actual output must be independently verified before eligibility | Official v0.1.14 BLOB SRS 4326 bug prevents assuming correct metadata; developer-pin fixes are not automatically present in a release |
| Native Building | Generic ingest records defined source CRS, copies it to output, does not restrict to 4979 | Copies geometry/attributes, including numeric Z, without a coordinate operation. Validates counts, 3D MultiPolygon, required measuredHeight and Z presence, not a complete source-to-output datum proof | [Native worker](../../src/ouem/native/building/_plateau_gdal_worker.py), _validate_layer/_inspect/_ingest. _has_xyz_coordinate checks some finite XYZ per feature, not every vertex. Generic capability is broader than accepted Standardizer input |
| Standard Building | Canonical Komae 6677; worker explicitly requires 4979 Native and uses its4326 horizontal component with traditional GIS order | Restores every source Z after XY transform, checks written values ≤1e-9m; manifest calls it absolute T.P. id→source_id; stable ouem_id; nullable LoD/height; full intersecting geometry retained, not clipped | [Worker](../../src/ouem/standardize/building/_gdal_worker.py), _is_source_crs/_horizontal_transform/_restore_z/_run; [orchestrator/manifest](../../src/ouem/standardize/building/__init__.py). No upstream geoid operation is undone |
| VoxCity Building Adapter | Reads 6677 Standard, derives 2D normalized footprints and explicitly projects them to4326; canonical Standard unchanged | top=max(all geometry Z); height=top−mean(raw VoxCity DEM under assigned ID); min_height=0. IDs mapped to positive engine integers; bottom/measuredHeight do not set relative top | [Adapter](../../src/ouem/adapters/voxcity/__init__.py), check_vertical_compatibility/derive_attributes/_run_voxcity_grids. String/status compatibility is a gate, not numerical datum verification |
| Terrain / Canopy fusion | Terrain6677 at accepted 0.5 m grid; Height Envelope uses a separate explicit 6677 / 1 m PoC grid | Terrain absolute source-declared T.P.; CHM is HAG, not an absolute CRS datum. Envelope top=DEM+CHM, bottom=DEM+CHM×(1−CR). No geoid operation / guessed offset | [Height Envelope validate_sources/calculate](../../src/ouem/height_envelope.py) hash-binds DEM/evidence; same names alone do not prove Building compatibility |

### What existing tests establish

| Tests inspected, not newly executed | Verified intended behavior / evidence boundary |
|---|---|
| [test_plateau_building.py](../../tests/test_plateau_building.py): test_ingest_writes_receipt_manifest_and_summary, test_3d_multipolygon_validation_requires_non_empty_z_geometry | Mocked worker results and FakeSRS explicitly include 6697. Native copy/registration is not inherently4979-only. These tests do not execute Converter or prove true datum/axis preservation |
| [test_standard_building.py](../../tests/test_standard_building.py): test_only_accepted_native_epsg4979_is_validated_as_formal_input | FakeOSR accepts 4979, rejects 6697; this intentionally encodes the current accepted input boundary |
| Same file: test_epsg4979_conversion_uses_only_epsg4326_horizontal_component; test_horizontal_reprojection_restores_every_nested_z_value | Mock OSR source 4326, target 6677 and GIS axis mapping; nested synthetic Z restoration. Not real PROJ/geoid or source-to-Converter verification |
| Same file: ID/metadata/intersection tests | Stable IDs, id mapping, required fields and no clipping; several worker/serialization checks use mocks or source assertions, not an actual new GDAL run |
| [test_voxcity_adapter.py](../../tests/test_voxcity_adapter.py): test_height_uses_absolute_top_and_effective_ground_not_bottom; test_vertical_gate_accepts_declared_tp_and_rejects_unresolved | Synthetic relative-height arithmetic and declared-T.P. gate. A false T.P. declaration can satisfy the string gate; accuracy is not established |
| [test_komae_vertical_provenance.py](../../tests/test_komae_vertical_provenance.py) | Synthetic full geometry/ID/lineage and incomplete-evidence checks support diagnosis; they do not prove historical Komae datum conversion |

Current manifest boundaries also matter. Native receipt/manifest identify the
**Converter GPKG** by hash and hard-code GUI preprocessor text; they do not record
the original GML hash, Converter operation/profile or a complete per-vertex
comparison. The Standard manifest records Native path/operation/validation but
does not itself hash-bind both Native and Standard bytes. The Adapter hashes
its input data and records declared references; that cannot reconstruct missing
earlier evidence. Reusing these records unchanged for a new CLI/profile would
misdescribe provenance. This is a future schema/interface task, not a change here.

### Existing artifacts versus recorded acceptance

[A1](../../experiments/a1_e2e_pilot/README.md) records 3,637 Native / 111 Standard
and numeric Z preservation; [A3](../acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md)
records a bounded accepted integration, with paths but no asserted input hashes.
Neither record proves source-to-Converter vertex correspondence or the new
2025 source equals the old input.

Read-only checks in this review found these **four specific paths missing**:
`data/native/building/komae.gpkg`, its `.gpkg.manifest.json`,
`data/standard/building/komae.gpkg`, its `.gpkg.manifest.json`.
This is not a whole-PC search, proof of all Building absence or a failed historical
acceptance. No old GPKG was decoded/rehashed. Compatibility below is contract/code
analysis; actual old-byte compatibility remains **UNVERIFIED**.

## 3. Source-to-Engine Coordinate Flow

Proposed B flow (names are descriptive, not approved schema/profile identifiers):

```text
immutable Raw 6697: (latitude, longitude, source-declared H), original LoDs/IDs
 → fixed Converter, explicit6697 output and recorded LoD/grouping
 → verified GPKG 6697: stored GIS (longitude, latitude, H)
 → Native source-H profile: copied geometry + hash-bound semantic evidence
 → profile-aware Standardizer: horizontal JGD2011(6668) → study6677; retain H
 → canonical Standard: (easting, northing, absolute H), explicit vertical evidence
 → engine Adapter: retain absolute-Z diagnostics, derive relative model heights
```

EPSG authority axis order and storage/reader axis mapping are separate fields.
A 6697 GPKG label is not permission to swap GIS-order coordinates a second time.
For B, use the JGD2011 horizontal component **6668**, not an unreviewed reuse of
the legacy 4326 transform; set/check the reader's traditional GIS XY mapping.
For Standard 6677, stored GIS coordinates are easting/northing even though EPSG's
formal axis listing differs. All operations need known-coordinate fixtures.

A T.P. Building H, Terrain D_raw, Height Envelope absolute top/bottom, conditioned
D_eff, model origin D0 and voxel index are different quantities. Datum conversion
belongs before canonical Standard/relative-height preparation, **not** in the
engine Adapter. In the proposed Phase 5 scene, D_eff and D0 must be common across
A/B/C; Building top subtracts its model effective ground once, and canopy absolute
top/bottom subtract D_eff once. Ground+1 layer/rounding and ray-origin differences
remain engine geometry, not vertical datum corrections. The existing geographic
Building Adapter is not automatically the projected Phase 5 mapping.

## 4. Identified Semantic Conflicts

| Conflict | Consequence / required boundary |
|---|---|
| Current Standard §3 claims4979-labelled Native Z remains T.P.; audited default Converter creates ellipsoidal h | Applying current restore-Z path to that new output preserves the wrong quantity for the canonical contract. Stop eligibility; no relabel-only repair |
| Generic Native code/tests can copy6697, but Standardizer rejects it | “Native supports6697” is a capability statement, not complete profile/acceptance support. Explicit dispatch and reviewed new provenance are required |
| 4979 can label a historically application-defined H or a genuine new h | EPSG alone, Z magnitude, filename, measuredHeight or approximately 37 m difference cannot select an inverse operation. Ambiguity must remain unresolved |
| Converter table CRS can disagree with per-geometry BLOB header | A layer EPSG/WKT reported by one reader is insufficient. Reject inconsistent output pending independent checks; do not normalize headers silently |
| Adapter's T.P. declaration gate can pass a misdeclared Standard artifact | Add trustworthy upstream evidence at an approved boundary; never interpret its PASS as independent datum accuracy or silently add a new downstream geoid correction |
| Same T.P. name across Building/Terrain is not a precision/epoch comparison | Preserve source realization/epoch/model/accuracy evidence and uncertainty; building bottom can differ from bare-earth DEM for valid structural/temporal reasons |
| LoD0 zero Z / different roof or part selection | Do not treat zeros as surveyed ground, infer datum from extrema or compare unmatched surfaces. ID/LoD/ring correspondence is mandatory |

The [approximately 37 m diagnosis](../research/OUEM_Komae_Building_Vertical_Geometry_Diagnosis.md)
remains **UNRESOLVED**. #83 supports an intentional geoid-addition mechanism,
not proof of old executable/settings/bytes. #82's source target range and
Terrain proximity are useful new-input diagnostics, not retrospective acceptance
or a correction constant. No old record is rescinded or reinterpreted here.

## 5. Design Options

| Option | Proposed processing and semantic condition | Compatibility / cost / principal risks |
|---|---|---|
| **A — keep 4979 container, explicit inverse to H** | Native stores genuine ellipsoidal h; an approved Standardizer branch applies H=h−N at corresponding source positions using the exact documented forward model/algorithm, then horizontal projection | Keeps nominal CRS/container, **not the full old “4979 means H” contract**. Needs a distinct semantic profile, forward-operation proof, grid/hash/interpolation/coverage and uncertainty budget. Blind inverse would corrupt old H or unrelated4979 h |
| **B — add source-H Native profile (recommended)** | Fixed Converter output6697 retains H; GIS-order Native6697 plus explicit vertical/source evidence; Standardizer projects6668→6677 and preserves H | Canonical Standard geometry/meaning can remain the existing target; Native eligibility/manifest and Standard upstream-profile documentation need approval. Avoids unnecessary geoid round trip. Real GPKG/axes/LoD support remains to be demonstrated |
| **C — projected Native profile** | Converter outputs6677 XY with retained H, or a supported explicit compound CRS such as10170 where verified; profile records the complete vertical semantics | Fewer later XY operations for Komae.6677 alone is not vertical metadata; mixed compound/2D reader behavior must be tested. Broader Native contract changes and zone-specific profiles; must not turn6677 into nationwide CRS |
| **D — source-preserving CityGML Native, separate reader/harness** | Retain original CityGML as the semantic Native representation and implement/reuse a separately approved profile-specific route to Standard | Avoids dependence on GPKG conversion semantics but adds parser/reference/LoD/part/geometry responsibility and a larger new interface. Existing Raw retention already preserves bytes; a new label alone provides no new safety. Defer unless B cannot be validated |

### Comparison across required criteria

| Criterion | A | B | C | D |
|---|---|---|---|---|
| Vertical meaning | Explicit h→H when forward chain known; legacy ambiguity highest | Explicit source H; no geoid arithmetic | Explicit H separate from projected CRS | Explicit source H; reader must prove interpretation |
| Terrain/Canopy agreement | Only after inverse/realization/epoch review | Same source-H target, still requires compatibility review | Same as B | Same as B, plus reader validation |
| Existing Standard compatibility | Changes preserve-Z rule for new branch; data contract target H retained | Adds accepted input branch; canonical H requirement retained | Adds projected input branch; output/CRS choice reviewed | New upstream route |
| Accepted artifacts | No automatic inverse/rewrite | Frozen legacy lane; new outputs separately accepted | Same; no in-place reprojection | Same |
| Converter feasibility | Audited4979 branch exists; inverse not currently implemented in OUEM | Audited6697 branch exists; SRS/LoD/binary validation mandatory | Audited geographic→projected H-preserving branches exist; verify zone/axes | Needs another verified parser/harness, no approved ready route |
| GPKG CRS integrity |4979 must mean h until inverse writes separate output |6697 compound label, GIS mapping and BLOB/table consistency required |2D6677+vertical receipt or tested compound; approval required | Depends on chosen output serializer |
| National applicability | Geoid coverage, realization and model versions become operational dependencies | Source-specific horizontal/vertical profiles; never infer T.P. for every source | Per-area projection/compound mapping needed | Highest schema/encoding/provider burden |
| Reproducibility / audit | Additional numerical model and double-conversion controls | Shortest H-preserving chain with explicit receipts | Explicit projection tied to Converter | More independently maintained steps |
| Implementation / maintenance | Highest datum-operation burden; inverse/coverage tests | Moderate profile/dispatch/provenance work | Moderate-to-high multi-CRS routing | Highest parser/geometry burden |

A can be the arithmetic inverse of the **audited forward operation** only when
the identical N model/data, interpolation, XY convention and domain apply.
For that audited route, the source audit identifies embedded **GSIGEO2011** and
resolved **japan-geoid 0.4.4**; package version alone does not identify an actual
binary or prove historical model bytes. Other 4979 inputs need their own evidence.
It is not a universal geodetic transformation from arbitrary WGS84 h to every
T.P./JGD realization. Record model data SHA, package/build identity, source/destination
references and any expected accuracy; do not invent an accuracy budget or use
a newer grid as a silent inverse substitute. This review neither selects a model
for production nor computes a Komae N value.

## 6. Recommended Architecture

**Select B as the design recommendation for review**, with these proposed boundaries:

1. Keep Raw bytes and original source declarations immutable. Preserve the complete
   source bundle, exact member hashes, selected LoDs, parts/surfaces and source IDs.
2. Permit new-source eligibility only with an explicit, versioned **source-H Native
   profile**, validated6697 GPKG and hash-bound Converter receipt. Generic ingest
   may supply the copy operation, but its current shape/CRS checks alone are insufficient.
3. At Standardizer entry, dispatch by approved profile **and verified evidence**,
   never by EPSG alone. Reject missing/conflicting/unknown profile, unit, quantity,
   coordinate operation or data hashes. An unverified4979 file is not auto-legacy.
4. For B, perform only the reviewed horizontal6668→6677 operation and restore/
   compare every retained H, including after serialization. Reject accidental geoid
   processing or an h-profile entering this branch. Preserve whole selected
   geometry, stable id→source_id→ouem_id and original source-LoD evidence.
5. Keep Standard canonical absolute H and current data representation as the
   intended target. Future amendments to upstream profile clauses/manifest are
   explicit review items; this proposal does not rewrite §3/§5 today.
6. Leave engine datum arithmetic unchanged: Adapter receives semantically validated
   Standard H and compatible Terrain, then derives model-relative heights. Any
   Adapter schema-dispatch/provenance gate extension needs separate approval,
   not a compensating Z offset or a changed height formula.

### Proposed provenance requirements (field concepts, not a new schema)

| Evidence group | Minimum information and validation |
|---|---|
| Identity / schemas | Exact Raw ZIP/member, Converter GPKG, Native, Standard and their receipts/manifests by size/SHA; schema/profile/version; run and parent artifact identities |
| Source semantics | Dataset/year/release, actual srsName, formal horizontal/vertical components, Z quantity/unit, axis order, vertical realization/epoch where known; declaration evidence and its reviewed status |
| Executed Converter operation | Repository/full commit, actual executable/build/lock/model identities, platform/runtime, full invocation/settings, requested/observed CRS, LoD/splitting, logs/exit; GUI or CLI recorded truthfully |
| Container / numeric evidence | Every BLOB SRS/type/Z dimension, layer/table SRS/WKT, storage/reader axis mapping, units/scale/offset, ID/part/LoD/ring correspondence, retained/dropped counts and reasons |
| Operation ledger | Each source→destination artifact edge, input/output quantity/reference, horizontal operation separately from vertical identity/inverse, applied direction, parameters/model hashes, explicit no-geoid decision for B |
| QA / acceptance | Independent XYZ residuals, masks/coverage, numerical vs scientific uncertainty, code/environment, repeat results; reviewer and acceptance scope distinct from COMPLETED |

Proposed semantic guards prevent double conversion: H→H B lane explicitly forbids
a geoid step; known h→H A lane, if later approved, requires one hash-bound inverse
edge and produces a new H artifact. Subsequent processing uses the output identity/
quantity, not a mutable “converted once” boolean. Reapplying an h→H operation to H,
unknown provenance, a changed grid/model or a stale receipt must fail. Append
new edge records; never edit old manifests to assert an operation happened.

## 7. Compatibility and Migration

| Phase, all future and approval-dependent | Plan / compatibility rule |
|---|---|
| M0: design decision | Independently review B, historical lane eligibility, profile/schema evolution and §8 tolerance plan; no implementation permission inferred from this Draft |
| M1: controlled Converter verification | Freeze candidate binary/source and execute approved synthetic tests; verify6697/4979/6677 branches, actual LoD and SRS behavior before any real conversion |
| M2: additive input profile | Extend explicit Native provenance/eligibility and Standardizer profile dispatch; retain old 4979/H behavior in a named historical branch, not as a catch-all fallback |
| M3: synthetic / real validation | Validate new branch with synthetic GDAL IO, then separately authorized #82 source conversion and matched vertices; generate new run paths, compare complete source chain and H |
| M4: independent acceptance | Review new dataset/profile chain and downstream compatibility; no inherited111-count or old A3 acceptance for a new source. Phase 5 Gate closure is a separate decision |
| M5: legacy retirement review | Consider ending new use only after agreed replacement, evidence/consumer inventory and migration fixtures pass; retain historical replay code/records or a reproducible frozen environment. No automatic deletion/date-based retirement |

**Legacy policy proposal:** preserve old accepted bytes, manifests, hashes (where
available) and decisions exactly. Keep their existing declared meaning as a historical
claim without silently reclassifying them as h or H. For new analytical eligibility,
require a separate, hash-bound review of actual source/Converter/Z evidence;
unknown files stay unresolved and cannot enter a new mixed scene. If a real error
is later established, add a dated correction/supersession record linking old/new
bytes and changed scope; do not rewrite history or rerun into old paths.

IDs are not dataset-version identifiers: the same source_id can recur in 2025,
and current UUIDv5 source-ID mapping can produce the same ouem_id for different
source bytes/LoDs. Preserve current ID rules unless separately changed; coexistence
uses **dataset/artifact identity + ouem_id**, not a forced global ID rewrite.
Store explicit correspondence/differences between old 111 and new selected IDs
when old data becomes available; matching IDs/counts alone does not prove equality.

**Expected implementation scope after approval:** Native profile/receipt validation;
Standardizer explicit profile and horizontal-source selection; all-coordinate
read/write checks and hash-linked provenance. For B the numerical Standardizer
Z operation remains identity. Do not “support6697” by weakening the4979 test and
retaining its4326 source blindly. No Terrain/Canopy regeneration is implied.

The current Adapter whitelists `ouem-standard-building-manifest/v0.1`; a new
manifest schema is **not automatically compatible**. Preferred proposal: version
Native/provenance explicitly, retain canonical output fields/geometry semantics,
and review whether Standard needs a versioned manifest extension plus linked
evidence or a new schema with explicit reader dispatch. Do not change a schema
name alone to bypass the old reader. Until that decision/tests are approved,
no claim of operational Adapter backward compatibility is made. Its height formula
and canonical data contract need no compensating change under B.

Regression strategy: keep historical-profile fixtures and existing ID/intersection/
Z/Adapter arithmetic expectations. Scope “4979-only” to the historical branch;
add separate6697 profile acceptance/rejection cases. Add real synthetic GPKG
round-trips in the appropriate GIS runtime, not only FakeOSR tests; keep OUEM/GIS
runtimes separate. Compare historical behavior without rewriting old expectations
to make corrected new data appear byte-identical.

## 8. Required Validation

Everything in this section is a **proposed future test**, not an executed result.
Define the full validation matrix, units, tolerances and independent oracle before
running. Artifact hashes/IDs/CRS/profile/state decisions use exact equality;
coordinate and scientific accuracy tests are distinct.

| Test | Proposed checks and pass/stop condition |
|---|---|
| V1:6697 axes | Synthetic non-symmetric latitude/longitude/Z, distinct east/north offsets, closed roof/base rings. Verify source tuple→GPKG GIS XY→6677 using an independent, pinned horizontal oracle and reader mapping. An axis swap, unknown dimension or fallback CRS fails |
| V2:4979 geoid addition | At multiple locations within independently established grid coverage, compare the same vertices to h=H+N using verified model data/algorithm and reference samples. Freeze grid/package hashes; test outside/nonfinite. Correct datum quantity and location dependence required; approximately 37 m is not an oracle |
| V3:6697 H preservation | Same selected LoD/surface/ring vertices after ordering/closure normalization; verify H is unchanged numerically and output semantics/GPKG metadata agree. No inferred ground from LoD0 zeros |
| V4:6677 output | Independent XY projection and storage-axis comparison; original H retained. Inspect horizontal-only6677 plus declared vertical provenance, and compound10170 separately if evaluated. Matching EPSG code alone cannot pass |
| V5:GPKG coherence | All geometry BLOB headers vs gpkg_contents/gpkg_geometry_columns/gpkg_spatial_ref_sys, actual geometry Z/type and decoded XYZ. Any inconsistent SRS or unsupported mixed geometry fails eligibility |
| V6:feature/LoD/vertex identity | Preserve gml:id→id→source_id→ouem_id with dataset identity, parts and selected roof/base rings. Account for dedup/closure/split/merge and every excluded/missing-LoD feature. Unmatched surfaces cannot be used to assert a Z shift |
| V7:Native→Standard | B profile uses6668→6677 and H identity; legacy branch retains its existing behavior. Compare all selected original and reread output Z/IDs/geometry structure; finite values, correct units, no clipping or unexplained loss required |
| V8:Terrain relation | Same XY, valid original Terrain, explicit nearest/other reviewed sampling and full coverage. Separate structural base/lowest vertex from actual bare-earth evidence; plot residuals by position/LoD/date, review independent control points where available. Numeric proximity is diagnostic, not automatic vertical-accuracy acceptance |
| V9:double conversion | Wrong profile/quantity, missing/stale manifest, modified bytes, repeated inverse, different grid, and H mislabelled as h must fail before publication/registration. Coordinate values alone cannot identify an operation's necessity |
| V10:repeat and lineage | Repeat exact pinned packet; compare bytes and separately normalized ID/LoD/XYZ semantics, timestamps/fid/ring order/WAL differences. Full operation ledger/hash links and input nonmutation required; unexplained numerical changes fail |

### Proposed tolerance-setting method

- **H-preserving operations:** retain the current **≤1e-9m maximum Z difference**
  as an initial compatibility criterion for exact numeric copying/restoration
  (both in-memory and reopened output). It is an existing software-preservation
  check, not survey accuracy. Use unrounded f64 source values; altered vertex
  sets must first be explained by V6. Ratifying it for a new profile is reviewable.
- **XY operations / vertex matching:** agree a metre-based budget from source
  precision, reference arithmetic/round-trip behavior and GIS serialization.
  Use an independent pinned oracle and controlled fixtures before setting it;
  do not use voxel size, a single successful point or historical 2 m roof QA.
  Matching tolerance must not accidentally pair different source vertices.
- **Geoid arithmetic:** separately bound floating/interpolation/serialization error
  against independently checked model samples; scientific model accuracy and
  realization/epoch uncertainty need their own evidenced budget. No numeric
  geodetic-accuracy tolerance is established by this review.
- **Terrain agreement:** predeclare diagnostics and review limits using the real
  source/ground evidence and acquisition dates; no universal bottom-to-DEM zero
  residual threshold is justified. NoData/outside samples are excluded explicitly
  with denominators, never filled. A datum declaration remains source-declared
  until stronger independent evidence exists.
- **Determinism:** exact hashes for identical artifacts/ledger edges; repeated
  numeric/semantic results must meet the predeclared computation tolerances.
  Byte differences require an explicit metadata/order explanation and do not
  themselves prove numerical equivalence. Do not tune bounds to observed results.

V1–V7 and V9–V10 are technical eligibility checks; V8 plus source/datum review
establishes only its documented compatibility scope. None grants scientific
accuracy or Standard Canopy acceptance. Any missing required evidence blocks
eligibility; a narrower claimed scope needs a recorded review before execution.

## 9. Decision Register

“Verified Existing Behavior” below means checked code/test definitions or an
explicitly cited prior record, not fresh successful runtime validation.

| ID | State | Decision / observation and owner boundary |
|---|---|---|
| D01 | Verified Existing Behavior | Audited Converter6697→4979 adds model N;6697 output preserves H and swaps XY. #83 pins/function references; historical use remains unverified |
| D02 | Verified Existing Behavior | Native generic copy can record 6697; Standardizer currently permits 4979 only and preserves numeric Z. Tests and code in §2 |
| D03 | Verified Existing Behavior | Canonical contract requires6677 horizontal + absolute T.P.; Adapter subtracts model ground. These remain current requirements, not new decisions |
| D04 | Proposed | Prefer Option B with explicit source-H profile, independent provenance gate and6668 horizontal-source branch |
| D05 | Requires Approval | Native/Standard profile identifiers, truthful CRS/vertical fields, versioned manifest evolution and legacy eligibility; no schema finalized here |
| D06 | Requires Approval | Converter repository/full commit/binary/Windows route, actual supported LoD policy, splitting/parts and GPKG integrity; do not adopt a label-only version |
| D07 | Requires Approval | V1–V10 oracles/tolerances, authoritative model/data for any A experiment and source/epoch compatibility review scope |
| D08 | Proposed | Freeze historical artifacts; additive correction/new outputs and explicit dataset+ID coexistence; no inferred inverse or37m correction |
| D09 | Deferred | Option A as a separate verified ellipsoidal profile; Option C projected profile; Option D new parser/harness unless justified after B validation |
| D10 | Deferred | Historical root cause/old binary recovery, national provider profiles/vertical realizations, independent accuracy and accepted-data retirement |
| D11 | Requires Approval | Later Standard upstream-clause / Implementation / Current State updates and new dataset acceptance, after tests/evidence; all Phase 5 A1–A4 remain OPEN |

## 10. Open Questions

1. Which candidate executable demonstrably preserves6697 H, writes coherent GPKG
   CRS, supports the approved LoD policy and fails safely on Windows? #83's
   developer commit is not a tested Windows release or an approved deployment.
2. What exact original Converter/input/settings produced the historical accepted
   bytes? The current four missing canonical paths cannot answer this, and
   source ID/count similarity is insufficient.
3. Which source realization/epoch and bare-earth evidence establish the required
   Building/Terrain compatibility for this chosen dataset? T.P. labels and
   hash identity establish different facts.
4. Can the new profile's manifests be consumed with an approved compatible
   extension, or is versioned reader dispatch necessary? No current reader
   support should be presumed.
5. How will split BuildingParts/roof surfaces, missing LoDs, near-coincident
   vertices and repeated source IDs across releases be recorded without loss?
6. Which old data remain available for replay, and what narrower scope can be
   justified if their source-to-Converter chain is unrecoverable? Only independent
   review can approve eligibility/retirement; this proposal changes no acceptance.
7. Phase 5 common D_raw/D_eff/D0, grid/IDs, source validity, canopy/building overlap,
   observer origins, common masks and all-scene halo remain separate prerequisites.
   Closing a datum question alone would not close A1–A4.

**Next minimum action:** approve or amend D04–D07, then separately authorize
controlled Converter CLI fixtures with exact source/binary/model identities.
Only after those pass should a new #82 real-data conversion be considered.
No execution or implementation is authorized by the present recommendation.

## 11. Documentation Impact and Review Validation

This PR adds **only this design review**. Architecture/Standard is analyzed but
not amended; Implementation/Interface describes current code plus clearly marked
future changes; no code or tests change. Verification uses prior bounded evidence
and code inspection, not a new acceptance. Current State and historical
Acceptance/diagnosis records remain unchanged under the task constraint.
A later approved profile must update the owning upstream-profile/interface/
manifest documentation and Current State through its own reviewed PR.

The new document's local paths/links and cited test/function names are checked
against this baseline; Git scope/whitespace are checked for the Draft PR.
No Python/Rust tests, Converter build/install/run, new geoid computation,
CityGML conversion, Native/Standard generation or engine experiment was performed.
The four existence checks in §2 were read-only and path-specific. Raw and existing
outputs/manifests were not altered. Independent review is required; no merge
or new coordinate contract/Standard/Gate approval is declared.
