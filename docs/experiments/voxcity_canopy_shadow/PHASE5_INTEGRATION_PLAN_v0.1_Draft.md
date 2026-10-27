# Phase 5 integration plan v0.1 — Draft (2026-10-27)

Entry points: [Completion Gate](PHASE4_COMPLETION_GATE_REVIEW_20261027.md) ·
[Repository inventory](REPOSITORY_INVENTORY_20261027.md).
Baseline main `56059467dde052ad95c8a666f18acb660c7622a4`.

This defines implementation/acceptance requirements for a **limited experimental
A/B/C comparison**, pending independent review. It does not alter the accepted
[Building Adapter](../../OUEM_VoxCity_Adapter_v0.1.md),
[Building](../../OUEM_Standard_Building_v0.1.md),
[Terrain](../../OUEM_Standard_Terrain_v0.1.md) or
[Canopy DRAFT](../../OUEM_Standard_Canopy_v0.1_Draft.md). No building integration,
new real-data processing, production Adapter or new tests are implemented here.

## 1. Pre-start decisions (Gate class A; not closed merely by writing this plan)

1. Freeze exact Building bytes+manifest, source/vertical evidence and chosen
   ROI/halo membership. Legacy canonical Building paths are absent on this
   checkout; the old A3 record has paths but no hashes. Search/selection of a
   different local artifact and its eligibility must be explicit. The tracked
   unresolved Converter/Building Z diagnosis is not a proven offset correction;
   obtain matched chosen-input evidence, or demonstrate an unaffected subset
   with review. Do not assume a new file is the accepted 111-building dataset.
2. Approve the projected common-grid experimental mapping below. Accepted
   Building rasterization uses an EPSG:4326/geodesic rectangle; it is not proven
   identical to Phase 2's explicit projected grid. Do not splice its arrays by
   equal shape or treat a new mapping as the accepted Adapter output.
3. Approve a **model-surface observer** using the unchanged public CPU ground-map
   route (Phase 4A option C). Report actual XYZ; no exact physical DEM+1.5m claim.
   If exact arbitrary physical observers are required, Phase 5 remains BLOCKED
   pending a separately reviewed tracing solution; do not compensate +0.5.
4. Approve common building-conditioned ground, source/mask retention, overlap
   order and comparison denominator. A is not a raw/unflattened terrain control.
   Unknowns cannot be filled as canopy-free. All A decisions require recorded
   review before Phase 5 integration implementation/real execution. Read-only
   data discovery and evidence collection to close them can occur beforehand.

## 2. Common grid, sources and mapping contract for the experiment

Initial proposed study profile: EPSG:6677, north-up source rasters to south-up
engine arrays once, isotropic **s=1m**, evaluation ROI
`[-23320,-40760,-23256,-40696]`, 64×64 cells. Start with 32m halo domain
`[-23352,-40792,-23224,-40664]`, 128×128 cells. Size/bounds/affine/centres and
rotation are explicit metadata, not nationwide requirements or inferred from
array shape. A sensitivity case at 0.5m is a separate later run, not mixed into
this primary comparison.

Use unchanged canonical Standard Terrain and Building. Keep existing Height
Envelope absolute top/bottom, state, source samples/evidence and hashes. Sample
Terrain to the same approved centres and compare to envelope generation samples
before any engine transformation. Preserve CHM/source support, effective masks,
original height sign class and all envelope flags. Require valid inputs across
the complete occluder domain and intended comparison region for this first run;
unknown surrounding occluders remain a stated scientific limitation.

**Projected Building mapping proposal:** derive footprints and all-surface
absolute top from the canonical Standard geometry with the accepted normalization
semantics as a reference, preserving ouem_id/source_id. Use the explicit projected
cell polygons, precise positive-area intersection (boundary-only contact does
not allocate a cell), and a versioned deterministic numeric ID map. If more than
one footprint claims a cell, record all candidates; select maximum intersection
area, breaking exact ties by stable ouem_id. This is a proposed experimental
cell-assignment policy, **not** an amendment to accepted precise rasterization.
It needs independent grid/ID/segment fixtures and approval under class A before
implementation. Do not silently drop zero-allocation or crossing buildings.

A registered source building top is max(all original surface Z), as in the
existing contract, not measuredHeight or maxZ-minZ. Keep the full source extent
for objects that intersect the model domain; report omitted exterior coverage.
The new experimental mapping may reuse unchanged normalization/ID helpers only
after interface validation; canonical geometry and accepted geographic Adapter
artifacts are not rewritten. If this mapping cannot be verified, stop and
revise the plan; a geographic grid-master alternative requires new review,
sampling tests and declared bounds, not a silent fallback.

## 3. Common terrain conditioning — chosen design

Let D_raw be the common sampled absolute Terrain and L the **fixed reference
Building ID grid** from the approved mapping, identical in all cases.
Define D_eff by assigning mean(D_raw[L=id]) to every nonzero reference ID and
leaving ID=0 cells unchanged; D0=min(D_eff). Preserve D_raw, D_eff, D0, L and
all source identifiers/digests separately.

The pinned Voxelizer uses IDs for ground processing even when building height
and segment arrays are empty (already characterized by the Phase 4A fixture).
Use that behavior explicitly: **all three calls receive the same D_raw and L**.
A has empty building segments/heights, while B/C carry the same real building
segments/heights. Therefore the engine performs the same per-ID averaging and
re-origin in A/B/C; building removal does not restore a different terrain.
Reference IDs in A are conditioning metadata, not evidence of BUILDING occupancy.
Keep `reference_building_ids`, `buildings_enabled`, scene geometry and voxel
class counts distinct in each run record.

| Input / property | A: terrain only* | B: terrain + buildings | C: terrain + buildings + canopy |
|---|---|---|---|
| D_raw and reference L | Identical | Identical | Identical |
| Effective ground / D0 / g | Identical, audited | Identical, audited | Identical, audited |
| Building heights/segments | Zero / empty | Frozen real arrays | Same arrays as B |
| Canopy source evidence | Retained, scenario disabled | Retained, scenario disabled | Retained, scenario enabled |
| Canopy relative arrays | 0/0 | 0/0 | Derived from absolute envelope and D_eff |
| BUILDING voxels | 0 | Audited real occupancy | Exactly same BUILDING mask as B |
| TREE voxels | 0 | 0 | After documented building overwrite |

*Label A as **Terrain-only occupancy on common building-conditioned model ground**.
It is not the original raw-terrain condition from Phase 2. A raw-terrain-only
control would be an additional compound-terrain sensitivity, not the matched
A/B/C contrast. Never compare raw A to conditioned B/C as a building-only effect.

Do not input preflattened ground to one case and raw ground to another; do not
use L=0 only in A. Audit actual processed arrays, D0, ground indices and GROUND /
land-cover voxel masks, not just the theoretical averaging equation. Any unequal
ground geometry blocks solar comparison. No invented elevation offset is used. Common air-only Z padding must cover
all scene geometry and actual observer origins at the same D0/indices; do not
rely on the terrain-only Voxelizer allocation to provide observation air.

## 4. Absolute Z, precision and collision diagnostics

For each building id, G_eff_abs=mean(D_raw[L=id]); relative building top is
Z_top_abs(id)-G_eff_abs, with explicit ground/base segment policy. Retain the
accepted min_height=0 policy only for its matching source/representation;
complex segments or alternate bases require separate review, not guessed values.
For positive-depth canopy cells, T=canopy_top_z-D_eff and B=canopy_bottom_z-D_eff.
This uses the **same engine-effective ground**, and subtracts it once. Original
absolute Height Envelope, sampled physical ground and original state stay intact.

A positive-height source with collapsed Float32 envelope depth is diagnosed and
counted; a genuine zero-height estimate is a separate class. Both can have no
TREE under the experimental mapping, without an absence claim. If positive-depth
canopy becomes negative/inconsistent relative to D_eff, mark a model-ground
conflict and stop this first run. Do not clip to zero, raise the crown, subtract
an unreviewed offset, or assume a building will hide the conflict.

Ground index remains `g=int(float32(D_eff-D0)/s+0.5)+1`. Record faces
`D0+(g+rounded_relative)*s` and voxel centres `D0+(k+0.5)*s`. Keep ground +s,
DEM rounding/casting, canopy rounding/casting and thin-crown expansion separate.
Building segment rounding and canopy Float32 paths need near-half fixtures; no
universal 2m canopy tolerance is inherited from historical A3 roof QA.

Generate an audited pre-collision canopy mask/count field and a building mask,
then use the pinned write order (building overwrites overlapping TREE indices).
Report pre/post TREE voxel counts, removed TREE voxels/columns and affected IDs;
retain source validity/presence-evidence status unchanged. Check exact set
relation `TREE_post = TREE_pre AND NOT BUILDING_B`, and B/C BUILDING equality.
Tree cells above a building are not removed merely because 2-D footprints overlap.
This records model precedence, not a physically accepted collision solution.

## 5. Observer and A/B/C mask contract

Use common experimental walkable surface code 1, identical solar route and
model ground. Pin existing CPU `get_direct_solar_irradiance_map`, roof inclusion
False. A common comparison mask is **predeclared before observing irradiance**:
ROI AND valid source/envelope support AND outside any model Building column
from the frozen reference building geometry. Exclude these columns in **all**
cases, including A; retain exclusion reasons/counts and complete output maps.
This conservatively avoids comparing A ground points with invalid B rooftop /
solid-origin points. It is not an ecological/land-cover mask.

For candidate points, verify actual public-map transition and actual origin
XYZ match in A/B/C, including the int(h/s) and tracer +0.5 rule. TREE origins
are allowed only under the recorded existing model-map interpretation; solid,
outside or nonfinite origins are invalid. If any predeclared comparison point
is invalid in any scenario, stop: do not post-hoc select a favourable mask.
A reduced intersection requires an explicit revised mask, exclusion report and
review before rerun. NaN is never replaced by zero; report denominators and
excluded area beside every mean/count. A nonempty predetermined mask is required.

## 6. Fixed solar and halo conditions

Initial conditions: 2026-06-21 12:00 JST, Astral at the same ROI centre,
DNI=800 W/m², k=.6, LAD=1, existing CR=.60, nominal public h=1.5m and no exact
physical-height claim. Use the same true/grid-north rotation/helper, no extra
180-degree reversal. Recalculate sun and record exact values; compare to the
Phase 2 record when using the same location/time. No building-face fast-path
substitution, diffuse/global/annual or thermal inference.

Reassess 32m halo using **Building plus canopy plus terrain** ceilings, D0,
rounding/face allowances and actual solar elevation. The old canopy-only bound
is insufficient proof for taller Buildings. Add a source-covered larger-halo
check and edge-band summary. With this ROI, the stored envelope permits at most
40m symmetric halo (south edge reaches −40800); do not extrapolate past that.
If the conservative ray bound or convergence cannot fit available support,
stop or obtain separately authorized broader inputs / reviewed ROI. Unknown
exterior obstructions are never asserted absent. Record boundary limitations
and any remaining CONDITIONAL interpretation even when internal QA passes.

## 7. Implementation and acceptance checklist (no new tests in this audit)

| Gate | Required future check | Acceptance / stop rule |
|---|---|---|
| P5-01 Identity | Chosen Building/DEM/envelope/manifest/evidence hashes, pin, code bytes, worktree, environment | Complete frozen packet and closed class A review; no path-only identification |
| P5-02 Grid/IDs | Exact affine, centres, orientation, logical IDs, footprint crossings/ties and sources | One approved deterministic projected grid; independent fixture for allocation and no unexplained loss |
| P5-03 Common ground | Same D_raw/L; actual D_eff/D0/g and GROUND/surface masks across scenarios | Exact equality; mismatch blocks comparison |
| P5-04 Z/rounding | Source absolute Z, effective subtraction, Float32/segment rounding, near-half/thin crowns | Actual faces match recorded pinned arithmetic; model-ground conflict blocks; no hidden correction |
| P5-05 Scenario geometry | A no buildings/trees; B buildings/no trees; C same buildings + audited canopy | Expected occupancy class sets and common air padding; never infer presence from labels |
| P5-06 Collision | Pre/post TREE and Building overlap | Exact set relation and per-ID/count/volume audit; no 2-D blanket removal |
| P5-07 State | Source support/validity/height class, original state, representation loss | Retained sidecars and counts; missing/unknown-to-zero conversion blocks |
| P5-08 Origins/masks | Fixed non-building-column comparison mask and actual A/B/C XYZ | Same actual points, all predetermined cells finite; no post-hoc silent filtering |
| P5-09 Direction/optics | Known sun/rotation, synthetic analytic attenuation/obstacle direction | Same CPU route and assumptions, fixture-defined numerical tolerance recorded before real outputs |
| P5-10 Halo | All-scene conservative bound, larger covered halo, edge impact | Bound fits data support; unresolved geometric boundary influence blocks the intended ROI comparison |
| P5-11 Solar outputs | A/B/C maps W/m² and B−A, C−B, C−A on identical fixed mask | Raw differences/distributions/NaN counts; unexpected increases under identical rays/added occluders require investigation, not clipping |
| P5-12 Reproducibility | Repeat same frozen packet, hashes/arrays, timing/memory and source nonmutation | Numeric/grid/state reproducibility demonstrated; byte differences explained separately; no acceptance by exit code alone |

Phase 5 should be a new isolated experimental module/runner with focused tests,
using validated helpers without editing frozen Phase 2/3 protocols or accepted
contracts. Implement deterministic preparation/fixtures first, inspect all model
geometry/state before radiation, then perform authorized small real runs into
new directories. Exact module names and helper extraction are implementation
choices after class A closure; no refactor is authorized by this plan.

Result status: PASS only when the scoped technical gates pass; CONDITIONAL PASS
when comparison is valid but explicitly stated interpretation limits remain;
BLOCKED for unmet A decisions, geometry/state/point/mask/coverage failures or an
unusable CPU route. A technical pass never confers full Standard Canopy, physical
observer accuracy, Building source correctness beyond reviewed evidence, or
scientific/production acceptance. Publish bounded evidence in a Draft PR and
wait for independent review; no automatic merge or formal reacceptance.
