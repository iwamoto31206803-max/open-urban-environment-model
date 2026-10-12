# Windows local acceptance helpers

Files in this directory are temporary, user-facing operational helpers for
local experiments and acceptance runs. Stable reusable logic belongs under
`src/ouem`, and accepted conclusions belong under `docs`.

## Runtime boundary

The Komae workflow keeps two independently managed runtimes:

- **QGIS/OSGeo4W** owns GDAL/OGR, `osgeo`, and future native tools such as
  PDAL.
- Repository-local **`.venv`** owns OUEM orchestration and portable Python.

OUEM is not installed into QGIS Python, and `osgeo` is not installed into the
OUEM venv. Never start `.venv\Scripts\python.exe` from OSGeo4W Shell. GIS
Python is used only as a child-process worker through a file/argument contract.

## Komae PLATEAU acceptance workflow

### 1. Manual preprocessing

Display the instructions with:

```bat
scripts\work\plateau_komae_local_acceptance.cmd manual
```

Open the PLATEAU Building CityGML in PLATEAU GIS Converter GUI, select maximum
LOD and settings that retain 3D/Z geometry, and export the GeoPackage to:

```text
data\work\building\plateau_komae\53393465_bldg_6697_op_convert.gpkg
```

This is an external/manual, non-authoritative processing intermediate, not
OUEM Native Building. `data\work` is a side workspace outside the formal
RAW-to-Native-to-Standard lifecycle. The helper does not automate or launch
the GUI.

### 2. Capture the GIS child runtime

In **OSGeo4W Shell**, run:

```bat
scripts\work\plateau_komae_local_acceptance.cmd gis
```

This runs the main-branch GIS runtime check and writes the ignored runtime
snapshot used by the ingest child process. Close OSGeo4W Shell afterward.

### 3. Run OUEM ingest

In a **new ordinary Windows cmd or VS Code terminal**, install the current
checkout and run:

```bat
.venv\Scripts\python.exe -m pip install -e .
scripts\work\plateau_komae_local_acceptance.cmd ouem
```

The OUEM stage rejects inherited QGIS/OSGeo4W variables, verifies the exact
repository `.venv` interpreter, runs the automated tests, and ingests the
Converter GeoPackage. With no second argument it uses the canonical work
path shown above. Explicit repository-relative paths are always resolved from
the repository root, regardless of the current working directory. Absolute
paths are also supported; quote any path that contains spaces:

```bat
scripts\work\plateau_komae_local_acceptance.cmd ouem D:\another\converted.gpkg
scripts\work\plateau_komae_local_acceptance.cmd ouem "D:\PLATEAU data\converter-output.gpkg"
```

The provider resolves a unique Building layer. If there are zero or multiple
candidates, it fails with available layer names and asks for an explicit layer.
Pass one as the optional third argument:

```bat
scripts\work\plateau_komae_local_acceptance.cmd ouem data\work\building\plateau_komae\53393465_bldg_6697_op_convert.gpkg bldg:Building
```

The helper checks the locally verified Komae Building count of 3637. This is
pilot acceptance metadata, not a general provider requirement. It does not
compare that count with unrelated layers in the intermediate GeoPackage.

Python 3.11.9 is the accepted local OUEM runtime but not a package-wide
minor-version lock; `pyproject.toml` remains authoritative. The confirmed GIS
runtime is QGIS 4.2.3, GDAL 3.13.3, and GIS Python 3.12.14.

The runtime snapshot records the GIS output encoding. OUEM captures GIS child
streams as bytes and decodes them explicitly, avoiding cp932/UTF-8 reader-thread
failures on Japanese Windows.

## Manual QGIS acceptance

After ingest passes, open `data\native\building\komae.gpkg` in QGIS:

1. confirm Building footprints in 2D View;
2. inspect `measuredHeight` and related attributes;
3. open QGIS 3D View using geometry Z; and
4. confirm height and three-dimensional form without artificial extrusion.

The successful Komae PoC contained 3,637 Building features, 3D Multi Polygon
geometry, EPSG:4979, and retained Z and source attributes.

## Native to Standard Building acceptance

After Native ingest has been accepted, run the following exact command from a
new ordinary Windows cmd or VS Code terminal (not OSGeo4W Shell):

```bat
scripts\work\plateau_komae_local_acceptance.cmd standard
```

The optional second argument overrides the accepted Native input and supports
repository-relative or absolute paths. The default input is
`data\native\building\komae.gpkg`; output is always
`data\standard\building\komae.gpkg` with an adjacent manifest. The command
uses the previously captured GIS child runtime and the canonical
`config\study_areas\komae_09LD3451.yaml` configuration. Its summary reports
input/output paths and counts, input/output CRS, geometry type and 3D status,
the extent, required metadata, Z preservation, deterministic IDs, and a final
PASS/FAIL. The accepted EPSG:4979 Native layer is the formal input. Conversion
uses its EPSG:4326 horizontal component for projection to EPSG:6677 and carries
the application-defined absolute T.P. Z unchanged rather than interpreting it
as ellipsoidal height. Boundary-intersecting buildings retain complete geometry.
The accepted Native schema uses its non-null String `id` field as the source
feature identifier. Standardization maps that value to Standard `source_id`;
it neither requires `gml_id` nor changes the Native GeoPackage.

The Komae real-data run completed with `PASS`: 3,637 input features produced
111 study-area-selected output features in EPSG:6677, with 3D Multi Polygon
geometry, required metadata, maximum Z delta 0 m, and deterministic IDs all
passing. The formal result and its scope limitations are recorded in
`experiments\a1_e2e_pilot\README.md`.

## Komae Terrain local acceptance

Install the package (including Rasterio) in the repository venv, place the
developer-local DEM at `data\raw\terrain\tokyo_23ku_dem_050m\komae\09LD3451.tif`, and run from an
ordinary Windows terminal:

```bat
scripts\work\terrain_komae_local_acceptance.cmd
```

An optional first argument overrides the input path. The helper runs synthetic
automated tests, creates the Native registration manifest, and creates and
validates Standard Terrain. Its Standard summary reports paths, dimensions,
CRSs, pixel sizes, extents, type, both NoData values, valid/NoData counts and
proportion, elevation range, grid/elevation preservation, source-declared T.P.
vertical status, and overall PASS/FAIL. The Native and adjacent Standard
manifests record the Tokyo Metropolitan Government evidence for that declaration
as well as deterministic source/output SHA-256 checks. The standalone A2 Komae
real-data run on 2026-10-06 recorded **PASS** and is **ACCEPTED** for the baseline
identified in the [formal A2 acceptance record](../../docs/acceptance/OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md).
That result is specific to the recorded local tile and conditions; a new run
requires the actual local input and is not replaced by synthetic tests.

## Isolated Komae A1/A2/A3 integration demonstration

`python -m ouem.komae_integration run` connects the existing Native Building
standardizer, Native Terrain standardizer, and A3 acceptance runner. It runs
all three stages twice in independent folders. It does not rerun CityGML
conversion/Native Building ingest, change Standard contracts, or promote any
output to the accepted baseline. Here A1/A2/A3 are implementation milestones,
not the conceptual national model variants.

### Read-only Adapter content failure diagnosis

After review/merge, from an ordinary Windows cmd at the repository root:

```bat
scripts\work\diagnose_komae_adapter_content.cmd komae-contained-001
```

This reads an **existing contained-PoC run** only. It does not start the runner,
A1/A2/A3, GIS Python, VoxCity, standardization, or a repair. Nothing in the run
is overwritten, deleted or regenerated. Use OUEM `.venv`, separately from GIS.
The launcher accepts exactly one run ID, not a path; no `--force` or output-file
option exists. Python equivalent (Linux uses `.venv/bin/python`):

```bat
.venv\Scripts\python.exe -B -m ouem.komae_adapter_diagnostics komae-contained-001
```

The diagnostic reads `integration-report.json`, discovers each A3 input and
Adapter from its recorded `repeat-N-a3` command and artifact inventory, and
reads the inventoried PoC reference. It **never executes a recorded command**.
It does not guess Adapter/Standard filenames. The reference supplies the exact
sorted ID list used by the runner; each repeat's Standard Building IDs are also
checked against it. Artifact SHA-256/size must match the saved inventory and
input hashes must remain unchanged during inspection. Missing/ambiguous stages,
changed artifacts, unsafe paths/links or active GeoPackage sidecars block the
diagnostic. Close concurrent writers; do not delete sidecars or edit evidence to
make it pass. A relocated byte-identical run can be read through its relative
inventory keys even when the saved command paths refer to the original location.

Each repeat shows these unchanged `adapter_quality()` clauses separately:

- Exact CRS string `urn:ogc:def:crs:EPSG::4326`, including the observed value.
- Exact ordered `ouem_id` list equality, with missing/extra occurrences,
  order-only mismatch, and differing positions. Set equality alone is not PASS.
- `id == voxcity_id ==` the 1-based feature position, with offending building,
  expected sequence value and both actual values. No new integer-type rule.
- Finite positive `height` and `min_height == 0`, with offending ID and values.
- Valid, nonempty, 2D geometry of positive area, with invalid/empty/Z/nonpositive
  area classifications, geometry type, area and Shapely validity explanation.

The production function and all generation/quality code remain unchanged.
Diagnostics call that existing function and check aggregate parity, then compare
with saved `quality.adapter_content`. Exceptions in the existing predicate are
reported as ERROR/NOT_CHECKED, never claimed as a verified boolean result.
Repeat comparison covers conditions and their observations; it is a diagnosis
comparison, **not a new voxel reproducibility or acceptance verdict**.

Exit codes: **0** both repeats PASS with consistent evidence; **1** one or more
adapter conditions FAIL, with matching existing/saved predicates; **2** blocked,
incomplete, exception, or inconsistent evidence. Exit 1 is an explained quality
failure, not a request to rerun the pipeline. The tool does not change the saved
`status`, `quality`, `reproducibility` or `acceptance` fields.

For complete per-building observations, add `--json` to the Python command;
JSON goes to stdout and nonfinite numeric values are represented as strings.
No files are created by the tool. If retaining terminal output, choose a new
local review file **outside existing runs and accepted inputs**; shell redirection
can overwrite files and is not protected by this tool.

Codex and CI use synthetic fixtures only. Run this command on the company PC to
identify the actual failing conditions/IDs in `komae-contained-001`. A cause in
Adapter generation, any correction, and formal acceptance require separate
review after inspecting those results. Do not commit diagnostic artifacts or
real-data inputs to GitHub.

### Read-only geometry provenance diagnosis

After reviewing/merging this diagnostic, use an ordinary Windows cmd and the
OUEM `.venv` (not OSGeo4W Shell):

```bat
scripts\work\diagnose_komae_geometry_provenance.cmd komae-contained-001
```

The default target is `oub-21a29be1-9794-593f-b22c-e3639a7d9d45`. Supply an
optional second argument to inspect another OUEM ID. Python equivalent:

```bat
.venv\Scripts\python.exe -B -m ouem.komae_geometry_provenance komae-contained-001
```

This inspects saved Native → full A1 Standard → contained Standard → Adapter
geometry for **both repeats**. Recorded A1/A3 commands, the artifact inventory,
adjacent manifests and subset parent fingerprints identify files. Commands are
never executed. Native is located through the report's original input path and
hash, not a guessed filename. Its manifest identifies the layer; A1's recorded
`source_id` mapping and deterministic OUEM ID rule identify the Native `id`.
There is no row-number or nearest-geometry fallback. A relocated run still needs
its Native inputs at their recorded paths; missing inputs/lineage are reported
as INCONCLUSIVE. Do not edit records to redirect them.

Each saved shape reports type, declared CRS, XY validity/reason, empty/Z flags,
bounds, area, polygon/ring/vertex counts (including ring closure vertices), WKB
hash and any self-intersection coordinate reported by GEOS. Areas and shape
differences are compared in **EPSG:6677 metres**, not geographic degrees.
Reprojection is horizontal-only and in memory, preserving Z without interpreting
Native EPSG:4979 Z as ellipsoidal height. Symmetric-difference area is only
calculated for valid, nonempty polygonal inputs; otherwise it is NOT_CHECKED.

The first invalid **saved representation** and its interval (Native already
invalid, Native→Standard, or Standard→Adapter) are distinct from a proven cause
of the Adapter's self-intersection. Native/Standard can contain 3D surface
assemblies whose XY projections overlap; GEOS ignores Z, and their raw area is
not the dissolved footprint area. Adapter manifest footprint diagnostics are
shown as recorded observations, not independently reconstructed geometry.
An XY-only projection probe shows whether projecting the raw Standard reproduces
the invalid Adapter exactly; it does **not** repeat footprint generation.
Missing normalized/pre-reprojection and rounding snapshots leave the causal
mechanism INCONCLUSIVE. No repair, union, `make_valid`, `buffer(0)`, rounding,
GIS conversion, standardization, voxel generation or E2E rerun is performed.

Saved hashes/sizes are checked before opening artifacts and Native inputs;
all opened evidence (including manifests/report) is fingerprinted and checked
again afterwards. Links, unsafe inventory paths, hash mismatches and active
GeoPackage sidecars block diagnosis. Close other writers first; do not remove
sidecars or alter evidence to make checks pass. Existing report/acceptance status
and all input/output files remain unchanged. Only this building's lineage is
inspected; this is not a revalidation of every run artifact.

Exit codes: **0** complete lineage with all saved geometries valid; **1** complete
lineage with an observed invalid geometry; **2** INCONCLUSIVE lineage, blocked
safety/integrity check, or an unreadable diagnostic. A complete observed interval
can still have an INCONCLUSIVE causal mechanism. Repeat comparison reports
geometry hashes, classification and diagnostic equality separately; it does not
replace the runner's reproducibility/quality checks or establish acceptance.

Add `--json` to the Python command for full metrics/evidence on stdout. No output
file option is provided, so the diagnostic itself cannot overwrite an existing
file. If retaining stdout, choose a **new external review file**, outside runs
and accepted inputs; shell redirection is not protected by the diagnostic.
Do not commit local data or diagnostic reports. Codex/CI exercise synthetic
fixtures only. The actual `komae-contained-001` diagnosis remains a company-PC
task after review/merge; any repair requires a separately reviewed change.

### Opt-in 92-building contained E2E PoC

After review/merge, run from an **ordinary Windows cmd**, with the existing
OUEM `.venv`, trusted GIS snapshot, accepted Native/Standard inputs and RAW DEM
prepared as described below:

```bat
scripts\work\run_komae_contained_poc.cmd komae-contained-001
```

Choose a new run ID every time. This command **executes real processing**; it is
not the read-only preflight. The launcher uses the same Komae input paths as
`preflight_komae.cmd`, a 1 m voxel mesh, 3637 Native features and 92 PoC features.
For different local paths use the existing Python `run` CLI with all its usual
arguments, adding `--contained-poc --expected-buildings 92`. Ordinary `run` and
read-only `preflight` retain the full-reference behavior; `preflight` does not
accept this run-only flag. No existing run can be reused or overwritten.

The user-reported Komae baseline is 111 Standard buildings, with 92 fully
contained and 19 crossing the EPSG:6677 400 m × 300 m Study Area, and an existing
0.5 m DEM (800 × 600). These are **local observations, not CI acceptance results**.
The PoC checks 92 selected / 19 crossing / 0 outside or touch-only at runtime;
any discrepancy blocks execution. The exact diagnostic rule is
`study.covers(normalized_2d_footprint)`, using the existing VoxCity footprint
normalizer. A footprint touching the boundary from inside is included. Entire
original XYZ features and Standard attributes are copied; crossing buildings
are excluded, never clipped. The canonical 111-building input stays unchanged.

Execution and evidence in `data/work/integration/<new-run-id>/`:

1. Hash original inputs/configuration/manifests, select from the accepted
   reference Standard and record selected/excluded IDs and counts in
   `integration-report.json` (`poc_selection`). Save a new `poc-reference.gpkg`
   and a derived, explicitly **not accepted** adjacent manifest with parent
   hashes. Verify that serialization preserves selected XYZ/metadata.
2. Before the GIS probe or any A1/A2/A3 stage, apply the runner's existing
   conservative VoxCity-rectangle DEM coverage check to that subset and RAW DEM.
   Record `poc_coverage` PASS or BLOCKED with the reason. Containment in Study
   Area alone does not prove rectangle coverage. If bounds, finite values or
   NoData coverage fail, stop and retain evidence; no shrinking, filling,
   extrapolation or DEM modification is attempted.
3. Run the existing A1 and its **full 111-building** count/ID/Z/metadata checks in
   each of two independent repeats. Retain `repeat-N/building.gpkg` and its
   original generated manifest. Reapply the same PoC selection, require identical
   reference selected/excluded IDs, and write `building-contained.gpkg` plus a
   derived manifest. This step is selection after A1, not a changed A1 contract.
4. Run unchanged A2 on the registered RAW DEM. Its Standard output still must
   preserve grid/mask/elevations. Recheck RAW and Standard DEM coverage against
   each newly selected building subset, then run existing A3 on the 92 buildings.
   Retain the roof, vertical, overlap, building-retention and array checks.
5. The integration report retains separate `quality` and `reproducibility`
   verdicts, stage logs, SHA-256 evidence and array dtype/shape/content evidence.
   Compare both selected and full A1 building semantics across repeats, as well
   as selection, Terrain, adapter and voxel results. Full A1 artifacts, selected
   inputs and original accepted inputs remain protected by hash checks.

The subset manifests describe PoC selection and parent provenance; they do not
rewrite the original A1 validation or certify a new formal acceptance. Failed
runs and partial artifacts are retained. This workspace is temporary in purpose
but is **not automatically deleted**. Current output isolation/link rejection,
no-overwrite and concurrent-writer limitations still apply.

An `AUTOMATED_PASS` establishes only this 92-building PoC's automated result.
It excludes the 19 crossing buildings and is not a full 111-building evaluation,
formal integrated acceptance, nationwide validation or Phase B simulation.
Standard contracts remain PROVISIONAL. This opt-in policy does not redefine the
Study Area or implement/constrain a future Computation Domain extension.
Codex/CI use synthetic inputs and mocked GIS stages; actual selection evidence,
coverage and E2E reports must be generated and reviewed on the company PC after
merge. Never commit those local artifacts or runtime snapshots.

### Read-only preflight (before authorizing a real-data run)

From an ordinary Windows cmd at the repository root, using a **trusted existing**
GIS runtime snapshot and the actual accepted input paths:

```bat
.venv\Scripts\python.exe -B -m ouem.komae_integration preflight ^
  --native-building data\native\building\komae.gpkg ^
  --native-terrain data\native\terrain\komae_09LD3451.json ^
  --reference-standard-building data\standard\building\komae.gpkg ^
  --study-area config\study_areas\komae_09LD3451.yaml ^
  --gis-runtime scripts\work\.runtime\plateau_komae_gis.json ^
  --run-dir data\work\integration\preflight-example-new-run ^
  --meshsize 1 --expected-buildings 111 --expected-native-buildings 3637
```

On Linux use `.venv/bin/python -B` with the same arguments and local paths.
Preflight neither creates/reserves the proposed run directory nor starts `run`.
It does not transform/write GIS datasets or generate voxels. Read-only geometry
inspection and in-memory coordinate calculations establish preliminary DEM
coverage. A separate GIS child runs only Python identity and `osgeo` import/GDAL
version checks, using `-B`, the snapshot environment, and a 30-second timeout.
The snapshot is executable configuration: use only a trusted local snapshot.
OUEM remains separate from GIS Python; snapshot environment values and child
stderr are not copied to the report. Do not modify an accepted snapshot to make
preflight pass; investigate discrepancies and capture a new snapshot separately
if necessary. Preflight does not install or change dependencies.

Output is JSON (`ouem-komae-preflight/v0.1`) on stdout; no report file is created.
It includes settings, observed environment, selected GIS identity/version,
SHA-256/size/resolved paths of inputs, manifests, snapshot and repository code,
pre/post input integrity, and individual checks. `PASS` (exit 0) means the
read-only prerequisite checks succeeded. `BLOCKED` (exit 2) includes a cause
and required action. Dependent checks and processing-only checks are explicitly
`NOT_CHECKED`. Missing/unverifiable VoxCity provenance blocks the preflight;
the provenance method has the same limitations described below. Python package
imports and `pip check` verify dependencies without invoking the engine.

Checks cover manifest schemas, registered RAW hash/metadata, Native Building
count/IDs/XYZ/EPSG:4979, reference Standard Building semantics/count/EPSG:6677,
Study Area finite EPSG:6677 extent, Terrain Float32 and vertical compatibility,
and the existing conservative DEM coverage check applied to the **reference**
Building. An active GeoPackage WAL/journal blocks inspection; close writers and
review recovery rather than deleting sidecars. Input files are hashed again at
the end. Existing runner output-path/link rules are checked without creating or
probing output files; the real runner still rechecks them on execution.

**PASS is not integrated acceptance or a guarantee that processing will succeed.**
Historical Building manifests do not certify GPKG byte hashes. Output ACLs,
space, locks, future changes/races, GIS conversion, newly generated A1/A2/A3
quality, actual generated VoxCity bounds, voxel arrays and two-repeat
reproducibility remain unchecked. The configured Study Area and preliminary
reference footprint bounds are not interchangeable. QGIS review and formal
local integrated acceptance remain separate. Close concurrent input writers;
these checks do not guarantee safety against hostile concurrent replacement.
If retaining stdout, save it only to a new explicitly chosen local review file
outside inputs, accepted artifacts and the proposed run directory; shell `>`
can overwrite files and is not an output-protection feature of preflight.

### Windows preparation and execution (explicitly authorized real-data runs only)

1. Use a checked-out repository installed into its local OUEM `.venv` (editable
   installation), with the existing dependency pin unchanged. Keep the accepted
   Native Building GeoPackage and its adjacent manifest, Native Terrain JSON
   and its referenced RAW DEM, and accepted reference Standard Building plus
   its adjacent manifest. The reference Standard Building supplies the expected
   `ouem_id` set; no historical Building artifact hash is invented. The Terrain
   registration's absolute RAW path must still resolve; do not edit an accepted
   manifest to relocate it.
2. In OSGeo4W Shell, validate GIS with `python scripts/work/gis_runtime_check.py`.
   Reuse a valid local runtime snapshot or capture a **new** one with
   `python scripts/work/capture_gis_runtime.py scripts/work/.runtime/<new-name>.json`.
   Never overwrite an accepted snapshot. This captures the environment and may
   contain sensitive values; keep it local and do not paste it into reports.
3. Close OSGeo4W Shell. Open an ordinary Windows cmd at the repository root.
   Check the OUEM interpreter and run the synthetic suite:

   ```bat
   .venv\Scripts\python.exe scripts\work\ouem_runtime_check.py --expected-python "%CD%\.venv\Scripts\python.exe"
   .venv\Scripts\python.exe -m pytest -q -ra
   ```

4. After authorization to process the local real data, run with a new run ID:

   ```bat
   .venv\Scripts\python.exe -m ouem.komae_integration run ^
     --native-building data\native\building\komae.gpkg ^
     --native-terrain data\native\terrain\komae_09LD3451.json ^
     --reference-standard-building data\standard\building\komae.gpkg ^
     --study-area config\study_areas\komae_09LD3451.yaml ^
     --gis-runtime scripts\work\.runtime\plateau_komae_gis.json ^
     --run-dir data\work\integration\<new-run-id> ^
     --meshsize 1 --expected-buildings 111 --expected-native-buildings 3637
   ```

   Replace `<new-run-id>` with a new directory name, and select the actual GIS
   snapshot. Exactly two full repeats are performed; there is no `--force`,
   reuse, or resume option. Only a new direct child of the repository's
   `data/work/integration/` is allowed. Symlinks, Windows reparse points/junctions,
   and hardlinked output files are rejected. Paths with `..` are rejected.
   Inputs are read only. Do not run a concurrent writer against this directory
   or the inputs: checks protect ordinary local operation, not an adversarial
   process racing filesystem changes.
5. Review `integration-report.json`, both repeat folders and logs. On failure,
   preserve the entire run and investigate; retry with a new run ID. For an
   `AUTOMATED_PASS`, perform QGIS 2D/3D checks against the **new** Standard and
   adapter outputs, recording screenshots/project and reviewer findings locally.
   A separate reviewed integration acceptance record is needed to declare the
   new run accepted. Existing A1/A2/A3 acceptance records remain unchanged.

A1 alone invokes GIS Python as an isolated child. A2 and A3 use OUEM Python;
no VoxCity execution occurs in QGIS Python. Cloud tests use synthetic inputs
and a mocked A1 GIS stage, including a small actual pinned-VoxCity A3 execution.
They do not establish local Windows GIS or Komae real-data acceptance.

### Preconditions and intentionally conservative checks

- VoxCity must be version 1.7.0 at the existing pinned Git commit. The runner
  requires non-editable PEP 610 `direct_url.json` VCS provenance matching that
  upstream and commit, verifies installed Python source hashes against RECORD,
  and checks that the imported module is not shadowed. Missing metadata, an
  editable checkout, a wrong pin, or altered source blocks execution. This
  establishes recorded installation provenance and local integrity, **not** an
  independent byte comparison with the upstream Git tree. The method and its
  limitation are included in the report; unverified installs are never passed.
- Native Terrain is revalidated using the existing loader. Source-declared or
  verified T.P. must be compatible with Building Z. A1/A2 quality and input
  hashes must pass before A3 consumes the newly generated Standards.
- The configured study-area rectangle controls Building selection. The actual
  VoxCity rectangle is the normalized complete-building footprint bounds in
  EPSG:4326. These can differ. The runner does not pass the current adapter's
  `--aoi` option, which does not control its grid construction.
- RAW and Standard DEM must cover the conservative EPSG:6677 envelope of the
  actual VoxCity rectangle, transformed with densified edges. Every intersecting
  cell must be unmasked and finite. This can reject a boundary case previously
  processed using implicit outside coverage/filling. It never silently clips,
  fills, resamples, or relaxes the condition. Investigate a blocked run separately.

### Evidence and report v0.1

Outputs are local ignored files under the new run directory:

```text
data/work/integration/<run-id>/
  integration-report.json
  logs/                         # combined stdout/stderr per child process
  repeat-1/                     # independent A1 -> A2 -> A3 outputs
    building.gpkg
    building.gpkg.manifest.json
    terrain.tif
    terrain.tif.manifest.json
    adapter.geojson
    adapter.geojson.manifest.json
    a3-report.json
    arrays.json
  repeat-2/
    ...
```

The existing A3 runner accepts optional `--array-evidence PATH`. This writes a
separate `ouem-voxcity-array-evidence/v0.1` JSON without changing its existing
report fields or quality thresholds. `first` and `second` contain DEM, heights,
segments, IDs and voxel fingerprints, each with `dtype`, `shape`, `encoding`,
and `sha256`. Numeric arrays use C-order bytes; object segment grids use
row-major semantic segment JSON, never object-pointer bytes. Full voxel arrays
are not persisted.

The integration report schema is `ouem-komae-integration/v0.1`:

| Field | Meaning |
| --- | --- |
| `run_id`, timestamps, `status` | New demonstration identity and execution state |
| `environment` | OUEM commit/working-tree state, Python/platform/package versions, VoxCity provenance, selected GIS executables; GIS version output is in its stage log |
| `settings` | Study-area ID/extent, mesh size, expected counts, exactly two repeats |
| `inputs` | Paths/resolved paths, sizes and SHA-256 of source data, manifests, settings, optional Native receipt, pyproject, A3 runner and OUEM Python sources |
| `stages` | Commands, start/end, exit code, status and log path; no snapshot environment dump |
| `repeats` | Per-stage quality checks, actual coverage, protected A3 Standard-input fingerprints, internal determinism and comparison evidence |
| `comparisons` | Independent-repeat content equality by artifact type |
| `input_integrity` | Input/configuration/manifest before/after checks, including Standards consumed by A3 |
| `environment_integrity` | Python, platform, OUEM commit, dependency versions and VoxCity source/provenance equality checked between stages and at completion |
| `artifacts` | Run-relative keys use `/` on every OS; values record paths, sizes, SHA-256 for outputs, manifests, logs and partial files; excludes the report itself to avoid self-hashing |
| `quality`, `reproducibility` | Separate `PASS`, `FAIL`, or `NOT_COMPLETED` decisions |
| `acceptance`, `not_performed` | Local visual/formal acceptance remains pending; nationwide/Phase B validation is not performed |

Checkpoints precede child execution. Caught failures and Ctrl+C/SIGTERM retain
partial outputs/logs and finalize evidence; active child process groups are
stopped. Power loss, SIGKILL, or unsafe filesystem substitution can leave the
last checkpoint marked RUNNING. Such a run is incomplete, never a PASS, and
must not be reused. If output safety cannot be established, the runner refuses
to follow links merely to write a final report.
Report JSON is serialized before creating an exclusive, uniquely named
`integration-report-*.json.tmp` file in the run directory. The writer is closed
before replacement. Windows replacement errors 5/32/33 allow five total attempts
(four retries, 0.75 seconds total backoff), with output-tree and candidate-identity
checks before every attempt. Persistent or other errors remain failures.
Failed/partial candidates and older temporary files are retained as evidence;
they are never unconditionally removed or reused. A later safe save uses a new
candidate. Only `integration-report.json` is the committed checkpoint; retained
candidates do not establish acceptance. Persistent locking can leave that
checkpoint stale even when a newer candidate contains completed verdicts.
If finalization fails, the process exits nonzero and prints `REPORT_SAVE_FAILED`,
never an automated success for the stale checkpoint.
If link creation fails before substitution (for example, Windows WinError 1314),
the output tree remains safe and the ordinary failure is finalized as FAILED.
Synthetic symlink tests probe privileges before execution and skip only for
WinError 1314. Hardlink, traversal and simulated reparse-point checks still run;
Linux symlink protection tests remain enabled.
The output-substitution test prepares its actual file link before starting the
runner, so a directory-symlink probe cannot conceal a file-symlink permission
failure. Only symlink creation with WinError 1314 is skipped; hardlink creation
errors remain test failures. Once the link is prepared, replacement and output
protection failures are never converted to skips.

### Equality versus quality

- Standard Building equality compares CRS, sorted IDs, exact attributes and
  normalized XYZ WKB. GeoPackage byte hashes are retained for lineage but are
  not required to match between repeats (container metadata can differ).
- Standard Terrain requires both file SHA-256 equality and equality of CRS,
  grid, dtype, NoData, mask and valid-elevation content.
- Adapter GeoJSON bytes and the explicit semantic manifest fields must match
  between repeats. Paths and GPKG container hashes remain in the original
  manifests and lineage checks but are excluded from semantic equality.
- Grid/voxel dtype, shape and content fingerprints must match internally and
  between repeats. Existing A3 internal serialization checks also remain required.
- Quality independently requires expected Building counts and canonical ID set,
  A1 Z delta <= 1e-9 m, A2 preservation, valid 2D adapter footprints and IDs,
  A3 absolute invariant error <= 1e-7 m, roof error <= 2 * mesh size, and all
  existing A3 preservation/vertical flags. The existing overlap-aware roof
  envelope calculation is unchanged; generic building voxels are not assigned
  to individual buildings through last-wins IDs.

`AUTOMATED_PASS` requires both quality and reproducibility PASS and unchanged
inputs. `BLOCKED` means a prerequisite was not established; `FAILED` means an
execution/check failed; `INTERRUPTED` means a caught interruption. All outcomes
retain `acceptance: PENDING_LOCAL_REVIEW`. Contract maturity stays PROVISIONAL.
Past Komae acceptance numbers are not substituted for this run's measurements.
