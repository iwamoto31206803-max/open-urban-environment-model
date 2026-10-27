# GDAL-only PLATEAU CityGML feasibility — 2026-10-27

## 1. Decision and baseline

**Overall: CONDITIONAL** — GDAL can serialize the fixture's already identified
LoD2 polygons correctly, but an additional constrained CityGML extraction/profile
layer would be required. **Direct GML-driver conversion: NO-GO for the required
LoD2 path on this fixture.** No production route or Option B is adopted.

The recommended next default is the **audited PLATEAU GIS Converter Windows
build/CLI verification**, with its missing Rust/MSVC prerequisites addressed
separately. Do not replace the current workflow with the incomplete GDAL route.
A limited XML/GMLAS investigation can continue only if independent review
explicitly chooses that additional mapping/validation maintenance.

Baseline main **`eb4ab7e43c0445cbd1637aa3fdc952d85ce54201`**; PR #85 confirmed
merged. Sources: [Converter audit #83](../../reviews/OUEM_PLATEAU_GIS_Converter_Source_Audit_20261027.md),
[CRS design #84](../../reviews/OUEM_Building_CRS_Vertical_Datum_Design_Review_20261027.md),
[CLI verification #85](CLI_SYNTHETIC_VERIFICATION_20261027.md),
[Standard Building](../../OUEM_Standard_Building_v0.1.md),
[Building Current State](../../status/BUILDING_CURRENT_STATE.md) and
[Documentation Governance](../../OUEM_Documentation_Governance_v0.1.md).

Only the committed synthetic fixture was processed. No Komae2025 source,
existing Converter/Native/Standard dataset or Accepted artifact was converted,
modified or overwritten. Phase 5 A1–A4 remain **OPEN**.

## 2. Environment and runtime separation

| Runtime actually inspected | Observed capabilities |
|---|---|
| OUEM venv, ordinary Windows | Python3.11.9; no osgeo Python bindings. Rasterio1.4.4 embeds GDAL3.10.3, which is **not** the OGR execution runtime |
| Captured approved GIS runtime | Python3.12.15, **GDAL/OGR3.13.3**, GML, GMLAS and GPKG drivers available; Python GDAL bindings work |

The existing ignored snapshot `scripts/work/.runtime/plateau_komae_gis.json`
selected OSGeo4W Python/OGR executables and a **child-process-only environment**.
It was read, not rewritten. OUEM was not installed into GIS Python; no system
package or new GDAL binding was installed. Driver metadata advertises Z support
for GML/GPKG; actual Z results, rather than that advertisement, are below.
Complete metadata remains local in `environment.stdout.log`.

The runtime receipt hashes the snapshot and GIS Python/ogrinfo/ogr2ogr executables.
The reusable script's executed disk SHA-256 was
`ad544ad527b905e430efe39d31d9775c1e7e72e2cce927d059e228869565bb4f`.
It was new/uncommitted code over the baseline at execution; no claim is made
that it was already part of main. A source tag used to explain a setting is
not proof that the installed DLL was built identically from that tag.

## 3. Inputs, commands and isolated execution

Unchanged [two_buildings.gml](../../../tests/fixtures/plateau_converter/two_buildings.gml):
SHA-256 `ac2794be68822389f784c3ae896b0343dd4a046edcf46d8ca577418af52081f8`.
Unchanged [expected.json](../../../tests/fixtures/plateau_converter/expected.json):
SHA-256 `4116bb577fd45c3db025f4d0f6fec0b51fcd079b21069a41287403c5b2583ca1`.
These contain two distinct IDs/locations, six-face LoD1 solids and ten-face
LoD2 roofs/walls/bases per Building, with courtyard interior rings.

The actual subprocess invocation was the captured GIS Python executable followed by:

```text
<repo>/src/ouem/gdal_citygml_feasibility.py
  --repo <repo>
  --output-dir <repo>/data/work/gdal-citygml/final-results-20261027-01
```

The parent OUEM Python passed the snapshot's environment only to that child,
captured raw stdout/stderr and returncode, and recorded argv/cwd, time, code/
runtime/executable hashes. The worker exited **0**, in **0.747s**; that means
the diagnostic completed, **not that its direct-conversion cases passed**.
All output paths were new; existing directories are rejected by the script.

Actual API operations, kept explicit in the
[standalone probe](../../../src/ouem/gdal_citygml_feasibility.py):

- `gdal.OpenEx(..., allowed_drivers=['GML'])` with WRITE_GFS=NO,
  DOWNLOAD_SCHEMA=NO, EXPOSE_GML_ID=YES, GML_ATTRIBUTES_TO_OGR_FIELDS=YES and
  FORCE_SRS_DETECTION=YES. No GFS sidecar was written beside the tracked fixture.
- `gdal.VectorTranslate(..., format='GPKG')`, first default, then compound/all
  geometry reporting, then additionally `geometryType='MULTIPOLYGONZ'`.
  No CRS reprojection or 4979 assignment was requested.
- Explicit `GMLAS:` OpenEx with validation/error options and remote schema
  downloading disabled, using an isolated cache path.
- A fixture-only XML oracle followed by OGR CreateLayer/CreateFeature, storing
  source LoD2 rings as MultiPolygonZ, with GIS-axis mapping under6697.

To reproduce from an ordinary terminal, start an OUEM Python parent, load the
snapshot with `json.loads`, and call `subprocess.run([runtime['python'],
absolute_script, '--repo', absolute_repo, '--output-dir', new_absolute_child],
env=runtime['environment'], capture_output=True, timeout=90)`. Keep stdout,
stderr, argv, exit and hashes in a new local receipt, as in this run.
The worker imports no OUEM package into GIS Python and only permits the exact
fixture SHA; this is not a general conversion CLI.

## 4. Observed direct-GML results

Default OpenEx exposed **one Building layer, two features**, fields
`gml_id`, `measuredHeight`, `measuredHeight_uom` and geometry field `lod1Solid`.
Both source IDs were retained and unique; height attributes9.5/14.75 and unit m
were retained. No part or nested-feature relationship was exercised.

| Case | Actual geometry / source-LoD content | Layer / BLOB CRS | Required-LoD2 result |
|---|---|---|---|
| default | Nonempty 3D PolyhedralSurface, 12 polygons /12 rings /60 vertex occurrences total; all source LoD1 XYZ retained |6668 in table and both BLOBs | **FAIL:** source LoD2 surfaces/courtyards absent; vertical component omitted from CRS |
| compound_all | Same LoD1 geometry; GML_REPORT_COMPD_CS=YES, GML_FETCH_ALL_GEOMETRIES=YES |6697 in table and both BLOBs | **FAIL:** compound CRS fixed, LoD2 still absent |
| forced_multipolygon |3D MultiPolygon, WKB1006; same12 LoD1 polygons |6697 in table and both BLOBs | **FAIL:** changing the container does not recover LoD2 |

The first two output files used non-standard `gpkg_geom_POLYHEDRALSURFACE`
extensions and WKB1015, with explicit GDAL warnings. These surfaces were **not
empty** on the present fixture/runtime. The historical A1 report of empty
PolyhedralSurface from an earlier real-data route is not reproduced, corrected
or disproved by this different fixture/environment.

Source LoD1 tops are18.25/112.625m; required LoD2 tops are19.75/114.875m.
Thus preserved `measuredHeight` alone would mislead a height-only check: geometry
is LoD1 while the authored height attribute describes the taller source estimate.
All copied **LoD1** Z is exact; this is not “all required LoD2 Z preserved”.

Preliminary GFS probing exposed three requested geometry columns for paths
`boundedBy|RoofSurface|lod2MultiSurface`, corresponding GroundSurface and WallSurface,
but all returned null geometry. Its explicit property list also omitted the
unit field. This rules out **that tested template**, not every possible GFS.
No schema/namespace hack or source rewrite was used to force a favorable result.
The preliminary scripts/template/logs are retained locally, not a second interface.

The [GML documentation](https://gdal.org/en/stable/drivers/vector/gml.html)
describes partial CityGML/simple-feature support and explicit geometry-path
configuration. The observed compound-CRS behavior is explained by
[GDAL3.13.3 source, fixed commit, lines1711–1735](https://github.com/OSGeo/gdal/blob/c8b4c45fca87d3e6fbf80e7a7898b8a661ad0edc/ogr/ogrsf_frmts/gml/ogrgmldatasource.cpp#L1711-L1735).
These references explain settings; conclusions above come from executed results.

## 5. GMLAS and invalid-input behavior

GMLAS was present, but opening this fixture failed with:
`Cannot resolve https://schemas.opengis.net/citygml/2.0/cityGMLBase.xsd`.
Remote schema downloads were deliberately disabled; no complete pinned schema
closure was available. Result: **BLOCKED for the schema-driven alternative**,
not proof that GMLAS cannot represent CityGML. Its
[documented schema dependency](https://gdal.org/en/stable/drivers/vector/gmlas.html)
must be addressed before evaluating layer relationships/LoD/CRS behavior.

The first exploratory GMLAS configuration contained an unsupported cache Enabled
element and emitted a warning. The final run used only the supported cache
Directory plus disabled remote downloads; the missing-schema result persisted.
The initial diagnostic was not counted as successful validation.

| Executed negative case | Observed result | Assessment |
|---|---|---|
| Malformed XML `<invalid` | OpenEx rejected the file as unsupported format | PASS for this rejection case only |
| Replace first source10.25 Z token with `invalid` | OpenEx still exposed two features; affected coordinate became0.0 and a non-closed-ring warning was emitted | **FAIL** for fail-closed numeric input validation; no silent acceptance permitted |
| Other input to fixture-only writer | SHA whitelist rejects before extraction (unit tested) | Safety guard for this probe, not a generic CityGML validity policy |

Error receipts distinguish dataset errors from process exit status. A warning,
non-null dataset or child exit0 is insufficient evidence of valid conversion.
Malformed real schemas, BuildingParts, XLinks, mixed CRS/units, LoD variants and
production write/cancellation failures were **not** tested.

## 6. Limited XML→OGR serialization feasibility

The dedicated helper is deliberately **fixture-only**, not an OUEM Native
adapter. It reads inline CityGML2 Building LoD2 Polygon/LinearRing/posList data
from the fixed hash and manually changes source(latitude,longitude,H) to stored
GIS(longitude,latitude,H). OGR then writes the **same** source6697 reference
with explicit traditional-GIS axis mapping. There is no4979 label, geoid
addition/subtraction, height correction, geometry repair or wall deletion.

Both independent writes produced layer `building_lod2`, **2 features**, fields:
integer fid, string `gml_id`, integer `source_lod=2`, real `measuredHeight`.
The helper assigns the fixture's authored expected height to that attribute;
it does not implement arbitrary source attribute mapping. Source unit m is
not exported as a separate attribute; units/experimental H meaning are recorded
in metadata. No assertion of universal attribute preservation is made.

### Geometry, identity and independent readback

- Per Building: **10 polygons,12 rings,60 closed-ring vertex occurrences**;
  total **20/24/120**. All source roof/base/wall polygons and interior rings survive.
- Full source and reread polygon/ring signatures agree, preserving exterior/
  interior roles and multiplicities while normalizing cyclic start/direction.
  Solid topology/oriented-shell validity is **not** thereby proved.
- A separate OUEM-side check used **lxml source parsing + sqlite3 raw BLOB
  decoding + Shapely**, without the GIS worker helpers. All4 feature readbacks
  across the two files matched the source XYZ multiset/counts and expected
  base/top values exactly. Maximum copied-Z error: **0.0m** on these samples.
- Tokyo H range10.25..19.75m; Niigata100.125..114.875m. MeasuredHeight and the
  two IDs match the authored fixture. This verifies synthetic H preservation,
  not independent real T.P. accuracy or a physical ground comparison.

### GeoPackage CRS / binary structure

For both files, gpkg_contents and gpkg_geometry_columns say6697;
geometry_type_name=MULTIPOLYGON, z=1,m=0; every BLOB header says6697 and
WKB type is **1006** (MultiPolygonZ). Readback reports compound6697 and GIS
axis mapping; numeric longitude/latitude/H matches the source oracle.

The srs6697 row has authority EPSG/6697. Its legacy `definition` is `undefined`,
but **`definition_12_063` contains the compound WKT2 with gravity-related vertical
axis**, and `gpkg_crs_wkt_1_1` is registered. The initial independent checker looked
only at legacy WKT and stopped; the corrected check explicitly inspected the
WKT2 extension **without editing the GPKG**. See the
[GDAL GeoPackage WKT extension documentation](https://gdal.org/en/stable/drivers/vector/gpkg.html#dataset-creation-options).
Ignoring this extension would incorrectly classify the observed CRS as absent.
Full GeoPackage conformance validation was not performed.

## 7. Reproducibility and evidence identities

Two identical fixture-writer calls gave **equal normalized geometry/attributes
and equal readback CRS**, but **different file SHA-256**. Actual gpkg_contents
last_change values are respectively2026-10-27T11:25:48.706Z and
2026-10-27T11:25:48.766Z. These observed timestamps explain at least a metadata
byte difference; an exhaustive binary-diff cause analysis was not performed.
Do not claim byte identity, silently force timestamps or alter outputs to match.

| Final local artifact | SHA-256 |
|---|---|
| default.gpkg | `fadd5c81b50d706fea13f8eb4e0ee16519cf76bee6035bd5da570ae6d0a408f2` |
| compound_all.gpkg | `c5253afa9cb786982f3680a005250df13f53bb1292be234d88413ec609008d88` |
| forced_multipolygon.gpkg | `c50ef97fb7a4767aeb6ce993703faa0679ee28fbe650e4f94cbd7852f14ed014` |
| xml_lod2_1.gpkg | `3c182cf17dcc4e0b6029e3185d476a522e420e29cf282c4edf4d3d448962736d` |
| xml_lod2_2.gpkg | `37311c2e62bfd39a564c8f02d813c1dff1855f607f0ed00d891e65cd82abe0dc` |
| results.json | `b074d11bf7c70da2797dba6de3b5435948a128ecf52fb2f326384707046f04b7` |
| independent-verification.json | `f500919a50586df43938277405ec1d58535a95b2a53e2bc356f60ba49603b13a` |

Local roots, not committed:

- `data/work/gdal-citygml/synthetic-20261027-01/`: environment, initial/GFS/GMLAS
  probes and early execution logs, including the superseded cache-config warning.
- `data/work/gdal-citygml/final-results-20261027-01/`: final5 GPKGs, negative
  fixture copies, complete result metadata/coordinates and independent readback.
- `data/work/gdal-citygml/final-execution-20261027-01/`: exact invocation/runtime/
  executable/code identities, stdout/stderr and full pytest logs/receipt.

The original fixture hash was checked unchanged. Existing Runtime/Standard/
Acceptance inputs were not rewritten. Absolute paths in receipts identify this
workstation; repository-relative fixture/script paths are the reproduction inputs.

## 8. Six-condition gate and next minimum work

| Required condition | Direct standard GML route | Limited fixture XML→OGR helper |
|---|---|---|
| Building identity | PASS for2 source IDs; parts NOT RUN | PASS for fixed fixture; all other files rejected |
| Complete required LoD2 | **FAIL**, only LoD1 retained | PASS on fixture20 faces; no generalized LoD/part reader |
| Every required Z | LoD1 exact, **FAIL for requested LoD2** | PASS on fixture120 vertex occurrences |
|6697 + source H meaning | Default drops vertical CRS; compound option retains6697; not a full LoD2 path | PASS for synthetic declared H and axes; no real datum accuracy claim |
| GPKG metadata/geometry agreement | Tables/BLOBs agree, but default6668 differs from source compound meaning; forced MultiPolygon does not restore missing faces | PASS including WKT2 extension for these two files |
| Automated/reproducible/fail-closed path | Commands repeatable, **numeric invalid input accepted** | Repeat semantic equality only; fixed-hash scope is not a production error policy |

No complete GDAL CityGML route satisfies all six conditions as a reusable
Building conversion workflow. Do not upgrade this result to GO solely because
CreateFeature succeeded or the serializer's fixture checks passed.

To pursue a custom route, separately review a constrained CityGML2/PLATEAU source
profile, offline schema closure, LoD/BuildingPart/ID/surface/attribute mapping,
XLink resolution policy, axes/vertical evidence and an explicit reject-on-unknown
policy. Current helper rejects **every nonidentical input**; it must not be
relaxed into a permissive generic parser. Maintenance would include schema/URI
variants, references, shell/part grouping, multiple rings, collisions and exhaustive
loss accounting. That work can exceed a small adapter and is **not implemented**.

**Recommended next step:** return to the selected audited Converter candidate
from #85, provision/identify its Windows build prerequisites, and execute the
synthetic CLI matrix before any real data. The source audit's SRS/LoD/error
requirements still apply. If avoiding Rust remains essential, first review and
obtain the complete offline schema set for a bounded GMLAS feasibility test;
its current BLOCKED result must not be described as a general impossibility.

## 9. Validation and Documentation Impact

- New [portable helper tests](../../../tests/test_gdal_citygml_feasibility.py):
  **5 passed**,0.11s; no GIS runtime or real data used in those unit tests.
- Captured GIS-runtime execution and separate SQLite/Shapely inspection above
  are actual synthetic experiments, distinct from the portable tests.
- Full `.venv/Scripts/python.exe -m pytest -q` in the individually approved
  ordinary Windows environment: **619 passed,5 skipped,250 warnings**,160.07s,
  exit0. Warnings are Rasterio Affine PendingDeprecationWarning; no assertions
  or existing production tests changed to obtain this result.
- New Markdown links, file/hash references, whitespace and Git scope are checked.
  Only this report, the bounded standalone probe and its tests are added.
  No generated GeoPackage, runtime snapshot, new real dataset or local logs enter Git.

Documentation Impact: this adds Experimental verification and its replay helper
only. Standard/Native/Adapter semantics, accepted artifacts, Current State and
historical Acceptance Records remain unchanged. It introduces no production
CityGML reader, formal coordinate profile,37m correction or new acceptance.
Option B is not approved; Phase 5 A1–A4 remain OPEN. Draft PR for independent
review; no merge.
