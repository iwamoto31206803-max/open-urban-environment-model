# Minimal source-H synthetic 2.5D Building Adapter

**Experimental**, Step 4B-2, not a Standard or accepted data path.
Baseline main `4ba899e493adf056e2dbb445df81730adc6f61bf` includes merged #93.
See the [Step 4A audit](reviews/OUEM_Source_H_VoxCity_Adapter_Contract_Audit_20261028.md),
[Consumer](Source_H_Standard_Consumer_Validation_v0.1.md) and
[source-H Standardizer](Source_H_Standard_Building_v0.1.md).
The [existing Adapter v0.1](OUEM_VoxCity_Adapter_v0.1.md) is unchanged.

## API and implemented boundary

[source_h_synthetic.py](../src/ouem/adapters/source_h_synthetic.py) accepts a
Standard manifest/root/config plus explicit `FlatSyntheticTerrain` and
`synthetic_source_ids`. It calls the Consumer internally: no caller-supplied
persisted PASS is accepted. All observed artifacts are hash/size/stamp/path-bound
again at use and rechecked after preparation. Standard is opened read-only.
This is best-effort point-in-time TOCTOU detection, not file locking or a
guarantee for a later consumer.

```python
from ouem.adapters.source_h_synthetic import FlatSyntheticTerrain, adapt_synthetic_source_h

terrain = FlatSyntheticTerrain(
    bounds=(-23860., -41025., -23796., -40961.), resolution=1., elevation_H=10.25,
    vertical_crs="EPSG:6695", vertical_quantity="gravity_related_height",
    vertical_unit="metre", declaration="Authored synthetic common H; not survey evidence.",
)
result = adapt_synthetic_source_h(
    "standard-run/standard.gpkg.manifest.json", artifact_root, "area.yaml",
    terrain=terrain, synthetic_source_ids=["synthetic_tokyo", "synthetic_niigata"],
)
```

The explicit ID list must match all selected Standard source IDs. It is a caller
declaration of synthetic scope, not automatic authentication. **Do not use on
real datasets.** The Adapter reuses the Consumer's bounded actual GPKG reader
and v0.1's pure numeric-ID/relative-height helpers, not the legacy orchestrator.
No existing Standardizer, Consumer, Adapter or engine behavior is changed.

All ordered LoD2 XYZ remain in Standard. Only derived XY footprints are
simplified: discard zero-area vertical projections and union valid positive-area
surface projections with their holes. Invalid positive-area faces fail; no
repair or clipping. The maximum **all-vertex H** is the roof-top proxy, not a
semantic roof classifier. Source ID, UUIDv5 OUEM ID and numeric ID remain mapped.

## Terrain and relative height

Terrain is an authored Float64 constant on a complete EPSG:6677 north-up grid,
not a Standard Terrain artifact/sampler. Its H quantity, EPSG:6695 and metre
declarations must match Standard explicitly. No H→h conversion or offset.
Whole footprints must lie in-domain, not overlap and each own at least one
non-conflicting cell centre. Grid limit:65,536 cells. Initial grounded-box
scope requires geometry base H to equal the flat Terrain H.

`ground_H = mean(DEM_H where diagnostic building_id_grid == ID)`;
`height = max(all Building vertex H) - ground_H`; `min_height = 0`.

PR #92/v0.1 uses **actual engine-owned cells**. Here ground is constant, so
every nonempty ownership subset has exactly the same mean. The diagnostic
cell-centre mask is not VoxCity's precise intersection rule. This equivalence
does not extend to sloped/masked Terrain or engine conditioning/remapping.

`SyntheticBuildingResult` contains:

- `buildings`: complete EPSG:6677 2D GeoDataFrame with identities, absolute top,
  geometry base, assigned ground, relative height, sample count/range and area.
- `terrain_H`, `building_ids`: **diagnostic** north-up cell-centre arrays and
  explicit grid/affine metadata, not engine raster/voxel arrays.
- `voxcity_buildings`: EPSG:4326 2D GeoDataFrame with `id`, `height`, `min_height`
  and retained identities/H attributes. Only XY is reprojected; H is an
  attribute, not a CRS4326 Z ordinate. No engine call inside the Adapter.
- `summary`: technical checks, input identities, methods and governance states.

## Reproduce the small smoke

From an ordinary Windows OUEM terminal (existing pytest/Matplotlib dependencies):

```powershell
.venv\Scripts\python.exe tests/integration/run_source_h_synthetic_25d_smoke.py --run-dir data/work/source-h-synthetic-25d/my-new-run --run-voxcity
```

The run must not exist. The test-only factory reuses existing synthetic chain
helpers, relocates the second authored box and lowers it to the common base.
`synthetic_niigata` is a retained label, not a real Niigata/Komae building.
The historical fixture/expectations are untouched. Converter-shaped GPKG bytes,
dummy CLI identity and execution declaration are **synthetic fixtures**; the
Converter is NOT executed and no authentic execution is claimed.

The fresh run holds `chain/`, `derived/buildings_25d.gpkg` (2D plus H attributes),
`voxcity_buildings.geojson`, `buildings.csv`, `overview.png`, `summary.json`,
`RESULTS.md`. All remain ignored. This demo is not a transactional artifact
publisher; a partial failed run is not successful/Accepted and must not be reused.

Without `--run-voxcity`, engine checking is explicitly NOT RUN. With it, version
**1.7.0** and direct-URL commit `fa212656305328a9a657973bae26f352bfe813bc` are checked
before calling public `voxcity.geoprocessor.raster.create_building_height_grid_from_gdf_polygon`
with `overlapping_footprint=True` (pinned `src/voxcity/geoprocessor/raster/buildings.py:62`,
also audited in #92). Returned ID, height and `[0,height]` segments are checked.
This is not voxelization, DEM engine sampling or solar analysis.

Open the derived GPKG in QGIS, color by `height` and label `source_id`,
`z_top_abs`, `ground_eff_abs`. The PNG is a planar diagnostic, **not an observed
QGIS 3D display**. The GeoPackage has 2D footprints, not 3D roof meshes.

## Actually executed synthetic integration — 2026-10-28

Local run identifier `source-h-synthetic-25d/smoke-20261028-03` under `data/work/`;
Windows OUEM Python 3.11.9. Full chain, outputs and public API check: **2.608s**.
Consumer PASS; two valid whole footprints, original identities retained.
Derived GeoPackage was reopened: CRS, full 2D geometry, identities and H/height
attributes match the in-memory result exactly. The PNG was visually inspected.

| Source ID | Engine ID | Max H (m) | Ground H (m) | Height (m) | Diagnostic cells | Engine cells |
|---|---:|---:|---:|---:|---:|---:|
| synthetic_tokyo | 2 | 19.75 | 10.25 | 9.50 | 96 | 96 |
| synthetic_niigata (relocated) | 1 | 25.00 | 10.25 | 14.75 | 87 | 96 |

Both grids are 64×64 but **not identical**: projected centre sampling versus
engine geographic rectangle/precise area intersection explains the 87/96 count
difference. Arrays are not spliced by shape. No engine ID losses/remaps, all
owned heights equal expected values, all intervals match. Flat ground makes the
ground assignment insensitive to these masks. Engine DEM reader, `process_grid`,
voxelizer and solar were NOT RUN.

Execution used the baseline HEAD with then-uncommitted Adapter; local summary
records module SHA, dirty state, input identities and output hashes. Adapter SHA:
`73db8ec2d12fc611f2fe9cf49d517a0b4a43729a7a5475122abbe40e454a0fbf`.
This is not a claim that a later commit was executed.

### Automated validation on this branch

Four new tests cover the two-building successful pipeline/numeric heights/IDs,
read-only input preservation, Consumer failure, vertical mismatch and at-use
input tampering (success assertions are grouped in one integration test).
Related Native/Standard/Consumer/legacy Adapter suites: **293 passed, 1 warning**
in 39.56s. Full `.venv\Scripts\python.exe -m pytest -q -ra`: **860 passed,
5 skipped, 251 warnings** in 194.89s. Skips are existing Windows symlink
privilege limits; warnings are existing Rasterio deprecations plus the Consumer
ctime diagnostic. The optional actual VoxCity raster call above is a separate
explicit smoke, not implied by pytest results or real-data acceptance.

## Known limitations and next step

No real municipality data, sloped/NoData Terrain, elevated/underground buildings,
general overlaps, footprint repair, roof-detail preservation in derived2.5D,
geodetic accuracy, voxel geometry, canopy or solar acceptance. D0/effective DEM,
ground conditioning, rounding and observer geometry remain untested here.
The next slice can use these IDs/heights/flat declaration to test engine voxel
boundaries; real fusion needs separate pair/coverage/geometry review.

source-H eligibility **NOT_ESTABLISHED**; Human Review / Formal Acceptance
**NOT_VERIFIED**; Phase5 A1–A4 **OPEN**. No formal specification was revised.
