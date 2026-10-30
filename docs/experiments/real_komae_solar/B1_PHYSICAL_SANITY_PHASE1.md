# B1 Physical Sanity Verification — Phase 1

## Preregistered design (before the first test execution)

Basis: main `242f86f` (PR #119 merged),
[parameter audit](../../planning/OUEM_B1_VoxCity_Parameter_Baseline_Audit_v0.1.md).
This is synthetic technical/formula verification, not validation of real urban
canopy, weather, pedestrian exposure or Formal Acceptance. No Komae A/B rerun.

Owner and executable design:
[`tests/test_b1_physical_sanity.py`](../../../tests/test_b1_physical_sanity.py).
All cases fix azimuth 135°, elevation 35°, DNI 800 W/m², tree_k=0.6,
tree_lad=1.0, view_point_height=1.5 m, roofs=False. Rotation is zero to isolate
true-north geometry; existing rotation tests remain the separate regression owner.
No parameter is calibrated from the calculation output.

### Scenes and independent expectations

Common local Cartesian domain: 32×32×20 cells, 1 m, array axes u=north,
v=east, z=up. Source and effective DEM are flat H=20 m; D0=20 m. The public
Voxelizer creates the surface at k=0 (class 1); synthetic fixtures append only
AIR to reach the declared 20 layers. No original Run is read or written.
The domain is large enough to contain each tested box intersection; no exterior
obstacles are assumed in this authored scene.

| Case | Authored occupied geometry, edge coordinates relative to D0 | Expected result defined before execution |
|---|---|---|
| A: no obstacle | Bare surface z=[0,1); AIR above | All 1,024 columns finite; I0=800 sin(35°)=458.861149080837 W/m². |
| B: one building | u=[12,16), v=[12,16), z=[1,9); 4×4 m footprint, 8 m above voxel surface | 16 roof columns NaN; other columns either I0 or numeric zero by positive ray/box intersection. Sun SE bearing 135°, shadow NW bearing 315°. |
| C1: homogeneous TREE | u,v=[8,24); z=[4,6), from allocator inputs bottom=3, top=5 m above surface | T=exp(-0.6×1.0×L); I=I0×T unless T<0.01, then exact zero. |
| C2: deeper TREE | Same footprint; z=[4,10), from bottom=3, top=9 | Same formula; paths on both sides of T=0.01 must occur; sub-cutoff values become exact zero. |
| D: No-Canopy | C1/C2 with TREE alone replaced by AIR | All columns I0; original geometry unchanged outside TREE. |
| E: mixed pair | B+C2, BUILDING takes precedence; Current minus only TREE gives No-Canopy | OUEM solar_pair must equal independent building-intersection plus TREE-path oracle on shared non-roof observers; Difference=No-Canopy−Current. |
| F: observer discrimination | Same building footprint, heights 1 and 2 m above voxel surface | g=1, k=g+int(1.5)=2, centre H=22.5. At NW centre (16.5,11.5), top z=2 cannot block, top z=3 blocks; distinguishes DEM+1.5 from actual DEM+2.5. |

The independent unit sun vector is
`(cos(35°)cos(135°), cos(35°)sin(135°), sin(35°))` in north/east/up.
For each observer `(i+0.5,j+0.5,2.5)`, an analytic slab intersection computes
entry=max(0, per-axis entry times), exit=min(per-axis exit times),
L=max(0,exit−entry). This is a continuous box calculation: it calls no VoxCity
orientation, ray traversal, attenuation or kernel helper. Occlusion is L>0.
Zero-length corner tangencies are clear, not positive-length intersections.
The implementation correction explained below preserves this geometric rule.

Building shadow reach from its NW footprint corner (u=16,v=12), at the
observer's plane, is `(9−2.5)/tan(35°)` m. Centres `(16+n+0.5,11−n+0.5)`
lie NW at distances `(n+0.5)√2` m. Their blocked/clear pattern and SE control
must match the geometric inequality, not a fitted shadow length.

**Fixed tolerances:** absolute irradiance error ≤1e-9 W/m², relative tolerance
zero. Mask/occupancy/difference identities are exact (NaNs compared as missing,
not zero). The last-shadow/first-clear centre bracket must contain the analytic
reach and be no wider than √2 m (+1e-12 m arithmetic tolerance). This bracket is
the prescribed diagonal sample spacing, not an allowed numerical irradiance
error. No tolerance or expectation may be changed just to obtain PASS.

### Execution path and planned checks

Use ordinary Windows OUEM `.venv/Scripts/python.exe`, pinned VoxCity 1.7.0
commit `fa212656305328a9a657973bae26f352bfe813bc`; assert installed provenance.
Public `Voxelizer.generate_combined` and `get_direct_solar_irradiance_map` build
and calculate cases A–D/F. Case E also uses unchanged OUEM `solar_pair`, including
its five public API calls and existing positive-ROI-effect/sign/mask guards.
No internal simulation function is called directly. Constructing scene metadata
and expected occupancy in the test isolates physics from input acquisition,
CR estimation, GIS and RunConfig; it is not an alternative production runner.

Observer H is derived from actual surface/air voxel indices and the installed
kernel's documented integer-height plus centre convention, then checked by two
public-API occlusion probes. Surface upper edge H=21, observer H=22.5: 1.5 m
above voxel surface, 2.5 m above both source/effective DEM in this flat example.
This does not authorize changing the existing observation definition.

## Results

The design/tests were committed before execution at `4aca8b0`. Initial run:
**4 passed / 2 failed**, retained in local `physical-sanity.log`. Investigation
found seven geometric corner touches (u+v=24) whose exact L is zero, but separate
floating-point sin(135°)/cos(135°) evaluation in the independent oracle produced
positive lengths 1.11e-16–3.55e-15 m. The engine correctly returned unobstructed
irradiance there. The oracle now uses the exact angular identity
cos(135°)=-sin(135°)=-1/√2, plus an explicit zero-length corner regression.
The box geometry, physical expectations, irradiance tolerance, shadow-length
bracket and VoxCity/OUEM implementation were not changed. This is a corrected
test-oracle arithmetic defect, not a relaxed acceptance criterion.

### Measured results

Final focused run: **7 passed in 9.73 s**, including the added analytic-oracle
corner check. Windows OUEM venv Python 3.11.9; VoxCity 1.7.0 at the fixed commit;
NumPy 2.4.6, Numba 0.68.0. Two Numba threads during the test module, restored
afterward. PEP 610 and all 136 installed source RECORD hashes verified;
this is not an independent upstream Git-tree comparison.

| Check | Independent expectation | Measured / comparison | Verdict |
|---|---|---|---|
| Unobstructed horizontal direct | 458.861149080837 W/m² at all 1,024 observers | min=max=458.861149080837; maximum absolute error 0 | PASS |
| Building mask and direction | 16 roof exclusions; NW shadow, clear SE; binary box-intersection oracle | 1,008 finite observers; 49 exact-zero shadow cells; all non-roof cells match, maximum error 0 | PASS |
| Building shadow length at observer plane | (8−1.5)/tan(35°)=9.282962043824 m from NW corner | Last shadow centre 9.192388155425 m, first clear 10.606601717798 m; bracket width √2 m and contains expectation | PASS |
| Thin TREE at (u,v)=(20,10) | L=2/sin(35°)=3.486893591242 m; T=0.123423202956; I=56.634112731822 W/m² | Same probe irradiance; full 1,024-column maximum error 4.97e-14 W/m² | PASS |
| Deep TREE at same probe | L=6/sin(35°)=10.460680773727 m; T=0.001880141077 <0.01, so API I=0 | Exact zero; full-grid maximum error 1.99e-13 W/m² | PASS |
| Transmission cutoff across deep-TREE grid | All T<0.01 become zero; attenuated T≥0.01 remain positive | 167 cut cells; largest cut T=0.005718789019, smallest retained T=0.014698717671 | PASS for these samples; exact threshold equality UNVERIFIED |
| Observer origin | Actual g=1, k=2; H=22.5, source/effective ground offset=2.5 m, surface offset=1.5 m | Both low-building probes agree: 1 m high gives I0, 2 m high gives zero at (16,11) | PASS for authored flat scene |
| Pure-TREE No-Canopy | Only TREE removed; all 1,024 values I0 | Finite common masks, exact non-TREE identity; comparison within fixed 1e-9 tolerance | PASS |
| Mixed OUEM pair / Difference | Same Building/surface/observers, roof NaN, nonnegative No-Canopy−Current | 1,008 common valid / 16 excluded; current oracle error 1.99e-13, absent error 0; 253 ROI reduction cells; exact stored subtraction | PASS |

Representative plan coordinates (u=north, v=east; centres in metres relative
to the scene origin; irradiance in W/m²):

| Position | Centre (u,v) | Role | Building-only irradiance |
|---|---|---|---:|
| SE control | (11.5,16.5) | Sunward of building | 458.861149080837 |
| NW near | (16.5,11.5) | Opposite azimuth; shadow | 0 (valid) |
| NW last sampled shadow | (22.5,5.5) | 9.192388 m from corner (16,12) | 0 (valid) |
| NW first sampled clear | (23.5,4.5) | 10.606602 m from same corner | 458.861149080837 |
| Footprint | (12.5,12.5) | Excluded roof observer | NaN (missing, not zero) |

The zero caused by the transmission cutoff is a numerical model rule: a
physical exp(-k·LAD·L) remains positive at finite L. Both numerical complete
shadow and cutoff zero remain valid observations; neither is roof NoData.

### Regression, evidence and reproduction

Related suite: **113 passed, 39 warnings in 73.18 s**. Warnings are existing
rasterio `PendingDeprecationWarning` for affine matrix multiplication in Voxel,
Solar and RunConfig fixtures; no warning was reported by the new focused tests.
Initial full suite: **1 failed, 1,010 passed, 9 skipped, 295 warnings in
462.98 s**. The unchanged historical
`test_komae_repair_qgis_export.py::test_cli_prints_path_and_areas` failed while
creating a synthetic GeoPackage (`unable to open database file`) under the
long sandbox temporary path. An isolated retry with a shorter, unused
repository-local `--basetemp` passed (1 test, 3.69 s). This supports a temporary
path/environment issue; the precise OS/GDAL limit was not independently proved.
No exporter, dependency or system setting was changed. A full short-workspace
retry was interrupted after multiple fixture failures. An isolated reproduction
identified sandbox `PermissionError: WinError 5` at the unchanged acquisition
module's `os.link`, which is required by its fail-closed atomic publish contract.
Do not weaken that contract to accommodate the test sandbox. The final full
retry uses the same OUEM venv and a fresh short workspace temporary root, with
a per-command sandbox override through approval review; no persistent approval,
security or environment setting is changed. Final result: **1,011 passed,
9 skipped, 295 warnings in 425.47 s**. Skips: four isolated-GIS-runtime tests
and five Windows symlink-privilege tests. Warnings: existing rasterio affine
deprecations and one source-H stat/fstat diagnostic UserWarning. The previously
failing GeoPackage CLI test passed; no product-code fix was needed.
Commands, from the repository root:

```powershell
.venv/Scripts/python.exe -m pytest -q -ra -s tests/test_b1_physical_sanity.py
.venv/Scripts/python.exe -m pytest -q -ra tests/test_b1_physical_sanity.py tests/test_canopy_shadow_poc.py tests/test_real_komae_voxel.py tests/test_real_komae_solar.py tests/test_shared_vertical_domain.py tests/test_e2e_config.py
.venv/Scripts/python.exe -m pytest -q -ra
# Use a NEW, unused ignored temporary directory; pytest manages its contents.
.venv/Scripts/python.exe -m pytest -q -ra --basetemp data/work/b1-full-approved-20261030-01
```

Local ignored evidence: `data/work/b1-physical-sanity/phase1-20261030-01/`.
`environment.json`, initial/final focused logs and `grazing-investigation.log`
retain the environment, measured values and initial-oracle investigation.
Final focused log SHA-256:
`54567696b8bb979bdbf0e39a62d635c841622ede31d1866a101a5d0515ab865e`.
Final full-suite `full-pytest-approved.log` SHA-256:
`4ca2e7342e372ec29ed75de66e35f7a28851d7ea29648935d88b546d95ef6e0d`.
No real-data model command or existing Run write was performed. Production
code, RunConfig, parameters, dependencies, Standard/Adapter and Acceptance are
unchanged. Existing direction/rotation, shared-Z and real-run records retain
their separate authority; this report does not retroactively certify them.

## Impact, limitations and next stage

No engine or OUEM numerical discrepancy was found in these scenes after the
independent oracle's exact-corner arithmetic correction. The audit's cautions
remain: 1.5 m is above the voxel surface rather than necessarily source ground;
strong default k/LAD attenuation and the 1% cutoff can yield large reductions.
Those are explanations of current behavior, not evidence of realistic canopy
effects. No physical parameter or observation definition should be adjusted
solely to match a preferred map.

UNVERIFIED: exact-cutoff equality/near-machine-epsilon threshold behavior,
non-flat physical-height accuracy, real crown geometry/LAD/season/weather,
exterior shadow coverage, and scientific error bounds. This phase checks the
specified simple geometries and fixed sun, not all ray/cell degeneracies.
Next: review observer-height interpretation and independently observed geometry;
then authorize narrowly scoped threshold, non-flat/rotated geometry or optical
sensitivity experiments as needed. Keep any real A/B rerun and changes to
scientific assumptions under separate authorization.
