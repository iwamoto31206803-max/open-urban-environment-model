# Phase 2: independent canopy shadow PoC

This experimental adapter does not alter Standard Canopy, accepted Terrain,
Building, the Building Adapter, or `komae_canopy.py`. It uses pinned VoxCity
1.7.0 (`fa212656305328a9a657973bae26f352bfe813bc`) and its CPU direct solar API.
No GPU, global/diffuse irradiance, annual integration, or thermal model is used.

Run from ordinary Windows PowerShell in the OUEM venv. First run the synthetic
fixtures; a JUnit report with no failures/errors/skips is required by the runner:

```powershell
.venv\Scripts\python.exe -m pytest -q tests/test_canopy_shadow_poc.py --junitxml=data/work/voxcity-canopy-shadow/fixtures-new.xml
.venv\Scripts\python.exe -m ouem.canopy_shadow_poc `
  --envelope-run data/work/height-envelope/komae-exploratory-20261026-01 `
  --expected-manifest-sha 6121cbf732f8ece9553013be2483203f08faf9a8d364136a919c184b46738d68 `
  --dem-reference data/work/height-envelope/komae-exploratory-20261026-01/diagnostics/sampled_dem_z_nearest.tif `
  --expected-reference-sha f456fd5a94e7f0b9a94398281d9b0db35835f4959f23fede09e143ccefe7bd33 `
  --fixture-report data/work/voxcity-canopy-shadow/fixtures-new.xml `
  --output-dir data/work/voxcity-canopy-shadow/phase2-new-run
```

The output directory must not exist. Inputs are hash checked and the existing
Height Envelope semantic gate is reused. Full 300x400 input metadata, masks,
validity and the 0.5m DEM's 120,000 nearest samples must match the retained
generation reference. NoData is not filled. Relative top/bottom subtract that
DEM once; zero depth is excluded experimentally, not a canopy-absence decision.
All arrays flip vertically into south-up north/east/up axes, keeping the
explicit EPSG:6677 metre grid. No lon/lat rasterization or 3m cutoff is added.

The evaluation ROI and 32m halo domain are the Phase 1 proposal's 64x64 and
128x128 cells. Buildings are absent, both cases use common experimental
Bareland code 1. DEM minimum is retained as absolute Z origin. Every actual
voxel is compared with independently constructed expected occupancy, including
float32 rounding, the ground `+1` layer, and thin-crown expansion. Arrays are
padded with air only to common Z. No hidden elevation correction is made.

Astral computes the sun at 2026-06-21 12:00 JST. Projected grid north is measured
with Geod at the ROI centre and passed as the clockwise rotation. DNI=800 W/m²,
tree_k=0.6, tree_lad=1.0, and requested observation height=1.5m are experimental
constants; the engine truncates observation height to an integer voxel and
starts rays at voxel centres. Optical parameters are not measured leaf data.

The halo diagnostic crops already audited halo voxels, preserving Z origin and
all inner voxels instead of revoxelizing with a different DEM minimum. It
compares a domain with external occluders removed against the buffered result.
A conservative ray reach from full source max top/DEM and min DEM, plus 2m
vertical and 2m horizontal allowance, must fit inside 32m. This only addresses
recorded source coverage under the selected sun; unknown surrounding objects
and scientific source errors remain unverified.

Local outputs: JUnit fixture copy, `comparison_arrays.npz`, voxel arrays (not
for Git), `comparison.png`, and `run.json` with inputs/output hashes, exact
code SHA, Git HEAD/worktree state, pin verification, conditions and QA.
Failures produce `FAILED.json`; without `run.json` COMPLETED, partial outputs
are not successful evidence. The runner refuses mismatched observer masks,
missing ROI observations, unexpected voxel geometry or irradiance increases.
NaN is never replaced by zero for statistics. Differences are B minus A in
W/m²; no arbitrary binary shadow threshold is introduced.

Reproduction requires the local input/evidence packet and retained sampled DEM;
these are not bundled in Git. A successful run remains a limited experiment,
not Standard Canopy acceptance, measured canopy truth or scientific accuracy.
