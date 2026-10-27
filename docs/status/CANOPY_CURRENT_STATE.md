# Canopy Current State

Last checked: **2026-10-27**. Main baseline:
`66f262f1e9d0d22d01b25ae73ce5a4a7fd9057e2` (PRs #75 and #76 merged).
This is an informational entry point under the [documentation governance](../OUEM_Documentation_Governance_v0.1.md),
not a new acceptance decision. Checks here are code/record inspection, not a new
real-data run or a rerun of the cited tests.

## Design and implemented path

[Concept v0.2](../OUEM_Concept_Architecture_v0.2.md) is the registered upper design;
[Standard Canopy v0.1 DRAFT](../OUEM_Standard_Canopy_v0.1_Draft.md) remains a proposal.
The implemented experimental raster path is:

Meta/WRI CHMv2 COGs → AOI acquisition raster/record → evidence-guarded Height
Envelope with Standard Terrain → canopy-only VoxCity conversion → CPU direct
irradiance A/B comparison. This path does not complete the proposed
Raw → Native → Standard Canopy → Adapter lifecycle.

| Implemented component / source | Interface and meaning | Verification scope |
|---|---|---|
| [CHMv2 acquisition](../../src/ouem/acquire/meta_chmv2.py) | [Acquisition usage](../Meta_CHMv2_AOI_Acquisition_PoC.md): source COG/index identities, AOI GeoTIFF in EPSG:3857, acquisition record; not Standard Canopy | Recorded acquisition/audit evidence in that document; [offline tests](../../tests/test_meta_chmv2_acquisition.py) |
| [Height Envelope](../../src/ouem/height_envelope.py) | [Usage and contract](../CHM_Height_Envelope_PoC_v0.1.md): CHM HAG in metres plus absolute Terrain and evidence bridge; Float32 absolute `canopy_top_z.tif` / `canopy_bottom_z.tif`, validity-state raster and manifest. Initial Komae grid EPSG:6677, 1m; replaceable model's implemented choice is `constant_cr_v0.1` | [Synthetic tests](../../tests/test_height_envelope.py); [real-data 3D verification](../verification/OUEM_Height_Envelope_3D_Visualization_Komae_20261026.md) links the upstream envelope evidence; no scientific accuracy acceptance |
| [Canopy shadow PoC](../../src/ouem/canopy_shadow_poc.py) | [Phase 2 usage](../experiments/voxcity_canopy_shadow/PHASE2_USAGE.md): guarded inputs, DEM subtraction once, north-up to south-up conversion, canopy-free / canopy voxel pairs and CPU direct irradiance | [Phase 2 results](../experiments/voxcity_canopy_shadow/PHASE2_RESULTS_20261027.md), [tests](../../tests/test_canopy_shadow_poc.py); fixed ROI, sun and assumed optical parameters |
| [Sensitivity runner](../../src/ouem/canopy_shadow_sensitivity.py) | Isotropic 1m / 0.5m experiments; finer grid adds no new source information | [Phase 3 method](../experiments/voxcity_canopy_shadow/PHASE3_API_AND_METHOD.md), [results](../experiments/voxcity_canopy_shadow/PHASE3_RESULTS_20261027.md), [tests](../../tests/test_canopy_shadow_sensitivity.py); geometry, horizontal sampling and observer effects are mixed |

The older [komae_canopy.py](../../src/ouem/komae_canopy.py) is a separate experimental
path with its own legacy provenance/threshold assumptions, not the current envelope
contract or a full Standardizer. The [Native](../../src/ouem/native/canopy/__init__.py),
[Standardize](../../src/ouem/standardize/canopy/__init__.py) and
[Model](../../src/ouem/model/canopy/__init__.py) Canopy namespaces are placeholders.
Canonical polygon acquisition/rasterization, full Standard Canopy production and
formal acceptance, and mixed Building/canopy Phase 5 are **not implemented by this path**.

## Validity is not canopy presence

The [envelope implementation](../../src/ouem/height_envelope.py) treats state=1
as numerically valid, including CHM=0. Other bits distinguish CHM/DEM missing,
invalid and outside coverage, plus invalid model output. Top/bottom NoData denotes
invalid output; the codes are not the proposed Standard Canopy state encoding.
Do not fill missing/outside cells with zero or collapse coverage, numeric validity,
height estimate, presence evidence and model occupancy into one boolean.

In the [strict shadow path](../../src/ouem/canopy_shadow_poc.py), selected inputs
must be valid. Positive envelope thickness controls conversion; zero thickness
produces no model TREE. Float32 or voxel rounding can also remove positive height
or alter thin crowns. Neither CHM>0 nor TREE>0 proves real canopy presence; neither
CHM=0 nor TREE=0 proves absence. See the factorized
[Phase 4B audit](../experiments/voxcity_canopy_shadow/PHASE4B_CANOPY_PRESENCE_AND_COVERAGE_AUDIT.md)
and [fixtures](../../tests/test_canopy_presence_semantics.py).

## Verified limits and next gate

[Phase 4A](../experiments/voxcity_canopy_shadow/PHASE4A_OBSERVER_GEOMETRY_AND_VERTICAL_CONTRACT.md)
and its [fixtures](../../tests/test_canopy_observer_geometry.py) document actual
ray origins, ground-layer and rounding contributions. The public surface-map API
does not generally represent exact physical DEM+1.5m observations; a low-level
fractional-origin counterexample prevents claiming a safe arbitrary-point adapter.
Retain its option C and record actual coordinates. Terrain source-declared T.P.
and the evidence bridge do not independently validate CHM height science or
ground compatibility. CR and optical parameters remain assumptions.

The [Completion Gate](../experiments/voxcity_canopy_shadow/PHASE4_COMPLETION_GATE_REVIEW_20261027.md)
proposes **CONDITIONAL PASS** for the canopy-only milestone. Phase 5 execution
remains **blocked pending class A closure**: observer interpretation, common grid
and Building conditioning, selected Building identity/Z evidence, and state,
overlap and comparison-mask policy. The [Phase 5 Integration Plan DRAFT](../experiments/voxcity_canopy_shadow/PHASE5_INTEGRATION_PLAN_v0.1_Draft.md)
defines proposed implementation checks, not completed features or approval.
Use [Building Current State](BUILDING_CURRENT_STATE.md) for the Building evidence gap.
Independent canopy presence, source timing/registration, optical calibration and
scientific accuracy remain unverified within this exploratory scope. Detailed
metrics, hashes and historical test executions belong to the linked records.
