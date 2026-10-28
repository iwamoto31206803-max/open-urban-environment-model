# Source-H Native Building ingestion (Step 2)

Status: **Experimental, not an accepted data path**, 2026-10-28.
Phase 5 A1–A4 remain OPEN. No Standardizer or VoxCity Adapter integration.

Baseline main `6899cd72549617ac6dc79f6b1330f469d8f83f81` includes merged PR #89. This implements a bounded
Converter-to-Native processing step under the candidate
`ouem-native-building/plateau-source-h/v0.1` profile. It does not register that
profile, complete #88's eligibility gates, amend a formal Standard, or reclassify
historical 4979 artifacts.

References: [#88 design](reviews/OUEM_Source_H_Native_Building_Profile_Design_20261027.md),
[#84 CRS review](reviews/OUEM_Building_CRS_Vertical_Datum_Design_Review_20261027.md),
[#87 executed Converter checks](experiments/plateau_converter/CLI_SYNTHETIC_EXECUTION_20261027.md),
[Step 1 API](Source_H_Building_Provenance_Foundation_v0.1.md) and
[Standard Building](OUEM_Standard_Building_v0.1.md).

## API and record lifecycle

```python
from ouem.native.building.source_h import ingest_source_h
from ouem.native.building.provenance import validate_source_h_inputs

# plan is a NEW Python dict using the Step 1 foundation view, with the
# unmaterialized native artifact below. It is not an edited historical manifest.
preflight = validate_source_h_inputs(plan, artifact_root=artifact_root)
result = ingest_source_h(plan, artifact_root=artifact_root)
```

This is a Python API; there is no new command-line importer or automatic
translation of historical JSON. The complete synthetic plan factory in
[tests](../tests/test_source_h_ingestion.py) demonstrates all record fields.
Do not interpret its placeholder CLI/source-evidence bytes as a qualified build
or scientific evidence. Actual execution/binary qualification remains unverified.

All **input** artifacts have relative path, exact size_bytes/SHA-256 and role
as in Step 1. Select the Converter layer explicitly in its artifact reference.
The Native artifact is a **plan**, with exactly these required fields, no invented
size/hash and no existing output:

```json
{
  "role": "native_gpkg",
  "path": "new-native-run/native.gpkg",
  "layer": "bldg:Building"
}
```

`native.input_artifact_id` points to the Converter GPKG; `native.output_artifact_id`
points to this planned Native reference. The two ordered ledger edges remain
Raw→Converter→Native with identity_H. All other schema/profile/CRS/LoD declarations
retain Step 1 requirements. `validate_source_h_inputs` adds an explicit preflight
scope; it does not relax `validate_source_h_record`'s completed-record requirements.
Preflight checks all real inputs, excluding the unmaterialized Native ID; an
already populated Native size/hash is rejected rather than reused.

`artifact_root` is caller-selected and explicit; there is no filesystem discovery.
Use a capture bundle or explicit common ancestor to reference Raw and binary
files without modifying/copying them. Paths must resolve inside that root. Native
must use a new child run directory whose parent already exists. An existing run
directory, even empty, is refused. Never aim at historical Accepted locations.
`plan` is deep-copied; no input dictionary or old manifest is updated in place.

The new API preserves the **original layer name** (e.g. `bldg:Building`) and
requires planned Native and Converter layers to agree. SQLite backup copies the
whole container, including other tables/metadata; only the declared building
layer receives this geometry audit. Other content is retained, not independently
accepted. Layer renaming to historical Native `building` is deliberately not
performed: doing so safely would need a separate metadata/spatial-index review.
This is a documented bounded implementation choice, not an assertion that the
new artifact works with the old Standardizer's default layer or 4979-only input.

## Three validation phases (no circular Native dependency)

1. **Before creation:** Step 1 candidate format, every actual input size/hash,
   exact profile/schema and declared references/options/identity_H. No Native
   identity is required before its creation. Then independently audit Converter
   GPKG and supported Raw LoD2 correspondence.
2. **Staging:** reserve a new run directory exclusively; copy via SQLite backup
   into an `.unverified-*` child, close connections, reopen/audit every building,
   compare all input/Native geometry and IDs. Revalidate inputs, calculate actual
   staged Native SHA, and run completed-record validation against those staged
   bytes using a separate in-memory record.
3. **Final bytes:** publish the validated Native file without overwrite, run
   completed-record validation on its actual final path, reopen/recompare geometry,
   and write the candidate Native manifest and receipt. Recheck hashes before
   publishing the manifest as the last completion marker.

Outputs in the fresh directory:

- `native.gpkg`: a new file; original Converter bytes remain unchanged.
- `native.gpkg.manifest.json`: candidate `ouem-plateau-native-ingest/v0.2`, real
  Native size/SHA, original input references and operation declarations, timed
  ingestion QA and scoped foundation result.
- `native.gpkg.receipt.json`: candidate `ouem-plateau-native-receipt/v0.2`, profile,
  Native SHA and completed-manifest SHA. No cache/reuse API consumes it yet.

The manifest references GPKG bytes, the receipt references manifest bytes, and
neither hashes itself. Incoming review/acceptance assertions are not promoted:
the new record explicitly marks review and acceptance NOT_VERIFIED. Original
incoming records are left to the caller unchanged; the API does not edit them.

## Actual GeoPackage and geometry checks

[source_h_geometry.py](../src/ouem/native/building/source_h_geometry.py) uses
SQLite plus a bounded ISO WKB decoder and the existing PyProj dependency. It
does not import GDAL/OGR, use OSGeo4W or call a Converter executable.

- Read-only/immutable SQLite connection; refuse WAL/SHM/journal sidecars rather
  than inspecting a live database. Require GPKG application ID, integrity check
  and no foreign-key violations. Actual IDs are read as text, not coerced.
- Requested layer must have a feature entry in `gpkg_contents` and one geometry
  column with SRID6697, mandatory Z, no M. Actual BLOB SRIDs must match. Check
  authority/code and parse full WKT against compound EPSG:6697. If a WKT2 extension
  column is present, its definition must also match; no EPSG-label fallback.
- Each BLOB has a valid supported GPKG header and complete ISO WKB. Supported
  actual types: Polygon Z, MultiPolygon Z, and recursively polygon-only
  GeometryCollection Z. Reject lines/points, mixed nonpolygon children, empty/NULL
  geometry, M/EWKB/unsupported encodings, malformed/truncated/trailing bytes.
- Require `id` and existing `measuredHeight` columns, non-NULL/nonblank unique text
  IDs, every XYZ finite, explicit 3D coordinates and exactly closed rings. No
  negative-elevation or ecological threshold is invented. Geographic-domain
  checks catch gross XY mistakes, not all axis errors.
- Counts per ID include actual type, faces, exterior/interior rings and every
  vertex occurrence (including closure). Input-to-Native nested trees must be
  **exactly equal**, including face/ring/vertex order, all XYZ and duplicate
  multiplicity. Geometry BLOB SHA must also match: no serialization difference
  is currently permitted. The overall SQLite/GPKG file SHA need not equal the
  source after backup, so complete-file identity is separate from geometry identity.

No clipping, reprojection, repair, simplification, feature merge/split, H→h
operation or offset occurs. The SQLite copy preserves source BLOBs and IDs; the
old Native module, its GUI metadata, Standardizer and Adapter are untouched.

## What establishes the bounded LoD2 check

A declaration or a count of ten faces is insufficient to identify arbitrary LoD2.
[source_h_lod2.py](../src/ouem/native/building/source_h_lod2.py) incrementally reads
the referenced Raw members. It supports a deliberately narrow CityGML2 profile:
top-level Building with explicit6697/3D envelope, inline lod2MultiSurface,
MultiSurface/surfaceMember/Polygon, exterior/interior LinearRing and explicit
3D posList. Source latitude/longitude/H is mapped to GIS longitude/latitude/H.
Eligible IDs must match exactly, and all selected polygons/rings/XYZ/multiplicity
must correspond. Raw→Converter matching allows only polygon order and cyclic
ring starts/reversal; **Converter→Native** remains strictly order-preserving.

No-source-LoD2 buildings are explicitly inventoried as excluded, not silently
lost. BuildingPart, xlink, lod2Solid, uninspected selected geometry constructs,
missing/conflicting CRS, duplicate parent IDs, DTD/entities and unsupported
encodings fail closed. It is not a full CityGML schema/solid parser or a claim
that the existing real2025 tile fits this subset. It does not convert Raw data.

Resource guards are implementation budgets, not national Standard requirements:
Raw member ≤256 MiB, WKB BLOB ≤64 MiB, ≤1,000,000 vertices per decoded geometry,
≤100,000 GPKG features, collection nesting ≤32, canonical ring ≤4096
positions before closure. Larger/unsupported input must stop for explicit review;
do not drop geometry or tune budgets to make an unknown mismatch pass.

## Output states, failures and publication

The manifest separates:

| Check | Result on successful bounded ingestion |
|---|---|
| Step 1 foundation format / actual file hashes | PASS (completed Native bytes included) |
| GeoPackage supported structure | PASS |
| Converter→Native all XYZ / IDs / order / BLOB preservation | PASS |
| Supported Raw LoD2 numeric/axis correspondence | PASS |
| Source-H eligibility | NOT_ESTABLISHED |
| Converter build qualification, semantic H accuracy | Not verified by these checks |
| Human review / Formal Acceptance | NOT_VERIFIED |

The Step 1 report's coordinate_geometry_status remains NOT_RUN **for that
foundation validator**; independent Step 2 QA is stored separately under
`validation.ingestion`. No report upgrades the foundation layer itself.
Reading a compound6697 CRS and retaining numeric Raw H do not independently
prove T.P. realization, survey accuracy, ground semantics or a real Converter run.

`SourceHIngestionError.report` carries FAILED plus the foundation issues or a
code/field/reason. Added geometry errors include CRS_INCONSISTENT, IDENTITY_MISMATCH,
GPKG_INVALID/GEOMETRY_INVALID, LOD2_MISMATCH and XYZ_MISMATCH. These are diagnostics,
not a formal state/schema registration. Unknown/legacy profiles still fail via
Step 1; no old4979 fallback is added.

All Windows SQLite handles are explicitly closed: `with connection` commits or
rolls back but does not close a SQLite connection. Only verified files are
published, using no-clobber same-filesystem hard links; unsupported filesystems
or sandbox hard-link restrictions fail closed. Ordinary exceptions remove this
run's published paths and staging, then remove the exclusively created empty
run directory. Tests inject copy, geometry, publish and manifest failure as well
as mutation after Native publication. Existing outputs are never deleted.
If OS cleanup itself fails, report cleanup_errors and never success; do not hide
the failure or recursively remove unrelated/concurrently added files.

This is not a crash-safe transaction across three files. A process/power loss
before the last manifest may leave unmarked files/staging; they are not completed
artifacts and must not be consumed. Input rehashing is point-in-time detection,
not a filesystem lock against later mutation. Independent later consumers must
reverify files/receipt/manifest. COMPLETED is technical execution, not acceptance.

## Tests, limits and next Step

Step 3 adds an [independent experimental horizontal-only Standardizer](Source_H_Standard_Building_v0.1.md)
with candidate v0.2 output; qualification, formal contract/acceptance and Adapter
migration remain separate gates. It does not alter the legacy Standardizer.

Follow-up [actual Converter-output integration smoke test](experiments/plateau_converter/SOURCE_H_NATIVE_INTEGRATION_20261028.md)
passed using PR #87's saved EPSG:6697 output from the **synthetic** two-building
CityGML. This is separate from the 34 synthetic WKB unit cases below, and is not
real PLATEAU data acceptance. No ingestion behavior change was necessary.

[Synthetic tests](../tests/test_source_h_ingestion.py) create actual SQLite GPKGs
and ISO WKB from the committed two-building fixture using an independent test
encoder. They exercise compound CRS/header conflicts, Z/NaN/Inf, IDs, LoD2 face/
hole loss, GeometryCollection, input/output changes, XYZ/order, original-byte
protection, fresh-plan/final-record separation and handled-failure rollback.
They do not execute a real Converter or use OSGeo4W. Placeholder CLI/evidence
artifacts are intentionally unqualified and cannot establish eligibility.

Next Step must review qualification/source evidence, expand any needed real
geometry scope with tests, and explicitly integrate a new Standardizer profile
and manifest dispatch. Existing Standardizer accepts4979 and treats Z as a
historical T.P. claim; it must not be used as an automatic source-H path. Preserve
ID rules and old numerical assertions, amend owning contracts only with approval,
and separately authorize real-data validation and Adapter migration.

Documentation Impact: new independent experimental ingestion/API description,
plus a Step 1 navigation/preflight note. No formal Standard, accepted Native
profile, Current State accepted path, historical receipt/manifest, Converter,
Standardizer or VoxCity Adapter changes. PR validation reports actual test
results separately; no new real-data acceptance or Phase 5 Gate closure.

Validation in the ordinary Windows OUEM venv:

- New Step 2 + Step 1 + existing Native/Standardizer/Adapter/post-CRS repair
  tests: **159 passed** (8.94s); Step 2 contributes **34 synthetic cases**.
- Full `.venv/Scripts/python.exe -m pytest -q -ra`: **726 passed, 5 skipped,
  250 warnings** (176.49s). Existing skips concern Windows symlink privilege;
  warnings are Rasterio affine PendingDeprecationWarning.
- Markdown links and `git diff --check` passed. Initial test failures exposed
  unclosed SQLite connection lifetime on Windows; explicit close fixed them,
  and copy/QA/publication/manifest rollback tests then passed without skips.
