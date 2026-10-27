# Phase 4B — Canopy evidence, CHM zero, missing data and coverage

**Assessment: CONDITIONAL.** Existing state/data flow and retained Komae results
were audited. The current Komae packet has no missing/outside input samples or
positive-height-to-zero-depth losses, and no missing-to-absence conversion was
detected in the guarded Phase 2/3 paths. A limited Phase 5 experiment can proceed
only with the state-preservation and comparison gates below. This is not canopy
presence acceptance, scientific accuracy validation or a final Standard Canopy
state contract.

## 1. Baseline and scope

Latest main includes merged PR #73 (GitHub and local history agree):
`cace985675e921148781ccff8b31908fee4f7262`.
Reviewed Height Envelope generation/validation, CHMv2 acquisition, the retained
state raster/manifest, Phase 2/3 source, Phase 2–4A records/tests and the
[Standard Canopy DRAFT](../../OUEM_Standard_Canopy_v0.1_Draft.md).
The [Height Envelope PoC](../../CHM_Height_Envelope_PoC_v0.1.md) encoding remains
a partial PoC contract, separate from the draft's unratified polygon/presence
codes. Standard Terrain, Building, Building Adapter, formal records, source
rasters and Phase 2–4A code/results are unchanged.

VoxCity 1.7.0 pin `fa212656305328a9a657973bae26f352bfe813bc` is unchanged.
PEP 610 plus all 136 installed source RECORD hashes verified; aggregate
`33e2bfdbc8a677f53154e8cd16295603819c68cf9f24c7a4cdfeb196bcbcd0bd`.
This is not an independent upstream Git tree comparison.
Windows ordinary OUEM venv: Python 3.11.9, NumPy 2.4.6, Rasterio 1.4.4,
PyProj 3.7.2, Numba 0.68.0. Synthetic CPU threads=2.

Local audit ID: `data/work/voxcity-canopy-shadow/komae-phase4b-20261027-01/`.
The new local audit/report/JUnit are distinct from immutable historical runs.
Historic local absolute paths identify the execution environment, not portable
download destinations. No new real-data voxelization, solar comparison,
download, source rewrite or building/canopy assembly was performed.

## 2. Six independent concepts

| Concept | What the packet establishes | What it cannot establish |
|---|---|---|
| Source data validity | Numeric value + effective band mask + declared metadata support an available sample | Ecological truth or a presence classification |
| Source support / coverage | Sample centre lies in the opened raster footprint; mask may mark an interior sample missing | Surveyed absence, observation completeness or an accepted ecological assessment footprint |
| Height estimate | Hash-bound HAG-metres interpretation and recorded numeric value (positive/zero/invalid) | Independent land-cover classification, tree identity, or calibrated local height accuracy |
| Canopy presence evidence | No independent accepted canopy polygons/presence survey supplied for this packet | Neither CHM>0 nor CHM=0 determines confirmed presence/absence |
| Modelled TREE occupancy | Count/classification of voxels actually assigned TREE by a specified conversion/scenario | Evidence that real canopy exists or does not exist |
| Unknown / unobserved | Missing, outside, unsupported evidence or an unmodelled analysis location remains explicit | A reason to fill zero, infer absence, or include unknown observations in light statistics |

These are not reduced to a single boolean. In particular, A intentionally has
TREE=0 even where unchanged CHM estimates are positive. The scenario toggle is
an experiment, not a revision of source evidence.

## 3. Current data-flow audit

| Stage / source location | Verified behavior and boundary |
|---|---|
| `acquire/meta_chmv2.py:mosaic_crop` | Copies aligned source pixel values, masks, dtype, NoData and scale/offset metadata; no height threshold or presence class. Temporary fill values are never published as fabricated coverage: any unfilled raster support fails. Interior mask holes remain masked. Reopened pixels/masks/metadata are verified before publication |
| `height_envelope.py:181 sample_raster` | Nearest lookup at target cell centres, transformed to each source CRS; separate values/missing/outside arrays. Outside means outside inverse-affine raster support, not outside a verified survey. Effective Rasterio `read_masks()` is authoritative for missing samples; the code does not separately reconcile contradictory mask/sentinel metadata |
| `height_envelope.py:213 calculate` | Missing/outside/invalid bits are separate for CHM and DEM; finite negative DEM is allowed, negative CHM is invalid. Valid zero is retained. Float64 calculation to Float32 outputs can collapse small positive depth without a numeric error when inequalities still hold |
| `height_envelope.py:273 write_verified` | Nonvalid top/bottom = −9999; error detail retained in state. State TIFF has no NoData tag, so its storage mask is valid even for error-flag cells; `read_masks(state)>0` is not an envelope-validity test |
| `canopy_shadow_poc.py:174 load_inputs` | Hash/semantic gate; all masks/metadata checked; sampled DEM must match generation reference; `relative_grids` requires **every state==1**. Missing/outside is rejected for the whole run, not converted to canopy-free cells |
| `canopy_shadow_poc.py:48 relative_grids` | Converts absolute to relative by subtracting DEM once; flips north-up to south-up. Only top>bottom gets relative canopy values; all valid zero-depth cells map to 0/0. Source CHM sign class is not retained in these two arrays themselves |
| `build_pair` / `sensitivity.build_isotropic` | Finite, nonnegative relative inputs; actual engine occupancy audit. Individual small positive heights can round to no TREE; positive thin crowns may expand. The aggregate TREE>0 check is not a per-positive-cell existence guarantee |
| Phase 3 `subdivide` | Aligned 2×2 nearest replication creates no new height or canopy information. Four child cells are not four independent source observations |
| Legacy `komae_canopy.py:52 convert_chm` | Separate old provenance/3m-threshold experiment, not the guarded Height Envelope path; do not import its threshold as this audit's presence policy |

Meta's retained crop is **UInt8**, NoData tag **None**, with a `per_dataset`
mask; 0 is a valid numeric estimate when its mask is valid. The PoC's HAG bridge
supplies height semantics, not canopy classification. No special 255 sentinel,
3m threshold or independent presence label is invented. Provider-specific
reasons for individual zero predictions, clipping/calibration and a verified
absence interpretation are **unknown from this packet**. Source metadata/masks
and evidence must be checked for each future release; observed Komae metadata
is not a global CHMv2 guarantee. Raw full-tile mask counts outside the crop were
not computed.

### 3.1 Existing state encoding (unchanged)

| Value / bit | Current meaning |
|---|---|
| 1 | Valid numeric envelope, including CHM=0 and possibly collapsed positive depth |
| 2 / 4 | CHM / DEM missing: effective mask invalid at an inside-source sample |
| 8 / 16 | CHM unmasked negative/nonfinite / DEM unmasked nonfinite |
| 32 / 64 | Outside CHM / DEM raster support |
| 128 | Invalid CR/model or unrepresentable/inconsistent Float32 result |

Error bits combine with OR: 6 is both missing, 96 is both outside. Valid=1 does
not combine with error bits; output 0 is unused. Per source, outside suppresses
missing/invalid, and missing suppresses invalid; errors from the other source
remain visible. Per-bit counts overlap and must not be summed as disjoint
populations. `bool(state)` or `state!=0` is wrong for validity because errors
are also nonzero. Exact `state==1` is the current valid test.

All nonvalid float rasters share −9999, so float rasters **alone** cannot recover
missing-versus-outside reasons. State **alone** cannot distinguish valid zero
from positive height. In particular, top==bottom does not prove CHM=0.
The draft Standard Canopy candidate code 1 refers to polygon/presence semantics;
it is not this PoC's state=1, and its numeric proposals remain unratified.

## 4. Minimum diagnostic model proposal

**Unapproved derived diagnostics, not new official numeric state codes.**
Keep the original source masks/values, envelope state and provenance alongside
this factorized view. The following field domains are names for review, not a
schema migration or a new presence algorithm.

| Independent field | Minimum candidate values / information |
|---|---|
| CHM source support | IN_RASTER_SUPPORT / OUTSIDE_RASTER_SUPPORT / UNKNOWN |
| CHM sample validity | USABLE / MASKED_OR_NODATA / INVALID / NOT_SAMPLED |
| CHM height class | POSITIVE_ESTIMATE / ZERO_ESTIMATE / UNAVAILABLE; retain numeric HAG and source identity |
| DEM support + validity | Same independent support/validity axes; retain sampled absolute DEM identity |
| Envelope validity | Original UInt8 state unchanged; decode original error bits |
| Stored envelope depth | POSITIVE / ZERO / UNAVAILABLE, separate from CHM class |
| Canopy presence evidence | UNASSESSED in the present packet; independent accepted evidence/coverage required for future supported presence or surveyed absence |
| Model conversion diagnostics | Not attempted (blocked), excluded zero depth, Float32 depth collapse, rounded to no TREE, represented, thin-crown expanded; retain counts/reason evidence rather than infer absence |
| TREE occupancy | Numeric voxel/column counts and volume before and after collision/scenario, not presence boolean |
| Analysis validity | Explicit paired A/B observer/coverage mask and exclusion reason, separate from TREE |

Convenience labels such as VALID_POSITIVE_ESTIMATE and VALID_ZERO_ESTIMATE can
be derived **only with source samples and masks**. They cannot be reconstructed
reliably from state or top/bottom alone. Missing/invalid/outside may coexist
across the two sources; retain the axes/bitsets instead of forcing one priority
class. Missing includes a grouped mask/NoData observation; the cause (cloud,
water, omitted survey, etc.) is unknown unless a source-specific reason exists.
Raster support is never promoted to surveyed canopy assessment coverage.

If downstream exports only 0/0 relative arrays or TREE counts, that export loses
information about source sign, missingness and conversion decisions. Current
packets retain hash-bound originals and state, so this is recoverable by reading
them; Phase 5 must not discard those links/sidecars. A standalone TREE array is
insufficient. This proposal adds no classifier or numeric state codes to code.

## 5. Executed synthetic fixture crosswalk

`tests/test_canopy_presence_semantics.py`: **17 new cases**. A 1×12 synthetic
sampling grid plus existing Height Envelope fixtures cover the situations below; every nonvalid case blocks
the guarded VoxCity conversion, rather than becoming TREE-free input.

| Synthetic input | Envelope state | Stored top/bottom | Model / diagnostic consequence |
|---|---|---|---|
| CHM=5m, DEM=10m | 1 | 15 / 12m at CR=.6 | Positive estimate/depth; TREE represented at tested sizes |
| CHM=0, valid mask | 1 | 10 / 10m | Valid zero estimate; no TREE by experimental mapping, presence unassessed |
| CHM declared NoData or masked zero | 2 | −9999 / −9999 | Source missing; whole guarded conversion blocked |
| Unmasked CHM −1, NaN or Inf | 8 | −9999 / −9999 | Invalid input; blocked, not absence |
| DEM NoData | 4 | −9999 / −9999 | CHM can be positive while envelope unavailable; blocked |
| Outside CHM / DEM / both sources | 32 / 64 / 96 | −9999 / −9999 | Support unavailable; blocked |
| Both sources missing | 6 | −9999 / −9999 | Combined reasons retained |
| Unmasked nonfinite DEM | 16 | −9999 / −9999 | Invalid DEM; finite negative DEM is allowed |
| Float32 overflow | 128 | −9999 / −9999 | Invalid model/numeric result; blocked |
| CHM=1e−8, DEM=10 | 1 | 10 / 10m after Float32 | Positive source, collapsed stored depth, relative 0/0 and no TREE; not the same source state as CHM=0 |
| CHM=0.1m, DEM=10 | 1 | Positive stored depth | Relative faces both round to zero at 1m and 0.5m; no TREE despite positive source/depth |
| CHM=1.2m, CR=.1 (synthetic) | 1 | Positive stored depth | Rounded thin crown expands to one layer; represented geometry differs from input depth |

Other fixture checks: NoData tag None versus 0 changes a zero sample's validity;
declared NaN NoData is missing while unmasked NaN is invalid; state TIFF storage
mask does not equal envelope validity; acquisition retains valid-zero versus
masked-zero distinction with identical zero pixel values and different masks.
Tests retain a positive-height neighbour when testing no-TREE small cells, so
the current aggregate TREE guard does not hide this per-cell effect.
No ecological height threshold or presence inference is introduced.

## 6. Komae read-only audit (executed 2026-10-27)

The audit opened existing sources and outputs for reading and wrote only its
new local directory. Existing Height Envelope, Phase 2, Phase 3 and Phase 4A
files were hash-recorded before/after; recorded upstream hashes and Phase 2/3
output hashes matched. Acquisition record is COMPLETED; crop/output identity
and retained Raw tile SHA agree with that record. No network was used.

Existing full 1m nearest CHM/DEM samples exactly match the retained generation
diagnostics. In-memory envelope/state arithmetic exactly matches all three
stored rasters; this is a read-only numerical audit, not regenerated published
artifacts, a new voxel run or new acceptance.

Native crop: EPSG:3857, 313×414=129,582 pixels, 43,614 valid positive and
85,968 valid zero, **0 masked/NoData**, 0 unmasked invalid. Pixel spacing in its
projected CRS is approximately 1.194328567m; it is not the 1m target grid.
Canonical Terrain: EPSG:6677, 600×800 at 0.5m, 480,000 finite valid cells,
0 missing/invalid. Nearest target sampling changes population and support;
native and target counts must not be compared as identical source pixels.

| Scope | Cells | CHM positive | CHM zero | state=1 | B TREE columns | B TREE voxels |
|---|---:|---:|---:|---:|---:|---:|
| Full 1m envelope AOI | 120,000 | 40,789 | 79,211 | 120,000 | Unknown / not computed | Unknown / not computed |
| Phase 2 128m domain | 16,384 | 11,741 | 4,643 | 16,384 | 11,741 | 98,840 |
| Phase 2 64m ROI | 4,096 | 3,842 | 254 | 4,096 | 3,842 | 35,106 |

At every listed target scope: CHM missing/invalid/outside=0; DEM
missing/invalid/outside=0; all nonvalid state histogram entries=0. Full-AOI
positive-CHM/zero-depth cases=0. Positive CHM corresponds to positive stored
depth in this actual packet. Source zero corresponds to valid zero depth.
This does not test real missing/unknown behavior; those paths are synthetic only.

Within the Phase 2 domain and ROI, every positive estimate has at least one
B TREE voxel and every zero estimate has none. A TREE=0 throughout by scenario
design, with identical source evidence. The map's common valid ROI mask is
4,096 cells; no missing sample is counted as a bright/zero-shade observation.

Read stored Phase 3 per-column arrays (not regenerated full voxel fields):
S1/S1_low have 3,842 occupied ROI columns and 35,106 voxels; S2/S2_low have
15,368 occupied 0.5m child columns and 280,096 voxels. Source-zero child count
is 1,016; all 16,384 paired native observations are finite. Four children are
replicates of one parent estimate, not new independent presence evidence.
Full S2 domain counts remain prior-run record evidence, not a newly recomputed
field in Phase 4B. Full-AOI TREE occupancy beyond the existing simulation domain
is **unknown / not computed**, not zero.

Real canopy presence and surveyed absence remain **unassessed at all scopes**.
No independent accepted presence polygons or ecological assessment footprint
were supplied. True canopy spatial accuracy and reasons for exact CHM zeros
cannot be inferred from this audit.

## 7. Phase 5 handoff and judgement

**Can Phase 5 start? CONDITIONAL yes, as a tightly scoped exploratory integration
of this hash-bound Komae packet, after independent review and the following
integration-entry gates.** No newly discovered missing-to-zero defect requires
editing the existing Komae implementation before that work. However, preserving
source/conversion semantics in Phase 5 is mandatory; a generic unknown-data
integration cannot be claimed ready from these all-valid real inputs.

1. Retain raw/effective source masks, source height classes, state, input hashes
   and sampling/grid identity outside the voxel array. Do not infer classes from
   relative 0/0, state truthiness, or TREE=0. Report missingness by source and
   support separately. Keep modelled-domain exclusions distinct from source
   coverage exclusions.
2. Preserve pre-building canopy intent/voxel counts and post-building TREE counts.
   Log overwritten TREE by voxel and column, building overlap/ID and retained
   source evidence. A building overwrite must be MODEL_OCCLUSION/OVERWRITE,
   never a source absence revision. Actual collision assembly/policy remains
   Phase 5 work; no new overlap processing is implemented here.
3. Add per-cell/count diagnostics for positive source lost to Float32 depth
   collapse, positive depth rounded to no TREE, and expansion. Existing coarse
   helpers are building blocks, not a complete state-preserving interface.
   Source-bound recovery is possible now; do not drop that recovery path.
4. Freeze a common A/B evaluation region, halo and physical/model observer
   interpretation. Join source/DEM/envelope validity with scenario-specific
   observer validity; record paired mask, exclusions and reasons. Reject
   incomparable masks or explicitly review a reduced intersection with fixed
   denominators. Do not insert zero where irradiance is NaN. Unknown canopy
   coverage cannot support a claim that all occluders are represented, even
   at an otherwise valid observer cell.
5. Reuse Phase 4A's effective ground/D0, precision/collision and observer-height
   gates. Current source validity does not solve arbitrary physical 1.5m origins,
   building ground flattening, or generic-versus-fast optical differences.

If these diagnostics cannot be carried into the integrated outputs, or unknown
input cells are filled as canopy-free, **that proposed integration is BLOCKED**.
The existing guarded runners instead stop on any nonvalid state; do not relax
that policy in this PR. A future partial-coverage workflow requires a separately
reviewed occluder-domain and observation-mask policy before implementation.

### Confirmed, unknown and deferrable

Confirmed: source mask/value preservation, existing state bit semantics and
priority, valid-zero versus missing separation, strict conversion gate, possible
positive-to-no-TREE representation losses/expansion, retained Komae crosswalk and
hash invariance. No production code was fixed or silently changed.

Unknown / not accepted: ecological presence/absence, survey coverage, per-zero
provider rationale, local height/horizontal accuracy, full-AOI voxel occupancy,
real missing-data outcomes and future building-overwrite statistics. Existing
PoC manifests and arrays contain no independent presence truth to recover.

Can defer for this limited geometric experiment: accepted polygon acquisition,
full Standard Canopy state codes, ecological thresholds/CR/LAD calibration,
field accuracy and production/annual/thermal validation. Must not defer the
state-retention, loss/overwrite accounting, source/analysis coverage and common
A/B validity gates before interpreting Phase 5 results.

The original Height Envelope implementation document's initial “no real Terrain
available” note describes its earlier environment, not today's stored run.
Current real evidence is linked in Phase 2/3 records and this read-only audit;
no historical statement or acceptance record is rewritten here.

## 8. Validation and evidence

New tests: **17 characterization cases**. Focused command includes CHMv2,
Height Envelope and unchanged Phase 2–4A fixtures:
**150 passed, 122 warnings in 18.19s**. Full ordinary Windows pytest:
**605 passed, 5 skipped, 250 warnings in 160.52s**. Skips are existing Windows
symlink privilege limits; warnings are Rasterio/Affine pending deprecations,
including 7 warnings from new tiny raster fixtures. Tests are technical
characterization, not real-data/scientific or Standard Canopy acceptance.

```powershell
.venv\Scripts\python.exe -m pytest -q tests/test_canopy_presence_semantics.py tests/test_meta_chmv2_acquisition.py tests/test_height_envelope.py tests/test_canopy_shadow_poc.py tests/test_canopy_shadow_sensitivity.py tests/test_canopy_observer_geometry.py --junitxml=data/work/voxcity-canopy-shadow/phase4b-focused-20261027-01.xml
.venv\Scripts\python.exe -m pytest -q --junitxml=data/work/voxcity-canopy-shadow/phase4b-full-pytest-20261027-01.xml
```

Only this audit/proposal and the reusable synthetic test file are submitted.
Local audit script/JSON/JUnit, existing data and experiment arrays are not
committed. Proposed diagnostic names do not change formal state meanings.
Draft PR, no merge; independent review decides whether the Phase 5 gates suffice.

| Evidence | SHA-256 |
|---|---|
| Height Envelope manifest | `6121cbf732f8ece9553013be2483203f08faf9a8d364136a919c184b46738d68` |
| CHMv2 acquisition record | `ab83b9b466b85a4dd2a4a73749b1c2fffb68104b88f9d630ea88f2da76c956e0` |
| CHM crop | `c5f99a4e9b21e8f419825ef2cac25ec7b36bafbe8a79a89b062201343f0ef880` |
| Standard Terrain | `0afb6d1706b97bd39c8c93ff8feb580094fe585f567e2de1f2081c082602f90a` |
| Phase 2 run.json | `e153e8da170d6dc34cfaf76bd6b1564f7924e208695e4fef75208d664bcf571d` |
| Phase 2 voxel arrays | `65b9719bf31e5901c304a0010ddc2cc1f39640d604b558c25b1fd50ffd54da36` |
| Phase 3 run.json | `5ffea2f0aaad4a005bd8eaa768371aff3b2056bd73b6ea14918df7d6597fadcd` |
| Phase 3 saved arrays | `88f8e6547cbd0616adc5b37bf6d118ba86e0501a52db20629492be416c6cc650` |
| New read-only audit JSON | `a48c4449eb24e2dcff5c40d958e81cd185db0c717377b0e82026f353c9b12e2d` |
| New fixture source | `5ec4f3d80d206e762ae9aa034521ae490bde32bf3218b65ed2773c5d3290248d` |
| Focused JUnit | `debc01e19084ea1e06f18f229c417598dea1837e66fe30d86c4af0aa5d7b90c8` |
| Full JUnit | `c5cca00300a7cb26dfc897d3ab93f319d10bf16f115341b58579744137ec79bd` |
