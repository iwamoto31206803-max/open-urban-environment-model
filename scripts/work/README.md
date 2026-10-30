# Windows local acceptance helpers

Files in this directory are temporary, user-facing operational helpers for
local experiments and acceptance runs. Stable reusable logic belongs under
`src/ouem`, and accepted conclusions belong under `docs`.

For the current configured B1/GIS path, start at the
[B1 technical closeout](../../docs/status/B1_TECHNICAL_MILESTONE_CLOSEOUT.md).
The accepted-path and historical diagnostics below retain their separate scope.

## Navigation for current use

Choose the entry matching the intended task and its prerequisites; the links
do not authorize new runs or replace the conditions in the owning procedure.

| Task | Entry |
|---|---|
| Select the OUEM or separate GIS runtime | [Runtime boundary](#runtime-boundary), [runtime architecture](../../docs/architecture.md) |
| Use prepared inputs for configured B1 Voxel / Solar | [Voxel configuration procedure](../../docs/experiments/real_komae_voxel/README.md#configurable-reuse-v02-phase-2), [Solar configuration procedure](../../docs/experiments/real_komae_solar/README.md#configurable-reuse) |
| Inspect saved B1 GIS outputs | [Solar QML / manifest](../../docs/experiments/real_komae_solar/README.md#qml--manifest-visualization), [exact-cell display helpers](../../docs/experiments/real_komae_solar/README.md#gis-display-compatibility-and-exact-lookup), [QGZ generation](../../docs/experiments/real_komae_solar/README.md#qgz-project-generation) |
| Use saved Current Voxel for the bounded B2 CPU workflow | [B2 usage](../../docs/experiments/b2_gvi/README.md), [B2 Technical Closeout](../../docs/status/B2_TECHNICAL_MILESTONE_CLOSEOUT.md) |
| Diagnose saved Building geometry | [Tall-building diagnosis](#diagnose-unusually-tall-komae-adapter-buildings), [CityGML vertical trace](#trace-a-buildings-vertical-coordinates-from-citygml), [saved B1 observer/geometry diagnostics](../../docs/experiments/real_komae_solar/B1_GEOMETRY_OBSERVER_PHASE2.md) |

### Accepted-path procedures and experiment records

The following sections retain their original scope, commands and evidence.
Dated results describe those executions; consult the
[B1](../../docs/status/B1_TECHNICAL_MILESTONE_CLOSEOUT.md) /
[B2](../../docs/status/B2_TECHNICAL_MILESTONE_CLOSEOUT.md) closeouts for milestone
status and their linked backlogs for unverified science. These procedures are
not deprecated by this navigation.

- [Komae PLATEAU acceptance workflow](#komae-plateau-acceptance-workflow),
  [manual QGIS acceptance](#manual-qgis-acceptance),
  [Native to Standard Building](#native-to-standard-building-acceptance),
  [Terrain local acceptance](#komae-terrain-local-acceptance).
- [Isolated A1/A2/A3 integration](#isolated-komae-a1a2a3-integration-demonstration),
  [opt-in canopy PoC](#meta-chm-canopy-scenario-poc-opt-in),
  [saved-canopy QGIS review](#qgis-review-of-a-saved-canopy-run).
- [Adapter failure diagnosis](#read-only-adapter-content-failure-diagnosis),
  [geometry provenance](#read-only-geometry-provenance-diagnosis),
  [intermediate geometry](#read-only-adapter-intermediate-geometry-diagnosis),
  [memory-only CRS candidate](#memory-only-crs-repair-candidate-evaluation).
- [Contained E2E PoC](#opt-in-92-building-contained-e2e-poc),
  [read-only preflight](#read-only-preflight-before-authorizing-a-real-data-run),
  [recorded evidence/report](#evidence-and-report-v01).

See the [repository documentation guide](../../README.md#documentation-guide)
for design/contracts, execution evidence, status, backlog, planning and existing
Acceptance owners. This runbook owns local operational instructions.

## Runtime boundary

The Komae workflow keeps two independently managed runtimes:

- **QGIS/OSGeo4W** owns GDAL/OGR, `osgeo`, and future native tools such as
  PDAL.
- Repository-local **`.venv`** owns OUEM orchestration and portable Python.

OUEM is not installed into QGIS Python, and `osgeo` is not installed into the
OUEM venv. Never start `.venv\Scripts\python.exe` from OSGeo4W Shell. GIS
Python is used only as a child-process worker through a file/argument contract.

### Diagnose unusually tall Komae Adapter buildings

From the repository root in an ordinary Windows cmd terminal:

```cmd
scripts\work\diagnose_komae_building_heights.cmd komae-canopy-002
```

The helper only reads the saved integration run and its recorded RAW, Native,
and Standard Terrain inputs. It replays pinned VoxCity 1.7.0 DEM sampling and
building ID rasterization **in memory**, checking both against saved A3 array
hashes; it does not regenerate Adapter, voxels, or formal artifacts. A new
`data/work/dem-height-diagnostics/<run-id>-<unique-id>/` contains
`diagnosis.json` (all building records and raster statistics) and `summary.md`
(buildings at least 39 m and cause classification). `CONFIRMED` identifies a
verified processing mechanism, `LIKELY` flags evidence requiring inspection,
and `UNRESOLVED` requires more data. None establishes roof truth or changes
acceptance. Do not place local data or diagnostic outputs in Git.

### Trace a building's vertical coordinates from CityGML

For a saved run containing the target building, run from the repository root
in an ordinary Windows terminal:

```cmd
.venv\Scripts\python.exe -m ouem.komae_vertical_provenance komae-canopy-002 bldg_5f2d3f6c --citygml data\raw\building\plateau_komae\53393465_bldg_6697_op.gml --output-base data\work\vertical-diagnostics
```

This read-only diagnosis resolves a unique Standard `source_id` prefix and
matches it to the PLATEAU `gml:id`. It compares **all** CityGML vertex Z values
with the recorded Converter, Native and two Standard/Adapter repeats, plus a
few representative buildings. The new output directory contains
`diagnosis.json` and `summary.md`. For DEM NoData/zero-cell replay, run the
building-height diagnostic above against the same run. See the
[vertical-geometry investigation](../../docs/research/OUEM_Komae_Building_Vertical_Geometry_Diagnosis.md)
for evidence limits and interpretation. The target must appear in the supplied
CityGML tile and have consistent saved repeats. Optional representatives from
other tiles are marked `NOT_CHECKED` with a reason; they do not change a
complete target's exit code. `transition_status` reports observed numerical Z
changes, while `root_cause_status` remains `UNRESOLVED` until comparable
source/Converter coordinates and settings establish the mechanism. Different
vertex counts or sorted-Z hashes alone do not prove an incorrect vertical
transform. No original run or accepted input is modified.

If that strict command blocks on a saved GeoPackage size/SHA-256 mismatch, keep
the run untouched and use the separate **exploratory** diagnosis from ordinary
Windows cmd:

```cmd
scripts\work\diagnose_komae_vertical_exploratory.cmd komae-canopy-002 bldg_5f2d3f6c
```

The launcher uses the canonical local CityGML path. Only if that file has
moved, use the module's optional `--citygml PATH`. It does not rerun A1/A2/A3
or write into the saved run. It creates a new
`data/work/vertical-exploratory/<run-id>-<unique-id>/` containing
`diagnosis.json` and `summary.txt`. The console summary lists every inspected
byte mismatch, full-A1 XYZ/core-field comparison against the saved report and
the other repeat, stage Z ranges, and the first observed numerical change.
Matching geometry semantics cannot establish that an added `z_min` field was
the only modification. Root cause and formal provenance remain unresolved;
the original strict and acceptance workflows still block on altered bytes.
If the Converter path recorded in the Native Building manifest is missing,
this exploratory command checks the canonical
`data/work/building/plateau_komae/53393465_bldg_6697_op_convert.gpkg`
instead. It reads that candidate only when its SHA-256 matches the manifest;
a mismatch, missing candidate, or any `.gpkg-wal`/`.gpkg-shm` sidecar blocks
diagnosis. Close all GIS/SQLite users and investigate leftover sidecars;
the command never deletes or checkpoints them. The report labels a verified
path relocation separately from formal run provenance.
The CityGML reader collects 3D coordinates from nested surface members and
polygon exterior/interior rings. If a target surface uses an unresolved XLink,
an ambiguous dimension, or unsupported coordinates, it reports CityGML as
`NOT_CHECKED` and continues the Converter → Native → Standard → Adapter trace
as `PARTIAL_EXPLORATORY`. That partial result cannot locate a transition from
CityGML to Converter or establish the cause of the height anomaly.

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

The current Komae source is Tokyo Digital Twin **Tama** ground grid (0.50 m),
tile `09LD3451`; see the [dated source correction](../../docs/acceptance/OUEM_A2_Terrain_Source_Provenance_Correction_20261026.md).
The historical `tokyo_23ku_dem_050m` path and 2026-10-06 invocation remain in
the frozen A2 record; do not move old data or overwrite old manifests.

Install the package (including Rasterio) in the repository venv and use an
ordinary Windows terminal, not OSGeo4W Shell. First read the licence/terms in
the [acquisition procedure](../../docs/Terrain_Acquisition_PoC_v0.1.md).
Acquire Raw using a **new** Tama run directory (example identifiers must be
changed if already used):

```bat
.venv\Scripts\python.exe -m ouem.acquire.tokyo_tama_dem --raw-dir data/raw/terrain/tokyo_tama_dem_050m/komae/new-acquisition-01
```

Require a COMPLETED acquisition manifest, matching ZIP/TIFF hashes, no FAILED
record and no staging residue. These are operator checks: the current helper
does **not** read PR #66's acquisition manifest, check its COMPLETED status, or
compare the hashes recorded there with the ZIP/TIFF files. The helper's own
input checks only enforce the pinned A2 original TIFF hash and tile metadata;
they do not establish acquisition-manifest integrity or a completed acquisition
run. Acquisition does not register Native, generate Standard or grant acceptance.
Run **read-only preflight** with explicit input and a **new output directory**:

```bat
scripts\work\terrain_komae_local_acceptance.cmd "data\raw\terrain\tokyo_tama_dem_050m\komae\new-acquisition-01\09LD3451.tif" --run-dir "data\work\terrain-local-acceptance\new-rerun-01" --check
```

`--check` prints checked source hash, raster metadata, Tama source-declared T.P.
evidence and planned command arguments. It creates no output directories/files,
runs no tests and performs no Native/Standard processing. No-argument/old
one-argument invocation now fails with usage: this intentional change avoids
silently overwriting historical Native/Standard outputs. No source is auto-discovered.
Both relative paths resolve from the repository root when using the CMD launcher.

For a separately authorized future local generation, run the same command
**without `--check`**. The helper runs the full automated tests, rechecks source
identity, exclusively reserves the new output directory, calls the unchanged
Native CLI to write `native.json`, then the unchanged Standard CLI to write
`standard.tif` and `standard.tif.manifest.json`. No existing output directory,
even empty, is reused. Failed processing may leave partial results in that new
run; inspect and retain it, and choose a fresh directory for retry. This is a
single-writer local workflow, not an atomic transaction or protection against
hostile concurrent modification. The helper uses fixed, corrected Tama evidence
for this hash-pinned original; it is not a general provider/vertical override.

The printed command plan also supports separate Native and Standard CLI stages.
Native registration records Raw path/hash and provenance without copying Raw;
Standard generation consumes that manifest. Neither command's success creates
a formal acceptance decision. A later reviewer must examine the new manifests,
output hashes, grid/elevation validation and environment in a separate record.
`PROCESSING_COMPLETED_PENDING_REVIEW` means **only that the Native and Standard
CLI subprocesses exited successfully**. Those CLIs perform their existing
internal checks; the helper does not independently reopen/validate the outputs,
check output-file existence/hashes after their exit, or grant formal acceptance.

At the next formal re-acceptance, independently verify the acquisition manifest's
COMPLETED status and absence of FAILED/staging residue, compare its ZIP/TIFF
hashes with the retained files, and trace the Raw TIFF hash through the Native
manifest and Standard manifest's source identity. Match the Standard manifest's
output hash to the actual Standard TIFF, independently inspect grid/elevation
preservation and corrected source provenance, and compare with the historical
accepted baseline. Record any differences and the review/acceptance decision in
a new record. These cross-stage checks are a future re-acceptance procedure,
**not implemented by the current helper**; this PR adds no acceptance automation.

The Standard summary reports paths, dimensions,
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

### Meta CHM canopy scenario PoC (opt-in)

After review/merge, prepare a developer-local Meta CHM GeoTIFF and an adjacent
`<filename>.tif.provenance.json` in an ordinary Windows environment. The JSON
must identify the exact raster hash and cite an explicit source statement that
pixel values are canopy height **above local ground in metres**; a filename or
unstated assumption is insufficient. Example structure (replace every example
value with verified provenance and the actual file SHA-256):

```json
{"schema":"ouem-meta-chm-provenance/v0.1","raster_sha256":"<actual SHA-256>","height_semantics":"height_above_ground_m","evidence":{"source":"<Meta CHM release>","citation":"<source document/URL>","height_statement":"<source's explicit ground-relative metres statement>"}}
```

The TIFF must have one band, a declared CRS and invertible transform; pixel
spacing at the first target centre must be finite, positive and at most 2 m
for this 1 m PoC. Its
targeted grid cells must cover every VoxCity cell centre, have finite,
nonnegative heights, and contain no NoData. Source pixel size and transform
are recorded. Resampling is deterministic nearest-neighbour at the actual
VoxCity `uv_m`/south-up cell centres (including rotated rectangles). A source
NoData/uncovered cell **blocks** the run with counts; it is never silently
treated as bare ground. DEM cells must be finite and free of Standard NoData.
Values below 3.0 m become no-canopy (top and bottom zero); otherwise top is
CHM height and bottom is `0.4 × top`, without adding DEM elevation. Existing
building overlap is retained for VoxCity to resolve.

From an ordinary Windows cmd, not OSGeo4W Shell, run with a fresh ID and the
explicit local CHM path (quote paths with spaces):

```bat
scripts\work\run_komae_meta_chm_e2e.cmd komae-canopy-001 "D:\local-data\meta-chm\komae.tif"
```

The launcher uses repository `.venv\Scripts\python.exe`, canonical Komae
Native/Standard inputs, the accepted study-area configuration, 1 m mesh, and
the two-repeat contained 92-building integration runner. Relative CHM paths
are resolved from the repository root; the adjacent provenance file is required.
Run IDs are new, portable names; existing runs are never resumed or overwritten.
Each `data\work\integration\<run-id>\repeat-N\` contains
`current-voxels.npy`, `no-canopy-voxels.npy` and `canopy-report.json`, in
addition to existing A1/A2/A3 outputs. `integration-report.json` links the
input hashes, per-repeat canopy checks and cross-repeat comparison. The canopy
report records CRS/transform/pixel size, coverage, NoData policy, threshold,
array hashes, tree/building voxel counts and deterministic results.

`AUTOMATED_PASS` requires existing A1/A2/A3 quality, complete CHM/DEM input
validation, preserved component arrays and building occupancy, tree voxels
where canopy is present, no tree voxels in No-Canopy, and matching scenario
results across repeats. Failure retains isolated run evidence. The report
keeps `acceptance=PENDING_LOCAL_REVIEW`; company-PC execution and review are
still required. The 92-building scope excludes 19 boundary-crossing buildings.
No CHM accuracy, crown-base estimate, shade/solar/green-view performance or
nationwide applicability is established. Those, and a future treatment of
source NoData, remain separate work.

### QGIS review of a saved canopy run

From the repository root in an ordinary Windows cmd terminal after the local
E2E has finished:

```cmd
scripts\work\export_komae_canopy_qgis.cmd komae-canopy-002
```

The launcher also works from another working directory when invoked by its
full path.

The launcher uses repository `.venv\Scripts\python.exe`. It reads the two
saved Current and No-Canopy voxel arrays, their SHA-256 evidence, the Adapter
grid rectangle, and the Standard DEM. It reconstructs **only** the A3 DEM
sampling grid to verify its saved hash and minimum elevation; it does not run
A1/A2/A3 or CHM conversion. The output is a new, independent
`data/work/canopy-qgis/<run-id>-<unique-id>/` directory. Existing runs and
acceptance evidence remain untouched. Any mismatch blocks export.

Open `canopy-qgis.gpkg` in QGIS and add its `canopy_occupancy`,
`canopy_3d_spans`, and `adapter_buildings` layers (EPSG:6677). Add the saved
`data/work/integration/<run-id>/repeat-1/terrain.tif` as terrain. In 2D,
check that tree cells align with the terrain/study area and that building
footprints occupy the expected locations. The occupancy layer is an exact
union of occupied grid cells, including cells overlapping buildings; visible
tree voxels may be absent where building voxels took priority.

For QGIS 3D View, set the saved `terrain.tif` as project terrain. Render
`canopy_3d_spans` from its PolygonZ **absolute** elevation (`base_m`) and
extrude by `height_m`; do not add terrain elevation to its geometry Z again.
Render `adapter_buildings` as a separate layer placed relative to the terrain
surface and extruded by `height_m`. Its 2D footprints and heights are
comparison context, not an exact per-voxel reconstruction of building roofs.
The span features merge adjacent cells sharing the same consecutive voxel-level
interval, without deleting occupied cells. `base_m` and `top_m`
are voxel lower/upper faces: saved A3 DEM minimum + `k_start`/`k_end` times
the mesh size. These are VoxCity grid levels, not original CHM heights. The
display in QGIS 4.2 has not yet been verified on the company PC.

Review `export-report.json` first. Export PASS requires saved hash integrity,
matching repeat arrays, correct uv_m orientation/cell centres, DEM hash,
tree cell/voxel counts, unchanged building occupancy, and Current/No-Canopy
differences confined to tree voxels. For local acceptance, additionally check
2D placement and 3D ground/canopy/building relationships in QGIS. Record
PASS or FAIL, date, run ID, output report SHA-256, QGIS observations and any
screenshots in a **new** local review record. A discrepancy is FAIL or needs
further investigation; do not change the saved integration report. Export
does not update `acceptance=PENDING_LOCAL_REVIEW` or establish CHM accuracy,
shade/solar/green-view performance or nationwide applicability.

`python -m ouem.komae_integration run` connects the existing Native Building
standardizer, Native Terrain standardizer, and A3 acceptance runner. It runs
all three stages twice in independent folders. It does not rerun CityGML
conversion/Native Building ingest, change Standard contracts, or promote any
output to the accepted baseline. Here A1/A2/A3 are implementation milestones,
not the conceptual national model variants.

### Read-only Adapter content failure diagnosis

The following five tools inspect existing contained-PoC evidence. Use the OUEM
venv from an ordinary Windows terminal, separately from GIS Python. They verify
recorded paths, lineage and hashes before/after reading; unsafe links, changed
bytes and active GeoPackage sidecars block inspection. Close writers; do not
remove sidecars or edit evidence to make checks pass. Recorded commands are
never executed, and no A1/A2/A3 or voxel pipeline is rerun. Inputs, saved runs,
quality criteria and acceptance remain unchanged. Only the final QGIS export
writes files, in a fresh diagnostic directory. Other tools print to stdout;
if retaining it, choose a new review file outside inputs/runs (shell redirection
has no overwrite protection).

```bat
scripts\work\diagnose_komae_adapter_content.cmd komae-contained-001
```

This checks both repeats against the original `adapter_quality()` predicates:
exact CRS, ordered reference IDs, `id == voxcity_id`, heights and 2D footprint
validity. Exit **0** means consistent evidence and both repeats PASS; **1** means
an explained predicate failure; **2** means blocked/incomplete or inconsistent
evidence. It diagnoses failure without changing the saved verdict.
[Historical detail](https://github.com/iwamoto31206803-max/open-urban-environment-model/blob/1f0b9f0a48d86cf4097a846f987cbab14d958235/scripts/work/README.md#L408-L473).

### Read-only geometry provenance diagnosis

```bat
scripts\work\diagnose_komae_geometry_provenance.cmd komae-contained-001
```

Traces both repeats' saved Native → full Standard → contained Standard → Adapter
for one building. Native must resolve at its recorded path; missing/conflicting
lineage is INCONCLUSIVE. EPSG:6677 area/shape comparisons and an XY projection
probe locate the first invalid saved representation, not its proven cause;
raw 3D-surface XY validity differs from footprint validity. Exit **0** means
complete valid lineage; **1** means complete lineage with observed invalidity;
**2** means INCONCLUSIVE/blocked/error. A complete interval can have unresolved cause.
[Historical detail](https://github.com/iwamoto31206803-max/open-urban-environment-model/blob/1f0b9f0a48d86cf4097a846f987cbab14d958235/scripts/work/README.md#L474-L542).

### Read-only Adapter intermediate geometry diagnosis

```bat
scripts\work\diagnose_komae_adapter_geometry_steps.cmd komae-contained-001
```

Replays the target's actual normalization, CRS transformation and JSON geometry
steps in memory for both repeats. A thread-local profiler observes existing
operations without replacement; an existing profiler is not displaced. All saved
footprint statistics and final WKB must match exactly, or results are INCONCLUSIVE.
No new repair or rounding is introduced. Exit **0** means faithful replay without
a valid→invalid transition; **1** means a reproduced transition; **2** means
INCONCLUSIVE/blocked. This is geometry fidelity, not whole-feature/voxel quality.
[Historical detail](https://github.com/iwamoto31206803-max/open-urban-environment-model/blob/1f0b9f0a48d86cf4097a846f987cbab14d958235/scripts/work/README.md#L543-L620).

### Memory-only CRS repair candidate evaluation

```bat
scripts\work\evaluate_komae_adapter_crs_repairs.cmd komae-contained-001
```

Requires exact baseline geometry/statistic replay over both full 92-building
repeats before memory-only A–D comparisons: conditional post-CRS `make_valid`,
source repeated-point removal, post-CRS rounding, and source-edge densification.
Only invalid baseline CRS outputs may change; already-valid buildings remain
exact. Empty/nonpolygonal/invalid results are rejected; components are never
silently discarded. Structural changes require review; small deformation or
Pareto inclusion is not approval. Ground/roof/voxel consistency needs subsequent
validation. Exit **0** means a complete repeatable evaluation (`EVALUATED`),
not an approved repair; **2** means INCONCLUSIVE/blocked. Parameter values,
measurements and candidate-screening rules remain in the
[historical detail](https://github.com/iwamoto31206803-max/open-urban-environment-model/blob/1f0b9f0a48d86cf4097a846f987cbab14d958235/scripts/work/README.md#L621-L719).

For these four tools, the Python equivalent is
`.venv\Scripts\python.exe -B -m MODULE RUN-ID [OUEM-ID] --json` from the repository
root. Modules, in section order: `ouem.komae_adapter_diagnostics`,
`ouem.komae_geometry_provenance`, `ouem.komae_adapter_geometry_steps`,
`ouem.komae_crs_repair_evaluation`. Omit `[OUEM-ID]` entirely for the first tool;
the other three accept an optional second positional argument (also in CMD),
defaulting to `oub-21a29be1-9794-593f-b22c-e3639a7d9d45`. `--json` selects full
JSON stdout and is a Python-only option. Run IDs identify existing directories
under `data/work/integration/`, not arbitrary paths. No output-file option exists.

### Export Candidate A for QGIS inspection

```bat
scripts\work\export_komae_adapter_repair_qgis.cmd komae-contained-001
```

Accepts the same optional OUEM ID/default. Python equivalent:
`.venv\Scripts\python.exe -B -m ouem.komae_repair_qgis_export RUN-ID [OUEM-ID]`
(no `--json`). Requires both baseline repeats and Candidate A geometry/attributes
to reproduce the current evaluator exactly, with source hashes unchanged.
Nonpolygonal output blocks export; no components are dropped. It creates a fresh
directory under `data/work/diagnostics/adapter-repair/` and prints the GeoPackage
path, Polygon areas and `inspection.json` path. Exit **0** means exported for
inspection; **2** means blocked/error. Failed partial output is retained.

Open `adapter_before`, `candidate_a`, `candidate_a_parts` and `self_intersection`
in QGIS. The last layer is omitted if GEOS provides no approximate location.
Review part areas/positions; original properties are in `properties_json`, with
ID/height columns and 1-based part indices. No production repair, downstream
voxel-quality recheck or formal acceptance is performed. Historical PR #42 JSON
is not an input. [Historical detail](https://github.com/iwamoto31206803-max/open-urban-environment-model/blob/1f0b9f0a48d86cf4097a846f987cbab14d958235/scripts/work/README.md#L720-L756).

### Opt-in 92-building contained E2E PoC

For the post-CRS repair rerun **after review and merge**, use a fresh ID on the
company Windows PC (the command works from any working directory):

```bat
scripts\work\run_komae_contained_e2e.cmd komae-contained-repair-001
```

The launcher uses the repository `.venv` and canonical Komae inputs, refuses
existing or unsafe run IDs, and displays
`data\work\integration\<new-run-id>\integration-report.json` when written.
Do not reuse `komae-contained-001`. The report now checks that exactly the known
OUEM building was repaired, retains projected-area, symmetric-difference and
Hausdorff diagnostics for review, and compares repair evidence across both
repeats. Automated checks do not constitute local real-data acceptance; inspect
the report, logs and repaired geometry before any acceptance decision.

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

For the separate read-only reference DEM coverage diagnostic, run from the
**repository root** in an ordinary Windows terminal (the former CMD shortcut
has been removed):

```bat
.venv\Scripts\python.exe -B scripts\work\diagnose_komae_dem_coverage.py
```

It takes no arguments and reads the canonical Standard Building, Native Terrain
manifest/its Raw DEM, and study-area configuration. JSON goes to stdout; no files
are written. It reports boundary classes and coverage shortfalls, not NoData or
actual engine-output validation. Exceptions exit nonzero; completion is not acceptance.

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
