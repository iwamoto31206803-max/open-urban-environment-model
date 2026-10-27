# Source-H Building provenance foundation (Step 1)

Status: **Experimental implementation boundary**, 2026-10-28. Candidate profile
and schema names are not formally accepted by this implementation. Phase 5
A1–A4 remain OPEN. No Native ingestion, Standardization or Adapter integration
is enabled by these functions.

Baseline: main `155e3db002d67f7f152b810150abab1f45ce65fe`, with #88 merged.
Design: [source-H profile proposal](reviews/OUEM_Source_H_Native_Building_Profile_Design_20261027.md),
[CRS review](reviews/OUEM_Building_CRS_Vertical_Datum_Design_Review_20261027.md),
[Converter synthetic execution](experiments/plateau_converter/CLI_SYNTHETIC_EXECUTION_20261027.md).
[Standard Building](OUEM_Standard_Building_v0.1.md) and all historical records
remain unchanged. A design plan and these foundation checks are not new acceptance.

## API and runtime

[ouem.native.building.provenance](../src/ouem/native/building/provenance.py) uses
only the Python standard library. It imports neither GDAL/OGR nor the Converter,
and executes no subprocess. Existing Native/Standardizer/Adapter entry points
do not import or call it. There is no new CLI or migration writer.

```python
from pathlib import Path
from ouem.native.building.provenance import load_source_h_record

report = load_source_h_record(
    Path("new-run/native-foundation.json"),
    artifact_root=Path("new-run/artifacts"),
)
print(report.to_dict())
# report.foundation_valid means ONLY format and byte checks passed.
# It MUST NOT authorize Standard generation or scene/acceptance eligibility.
```

- `identify_profile(profile) -> str`: exact supported key or
  `ProfileValidationError` with structured `.issue`.
- `validate_source_h_record(record, *, artifact_root, verify_files=True)`:
  validate an already loaded JSON-like dict; return a `ValidationReport`.
- `load_source_h_record(path, *, artifact_root, verify_files=True)`:
  reject duplicate JSON keys, nonfinite constants/overflow and malformed JSON;
  return structured errors for unreadable/invalid records, then validate.
- `verify_files=False` is format-only: no artifact reads, and no file or
  eligibility PASS. The caller supplies the artifact root explicitly; there is
  no automatic repository lookup or selection of an adjacent manifest.

## Input foundation view

This is an explicit **Step 1 view of the candidate Native v0.2 record**, not a
complete schema validator for all #88 QA/review/cache fields. Do not feed a
current v0.1 manifest to it or rename an old manifest. No adapter for the #87
compact evidence JSON is implemented. Richer records will need an explicit
extension/mapper and review; unknown foundation fields are rejected rather than
silently treated as inspected. Full #88 semantic/review requirements are deferred,
not weakened or considered satisfied by this subset.

| Object | Required fields / declaration checks |
|---|---|
| root | `schema="ouem-plateau-native-ingest/v0.2"`, separate `profile="ouem-native-building/plateau-source-h/v0.1"`, and all groups below |
| `artifacts` | Nonempty map from unique nonempty IDs to `{role, path, size_bytes, sha256}`. Geometry references also require nonempty `layer`. SHA is exactly 64 lowercase hex; size is a nonnegative integer (bool is rejected). |
| artifact roles | At least one `raw_citygml`; exactly one each of `converter_cli`, `converter_gpkg`, `native_gpkg`, `source_evidence`. Optional `raw_dependency` and `raw_archive`. Dependency members participate in Converter input references; archive identity is retained but archive membership is not verified. |
| `source_declaration` | `srs_name="http://www.opengis.net/def/crs/EPSG/0/6697"`, `horizontal_epsg=6668`, `vertical_epsg=6695`, `quantity="gravity_related_height"`, `unit="metre"`, `axes=["latitude","longitude","H"]`, `evidence_artifact_id` referencing the evidence artifact |
| `coordinate_contract` | `input_epsg=6697`, same horizontal/vertical/quantity/unit, `storage_axes=["longitude","latitude","H"]` |
| `geometry_selection` | `requested_lod=2`, `split_components=false`; declarations only, no observed geometry claim |
| `converter` | `schema="ouem-building-converter-run/v0.1"`, `repository="https://github.com/MIERUNE/plateau-gis-converter"`, full lowercase40hex `commit`, nonempty `version`, `cli_artifact_id`, `input_artifact_ids`, `output_artifact_id`, `argv`, `resolved_options`, integer`exit_code=0`, `execution_status="COMPLETED"` |
| `converter.resolved_options` | Exactly `sink="gpkg"`, `epsg=6697`, `use_lod="lod2"`, `split_components=false` |
| `converter.argv` | Nonempty string array; explicit input arguments, one `--output`, exactly one `--sink gpkg`, `--epsg 6697`, and `-t use_lod=lod2`. Optional one `-t split_components=false`. Separate or `flag=value` spelling supported. Other flag spellings/options rejected in this bounded view. |
| `native` | `input_artifact_id` must reference the Converter GPKG; `output_artifact_id` must reference Native GPKG |
| `operations` | Exactly the two ordered edges below, not a general workflow DAG |

Root/artifact `extensions` objects are permitted for information only and do not
override contract fields. Optional root `validation`, `eligibility_review`,
`acceptance` payloads are **unverified claims**, not interpreted as successful
checks. Tests deliberately supply false success claims to prove no promotion.
The [unit-test record factory](../tests/test_building_provenance.py) is a complete
small example using deliberately invalid GIS placeholder files; it is not a
Native dataset, a Converter receipt qualification or an accepted manifest.

### Declared operation edges

Every Raw CityGML/dependency ID must appear exactly once in the Converter input
ID list and in the first edge. Unknown/dangling/duplicate/wrong-role references,
reordered/cyclic edges or extra edges fail.

```json
[
  {
    "input_artifact_ids": ["raw"],
    "output_artifact_id": "converter",
    "horizontal_operation": "latitude_longitude_to_gis_longitude_latitude",
    "vertical_operation": "identity_H",
    "offset_m": 0,
    "geoid_model": null
  },
  {
    "input_artifact_ids": ["converter"],
    "output_artifact_id": "native",
    "horizontal_operation": "identity_XY",
    "vertical_operation": "identity_H",
    "offset_m": 0,
    "geoid_model": null
  }
]
```

`raw`, `converter`, `native` here are artifact IDs, not filenames. Claimed H→h,
nonzero offset, a geoid model, 4979 or incompatible quantity/unit declarations
are rejected. This checks the ledger's declared consistency; it cannot establish
that a binary actually executed those operations.

## Byte validation and errors

Artifact locators must be relative to `artifact_root`; absolute paths, parent
traversal, resolved escapes and distinct IDs aliasing the same resolved path are
rejected during file verification. Relocation of the entire artifact tree is
allowed. Actual referenced files must exist and be regular/readable. Streamed
SHA-256 and exact byte count/size are checked on every call; there is no receipt
cache. Reading is bounded by declared size plus one byte, with before/after file
metadata checks for changes. This is a point-in-time check, not a filesystem
lock or a guarantee against changes before a later worker runs. Later Steps
must reverify inputs and operation-time identity. No output is created or modified.

Each issue carries `code`, `field`, `reason` and `artifact_id` where applicable.
Malformed nested fields are reported without treating arbitrary types as valid.

| Code | Meaning in this module |
|---|---|
| `PROFILE_UNSUPPORTED` | Missing/unknown profile/version; no EPSG-based inference |
| `SCHEMA_UNSUPPORTED` | Unknown Native/Converter schema version or profile used as schema |
| `PROVENANCE_MISSING` | Required group/reference/file missing or inaccessible; unsafe path/root/alias |
| `PROVENANCE_INVALID` | Wrong types/options/roles/edge relationships, malformed/duplicate/nonfinite JSON, unknown fields |
| `HASH_MISMATCH` | Actual size/SHA differs or file identity metadata changes during reading |
| `VERTICAL_SEMANTICS_CONFLICT` | Conflicting CRS/quantity/unit, h/H mixing, nonidentity vertical operation or offset/model |
| `AXIS_MISMATCH` | Incompatible declared source/storage axes |
| `LEGACY_NOT_REGISTERED` | Explicit historical profile requested; registration/replay is not implemented in Step 1 |

No EPSG4979 fallback or registration inferred from a filename/extension is offered.
The explicit legacy profile is rejected even when an untrusted payload claims
registration; actual replay registration is a later reviewed API.

## Report states and strict limits

| Report field | Meaning / possible result here |
|---|---|
| `format_status` | PASS/FAIL for this foundation view only; NOT full manifest/semantic validation |
| `file_hash_status` | PASS/FAIL; NOT_RUN when disabled or format failed |
| `checked_artifact_ids` | Only files whose current bytes passed size/SHA checks |
| `foundation_valid` | True only when both preceding checks PASS; never eligibility |
| `coordinate_geometry_status` | Always NOT_RUN |
| `converter_qualification_status` | Always NOT_VERIFIED |
| `human_review_status` / `formal_acceptance_status` | Always NOT_VERIFIED |
| `eligibility` | Always NOT_ESTABLISHED |
| `validation_scope` | `source-h-foundation/v0.1` |

Commit syntax, declared invocation conditions and actual CLI file SHA are checked;
the commit is **not** matched to an allowlisted qualified build, nor is a binary's
relationship to source, options/defaults or compiler independently established.
The CLI SHA need not be #87's qualified binary for *foundation* success; it must
match its referenced bytes. #88's recipe qualification is a later mandatory gate.
Likewise, argv path/glob resolution is not authenticated against an executed
process. Role-ID edges prove only declared referential consistency.

No XML/GPKG parsing, WKT/BLOB/axis measurement, ID/LoD/ring/vertex correspondence,
source-evidence scientific validation, review record-set digest/authenticity or
acceptance approval is implemented. Fake GPKG bytes can pass these two layers:
that is intentionally tested and is why downstream processing is not authorized.
No content-derived source-H eligibility is asserted from a label or hash.

## Scope and next Steps

This implements #88's format/identity foundation subset; it does not change its
required semantic or review gates. The artifact roles and bounded two-edge view
make the API concrete without registering a complete new schema. Current v0.1
manifests are neither read as new records nor rewritten. No change to Standard,
ID generation, legacy GUI metadata, GIS runtime or any existing processing route.

Before Step 2/3 integration: review the fuller schema/wire mapping, qualified
Converter receipt/defaults and byte-to-source identity, immutable record graph,
full CRS/geometry/all-vertex correspondence reports and review binding. Implement
independent semantic checks and explicitly authorized legacy handling. Preserve
all #88 fail-closed gates and test actual GIS subprocess IO separately from these
pure-Python tests. No real CityGML conversion was performed here.

Documentation Impact: this document owns the new independent API and its limits.
Existing formal Standards/acceptance/history remain unchanged. Building Current
State's processing route is unchanged; this helper is not an integrated Native
or Standard implementation. Tests and PR description record what ran, not a new
acceptance result.

## Validation of this implementation

- New pure-Python tests: `tests/test_building_provenance.py` — **73 passed**.
  All artifacts are small placeholder bytes, with no valid GIS/conversion claim.
- New + existing Native/Standardizer/Adapter, post-CRS repair, vertical diagnosis
  and Converter-probe/GDAL-feasibility unit tests — **161 passed**.
- Ordinary Windows OUEM venv, `.venv/Scripts/python.exe -m pytest -q` —
  **692 passed, 5 skipped, 250 warnings**, 174.50s. Warnings are existing Rasterio
  `PendingDeprecationWarning` for affine multiplication. Skips are not acceptance.
- The sandbox full-suite attempt was interrupted after failures/errors. A bounded
  `pytest -x -q` diagnostic yielded **1 failed, 115 passed, 7 warnings**: an existing
  CHM test's `os.link()` raised WinError5 in sandbox temporary storage. The
  individually approved ordinary-environment full run above passed; no existing
  hard-link implementation or test was changed to conceal the restriction.
- Markdown links, diff scope and `git diff --check` were checked. No real input
  was processed and no profile/semantic/acceptance Gate was closed.
