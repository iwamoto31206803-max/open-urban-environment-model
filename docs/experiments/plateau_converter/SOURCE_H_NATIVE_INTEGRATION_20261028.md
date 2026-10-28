# Source-H Native ingestion: actual Converter-output integration smoke test

Status: **Experimental technical PASS**, 2026-10-28. Independent review pending.
No formal Native acceptance, source-H qualification, Standardizer connection or
VoxCity Adapter change. Phase 5 A1–A4 remain OPEN.

## Scope and execution identity

This tests PR #90 Step 2 against the **actual Converter output of the synthetic
CityGML**, not a test-written WKB container and not real municipality data.
The original [PR #87 execution record](CLI_SYNTHETIC_EXECUTION_20261027.md)
remains unchanged. Its original 6697 output was present, so **no Converter
conversion was rerun**. Only safe `--version` was executed (0, `nusamai 0.1.19`).

Native ingestion/independent readback completed at **2026-10-28 12:25:47 JST**
(03:25:47 UTC). Executed OUEM HEAD was
`970c5860aaf14de62fce420883b6ea016c0f0196`. Production ingestion modules matched
that commit; the new integration runner was then uncommitted. Do not describe
the run as executing the later evidence commit. Exact module/runner SHA-256 and
the observed dirty status are retained in the [compact evidence JSON](evidence/SOURCE_H_NATIVE_INTEGRATION_20261028.json).

Ordinary Windows OUEM venv: Python **3.11.9**, SQLite **3.45.1**, Shapely **2.2.0**;
platform `Windows-10-10.0.26300-SP0`. No OSGeo4W or GDAL was used. Publication
ran outside the restricted sandbox because the existing Windows sandbox blocks
hard links; no publication fallback or validation weakening was introduced.

Converter identity checked again:

- Repository `C:/dev/plateau-gis-converter`, HEAD
  `ce7766df9788ce391b149c55df16d33082d0bc72`; `git status --short` empty.
- Package/version `nusamai 0.1.19`; target `x86_64-pc-windows-msvc`, profile
  `release-lto`, existing executable 27,265,024 bytes.
- CLI SHA-256 `0195a11df4fd0ef30dcd5578175035a918c41285b1fcc329f3399f5337326f1b`.
- Original `convert_6697.json` agrees with `execution.json`; stored stdout and
  stderr match the hashes in that receipt. The saved output matches PR #87's
  published hash, and the Raw fixture matches its published input hash.

These checks establish consistency with the historical local execution and
published record; they are not authenticated external attestation of a build.
`split_components=false` is the audited pinned-source default documented in
PR #87, **not** a flag explicitly present in the historical argv. No dummy CLI,
dummy receipt, invented conversion or independent scientific review is used.

## Inputs, outputs and SHA-256

Local run identifier: `data/work/source-h-native/converter-integration-20261028-01/`.
It holds `plan.json`, `identity.json`, `smoke.json` and the new `native/` outputs.
Input locators below are relative to the repository; the CLI is external.

| Artifact | SHA-256 |
|---|---|
| `tests/fixtures/plateau_converter/two_buildings.gml` | `ac2794be68822389f784c3ae896b0343dd4a046edcf46d8ca577418af52081f8` |
| PR #87 local `lod2_epsg6697.gpkg` | `00af24b34f750ef71ead24b02cf7ff395c0ac125e51449888c3a84ab309d0fce` |
| New `native/native.gpkg` | `27ce692dadf78462d6b6e2fc28870cbc4ea7caedbf7157013361b1b54b0d0c89` |
| New `native/native.gpkg.manifest.json` | `32918947fb7a84a9ce933f5f3474c5183119d3a613a695b6dc366226c98e1c6c` |
| New `native/native.gpkg.receipt.json` | `1735879b6d37874ffb85aa222f04cd413f80bb23f1316f37f37f1d64a6f13283` |

Converter GPKG is 98,304 bytes. SQLite backup is not a byte-for-byte file copy:
Native whole-file SHA differs, while both geometry BLOBs and ordered XYZ are
**exactly equal**. No tolerance, coordinate repair or new serialization allowance
was needed. A direct byte comparison found only five changed bytes, at
zero-based offsets 27, 43, 95, 98 and 99 in the first 100-byte SQLite file header;
all bytes from offset 100 onward are identical. Both files are 98,304 bytes.
Native hash matches its final artifact reference and receipt;
the manifest hash matches the receipt. Raw, Converter, CLI and source-evidence
bytes were rehashed after execution and were unchanged.

The plan uses actual size/hash references and `artifact_root=C:/dev` so the
external CLI and repository artifacts share a confined ancestor. That is an
environment-specific execution root, not a mandated data layout. The compact
JSON preserves the exact plan, original historical argv and result hashes;
absolute paths in these receipts are historical locations, not portable setup
instructions. Nothing under `data/work` or the CLI binary is committed.

## Results and independent checks

| Check | Actual result |
|---|---|
| SQLite/GPKG | Readable, application ID/integrity/foreign-key checks PASS |
| Layer / types | `bldg:Building`, `MULTIPOLYGON`, mandatory Z, no M |
| Coordinate metadata | Contents/geometry columns/BLOB SRID 6697; compound WKT equals EPSG:6697 |
| IDs | `synthetic_tokyo`, `synthetic_niigata`, non-NULL and unique; exact preservation |
| Per building | 10 faces, 10 exterior + 2 interior rings, 60 XYZ occurrences including closure |
| Total | 2 buildings, 20 faces, 24 rings (4 interior), 120 XYZ occurrences |
| Raw → Converter | Exact LoD2 coordinates after explicit lat/lon/H → GIS lon/lat/H mapping; no excluded IDs |
| Converter → Native | Exact type, face/ring/vertex order, all XYZ and geometry BLOB bytes |
| Independent check | Shapely/GEOS decoding plus separate fixture-only XML reference agrees; `measuredHeight` 9.5 / 14.75 also preserved |
| Final records | Completed Native manifest and receipt, final format/hash PASS against actual final file |

The [opt-in integration runner](../../../tests/integration/run_source_h_converter_smoke.py)
calls `inspect_geopackage`, `read_lod2`/`compare_lod2` and `ingest_source_h`.
After generation it reopens Native, compares snapshots, revalidates final
provenance and hashes, then independently decodes source and Native through
Shapely and compares against the pre-existing fixture-only XML oracle. Raw
comparison permits cyclic ring starts/reversal and face order; **Native
preservation comparison permits no change in vertex or structural order**.

No incompatibility was observed in the real Converter serialization. **No
production validator/ingestion fix was needed**, and no CRS, H or XYZ condition
was relaxed. Actual metadata/header details, building summaries and per-BLOB
hashes are retained in the compact JSON.

Foundation `coordinate_geometry_status=NOT_RUN` is intentional: the foundation
report is format/hash-only. Separate ingestion and integration QA report the
performed geometry checks; this does not promote foundation eligibility.

## Reproduction and test separation

1. Obtain the exact PR #87 saved artifacts/receipts and verified CLI; verify the
   full hashes above. This runner fails on a missing/different CLI or Converter
   artifact; it never substitutes unit fixtures or another binary. Rebuilding
   or reconverting needs a new execution receipt and review of new byte hashes.
2. Extract `plan` from the compact JSON into a **new local** `plan.json`. Adjust
   input locators to the actual artifact root, keeping actual size/hash. Select
   a fresh, absent Native child directory whose parent exists. Historical argv
   stays identified as historical; do not invent a new execution.
3. Use ordinary OUEM venv Python with installed OUEM and Shapely:

   ```powershell
   .venv\Scripts\python.exe tests/integration/run_source_h_converter_smoke.py --plan <new-run>/plan.json --artifact-root C:/dev --report <new-run>/smoke.json
   ```

   This exact command shape ran with the local run identifier above. Both report
   and Native run directory must be new. The CLI is hashed, **not invoked to
   convert** by this runner. The integration command must be explicitly run;
   ordinary pytest/CI does not collect it and must not count it as a CI PASS.
4. Check report PASS, final manifest/receipt and hashes; retain failures without
   relabelling them successful. Manifest timestamps/paths may differ on a new
   run; do not require historic manifest/receipt byte equality.

The 34 synthetic WKB unit cases remain separate from this **one actual-output
integration execution**. Related pytest results: **159 passed in 6.68s**.
Full `.venv/Scripts/python.exe -m pytest -q -ra`: **726 passed, 5 skipped,
250 warnings in 174.78s**. Existing skips concern Windows symlink privilege;
warnings are Rasterio affine PendingDeprecationWarning. No new skip/xfail was
introduced. Markdown local links, retained artifact hashes, executed production
module hashes against HEAD, and `git diff --check` passed.

## Limits, next Step and Documentation Impact

- H is the **authored synthetic source-declared gravity-related height**. CRS
  agreement and exact Z preservation do not prove measured T.P. accuracy or
  Converter's independent geoid accuracy. No 4979 path or offset is introduced.
- Source-H eligibility **NOT_ESTABLISHED**, human review and formal acceptance
  **NOT_VERIFIED**. This tests a small synthetic LoD2 grouping, not real 2025
  PLATEAU data, BuildingPart/xlink/Solid/full schema/topology or all attributes.
- Original layer name is retained. No Standardizer/Adapter consumption, legacy
  Native modification, Accepted artifact rewrite or gate closure occurs.
- Next: independent review of this compatibility evidence, then separately
  authorized real-input qualification and Step 3 profile-aware Standardizer
  work. This record does not authorize either.

Documentation Impact: additive Verification evidence and a short navigation
link in the experimental Step 2 interface document; reusable opt-in test runner.
Formal Standards, Current State acceptance scope, historical PR #87 record and
production modules are unchanged because no contract/behavior change occurred.
