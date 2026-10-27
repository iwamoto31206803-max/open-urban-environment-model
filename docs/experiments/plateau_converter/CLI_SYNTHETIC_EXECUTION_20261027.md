# PLATEAU Converter Windows CLI: synthetic execution evidence — 2026-10-27

Status: **Experimental technical verification; independent review pending.**
No Native profile, Standard revision, production Converter adoption or formal
acceptance is approved by this record. Phase 5 A1–A4 remain OPEN.

## Scope, chronology and evidence

The pinned Windows CLI actually converted the existing synthetic CityGML to
three separate GeoPackages. Each exited 0 and was independently read back.
LoD2 geometry/IDs and the source-H-preserving 6697/6677 paths passed the checks
below. Independent ellipsoidal-height accuracy remains **INCONCLUSIVE**.
Real CityGML and OUEM Native/Standard generation were **NOT TESTED**.

Documentation baseline: main **`0ba20af4b675f76e39676f0a4e20508aadbd7065`**,
including merged PRs #83–#86. The earlier execution used OUEM commit
**`8d052872d468a380d04102a062cf29e9acd3172b`**; do not describe it as an execution
of the later merge commit or of this evidence PR.

This supplements, rather than rewrites:

- [#83 source audit](../../reviews/OUEM_PLATEAU_GIS_Converter_Source_Audit_20261027.md): source-based transform/serialization findings.
- [#84 design review](../../reviews/OUEM_Building_CRS_Vertical_Datum_Design_Review_20261027.md): proposed options and unresolved migration decisions.
- [#85 preflight](CLI_SYNTHETIC_VERIFICATION_20261027.md): historically BLOCKED before Rust/MSVC and the CLI became available.
- [#86 GDAL feasibility](GDAL_ALTERNATIVE_FEASIBILITY_20261027.md): a different engine/path; its results are not replaced by this run.

The committed [compact evidence JSON](evidence/CLI_SYNTHETIC_EXECUTION_20261027.json)
contains actual argv/cwd, UTC start/end, return codes, stream hashes, one common
warning transcript, build/runtime identities, CRS/WKT, per-building numerical
results, output hashes and repeat digests. Values were checked against the local
receipts, actual GeoPackages and vertex CSVs when preparing this PR. No numerical
discrepancy with the local RESULTS.md was found.

Local evidence identifier: `data/work/plateau-converter-cli/synthetic-execution-20261027-01/`.
It retains RESULTS.md, the seven generated GPKGs, logs, CSVs and two local
verification scripts. Their identities are recorded in the JSON. These local
files are not committed; GitHub readers have the result tables, compact receipts,
independent fixture expectations and reproduction procedure here. Local scripts
were then-uncommitted diagnostic code, not an already committed OUEM validator.
The JSON is a selected technical evidence summary, not a new acquisition schema.

## Fixed Converter and actual environment

| Item | Observed identity |
|---|---|
| Repository / commit | [MIERUNE/plateau-gis-converter](https://github.com/MIERUNE/plateau-gis-converter/tree/ce7766df9788ce391b149c55df16d33082d0bc72), `ce7766df9788ce391b149c55df16d33082d0bc72` |
| Package / version | `nusamai`, `nusamai 0.1.19`; not an inference that the release tag has this commit |
| Target / profile | `x86_64-pc-windows-msvc` / `release-lto` |
| Rust / Cargo | rustc 1.99.1 (`58cf8f9c3`, 2026-10-13); cargo 1.99.1 (`5f94df478`, 2026-08-27) |
| Toolchain | `stable-x86_64-pc-windows-msvc` at those observed compiler versions; the moving name alone is not a reproducibility pin |
| Native build tools | Visual Studio Build Tools 2026; MSVC `14.51.36231`, Windows SDK `10.0.26100.0` |
| CLI size / SHA-256 | 27,265,024 bytes / `0195a11df4fd0ef30dcd5578175035a918c41285b1fcc329f3399f5337326f1b` |
| Cargo.lock working bytes | `e061cc4dc2db366d46ce620ddbbdbd2502a49a4e2c7e63823509dddba66f2730` |
| Cargo.lock Git blob | `0ea0ee91aad7f488fa37d21535d80e20055e4e57`, matching #85 |
| Independent reader | Ordinary Windows OUEM venv, Python 3.11.9, Shapely 2.2.0, PyProj 3.7.2; full platform/PROJ version in JSON |

The lockfile's Windows working-byte SHA differs from #85's downloaded LF-byte
SHA `6523c64b038d3c4bd458953a1deef105b0993edf88c1f94d077524d78d0500ef`.
Git blob identity matched and Converter status was clean; this is a checkout
newline representation distinction, not evidence of dependency updates.

```powershell
cargo build --locked -p nusamai --bin nusamai --profile release-lto --target x86_64-pc-windows-msvc
```

The prior build completed in 10m17s, exit 0, with no observed build warnings/errors.
CLI `--help` and `--version` both exited 0 from ordinary PowerShell. Converter
HEAD and clean source status were checked after execution. No source patch,
global runtime merge or toolchain upgrade was part of the conversion run.
Build receipt `citygml_conversion_performed=false` describes the earlier build
stage, not the later synthetic execution receipts in the same evidence summary.

Historical absolute paths were `C:/dev/plateau-gis-converter` and
`C:/dev/open-urban-environment-model`. They remain in original argv/cwd receipts
only as execution-location evidence; substitute your own roots for reproduction.

## Immutable synthetic input and expectations

- [two_buildings.gml](../../../tests/fixtures/plateau_converter/two_buildings.gml),
  SHA-256 **`ac2794be68822389f784c3ae896b0343dd4a046edcf46d8ca577418af52081f8`**.
- [expected.json](../../../tests/fixtures/plateau_converter/expected.json),
  SHA-256 **`4116bb577fd45c3db025f4d0f6fec0b51fcd079b21069a41287403c5b2583ca1`**.
- EPSG:6697 envelope; source tuple **latitude, longitude, H metres**.

| Building ID | Base H | LoD1 top H | LoD2 top H | LoD2 structure |
|---|---:|---:|---:|---|
| synthetic_tokyo | 10.25 | 18.25 | 19.75 | 10 polygons, 2 interior rings, 60 vertex occurrences |
| synthetic_niigata | 100.125 | 112.625 | 114.875 | Same counts |

Occurrences include ring closure. Each building has one roof, one base, four
outer walls and four courtyard walls; roof/base contain interior rings. LoD1
has six faces and deliberately different heights. Authored expectations and
PyProj horizontal controls were independent of Converter output. Structure,
identity, finite coordinates, closed rings and input hashes were checked;
complete XSD closure and 3D solid topology were not validated.

## Commands actually executed

Initial LoD2 conversions ran 2026-10-27 **23:29:13.719635–23:29:13.962094 JST**.
The following uses path placeholders for the exact argv retained in JSON:

```powershell
$cli = '<converter-root>\target\x86_64-pc-windows-msvc\release-lto\nusamai.exe'
$fixture = '<ouem-root>\tests\fixtures\plateau_converter\two_buildings.gml'
& $cli $fixture --sink gpkg --output '<new-run>\lod2_epsg6697.gpkg' --epsg 6697 -t use_lod=lod2
& $cli $fixture --sink gpkg --output '<new-run>\lod2_epsg4979.gpkg' --epsg 4979 -t use_lod=lod2
& $cli $fixture --sink gpkg --output '<new-run>\lod2_epsg6677.gpkg' --epsg 6677 -t use_lod=lod2
```

`use_lod=lod2` was explicit; `split_components=false` was the unchanged GPKG
default. Each command was repeated to a new `repeat_lod2_epsg*.gpkg`, and a
separate `--epsg 6697 -t use_lod=lod1` control was executed. All seven exited 0.
`record_command` captured subprocess argv without shell interpolation, raw
stdout/stderr and return codes. An existing output was never reused: the
audited sink can delete an existing file.

Each conversion emitted six schema warnings about unsupported Point attributes
`location`, `startPoint`, `endPoint`, `origin`, `elevationValue`, `pos`.
They do not demonstrate a missing non-null fixture value, but prevent any claim
of universal attribute preservation. Empty stdout was not used as proof of success.

## Independent GeoPackage and geometry checks

Each output had SQLite integrity `ok`, no foreign-key violations and one feature
layer **`bldg:Building`**, two uniquely identified buildings, geometry column
`geometry`, type **MULTIPOLYGON Z**, `z=1`, `m=0`.

Every BLOB header and WKB geometry was decoded independently of Converter.
`gpkg_contents`, `gpkg_geometry_columns` and BLOB SRS IDs matched the requested
EPSG, and `gpkg_spatial_ref_sys` organization/code/WKT matched PyProj's EPSG
definition. Geometry coordinates follow GIS longitude/latitude or easting/northing
order; this mapping is explicit and distinct from EPSG authority axis order.

All 20 LoD2 polygons, 24 rings and **120 XYZ occurrences** were matched by building,
surface geometry and ring, allowing cyclic ring starts/reversal. Exterior/interior
identity, repeated vertices and multiplicity were retained. Every XYZ was finite.
`id` survived; `measuredHeight` was 9.5 / 14.75 m. LoD1 control readback matched
all source LoD1 rings/XYZ exactly, with six faces and tops 18.25 / 112.625 m.

This does **not** prove retention of separate thematic RoofSurface/WallSurface/
GroundSurface IDs or classification. They are grouped into parent geometry in
the tested unsplit output. There is no explicit source_lod field in that output;
the selected LoD is retained in the hashed execution receipt. MultiPolygon Z
is not CityGML Solid serialization or an independently proven watertight solid.

## XYZ and vertical results: separate verdicts

| Check | Verdict and measured evidence |
|---|---|
| LoD2 geometry/Building IDs | **PASS**, within this fixture and grouping mode |
| 6697 XYZ preservation | **PASS** after lat/lon → GIS lon/lat mapping: all XY and H residuals exactly 0 |
| 6677 Z preservation / horizontal projection | **PASS**: all H residuals 0; maximum XY component residual `3.2272509997710586e-08 m` against independent PyProj horizontal 6668→6677 |
| 4979 unchanged XYZ preservation | **FAIL for this preservation criterion**: Z is intentionally transformed; this is not a claim of a Converter defect |
| 4979 independent vertical-transform accuracy | **INCONCLUSIVE**: no independent geoid N oracle supplied |
| 6677 standalone vertical declaration | **INCONCLUSIVE**: its actual WKT is 2D; a name mentioning vertical height does not define a vertical CRS |
| Real CityGML application | **NOT TESTED** |
| OUEM Native / Standard generation | **NOT TESTED** |

The pre-existing diagnostic budgets were H ≤1e-9 m and horizontal residual ≤1e-4 m.
They were not tuned to outputs and are computational checks, not survey accuracy.

Measured 4979 `output Z − source H`:

| Location | Minimum increase (m) | Maximum increase (m) |
|---|---:|---:|
| Tokyo | 37.25503752000003 | 37.256111280000034 |
| Niigata | 39.49240892 | 39.49331448000004 |

XY remained exact and top-minus-base at the **same XY** remained exactly 9.5 /
14.75 m. Matching geometry/relative height is not an independent oracle for N.
The [pinned vshift implementation](https://github.com/MIERUNE/plateau-gis-converter/blob/ce7766df9788ce391b149c55df16d33082d0bc72/nusamai-projection/src/vshift.rs)
identifies `h=H+N(lon,lat)` with embedded GSIGEO2011; the executed location-dependent
change is consistent with that source path. Model accuracy, coverage and real
datum alignment are not independently proven by this observation.

6697 compound WKT and retained synthetic source H are semantically consistent
within the declared fixture. This is not independent T.P. measurement validation.
6677 `srs_name` contains `+ JGD2011 (vertical) height`, but its WKT has only two
horizontal axes. Retained H therefore needs separate vertical provenance or a
reviewed compound representation. No CRS label was rewritten to force agreement.
The observed difference is not a constant correction and does not establish
the cause of historical A1/A3 data discrepancies.

## Repeatability and output identities

Repeated outputs had exactly equal normalized digests of IDs, geometry XYZ/rings
and attributes. Normalization excludes generated fid, row order and cyclic ring
start/direction; it preserves ring roles, all XYZ and multiplicity. CRS/geometry
metadata also agreed, and contents agreed excluding `last_change`.

**Byte-level SHA-256 did not match.** Different `last_change` values were observed;
the experiment did not attribute every individual differing byte. Do not promise
byte reproducibility from normalized semantic equality.

| Initial LoD2 output | SHA-256 |
|---|---|
| 6697 | `00af24b34f750ef71ead24b02cf7ff395c0ac125e51449888c3a84ab309d0fce` |
| 4979 | `9ea28fd02a46611abfc85ddd2d67e9c77edbae114c099c28ba561365734320de` |
| 6677 | `f3b324788ecfb6cdff85c593a808b358f5c10e6dde3313379c218c03d812a752` |

Repeated output hashes, semantic digests, timestamps and the LoD1 control hash
are retained without abbreviation in the evidence JSON. GPKGs themselves are
not committed; they are 98,304 bytes each in this local run.

## Reproduction procedure

1. Obtain the exact Converter commit and locked dependencies. Use the build
   command above in an MSVC developer environment; record actual compiler/SDK
   versions. Confirm clean source and executable identity before reproducing
   this binary's results. A different toolchain may yield a different binary
   hash and must have a new receipt, not be called the recorded executable.
2. Verify both fixture hashes above. In the ordinary OUEM venv, run
   `ouem.plateau_converter_probe.inspect_fixture(fixture, expected)` and the
   existing related tests. This is structural checking, not full XSD validation.
3. Create a **new** ignored child of `data/work/plateau-converter-cli/`; refuse
   existing output paths before starting. Use the three explicit commands above.
   The existing [record_command](../../../src/ouem/plateau_converter_probe.py)
   helper can retain argv/stdout/stderr/exit/time/hash receipts with timeout 120s.
   It does not validate output. Do not point a command at a previous GPKG.
4. Open each GPKG with Python `sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)`
   using an absolute path. Query `PRAGMA integrity_check`, `PRAGMA foreign_key_check`,
   `gpkg_contents`, `gpkg_geometry_columns`, `gpkg_spatial_ref_sys`, and all feature
   BLOBs/attributes. Store output hashes before and after reading.
5. Decode the GPKG prefix: bytes 0–1 must be `GP`; byte 3 flag bit0 selects
   header endianness; bytes4–7 hold int32 SRS. Envelope indicator `(flags>>1)&7`
   selects 0/32/48/48/64 envelope bytes for codes0–4. WKB starts at `8+envelope_bytes`.
   Decode with `shapely.from_wkb` and require MultiPolygon Z. Do not treat a
   2D geometry-validity result as a 3D solid check.
6. Compare all source LoD2 exterior/interior rings by ID, allowing only cyclic
   starts/reversal. The existing fixture-only
   [source_reference/signature helpers](../../../src/ouem/gdal_citygml_feasibility.py)
   provide an independent source extraction and exact canonical ring signature
   for 6697 GIS lon/lat/H. For 6677 apply
   `Transformer.from_crs(6668, 6677, always_xy=True)` to source lon/lat; preserve
   source H and check all component residuals against the stated budgets.
   For 4979 check XY/structure and same-XY vertical span separately; record all
   h−H deltas, without claiming an independent N accuracy result.
7. Check WKT against `CRS.from_epsg(code)` with explicit GIS axis mapping, and
   compare selected SRS ID in all tables and BLOBs. Inspect axis/vertical
   content rather than trusting the EPSG label or srs_name alone.
8. Repeat into separate paths; compare byte SHA independently of normalized
   ID/geometry/attribute equality. Run the separate LoD1 control and verify its
   expected six faces and distinct heights. Keep failure receipts as failures.

No new conversion or algorithm was run to publish this evidence PR. The original
local verification scripts are identified by hash; they were not promoted as
a complete reusable validator or copied into production code. The existing
fixture/recorder and explicit method above are reused rather than introducing
a second parser or formal validation specification.

## Native boundary, remaining work and Documentation Impact

Generic Native ingest can copy defined-CRS geometry, but actual ingest was not
executed. The current [Standardizer](../../../src/ouem/standardize/building/_gdal_worker.py)
accepts 4979 and preserves Z as application-defined T.P. H. Passing this run's
4979 h output through that unchanged path would misinterpret h as H. 6697 is
not an accepted Standardizer input. A metadata relabel is not a solution.

Next minimum step: review the #84 source-H-preserving profile proposal, explicit
axis/vertical provenance, profile dispatch and backward compatibility before any
implementation. Option B remains proposed. If retaining the 4979 route, obtain
an independent N reference/model identity and test inverse/double-transform
prevention. Do not change old Accepted artifacts or reinterpret their meaning.

Full XSD closure/solid topology, BuildingPart/xlink/appearance, malformed/nonfinite
inputs, interruption and existing-output behavior were not executed here.
Real PLATEAU v5 conversion, source-to-ground comparisons and Phase 5 integration
need separate authorization and evidence.

Historical related tests: **14 passed in 0.36s** for
`tests/test_plateau_converter_probe.py tests/test_gdal_citygml_feasibility.py`.
These test fixture/recording helpers; they are distinct from the seven Converter
executions and independent GPKG checks. Publication-time test results are recorded
in this PR description. Full pytest is not required for this documentation-only
PR and was not claimed as executed in the historical conversion record.

Documentation Impact: Verification evidence is added and the historical preflight
receives only a navigation link. Architecture/Standard, Implementation, Current
State, Acceptance and Phase 5 Gate are unchanged: no contract, behavior or accepted
scope changes, and no new Native/Standard execution. The historical blocked result
and GDAL assessment retain their date and original scope.
