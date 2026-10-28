# Source-H Standard Building: experimental Step 3 implementation

Status: **Experimental implementation / candidate v0.2 manifest**, 2026-10-28.
Not a revised Standard, qualified data path, Formal Acceptance or Phase 5 gate
closure. Baseline main `4602b928dfddd95b9a9ef5b392b5355d76585529` includes merged PR #90; exact baseline and
executed implementation hashes are in the integration evidence below.

The [real Komae source-H experiment](experiments/real_komae_source_h/RESULTS.md)
uses this same Standardizer and Consumer Validator after bounded Raw reference
resolution. It leaves the horizontal-only operation, exact H checks, candidate
schema, source-H eligibility and Phase 5 gates unchanged.

## Compatibility decisions before implementation

Owning sources: [Standard Building v0.1](OUEM_Standard_Building_v0.1.md),
[#88 design](reviews/OUEM_Source_H_Native_Building_Profile_Design_20261027.md),
[#89 foundation](Source_H_Building_Provenance_Foundation_v0.1.md),
[#90 Native ingestion](Source_H_Native_Building_Ingestion_v0.1.md) and its
[actual Converter-output smoke test](experiments/plateau_converter/SOURCE_H_NATIVE_INTEGRATION_20261028.md).

| Boundary | Existing accepted lane (unchanged) | This experimental lane |
|---|---|---|
| Dispatch | Existing `standardize_native_buildings` / CLI | Separate `standardize_source_h`, exact explicit profile; no fallback |
| Input | EPSG:4979 with historical retained-Z claim | EPSG:6697 compound CRS, explicit source-H profile/provenance |
| Layer | Default `building` | Read Native layer from its manifest, including `bldg:Building` |
| Identity | Native `id` → `source_id`; not `gml_id` | Same mapping; nonblank unique ID preserved without normalization |
| Geometry | Existing GDAL worker | Bounded Polygon/MultiPolygon/polygon-only GeometryCollection Z; exact nested order |
| Horizontal operation | Historical EPSG:4326 → 6677 | Explicit **2D EPSG:6668 → 6677** |
| Z | Historical absolute T.P. claim | Source-declared gravity-related **H**, EPSG:6695, metres; exact retention, no independent datum proof |
| Output | `building`, mandatory Standard fields, v0.1 manifest | Same field names/ID rule, `building`, candidate **v0.2** manifest/receipt |
| Adapter | Accepted v0.1 manifest reader | Intentionally unsupported by current Adapter; no whitelist change |

The new representation follows the geometry/metadata intent of Standard §1/§2/§4,
but §3/§5 describe the accepted 4979 lane. This implementation does **not** amend
them or claim new-profile conformance. Generic source-declared H does not by
itself establish surveyed T.P. alignment. A future owning-contract review and
qualified dataset evidence remain necessary. Old Accepted data and the meaning
of their Z values are not retrospectively changed.

## API and CLI

[Step 4B-1 Consumer Validator](Source_H_Standard_Consumer_Validation_v0.1.md)
independently rechecks saved candidate outputs read-only; it does not enable the
VoxCity Adapter or alter this producer's API/behavior.

Implementation: [orchestrator](../src/ouem/standardize/building/source_h.py),
[geometry IO/QA](../src/ouem/standardize/building/source_h_geometry.py).
Uses existing PyProj/Shapely and Python SQLite; no GDAL worker, OSGeo4W,
Converter execution or new dependency. Existing CLI/worker files are untouched.

```python
from ouem.standardize.building.source_h import standardize_source_h

result = standardize_source_h(
    profile="ouem-native-building/plateau-source-h/v0.1",
    native_manifest="native-run/native.gpkg.manifest.json",
    artifact_root="<artifact-root>",
    output="new-standard-run/standard.gpkg",
    study_area_config="<study-area.yaml>",
)
```

```powershell
.venv\Scripts\python.exe -m ouem.standardize.building.source_h --profile ouem-native-building/plateau-source-h/v0.1 --native-manifest <relative-native-manifest> --artifact-root <artifact-root> --output <new-run>/standard.gpkg --study-area <study-area.yaml>
```

Manifest/output locators must be relative and confined to artifact-root; the
study-area file has its own explicit path/hash. Output parent must be a **new**
child directory with an existing parent. No accepted or existing run is reused.
The explicit profile must match exactly; CRS alone never selects the lane.
The argument must also exactly match the profile returned by Native manifest
validation; a mismatch fails with `PROFILE_MISMATCH` before output directory creation.
Legacy/unprofiled/future-version input fails closed. Existing legacy CLI remains
available with its original behavior; this entry point never dispatches to it.

## Input verification and transformation

1. Strict foundation validation checks full format/schema/profile and **all real
   artifact bytes**. Native manifest must be adjacent to its declared Native;
   its candidate v0.2 receipt must bind actual Native and manifest SHA-256,
   COMPLETED and NOT_ESTABLISHED. Duplicate/nonfinite JSON is rejected.
2. Reperform actual Native and Converter GPKG metadata/WKT/BLOB6697/3D/finite-ID
   audits, exact Native↔Converter snapshots and bounded Raw LoD2 correspondence.
   Do not trust persisted PASS declarations. Step 2's unsupported geometry/XML
   limits remain in force. No review claim establishes eligibility here.
3. Transform **every input vertex before AOI exclusion** with
   `Transformer.from_crs(6668, 6677, always_xy=True, allow_ballpark=False,
   only_best=True)`. Call `transform(longitude, latitude, errcheck=True)` with
   **two arguments only**. Build output tuples `(easting, northing, original_H)`.
   No compound/3D pipeline, 4979, geoid model or Z correction is constructed.
4. `always_xy=True` explicitly chooses GIS storage order, distinct from EPSG
   authority axis order: source lon/lat/H, output easting/northing/H. EPSG:6677
   alone is only horizontal. Manifest separately declares:

   | Field | Value |
   |---|---|
   | horizontal_crs | EPSG:6677 |
   | vertical_quantity | gravity_related_height |
   | vertical_crs / vertical_unit | EPSG:6695 / metre |
   | vertical_operation | identity_H |
   | horizontal_operation | EPSG:6668 → EPSG:6677 |
   | source_horizontal_crs / source_compound_crs | EPSG:6668 / EPSG:6697 |

5. Select by 2D intersection with the configured **closed** EPSG:6677 rectangle;
   retain each complete geometry, never clip/repair/merge/split. An XY-only
   GeometryCollection is used for the intersection predicate; the written tree
   preserves its original Polygon/MultiPolygon/GeometryCollection type. Vertical
   faces may be degenerate in XY; this is not a 3D solid-topology acceptance.
   No selected buildings is an explicit failure.

Output fields remain `ouem_id`, `source_id`, `source_dataset`, `source_lod`,
`measured_height`. `source_id` preserves Native `id`; dataset is `PLATEAU CityGML`;
the existing `deterministic_ouem_id` UUIDv5 rule is reused. Existing recognized
LoD field is copied as text or remains NULL; it is **not inferred from the run**.
Contradictory LoD fails. `selected_lod_by_id=2` independently records verified
run selection. Measured height is copied or remains NULL; nonnumeric/nonfinite
values fail. No other provider attributes or thematic surface IDs are invented.

## Write/reopen QA, provenance and publication

Write ISO WKB Z into a fresh GPKG `building` layer with SRID6677; include required
GPKG tables, default SRS rows and the registered `gpkg_crs_wkt` WKT2 extension.
WKT1 is generated consistently alongside exact WKT2. The first implementation
attempt caught WKT1 projection-parameter/axis round-trip differences in strict
CRS equality; preserving WKT2 fixes representation without weakening CRS checks.
Output remains 2D horizontal CRS plus separate vertical metadata, not ellipsoidal h.

Reopen stage and final file using a Shapely/GEOS WKB reader independent of the
Native handwritten decoder/writer; check table/BLOB SRIDs, WKT/extension,
SQLite integrity/foreign keys, required attributes, IDs, geometry types/counts,
faces, exterior/interior rings and **ordered all-vertex correspondence**.

H has **zero tolerance**: compare binary64 bytes, including signed zero, before
and after serialization. XY must exactly equal the generated tree and is also
checked against separately constructed `Proj(EPSG:6677)` from source lon/lat.
The latter uses a separate API path but the same PROJ library/model; it is not
an independent geodetic accuracy test. A pre-existing authored control table in
`tests/fixtures/plateau_converter/expected.json` provides a further fixed oracle.

The computational XY budget is **1e-7 m**: over three times the earlier #87
cross-implementation synthetic residual `3.2272509997710586e-08 m`, tighter than
the earlier 1e-4 m diagnostic budget. It accommodates binary64/projection API
rounding, not survey error or datum mismatch. Current authored-control residual
is reported below. Authored controls sometimes contain `35.630100000000006`
where XML serializes `35.6301`; reference-point identification permits ≤1e-12
degree only, without changing expected values or output H. No error budget is
used to permit missing vertices, structure/order changes or wrong axes.

Candidate `ouem-standard-building-manifest/v0.2` records Native/manifest/receipt
hashes, original source-chain snapshot, output size/hash/layer, study-area config
hash and extent, selected/excluded IDs, LoD evidence, all coordinate operations,
runtime/module hashes, QA and separate eligibility/review/acceptance states.
Candidate `ouem-standard-building-receipt/v0.2` binds Standard and manifest hashes.
These are experimental implementation formats, not registered formal schemas.

All inputs/config/Native records are revalidated before publication and again
before completion. Close database handles; no-clobber hard-link stage→final;
reopen final and verify; publish receipt then **manifest last**. Requires
same-filesystem hard-link support (unsupported environments fail closed).
Ordinary exceptions roll back only owned files/new run directory, with cleanup
errors in structured `SourceHStandardError.report`. This is not a crash-atomic
multi-file transaction; unmarked crash remnants require investigation and are
not completed/accepted artifacts. No implicit retry into an existing directory.

## Tests and actual Converter-derived Native integration

[Tests](../tests/test_source_h_standard.py) use synthetic SQLite/WKB plus the
existing authored fixture; no real CLI/GDAL required. They cover normal
transformation, 2D-only call instrumentation, exact/signed-zero H, pre-existing
XY controls, axis conflicts, holes/collections, IDs/null metadata, wrong
CRS/Z/nonfinite data, hashes/receipts, exact profile dispatch, original file
protection, AOI whole-building selection, input/final-output mutation and
write/QA/publication/completion rollback. Legacy tests stay unchanged.

Actual ordinary Windows validation:

- New suite: **33 synthetic cases**.
- New + foundation/Native/legacy Standardizer/Adapter/post-CRS tests:
  **192 passed in 11.24s**.
- Full `.venv/Scripts/python.exe -m pytest -q -ra`:
  **759 passed, 5 skipped, 250 warnings in 168.75s**. Existing skips are Windows
  symlink privilege; warnings are Rasterio affine PendingDeprecationWarning.
- No new skip/xfail or change to legacy assertions/fixtures.

The separately authorized **actual Converter-derived Native** integration ran
2026-10-28 **12:49:02.800 JST** using PR #90's saved Native. It is still the
**synthetic** two-building CityGML, not real PLATEAU municipality data. A broad
synthetic EPSG:6677 AOI `[-1000000,-1000000,1000000,1000000]` includes both fixture
locations; this is not the Komae study extent or nationwide accuracy validation.

[Compact execution evidence](experiments/plateau_converter/evidence/SOURCE_H_STANDARD_INTEGRATION_20261028.json)
retains exact baseline HEAD/dirty code identities, operations, all hashes and QA.
The implementation was then uncommitted on main baseline `4602b928dfddd95b9a9ef5b392b5355d76585529`; module
hashes identify what ran, rather than claiming execution of a later commit.
Ignored local run: `data/work/source-h-standard/converter-integration-20261028-01/`.
It retains config, execution identity and independent result; GPKG/manifest/
receipt and local artifacts are not committed.

| Artifact | SHA-256 |
|---|---|
| Input Native | `27ce692dadf78462d6b6e2fc28870cbc4ea7caedbf7157013361b1b54b0d0c89` |
| Native manifest | `32918947fb7a84a9ce933f5f3474c5183119d3a613a695b6dc366226c98e1c6c` |
| Native receipt | `1735879b6d37874ffb85aa222f04cd413f80bb23f1316f37f37f1d64a6f13283` |
| Standard GPKG (53,248 bytes) | `f0f8dd826e5055277cb8d39f6f40b67efe3d7e02f19be57a89c392e1994d785c` |
| Standard manifest | `5d68d5441314af3313bb56b9793e22bc86d8f1a6e40ed0ceb4f6a836ddea0559` |
| Standard receipt | `e330d2369634d620ab945e18e66976d76e0702dca33a1a51962cb8b147df53bf` |

Observed: 2 IDs, 20 faces, 24 rings including 4 interior, 120 vertex occurrences,
exact ordered structure and H; Proj-vs-Transformer XY residual **0 m**. Separate
read-only SQLite/Shapely comparison against the unchanged authored controls
found maximum XY component residual **7.130438461899757e-10 m**. Native hash
remained unchanged. GeoPandas independently opened the output as EPSG:6677,
two MultiPolygon Z features, expected IDs, NULL LoD and heights 9.5/14.75.

Reproduce with the CLI above, using the original Native manifest under an
artifact root that also contains its external CLI references (the historical
Windows root was `C:/dev`). Create a **new** run/config and output child. Keep
all input hashes verified; never overwrite the existing run. Timestamps/paths
can change manifest/receipt hashes; numerical/ID/structure equality is distinct
from byte repeatability. Run related pytest as listed in the PR; ordinary CI
does not claim this local integration execution or access its saved GPKGs.

## Limits and Documentation Impact

Source-H eligibility **NOT_ESTABLISHED**, human review and Formal Acceptance
**NOT_VERIFIED** in all successful outputs. Real municipality conversion,
independent H/T.P. measurement validity, complete CityGML schema/solid topology,
Adapter compatibility and mixed-scene scientific accuracy remain unverified.
The Adapter still rejects v0.2. Phase 5 A1–A4 remain OPEN; do not apply a 37 m
offset, relabel h as H or silently migrate historical Accepted artifacts.

Implementation/Interface: this experimental lane and its candidate IO are
documented here. Verification: bounded synthetic/actual-Converter-derived
results linked here; technical success is not qualification. Current State:
minimal navigation to the new experimental lane. Architecture/Standard and
historical Acceptance remain unchanged because no formal contract revision or
new accepted scope is claimed. Next Step requires independent review, real
input qualification and explicit Adapter migration authorization.
