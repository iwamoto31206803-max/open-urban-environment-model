# Step 4A — Source-H VoxCity Adapter contract and vertical datum audit

## 1. Executive Summary

**CONDITIONAL.** An independent, explicitly dispatched **experimental 2.5D
Adapter v0.2 candidate** is feasible for controlled synthetic inputs. A schema
whitelist extension is insufficient. Real Building/Terrain fusion is **not ready**
until exact-file provenance, compatible vertical declarations/pair review,
full coverage and common-grid/ground/overlap gates are established. No Adapter
implementation or real-data fusion is performed by this audit.

Baseline fetched main: **`2c76c956bdce515395f7044ceb2c5b2a8c91f854`**, PR #91
merged, including its explicit argument↔Native-profile binding fix. Inspection:
2026-10-28 JST. [Governance](../OUEM_Documentation_Governance_v0.1.md) applies.
Source-H eligibility stays **NOT_ESTABLISHED**, human review/Formal Acceptance
**NOT_VERIFIED**, and Phase 5 A1–A4 **OPEN**. This report proposes implementation
boundaries for review; it does not approve a formal contract or a real dataset.

Evidence labels below: **CODE** means inspected pinned/local code; **TEST** means
existing tests actually rerun here; **HISTORICAL** means a linked prior execution;
**PROPOSED / OPEN** is a recommendation or unverified condition. Code-derived
failure possibilities are not claimed as newly executed reproductions.

### Decisions A–F

| Question | Conclusion and boundary |
|---|---|
| A. Can VoxCity use absolute Building H directly? | **No for the audited GeoDataFrame→building raster→`Voxelizer.generate_combined` route**: it consumes 2D footprints and ground-relative interval endpoints, not a Standard 3D H model or vertical CRS. Other package CityGML/mesh routes are outside this audit; no universal impossibility claim. |
| B. Is relative conversion needed? | **Yes**: `h_b=max(H_vertices_b)-G_b`, where `G_b` is the mean of actual engine DEM cells assigned to ID b, conditional on compatible vertical references. Preserve original H; subtract ground once; do not feed H as `height`. |
| C. How is datum compatibility established? | **OPEN for a real chosen pair**: exact Raw/Converter/Native/Standard chain and source declarations plus Terrain acquisition/Native/Standard evidence and an explicit limited compatibility review. EPSG:6677, the word T.P., positive derived height and hash agreement alone do not establish compatibility/accuracy. |
| D. Are candidate Standard attributes/geometry sufficient? | Sufficient for the core **2.5D arithmetic**, not sufficient alone for safe fusion. Also require verified manifest/receipt chain, masks/coverage, common grid, Terrain data, declared-ground compatibility and pin/operation evidence. NULL `source_lod` is not a reason to guess: verify `selected_lod_by_id` and source correspondence. |
| E. Keep LoD2 in Adapter? | Keep full LoD2 in immutable Standard and provenance. Explicit lossy **2D support + maximum roof H** is appropriate for this bounded public-raster PoC, with loss diagnostics. It does not preserve roof slopes, wall surfaces, overhang/underpass structure or actual 3D roof irradiance. A full-LoD2 downstream objective needs a separate route/review. |
| F. What before implementation/execution? | Synthetic validator/geometry/ground/grid fixtures may proceed after review of this proposal. Real fusion additionally needs the pair-specific evidence and gates in §9. Unknown ground/datum/ownership must fail, without an inferred offset or silently dropped IDs. |

## 2. Existing Adapter contract and OUEM evidence

Read together: [Standard Building v0.1](../OUEM_Standard_Building_v0.1.md),
[Terrain v0.1](../OUEM_Standard_Terrain_v0.1.md),
[Adapter v0.1](../OUEM_VoxCity_Adapter_v0.1.md),
[#88 source-H design](OUEM_Source_H_Native_Building_Profile_Design_20261027.md),
[#89 foundation](../Source_H_Building_Provenance_Foundation_v0.1.md),
[#90 ingestion](../Source_H_Native_Building_Ingestion_v0.1.md),
[#91 Step 3](../Source_H_Standard_Building_v0.1.md), and
[Building Current State](../status/BUILDING_CURRENT_STATE.md).

All following OUEM code positions are at the baseline above, in
[`src/ouem/adapters/voxcity/__init__.py`](../../src/ouem/adapters/voxcity/__init__.py):

| CODE: function / lines | Actual behavior, not an approval claim |
|---|---|
| `adapt_standard_to_voxcity`, 443–506 | Requires adjacent Building **v0.1** and Terrain v0.1 schema strings; new Standard v0.2 is refused. Reads JSON, runs the vertical string gate, then invokes worker. Hashes current inputs for the *outgoing* Adapter record; does not authenticate formal approval or compare Standard bytes to a v0.2 declared output hash/receipt. |
| `check_vertical_compatibility`, 82–92 | Requires Terrain `verified` or `source-declared`, then normalized names containing `tp`. This is a declaration/string gate, **not typed datum equivalence or proof of independent survey validity**. v0.2 does not have the legacy `z_reference` string. |
| `_z_values`, 121–128; `derive_attributes`, 95–114 | Capture Z before 2D projection; top=max(all source Z), geometry bottom=min(Z), `ground_eff_abs`=mean assigned raw DEM, height=top−mean, `min_height=0`. Empty/nonfinite inputs/nonpositive height fail. No use of `measured_height`, maxZ−minZ or arbitrary source DEM point. |
| `numeric_id_mapping`, 37–52 | Lexically sorted unique `ouem_id` → positive `voxcity_id`, duplicated into engine property `id`; zero is background. This map is dataset/run scoped, not an invariant numeric ID across changed selections. |
| `build_normalized_footprint`, 131–198 | Recursively collects polygon surfaces, force-2D, drops zero-area XY projections (walls), repairs invalid parts, normalizes/sorts/unions positive-area support. No Standard modification. Nonpolygonal components can be ignored during polygon collection/repair, so new-lane validation must reject unsupported source structures first. |
| `_set_normalized_footprints` / `_to_voxcity_building_crs`, 201–230 | Explicitly retain input CRS on replacement GeoSeries, then transform footprints 6677→4326 for the geographic engine rectangle. No H transforms: heights already captured. |
| `_repair_post_crs`, 246–334 | Conditional `make_valid` only for invalid transformed footprints; reject residual collections/nonpolygonal output, preserve valid geometry, record projected shape differences. No accepted universal repair-deformation tolerance. |
| `_run_voxcity_grids`, 337–433 | Checks runtime version string 1.7.0, reads `building` in6677, keeps only `ouem_id`/geometry before deriving IDs/heights. The Standard `source_id` is **not retained in current output**. Rectangle comes from transformed building total bounds. Bootstrap height1, then up to8 rasterization/height updates until ID grid stable. |
| worker 379–414 | Local Terrain rasterized at that rectangle, finite check, precise building rasterization. Every original ID needs assigned cells. Validates processed ground against absolute or raw-min-shifted expected ground using `np.allclose(atol=1e-9)` with its **default rtol**; not an exact-height check. |
| `aoi` argument, 443–465/490 | **Does not select/clip or control the worker grid**; if provided, it changes recorded manifest AOI only. It must not be advertised as an actual computation-domain selector in v0.2. |

The canonical Standardizer selected complete buildings intersecting its AOI;
Adapter union/reprojection does not clip them. Engine rasterization assigns
cells only within its rectangle. This is not equivalent to clipping Standard
geometry or to proving full external occluder coverage.

HISTORICAL acceptance remains bounded to its recorded artifacts/conditions:
[A1](../../experiments/a1_e2e_pilot/README.md),
[A3](../acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md), and
[A3 runner](../../scripts/work/voxcity_komae_a3_acceptance.py).
The runner deliberately audits overlap segment envelopes rather than attributing
generic BUILDING voxels to the last-wins ID. Neither that record nor its 111
count accepts new source-H bytes, a new grid, solar calculations or generic overlap.

## 3. Pinned VoxCity source, height and shape handling

### 3.1 Identity and source evidence

Installed distribution version **1.7.0**. `importlib.metadata.distribution('voxcity')`
and `direct_url.json` identify `https://github.com/kunifujiwara/VoxCity.git` at
**`fa212656305328a9a657973bae26f352bfe813bc`**, matching `pyproject.toml` and
OUEM constants. The old runtime worker checks the version string, **not commit
authenticity**. For this audit, the following **10 actual source files** were
also fetched at that immutable commit and compared to installed files:
all match **after CRLF→LF normalization**, not raw-byte equality. This is
selected-source identity checking, not verification of every package/dependency.

| Pinned file / function evidence | SHA-256 of fetched LF content |
|---|---|
| [buildings.py:62–197](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/geoprocessor/raster/buildings.py#L62-L197), `create_building_height_grid_from_gdf_polygon` | `2bad0ea303c9a2c819d9d95a3a98e133422b3e979b76d0e593e0db8657ac1a58` |
| [buildings_precise.py:49–225](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/geoprocessor/raster/buildings_precise.py#L49-L225), collection/intersection | `849e0a8e039cc69cf083f452b41fedcb64cc039e6ad441eecae91a24eb62cb94` |
| [raster.py:51–105](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/geoprocessor/raster/raster.py#L51-L105), local DEM rasterizer | `db0676f08f810d3cadf6578dffb9d27c301dc19600c31231d61642a2721ae47e` |
| [core.py:48–89](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/geoprocessor/raster/core.py#L48-L89), `process_grid`; [grid construction:153–216](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/geoprocessor/raster/core.py#L153-L216) | `0bcb254f86af0e7618f131c6ecf01f4e8c17932cfcebe4f285b523c8530f0452` |
| [overlap.py:9–82](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/geoprocessor/overlap.py#L9-L82), `process_building_footprints_by_overlap` | `9d14126cdcac0b3f7554d06b88ed356fe1c524e7526e536d61249b3e239514fb` |
| [voxelizer.py:39–120](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/generator/voxelizer.py#L39-L120), packing/kernel; [generate_combined:158–244](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/generator/voxelizer.py#L158-L244) | `6590886b01529d0a33be70d91672016fc8f1039dfc3d36ba355ece1a5888dd60` |
| [grids.py:193–324](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/generator/grids.py#L193-L324), `get_building_height_grid` | `37999981251cb95e69874fa57641592548935c7d90ebaec30a827c4b853b03d0` |
| [projector.py](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/utils/projector.py), grid geometry helpers | `23e17a5195a6335a4074b968f3c7d8b238c8a087afd0b374b29b1061cf4dcdf5` |
| [pipeline.py:97–173](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/generator/pipeline.py#L97-L173), metadata/assembly; [296–333](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/generator/pipeline.py#L296-L333) | `ca8ca2f437fd72f25fc4af7186c38751a0a9f82109d392805fe801f623f5ed24` |
| [models.py:10–55](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/models.py#L10-L55), grid/scene metadata; [78–116](https://github.com/kunifujiwara/VoxCity/blob/fa212656305328a9a657973bae26f352bfe813bc/src/voxcity/models.py#L78-L116) | `9cd51416ea6cb80de2269de4d0184c252e81be210f73e45b708ad12a50997cf9` |

For comparison with older local hashes, installed CRLF `voxelizer.py` SHA is
`1c3402651e8eb6a6e706010893f4ac90276f5d0e1e07aece5dd4dc000664cc5c`,
and `raster/core.py` is
`99d346819fb0b6daa0683d2f3f13caadb91005c38896c28439308207f171c402`.
Local ignored audit scratch: `data/work/source-h-adapter-audit/20261028-01/`.
It contains fetched source snapshots and all installed/remote hashes; they are
not committed. The pinned links and hashes above make this record independently
traceable without relying exclusively on scratch files.

### 3.2 Engine call graph and simplifications — CODE

`Adapter._run_voxcity_grids → create_dem_grid_from_geotiff_polygon` and
`create_building_height_grid_from_gdf_polygon(overlapping_footprint=True)`;
the latter filters by geographic bounding box, invokes the overlap preprocessor,
then uses precise geometry intersection. `get_building_height_grid` accepts a
supplied GeoDataFrame, but the OUEM worker calls the raster function directly.
The A3 runner later calls `Voxelizer.generate_combined`; the Adapter itself
produces GeoJSON/manifest, **not voxels or solar output**.

| Engine stage | Confirmed behavior and risk for v0.2 |
|---|---|
| Geographic grid | Rectangle lon/lat, mesh size metres, geodesic side lengths and angular increments; cell centres generated from adjusted grid spacing. Not automatically the same centres/affine as a projected EPSG:6677 1 m raster, even if array shapes match. Standard H is not involved in this XY conversion. |
| DEM sampling | Raster band1, pixel centres transformed to a local UTM metric interpolation frame, `griddata` nearest when `dem_interpolation=False`. **All values <−1000 become0**, without checking the raster validity mask. Nearest interpolation alone is not a bounds/coverage gate and can return edge values outside the original sample support. A finite result is not proof of coverage or valid NoData handling. |
| Overlap preprocessor | Always invoked, even in precise mode. Projects to3857 for area comparison and can remap a smaller footprint's `id` to a larger overlapping one when intersection/current area >0.5. It changes IDs, not a transparent canonical-ID-preserving union. Current Adapter may then fail on an original ID with no assigned cell; no claim that historical accepted data encountered this case. |
| Precise allocation | Requires cell intersection fraction **>0.3**; not simply any positive overlap. Orders candidates by height descending, tie by input index. Stores every qualifying interval `[min_height,height]`, a maximum height grid, but only one last-written ID per cell. Cell ID, interval owners and maximum roof source are not equivalent. Courtyard rings participate in area intersection; coarse cells can still span holes. |
| Default/fill handling | Optional height complement paths exist but OUEM does not supply them. Voxelizer converts NaN building heights/nested intervals to10; new Adapter must reject invalids first, never rely on that fallback. `measured_height` is not an absolute elevation input. |
| Ground/voxel | Per-ID mean conditioning, re-origin, discrete intervals and ground+1 layer; see §5. Building segments are written after TREE, overwriting overlapping TREE labels. Final BUILDING_CODE does not retain source Building IDs. |
| Scene/output | `GridMetadata` has CRS/bounds/mesh, **no intrinsic vertical CRS or absolute Z origin**. Low-level voxel arrays have no geodetic metadata. Default assembly stores supplied DEM separately; it is not proof that voxel indices carry T.P. `to_xarray` exposes local centre coordinates `(k+0.5)*s`, without adding an absolute vertical origin. Extra metadata can be supplied, but none is inferred here. |

## 4. Source-H Standard gaps and geometry policy

The #91 output is horizontal6677 + vertical6695 gravity-related H, identity_H,
source horizontal6668/compound6697, `building` layer, candidate v0.2. It has all
ordered XYZ, source/OUEM IDs and nullable legacy-mapped attributes; its manifest
adds hash-linked source chain and per-ID LoD2 evidence. [Step 3 geometry QA](../../src/ouem/standardize/building/source_h_geometry.py)
and [orchestrator](../../src/ouem/standardize/building/source_h.py) are implemented,
but no public standalone complete **Standard v0.2 consumer validator** currently
authenticates all these records and input bytes on behalf of an Adapter.

| Topic | Existing behavior → required candidate treatment | Risk / required test |
|---|---|---|
| Polygon/MultiPolygon/Collection | Recursively projected polygons → strict recursive polygon-only 3D type/finite/ID gate **before** any maxZ or footprint operation; reject unknown types/empty/2D inputs | Existing generic polygon collector can drop lines/points; assert unsupported mixed collections fail rather than affect maxZ or disappear |
| Roof/wall/ground surfaces | All positive-area XY support union, global maximum H; vertical-wall XY area0 discarded → preserve canonical LoD2, report source/retained/discarded counts and top-source correspondence | Deliberate 2.5D loss, not all-vertex Adapter preservation; test sloping/stepped roofs, disconnected components, wall/roof overhang support |
| Interior rings | Rings preserved in source polygons but union/repair/raster resolution can change hole support → record hole/area/component diagnostics before/after | Test courtyard clear cells and partial coverage; no automatic `is_inner` conversion or assertion of exact courtyard voxel geometry |
| ID/attributes | `ouem_id` and numeric engine ID survive; legacy worker discards `source_id` → retain source/OUEM/numeric bijection in candidate output/audit | Reject duplicates, unassigned/remapped/vanished IDs and unresolved per-cell multiple owners; nullable LoD/height stay nullable, never substitute measured height for roof H |
| AOI | Standard whole-building selection; Adapter auto bounds and metadata-only AOI → **explicit grid-master rectangle/ROI/halo** must control every actual grid call | Test boundary crossing, full source geometry retention, actual centres/coverage and manifest-domain agreement; do not reuse the old AOI argument as implementation |
| XY/georeferencing | Standard6677→2D footprint4326 → document actual axis/grid mapping and roundtrip diagnostics | Native height never goes through 4979/geoid. Reject unknown CRS/axis; approved projected-grid alternative is a separate mapping decision |
| Terrain placement | ID-specific ground mean and constant min_height0 → ordinary grounded-building representation only, with explicit pair review | Base/roof gaps and basement/elevated structures need separate semantics; geometry minH is a diagnostic, not automatically Terrain |

## 5. Vertical references and ground alignment

### 5.1 Five distinct quantities

1. `H_top(b)` / all Standard vertices: absolute source-declared H, no h conversion.
2. `D_raw(i,j)`: sampled absolute Terrain elevation under its own declaration.
3. `h_b=H_top(b)−G_b`: derived relative building top above **engine-effective**
   ground, not a second absolute elevation and not measuredHeight.
4. Define final cell labels L, per-ID conditioned absolute `D_eff`, and
   **`D0_eff=min(D_eff)`**. In the audited optimized engine,
   `d=D_eff−D0_eff`; it is not generally `D_raw−min(D_raw)`.
5. Voxel indices/centres are model-local. For a known D0 and isotropic size s,
   absolute interpretation would be `D0_eff+(k+0.5)*s` for a centre, `D0_eff+k*s`
   for a face; this needs a recorded datum/origin, not a horizontal CRS label.

CODE: `generate_combined` first subtracts raw DEM minimum, then `process_grid`
averages IDs **and subtracts the minimum again**. Algebraically, with unchanged
labels and ordinary finite inputs, this yields `D_eff−min(D_eff)`. Ground is
`g=int(float32(d)/s+0.5)+1` on the Numba path; packed building interval endpoints
are rounded from float64 before adding g. Thus model roof faces differ from
the continuous target through ground rounding, segment rounding and +1 layer.
Do not introduce a compensating −1 m or inherited universal roof tolerance.

TEST: [Phase 4A fixtures](../../tests/test_canopy_observer_geometry.py)
`test_building_ground_processing_can_change_minimum_reference` use raw
`[[10,12],[11,13]]`, ID1 over the first row: effective DEM becomes
`[[11,11],[11,13]]`, with D0_eff=11 rather than raw minimum10. Existing Adapter
code tests normalized ground with the **raw** minimum; this can reject such a
valid conditioning case. This conditional incompatibility is CODE + the existing
engine fixture, **not a newly run full Adapter reproduction**. v0.2 must compute
and audit actual raw/effective arrays/D0 instead of inheriting that check blindly.

For overlaps, each interval h_b may have been computed against G_b, while its
cell uses ground determined by **L(cell)**, possibly another ID. Without rounding,
that cell reconstructs `H_top(b)+(G_L−G_b)`, not necessarily H_top(b). ID remapping
and interval-owner loss make this more than a pure geometric union issue.
Initial v0.2 should fail on remapping/multiple qualifying owners; general overlap
and alternative per-segment bases remain OPEN, not silently grouped or averaged.

### 5.2 Evidence needed for compatible source-declared elevations

[Terrain source correction](../acceptance/OUEM_A2_Terrain_Source_Provenance_Correction_20261026.md)
and [Terrain reproducibility](../acceptance/OUEM_A2_Terrain_Reproducibility_Verification_20261026.md)
support the identified Tokyo Tama DEM's **source-declared T.P.**, not independent
survey accuracy. [PLATEAU acquisition](../experiments/voxcity_canopy_shadow/PHASE5_PLATEAU_ACQUISITION_20261027.md)
supports actual Raw source CRS/declarations but expressly does not validate its
Converter→Native→Standard chain. #87/#90/#91's executed correspondence uses
synthetic authored source H, not a real municipality conversion.

Before using a real pair: select exact Building and Terrain bytes/records;
recheck their hashes, source declarations, units, coordinate operations and
coverage; bind a review to those exact identities/scope. It must explain why
the declared H and T.P. ground may be combined, acquisition epochs/local-ground
differences and remaining uncertainty. Match actual source GroundSurface/known
ground control points through the chosen conversion where available. Global
min geometry H or a roof is not automatically a ground control observation.
No new alignment, independent accuracy or professional review is claimed here.

An explicit limited exploratory compatibility review could authorize an
experimental pairing while overall eligibility remains NOT_ESTABLISHED; it
cannot promote declarations to surveyed truth or close Phase 5 Gates. Absent
that review/evidence, numerical real-data fusion stays blocked. Unknown/different
references fail; never apply an estimated datum offset, 37 m constant or relabel h.

## 6. Adapter v0.2 candidate design — PROPOSED

Implement a **separate module/API/manifest lane**. Preserve v0.1 behavior,
Standardizer, accepted artifacts and old receipts. A candidate output schema
name/version and review-binding format still require review; do not emit new
semantics under the old v0.1 schema or simply whitelist Standard v0.2.

1. **Exact dispatch:** require supported source-H profile plus Standard manifest
   `ouem-standard-building-manifest/v0.2`; argument/record profile must match.
   No EPSG-only inference, old4979 fallback or implicit migrated receipt.
2. **Consumer validation first:** strict JSON/schema; adjacent Standard receipt
   binds actual manifest/output SHA and size/layer. Revalidate the referenced
   Native manifest/receipt, all Raw/Converter/Native artifacts and source-chain
   agreement, not just the embedded historical snapshot. Verify actual Standard
   GPKG WKT1/WKT2/extension, table/BLOB6677/XYZ/IDs, full H preservation and
   horizontal mapping against Native. Keep failures field/artifact traceable.
3. **Separate CRS/semantics gate:** horizontal6677; vertical quantity H, CRS6695,
   metre, identity_H and source6668/6697; Terrain masks and explicit vertical
   reference/source. Do not synthesize a legacy `z_reference` containing T.P.
   just to pass the old string check. Verify a hash-bound pair review/mode.
4. **Geometry policy:** strict supported polygon-only input; capture original H
   before force2D; reuse unchanged pure normalization/ID/arithmetic helpers only
   after explicit interface tests. Record repair/discard/union/reprojection
   effects; fail invalid/nonpolygonal results and unspecified deformation policy.
   New orchestrator must not treat private `_run_voxcity_grids` as a complete
   safe boundary: it lacks the required explicit domain/mask/ownership controls.
5. **Common grid and coverage:** initial reference option is the pinned geographic
   public-raster route with explicitly supplied rectangle and actual cell centres.
   Require all intended source/support cells in-domain, unmasked and finite **before**
   calling the engine DEM sampler; prohibit −9999→0 or nearest extrapolation from
   qualifying as valid coverage. Record source affine/CRS/masks, centres, shape,
   array axes, spacing/rotation, ROI/halo. This does not approve alignment with
   the projected Canopy grid; that Phase 5 decision remains OPEN.
6. **Relative-height/ownership:** single-owner initial scope, audited original→
   returned engine ID map, no missing IDs, exact captured grid/segment ownership.
   Derive positive h_b from the final G_b, min_height0 only for explicitly reviewed
   ordinary grounded-building semantics. Require convergence of actual relevant
   grid/ID/segment content, not only equal shapes. Persist raw/effective DEM,
   D0_eff, ground indices, top target/derived height, rounding/casting diagnostics.
7. **Publication/result states:** fresh no-clobber run, stage/reopen/hash/QA then
   completion marker, handled-failure rollback. Bind output, inputs, pin/source
   hashes, method/version, ID/ground/coverage diagnostics and limitations in a new
   record. Technical COMPLETED/QA PASS, pair compatibility scope, source-H
   eligibility NOT_ESTABLISHED, human review/Formal Acceptance NOT_VERIFIED remain
   distinct. A technical compatibility review is not a formal eligibility approval.

**H passing condition:** canonical absolute H is immutable; only the explicitly
derived model-relative h_b is supplied to the raster API. H is not transformed
vertically. The subtraction is permitted only after the pair gate. Output
model coordinates require D0_eff/datum metadata to be interpreted absolutely;
neither GeoJSON CRS4326 nor voxel metadata alone carries absolute T.P. semantics.

## 7. Risks, priorities and OPEN questions

| Issue | Required action / status |
|---|---|
| Actual real source-H Standard/Terrain pair and vertical review | **OPEN, before real fusion.** Synthetic preservation does not establish T.P. accuracy or real dataset eligibility. |
| No standalone complete v0.2 consumer validator | **Required in Step4B**, including Standard receipt/hash/Native-chain agreement and actual geometry. Existing foundation does not validate Standard v0.2 automatically. |
| DEM NoData→0 and nearest outside support | **Required before any candidate engine run**, prove support/masks independently; do not patch VoxCity or change Terrain. Invalid-source fixtures must fail upstream. |
| Metadata-only AOI / projected-vs-geographic mismatch | **Required explicit domain before candidate run**. Phase 5 common projected mapping still needs its existing design review, not implicit reuse by shape. |
| ID remapping / overlap intervals vs cell ground | **Initial fail-closed restriction**. General overlaps, partial-cell adjacent owners and elevated segments need additional reviewed design/fixtures. |
| Conditioned minimum and raw-min comparison | **Required new-lane ground audit**. Actual normalized engine d must match independently reconstructed D_eff−D0_eff; do not retrofit/fix v0.1 in this PR. |
| Repair topology and LoD2 loss | **Proposed 2.5D scope** with diagnostics/explicit failure boundaries. Full roof/overhang/bridge support is deferred; no scientific precision claim. |
| Exact physical observer / solar / canopy collision | **Deferred here**, inherited [Phase4A limits](../experiments/voxcity_canopy_shadow/PHASE4A_OBSERVER_GEOMETRY_AND_VERTICAL_CONTRACT.md) and [Phase5 plan](../experiments/voxcity_canopy_shadow/PHASE5_INTEGRATION_PLAN_v0.1_Draft.md) unchanged; not solved by a Building Adapter. |

## 8. Step 4B implementation scope

Recommended next slice: **read-only consumer validator + synthetic-only 2.5D
Adapter candidate**, no v0.1 changes, source data acquisition, real municipality
fusion, canopy integration or solar analysis. Allow synthetic fixtures only
with explicit authored compatible elevations/coverage; never pass dummy source
evidence as a real pair approval. Introduce exact profile/schema dispatch and
dry-run diagnostics first, then isolated fixture grids/relative attributes.

After those pass, a separately authorized real pair trial may be designed under
the gates below. This report does not grant that authorization. Phase 5's
projected common-grid, common-ground and observer gates remain separate. The
accepted Adapter's geographic output must not be spliced into projected Canopy
arrays by equal shape, and its old111 acceptance is not inherited.

## 9. Required tests and Acceptance Gates

| Gate / proposed tests | Required result before extending scope |
|---|---|
| Dispatch/chain | Exact schema/profile match; unknown/legacy/version mismatch, missing receipt, tampered Raw/Native/Standard/config/layer/WKT/BLOB hash failures before output directory/engine work |
| Vertical compatibility | Compatible synthetic H/G declarations succeed; absent/different/unresolved references, h-as-H and absent/mismatched review bindings fail. No offset, geoid or inferred T.P. |
| Actual geometry/ID | Polygon/MultiPolygon/nested polygon-only collection, holes, sloped roof/walls; unknown mixed/nonfinite/NULL/2D structure rejected; deterministic IDs and `source_id` retained; complete input bytes immutable |
| DEM support | Valid zero elevations preserved as elevations, separate NoData/mask/outside reasons. Boundary/halo and source-pixel/grid-centre support explicitly tested; no invalid-source sample allowed to become0 or edge-extrapolated ground |
| Height/grid | Independently known Htop/G, height=Htop−G and ground+height target; wrong axes, mismatched cells and nonpositive h fail. Actual AOI must change grid/domain, not just manifest text |
| Conditioning/origin | Flat/sloped DEM, minimum inside a footprint, Float32/half-step boundaries. Verify D_raw/D_eff/D0 and engine indices/rounding/+1 separately, no guessed correction |
| Ownership | No-cell small footprint, ID remap >0.5 overlap, >0.3 coverage threshold boundaries, adjacent multiple owners and interval lists. Initial lane rejects unresolved collisions/remaps rather than claiming per-ID voxel roofs |
| Reproducibility/safety | Same inputs/settings give equal semantic grids/IDs; byte hashes reported independently. Fresh outputs, interrupted/failed stage rollback, immutable Accepted artifacts and unchanged v0.1 tests |
| Real-pair technical trial | Exact dataset source chain and chosen bytes + declaration/pair review + full domain/support + correspondence/ground diagnostics, separate authorization. Technical result must not be called Formal Acceptance |
| Formal/Phase5 | Separate reviewed acceptance decision and A1–A4 closure evidence; **not supplied by this audit or a future green synthetic test** |

TEST actually rerun in ordinary Windows OUEM venv (Python3.11.9):

```powershell
.venv\Scripts\python.exe -m pytest tests/test_voxcity_adapter.py tests/test_voxcity_post_crs_repair.py tests/test_source_h_standard.py tests/test_source_h_ingestion.py tests/test_building_provenance.py tests/test_standard_building.py tests/test_canopy_observer_geometry.py tests/test_canopy_shadow_poc.py -q -ra
```

**219 passed in 17.30s**, no reported skip/warning. These are existing synthetic,
mocked-worker and pinned-engine fixture tests, not a real source-H/Terrain
Adapter integration or new acceptance. They exercise the named identity,
footprint/CRS repair, relative-height and existing ground-origin fixtures; they
do not establish all proposed gates. No new tests/algorithms are introduced.
Full pytest was not rerun for this documentation-only audit; PR #91's historical
full result is not represented as a run of this branch. Code-only NoData/overlap/
AOI failure possibilities were not executed as new integration experiments.

## 10. Documentation Impact and final disposition

One new **Experimental review/design report** only. Links to owning Standard,
Implementation, Verification and Current State evidence; no duplicated formal
schema or revised Acceptance record. No Adapter/Standardizer/VoxCity code, tests,
Current State accepted status, Formal Standard or local accepted artifact changes.
External fetched source snapshots/scratch are ignored and not committed.

**Final: CONDITIONAL**, with bounded Step4B validator/synthetic implementation
recommended for review, and real fusion blocked until pair/coverage/domain/ground/
ownership evidence is supplied. Unknown scientific accuracy and historical Z
questions remain OPEN; source-H eligibility NOT_ESTABLISHED and Phase5 A1–A4 OPEN.
Draft PR for independent review; no automatic merge.
