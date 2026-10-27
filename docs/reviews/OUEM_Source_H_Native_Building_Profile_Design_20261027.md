# Source-H Native Building profile and Standardizer migration design

Status: **Proposed / requires design approval**, 2026-10-27. This is an
implementation-ready candidate, not a new authoritative Standard, an implemented
profile or acceptance. Option B remains unapproved. Phase 5 A1–A4 remain OPEN.

## 1. Baseline and evidence boundary

Main **`6f654ef4b76dfbfacd340833b17de4109ded5c2a`**, with PR #87 merged, was
inspected. This specializes [#84 Option B](OUEM_Building_CRS_Vertical_Datum_Design_Review_20261027.md)
using [#87 CLI execution](../experiments/plateau_converter/CLI_SYNTHETIC_EXECUTION_20261027.md)
and its [compact evidence](../experiments/plateau_converter/evidence/CLI_SYNTHETIC_EXECUTION_20261027.json).
Other owning references are [#83 source audit](OUEM_PLATEAU_GIS_Converter_Source_Audit_20261027.md),
[#85 fixture/preflight](../experiments/plateau_converter/CLI_SYNTHETIC_VERIFICATION_20261027.md),
[#86 GDAL assessment](../experiments/plateau_converter/GDAL_ALTERNATIVE_FEASIBILITY_20261027.md),
[Standard Building](../OUEM_Standard_Building_v0.1.md),
[Building Current State](../status/BUILDING_CURRENT_STATE.md) and
[documentation governance](../OUEM_Documentation_Governance_v0.1.md).

**Verified existing behavior:** #87 demonstrates source-H preservation for a
two-building synthetic 6697 GPKG and 6677 horizontal projection, explicit LoD2
geometry/ID preservation and internally coherent BLOB/table/WKT SRIDs. It does
not test Native/Standard execution, real CityGML, full solid topology or independent
geoid accuracy. The tested 4979 branch adds location-dependent N to H. Neither
that branch nor a roughly 37m constant is part of the proposed new route.

Current State's older dated source-Z discussion remains historical; #83/#87
refine the known pinned Converter behavior, not the identity or cause of old
A1/A3 artifacts. No old evidence or Current State is rewritten here.

## 2. Current implementation and actual gaps

| Existing owner / function | Observed behavior | Gap for source-H eligibility |
|---|---|---|
| [Native orchestrator](../../src/ouem/native/building/plateau.py): `ingest_converter_geopackage`, `write_manifest` | Copies a Converter GPKG via GIS subprocess; `ouem-plateau-native-ingest/v0.1` records Converter GPKG source SHA, path/layers, runtime, counts, fields, warnings | No explicit profile, Raw-to-Converter evidence or Native output SHA; `manual_preprocessor` is hard-coded GUI even for a future CLI input |
| Same: `_receipt_value`, `_receipt_matches` | `ouem-plateau-native-receipt/v0.1` caches source path/hash, requested layer, provider/preprocessor | Output existence/nonzero size and receipt equality are not Native byte identity or current semantic eligibility |
| [Native worker](../../src/ouem/native/building/_plateau_gdal_worker.py): `_inspect`, `_validate_layer`, `_compare`, `_ingest` | Defined CRS, 3D MultiPolygon, nonempty geometry, some finite XYZ per feature; count/field/type/CRS-label comparisons; clone/copy | Does not independently compare every XYZ, every attribute value or Raw building/surface correspondence; one finite vertex does not validate all vertices |
| [Standard orchestrator](../../src/ouem/standardize/building/__init__.py): `standardize_native_buildings`, `deterministic_ouem_id` | No Native manifest/profile argument; fixed 6677 Komae target; emits `ouem-standard-building-manifest/v0.1` with paths, operation, Z claim, selection and validation | No hash-linked Raw/Converter/Native chain; operation string always describes legacy 4979/4326 path |
| [Standard worker](../../src/ouem/standardize/building/_gdal_worker.py): `_is_source_crs`, `_horizontal_transform`, `_points`, `_restore_z`, `_run` | Requires 4979; horizontal4326→6677; captures/restores all Z and rechecks after writing; full intersecting geometry retained; stable IDs | No source-H profile dispatch, 6668 horizontal source, full native CRS-BLOB audit or datum eligibility gate |
| [VoxCity adapter](../../src/ouem/adapters/voxcity/__init__.py): `adapt_standard_to_voxcity` | Allows `ouem-standard-building-manifest/v0.1`, hashes actual inputs in its own record, applies existing vertical-reference gate | A proposed new Standard manifest version is currently rejected. Existing reader is not automatically provenance-compatible |

Core tests: [Native](../../tests/test_plateau_building.py),
[Standard](../../tests/test_standard_building.py),
[Adapter](../../tests/test_voxcity_adapter.py),
[vertical diagnosis](../../tests/test_komae_vertical_provenance.py).
Mocks/FakeSRS demonstrate local assertions, not actual GPKG/Converter operation.

## 3. Proposed profiles and version dispatch

Identifiers are **candidates**, not registered schemas:

| Exact profile key | Use / eligibility |
|---|---|
| `ouem-native-building/plateau-source-h/v0.1` | New source-H lane below; full chain validation required |
| `ouem-native-building/plateau-legacy-4979-claimed-tp/v0.1` | Explicit historical replay lane only, with hash-bound legacy registration; declared historical T.P. claim is not newly verified geodesy |

Profile family and major/minor version are parsed separately but dispatched by
**exact registered key**. Unknown versions fail; never accept a prefix or infer
a profile from EPSG/path/date. Profile version controls interpretation; manifest
schema version controls serialization. Semantic changes require a new profile
version and an explicit migration review; nonsemantic clarifications may amend
the same design with a decision log. No implicit latest-version upgrade.

### Source-H candidate v0.1

- Input: Converter **EPSG:6697** 3D MultiPolygon GPKG. Formal compound reference:
  horizontal JGD2011 geographic (6668), gravity-related vertical component
  declared by source (6695 for this 6697 profile). Unit metre for H.
- Storage/reader mapping: **X=longitude, Y=latitude, Z=H** in GPKG GIS order;
  Raw EPSG:6697 tuple is latitude/longitude/H. Record both, including traditional
  GIS axis mapping for OGR. Do not relabel as 4979 or run a compound 3D transform.
- H is source-declared gravity-related absolute elevation. Record exact source
  declaration/reference/evidence hash and realization/epoch if known; unknown
  survey accuracy/epoch is retained as unknown, not supplied by the EPSG number.
- Initial qualified recipe: #87 pinned Converter commit
  `ce7766df9788ce391b149c55df16d33082d0bc72`, CLI SHA
  `0195a11df4fd0ef30dcd5578175035a918c41285b1fcc329f3399f5337326f1b`,
  explicit `--sink gpkg --epsg 6697 -t use_lod=lod2`, resolved
  `split_components=false`. Omission of the split flag must bind its default
  to that audited binary. Other builds/recipes need a reviewed qualification
  receipt; same version string is insufficient.
- Initial bounded geometry support: top-level Building and its selected LoD2
  polygon surfaces/rings grouped under preserved parent `id`. No repair,
  tessellation, simplification, merge across buildings or dimension reduction.
  BuildingPart, external/unresolved xlink and uninspected geometry constructs
  are fail-closed until a separately tested mapping is added. This may block a
  real tile; synthetic success is not an assertion of PLATEAU v5 coverage.
- Record LoD as requested **and observed**, with per-building selected geometry
  evidence. No `max_lod`/fallback can stand in for explicit LoD2 in this first
  recipe. The LoD1 control in #87 is evidence for a control, not permission to
  expand the new profile without review.
- Stable identity is Raw parent `gml:id` → Converter `id` → Native `id`.
  Required ID mapping includes member hash and parent identity. IDs must be
  nonempty and unique within the declared merged dataset; duplicates across
  tiles are rejected for explicit review, not silently renamed/deduplicated.
- Existing `measuredHeight` ingest requirement is retained; missing values do
  not trigger invented heights. Numerical Z and canopy/building presence are
  not inferred from measuredHeight or a feature count.

Eligibility requires the whole selected-source inventory. Buildings with no
requested LoD are explicitly inventoried as excluded before correspondence
validation; their absence cannot be silently treated as Converter loss or
coverage. Each eligible Building must map exactly once and all its selected
surfaces/rings/vertices must match. Unknown differences block the run.

## 4. Proposed data flow and validation boundary

```text
Raw ZIP (if applicable) + exact CityGML/dependency member bytes
  -> source inventory: declarations, eligible/excluded IDs and selected LoD geometry
  -> hash-bound Converter run/qualification evidence
  -> Converter GPKG 6697, GIS lon/lat/H + all-coordinate correspondence QA
  -> Native copy to new GPKG + reopen/all-coordinate and attribute-value QA
  -> Native manifest/receipt v0.2 + immutable operation ledger
  -> explicit profile + verified provenance gate (before Standard output creation)
  -> horizontal 6668 -> 6677 only, restore each H, select full intersecting geometry
  -> new Standard GPKG + reopen/all-coordinate QA + manifest v0.2
  -> independent dataset review; future Adapter schema support is a separate gate
```

Every artifact reference contains relative locator, size and lowercase SHA-256;
path is a locator, not identity. All referenced bytes/records must be available
for new-lane eligibility. Store immutable small source-declaration snapshots and
validation reports beside runs; no need to embed entire Raw data in manifests.
Use new output paths. Validate in staging, close all Windows handles, reopen and
verify before publishing artifacts/COMPLETED records. No automatic overwrite,
no reuse of a partly written output, and a failed run must not publish eligible
outputs. Multi-file publication/rollback needs fault tests; a status flag alone
is not atomic publication. None of this safety behavior is claimed implemented.

Parent orchestration hashes artifacts, checks exact profile/schema and passes
only a validated job to the GIS worker. Worker independently validates actual
CRS/storage, geometry and profile-specific operation; it must not trust an
unvalidated string supplied in the job. Hash/reopen after processing detects
input changes; reject changes during the run. Revalidate on every cached reuse.
Do not use `_receipt_matches` v0.1 as the new gate.

## 5. Manifest/receipt additions and proof of source correspondence

Recommended serialization candidates, all requiring approval:

- Native manifest: `ouem-plateau-native-ingest/v0.2`.
- Native cache receipt: `ouem-plateau-native-receipt/v0.2`.
- Standard manifest: `ouem-standard-building-manifest/v0.2`.
- Converter-run evidence: candidate `ouem-building-converter-run/v0.1`.
  Existing #87 compact JSON is experimental evidence, **not** this schema.
  An importer must validate its content and emit a new linked record, never
  rename that JSON's schema or overwrite its bytes.

| Proposed group | Required contents / validation | Relation to current fields |
|---|---|---|
| `profile` / `schema` | Exact key/version, rule implementation version | New; do not overload current provider |
| `artifacts` | Raw archive (when present), all selected GML/dependency members, Converter GPKG, Native GPKG: path/size/SHA; referenced record digests | Extends `source.sha256`; adds actual Native/output identity |
| `source_declaration` | Actual srsName, axis/dimension, horizontal/vertical components, quantity=`gravity_related_height`, metre, exact evidence URI/snapshot SHA; known/unknown realization/epoch, reviewed scope | New; independent accuracy remains unknown |
| `converter` | Repository/full commit, binary SHA/size, version, build target/profile/compiler/lock identity; argv, resolved defaults, environment/time/exit/stream hashes, output identity, qualification reference | Replace truthful per-run preprocessor metadata in new schema; never label CLI as GUI |
| `geometry_selection` | requested/observed LoD2, split=false, source-layer mapping, eligible/excluded IDs/reasons/counts; member+ID+surface/ring correspondence report SHA | New; a matching ID or count alone is inadequate |
| `coordinate_contract` | source vs storage vs reader axes; expected/observed WKT, BLOB SRID/type/Z, units and vertical identity | Extends scalar CRS labels |
| `operations[]` | Input/output artifact IDs; per edge horizontal operation, `vertical=identity_H`, no model/offset, implementation/environment, parameters, report reference | New append-only graph; rejects unrecorded h/H changes |
| `validation` | Per check status, totals, unmatched IDs/geometries/vertices, max errors, budgets/oracle identities, all finite/dimension checks, warnings/unverified list | Retains current results but separates computed QA and human semantic review |
| `eligibility_review` | Actual reviewer identity/date, decision scope, exact reviewed record-set digest; acceptance reference separately nullable | New; a hash/COMPLETED flag is not scientific truth or formal acceptance |
| `cache_key` | Profile+schema, Converter/Native bytes, layer, recipe, provenance-record digests, verifier version | Replaces source-only v0.1 reuse semantics for new lane |

All mandatory evidence links are verified, including parent record hashes and
actual Raw/GPKG bytes. Optional unknown facts are explicitly null with reason;
required source H semantics/correspondence cannot be null. A record-set digest
binds review to immutable records, not mutable `approved=true` inside the file
being hashed. Human review is authenticity/semantic evidence, not a digital
signature requirement or proof of independently surveyed heights.

Candidate wire-level rules for implementation review:

- Artifact reference: `{path: string, size_bytes: nonnegative integer,
  sha256: 64 lowercase hex characters}`; geometry references also require
  `layer: nonempty string`. Arrays of Raw members cannot be empty. File hashes
  use actual bytes, not normalized geometry or decoded/re-encoded JSON.
- `profile` is the exact key string; `schema` is a separate exact schema string.
  `operations` is an ordered array of edges with `input_artifact_ids`,
  `output_artifact_id`, `horizontal_operation`, `vertical_operation` and
  `validation_report` reference. Native copy and Standard H preservation each
  require `vertical_operation="identity_H"`, `offset_m=0`, `geoid_model=null`;
  Raw→Converter separately records the latitude/longitude storage-axis swap.
- `converter.argv` is a string array; `resolved_options` explicitly includes
  `sink="gpkg"`, `epsg=6697`, `use_lod="lod2"`, `split_components=false`.
  `exit_code` must be integer0, and `execution_status="COMPLETED"` is required
  independently of `validation`. An exit0/COMPLETED run can still fail eligibility.
- Each `validation.checks[]` entry has `id`, result in `PASS|FAIL|NOT_RUN`,
  scope, method/version, evidence reference, counts and optional unit-labelled
  residual/budget. All mandatory checks require PASS. Unsupported/bypassed checks
  are NOT_RUN, never silently true. Numerical QA and review/acceptance remain
  separate fields; a mandatory check cannot be waived by a generic review flag.
- External `eligibility_review` contains reviewer identity, timestamp, reviewed
  record-set digest, profile key, scope and decision `ELIGIBLE|INELIGIBLE|PENDING`.
  New-lane dispatch requires ELIGIBLE for the selected chain. A pending review
  can retain diagnostic reports but cannot authorize Standard generation. An
  acceptance reference is separately null unless an actual scoped approval exists.
- Missing/unrecognized required values or conflicting duplicate declarations
  reject the record. Informational extension keys are allowed only in an explicit
  `extensions` object and cannot override known fields. Actual source srsName and
  inspected geometry declarations must agree; parser fallback6697 is not evidence.

Avoid circular digests: Converter-run record references its input/output bytes;
Native manifest references that record and Native bytes; cache receipt references
the completed Native manifest hash, without the manifest referencing the cache
receipt hash. Standard manifest references Native bytes/manifest and its own
Standard GPKG bytes, never its own hash. Later review records reference these
completed manifests. Final eligibility is evaluated against that external review
record and the currently verified graph.

### Full correspondence algorithm (proposal)

Stream the selected Raw members and build a bounded per-building inventory of
LoD2 surfaces and exterior/interior rings. Fail on unsupported references or
ambiguous dimensions. Preserve parent ID, member hash and surface/ring identity
in the report even if Converter loses thematic IDs. Group Converter polygons
under the same parent ID and require one-to-one polygon/ring correspondence,
allowing only cyclic ring starts/direction and documented surface ordering.
All XYZ occurrences, closure, holes and duplicate multiplicity are checked;
coordinate deduplication in internal storage is not a missing surface.

Compare Raw lat/lon/H to Converter lon/lat/H: exact H identity is the target,
with maximum absolute H residual ≤1e-9 m as the existing computational bound.
Nonprojected XY should be identical after axis mapping; any nonzero discrepancy
needs a pre-reviewed diagnostic budget, not a post-hoc tolerance change.
For the initially qualified recipe, unexpected topology/tessellation changes
block rather than being normalized away. Build/report hashes and normalized
digests are diagnostics; they do not replace per-vertex correspondence or prove
real-data source correctness. Readback may reorder rings only under a documented
bijection preserving all vertices and ring roles; otherwise reject.

## 6. Standardizer dispatch and exact output contract

Proposed public inputs (not current options): `--native-profile`,
`--native-manifest`, `--provenance-review`; a legacy invocation additionally
needs `--legacy-registration`. Function arguments mirror these references.
Do not infer them from adjacent filename, EPSG or a reused receipt. All validation
precedes output creation, including via a direct library call.

Dispatch table:

| Explicit profile and verified graph | Operation | Action |
|---|---|---|
| source-H v0.1, valid reviewed6697/H chain | GIS-order horizontal6668→6677, identity H | New lane |
| legacy key, registered exact4979 bytes and historical replay authorization | Existing horizontal4326→6677, retained historical numeric Z/claim | Historical replay only; not new scene eligibility |
| 4979 file from #87 h branch, missing/unknown profile, stale/failed evidence or conflicting quantity | None | Reject before output; no fallback or inverse conversion |

New worker constructs **2D** EPSG:6668 and 6677 spatial references with
`OAMS_TRADITIONAL_GIS_ORDER`. It must not construct a compound6697→6677 pipeline
and hope that Z stays unchanged. Record actual PROJ/GDAL operation and missing
grid/ballpark warnings; no silent fallback/geoid/offset or assumed datum from
EPSG:6677. Pin the computational operation/runtime in the run evidence.

For every Native feature (before AOI exclusion), recursively validate finite
XYZ, exact coordinate dimensionality, rings/structure and ID. Capture each H,
transform XY only, restore each H and require the same structure/vertex count.
Select by transformed 2D intersection with the configured **closed** AOI rectangle;
retain the full selected geometry, without clipping, as today.
Close/write/reopen and compare **all** selected XYZ/ring correspondence, H residuals,
IDs, attribute mapping and BLOB/table/WKT. Use existing ≤1e-9 m H bound before
and after serialization, aiming at exact numeric preservation. Horizontal
diagnostic budget ≤1e-4 m against the independent synthetic oracle comes from
#85/#87, not a geodetic accuracy claim. Unsupported reorder/missing vertex fails.

Maintain output layer `building`, existing 3D geometry representation, and fields:
`source_id` = preserved Native `id`, literal `source_dataset='PLATEAU CityGML'`,
`measured_height` existing mapping, `ouem_id` = `oub-` + UUIDv5(URL namespace,
`ouem-standard-building-v0.1|PLATEAU CityGML|<source_id>`). No new UUID rule.
Treat artifact/dataset identity plus ouem_id as the cross-release identity;
same ID does not prove same geometry or source version.

Preserve the current nullable `source_lod` mapping: copy an existing recognized
Native field; otherwise leave null. The new manifest/correspondence report must
still record the explicitly selected LoD for **every** selected ID. If an existing
field contradicts receipt LoD, reject. Populating a formerly null Standard field
from the run record is a separate mapping change requiring review; this design
does not silently introduce it or mutate Native inputs.

Output remains horizontal6677 plus absolute source-declared H, intended to meet
the existing canonical representation. Standard §3/§5 currently describe the
4979-only accepted input, so approval of this design must be followed by an
explicit owning-spec amendment before claiming new-profile conformance. This
PR makes no such amendment or operational compatibility claim.

### Standard manifest / Adapter compatibility choice

Recommend explicit **v0.2 Standard manifest**, retaining current core output
semantics/fields and adding input/output hashes, profile, Native/Converter evidence,
vertical operation and review references. Do not silently attach new semantics
under v0.1 or merely whitelist a new schema string. This means the current
VoxCity adapter rejects the new manifest, which is an intentional migration gate.
Later reader dispatch must validate the new fields before using unchanged height
arithmetic. An adapter version/reader patch requires its own approved implementation
and regression evidence; no Terrain/Canopy regeneration or compensating Z change.
Alternative v0.1 plus sidecar is deferred because current readers could ignore
the eligibility boundary. New metadata versions are proposed, not registered here.

## 7. Historical compatibility and migration

1. Freeze accepted A1/A3 files, manifests, declared meanings and records. Do not
   interpret every historical4979 Z as h, or claim its T.P. meaning newly proven.
2. No automatic legacy selection for unprofiled files. A new **external legacy
   registration** must bind exact Native/manifest bytes to the actual historical
   acceptance record, eligibility=`historical_replay_only`, observed CRS and
   explicitly unresolved original Z evidence. Missing artifact hashes/bytes
   cannot be invented from an acceptance path/count; registration then blocks.
3. A legacy registration cannot bless a new GPKG produced today, including an
   h-producing Converter run. No copy/relabel/profile-only migration. A new
   source-H dataset needs a new Raw→Converter→Native chain and separate review.
4. Preserve old numerical/ID/selection/Z operations in a named legacy branch and
   a frozen historical environment for exact old unprofiled command replay.
   New entry points reject unprofiled inputs; do not expose an unrestricted
   `--assume-tp` bypass. Historical replay outputs go to new directories and
   remain ineligible for a mixed analytical scene without a separate review.
5. Existing test **invariants** remain: GUI metadata for the historical writer,
   stable UUID, 4979 historical horizontal path, complete geometry, H preservation
   and Adapter arithmetic. Stricter entry checks necessarily require test setup
   to supply explicit legacy descriptors/new reviewed fixtures in a future PR;
   do not claim all unchanged orchestration mocks will pass with required new
   arguments. Keep numerical/semantic assertions, add missing-profile rejection
   and separate new-lane tests; never weaken old assertions to admit6697.
6. Old v0.1 readers/outputs remain supported for registered replay. No retirement
   date is selected. Removing legacy replay or changing acceptance requires a
   later reviewed correction/supersession decision, never in-place rewrites.

## 8. Proposed code touchpoints after approval

| File/owner | Minimal proposed change |
|---|---|
| `src/ouem/native/building/plateau.py` | Add explicit profile/evidence inputs, truthful CLI preprocessor for v0.2, graph validation, Native hash, receipt v0.2 cache gate; keep historical v0.1 writer/replay behavior scoped |
| `src/ouem/native/building/_plateau_gdal_worker.py` | Audit actual CRS/BLOB/WKT/axes and every XYZ/attribute-value correspondence on new ingest/reuse; keep GIS process boundary |
| New small profile/provenance validator under `src/ouem/native/building/` | Exact schema/profile dispatch, hash graph and review gate; share validation without duplicating Standard spec or implementing a general CityGML parser |
| `src/ouem/standardize/building/__init__.py` | Explicit validated-profile args/job, versioned operation/provenance manifest, native/output hashes; keep ID rule/selection/fields |
| `src/ouem/standardize/building/_gdal_worker.py` | Profile-aware entry guard and 6668 horizontal lane; strengthen full-structure readback; retain legacy numerical lane |
| `src/ouem/adapters/voxcity/__init__.py` (later gate) | Explicit v0.2 manifest eligibility dispatch after review, unchanged vertical arithmetic; current reader intentionally remains incompatible |
| `tests/test_plateau_building.py`, `tests/test_standard_building.py` and new focused profile tests | Preserve historical assertions with explicit test eligibility; add dispatch/provenance negatives and actual synthetic GPKG subprocess tests |
| `tests/test_voxcity_adapter.py` and existing diagnosis tests | Protect schema rejection, height/Z semantics, IDs and unrelated diagnosis behavior |
| Owning Standard/usage/Current State docs (separate approved implementation PR) | Amend accepted-input description and document actual new interface/state only when authorized; no current change |

CLI parser wiring remains thin; reusable policy belongs in `src/ouem/`. Keep
OSGeo4W/QGIS child runtime separate from the OUEM venv. No Converter source patch
or new large parser is authorized. If full real source correspondence exceeds
the bounded verifier, block that dataset and review an extension instead.

## 9. Rejection codes and test/acceptance matrix (all future unless noted)

Error codes below are proposed machine-readable categories with a failing edge,
artifact/feature/ring locator and human diagnostic. No eligibility outputs on
failure. No automatic retry with another profile/CRS/LoD.

| Case / error | Unit tests | Synthetic GPKG/CLI execution | Separately authorized real CityGML |
|---|---|---|---|
| Unknown/missing version/profile (`PROFILE_UNSUPPORTED`) | Exact dispatch; no EPSG/default fallback | Same6697/4979 bytes rejected with unknown profile | No invented profile from old path |
| Missing/stale record or SHA (`PROVENANCE_MISSING`, `HASH_MISMATCH`) | All required edges, canonical review binding, relocated locator same bytes allowed, cycles rejected | Mutated Raw/Converter/Native/manifest and output on cache reuse rejected | Stream-hash full selected source bundle/dependencies |
| CRS/WKT/table/BLOB disagreement (`CRS_INCONSISTENT`) | Correct profile incompatible with any inconsistent actual code | Deliberately mismatched individual BLOB, 2D WKT masquerading compound, wrong units/Z dimension | All feature headers and source declarations checked |
| Wrong storage/reader axes (`AXIS_MISMATCH`) | Explicit GIS/authority maps | Swapped lon/lat fails source correspondence and independent XY controls | All selected source→Converter coordinates; bounds alone not proof |
| Missing/nonfinite XYZ (`GEOMETRY_INVALID`) | NaN/Inf/2D anywhere, including a later vertex in a feature | Round-trip rings/holes, no first-finite-vertex shortcut | Full supported geometry audit; unsupported constructs fail |
| H vs h / unintended model (`VERTICAL_SEMANTICS_CONFLICT`) | Quantity/operation ledger reject any H→h edge for this lane | #87-style4979 output and6697-labelled shifted Z rejected; no offset correction | Full correspondence, declared H evidence; no survey-accuracy inference |
| LoD/ID/part mismatch (`SOURCE_CORRESPONDENCE_FAILED`) | Empty/duplicate IDs, wrong LoD field/receipt, missing/excess vertices | Two-building LoD1/2 distinction,20 LoD2 faces/24rings/120 occurrences; fail on dropped hole or parent misassignment | Eligible/excluded ID inventory, tile-boundary duplicates and all selected geometry |
| Standard XYZ/ID/selection regression (`OUTPUT_QA_FAILED`) | Keep UUID/nullable fields and all-H traversal assertions | Reopen actual Standard GPKG, full XY/H/ring bijection, AOI boundary retains whole building | Source→Native→Standard matched geometry and Terrain comparison reported separately |
| New4979 auto-legacy (`LEGACY_NOT_REGISTERED`) | Unregistered files never legacy | Exact registered historical fixture can replay; modified bytes blocked | Missing historical artifact/evidence remains unavailable |
| Interrupted write or concurrent input mutation (`PUBLICATION_FAILED`) | Simulated faults, no overwrite | Windows handle-close/reopen and rollback tests; FAILED record not usable | No failure promoted to completed/accepted |
| Repeatability / Adapter (`SCHEMA_UNSUPPORTED`) | Deterministic IDs, explicit schema lanes | Semantic equality vs byte hash distinguished; current Adapter rejects v0.2 until reader implementation | Dataset-specific new acceptance and downstream review required |

Pass/stop budgets: exact hashes/IDs/schema/version/counts; finite XYZ and complete
ring correspondence; H identity with ≤1e-9 m maximum absolute residual before
and after write; ≤1e-4 m synthetic horizontal computational residual against a
fixed independent oracle. #87 observed exact H and ~3.23e-8 m XY residual; it did
not validate these new-lane workers. No arbitrary real-world height tolerance,
ecological threshold or independent accuracy claim is introduced.

Layer U (unit): mocked policy/dispatch and traversal. Layer S (synthetic): actual
GIS-runtime GPKG IO, source correspondence and independent full readback on a
qualified Converter. Layer R (real): separately authorized PLATEAU source chain,
schema/geometry scope, all selected XYZ, IDs and source reference; Terrain ground
comparison diagnoses offsets/surface differences but does not force a fit or
prove measured accuracy. Passing U does not pass S/R; #87 passes only its recorded
Converter checks. Real and downstream acceptance need independent scope decisions.

## 10. Decisions, unresolved items and next gates

| ID | Candidate / status | Required review or remaining evidence |
|---|---|---|
| D1 | **Proposed** source-H exact key, 6697 GIS lon/lat/H, LoD2 unsplit first recipe | Approve bounded geometry/recipe and explicit version registry before implementation |
| D2 | **Requires Approval** Native/receipt/Standard v0.2 plus hash-linked Converter evidence | Approve serialization/required fields, external review binding and Adapter migration gate |
| D3 | **Proposed** 6668→6677 only; all H preserved; stable IDs and nullable LoD mapping unchanged | Approve entry contract and implementation/test work; owning-spec input clauses require explicit amendment |
| D4 | **Requires Approval** registered legacy replay only; no automatic4979 fallback | Inventory actual old bytes/records; setup adaptation in tests; pin historical runtime for unprofiled replay |
| D5 | **Verified Existing Behavior** #87 synthetic H/LoD/CRS results; current Standardizer4979/H and Adapter v0.1-only | Evidence links above; does not imply new route implemented or historical source identity resolved |
| D6 | **Deferred** mixed LoD, split components, BuildingPart/xlink and broader Converter qualification | May be needed for real PLATEAU v5; fail closed rather than asserting first recipe covers it |
| D7 | **Deferred** independent geoid precision, survey accuracy and h→H inverse | Not necessary for identity-H candidate's numeric operation, still needed before any h-route adoption |
| D8 | **Requires Approval** dataset-specific real validation and new Adapter eligibility | No reuse of old111-count/A3 result as acceptance of new bytes; Phase 5 A1–A4 stay OPEN |

Recommended order: approve profile/manifest/legacy policy → implement narrowly with
U/S tests and an explicit owning-spec update → independently review synthetic new
Native/Standard chain → separately authorize real conversion and required geometry
extensions → review dataset/Adapter eligibility → assess Phase 5 Gates separately.
No stage is automatically complete because this design or a PR merges.

## 11. Documentation Impact and validation of this design PR

Only this new review document changes. No Python, fixture, test, Standard,
Current State, acceptance, historical manifest or existing experiment is modified.
No Converter or data transformation is run. Architecture/Standard and interface
amendments remain approval-dependent future work; Current State does not need a
new implementation claim. Related existing tests are run as baseline regression
checks, not as tests of this unimplemented profile. Publication-time commands and
actual counts are recorded in the PR description. Relative links and diff scope
are checked; new acceptance or scientific accuracy is not declared.
