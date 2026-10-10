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
| `artifacts` | Paths, sizes, SHA-256 for outputs, manifests, logs and partial files; excludes the report itself to avoid self-hashing |
| `quality`, `reproducibility` | Separate `PASS`, `FAIL`, or `NOT_COMPLETED` decisions |
| `acceptance`, `not_performed` | Local visual/formal acceptance remains pending; nationwide/Phase B validation is not performed |

Checkpoints precede child execution. Caught failures and Ctrl+C/SIGTERM retain
partial outputs/logs and finalize evidence; active child process groups are
stopped. Power loss, SIGKILL, or unsafe filesystem substitution can leave the
last checkpoint marked RUNNING. Such a run is incomplete, never a PASS, and
must not be reused. If output safety cannot be established, the runner refuses
to follow links merely to write a final report.

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
