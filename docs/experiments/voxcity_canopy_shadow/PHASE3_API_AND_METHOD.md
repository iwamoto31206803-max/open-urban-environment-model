# Phase 3A: vertical discretization / observer API review

Base: main after PR #71, merge `e625e03f0dd2b826e03380f941edca4aa2126199`.
Pinned VoxCity 1.7.0 commit `fa212656305328a9a657973bae26f352bfe813bc`.
Installed PEP 610 plus all 136 source RECORD hashes verified; aggregate
`33e2bfdbc8a677f53154e8cd16295603819c68cf9f24c7a4cdfeb196bcbcd0bd`.
This is not an independent upstream Git tree comparison.

## Pre-implementation decision

**Safe to proceed with 0.5 m isotropic public-API fixtures.** A single scalar
size is shared by horizontal metadata, voxel height and ray path length.
1 m horizontal / 0.5 m vertical anisotropy has no supported representation in
this investigated path; do not emulate it by relabeling metadata or patching
VoxCity. No existing adapter/contract is changed.

Installed source paths below are relative to `.venv/Lib/site-packages/voxcity/`.
Line numbers refer to the verified pinned source, not an inferred newer API.

| Evidence | Meaning |
|---|---|
| `models.py:10`, `GridMetadata.meshsize` | One scalar; `VoxCity.to_xarray()` uses it on all three axes |
| `generator/voxelizer.py:125`, `Voxelizer`; `:158`, `generate_combined()` | Public scalar voxel_size; caller supplies equally shaped 2-D arrays; DEM minimum is removed internally |
| `generator/voxelizer.py:39`, `_voxelize_kernel` | Shared size divides DEM and relative canopy elevations; ground +1, half-up rounding and thin-crown expansion |
| `simulator/solar/radiation.py:18`, `get_direct_solar_irradiance_map()` | Public scalar observation height; returns horizontal direct W/m²; no per-cell ray-origin argument |
| `simulator/solar/kernels.py:11`, `compute_direct_solar_irradiance_map_binary` | `int(view_point_height / meshsize)`, first walkable surface transition |
| `simulator/common/raytracing.py:11`, `trace_ray_generic` | Adds +0.5 to origin on each axis; multiplies ray segment length by the same scalar meshsize |

These source bytes are retained as local source snapshots with SHA-256.
The low-level functions are inspected, not patched. Production calculations use
`Voxelizer.generate_combined()` and `get_direct_solar_irradiance_map()`.

## Geometry equations

Let s be isotropic voxel size, D the input DEM, D0 its domain minimum,
T/B relative canopy top/bottom, and h the requested observation parameter:

```text
g = int(float32(D-D0)/s + 0.5) + 1
lo = int(float32(B)/s + 0.5)
hi = int(float32(T)/s + 0.5)
if lo == hi and lo > 0: lo -= 1
TREE = [g+lo, g+hi)
bottom face Z = D0 + (g+lo)*s
top face Z = D0 + (g+hi)*s
ray-origin Z = D0 + (g + int(h/s) + 0.5)*s
```

Ground +1 adds s; individual ground/crown rounding also changes faces.
With flat ground and h=1.5 m, ray height is 2.5 m for s=1 and 2.25 m for s=0.5.
No scalar parameter makes exactly 1.5 m above that flat ground at either size:
ray centres lie on half-integer multiples of s after the surface transition.
Rough terrain adds spatial rounding differences, so a common scalar cannot
represent exact 1.5 m everywhere. The investigated public map API has no explicit
per-cell absolute-origin input. No undocumented correction is introduced.

## Controlled resampling and cases

S1 uses the existing 1 m DEM/top/bottom. S2 repeats each existing cell into four
0.5 m cells (nearest, aligned 2×2 children). All absolute top/bottom/DEM values
and coverage are preserved; subtract the repeated DEM once. This intentionally
keeps the Height Envelope generation DEM, rather than resampling extra detail
from canonical 0.5 m Terrain. It creates no new canopy or terrain information.
A parent is exactly the union of its four children; compare 64×64 m ROI using
an equal-area mean of the 2×2 finite child irradiances. No NaN-to-zero filling.

Primary cases: S1 (s=1,h=1.5) and S2 (s=0.5,h=1.5).
Additional same-geometry cases: S1_low (s=1,h=0.5) and S2_low (s=0.5,h=1.0).
These parameters expose each API's next lower observer lattice, not a guarantee
of exact 1.5 m. Their actual origin distributions must be measured.
Within-size differences isolate changing observation index on fixed geometry.
Across-size differences combine geometry, horizontal ray-origin sampling and
observation heights. With common D0, 1 m origin centres and 0.5 m origin centres
lie on disjoint Z lattices: exact cross-size origin matching is unavailable.
Do not label the main contrast a pure vertical-resolution effect.

Both cases retain 32 m halo, source coverage, sun/time, DNI, CR, optical
parameters, rotation and no-building assumptions from Phase 2. Recheck halo
reach for both sizes; a cropped no-halo diagnostic preserves D0 and inner
occupancy. Measure array storage and sampled process RSS separately: RSS
includes interpreter/libraries/JIT and is not an isolated algorithm allocation.

Proceed to real data only after all critical synthetic fixtures pass. Outputs
remain exploratory technical evidence, not scientific or Standard Canopy
acceptance. Reproduction requires local input/evidence packets (not in Git).

## Other inspected solar entry points

`radiation.py:543 get_building_solar_irradiance()` and the face kernels
`:222 compute_solar_irradiance_for_all_faces`, `:369
compute_solar_irradiance_for_all_faces_masked` accept building mesh face
centres/normals/SVF, with their own normal offset and coordinate conventions.
They are not an existing exact-1.5m ground-observer map switch. Repurposing a
synthetic mesh as free sensors would be a separate adapter/validation effort,
not a demonstrated solution in this experiment. No claim of exhaustive
absence of all possible low-level constructions is made.

## Reproduction (ordinary Windows OUEM venv)

First run the fixtures, with no skips/failures/errors:

```powershell
.venv\Scripts\python.exe -m pytest -q tests/test_canopy_shadow_sensitivity.py tests/test_canopy_shadow_poc.py --junitxml=data/work/voxcity-canopy-shadow/phase3-fixtures-new.xml
.venv\Scripts\python.exe -m ouem.canopy_shadow_sensitivity `
  --envelope-run data/work/height-envelope/komae-exploratory-20261026-01 `
  --expected-manifest-sha 6121cbf732f8ece9553013be2483203f08faf9a8d364136a919c184b46738d68 `
  --dem-reference data/work/height-envelope/komae-exploratory-20261026-01/diagnostics/sampled_dem_z_nearest.tif `
  --expected-reference-sha f456fd5a94e7f0b9a94398281d9b0db35835f4959f23fede09e143ccefe7bd33 `
  --phase2-run data/work/voxcity-canopy-shadow/komae-phase2-20261027-01 `
  --expected-phase2-sha e153e8da170d6dc34cfaf76bd6b1564f7924e208695e4fef75208d664bcf571d `
  --fixture-report data/work/voxcity-canopy-shadow/phase3-fixtures-new.xml `
  --output-dir data/work/voxcity-canopy-shadow/phase3-new-run
```

A new output directory is mandatory. On failure, FAILED.json is written;
partial arrays are not successful results. `run.json` COMPLETED is written
last, with code/Git identity, pin, input/output hashes and all case statistics.
RSS sampling currently targets Windows explicitly; other platforms require a
reviewed measurement implementation before this runner can execute.

The Phase 2 crop helper has a fixed 1m metadata profile. Phase 3 wraps it with
explicit size-preserving metadata for all model components; the existing
helper is unchanged. A two-size fixture checks native cropped API results
against zenith results from the full scene.
