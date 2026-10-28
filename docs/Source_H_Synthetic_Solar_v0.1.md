# Minimal synthetic Building direct solar / shadow analysis

**Experimental**, Step 4B-4. Baseline main
`9f01631c5c5a06b3dcafa8ead6d210d34aefff23` includes merged #95.
This connects the existing [2.5D](Source_H_Synthetic_25D_Adapter_v0.1.md) and
[voxelization](Source_H_Synthetic_Voxelization_v0.1.md) pipeline to actual CPU
solar calls. No Standard, Adapter, Consumer, Accepted artifact or dependency
was changed. This is not real-data or scientific accuracy acceptance.

## Implementation and audited API

[synthetic_building_solar.py](../src/ouem/synthetic_building_solar.py) provides
`run_synthetic_building_solar(manifest, root, config, *, terrain, synthetic_source_ids)`.
It runs the existing fresh Consumer → 2.5D → pinned actual voxelizer first.
Installed VoxCity **1.7.0**, direct-URL commit
`fa212656305328a9a657973bae26f352bfe813bc` is verified upstream. Runtime source
hashes for the actual solar/orientation/kernel/ray modules are recorded.

Inspected code under pinned `src/voxcity/`:

| File / function | Actual contract used |
|---|---|
| `models.py`, `VoxCity`, `VoxelGrid`, `GridMetadata` | Solar reads voxel classes/meshsize; complete scene also contains BuildingGrid, LandCoverGrid, DemGrid, CanopyGrid, extras |
| `simulator/solar/radiation.py:18`, `get_direct_solar_irradiance_map` | `(VoxCity, azimuth, elevation, DNI, show_plot=False, **kwargs)`; returns horizontal direct W/m² |
| `utils/orientation.py:72`, `direction_to_axis_vector` | Degrees, true north0, clockwise; subtract `extras.rotation_angle` in degrees, output `[u,v,up]` toward the sun |
| `simulator/solar/kernels.py:11`, `compute_direct_solar_irradiance_map_binary` | First air/tree transition above walkable ground; integer view-height offset; roofs excluded → NaN when below is Building |
| `simulator/common/raytracing.py:11`, `trace_ray_generic` | Adds0.5 to origin indices; air allowed, opaque Building blocks; returns transmission along the sun ray |

The module calls **only the public solar entry** for A/B analysis. Kernel/ray
functions are inspected and identified, not called as alternate solvers. Numba
`py_func` is accessed only for source identification, never used to replace JIT
execution. Initial test setup failed after computation when `inspect` was given
a Numba dispatcher; correcting only that source-identification step resolved it.

## Fixed artificial condition and common geometry

Sun azimuth **135° true clockwise**, altitude **35°**, DNI **800W/m²**. No date,
weather observation or annual/time-series meaning. Expected unobstructed
horizontal direct = `800*sin(35°)` = **458.861149080837W/m²**, not800.

The actual engine grid has rotation **−0.1534627608°** from true north.
Solar extras contain that rotation and the exact geographic rectangle. The
direction is checked against an independent elementary trigonometric expression:
`[cos(el)*cos(az-rotation), cos(el)*sin(az-rotation), sin(el)]`.
It points toward the southeast (−u,+v); Building shade lies northwest (+u,−v).

Case B is the actual #95-derived voxel model. Its pre-padding NPY hash matches
`346a5bcc1c649cc3de70674a50cf1a539b6425a7a1edcaf9f0ed8a5f772612f2`.
Case A changes only Building **−3→air0**. Surface1 and all other classes remain
identical. Both cases receive **two identical top air layers**, preserving the
original occupancy and giving the tallest Building air above it. Final shape
**64×64×18**, nominal1m, shared D0/source-ground **H10.25m**. The public objects
have identical normalized/effective DEM0, surface cover1, empty canopy and sun
parameters. Optical defaults tree_k0.6/tree_lad1.0 have no effect with TREE=0.
No projected EPSG:6677 diagnostic arrays are used as engine grids.

### Observer and validity

`view_point_height=1.5`, `include_building_roofs=False` for both calls. On common
valid ground: transition k=1, `int(1.5/1)=1`, API origin index k=2, DDA ray
centre k=2.5. With the inherited **nominal** D0+index interpretation, origin
H=**12.75m**, **2.5m above source ground**, not exact physical1.5m. No offset
or engine patch is introduced. Both cases have exactly the same ground/air
transition and observer air cells; upstream surface+1/Building rounding remain.

The common semantic mask is **engine Building ID=0**, including courtyard
holes, excluding all192 Building columns from both A/B. The code verifies API
A is finite everywhere and API B is finite exactly on this mask. No unexpected
invalids are hidden by merely intersecting finite-result masks. Raw NaNs:
A0/B192; saved common-mask NaNs:A192/B192. NaN is never replaced by0.

## Actual result — 2026-10-28

Local run identifier `source-h-synthetic-solar/smoke-20261028-02` under
`data/work/`; Windows OUEM Python3.11.9, **4.501s** including chain, actual
voxelization, both real CPU solar calls, output save/reload and plotting.

| Metric | Executed result |
|---|---:|
| Common valid ground |3,904 cells|
| Excluded Building ground columns |192 cells|
| In-domain shadow / reduction cells |507 (12.9867% of valid ground)|
| In-domain shadow area, nominal grid |507m²|
| Adjusted mesh area approximation |507.0942m²|
| A mean horizontal direct |458.861149W/m²|
| B mean horizontal direct |399.270319W/m²|
| Maximum reduction |458.861149W/m²|
| Mean reduction over all valid ground |59.590831W/m²|
| Mean reduction over shadow cells only |458.861149W/m²|
| Unexpected invalid valid-ground cells / increases |0 /0|

Difference is explicitly **A−B**, positive=less horizontal direct irradiance.
Shadows are fully opaque in this Building-only binary case. A tolerance of
1e−9W/m² is a floating-point computation budget, not a physical threshold.
All statistics exclude the common NaN mask; valid zeros remain real shade.

The PNG was inspected: northwestern shadows, rasterized Building outlines and
identical excluded ground columns are visible. A coarse **planar direction QA**
finds a sunward Building column for every shaded cell within a cell-square
lateral radius sqrt(2)/2 (observed maximum minimum lateral distance0.70521 cells).
This is not ray tracing or independent exact-shadow validation and does not
produce the irradiance arrays; those come exclusively from the actual API.

**Western-boundary shadow count12**; other boundaries0. The westward shadow is
cut by the finite domain. Reported507m² is **in-domain**, not the entire
untruncated shadow area or evidence of sufficient halo. Outside occluders are
absent. No unnecessary domain expansion/convergence experiment was added.

## Reproduce / outputs

Ordinary OUEM Windows terminal, new directory required:

```powershell
.venv\Scripts\python.exe tests/integration/run_synthetic_building_solar_smoke.py --run-dir data/work/source-h-synthetic-solar/my-new-run
```

The existing authored two-box test factory creates a synthetic chain. Its
dummy Converter/CLI execution identities are fixtures; **Converter NOT RUN**.
The relocated `synthetic_niigata` label is not real municipality data.

Saved local files (ignored, not committed or Accepted):

- `solar_terrain_only.npy`, `solar_with_buildings.npy`: common-mask horizontal
  direct W/m², not raw API maps on Building columns.
- `solar_difference.npy`: A−B, same mask; `valid_ground_mask.npy`: bool.
- `building_id_grid.npy`: engine-aligned identity/outline aid.
- `solar_metadata.json`: full input/engine identities, conditions, raw/saved
  NaN counts, observer, grid, QA, output hashes, runtime/module identities.
- `solar_comparison.png`: A/B/reduction, common scale, grey exclusions and
  rasterized Building outlines; `RESULTS.md`: completion report.

All five saved arrays were reloaded with `allow_pickle=False` and exactly
compared including NaNs. Use NumPy or the PNG to inspect; QGIS GUI/3D rendering
was not executed. A partial failed run is not successful; RESULTS is written
only after successful calls, QA, save/reload and plotting.

Solar difference NPY SHA-256:
`f69389d5857bedf3e49489e387b11336538d48ba61fc07affa51beb7ea829d2e`.
Implementation SHA at execution:
`a8c91975d91b489aef23df0b00ac8df3617fb0fd0f94df9d773c61d91e6e5667`.
The execution used baseline HEAD with then-uncommitted code, recorded dirty
state/runner hash; it is not a claim that a later commit was executed.

### Tests actually run

Two new actual-API integration tests observe both real calls and verify common
grid/ground/observer arguments, reference irradiance, shared semantic mask,
Building shade, coarse sun/shadow direction, unchanged inputs and governance.
Related source-H/voxel/Adapter v0.1 suites: **297 passed, 1 warning** in 44.55s.
Full `.venv\Scripts\python.exe -m pytest -q -ra`: **864 passed, 5 skipped,
251 warnings** in 194.81s. Skips are existing Windows symlink privilege limits;
warnings are existing Rasterio deprecations and Consumer ctime diagnostics.
No new skip/xfail or changed existing assertion. No real-data acceptance implied.

## Next step and limits

This completes the small **synthetic source-H Building → actual direct-solar**
path. Next canopy integration needs a common engine grid, D0/ground conditioning,
shared observer/mask policy and TREE/Building collision diagnostics; do not mix
the projected Canopy/diagnostic arrays by shape. A real-data trial additionally
requires selected-source identification, eligibility/datum/coverage review and
the existing Phase5 gates. Keep physical-height interpretation separate from
this nominal discrete model. Domain enlargement is needed before claiming
complete shadow area; choose actual date/weather only in a later scoped study.

No canopy, diffuse/reflected/global radiation, time series, thermal model,
complex Terrain/geometry, rare concurrency handling or scientific-accuracy
guarantee. source-H eligibility **NOT_ESTABLISHED**; Human Review/Formal
Acceptance **NOT_VERIFIED**; Phase5 A1–A4 **OPEN**.
