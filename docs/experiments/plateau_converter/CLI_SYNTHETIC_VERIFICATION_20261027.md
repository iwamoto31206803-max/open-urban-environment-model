# PLATEAU Converter CLI synthetic verification — 2026-10-27

Later evidence: [Windows CLI synthetic execution](CLI_SYNTHETIC_EXECUTION_20261027.md)
records the subsequent successful build/run and bounded output checks. The
BLOCKED preflight below remains a historical account of its inspected environment.

## Result and scope

**Converter execution: BLOCKED.** No located Windows CLI or Rust/Cargo build
chain is available in the inspected environment, including an individually
approved ordinary-environment preflight. No Converter was installed/built/run;
no synthetic or real CityGML was converted. This is a reproducible preflight
and fixture preparation record, **not a completed Converter verification suite**.
Option B remains a proposed design; Phase 5 A1–A4 remain **OPEN**.

Baseline main **`417dac6974cab9200b79d672e50ad23157292853`**, PR #84 confirmed
merged. Basis: [source audit #83](../../reviews/OUEM_PLATEAU_GIS_Converter_Source_Audit_20261027.md),
[design review #84](../../reviews/OUEM_Building_CRS_Vertical_Datum_Design_Review_20261027.md),
[Standard Building](../../OUEM_Standard_Building_v0.1.md),
[Building status](../../status/BUILDING_CURRENT_STATE.md),
[Raw acquisition](../voxcity_canopy_shadow/PHASE5_PLATEAU_ACQUISITION_20261027.md)
and [governance](../../OUEM_Documentation_Governance_v0.1.md).
The existing 2025 CityGML, Converter/Native/Standard artifacts and accepted
records were not used as conversion inputs or modified.

## Environment and candidate selection

Observed OS: Windows 10.0.26300, x64 (Python machine AMD64), PowerShell 7.6.5;
OUEM `.venv/Scripts/python.exe`, Python 3.11.9. PATH lookup found no `rustc`,
`cargo`, `cl`, `cmake` or `nusamai`. Read-only checks also found no Rust executables
under the user's standard `.cargo/bin`, Visual Studio Installer `vswhere.exe`,
or Visual Studio directories under the two standard Program Files roots.
Known PLATEAU GUI installation paths and repository filename search found no
usable CLI. This is bounded discovery, not a whole-PC absence claim.

The recorded `git --version` command succeeded. Actual attempts to start
`rustc --version` and `cargo --version` raised WinError 2; their receipts have
null exit codes and explicit start errors. Empty stdout/stderr files do not
mean a compiler ran successfully. Ordinary-environment preflight confirmed the
same missing CLI/build prerequisites; no alternate OS/container was assumed.
The [Rust Windows prerequisites](https://rust-lang.github.io/rustup/installation/windows-msvc.html)
require a linker/libraries/Windows API import libraries; installation of a
toolchain or system build tools was not attempted by this task.

| Candidate | Exact identity / reason for distinction |
|---|---|
| Official v0.1.14 | `e1c8feff7d8ff3e132230d6c21eaed4879e4a235`; audited BLOB SRS4326 mismatch, max/min-only LoD and CLI runtime error handling make it unsuitable as an assumed-correct oracle |
| Developer v0.1.19 | `a038cff3b1a98c38ef4753f5f7ca3272a3eb1e37`; a release, **not** the audited developer commit; newer fixes are not assumed present |
| **Selected future verification candidate** | **MIERUNE `ce7766df9788ce391b149c55df16d33082d0bc72`**, already audited in #83: requested SRS propagation, fixed-LoD options, improved error propagation/finalization. Existing output is still deleted, so isolation is mandatory. This is source-based selection, not an executed binary acceptance |

Current official/developer release metadata was re-read. Both observed release
asset lists contain Windows GUI EXE/MSI and CLI macOS ARM/Linux x64 tarballs,
**no Windows nusamai CLI asset**. No GUI installer was downloaded or treated as
a CLI. Sources: [official release](https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter/releases/tag/v0.1.14),
[developer release](https://github.com/MIERUNE/plateau-gis-converter/releases/tag/v0.1.19).

Only the selected commit's [Cargo.lock](https://github.com/MIERUNE/plateau-gis-converter/blob/ce7766df9788ce391b149c55df16d33082d0bc72/Cargo.lock)
was downloaded as source metadata, with individual network approval:

- 243,814 bytes; SHA-256 **`6523c64b038d3c4bd458953a1deef105b0993edf88c1f94d077524d78d0500ef`**.
- Git blob SHA-1 `0ea0ee91aad7f488fa37d21535d80e20055e4e57` independently
  recomputed from the received bytes and matched the GitHub file response.
- Lock graph includes japan-geoid 0.4.4 / embedded GSIGEO2011, jprect 0.0.4,
  flatgeom 0.0.2, SQLx 0.8.6 and Quick-XML versions described in #83.
- Complete Converter source archive, dependency packages, model artifact and
  executable were **not acquired**: their actual SHA-256 values are unavailable,
  not fabricated from the commit or lock hash. No build-success claim follows.

Sandbox network policy is restricted; approved Git fetch and fixed raw lockfile
HTTP acquisition succeeded. Dependency registry/Git dependency downloads and a
locked Windows build were not attempted. Network success is not build readiness.

## Committed fixture and independent expectations

[two_buildings.gml](../../../tests/fixtures/plateau_converter/two_buildings.gml)
is a small, authored CityGML 2.0 Building fixture, not a sample copied from real
PLATEAU data. [expected.json](../../../tests/fixtures/plateau_converter/expected.json)
records authored IDs/quantities, counts and independent horizontal controls.

| Building | Source latitude / longitude | Base H | LoD1 top H | LoD2 top H |
|---|---|---:|---:|---:|
| synthetic_tokyo | 35.63 / 139.57 | 10.25 m | 18.25 m | 19.75 m |
| synthetic_niigata | 37.12 / 138.28 | 100.125 m | 112.625 m | 114.875 m |

The envelope declares the full EPSG:6697 HTTP URI and dimension3. Each building
has a six-face LoD1 solid and ten LoD2 thematic polygons: one roof, one base,
four outer walls and four courtyard walls. Roof/base each contain an interior
ring. Distinct LoD heights make accidental max/min selection observable.
All rings use closed 3D posList sequences; XML IDs are unique.

Fixture SHA-256: **`ac2794be68822389f784c3ae896b0343dd4a046edcf46d8ca577418af52081f8`**.
Committed LF expected JSON SHA-256: **`4116bb577fd45c3db025f4d0f6fec0b51fcd079b21069a41287403c5b2583ca1`**.
The checked-in original fixture is immutable per run; failure variants must be
separate temporary copies with new hashes.
Directory-local Git attributes force LF for these GML/JSON fixtures so Windows
checkout newline conversion cannot silently invalidate the recorded hashes.
Earlier preflights used the same expected JSON content with CRLF (SHA-256
`378fb1120d17567969141d1d68ecd57007f60dde0acb287fc4f4db748c3250a0`);
their receipts are preserved. A final preflight records the normalized LF bytes;
no GML coordinates, expected values or old receipts were changed.

Expected H/top values are authored independently of Converter. XY controls use
PyProj 3.7.2, explicit horizontal6668→6677, always_xy; outer four and inner four
corners are identified by source coordinate pairs. Match by ID/LoD/surface/ring
and coordinates, not ordinal position after Converter dedup/merge. Proposed
computational checks are preserved-H ≤1e-9m and horizontal residual ≤1e-4m;
the latter is a diagnostic budget far below the fixture vertex spacing, not
survey accuracy, and requires review before execution. Neither is tuned to
Converter output. No independent geoid N reference has been supplied.

**Actually checked:** well-formed XML, hash, CRS declaration, IDs, per-LoD polygon
counts, finite triples, closed rings, base/top extrema, inner rings and thematic
surface presence. **Not checked:** complete CityGML XSD closure, solid topology,
Converter parser compatibility, output correspondence or geoid accuracy.
Existing source support has only two local XSD files, not a complete pinned OGC
schema closure. No full-schema validity claim is made; obtaining and validating
that closure is a prerequisite to the future claimed schema check.

## Reusable script and local evidence

[ouem.plateau_converter_probe](../../../src/ouem/plateau_converter_probe.py) is
an **experimental preflight/fixture inspector and command recorder**, not a new
Building adapter, a Converter substitute or a full GPKG validator. It only creates
a new child of ignored `data/work/plateau-converter-cli/`, rejects existing/outside
run directories, records argv/environment/raw stdout/stderr/exit/start errors and
hashes, and marks unexecuted conversion cases NOT RUN. Its CLI does not run Converter.

```powershell
.venv\Scripts\python.exe -m ouem.plateau_converter_probe `
  --output-dir data/work/plateau-converter-cli/new-run-id
```

BLOCKED returns module exit2; a start failure has no subprocess exit code.
Do not confuse this preflight result with a Converter exit code. This session's
shell tool reported exit1 for a direct blocked invocation. A separate recorded
Python subprocess independently confirmed the module's actual child exit2 and
retained stdout/stderr/exit receipts; this is not a Converter exit code.

Local evidence roots (not committed):

- `data/work/plateau-converter-cli/blocked-synthetic-20261027-01/`: initial
  sandbox preflight, fixture identities, environment and tool-command receipts.
- `data/work/plateau-converter-cli/approved-preflight-20261027-01/`: ordinary
  environment preflight; same missing prerequisites. Every command has its
  `.json`, `.stdout.log`, `.stderr.log` and content hashes.
- `data/work/plateau-converter-cli/source-metadata-20261027-01/`: exact downloaded
  Cargo.lock and HTTP/source/hash receipt.
- `data/work/plateau-converter-cli/recorded-preflight-20261027-01/`: outer
  invocation receipt confirming child exit2, and its nested fresh preflight run.
- `data/work/plateau-converter-cli/final-preflight-20261027-01/`: final LF
  expectation identities and independently recorded blocked child exit2.

Preflight module disk SHA-256 at execution is recorded in each preflight JSON.
Those executions used then-uncommitted added code over the baseline; do not
claim they ran from an already committed implementation. No runtime snapshot,
binary, dependency cache, generated GPKG or local run directory is committed.

## Verification classification

| Item | Classification | Actual evidence / remaining condition |
|---|---|---|
| Environment/probe and fixture structural checks | PASS | Executed, independently inspected fixture structure; limited scope stated above |
| Cargo.lock received-byte identity | PASS | Actual SHA-256 and Git blob identity checked; no dependency binary claim |
| Full CityGML XSD / topology | NOT RUN | Complete pinned schema closure and topology validation still required |
| V1:6697 axes/H/correspondence | BLOCKED | No Converter execution; source-H preservation remains SOURCE-ONLY in #83 |
| V2:4979 geoid addition/location dependence | BLOCKED | No CLI or independent N oracle; no numeric accuracy PASS even if a future CLI completes |
| V3:6677 XY/H preservation | BLOCKED | Independent expected XY supplied, no Converter output to compare |
| V4:BLOB/CRS tables/type/Z/ID/LoD/count | BLOCKED | No generated GPKG; source fixes are not actual serialization evidence |
| Invalid XML/coordinate/CRS, existing-output deletion, partial failure | NOT RUN | No Converter process; recorder's tests are not Converter fault tests |
| Repeated GPKG byte and normalized semantic equality | NOT RUN | No GPKGs exist from this task |
| Source transform/LoD/error behavior | SOURCE-ONLY | Fixed-commit findings from #83, not release/binary execution results |

No actual Converter FAIL was observed because none ran. The local matrix's
NOT RUN entries describe execution occurrence; the table's BLOCKED explains
why CRS/GPKG execution could not begin. Exit0 alone will never close those checks.

## Resume procedure and missing conditions

1. Provide a verified Windows nusamai CLI or explicitly provision an appropriate
   Windows Rust/MSVC/SDK environment. Do not silently substitute Linux/WSL or use
   a GUI installer as a CLI. Record compiler/linker/SDK/target versions.
2. In a new ignored directory, obtain the exact selected source commit and verify
   `git rev-parse HEAD`, clean status and the Cargo.lock SHA above. Record the
   source archive/tree receipt and every acquired dependency's lock checksum/Git
   revision; keep local package/model content hashes and notices. No download or
   build in this step has been performed here.
3. From that source, proposed CLI build is `cargo build --locked -p nusamai
   --profile release-lto --target x86_64-pc-windows-msvc`. Fix a compatible exact
   Rust toolchain before running; `stable` alone is not a reproducible toolchain
   pin. Dependency cache/network and any extra native prerequisites must be
   resolved rather than removing --locked. Record executable SHA and build logs.
4. Validate fixture with a complete pinned CityGML2/Building/GML schema closure.
   Resolve parser support and independently checked geoid reference samples/model
   identity. Do not call the same Converter output or the same helper twice an
   independent N oracle.
5. Create a new synthetic-only run; for each6697/4979/6677 use an explicit separate
   output and a recorded command of this form (not run here):

```text
<verified-nusamai.exe> <repo>/tests/fixtures/plateau_converter/two_buildings.gml
  --sink gpkg --output <new-run>/v1.gpkg --epsg 6697 -t use_lod=lod2
```

Use `record_command(argv, new_case_directory, label, timeout=...)` from the probe
to retain argv, cwd, raw logs and returncode, with absolute input/executable/output
paths. Before invoking, independently verify the binary SHA against its build
receipt. This recorder **does not independently inspect GPKG or mark a case PASS**;
the V1–V4 decoder/validator and complete matrix runner remain subsequent work.

6. Independently decode each BLOB SRS/WKB Z and compare all three GPKG CRS tables,
   expected two parent Building IDs, selected-LoD surfaces/heights and ring/hole
   correspondence. Record split/group/lost-feature counts. Source-declared T.P.
   and ellipsoidal h must remain distinct.
7. Isolated failure copies: malformed XML; posList token `invalid` and separately
   nonfinite NaN; an explicitly unsupported CRS; a disposable existing-output
   sentinel; a partly valid then malformed input/aborted run. Record returncode,
   logs and *all* output/sidecar bytes or absence, including sentinel deletion.
   Never aim these cases at existing OUEM/Converter datasets.
8. Repeat identical pinned input/settings. Record file hashes separately from
   normalized ID/LoD/geometry/attribute digests, ignoring only predeclared ordering/
   timestamps. Explain byte differences, require independent numerical agreement
   and no input mutation. Do not silently repair output or tune expectations.

These steps are pending verification work, not evidence of an available complete
Windows build recipe or automatic Option B approval. Independent review must
decide the next environment provisioning and validation work before real data.

## Repository validation and Documentation Impact

The new recorder/fixture tests are separate from Converter verification.
Actual repository validation:

- `.venv/Scripts/python.exe -m pytest -q tests/test_plateau_converter_probe.py`:
  **9 passed**, 0.27s; no Converter executable used.
- Initial sandbox full pytest: **71 failed, 518 passed, 5 skipped, 245 warnings,
  25 errors**, 211.92s. Representative traces include existing `os.replace` /
  link operations denied with WinError5. This run was not PASS.
- Individually approved ordinary Windows rerun, same full pytest command:
  **614 passed, 5 skipped, 250 warnings**, 161.21s, exit0. Existing tests/expected
  values were not weakened. Warnings are Rasterio Affine PendingDeprecationWarning.
  Full stdout/stderr and argv/cwd/exit receipt are retained under the approved
  preflight directory. This separates environment failure from normal-runtime
  regression evidence; it does not certify Converter behavior.
- Final LF normalization changes expectation JSON line endings only; fixture
  structure/recorder tests passed again (**9 passed**, 0.20s), and the final
  recorded preflight returned actual child exit2 / BLOCKED.

Existing production
Building/Standard/Adapter code and schemas, Current State and Acceptance Records
are unchanged. This adds only experimental preparation code, small synthetic
fixtures/tests and this bounded report. No new data contract or public production
CLI is registered; the module is invoked explicitly.

Documentation Impact: Verification records an environmental BLOCKED outcome and
limited fixture/probe checks; Implementation documents only the new experimental
probe. Architecture/Standards and historical records require no amendment because
no approved coordinate semantics, accepted dataset or production behavior changed.
Phase 5 A1–A4 stay OPEN. Option B and Converter adoption remain unapproved.
Draft PR, independent review required; no merge.
