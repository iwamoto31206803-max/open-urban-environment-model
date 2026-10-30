# Komae A/B CPU view-index Technical E2E

Experimental entry point: [`ouem.b2_gvi`](../../../src/ouem/b2_gvi.py).
This consumes **completed configured B1 runs**, including the saved Current 3D
array, receipt, reports, centres, grid and masks. It does not construct a new
model or call Solar. Read the [Phase 3 results](RESULTS.md),
[CPU characterization](B2_CPU_GVI_Synthetic_Characterization_v0.1.md),
[audit](../../planning/OUEM_B2_VoxCity_GVI_API_Audit_v0.1.md) and
[deferred backlog](../../planning/OUEM_B2_Deferred_Validation_Backlog.md).

The authorized provisional name is **CPU weighted first-TREE view index**.
It is dimensionless, not photograph-based green-view fraction, whole-crown
transmission integration or scientifically validated GVI.

## Runtime and commands

Use ordinary Windows PowerShell and the OUEM `.venv`; keep existing QGIS Python
separate. VoxCity 1.7.0 remains pinned to
`fa212656305328a9a657973bae26f352bfe813bc`. No new dependencies.

Create an output parent under ignored `data/work/`; every command requires a
**new output directory outside the B1 Run**, with no overwrite or resume.
Actual 2026-10-30 paths below are local evidence, not data supplied by Git.

```powershell
$source = 'data/work/shared-vertical-domain/phase3c-20261029-01/outputs'
$out = 'data/work/b2-gvi-phase3-20261030-01'
# Repeat per site ('a' then 'b'), using distinct outputs:
$site = 'a'
.venv/Scripts/python.exe -m ouem.b2_gvi --run-root "$source/komae-$site-3c-20261029-01" --output "$out/benchmark-$site" --benchmark
.venv/Scripts/python.exe -m ouem.b2_gvi --run-root "$source/komae-$site-3c-20261029-01" --output "$out/$site" --benchmark-report "$out/benchmark-$site/report.json"
```

The CLI fixes mode=None, TREE-only targets=(-2,), inclusion=True,
fast_path=False, k=0.5, LAD=1.0, height=1.5 m, grid 120×20 directions,
elevation −30 to +30 degrees, roofs=False and OBJ off. Only CPU thread count
(`--threads`, default 2, supported 1–8) is exposed. It does not silently reduce
ray counts or scene extent. Matplotlib uses Agg and closes only new figures.

The benchmark calls the same public API twice on a 16×16 (or smaller synthetic)
subset. Its values are **only a cost probe**, never evaluation evidence: cropped
domain exits bias visibility. The heuristic scales repeat cost by observer count
and XY diameter, adds first-call overhead and records its assumptions. A matching
successful receipt, fixed settings and Current hash are required for a full run.
The resource guard uses estimated 600 seconds/site and observed process RSS below
2 GiB as local feasibility limits, not accuracy criteria or a runtime guarantee.
An unsuccessful probe stops full execution; do not bypass it by changing sampling.

## Inputs, outputs and checks

The reader reuses `gis_visualization.inspect_run` **only as a saved completed-B1
handoff reader**, then additionally checks all delivered output hashes, Current
dtype/shape/classes, TREE/control occupancy, ground finiteness, independent GVI
surface selection, origin capacity/classes and original file inventory. It also
hash-checks the five frozen configuration input bindings (study area and
Building/Terrain/Envelope input identities). This does not replay the fresh
Consumer or revalidate every upstream Raw file, nor authenticate the producer.
Read-only memmaps and before/after byte hashes protect the arrays.

The **entire saved context domain** enters `get_view_index` first. The saved
centre-based rectangular evaluation mask is extracted only afterward. For these
A/B runs, full arrays are 128×128 and the evaluation ROI is **64×64**, u/v
`[32:96,32:96]`, surrounded by 32 m context. The request's description of a
128×128 evaluation ROI did not match the actual runs. The implementation retains
their existing geometry and delivers both full-domain and saved-ROI rasters.
It cannot supply a new 128×128 ROI with additional exterior context from these
inputs; that would require a separately scoped input/extent change.

Each full output directory contains:

| File | Meaning |
|---|---|
| `view_index.npy`, `view_index.tif` | Full-domain UV values / geographic Float64 raster |
| `evaluation_view_index.npy`, `.tif` | Saved ROI extracted after full computation |
| `observer_valid.npy`, `.tif` | Independently checked valid observation columns |
| `roi_mask.npy`, `.tif` | Saved evaluation membership; remaining cells are context |
| `observer_index_k.npy` | Integer index at selected columns; −1 for invalid columns |
| `settings.json`, `preflight.json`, `report.json` | Frozen conditions, source identities, grid/D0, resource observations, statistics, output hashes and immutability result |

Failed post-preflight execution leaves `failure.json` and partial files for
diagnosis. A preflight rejection creates no result directory. Finite API masks
must exactly match the independent observer diagnostic; opaque/out-of-Z origins,
unexpected classes/masks or out-of-range scores stop execution, with no clamping
or silent NaN/zero repair. Source canopy missing/outside cells are reported as
uncertainty; no ground filling or fabricated canopy is introduced.

GeoTIFFs keep the existing B1 **EPSG:4326 rotated geographic affine** at actual
saved centres. In full rasters `row=nu-1-u`, `col=v`; the ROI affine translates
the full raster by `(v0, nu-u1)`. No analytical reprojection/resampling occurs.
Float NaN is declared NoData; finite zero remains valid. Masks use uint8 0/1
without declaring zero NoData. Every write is reopened and checked for CRS,
affine, shape, values and validity mask. The full affine is checked against
existing B1 GeoTIFFs, not inferred from a projected north-up square.

## QGIS

[`b2_gvi_qgis.py`](../../../src/ouem/b2_gvi_qgis.py) is a separate existing-GIS-
Python script. It reads B2 reports and hashes, not the Solar seven-layer manifest.

```powershell
$gisPython = 'C:/Users/iwahi/AppData/Local/Programs/OSGeo4W/bin/python-qgis.bat'
& $gisPython src/ouem/b2_gvi_qgis.py --reports "$out/a/report.json" "$out/b/report.json" --output "$out/qgis"
& $gisPython src/ouem/b2_gvi_qgis.py --reports "$out/a/report.json" "$out/b/report.json" --verify "$out/qgis/project.qgz"
```

It creates a relative-reference `project.qgz`, a QGIS-rendered `overview.png`,
saved ROI outline GeoJSONs and a receipt. Project CRS=EPSG:6677, data CRS=4326.
Each A/B group has a red saved-ROI outline, gray invalid-observer overlay,
full index (common dimensionless 0–1 viridis scale), and initially hidden ROI
extract. Provider alpha is preserved to avoid opaque rotated-grid fringes.
Both full context domains overlap: toggle a group to inspect that site's result
without another site's context covering it. Their ROI rectangles lie side by side.

Generation checks all GDAL raster cells against reversed-u NPY values and masks.
The separate reopen command checks sources, CRS, raster visibility, ramp/range
and alpha, without saving over the QGZ. GUI observation is a separate check; its
receipt stays NOT_VERIFIED until a separately recorded human/agent display test.
QGZ references the rasters rather than embedding them: retain the relative
directory topology. This helper does not implement a general GIS contract.

For exact original-cell queries, use the existing `gis_display.py lookup` helper
in GIS Python. QGIS provider Identify may query a virtual display grid and is
not the source-cell oracle. Extent/context sufficiency, actual pedestrian
height, source accuracy and backend scientific interpretation remain unresolved.
