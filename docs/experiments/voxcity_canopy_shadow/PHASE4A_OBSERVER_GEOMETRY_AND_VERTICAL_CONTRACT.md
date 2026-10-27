# Phase 4A — Observer geometry and vertical coordinate proposal

**Recommendation: C for the current pin.** Retain the existing ground-map API
with measured observer-height limitations. Arbitrary physical-point tracing is
**not validated and no observer Adapter is implemented**. A low-level route
(B) is a possible future investigation, but a fractional-start counterexample
prevents recommending it for arbitrary points now. A (public-only arbitrary
observer Adapter) is not established by the investigated APIs.

This is an experimental coordinate-contract **proposal for independent review**,
not a change to Standard Terrain, Building, Canopy or the accepted Building
Adapter. Phase 2/3 source, tests and conclusions remain unchanged. No VoxCity
patch, hidden height correction or new large real-data calculation is included.

## 1. Baseline and evidence

Latest fetched main and GitHub agree that PR #72 is merged:
`b6a0b08139a7a66d59b90c404cb21958bdcbb3e6`.
Read [Phase 3 method](PHASE3_API_AND_METHOD.md),
[Phase 3 results](PHASE3_RESULTS_20261027.md), both existing implementations and
Phase 2/3 fixtures, plus the existing authoritative
[Terrain](../../OUEM_Standard_Terrain_v0.1.md),
[Building](../../OUEM_Standard_Building_v0.1.md) and
[Building Adapter](../../OUEM_VoxCity_Adapter_v0.1.md) contracts.

VoxCity **1.7.0**, commit `fa212656305328a9a657973bae26f352bfe813bc`, unchanged.
PEP 610 origin plus all 136 installed Python source RECORD hashes verified;
aggregate `33e2bfdbc8a677f53154e8cd16295603819c68cf9f24c7a4cdfeb196bcbcd0bd`.
This is not an independent comparison with the upstream Git tree.
Windows ordinary OUEM venv: Python 3.11.9, NumPy 2.4.6, Numba 0.68.0,
Rasterio 1.4.4, PyProj 3.7.2, trimesh 5.2.0; synthetic CPU threads=2.

Local evidence ID:
`data/work/voxcity-canopy-shadow/komae-phase4a-20261027-01/`.
`inspection.json`, `source-index.json` with source hashes/AST positions,
`source-snapshots/`, focused/full JUnit, and arithmetic decomposition are local
only. Historical checkout `C:\dev\open-urban-environment-model` is environment
specific. API inspection and synthetic fixtures were executed on 2026-10-27.
New tests were initially uncommitted over the main SHA above; their SHA is
retained locally and the same bytes are submitted in this PR. No runtime
snapshot, dataset or copied installed source is committed.

## 2. API comparison and exact findings

Paths/line numbers below refer to the verified installed source, relative to
`.venv/Lib/site-packages/voxcity/`.

| Route and evidence | Observers / actual origin | Solar and attenuation | Assessment |
|---|---|---|---|
| Public `solar.get_direct_solar_irradiance_map`, `solar/radiation.py:18`; kernel `solar/kernels.py:11` | First walkable surface transition z=g; scalar h becomes int(h/s); tracer starts at (i+0.5,j+0.5,g+int(h/s)+0.5) | `direction_to_axis_vector(azimuth,elevation,rotation)`; generic path-length exponential | Established Phase 2/3 route; no per-cell physical XYZ input |
| Internal `common.raytracing.trace_ray_generic`, `:11` | Accepts float origin vector o; uses continuous start o+0.5 but initial cell trunc(o) | Same direction can be supplied; exp(−k×LAD×actual segment metres), hit mode must match ground API | Importable implementation detail, not exported in `common.__all__`; fractional start must not be assumed correct |
| Public `solar.compute_solar_irradiance_for_all_faces`, `solar/radiation.py:222` | Face centre/s + 0.1×normal then generic +0.5 on all axes | Generic optical law, face-incidence dot product, SVF/DHI interface | Public float centres do not mean an exact unshifted observer API |
| Public `solar.get_building_solar_irradiance`, `:543`, default fast_path=True | Scene east/north axes swapped to model north/east; face-normal offset +0.1 then masked tracer +0.5 | Default masked ray uses per-visited-voxel exp(−k×LAD×s), not generic partial/slanted segment length | Same k/LAD alone does not establish parity; not adopted as ground sensors |

The public solar package explicitly exports the ground/face functions. Generic
ray tracing is accessed by an internal module path in the new tests only.
The non-underscored function name is not a supported arbitrary-origin contract.
Source `common/coordinates.py:13–25` defines the scene/array axis swap;
`utils/orientation.py:72` defines the existing clockwise true/grid-north mapping.

### 2.1 Fractional-origin counterexample (executed)

In unit-voxel coordinates q, a proposed physical point is (1.5,1.5,2.25),
inside a TREE slab z∈[2,3). Candidate inverse o=q−0.5 gives (1,1,1.75).
The continuous start is q, but initial k=int(1.75)=1 instead of floor(2.25)=2.
The first boundary parameter is negative; segment clipping does not restore
the correct subsequent path length.

| Quantity, s=1m, ray straight up | Analytic physical segment | Observed generic tracer |
|---|---:|---:|
| Crown path length m | 0.75 | 1.00 (inferred from transmission) |
| Transmission, k=0.6 / LAD=1 | 0.637628151622 | 0.548811636094 |
| Horizontal direct, DNI=800 W/m² | 510.102521297 | 439.049308875 |

The same mismatch was reproduced along north, east and up at s=1 and s=0.5.
Starts q=2.5 and q=2.75 along the tested ray axis do match analytic partial
lengths because their initial cell is consistent. Thus this is a demonstrated
limitation, not a claim that every fractional origin fails. On nonnegative
coordinates the consistency check is `trunc(o) == floor(o+0.5)` per axis.
Integer o (existing centre rays) satisfies it; arbitrary points generally do
not. Boundary/tie/negative coordinates need further validation even when a
particular example happens to agree. **Do not deploy q−0.5 as a universal fix.**

### 2.2 Equality with the existing map (executed)

At the map's actual integer origin o=(i,j,g+int(h/s)), internal generic calls
with hit_values=(0,), inclusion_mode=False reproduce every pixel of the public
map in the synthetic grids, for both sizes, cardinal/rotated sun and multiple
k/LAD values (including zero extinction). Irradiance is
`(0 if hit else transmission) × DNI × sin(elevation)` in W/m².
Use the same existing sun-vector helper and rotation; no extra 180° is added.
This confirms a restricted parity condition, **not arbitrary XYZ support**.

### 2.3 Building-face alternative (executed)

A horizontal triangle at local z=2, within a TREE slab [2,3), yields generic
continuous z=2+0.1+0.5=2.6. The slow public building path returns
**629.302288853 W/m²** (0.4m remaining crown path); the default masked fast path
returns **439.049308875 W/m²** (one voxel attenuation). It adds normal and centre
offsets, requires face normals/SVF, and applies face incidence. It cannot be
substituted for physical ground points while claiming the existing CPU map's
geometry and optical integration are unchanged. Slanted rays, arbitrary mesh
boundaries and full building irradiance remain outside this fixture's scope.

### 2.4 Outside / solid / canopy observers

Observed raw generic behavior: an initially positive-outside origin returns
(False,1), identical to an unobstructed normal domain exit. A ground voxel
returns (True,1); transmission alone is not irradiance. Starting at a consistent
TREE centre attenuates the remaining crown segment. There are no explicit
OUTSIDE / IN_GROUND / IN_TREE quality flags. Negative arguments are truncated
toward zero, so negative-boundary safety is not inferred from positive tests.
NaN/Inf coordinates, self-intersection tolerances and arbitrary fractional
origins have not been accepted.

Proposed OUEM boundary for any future observer route:

- Validate finite physical XYZ, explicit CRS/vertical reference, and half-open
  model extent before calling a tracer. Do not classify an out-of-volume return
  as open sky. Outside source coverage is invalid evidence, not zero shading.
- Distinguish original DEM+h physical target from the voxelized surface+h.
  A target can lie inside displaced model ground/building; report invalid-solid,
  without silently lifting it, snapping to a centre or replacing it with zero.
- TREE origin may be meaningful for an experimental sensor, but requires an
  explicit policy and analytic remaining-path check. It is not the same as
  canopy absence or invalid data. Keep A/B validity/status masks explicit.

## 3. Proposed vertical and observer coordinate contract

**Draft, unapproved integration conditions**, not normative Standard changes.
Let D be the physical DEM at the chosen sample location, Zt/Zb the canonical
absolute Height Envelope, s a scalar isotropic voxel size, D0 the local Z origin.
For Phase 2/3 (all building IDs zero), D0=min(D), effective ground is D.
Relative inputs are T=Zt−D, B=Zb−D; subtract D only once.

| Representation | Meaning / conversion |
|---|---|
| Standard Terrain D | Absolute metres, source-declared T.P.; EPSG:6677 alone supplies no vertical datum |
| Height Envelope Zt/Zb | Absolute top/bottom in the same recorded vertical context; no geometric or scientific acceptance implied |
| Engine DEM input / origin | Relative ground d=D−D0 for the no-building case; preserve D0 independently of GridMetadata |
| Ground index | g=Q_s(d)+1; Q_s(x)=int(float32(x)/s+0.5) for nonnegative inputs |
| Ground top face | D0+g×s, not exactly D |
| TREE occupancy | [g+lo,g+hi), lo=Q_s(B), hi=Q_s(T); if equal and positive, lower lo by one |
| Canopy faces | D0+(g+lo)×s and D0+(g+hi)×s |
| Voxel centre (i,j,k) | Model array axes north/east/up; absolute Z=D0+(k+0.5)×s |
| Existing ground ray | Actual absolute Z=D0+(g+int(h/s)+0.5)×s |
| Desired physical observer | Zphysical=Dsample+hphysical; store independently from API h and actual Z |

For this unrotated EPSG:6677 grid with southwest (Emin,Nmin), physical
(E,N,Z) maps to continuous **model cell coordinates**
q=((N−Nmin)/s,(E−Emin)/s,(Z−D0)/s). Rotated grids require their explicit grid
basis; do not invent an extra rotation of already projected coordinates.
EPSG cell indices, model coordinates, scene mesh metres and geographic
azimuth are separate quantities. Scene (east,north,up) must swap horizontal
axes to model (north,east,up). TIFF north-up rows flip once at the model input.

The desired q is a coordinate definition, **not a validated input recipe for
trace_ray_generic**. That function currently uses o+0.5 and trunc(o), as above.
No proposed offset is applied to existing data, grids, observers or outputs.
A future observer manifest should record requested physical XYZ/baseline,
actual continuous ray XYZ, raw API argument, initial voxel index/class,
coordinate mapping, source/processed DEM identity, D0, s, sun rotation, optical
integration route and point validity. These fields are design candidates only.

### 3.1 Separate ground +1, rounding and Float32 effects

For an unexpanded face at relative height H:

```text
Eface = (voxel face absolute Z) − (D + H)
      = s + epsilon_D + epsilon_H

epsilon_D = s*Q_s(D−D0) − (D−D0)
epsilon_H = s*Q_s(H) − H
```

Each epsilon contains Float32 casting and half-up rounding. They can be split
as `float32(x)−x` plus `s*round_half_up(float32(x)/s)−float32(x)`.
For a thin expanded lower face, add **−s**; top is unchanged. The synthetic
fixture independently adds these terms and matches faces read from generated
voxels at both sizes, including a thin crown. Thus a generic “subtract 1m”
would remove only one term, depends on s, mishandles expansion, and is not an
accepted correction. Ideal half-step error bounds also need casting precision
and expansion exceptions recorded.

The following is **read-only arithmetic on existing Phase 3 saved arrays**, not
new real-data voxelization or irradiance. It uses the occupied ROI mask (3,842
parents / 15,368 children) and the recorded unexpanded real crowns. Separate
DEM and crown epsilons below include precision plus rounding; only the synthetic
fixture separates their casting subterms directly.

| Existing case / face | Occupied samples | Ground +1 m | Mean DEM epsilon m | Mean crown epsilon m | Mean face error m |
|---|---:|---:|---:|---:|---:|
| S1 bottom | 3842 | 1.000000000 | +0.001790141 | -0.005153492 | +0.996636649 |
| S1 top | 3842 | 1.000000000 | +0.001790141 | +0.000000005 | +1.001790146 |
| S2 bottom | 15368 | 0.500000000 | -0.000942811 | +0.019312932 | +0.518370121 |
| S2 top | 15368 | 0.500000000 | -0.000942811 | +0.000000005 | +0.499057194 |

This identifies the systematic +s layer and the distinct residual terms without
reinterpreting prior outputs or accepting a correction.

### 3.2 Future buildings: effective ground and re-origin gate

`generator/voxelizer.py:183–184` subtracts min(raw DEM), then calls
`geoprocessor/raster/core.py:48/75` process_grid. Nonzero building IDs replace
all cells of each ID with the mean and **subtract the new minimum again**.
In absolute notation, define Deff=raw DEM with per-ID means applied and
D0eff=min(Deff). The engine ground is Deff−D0eff (before casting/rounding), not
necessarily D−min(D). Store both raw D and processed Deff/D0eff.

Executed sloping 2×2 fixture: raw D=[[10,12],[11,13]], ID1 on the first row;
Deff=[[11,11],[11,13]], D0eff=11 although min(raw D)=10. Ground indices at
s=1 are [[1,1],[1,3]]. Continuing to label them using D0=10 would introduce a
1m coordinate-reference error. This is a synthetic integration requirement,
not a claim that a specific accepted Komae artifact has this error.

Existing Building Adapter computes relative building top from the per-ID
mean effective ground. Future canopy integration must review how absolute
crown Z is referenced to that **same engine-effective ground**, without changing
canonical Height Envelope or reusing its Draw subtraction blindly in cells
where Deff differs. A physically DEM+h observer still refers to its stated
physical baseline, not automatically to a flattened modelling surface.
No rebasement is performed or accepted in Phase 4A.

A second precision gate is required: `_flatten_building_segments` (:91,
rounding :119–120) rounds building segments before the kernel, using the
input arithmetic; canopy arrays enter the kernel as Float32 (:206–208).
Executed near-tie example relative top=3.4999999m at s=1: building exclusive
end index=4, canopy end index=5 on the same flat ground. With ordinary exact
heights, building and tree extents match; buildings overwrite TREE in shared
voxels, as the fixture confirms. Same nominal height and origin do not alone
guarantee identical rounding. Define/record a precision policy before claiming
geometric correspondence; do not silently change existing Building Adapter.

## 4. A/B/C options and recommendation

| Option | Scale / dependency | Building integration implications | Recommendation |
|---|---|---|---|
| A: public-only arbitrary observer Adapter | No demonstrated sensor API. A synthetic mesh wrapper would be small initially but needs new offset/attenuation/validity validation | Building-face fast/slow semantics differ; no accepted point-parity claim | Do not implement as if already safe |
| B: internal generic ray tracer | Small caller wrapper, substantial analytic/edge/property fixtures and pin/source guards; internal module stability risk | Exact-origin initialization, negative/tie cases, physical baseline and solids remain unresolved | Research option only; current fractional counterexample blocks general acceptance |
| C: existing public ground map | Smallest change: retain code, report actual origins and limitations | Permits only clearly labelled model-surface observations; does not solve arbitrary physical height | **Recommended for current pin** |

C does not solve arbitrary physical 1.5m, and does not permit such a claim.
Phase 4A investigation is complete, but general arbitrary-observer capability
remains **BLOCKED under the unmodified investigated path**. The previous
centre-ray PoCs remain valid within their recorded conditions.

Revisiting B would require a supported, validated initialization that couples
continuous start with its actual containing voxel, analytic partial lengths,
axis/tie/negative/boundary tests, classification/status checks and centre-ray
parity. An upstream solution or a separately designed OUEM tracing route needs
explicit review; changing the VoxCity pin requires approval. This PR supplies
neither a new tracer nor an experimental compensation that hides the issue.

## 5. Building integration gates and deferrable work

Before any mixed building/canopy result is interpreted geometrically:

1. Preserve common CRS, metre units and explicit vertical-reference evidence;
   do not infer T.P. from EPSG. Hash/check Terrain, Building and crown inputs.
2. Fix one study grid, orientation, extent/halo, sampling, isotropic size and
   common Z bounds. Verify public Building rasterization and this experimental
   projected grid really correspond; accepted geographic Adapter output is not
   automatically the same grid.
3. Record raw/effective DEM, building IDs, per-ID means and D0eff. Review crown
   relative-height baseline, precision/rounding and collisions. No double DEM
   addition or unrecorded offset. Require actual voxel-face audits.
4. Choose physical observer baseline versus model-surface observer explicitly.
   Physical targets inside displaced model ground/buildings must have invalid
   status; A/B geometry, observer masks and coverage need common comparisons.
5. Select the solar integration route and k/LAD semantics, direction/rotation,
   domain bounds and boundary tests. Do not mix building fast-path attenuation
   with generic ground results and label it a controlled comparison.

Can be deferred for a narrowly labelled geometric PoC: ecological CR/LAD
calibration, source accuracy/field surveying, seasonal foliage, diffuse/global
or annual integration, thermal models and full Standard Canopy definition.
They remain necessary for later scientific/production claims. Actual Komae
building/canopy assembly, real arbitrary-point maps and upstream fixes were
**not implemented or tested** here.

## 6. Executed tests and evidence boundary

New file `tests/test_canopy_observer_geometry.py` contains **26 characterization
cases**. Together with unchanged Phase 2/3 fixtures:
**62 passed in 10.22s**, no failures/errors/skips. The fractional-origin and
building fast/slow tests intentionally assert observed limitations; their passing
does not mean arbitrary physical-point tracing passed.

```powershell
.venv\Scripts\python.exe -m pytest -q tests/test_canopy_observer_geometry.py tests/test_canopy_shadow_poc.py tests/test_canopy_shadow_sensitivity.py --junitxml=data/work/voxcity-canopy-shadow/phase4a-fixtures-20261027-01.xml
.venv\Scripts\python.exe -m pytest -q --junitxml=data/work/voxcity-canopy-shadow/phase4a-full-pytest-20261027-01.xml
```

Final full pytest in ordinary Windows OUEM runtime: **588 passed, 5 skipped,
243 warnings in 160.98s**. Skips are existing Windows symlink-privilege limits;
warnings are existing Rasterio/Affine pending deprecations. No failed test was
silently treated as passed. The full run uses the same new fixture bytes as
the focused run; no production code was modified.

Only this decision/contract-proposal document and the reusable small synthetic
fixture file are added. No production implementation, existing contract, phase
2/3 result, formal record or input artifact is changed. Local evidence hashes
and final PR commit are reported in the PR description; no local datasets or
installed-source snapshots are uploaded. Draft PR, awaiting independent review.

### Evidence identities

| Evidence | SHA-256 |
|---|---|
| New fixture module | `936f0c20a196e8287ff6680afc931ad57cd5f049333e97ed734057029a22867f` |
| Focused JUnit | `320e0c238a2bb85ee886be9671c3904d3acfd8d0dc146b9da3bdcb9354a2dd97` |
| Full JUnit | `6861b57fc34944ed61b40867a73c638021a798ebd4972c843898a1e397d2bfea` |
| Existing Phase 3 saved arrays | `88f8e6547cbd0616adc5b37bf6d118ba86e0501a52db20629492be416c6cc650` |
| Read-only historical decomposition | `becfff73bf15b67161fa22c8cb6271e7c17f190274f06bcf736f7181793b5c19` |
| Pinned source `simulator/common/raytracing.py` | `549e6a0a3c028e1fb638f9294f92afa0080d568580426440c97262ba263e24d7` |
| Pinned source `simulator/solar/radiation.py` | `a05289164e306ac1a9d5c7fe22ad1b264eab84e82848441664610d28ef6f0c05` |
| Pinned source `generator/voxelizer.py` | `1c3402651e8eb6a6e706010893f4ac90276f5d0e1e07aece5dd4dc000664cc5c` |
| Pinned source `geoprocessor/raster/core.py` | `99d346819fb0b6daa0683d2f3f13caadb91005c38896c28439308207f171c402` |
