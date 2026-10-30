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
All selected rays avoid zero-length grazing ambiguity at a box top.

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

PENDING execution. Expectations and tolerances above are fixed before running.
