# B2 VoxCity GVI API Audit v0.1

Status: **Static audit, not a GVI execution or scientific validation**.
2026-10-30; OUEM main `c73ef78853d0be242686923e0a9d35e225c0a774`
(PR #122 merged). Read with the [minimal E2E proposal](OUEM_B2_Minimal_Technical_E2E_Design_v0.1.md).
The [B1 closeout](../status/B1_TECHNICAL_MILESTONE_CLOSEOUT.md) and
[deferred backlog](OUEM_B1_Deferred_Validation_Backlog.md) remain unchanged.
No simulator import/call, JIT compilation, dependency change or Run write occurred.

Labels: **Confirmed** means installed-source/metadata inspection; **Derived**
means a mathematical consequence of that code, not a measured result;
**UNVERIFIED** means runtime behavior/accuracy was not established here.

## 1. Runtime and source anchors

Ordinary Windows OUEM venv Python 3.11.9; installed VoxCity **1.7.0**.
[pyproject.toml:18](../../pyproject.toml#L18) pins Git commit
`fa212656305328a9a657973bae26f352bfe813bc`. Installed PEP 610 records the same
origin/revision/commit; all **136 installed Python sources** match their SHA-256
RECORD entries. This checks installation integrity, not an independent comparison
with the upstream Git tree. Inspection used stdlib metadata/AST and read-only
NPY headers/JSON; it did not import `voxcity.simulator.view` to inspect signatures.

Paths below are relative to `.venv/Lib/site-packages/voxcity/`, with line numbers
for these exact installed bytes. They are local package references, not tracked
OUEM files or a claim that current upstream main has the same implementation.

| Ref | File / definitions | SHA-256 |
|---|---|---|
| L | `simulator/view.py`: compatibility re-exports, lines 14–40 | `4a1aa7eeb1618730843d81d3bbc5a0fbab8267c48dacf08e0d8e2c63393c3262` |
| V | `simulator/visibility/view.py`: `get_view_index` 19–114; low-level exports 581–604 | `9439fd6513735ba607200df784679dd85153237a7eefc31a622a3701e7f04760` |
| G | `simulator/common/geometry.py`: grid rays 7–13, Fibonacci rays 16–29 | `cb7c9405349a1e19e401cdee9525fb9de14c6dc620ddbf3093f04c5abcede9fa` |
| R | `simulator/common/raytracing.py`: generic trace 11–156; point VI 160–178; map 182–220; masks/fast traces 223–351; fast map/observer scans 355–445 | `549e6a0a3c028e1fb638f9294f92afa0080d568580426440c97262ba263e24d7` |
| U | `simulator_gpu/visibility/view.py`: calculator 35–232, map kernel 350–430, trace 433–550 | `c4097701b2f3130952ee5f0643aef573df2fc2c478d779c4791853344fc5af1e` |
| H | `simulator_gpu/visibility/geometry.py`: direction generation 14–91 | `b108aee2c38e2f6b7bb126184dbca5ab1d9f349612f2f2b049a65952fd2af0b4` |

Other inspected owners: `models.py:11–60` dataclasses;
`utils/orientation.py:72–111` array-axis direction mapping;
`utils/classes.py:25–88` class codes;
`simulator/visibility/__init__.py:1–29` public exports;
`simulator_gpu/visibility/integration.py:322–488` GPU wrappers.

## 2. APIs and actual call graph

**Confirmed:** `voxcity.simulator.view` is now a compatibility wrapper, not the
algorithm owner. `voxcity.simulator.visibility.get_view_index` and
`voxcity.simulator.visibility.view.get_view_index` reach the same CPU function.

```text
simulator.view.get_view_index (re-export)
  → visibility.view.get_view_index
      → common.geometry._generate_ray_directions_grid / _fibonacci
      → default fast_path=True:
          _prepare_masks_for_vi → _compute_vi_map_generic_fast
            → _precompute_observer_base_z / _top_z
            → _trace_ray_inclusion_masks / _exclusion_masks
        any exception in fast block → generic map below
      → fast_path=False: compute_vi_map_generic
          → compute_vi_generic → trace_ray_generic → calculate_transmittance
      → unconditional Matplotlib plot/show; optional OBJ export → 2D ndarray
```

| API / signature from installed AST | Role / boundary |
|---|---|
| `get_view_index(voxcity, mode=None, hit_values=None, inclusion_mode=True, fast_path=True, **kwargs)` | Public full-grid API (V:19). `voxcity.voxels.classes` must represent a 3D class array; `voxcity.voxels.meta.meshsize` supplies the scalar metre step. It does not validate an OUEM contract or geographic coordinates. |
| `compute_vi_generic(observer_location, voxel_data, ray_directions, hit_values, meshsize, tree_k, tree_lad, inclusion_mode=True)` | Existing **low-level single-observer API**, R:160, publicly re-exported in `visibility.view.__all__` (V:589–603), also documented in the official reference. Caller supplies `(M,3)` directions and an index-space origin; no surface selection, coordinate conversion, mask, point-set wrapper or default k/LAD is supplied here. |
| `compute_vi_map_generic(voxel_data, ray_directions, view_height_voxel, hit_values, meshsize, tree_k, tree_lad, inclusion_mode=True, include_building_roofs=False)` | Exported low-level full-grid implementation (R:182), accepting prepared directions and an **integer voxel height offset**, not metres. It is the slow/generic path of the public wrapper. |
| `get_surface_view_factor(voxcity, **kwargs)` | Public building-face/mesh view factors (V:460 onward), not a pedestrian GVI raster or general world-coordinate observation API. Different hemisphere/face-normal processing and defaults; do not substitute it for the map API. |

The low-level point function is **not** exported by the legacy L wrapper or the
top `visibility` package's short `__all__`; use its actual module path. It is an
existing engine computation, not permission to write an OUEM ray tracer. Private
direction helpers/mask kernels are implementation details; using them later
would need a specific reason (e.g. pinned sampling diagnostics) and recorded hashes.

## 3. CPU defaults and sampling

All defaults below are from V:19–56, not B1 Solar or a tutorial example.

| Parameter | CPU `get_view_index` default / effect |
|---|---|
| `mode`, `hit_values`, `inclusion_mode` | None / None / True. No custom targets with mode None raises ValueError. `mode='green'` **overwrites** targets to `(-2,2,5,6,7,8)` and inclusion=True; `mode='sky'` sets `(0,)`, exclusion=False. |
| `fast_path` | True; mask-based Numba fast path with catch-all silent fallback to generic map. No actual-path receipt is returned. |
| `view_point_height` | 1.5 m; converted by `int(height / meshsize)` before observer selection. |
| `N_azimuth`, `N_elevation` | 120, 20: **2,400 directions** for grid sampling. |
| `elevation_min_degrees`, `elevation_max_degrees` | −30°, +30°, inclusive grid endpoints. This is a 60° vertical band, not a full sphere. |
| `ray_sampling`, `N_rays` | `'grid'`; N_rays defaults to N_azimuth×N_elevation but is used only for Fibonacci. Every non-`fibonacci` string selects grid rather than raising. |
| `tree_k`, `tree_lad` | **0.5, 1.0**. B1 direct Solar explicitly uses 0.6/1.0; GVI has a different default k. |
| `include_building_roofs` | False. Surface search/invalidity described below. |
| `num_threads` | None; if supplied it attempts Numba global thread selection and suppresses exceptions. Not a scientific weighting parameter. |
| Plot / OBJ | viridis, vmin=0, vmax=1; **plot/show is unconditional**. `show_plot=False` is an unconsumed kwarg, not a headless switch. OBJ default False. No CPU ROI/computation-mask, maximum ray range or arbitrary-points kwarg is consumed. |

**Confirmed grid rule (G:7–13):** azimuths are `linspace(0,360,N_azimuth,
endpoint=False)`; elevations are `linspace(min,max,N_elevation)`; elevation is
the outer loop, azimuth the inner. Direction components are
`(cos(e)cos(a), cos(e)sin(a), sin(e))` along local **u, v, up**. At defaults,
azimuth step is 3°, elevation step 60/19≈3.157895°; the even elevation count
does **not** include 0° (nearest ±1.578947°). Each ray has equal weight in the
final mean: no cosine-of-elevation or projected-area weighting is applied.

**Confirmed Fibonacci rule (G:16–29):** N=max(1,int(N_rays)); z is uniformly
spaced at bin midpoints between sin(min elevation) and sin(max elevation), and
azimuth follows the golden angle. Directions are Float64. Equal weights here
approximate equal solid-angle sampling of the band; equal-elevation grid weights
are a different measure. Neither is automatically a photograph's pixel weighting.

The full-map wrapper ignores `extras['rotation_angle']`; the grid helper calls
the orientation function with its zero-rotation default. Thus azimuth zero means
the local u axis, not exactly true north on rotated Komae grids. Continuous 360°
coverage is rotationally symmetric, but finite grid/Fibonacci ray sets have a
sampling phase. Geographic directional products require additional explicit
design; passing a rotation kwarg currently does not rotate the ray set.

Counts/angles, finite positive meshsize, target classes and kwarg names are not
strictly validated by the wrapper. Int conversion, zero-direction/empty sets,
out-of-range angles or ignored misspellings must not become an OUEM run contract.

## 4. What the CPU index actually measures

**Confirmed** for canopy-only targets `(-2,)`, inclusion=True (R:53–86,
160–178, 265–291, 373–394):

1. Start at `(i+0.5,j+0.5,k+0.5)` in voxel units; scale segment lengths by meshsize.
2. Traverse AIR. An opaque non-target such as Building/subsurface/surface stops
   with no target contribution. A domain exit before a target also contributes 0.
3. In a TREE voxel, multiply T by `exp(-tree_k × tree_lad × segment_length)`.
   If T<0.01, inclusion mode returns **no hit**, hence contribution 0.
4. Otherwise TREE is immediately a target: return hit=True and current T.
   Because TREE is itself a target, this stops at the **first TREE voxel**, not
   after traversing the whole crown.
5. A hit contributes `1−clip(T,0,1)`; a non-hit contributes 0. The result is
   `sum(contributions) / M`, where M is **all generated directions**, including
   blocked and escaped rays. There is no renormalization to rays with in-domain
   targets or an unobstructed field of view.

For the first TREE segment length L, the ordinary contribution is therefore
`1−exp(−k·LAD·L)`, subject to the cutoff above. **Derived example, not execution:**
L=1 m with the defaults gives ≈0.393469, not 1. A deeper crown does not add
further TREE segments once that first target has returned. At nominal 1 m and
default k/LAD, a single voxel chord cannot exceed √3 m, so ordinary first-hit
attenuation cannot reach the 0.01 cutoff; that branch still matters for other
parameters/coarser meshes and must not be interpreted as monotonic saturation.

This is **not the literal binary canopy-hit count / total-ray count**, nor
integrated whole-crown extinction. The Concept's canopy-ray ratio and this CPU
score require an explicit metric/label decision before being equated.

Default `mode='green'` is additionally broader than OUEM's canopy-only target:
positive codes 2/5/6/7/8 denote Rangeland/Tree/Moss-and-lichen/Wetland/Mangrove
(`utils/classes.py:46–61`), while -2 is 3D TREE. The CPU's global "trees in
targets" flag selects `1−T` even for a non-TREE target. **Derived:** such a
surface reached through AIR has T=1 and contributes zero, despite its membership
in the green tuple. That source behavior is not justification for relying on the
broad mode as a stable canopy contract; use explicit targets after review.
For non-TREE-only target sets the CPU instead adds clipped surviving T, not 1−T.

Generic DDA handles simultaneous boundary crossings and inclusion-side checks
(R:90–146); fast DDA advances one selected axis at a time (R:260–291). Both
include the starting voxel. Boundary/corner equivalence, fastmath effects and
fallback frequency are **UNVERIFIED**, not proven by shared function names.

## 5. Observers, masks, output and finite boundaries

With roofs=False, both map paths find the first bottom-up AIR/TREE-above-solid
transition. Supporting water-like codes 7/8/9 or any negative class (including
Building -3) invalidate that column. No transition also yields NaN. With roofs=True,
the top-down scan allows -3 roofs and skips other invalid supporting surfaces
(R:182–220, 355–445). A positive "No Data" class 14 is **not** automatically
converted to missing/NaN by these rules. Source validity remains the caller's job.

Let g be the first walkable transition, m the meshsize. The ray centre is
`(i+.5, j+.5, g+int(requested_height/m)+.5)` in index units; OUEM absolute H is
`D0 + (g+int(height/m)+.5)*m`. At m=1, height=1.5, this is **D0+g+1.5**:
the same voxel-surface convention as B1. **Derived:** existing non-building A/B
geometry would inherit the approximately DEM+2–3 m placement recorded in
[PR #121](../experiments/real_komae_solar/B1_GEOMETRY_OBSERVER_PHASE2.md), not
automatically DEM+1.5 m. No GVI observation was actually computed to confirm it.

The CPU map does not separately reject an offset observer beyond nz before
tracing; an out-of-domain start can become finite zero instead of NaN. It also
does not provide a caller-specified observer mask. Precheck capacity and actual
origin classes, and independently compare masks rather than treating every finite
return as physical validity. Starting inside TREE immediately uses that cell's
remaining chord. Counts of such A/B origins were not examined here.

The point API does not select a ground transition. Its origin is index-space and
the trace adds 0.5 before starting, while initial cell indices use `int(origin)`.
Arbitrary fractional/negative inputs therefore must not be assumed to implement
correct continuous world-coordinate observation points. Integer-index point
diagnostics are a supported source-level route; arbitrary physical-height
observations need separate validation/design.

Output: Float64 2D `(n_u,n_v)` on the same column indices as input classes; no
transpose/flip, CRS, affine, D0, ROI or units metadata is returned. Values are
dimensionless ratios in the ordinary 0–1 range, not percent or W/m². Valid zero
means no counted target contribution in the finite scene; NaN is an invalid
surface/search result. Arrays have no raster NoData or geographic export by
themselves; optional OBJ/Matplotlib are not a GeoTIFF writer.

Rays stop on class encounters or exit **any** finite array face; no distance
horizon, exterior-object model, per-ray escape counter or unknown-outside flag is
returned. Escapes stay in the denominator with zero inclusion contribution.
For fixed observers/directions and unchanged interior cells, an escaping
inclusion ray contributes zero and an extension could add a nonnegative target
contribution. That is a ray-level truncation observation, not a bound on physical
accuracy; a new run with changed D0, grid/sampling or geometry need not be a
monotonic comparison. **32 m context is not certified sufficient** for 360° low-angle
views; Solar's single-sun height bound cannot be transferred. Saved upper Z fits
known occupied cells, not an infinite sky/exterior scene.

## 6. CPU/GPU distinction

| Aspect | Inspected CPU | Inspected GPU path / limitation |
|---|---|---|
| Entry | V:19; NumPy/Numba, Matplotlib imported | `simulator_gpu.visibility.get_view_index` → integration:437 → `get_view_index_gpu`:322 → `ViewCalculator.compute_view_index` U:95 → map/trace kernels U:350/433 |
| Dependencies | NumPy, Numba JIT; plotting and OBJ-import dependencies already installed | Taichi fields/runtime/device plus NumPy. Installed metadata marks Taichi as optional `gpu` extra; **Taichi is not installed** here. No GPU import/initialization attempted. |
| TREE-target score | 1−T at first target chord, or zero if cutoff reports no hit | U:407–413 adds **1.0** per hit when TREE is in targets; k/LAD still affect trace/cutoff, but not the ordinary 1.0 score. Not numerically equivalent to CPU. |
| Origin / precision | Starting voxel included; Float64 output; default fastmath path | U:464–515 skips starting voxel; Float32 map/ray fields; explicit observer-capacity guard U:398. Origin-in-canopy cases can differ. |
| Sampling / axes | G uses north/east/up components | H grid comments/formula use east/north/up; wrapper passes arrays without an explicit transpose at integration:299–317. Full backend-axis equivalence is UNVERIFIED; finite sampling phase matters, particularly Fibonacci. |
| Scope controls | No CPU computation-mask kwarg; full map | GPU accepts computation_mask/workspace. Wrapper parameters/caching differ; no tested drop-in parity. |

GPU API compatibility claims and comments (including an integration comment
about flipping) do not override actual kernel/return logic; U:234 returns
`vi_map.to_numpy()` with no map flip at that return. These are static differences,
not a completed GPU correctness review, performance comparison or execution result.
GPU is excluded from the proposed first OUEM implementation.

## 7. Official examples / paper versus this installed code

| Primary reference | Published example / statement | Audit interpretation |
|---|---|---|
| [CPU API reference](https://voxcity.readthedocs.io/en/latest/autoapi/voxcity/simulator/visibility/view/index.html) | Lists map and low-level point interfaces | Confirms API discoverability; detailed semantics above come from installed bytes, not this latest-version index. |
| [View tutorial](https://voxcity.readthedocs.io/en/latest/examples/demo_view.html) | Example table says 72×12, −15°…30°, Fibonacci, k=0.5 | Those are the tutorial's explicit settings (even labeled defaults there); installed CPU defaults are 120×20, −30°…30°, grid. |
| [Complete demo](https://voxcity.readthedocs.io/en/latest/examples/demo_basic.html) | View example explicitly sets k=0.6 | An override/example, not the installed GVI default or a reason to copy B1 Solar k. |
| [Authors' arXiv v1, §4.2.2](https://arxiv.org/html/2504.13934v1#S4.SS2.SSS2) | Demonstration uses 600 rays (60×10) and a −30°…30° band, horizontal 360° | A 2025 paper example, not the pinned 1.7.0 defaults or proof of this CPU score. Do not infer identical endpoint spacing from the paper wording. |

Latest docs are not version-pinned evidence. The published 2026 PDF could not be
retrieved through the browser's size limit; paper comparison above is explicitly
the accessible **arXiv v1**, not a claim of verifying the final journal methods.

## 8. Findings for implementation review

**Confirmed:** API/data structures exist, saved A/B headers are compatible with
the expected shape/type and the GVI surface convention is the same index rule as
B1. **Not confirmed:** any GVI call/import in this runtime, actual A/B GVI masks
or values, fast/generic equivalence, CPU/GPU parity, physical observer accuracy,
or a correct OUEM canopy-only binary GVI interpretation.

Review first: CPU weighted first-chord metric versus Concept meaning; explicit
canopy-only targets; fast/default/fallback policy; height/angle/weighting and
local-azimuth interpretation; finite-domain label and validation limits. The
[design proposal](OUEM_B2_Minimal_Technical_E2E_Design_v0.1.md) turns those into
bounded decision points and an implementation sequence, without starting it.
