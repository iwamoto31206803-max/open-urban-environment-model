# Building Current State

Last checked: **2026-10-27**. Main baseline:
`66f262f1e9d0d22d01b25ae73ce5a4a7fd9057e2` (PRs #75 and #76 merged).
This is an informational entry point under the [documentation governance](../OUEM_Documentation_Governance_v0.1.md).
It does not amend contracts, historical acceptance or source Z. Code/record and
explicit path checks were performed; no new Building processing or acceptance run.

## Contracts, implementation and bounded evidence

[Concept v0.2](../OUEM_Concept_Architecture_v0.2.md) is the upper design;
[Standard Building v0.1](../OUEM_Standard_Building_v0.1.md) remains **PROVISIONAL**
with bounded Komae acceptance. The [VoxCity Building Adapter v0.1](../OUEM_VoxCity_Adapter_v0.1.md)
is the accepted engine-specific conversion boundary, not the canonical Building
representation or a Canopy contract. Read the current-status note in the
[Phase A implementation design](../Phase_A_Implementation_Design_v0.1.md) before
using its historical pending statements.

| Path / implemented responsibility | Inputs and outputs / boundary | Evidence and tests |
|---|---|---|
| PLATEAU → converter output → Native: [plateau.py](../../src/ouem/native/building/plateau.py), `ingest_converter_geopackage`, CLI `ouem-plateau-buildings` | PLATEAU GIS Converter is an external/manual prerequisite. Its GeoPackage is not already OUEM Native; OUEM registers source identity, retained geometry/Z and Native metadata | [A1 pilot/acceptance procedure](../../experiments/a1_e2e_pilot/README.md), [Native tests](../../tests/test_plateau_building.py) |
| Native → Standard: [building standardizer](../../src/ouem/standardize/building/__init__.py), `standardize_native_buildings`, CLI `ouem-standardize-buildings` | Native GeoPackage to canonical EPSG:6677 3D Building and manifest; horizontal transform with retained Z, stable identity and AOI intersection selection without clipping full geometry | [Building contract](../OUEM_Standard_Building_v0.1.md), [Standard tests](../../tests/test_standard_building.py), same bounded A1 record |
| Standard → VoxCity: [adapter](../../src/ouem/adapters/voxcity/__init__.py), `adapt_standard_to_voxcity`, CLI `ouem-adapt-voxcity` | Manifest-backed Standard Building and Terrain to EPSG:4326 2D footprints, engine IDs, relative heights and Adapter provenance | [A3 acceptance](../acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md), [Adapter tests](../../tests/test_voxcity_adapter.py), [post-CRS repair tests](../../tests/test_voxcity_post_crs_repair.py) |

The A1 record covers its recorded Komae Native/Standard pilot; A3 covers the
recorded local Building Adapter through VoxCity voxel generation. They establish
neither nationwide applicability nor mixed Building/canopy solar acceptance.
The later [contained E2E record](../acceptance/OUEM_Komae_Contained_E2E_Acceptance_20261018.md)
has its own subset and review scope; it does not replace A1/A3 or prove every
historical artifact remains available. Existing tests exercise defined properties;
their presence alone is not a fresh execution result.

## Coordinates and unresolved source Z

The Building contract declares canonical Komae horizontal CRS **EPSG:6677**, Z
as absolute metres under T.P., and source-profile/converter interpretation
separately. The accepted Native path preserves converter numeric Z; the
Standardizer preserves it while transforming horizontal coordinates. Neither
EPSG:6677 nor retained numbers independently proves vertical datum accuracy.
The contract's PLATEAU profile declares EPSG:6697; the converter/Native layer
uses EPSG:4979. That CRS formally has ellipsoidal height, whereas OUEM interprets
retained Z as T.P. This unresolved semantic boundary requires actual converter
operation and matched-coordinate evidence, not inference from a CRS label.
[Terrain](../OUEM_Standard_Terrain_v0.1.md) uses source-declared T.P., also without
independent survey validation.

The Adapter derives relative height from canonical maximum Z minus the mean
VoxCity raw DEM under assigned Building IDs, with the profile's `min_height=0`.
Engine per-ID ground conditioning and D0 re-origin must be audited separately;
canonical absolute Z and voxel index are not interchangeable. The accepted
geographic Adapter grid is not automatically the experimental projected 1m grid.
See [Adapter contract](../OUEM_VoxCity_Adapter_v0.1.md) and
[Phase 4A coordinate analysis](../experiments/voxcity_canopy_shadow/PHASE4A_OBSERVER_GEOMETRY_AND_VERTICAL_CONTRACT.md).

The [Building vertical diagnosis](../research/OUEM_Komae_Building_Vertical_Geometry_Diagnosis.md)
is **UNRESOLVED**. The roughly 37m difference is a reported source/converter/geometry
hypothesis, not a proven matched-vertex datum shift. Full geometry/LoD and
conversion history require evidence. Do not subtract an offset or treat a T.P.
label as measured accuracy. The read-only [provenance diagnostic](../../src/ouem/komae_vertical_provenance.py)
and [tests](../../tests/test_komae_vertical_provenance.py) support investigation;
this update does not claim that the missing source chain has been reconstructed.

## Availability, reproduction and next gate

On the check date, these specific local paths were **absent**:
`data/native/building/komae.gpkg`, `data/standard/building/komae.gpkg`, and
`data/standard/building/komae.gpkg.manifest.json`. This is a path-specific check,
not a whole-PC search or proof that no alternative Building dataset exists.
Historical A3 paths alone do not identify selected bytes or supply their hashes.
Reproduction needs the actual source/converter/Native/Standard chain and adjacent
manifests, recorded AOI/profile and the pinned VoxCity 1.7.0 commit
`fa212656305328a9a657973bae26f352bfe813bc`; follow the
[runtime architecture](../architecture.md) and [runbook](../../scripts/work/README.md)
to keep OUEM and GIS environments separate.

Before Phase 5, identify the chosen Building file/manifest by SHA-256, source
release and IDs; obtain height/LoD and converter-operation evidence, compare
matched source/Native/Standard Z, and resolve the selected-data implications of
the diagnosis or demonstrate an unaffected subset. Approval of common grid,
ground conditioning, observers and masks is also required by the
[Completion Gate class A items](../experiments/voxcity_canopy_shadow/PHASE4_COMPLETION_GATE_REVIEW_20261027.md).
The [Phase 5 plan](../experiments/voxcity_canopy_shadow/PHASE5_INTEGRATION_PLAN_v0.1_Draft.md)
is **Draft, not implemented**: common raw/effective DEM and D0, Building-over-TREE
audit, IDs/heights and paired masks must be tested during implementation.
The canopy-only milestone's CONDITIONAL PASS does not close these Building gates.
See [Canopy Current State](CANOPY_CURRENT_STATE.md) for source validity and presence
limits; no new acceptance or coordinate correction is declared here.
