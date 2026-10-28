# Real Komae three-element direct-solar PoC

Bounded exploratory integration on the actual PR #98 grid.
[Executed results](RESULTS.md). No new Standard, eligibility, acceptance,
Phase 5 gate or generic model framework.

Run in an ordinary Windows terminal using the repository OUEM venv:

```powershell
.venv\Scripts\python.exe -m ouem.real_komae_solar `
  --run-dir data/work/real-komae-solar/<new-run-id> `
  --base-run data/work/real-komae-voxel/run-20261028-04 `
  --envelope-run data/work/height-envelope/komae-exploratory-20261026-01 `
  --artifact-root C:/dev `
  --study-area config/study_areas/komae_09LD3451.yaml
```

Create the output parent first. Outputs require a new directory; no overwrite,
resume, download or reconstruction fallback. The exact PR #98 report and
existing Envelope manifest are SHA-pinned. Missing/mismatched inputs stop.
See [upstream reproduction](../real_komae_voxel/README.md) if prerequisites
need regeneration: a new upstream identity requires explicit review and a new
pin, not relabeling old artifacts as successful.

## Reuse and quality gates

1. Verify PR #98 COMPLETED report, all recorded source/output hashes and engine
   PEP 610/RECORD provenance. Rerun Consumer and bind the same source identities.
   Recheck saved centres/CRS, ROI, source DEM samples, conditioned ground/D0,
   ground indices, Building segments and saved voxels using PR #98 helpers.
2. Verify Envelope input/output hashes, retained raw CHMv2 tile, acquisition,
   source statement snapshot and limited review. Reuse `validate_sources` for
   HAG/metre/DEM/vertical provenance. Require matching Terrain and CR=0.60.
3. Feed existing nearest `sample_raster` the saved engine x/y centres. Keep
   numerical state, NoData/missing, outside and candidate masks separate.
   This full-coverage PoC stops on any invalid/missing/outside sample rather
   than inferring absence. State 1 means valid computation only. Candidates
   require valid finite top>bottom: positive estimated crown depth, not confirmed
   trees. Source Envelope rasters are read only.
4. Subtract unchanged engine-conditioned absolute ground from crown H for the
   public API. Below-ground intervals are excluded/counted, never shifted or
   clamped. `Voxelizer.generate_combined` generates TREE before BUILDING
   priority. Its allocation can add Building+tree heights; remove unused air
   only to preserve 128×128×27, and fail if any occupied voxel would be lost.
   No custom voxel generator is presented as VoxCity.
5. Independently audit every TREE interval and thin-crown expansion. Require
   no TREE in original Building/ground/surface and Current with TREE replaced
   by air to be exactly PR #98. Keep IDs, DEM, D0, origin, rotation and ROI.
6. Use actual public solar API with PR #96's artificial azimuth 135°, elevation
   35°, DNI 800 W/m², requested height 1.5 m, roofs excluded, tree k=0.6 and
   LAD=1.0. Both primary cases share observers and geometry; difference is
   No-Canopy−Current. Three additional diagnostic API calls remove Building
   while retaining conditioned ground, and crop each original lattice to ROI
   with identical Z/D0 to measure outside-ROI effects. No resampling occurs.

## Outputs and limits

Local ignored outputs: Current/No-Canopy classes; TREE/candidate/state/missing/
outside masks; sampled H; direct solar/difference and Building obstruction
control; common observer mask/indices; cropped boundary controls; ROI mask;
unchanged grid; statistics/report JSON; PNG plan/section and local results.
NPYs have exact pickle-disabled readback. NaN denotes excluded Building
observers, not zero irradiance. Full 128×128 2D arrays also have exact-affine
EPSG:4326 GeoTIFFs, reversed-u rows and v columns, for QGIS. No false regular
EPSG:6677 affine or older projected-array index alignment is used.

CR=0.60 is an estimated constant crown ratio. Meta CHMv2 is modeled HAG, with
uncertain local ground/height, XY displacement, false canopy over structures
and observation-date alignment. Positive height/state do not establish tree
presence/absence. Uncalibrated homogeneous k/LAD and the API's <1% transmission
cutoff can produce exact zero. Strong modeled attenuation is not measured
urban exposure or canopy benefit. No diffuse/global/reflected radiation,
weather/time series, annual or heat assessment is implemented.

Actual nominal observer centre is D0_effective+g+1.5 m: common across cases,
not verified physical 1.5 m above source ground. TREE edge errors include the
surface layer and rounding, not an H transformation.

Halo review uses full source AOI maximum Building/Envelope H plus 2 m edge
allowance, the lowest ROI observer, sun elevation and actual sunward exit
distance. Directional sufficiency is conditional on known source heights;
unknown taller exterior objects/different suns remain unverified. Cropping
shows effects of outside-ROI objects, not expanded-domain convergence.
No QGIS/formal acceptance, survey accuracy or ecological validation is claimed.
