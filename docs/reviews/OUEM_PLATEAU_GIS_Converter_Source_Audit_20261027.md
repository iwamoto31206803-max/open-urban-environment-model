# PLATEAU GIS Converter source audit — 2026-10-27

## 1. Executive Summary

**Status: source-audit findings; adoption remains CONDITIONAL, not an approved conversion route.**
No CityGML conversion, Converter build/install, new data acquisition, OUEM code/test
change or formal acceptance was performed. Phase 5 A1–A4 remain **OPEN**.

The principal finding is an **executed-by-design vertical transformation**, not
just a geoid dependency: for parsed EPSG:6697 input and requested EPSG:4979 output,
`ProjectionTransform::transform_from_jgd2011` swaps latitude/longitude, calls
`Jgd2011ToWgs84::convert`, and replaces every vertex Z with
**source H + embedded GSIGEO2011 geoid height at that longitude/latitude**.
The CLI and ordinary local-file GUI default to 4979. Both audited source pins
contain this branch ([O-PROJ], [O-SHIFT], [O-CLI], [O-GUI-DEFAULT], [D-PROJ]).
This is a static call-path conclusion; the Komae geoid value was **not computed**
and no historical binary/output was replayed.

Consequently, the generic claim “Converter output labelled 4979 retains source
T.P. numbers” is **not true of this configured source path**. Existing OUEM
[Standard Building §3–5](../OUEM_Standard_Building_v0.1.md) preserves Native numeric Z
while interpreting it as T.P. The two meanings cannot be joined automatically.
This is a concrete source-to-OUEM semantic conflict **if that Converter path is
selected**, not proof that every historical accepted artifact used it.

Other adoption-relevant findings:

- Official v0.1.14 hard-codes **4326 in each geometry BLOB header**, while table
  metadata uses the requested EPSG. The audited developer pin instead propagates
  the requested SRS and checks geometry/SRS agreement ([O-GPKG], [O-TABLE], [D-ENCODE]).
- Official GeoPackage exposes only maximum/minimum LoD selections; its manual
  advertises fixed LoDs that the actual option validator rejects. The developer
  pin implements explicit LoD0–4 choices ([O-LOD-OPTIONS], [O-LOD-SETTING], [O-OPTIONS],
  [D-LOD], [D-SETTING]). Do not trust a generic example without checking the pin.
- Official CLI can return success after pipeline errors logged during execution;
  its sink deletes existing output and can commit before checking the producer
  result. The developer pin improves error propagation/finalization, but still
  deletes existing output ([O-EXIT], [O-GPKG-END], [D-EXIT], [D-GPKG], [D-GPKG-END]).
- Byte determinism, actual Windows CLI operation, complete CityGML support and
  historical input/version identity remain **UNVERIFIED**. A version pin alone
  is insufficient for acceptance.

## 2. Audited repositories / commits

OUEM baseline: main **`e57b9aacc88bd9741b0cb924fd8cd394e2a2d552`**.
PR [#82](https://github.com/iwamoto31206803-max/open-urban-environment-model/pull/82)
was confirmed merged; its merge commit equals this baseline. Work uses a new
task branch. Inspection date is **2026-10-27 JST**.

| Identifier | Repository / fixed revision | Scope |
|---|---|---|
| O | Project-PLATEAU/PLATEAU-GIS-Converter, **`e1c8feff7d8ff3e132230d6c21eaed4879e4a235`** | Primary end-to-end audit; observed main and resolved v0.1.14 commit, author date 2026-02-05 UTC |
| D | MIERUNE/plateau-gis-converter, **`ce7766df9788ce391b149c55df16d33082d0bc72`** | Fixed developer comparison; observed main, author date 2026-10-20 UTC; not represented as a released v0.1.19 binary |
| Developer release metadata | v0.1.19 resolves to **`a038cff3b1a98c38ef4753f5f7ca3272a3eb1e37`** | Published 2026-08-26; release assets/commit identification only, not an end-to-end source audit of this revision |

GitHub repository metadata identifies Project-PLATEAU as a fork whose parent/source
is MIERUNE. The official install guide distinguishes the PLATEAU stable release
from the developer release channel ([O-INSTALL]). This does not establish equal
trees, synchronized releases or binary equivalence. The observed latest official
release v0.1.14 was published 2026-02-05; GUI asset filenames still contain 0.1.0,
whereas CLI tarballs contain v0.1.14. Record repository, full commit, asset and
binary hash; the displayed version/filename alone is not sufficient.
See [official release](https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/releases/tag/v0.1.14)
and [developer release](https://github.com/MIERUNE/plateau-gis-converter/releases/tag/v0.1.19).

The audited LICENSE files are MIT (MLIT Japan / MIERUNE copyright); preserve
notices for copied/distributed software ([O-LICENSE]). Dependency/geoid-model
and PLATEAU data rights are separate: this audit does not certify every
third-party redistribution condition. No upstream source was copied into OUEM.

OUEM reference basis:
[acquisition](../experiments/voxcity_canopy_shadow/PHASE5_PLATEAU_ACQUISITION_20261027.md),
[source selection](../experiments/voxcity_canopy_shadow/PHASE5_PLATEAU_SOURCE_SELECTION_20261027.md),
[Building Current State](../status/BUILDING_CURRENT_STATE.md),
[vertical diagnosis](../research/OUEM_Komae_Building_Vertical_Geometry_Diagnosis.md),
[Phase 5 plan](../experiments/voxcity_canopy_shadow/PHASE5_INTEGRATION_PLAN_v0.1_Draft.md)
and [governance](../OUEM_Documentation_Governance_v0.1.md).
Their historical observations/acceptance limits are preserved.

## 3. Architecture and call graph

Workspace members include Tauri app, `nusamai` (CLI and Rust library),
`nusamai-citygml`/macros, `nusamai-plateau`, `nusamai-projection`,
`nusamai-gpkg` and other format crates ([O-ARCH], [O-LIB], [O-DEPS]).
The GUI does **not** shell out to a different CLI conversion engine.

The O GeoPackage path, with actual call names:

```text
CLI main / GUI run_conversion
  → GpkgSinkProvider.create + transformer_options + GpkgSink.make_requirements
  → DataRequirements → transformer::Request
  → NusamaiTransformBuilder.new / transform_schema / build
  → pipeline::run
      CityGmlSource.run
        → CityGmlReader.start_root → toplevel_dispatcher
        → TopLevelCityObject.parse (generated Building parsers)
        → SubTreeReader.collect_geometries → GeometryCollector.into_geometries
      MultiThreadTransformer.run
        → SerialTransform: ProjectionTransform
        → optional statistics/appearance → field-name mapping
        → FilterLodTransform → FlattenTreeTransform
        → GeometricMergedownTransform → attribute serialization
      GpkgSink.run → run_async
        → selected polygon refs → write_indexed_multipolygon
        → GpkgHandler / GpkgTransaction.add_table / insert_feature / commit
```

Evidence: [O-OPTIONS], [O-GUI-RUN], [O-GUI-ENGINE], [O-SOURCE],
[O-BUILDER], [O-PARALLEL], [O-PIPELINE], [O-GPKG], [O-GPKG-END].
Projection runs **before** LoD filtering/flattening. Default requirements use
no appearance, highest LoD, descendant geometry merge/removal and JSON-like
nested attributes ([O-REQUEST]). This is not a model that simply exports each
original XML Building unchanged.

### Dependency and Windows reproducibility boundary

O Cargo.lock resolves `japan-geoid 0.4.4`, `jprect 0.0.4`,
`flatgeom 0.0.2`, `quick-xml 0.38.4` (another dependency also has 0.37.5)
and `sqlx 0.8.6`. D has the same observed versions for these packages.
O manifest ranges and Git dependencies are not exact standalone pins; lockfile
registry checksums and Git revisions provide the resolved graph ([O-DEPS],
[O-GEOID-LOCK], [O-JPR-LOCK], [O-XML-LOCK], [O-SQL-LOCK]).
Future builds should use the exact source plus lockfiles, a recorded Rust target/
toolchain, features/profile and **--locked**; this is a proposal, not a tested build.

README documents Windows 10+ Intel GUI support, Cargo CLI, npm/Tauri GUI
development/build. CI uses `windows-latest` for GUI, mutable Rust stable and
Node LTS, not a completely fixed build image ([O-BUILD], [O-CI]).
Observed O v0.1.14 and developer v0.1.19 release lists contain Windows GUI
EXE/MSI but **no Windows nusamai CLI asset** (CLI assets are macOS ARM/Linux x64).
Do not assert that the GUI installer supplies a usable headless CLI.
Windows CLI compilation/runtime, exact minimum Rust/MSVC/SDK/WebView2 versions,
native dependency requirements and offline build feasibility are **UNKNOWN here**;
no toolchain or Converter was installed. A later Windows build plan must resolve
these prerequisites explicitly, without merging OUEM and GIS Python runtimes.

## 4. CityGML parsing

| Concern | Code-observed behavior / limitation | Evidence |
|---|---|---|
| Dispatch and bounded parsing | Per-file XML reader; top-level cityObjectMember becomes Entity. With appearance disabled, entities are sent onward immediately; files can be parsed in parallel. Appearance mode buffers entities for later binding, so this is not an unlimited-memory guarantee | [O-SOURCE] |
| CRS | Envelope URI is passed into geometry collection and takes precedence over the collector's geometry URI. Only the exact HTTP EPSG URI prefix is recognized there; missing/unrecognized/unparseable URI falls back to 6697. No general CRS/axis discovery should be assumed; mixed CRS/URN forms need explicit tests | [O-COLLECT], [O-CRSREAD] |
| Coordinates | Polygon parser expects exterior/interior LinearRing/posList, reads f64 triples unchanged into a shared indexed vertex store; requires a multiple of 3. It does not infer axes from axisLabels or perform arbitrary dimension/unit conversion | [O-PARSE], [O-COLLECT] |
| Vertices/rings | Identical XYZ bit patterns are deduplicated into indices; exteriors/interiors retained separately. Writer later closes rings. Original vertex indices/count/order are therefore not a universal correspondence key | [O-COLLECT], [O-WKB] |
| Geometry | Generated LoD0/1/2 etc. properties produce GeometryRefs with type/LoD/ranges; Solid/MultiSurface/Surface parsing builds polygon sets. Solid shell topology is not preserved as a solid output contract | [O-LOD-MACRO], [O-GEOMPROP], [O-CRSREAD] |
| Building ID | Building uses the feature macro; required gml:id is inserted into the model and becomes ObjectStereotype::Feature.id, subsequently written as text id. This is distinct from uro:buildingIDAttribute and generated integer fid | [O-MODEL], [O-ID], [O-IDMAP], [O-TABLE] |
| Missing/unsupported encoding | Numeric parse/schema failures return errors; some geometry branches are TODO/unimplemented or skip unsupported forms. The inspected polygon path expects posList, not arbitrary pos/coordinates/XLink encodings. Full XLink, 2D, mixed dimension and nonfinite/topological validation are not established | [O-PARSE], [O-CRSREAD] |

**LoD policy:** O GeoPackage `transformer_options` defaults to `max_lod`.
`FilterLodTransform` recursively finds available LoDs for an entity, retains the
highest/lowest chosen LoD across its object tree, or emits nothing when none is
available ([O-LOD-FILTER]). This is not independent “highest LoD per surface”.

O selection advertises only max/min for this sink. Although the O CLI manual
lists lod0–4, `Selection::set_selected_value` and CLI validation reject those
unavailable values; `TransformerSettings::build` also lacks their cases
([O-LOD-OPTIONS], [O-OPTIONS], [O-LOD-SETTING]). Thus fixed `-t use_lod=lod2`
must **not** be proposed as working on O v0.1.14. D adds those option values and
single-LoD filters ([D-LOD], [D-SETTING]); a fixed LoD can drop features lacking
that LoD. No runtime LoD/count comparison was performed here.

## 5. CRS and Z transformation

Code constants bind 6697 to JGD2011 geographic + vertical height, 4979 to WGS84
geographic 3D, 6677 to plane rectangular IX, and 10170 to IX + vertical height
([O-CRS]). The relevant input is actual 6697 geographic CityGML, not an arbitrary
projected or already-reordered input.

| Requested output, from 6697 | Actual coordinate operation in audited source | Vertical consequence / OUEM boundary |
|---|---|---|
| **4979 (CLI/local GUI default)** | Swap source (latitude, longitude) to GIS (longitude, latitude); call Jgd2011ToWgs84.convert for every stored vertex; set geometry/schema EPSG to output | **h = H + N(lon,lat)**. Embedded GSIGEO2011, not retained T.P. H. No additional XY datum motion occurs inside convert |
| **6697** | Swap first two ordinates; retain Z; set EPSG | No geoid addition for geographic input. Still not byte-for-byte “no transformation”: axis order changes and later geometry processing occurs |
| **6677 / 10170** | Compute projected XY with zone projection; retain existing vertex Z | Candidate source-height-preserving branch, not an approved new OUEM Native interface; 6677 alone is a horizontal CRS, not independent vertical proof |
| Unsupported CRS/direction | Match branches may panic/unimplemented (e.g. audited WGS84-to-JPR paths) | Not a general PROJ-style arbitrary CRS transformation service |

O branches/functions: [O-PROJ]; D geographic branches: [D-PROJ].
`NusamaiTransformBuilder::build` always inserts ProjectionTransform; there is no
audited CLI/GUI switch to remove it while independently selecting a CRS label.
Choosing output 6697 avoids the geoid-addition branch for this input, **not**
all coordinate processing. No general user-selectable vertical grid/offset/epoch
or independently toggled “keep Z under 4979” setting was found in this path.

`Jgd2011ToWgs84::new` loads embedded GSIGEO2011 data; `convert` adds the model
value to H and returns unchanged longitude/latitude ([O-SHIFT]). Its source test
asserts a 39.47387115961899m result for a different fixture location, demonstrating
intended arithmetic **in a test definition**, not an executed test or a Komae
measurement. Interpolation internals, geoid coverage/out-of-range behavior and
model-data redistribution details were not independently audited in japan-geoid.
Do not extrapolate a tested national accuracy or a constant Komae 37m correction.

### Conflict with existing OUEM input semantics

[Native ingest](../../src/ouem/native/building/_plateau_gdal_worker.py) clones
Converter geometry without coordinate transformation. The
[Standardizer](../../src/ouem/standardize/building/_gdal_worker.py) requires
accepted 4979 Native, explicitly transforms the horizontal 4326 component and
restores input Z, while the contract declares those numbers T.P.
Those safeguards preserve numbers **after Converter**, not their earlier meaning.

For the audited default Converter route, ellipsoidal h would remain ellipsoidal
numerically downstream while being interpreted as T.P. **Stop this connection
until source/output correspondence and the interface decision are reviewed.**
Neither relabelling that result nor subtracting approximately 37m is authorized.
Conversely, genuine 6697 output cannot simply be passed as accepted 4979:
the current Standardizer requires 4979. A future profile/interface change or
explicitly documented datum operation requires separate approval and tests.
This audit reports the conflict; it does not edit or retroactively invalidate
existing Standard/Acceptance records.

## 6. GeoPackage serialization

O `GpkgSink::run_async` collects Solid/Surface/Triangle polygon ranges and writes
**MultiPolygonZ** (WKB 1006, children PolygonZ 1003) with f64 XYZ. It does not
perform another geoid shift in the serializer; it writes the already transformed
vertex buffer. Rings are closed by the writer. This stores surface polygons,
not an accepted solid/PolyhedralSurface reconstruction ([O-GPKG], [O-WKB]).

| Issue | O finding | D comparison / consequence |
|---|---|---|
| SRS coherence | write_indexed_multipolygon receives literal **4326**; gpkg_contents/gpkg_geometry_columns use schema EPSG; gpkg_spatial_ref_sys includes formal 4979/6697 definitions | D encode_feature_geometry checks geometry EPSG equals requested SRS and writes that SRS into BLOB; table metadata also receives it. Code-level O discrepancy is established; actual consumer interpretation is UNVERIFIED ([O-GPKG], [O-TABLE], [O-SRS], [D-ENCODE], [D-TABLE]) |
| Feature identity | Text id from source Object ID; integer fid autoincrements, id is NOT NULL but not UNIQUE | Duplicate-ID detection must be an independent OUEM check, not inferred from fid or table success ([O-TABLE]) |
| Surface/feature grouping | Flatten all except thematic surfaces, then merge remaining descendant geometry into emitted parent; BuildingParts/other flattened features may be separate records/tables. Typed tables derive from object type | D adds split_components default false; true emits components separately before merging, with parent linkage. No boolean equivalence to “one original Building, one row” ([O-FLATTEN], [O-MERGE], [O-GPKG-END], [D-GPKG-END]) |
| Empty/unsupported | Empty polygon set is skipped; O Curve/Point sink branches unimplemented. Serialization error check has TODO rather than propagating it; object stereotype warns | D supports more geometry types with range checks, errors on mixed populated types and SRS mismatch, skips empty geometry. Neither path constitutes complete geometry validity/repair ([O-GPKG], [D-ENCODE]) |
| Overwrite / partial output | Existing file removed before work. WAL database initialized; transaction commits before producer status is checked; cancellation is accepted in that final producer match | D still deletes existing output, awaits producer success before commit and calls finalize to make a self-contained file. Neither is a safe no-overwrite OUEM acquisition/publication wrapper ([O-GPKG], [O-GPKG-END], [O-WAL], [D-GPKG], [D-GPKG-END]) |
| Determinism | Parallel file/feature processing, HashSet geometry-ref merge, auto fid and time-dependent last_change mean stable byte order/hash is not promised | Compare normalized ID/LoD/geometry semantics separately from file bytes; repeat-run results are UNVERIFIED ([O-SOURCE], [O-PARALLEL], [O-MERGE], [O-TABLE], [O-SQL]) |

Output does not inherently retain all original per-face semantics, original ring/
vertex order or selected-LoD provenance. Output ID, face/part grouping and lost/
skipped geometry counts need a correspondence ledger; do not assume a nullable
OUEM source_lod field proves how max_lod was selected.

## 7. CLI / GUI comparison

| Topic | Source evidence and assessment |
|---|---|
| Shared engine | CLI and Tauri run_conversion construct source/requirements/NusamaiTransformBuilder/MultiThreadTransformer and call the same pipeline and gpkg sink; same pin/options should share numeric processing, but byte equality has not been demonstrated ([O-EXIT], [O-GUI-ENGINE]) |
| GUI defaults | Local-file page starts gpkg + EPSG4979; SettingSelector defaults/fallback to4979 or the first supported option. UI labels explicitly distinguish ellipsoidal4979 from6697 height. Backend receives epsg, not a fixed T.P. bypass ([O-GUI-DEFAULT], [O-GUI-SELECT], [O-GUI-CRS], [O-GUI-RUN]) |
| CLI configuration | Input globs, --sink, --output, --epsg (u16; default4979), --rules, --schema, -t transformer, -o sink, -i source options. Actual provider whitelist applies; no-input is failure. A flag's presence does not prove arbitrary CRS/LoD support ([O-CLI], [O-OPTIONS]) |
| Unattended operation | Public nusamai CLI exists; no GUI interaction needed by its main. Windows executable availability/build and a verified headless run remain open |
| O errors/logs | Early option/input errors return failure; pipeline logs via RUST_LOG/Feedback. After run(), main returns SUCCESS even when run logs a worker panic/cancellation. Pipeline stage errors are delivered to Feedback and cancel execution, not returned as an ordinary Result by run ([O-EXIT], [O-PIPELINE]) |
| GUI errors | Backend log watcher emits conversion-log and records a first error, joins workers, checks cancellation and returns Err. This differs from O CLI exit handling; not an independent output validation ([O-GUI-ENGINE]) |
| D CLI errors | run returns Result from first reported pipeline error/worker join and main maps it to FAILURE. Cancellation/edge cases still require tests; do not transfer this behavior to O or an unaudited release ([D-EXIT]) |

The GUI map/ZIP selectors and their download convenience flows are not authorized
acquisition replacements here; this audit focuses on local CityGML → GeoPackage.
No GUI session, executable help or CLI output was run.

## 8. Historical vertical discrepancy hypotheses

| Hypothesis | What code supports / does not establish | Remaining decisive evidence |
|---|---|---|
| H1: intentional vertical conversion | **Supported mechanism** for audited 6697→4979: h=H+N is directly called. Strong candidate explanation; not proof the historical tool/version/settings used it | Identify historical binary/hash/commit/settings and source bytes; compare same feature/LoD/surface/vertex and position-specific expected N |
| H2: Z retained but CRS meaning/label differs | For audited default path, “only relabelled, Z unchanged” is contradicted by arithmetic. Separately, O BLOB4326 vs table EPSG is a confirmed metadata mismatch; OUEM's T.P. interpretation of numeric4979 output is a conditional semantic conflict | Inspect actual BLOB header, table SRS/WKT and decoded coordinates in historical/new outputs; distinguish these different mismatches |
| H3: LoD/geometry comparison changed | Supported possibility: entity-level LoD selection, ring closure, vertex deduplication, flatten/merge and output grouping alter comparison sets | Compare same selected LoD and source surfaces, not a single vertex against all-surface extrema or two vertex indices |
| H4: downstream OUEM caused difference | Inspected Native clone and Standard XY-only/restore-Z do not intentionally introduce a geoid shift. Adapter uses absolute maximum Z minus model ground; it can carry an upstream error. No complete old-file trace establishes absence of other issues | Frozen Converter/Native/Standard/Adapter bytes, all-stage corresponding XYZ and manifests, actual ground and selected IDs |
| H5: input/version/conditions differ | Still plausible; PR#82's same historical-looking ID/count is not original-file identity. Different source vintage/release/LoD/Converter version remains unresolved | Recover old source ZIP/GML hashes, binary, settings and full accepted ID/surface set |

PR#82 records the 2025 mesh65 diagnostic target's LoD2 range
24.441737..28.842700m and measuredHeight4.4m. Those source observations do not
reproduce reported old Standard z_min≈61.70m or prove a matched shift.
**Historical root cause remains UNRESOLVED.** Do not apply a constant correction,
substitute measuredHeight or alter past expectations/records.

## 9. OUEM integration options (proposal, no selection ratified)

| Option | Transparency / reproducibility / vertical control | IDs/LoD, Windows, maintenance and national scope |
|---|---|---|
| A — manual GUI | Same inspectable engine, but operator state/options harder to reproduce. Must pin binary/hash and export/capture every setting; default4979 changes Z | Existing workflow, Windows GUI assets available. ID/LoD/grouping depends on exact pin. Low initial effort, high repeated audit burden; no universal national acceptance |
| B — pinned public CLI | Most direct candidate for a machine-recorded invocation; explicit CRS/LoD/settings and independent receipt. Does not itself solve the vertical contract or O defects | Investigate a pin with verified SRS/error/LoD behavior, plus Windows build/runtime. Moderate wrapper/test burden; potentially reusable nationally with source-profile and error/coverage tests |
| C — public Rust crates | Exposed source/pipeline/sink/transformer modules allow a separate Rust harness, not direct Python import. Can construct reviewed requirements, but removing/replacing projection would create a new maintained route | Version0.1/internal APIs and workspace path dependencies imply coupling. Rust bridge/IPC, Windows toolchain, licenses/lockfiles and new tests needed. Higher maintenance; not assumed a stable SDK |
| D — narrow OUEM implementation | Maximum explicit control over selected supported encodings/XY/Z, but must independently implement and validate IDs, parts, rings, references, schemas and error behavior | Highest new maintenance/contract burden; a small Komae subset is not a nationwide reader. Data/software dependency rights remain; no justification to duplicate broadly before B/C evaluation |

**Investigation recommendation:** evaluate B first after approving the required
source-height/Native-interface decision, with A retained for controlled comparison.
This is a test priority, **not adoption of a particular release or new contract**.
Do not choose O defaults merely because past instructions used a GUI.
D is not a “minimal” safe nationwide substitute without substantial validation.
MIT applies to audited project code, not automatically to all dependencies/data.
Rust library reachability is supported by [O-LIB], [O-BUILDER], [O-DEPS];
binary/API longevity and maintenance estimates are recommendations.

## 10. Verification plan (future, not executed)

Use a new immutable run and separately authorize build/install/conversion.
Pin source commit/lockfile/build environment and actual executable SHA-256;
record tool output, settings, environment, input GML/companion hashes, stdout/
stderr/exit and every output/sidecar hash. Never overwrite old data. Stage output
in a new private directory; verify it independently before any Native registration.

1. **Input identity / scope:** reuse exact PR#82 2025 API ZIP and selected GML
   hashes. Start with controlled fixtures, then primary53393456 and neighbor53393466;
   keep historical53393465 separate. Whole crossing geometries, selected IDs and
   omitted/source coverage must be explicit;32m halo remains unproved.
2. **Axes:** synthetic unequal latitude/longitude and Z, source6697 URI and
   actual source axis order. Independently compare numeric XY, projected6677
   control coordinates and output units. Test absent/URN/mixed CRS and dimension;
   do not accept silent fallback as verified input semantics.
3. **Correspondence:** retain full gml:id, LoD, BuildingPart/parent and
   roof/ground surface/ring keys. Match XY/rings with declared tolerances and
   preserved closure/multiplicity rules; do not pair by index after dedup/merge.
4. **Vertical branches:** separately test requested4979 (expect location-specific
   H+N from independently verified model),6697 (expect preserved H plus axis
   swap), and any proposed projected output. Check same roof/bottom vertices,
   not only minima/maxima. Define numeric tolerances before observing results;
   sample target and several low/high/source-invalid cases. No guessed offset.
5. **GeoPackage contract:** inspect raw geometry BLOB header SRS, WKB Z/type,
   gpkg_contents, gpkg_geometry_columns and gpkg_spatial_ref_sys/WKT. Compare
   formal CRS semantics, actual XYZ and source declaration. Verify all headers
   and tables agree; a reader reporting one layer EPSG is insufficient.
6. **LoD/ID/grouping:** compare selected-LoD policy against actual per-feature
   availability; count missing-LoD drops, empty/unsupported geometry, part/surface
   splitting, duplicate/missing IDs and null attributes. Compare max_lod and an
   actually supported fixed-LoD route; account for every selected source object.
7. **Failure/publication:** invalid XML/posList, nonfinite/out-of-range coordinates,
   unsupported CRS/references, missing output directory, existing target, disk
   write failure and cancellation. Require diagnostic failure plus no published
   completed artifact; CLI exit alone is not acceptance.
8. **Determinism:** repeat same pinned invocation, input order and controlled
   concurrency. Compare file hashes, then ID-sorted normalized geometry/attribute
   digests, Z correspondence and counts. Investigate fid/ring/ref order,
   timestamps and WAL finalization when bytes differ; never force expected hashes.
9. **Downstream boundary:** only after a separate approved semantics decision,
   verify Converter→Native→Standard matched XYZ/IDs and eventual ground-relative
   Adapter heights. Retained numeric Z is not evidence that its datum is correct.
   Keep historical reproduction distinct from a new accepted input profile.

No step above was executed by this audit; no acceptance threshold or new Standard
is established by this proposed matrix.

## 11. Open questions and next actions

| Priority / owner | Required next action / limit |
|---|---|
| P0 — independent design review | Decide how a source-H-preserving Converter result can legally enter OUEM's existing 4979-labelled/T.P. Native boundary. No automatic relabel, constant offset or silent contract change |
| P0 — operator/historical evidence | Recover old Converter executable/version/hash, chosen CRS/LoD, original GML and corresponding GeoPackages. H1 mechanism is known; historical causation is not |
| P1 — separately authorized verification task | Choose one exact candidate commit/binary, resolve Windows CLI availability/build prerequisites and run synthetic correspondence/SRS/failure tests before real conversion |
| P1 — source/version review | Check whether selected release actually contains developer fixes; developer main findings are not transferred to v0.1.19 or official v0.1.14 |
| P1 — dependency review | Verify embedded geoid interpolation/coverage/outside behavior, build lock graph and model/dependency redistribution notices without treating model availability as accuracy proof |
| P2 — later authorized real run | Perform §10 on PR#82 source bytes, including adjacent mesh and target roof/base points; then review Native/Standard implications independently |
| Deferred | National schemas/references/epochs/coverage support, exact historical111-building equivalence, complete geometry validity, independent survey accuracy and Phase5 combined scene |

Adoption is conditional on these boundaries; current Phase5 A1–A4 are unchanged
and OPEN. No Building Z correction, new Standard, input transformation,
implementation migration or Gate closure is authorized by this document.

## 12. Evidence references and validation

O/D links below use **full immutable commit SHAs**, repository paths and inclusive
source line ranges. Paths/functions in the tables are static code observations.
Release facts were read from GitHub release/commit metadata on the inspection
date, not inferred from a mutable target_commitish field. The tags collection
endpoint was unavailable through the connector; named release tags were resolved
through their commit endpoints instead. This limitation did not prevent either
source pin or observed release commit from being identified.

Public code/metadata was read through GitHub tools, without cloning/copying audited
code into OUEM, downloading binaries or touching existing Raw/source outputs.
O was traced end to end; D comparison concentrates on relevant changed projection,
parser/LoD, GeoPackage and CLI/GUI paths, not every upstream format.
External dependency internals and release-binary equivalence remain UNKNOWN.

Validation for this documentation-only change: source evidence line ranges and
fixed commit URLs checked against fetched source; local Markdown references and
Git scope checked. No upstream/OUEM build or Python/Rust tests were run, and no
new experiment or acceptance is claimed.

**Documentation Impact:** Verification adds this source audit and prospective
validation plan only. Architecture/Standard and Implementation/Interface are
unchanged. Current State, prior diagnoses, Acceptance Records and Phase5 Gate
are intentionally preserved under the task constraint; a later approved interface
decision must update its owning documents. Draft PR for independent review;
no merge.

### Fixed source references

[O-ARCH]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/Cargo.toml#L1-L21
[O-LIB]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai/src/lib.rs#L1-L23
[O-DEPS]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai/Cargo.toml#L6-L65
[O-GEOID-LOCK]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/Cargo.lock#L3610-L3620
[O-JPR-LOCK]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/Cargo.lock#L3675-L3682
[O-XML-LOCK]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/Cargo.lock#L5616-L5622
[O-SQL-LOCK]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/Cargo.lock#L7037-L7043
[O-LICENSE]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/LICENSE#L1-L11
[O-INSTALL]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/docs/manual/install.md#L3-L10
[O-BUILD]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/README.md#L181-L210
[O-CI]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/.github/workflows/release.yml#L1-L117
[O-CLI]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai/src/main.rs#L26-L66
[O-OPTIONS]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai/src/main.rs#L169-L244
[O-EXIT]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai/src/main.rs#L336-L412
[O-SOURCE]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai/src/source/citygml.rs#L59-L155
[O-COLLECT]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai-citygml/src/geometry.rs#L86-L162
[O-PARSE]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai-citygml/src/parser.rs#L824-L947
[O-GEOMPROP]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai-citygml/src/parser.rs#L318-L460
[O-CRSREAD]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai-citygml/src/parser.rs#L507-L600
[O-MODEL]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai-plateau/src/models/building.rs#L1-L57
[O-ID]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai-citygml/macros/src/type_attrs.rs#L127-L148
[O-IDMAP]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai-citygml/macros/src/derive.rs#L228-L245
[O-LOD-MACRO]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai-citygml/macros/src/derive.rs#L125-L179
[O-REQUEST]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai/src/sink/mod.rs#L62-L108
[O-BUILDER]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai/src/transformer/builder.rs#L118-L201
[O-PROJ]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai/src/transformer/transform/projection.rs#L19-L190
[O-SHIFT]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai-projection/src/vshift.rs#L1-L42
[O-CRS]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai-projection/src/crs.rs#L1-L45
[O-LOD-OPTIONS]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai/src/transformer/selection.rs#L67-L111
[O-LOD-SETTING]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai/src/transformer/setting.rs#L77-L135
[O-LOD-FILTER]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai/src/transformer/transform/lods.rs#L31-L139
[O-FLATTEN]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai/src/transformer/transform/flatten.rs#L157-L283
[O-MERGE]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai/src/transformer/transform/geommerge.rs#L18-L67
[O-GPKG]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai/src/sink/gpkg/mod.rs#L90-L205
[O-GPKG-END]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai/src/sink/gpkg/mod.rs#L208-L289
[O-WKB]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai-gpkg/src/geometry.rs#L49-L116
[O-TABLE]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai-gpkg/src/handler.rs#L194-L290
[O-SRS]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai-gpkg/src/sql/srs.sql#L35-L74
[O-SQL]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai-gpkg/src/sql/init.sql#L16-L40
[O-WAL]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai-gpkg/src/handler.rs#L20-L45
[O-GUI-DEFAULT]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/app/src/routes/+page.svelte#L15-L46
[O-GUI-CRS]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/app/src/lib/settings.ts#L1-L44
[O-GUI-SELECT]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/app/src/routes/SettingSelector.svelte#L20-L35
[O-GUI-RUN]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/app/src-tauri/src/main.rs#L350-L424
[O-GUI-ENGINE]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/app/src-tauri/src/main.rs#L490-L584
[O-PIPELINE]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai/src/pipeline/runner.rs#L29-L161
[O-PARALLEL]: https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/blob/e1c8feff7d8ff3e132230d6c21eaed4879e4a235/nusamai/src/transformer/runner.rs#L19-L36
[D-PROJ]: https://github.com/MIERUNE/plateau-gis-converter/blob/ce7766df9788ce391b149c55df16d33082d0bc72/nusamai/src/transformer/transform/projection.rs#L108-L218
[D-GPKG]: https://github.com/MIERUNE/plateau-gis-converter/blob/ce7766df9788ce391b149c55df16d33082d0bc72/nusamai/src/sink/gpkg/mod.rs#L120-L178
[D-GPKG-END]: https://github.com/MIERUNE/plateau-gis-converter/blob/ce7766df9788ce391b149c55df16d33082d0bc72/nusamai/src/sink/gpkg/mod.rs#L253-L305
[D-ENCODE]: https://github.com/MIERUNE/plateau-gis-converter/blob/ce7766df9788ce391b149c55df16d33082d0bc72/nusamai/src/sink/gpkg/geometry.rs#L26-L145
[D-LOD]: https://github.com/MIERUNE/plateau-gis-converter/blob/ce7766df9788ce391b149c55df16d33082d0bc72/nusamai/src/transformer/selection.rs#L67-L79
[D-SETTING]: https://github.com/MIERUNE/plateau-gis-converter/blob/ce7766df9788ce391b149c55df16d33082d0bc72/nusamai/src/transformer/setting.rs#L105-L139
[D-EXIT]: https://github.com/MIERUNE/plateau-gis-converter/blob/ce7766df9788ce391b149c55df16d33082d0bc72/nusamai/src/main.rs#L353-L457
[D-TABLE]: https://github.com/MIERUNE/plateau-gis-converter/blob/ce7766df9788ce391b149c55df16d33082d0bc72/nusamai-gpkg/src/handler.rs#L299-L360
