# Source-H Standard Building Consumer Validator (Step 4B-1)

Status: **Experimental read-only implementation**, 2026-10-28. Candidate
source-H/v0.2 technical validation only; no formal profile/schema acceptance,
Adapter enablement, Terrain fusion or Phase 5 gate closure.

Baseline: main with PR #92 merged, identified in the [integration evidence](experiments/plateau_converter/evidence/SOURCE_H_CONSUMER_INTEGRATION_20261028.json).
Owning sources: [#88 design](reviews/OUEM_Source_H_Native_Building_Profile_Design_20261027.md),
[#89 foundation](Source_H_Building_Provenance_Foundation_v0.1.md),
[#90 Native](Source_H_Native_Building_Ingestion_v0.1.md),
[#91 Standardizer](Source_H_Standard_Building_v0.1.md),
[#92 Adapter audit](reviews/OUEM_Source_H_VoxCity_Adapter_Contract_Audit_20261028.md),
[Standard Building](OUEM_Standard_Building_v0.1.md) and
[Governance](OUEM_Documentation_Governance_v0.1.md).

## API, CLI and the configuration locator boundary

[Validator](../src/ouem/consumers/source_h_standard.py):

```python
from ouem.consumers.source_h_standard import validate_source_h_standard

report = validate_source_h_standard(
    standard_manifest="standard-run/standard.gpkg.manifest.json",
    artifact_root="<artifact-root>",
    expected_profile="ouem-native-building/plateau-source-h/v0.1",
    study_area_config="study-area.yaml",
)
assert report["technical_validation"] == "PASS"
```

```powershell
.venv\Scripts\python.exe -m ouem.consumers.source_h_standard --standard-manifest <relative-manifest> --artifact-root <artifact-root> --expected-profile ouem-native-building/plateau-source-h/v0.1 --study-area-config <relative-config>
```

The function returns a JSON-serializable dict, including failures; no artifact
is written. CLI prints the report and exits0 for technical PASS or2 for FAIL.
Report persistence/redirects are caller actions, not validator writes.

**Necessary API adjustment:** the existing candidate Standard manifest stores
`study_area.config_sha256` but no config locator. The consumer therefore needs
the explicit `study_area_config` keyword. Omission returns FAIL with
`CONFIG_LOCATOR_REQUIRED`; it does not scan directories, invent a locator or
pretend the declared hash alone verifies config bytes. This adds no producer
field or Standardizer behavior. Config bytes/hash/id/6677/extent are checked.

Entry manifest/config arguments may be relative or absolute **inside** the
resolved artifact root. All actual manifest/artifact references must be relative,
without drive/absolute/traversal components and resolve inside that root.
Windows-style traversal/drive paths are rejected on other hosts too. An external
CLI reference needs an appropriately chosen common root, not an escape: the
historical local smoke test used `C:/dev`. Only declared paths are read; no PC-wide
search, download or execution occurs. Historical argv strings/informational
extensions are not treated as executable commands or additional artifact locators.

## Reuse versus independent validation

| Component | Reuse / new responsibility |
|---|---|
| Native foundation | Reuse `validate_source_h_record` for exact source-H profile/schema, declared graph and real artifact sizes/hashes; never infer eligibility from foundation PASS |
| Native geometry/source | Reuse actual read-only `inspect_geopackage`, Converter↔Native `compare_snapshots`, Raw `read_lod2`/`compare_lod2`; rerun them, not stored PASS claims |
| Safe Native SQLite access / counts | Reuse closed-handle `mode=ro&immutable=1`, query-only/trusted-schema-off access and structural counting utility |
| Standard data | **New independent bounded binary reader**, not Standardizer `from_shape`, `map_xy`, writer or `audit_standard`; read actual tables, attributes and every WKB coordinate |
| Coordinate/AOI/ID | **New** projection/reference traversal, ordered XYZ/ring comparison, AOI selection and UUIDv5 computation; no call to Standardizer processing or its geometry QA |
| Strict records / TOCTOU | **New** known-candidate schema/type checks, duplicate/nonfinite JSON rejection, fresh Native source-chain equality, receipt/Standard binding and input watch set |

[Independent geometry module](../src/ouem/consumers/_source_h_geometry.py) uses
`Proj(CRS.from_epsg(6677))` on source lon/lat **two values only**, separate from
producer `Transformer` calls. A `Transformer.from_crs(6668,6677,always_xy=True,
allow_ballpark=False,only_best=True)` instance is constructed only to compare
the recorded operation definition/accuracy; no H or geometry is passed to it.
The oracle paths share PROJ, so this is an independent traversal/reader/API
check, not independently measured geodesy. Unknown operation definitions fail
closed; semantically equivalent future producer/PROJ representations may need
review instead of implicit acceptance.

## Exact records and source chain

- Exact Standard manifest `ouem-standard-building-manifest/v0.2`, explicit
  expected profile equal to manifest and actual Native profile. Unknown,
  legacy4979 and future versions fail; no fallback.
- Known object fields/types are required. Booleans are not accepted as numeric
  counts; missing/unknown fields, duplicate keys, nonfinite JSON and invalid
  statuses fail. Recognized optional `extensions` must be an object and does
  not grant authority or supply additional consumed files.
- Standard `EXPERIMENTAL`/`COMPLETED`, eligibility NOT_ESTABLISHED and review/
  acceptance NOT_VERIFIED must agree. Adjacent Standard receipt must exactly
  bind candidate receipt v0.2/profile/status, actual Standard SHA and manifest SHA.
- Standard file hash/positive integer size/layer, actual Native manifest/receipt
  hashes and adjacent paths are checked. Embedded `source_chain` must equal the
  freshly read Native record with JSON type distinctions preserved.
- Rehash every actual Raw/Converter/Native/CLI/source-evidence artifact. Native
  receipt and Native input path/layer/hash must agree with the real record.
  Recheck completed Native/foundation status and unverified eligibility/review
  boundaries. Reperform actual Native↔Converter and Raw LoD2 correspondence. Persisted Native
  foundation/ingestion QA must also match the fresh reports, including status,
  issue lists, counts and source exclusions; a valid actual file does not excuse
  a contradictory completed record.

Matching hashes/metadata do not authenticate original Converter execution,
publication claims, source declarations or reviewer identities. Producer module
hashes/runtime strings are format-checked records, not a replay or verification
of the historical executable/code. Actual source/geometry correspondence is
recomputed separately. No external qualification is approved.

## Standard GeoPackage, selection and coordinates

Read actual SQLite integrity/foreign keys/application_id, `gpkg_contents`,
`gpkg_geometry_columns`, selected SRS authority/code/WKT1/WKT2 and registered
`gpkg_crs_wkt` extension. Candidate WKT1 must match generated6677 representation;
WKT2 must semantically equal6677. Geometry-column/table/BLOB CRS, Z and M flags
must agree. Contents bounds must equal the actual complete vertex bounds.

Supported subset: ISO Polygon Z, MultiPolygon Z, recursively polygon-only
GeometryCollection Z, bounded nesting/vertices, closed nonempty rings and finite
XYZ. No empty/mixed/2D/M/EWKB/unknown type, trailing bytes or unrecognized BLOB
envelope/extension is silently accepted. Current candidate writer emits no BLOB
envelope; a future encoding needs reviewed support. Bounds:16MiB JSON,64MiB per
BLOB,1,000,000 vertices per BLOB,32 nested levels,100,000 Standard features;
Raw parsing retains Step2's256MiB/member and inline CityGML2 limitations.
These are bounded implementation limits, not a complete GPKG/CityGML certification.

Required `ouem_id`, `source_id`, dataset, geometry must be non-NULL/valid;
source and OUEM IDs unique; dataset exactly `PLATEAU CityGML`; UUIDv5 uses the
unchanged documented v0.1 name/URL namespace. Existing recognized Native LoD
field is copied as text, or NULL; no inference from the run. Contradictory LoD
fails, and `selected_lod_by_id` independently records2 for exactly selected IDs.
Measured height must equal the Native value or remain NULL, never substituted
for source H.

All Native features are independently projected to evaluate the closed 2D AOI
rectangle. Compare actual selected IDs, excluded Native remainder, no duplicates,
input/output counts and config. Then compare each selected complete ordered tree:
type, faces, exterior/interior rings, vertices/order and every XYZ. No clip,
repair, union, cyclic ring normalization or point deletion occurs. Per-vertex H
is compared by packed **binary64 bytes**, including signed zero, with **zero
tolerance**. XY uses **1e-7 m**, following Step3's documented computational
rounding budget; it is not survey accuracy. Shape/order is not normalized to
make a changed result pass. Full3D shell/watertight topology is not established.

Required declarations are checked individually: horizontal6677; vertical quantity
gravity_related_height; vertical6695/metre/identity_H; source horizontal6668 and
compound6697; horizontal operation6668→6677; GIS input lon/lat/H and output
easting/northing/H; `always_xy=True`. H never enters PROJ. No4979, ellipsoidal h,
geoid operation or constant Z correction is introduced. Stored producer QA must
have consistent statuses/types/counts/budgets but does not replace these checks.

## Read-only, TOCTOU and report interpretation

Every consumed file is captured using a regular-file handle, bounded read up
to original size+1, SHA-256, before/after descriptor/path metadata and resolved
locator binding. SQLite sidecars (`-wal`, `-shm`, `-journal`) are refused; files
are opened with read-only immutable URI and handles closed. After geometry/
selection QA, re-resolve and rehash the complete watch set and compare device,
inode, size, modification/creation metadata and content. Same-byte replacement
is detectable via file identity. Growing files do not cause unbounded streaming.

This is **best-effort point-in-time observation**, not a lock, atomic snapshot,
signature or proof against every reversible concurrent mutation. A successful
report cannot guarantee later input identity. A later Adapter must revalidate
at use or bind immutable verified artifacts, including the referenced chain.
It must not treat this dict or the persisted PASS text as an authorization token.

Reports include technical PASS/FAIL, verified profile/schema, artifact locators/
sizes/hashes/watch metadata, selected/excluded IDs, Native/Standard feature and
selected vertex counts, per-building structure, actual XY/H QA, issues with
field/code/reason, validation scope and limitations. On failure some earlier
checks/partial counts may be present; **technical FAIL remains decisive**.
All outcomes retain source-H eligibility NOT_ESTABLISHED, human review and Formal
Acceptance NOT_VERIFIED; Phase5 A1–A4 remain OPEN. Neither Terrain compatibility,
coverage/ground modelling, VoxCity, solar nor scientific accuracy is validated.

## Validation and actual saved-file smoke test

[Tests](../tests/test_source_h_consumer.py) build small synthetic file chains using
existing fixture writers; only test setup generates data. Consumer invocation
is read-only. Tests guard SQLite read-only connections, input bytes/mtime/file
set, no Standardizer/writer/subprocess/VoxCity calls, matching profile/chain,
Polygon/MultiPolygon/nested Collection, holes, nullable attributes, signed-zero
H, AOI exclusions, schema/status/type/receipt/hash/CRS/WKT/BLOB/axis/ID/LoD errors,
closed-ring cyclic reorder, duplicate/nonfinite JSON, traversal, mid-validation
mutation and same-byte file replacement. Geometry corruption tests rebind hashes
so they exercise actual semantic checks rather than only a hash mismatch.

Related run (eight suites including unchanged Native/Standardizer/Adapter tests):
**281 passed in37.99s**; **86 new Consumer cases**. Final full `.venv/Scripts/python.exe -m pytest -q -ra`: **848 passed,
5 skipped, 250 warnings in193.10s**. Existing skips are Windows symlink privilege;
warnings are Rasterio affine PendingDeprecationWarning. No skip/xfail or existing assertion modification is used.
The initial full run had **1 failed, 840 passed, 5 skipped, 250 warnings**
(194.06s): a concurrent documentation edit changed Git state during an existing
Height Envelope fixture, which correctly rejected that mutation. No test or
Height Envelope code was altered; final full validation runs with the repository
worktree/index frozen until pytest exits.

**Explicit saved-file integration: PASS**, 2026-10-28 14:13:37 JST. This is PR #91's
actual Converter-derived **synthetic CityGML** Standard, not municipality data.
No Converter, Standardizer, Adapter, Terrain fusion or engine was executed.
2 features /120 XYZ occurrences; binary64 H and ordered geometry PASS;
XY residual0m; pre/post input watch checks PASS. Original Standard SHA remained
`f0f8dd826e5055277cb8d39f6f40b67efe3d7e02f19be57a89c392e1994d785c`, Native
`27ce692dadf78462d6b6e2fc28870cbc4ea7caedbf7157013361b1b54b0d0c89`.

[Compact evidence](experiments/plateau_converter/evidence/SOURCE_H_CONSUMER_INTEGRATION_20261028.json)
records all11 consumed file identities, actual results, baseline HEAD/dirty-code
hashes and limitations. Execution used then-uncommitted Consumer modules, not
the later evidence commit. Local ignored run
`data/work/source-h-consumer/converter-integration-20261028-03/` retains full report
and code identity. Report persistence was an outer evidence-capture action;
the API wrote nothing. No local GPKG/CLI/source snapshot/large log is committed.

To reproduce, use CLI above with the original Standard manifest and area.yaml,
an artifact root containing every real referenced artifact (historically `C:/dev`)
and verified original hashes. Do not replace absent evidence with dummy files or
claim this integration ran in ordinary CI: CI tests use synthetic fixtures only.

Documentation Impact: new experimental consumer interface/evidence, brief
Standardizer usage and Current State navigation. Existing Standardizer/Adapter
APIs/behavior, formal Standards and historical acceptance records are unchanged.
Next Step requires independent review plus separate datum/coverage/grid/ownership
and use-time binding gates from #92; this validator does not enable an Adapter.
