# Minimal synthetic source-H VoxCity voxelization

**Experimental**, Step 4B-3, technical integration only. Baseline main
`36942f0dba1f37916a0e3be2015d0c0932e32906` includes merged #94.
Reuses the [synthetic 2.5D Adapter](Source_H_Synthetic_25D_Adapter_v0.1.md),
[Consumer](Source_H_Standard_Consumer_Validation_v0.1.md) and
[Step 4A audit](reviews/OUEM_Source_H_VoxCity_Adapter_Contract_Audit_20261028.md).
Existing source-H processing, Adapter v0.1, Standards and Accepted data are unchanged.

## Actual engine path and input contract

[source_h_synthetic_voxel.py](../src/ouem/adapters/source_h_synthetic_voxel.py)
adds `voxelize_synthetic_source_h(manifest, root, config, *, terrain, synthetic_source_ids)`:

1. Verify installed VoxCity **1.7.0**, distribution direct-URL commit
   `fa212656305328a9a657973bae26f352bfe813bc`.
2. Existing 2.5D Adapter performs fresh Consumer PASS and at-use input binding.
   Same two authored boxes, same IDs and flat synthetic H=10.25m declaration.
3. Call `create_building_height_grid_from_gdf_polygon` with geographic footprints,
   explicit rectangle from the projected domain corners and precise intersection mode.
   Verify both IDs, heights and `[0,height]` segments; no missing/remapped IDs.
4. Create a **new constant DEM on the actual engine grid**. No projected
   diagnostic array is copied, flipped or resampled merely because shapes match.
5. Audit `process_grid(ids, DEM-min(DEM))`; in this flat case it remains all0.
   Land cover is authored Standard Bareland=1, no trees.
6. Execute **`Voxelizer(1.0, "Standard").generate_combined`**, unmodified.
7. Independently compare every actual output cell against scalar rules and
   check Building/ID/footprint/ground correspondence. The oracle is QA after
   execution, never substituted for the generated voxel model.

VoxCity source inspected at the pin / installed source hashes are retained in
local metadata. Actual named call sites:

| Source file under `src/voxcity/` | Function / behavior |
|---|---|
| `geoprocessor/raster/buildings.py:62` | Public building raster entry, returns heights, segment lists, ID grid, filtered GeoDataFrame |
| `geoprocessor/raster/buildings_precise.py` | Precise owned-cell area fraction >0.3 |
| `geoprocessor/raster/core.py` | `compute_grid_geometry`, `compute_cell_center_coords`; grid mapping utility at this pin |
| `geoprocessor/raster/core.py` | `process_grid`, `process_grid_optimized`; per-ID DEM means then minimum subtraction |
| `generator/voxelizer.py:158` | `Voxelizer.generate_combined`; subtract DEM minimum, condition ground, allocate and generate |
| `generator/voxelizer.py:39` | Actual Numba kernel called by the public method; only inspected, never directly invoked/patched by OUEM |
| `utils/orientation.py` | uv_m/SOUTH_UP, axes u/north, v/east, up; voxelizer does not flip |
| `utils/classes.py`, `utils/lc.py` | -3 Building, -2 Tree, -1 ground, positive surface classes; Standard Bareland=1 |

The distribution pin is checked; runtime module SHA-256 values identify actual
installed bytes. This is a bounded dependency on these named APIs/helpers, not
a promise that unpinned future releases behave identically.

## Axes, ground and vertical interpretation

Engine arrays are `[i=u, j=v, k=up]`; i=0 is the southern origin edge and j=0
the western edge for this rectangle. No transpose/flip is applied between
building raster, authored DEM and voxelizer. The geographic affine is explicit:

`lonlat(i,j) = origin + (i+0.5)*du*u_vec + (j+0.5)*dv*v_vec`.

The 64×64 horizontal engine grid is **not** PR #94's EPSG:6677 north-up
diagnostic grid. Tests poison the diagnostic arrays with an incompatible shape,
NaN Terrain and ID999 to prove they are not used. Actual axis0 true azimuth is
**−0.1534627608°**; adjusted horizontal spacings are approximately
**1.000092885 / 1.000092924m**, while voxelizer nominal mesh is1m.
Rectangle, basis vectors, spacings and angle are saved for the next boundary.

Building source H and authored Terrain H share declared EPSG:6695 gravity-related
height in metres. Terrain is authored directly on the engine domain, not a
claim of resampling an accepted DEM. Relative heights remain9.50/14.75m;
Terrain H is not added to those heights before voxelization.

For this case: raw/effective origin **D0=10.25m**, effective DEM=0 everywhere.
Pinned rule `ground_level=int(dem_eff/1+0.5)+1` gives1: surface class1 at k=0.
No -1 subsurface layers remain in a flat minimum-origin scene. Building starts
at k=1. Segment bounds use `int(relative_height/1+0.5)` for these positive values.

Metadata uses **nominal index-edge H=D0+k×1m**, centre H=D0+(k+0.5)×1m.
These are declared lattice interpretation coordinates, **not independently
calibrated physical elevations**. Surface layer shift and rounding are separate:

| Source label / ID | Input roof H | Relative h | Occupied k interval | Layers | Round delta | Nominal top edge H | Top edge minus input roof H |
|---|---:|---:|---|---:|---:|---:|---:|
| synthetic_tokyo /2 |19.75m|9.50m|[1,11)|10|+0.50m|21.25m|+1.50m|
| relocated synthetic_niigata /1 |25.00m|14.75m|[1,16)|15|+0.25m|26.25m|+1.25m|

Both bottom index edges are nominal H11.25m, **not source ground H10.25m**.
The +1m surface layer is retained and reported, not silently removed as an
offset. This is an exact pinned-engine behavior check, not exact roof alignment
or a new coordinate contract for real Building data. Highest Building reaches
the allocated upper boundary; future scene comparisons must review/pad common
Z extents rather than assume an air cap or equal depths across scenarios.

## Reproduce / inspect

From the ordinary OUEM Windows environment (no GIS runtime, download or Converter):

```powershell
.venv\Scripts\python.exe tests/integration/run_source_h_synthetic_voxel_smoke.py --run-dir data/work/source-h-synthetic-voxel/my-new-run
```

The directory must be new. The #94 test-only factory makes small synthetic
Raw/Converter-shaped bytes, then existing Native/Standard processing. Converter
CLI identities are synthetic; no actual Converter execution is claimed.

Local outputs, **not committed or Accepted**:

- `voxel_grid.npy`: actual class array; no Building IDs encoded in it.
- `building_id_grid.npy`, `building_ids.csv`: owner raster + source/OUEM/numeric
  ID mapping; for any -3 cell its Building ID is `id_grid[i,j]`.
- `building_height_grid.npy`, `terrain_H.npy`, `effective_dem.npy`: engine-aligned
  heights and raw/effective ground diagnostics.
- `voxel_metadata.json`: input identities, pin/source hashes, affine, origin,
  classification counts, per-ID QA, execution/implementation identities and output hashes.
- `sections.png`: actual occupancy map and per-Building vertical cuts; `RESULTS.md`.

All five saved arrays are reopened with `allow_pickle=False` and exactly
compared. Inspect in Python with `np.load(..., allow_pickle=False)`; PNG provides
horizontal and vertical diagnostics. This step did not execute QGIS GUI or a
3D renderer. A failed partial demo directory is not a successful artifact;
`RESULTS.md` is written only after successful generation, save/reload and QA.

## Executed results — 2026-10-28

Run identifier `source-h-synthetic-voxel/smoke-20261028-02` under `data/work/`.
Windows Python3.11.9; actual pinned engine with Numba enabled; **3.530s** total.
Array **64×64×16, int8**, 65,536 bytes in memory (NPY65,664 bytes).
Each Building owns96 horizontal cells; ID2 has **960** voxels, ID1 **1,440**.
Totals: Building -3=**2,400**, surface1=**4,096**, air0=**59,040**.
No -1/-2 cells in this specific scene. All array/classification/ground/ID QA PASS.

Owned cell/footprint overlap fractions are all >0.3 (minima approximately
0.496/0.471). No Building code appears in unowned columns or k=0 surface.
Partly occupied boundary cells follow the engine area-intersection rule;
this is not a claim that every voxel lies entirely inside the vector footprint.
All ordered inputs remain unchanged; canonical Standard LoD2 is not rewritten.
The saved array readback and PNG were confirmed; cuts are j=40 and13.

Voxel NPY SHA-256:
`346a5bcc1c649cc3de70674a50cf1a539b6425a7a1edcaf9f0ed8a5f772612f2`.
Implementation SHA at execution:
`917799b6a22c6d0aa1f12918063e26f966805fa2562e5c6a33af5a4744956a46`.
Execution used the baseline HEAD and then-uncommitted code; local metadata
records dirty state/runner hash, not a claim that a later commit was executed.

### Tests actually run

Two new actual-engine integration tests cover both Buildings, exact expected
class/height/ground/ID/position correspondence, unchanged inputs and poisoned
projected diagnostic arrays. Existing Consumer/Native/Standard/2.5D/Adapter v0.1
regressions were included: **295 passed, 1 warning** in 42.41s.
Full `.venv\Scripts\python.exe -m pytest -q -ra`: **862 passed, 5 skipped,
251 warnings** in 204.04s. Skips are existing Windows symlink privilege limits;
warnings are existing Rasterio deprecations plus Consumer ctime diagnostics.
No new skip/xfail or weakened existing assertion. Synthetic tests and this local
engine execution do not constitute real-data or formal acceptance.

## Next minimal shadow boundary and limitations

The pinned CPU entry is `voxcity.simulator.solar.radiation.get_direct_solar_irradiance_map`.
It requires a `VoxCity` object containing the voxel array and mesh metadata,
true sun azimuth/elevation, DNI and an observer policy. Next work must bind
the saved rectangle/rotation (the API reads `extras.rotation_angle`), classes,
ID mask and effective ground; choose an explicit time/sun condition and shared
valid observation mask, review actual ray-origin quantization, and compare
Terrain-only/Building scenes with a common grid/Z extent. No arrays are to be
spliced with the old projected diagnostic grid. No solar call was made here.

Special geometry, sloped/NoData Terrain, overlapping owners, rare filesystem
races, real-data eligibility, scientific accuracy, canopy/observer physics and
formal acceptance are outside this tiny normal-path PoC. No engine patch,
hidden height correction or change to formal Adapter/Standards was made.

source-H eligibility **NOT_ESTABLISHED**; Human Review/Formal Acceptance
**NOT_VERIFIED**; Phase5 A1–A4 **OPEN**.
