# Real Komae Building + Terrain VoxCity experiment

This bounded experimental source-H lane reuses PR #97 artifacts and the fixed
VoxCity 1.7.0 public raster/voxel APIs. [Executed results](RESULTS.md).
It does not broaden the accepted v0.1 Adapter's manifest whitelist, change any
Standard, certify eligibility or close Phase 5 gates. It adds no canopy/solar.

From an ordinary Windows terminal at the repository root, using the OUEM venv:

```powershell
.venv\Scripts\python.exe -m ouem.real_komae_voxel `
  --run-dir data/work/real-komae-voxel/<new-run-id> `
  --building-manifest data/work/real-komae-source-h/run-20261028-04/standard/standard.gpkg.manifest.json `
  --terrain data/work/terrain-reproducibility/komae-20261026-01/generated/standard.tif `
  --study-area config/study_areas/komae_09LD3451.yaml `
  --artifact-root C:/dev
```

Create `data/work/real-komae-voxel/` first if absent. Use a new run directory;
there is no overwrite, resume, force, source reconstruction or automatic download.
`C:/dev` is the explicit common artifact root of the PR #97 source chain,
including its fixed Converter binary. No Converter is executed in this task.
Keep historical input paths/manifests unchanged.

If the Building file or its dependency chain is missing, stop and follow
[PR #97 regeneration](../real_komae_source_h/README.md) into a new directory,
then pass that new adjacent manifest and repeat Consumer validation. A saved
PASS from another run cannot substitute for actual files. Missing Terrain
requires the [existing reproducibility procedure](../../Terrain_Acquisition_PoC_v0.1.md)
and its Native/Standard records; do not invent or relabel a DEM or edit an
accepted manifest to make paths resolve. Any failed/partial run remains FAILED
with its report and partial artifacts preserved; retry only in a new directory.

## Method and reuse boundary

1. Verify pinned engine installation through existing PEP 610 + RECORD checks.
   Run the independent Consumer on the actual source-H Standard and rebind its
   full input watch set. Verify Terrain manifest SHA, EPSG:6677, north-up Float32
   grid/NoData and explicit source-declared T.P. versus Building EPSG:6695 H.
   Require Building/Terrain extent overlap and contained ROI/domain definitions.
2. Reuse only `ROI`/`DOMAIN` constants from `canopy_shadow_poc.py`: EPSG:6677
   64×64 m evaluation bounds and 128×128 m computation bounds with 32 m halo.
   No canopy or solar functions are called. Transform corners to EPSG:4326;
   VoxCity `compute_cell_center_coords` defines the actual affine lon/lat grid.
   Its NE corner is reconstructed from SW + u + v, not assumed identical to the
   independently transformed projected NE. Save exact u/v steps and all centres.
3. Sample unchanged Standard DEM at actual engine centres (4326 → 6677, XY
   only), selecting the containing 0.5 m source pixel. Reject outside, masked
   and nonfinite samples. No filling, nearest-outside extension or interpolation.
4. Derive whole 2D supports using existing footprint normalization, retaining
   original XYZ in unchanged Standard. Require selected geographic footprints
   valid; no post-projection repair is silently applied. Use complete shapes
   intersecting the actual engine parallelogram, without clipping. Record each
   boundary intersection and full-footprint DEM bounds coverage separately.
5. Public precise rasterization (`overlapping_footprint=True`) supplies ID,
   relative-height and segment grids. Compute each Building's relative height
   as source maxH minus mean raw DEM under its actual owner cells. Iterate
   rasterization until ownership is stable; fail on nonconvergence, lost IDs,
   engine ID merging or changed footprints. IDs are assigned lexically over
   **all 173 canonical OUEM IDs**, so selected IDs need not be consecutive.
6. Execute `Voxelizer(1., 'Standard').generate_combined` with raw DEM, real
   rasterized buildings, zero trees and a common Bareland surface class.
   This surface label is a required engine placeholder, not observed land cover.
   Independently reconstruct per-ID ground conditioning and normalized D_eff.
   Audit all output classes/positions against scalar engine rules, independently
   match footprint contributors to segment multisets, and report roof/ground
   discretization separately from unchanged source H.

`terrain_H.npy` is the raw sampled H grid. `effective_ground_H.npy` is the
engine's absolute per-owner conditioned ground. `effective_dem.npy` is D_eff,
normalized by the conditioned minimum **D0_effective**, which can differ from
D0_raw in other inputs (covered by a test). These are MODEL products, not
modified Standard Terrain. Building begins above the retained surface layer:
`g = int(float32(D_eff)/1m + 0.5)+1` for the installed Numba path. Ground is below
g; surface occupies g−1; ordinary Building segments start at g and end at
g+round(relative_height). Nominal H edges are D0_effective+k; centres add 0.5 m.
The surface layer and rounding are retained, reported and never offset-corrected.

## Artifacts for PR #99

All local generated products remain ignored:

- `grid.json`: exact actual-grid origin, u/v step, shape, vertical origin,
  nominal/adjusted resolution, ROI bounds, halo and coordinate conventions.
- `centre_lon/lat/x/y.npy`, `roi_mask.npy`: exact centre coordinates in both
  CRSs and evaluation membership; never replace with projected north-up indices.
- `building_ids.npy`, `building_heights.npy`, `building_segments.json`:
  public raster output and per-cell contributor IDs; frame mapping and per-ID
  absolute top/ground/relative height are in the report and whole-footprint GeoJSON.
- `terrain_H.npy`, `effective_ground_H.npy`, `effective_dem.npy`,
  `ground_indices.npy`, `voxels.npy`: same uv_m engine layout, safe NumPy loading
  with `allow_pickle=False`. The actual 3D class array has no intrinsic IDs;
  bind it to the separate owner/contributor records.
- GeoTIFFs for Terrain, conditioned ground, IDs, heights and ROI use an exact
  **EPSG:4326 affine**, row reversed u, column v. They are QGIS-friendly MODEL
  diagnostics, not EPSG:6677 north-up rasters. No extra warp is performed.
- `plan.png`, `section.png`, `report.json`, local `RESULTS.md`: visual/numerical
  diagnostics, immutable input/output fingerprints, engine provenance and limits.

PR #99 should verify fingerprints, reuse this grid and Building IDs, and sample
canopy at these exact centres. Convert absolute canopy H against the recorded
conditioned ground if required by the public API; re-audit D0, occupancy, ROI
and vertical semantics after integration. A 32 m halo is not a promise of solar
boundary sufficiency. Do not reuse the older projected-grid canopy arrays by
index, assume the class voxels retain building identity, or call this run solar
validation. Source declarations are not independently surveyed datum accuracy.
