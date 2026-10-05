# OUEM A2 Standard Terrain Komae Acceptance Record

## 1. Record metadata

| Field | Value |
| --- | --- |
| Acceptance date | 2026-10-06 |
| Status | **ACCEPTED** |
| Phase | Phase A / A2 |
| Scope | OUEM Standard Terrain v0.1 — Komae real-data acceptance |
| Repository | `open-urban-environment-model` |
| Main commit used for the reported rerun | `e1037dc4b01b4b091e30a8f3806b363d5ef12cc0` |
| A2 implementation | PR #10, merge commit `c4b4d4cc669eb285b4032fdbc30b0904ce69f83e` |
| Vertical-provenance correction | PR #11, merge commit `e11fdc5e700402a8eeecd9fbd1265fe98c6001c1` |

This record documents a fresh manual Komae real-data acceptance rerun performed
on 2026-10-06 from the main checkout identified above. The operator ran:

```bat
scripts\work\terrain_komae_local_acceptance.cmd
```

The run was performed in the local acceptance environment, not by the authoring
agent for this record. This document records the supplied terminal results and
artifact metadata; it does not claim an additional rerun while authoring the
record.

## 2. Implementation provenance

OUEM Standard Terrain v0.1 was introduced by PR #10, merged as
`c4b4d4cc669eb285b4032fdbc30b0904ce69f83e`. Its implementation history includes
commit `a5d4c03fcf78d7a5ffb925b1e2f90166d4c776aa` (`Implement A2 OUEM Standard
Terrain v0.1`).

The Tokyo DEM vertical provenance was subsequently corrected to
source-declared T.P. by PR #11, merged as
`e11fdc5e700402a8eeecd9fbd1265fe98c6001c1`. The corresponding implementation
and documentation commit is `e64c424a4d5781a97d23926d89fdf6e8f54dbe43`
(`Correct Tokyo DEM vertical provenance`).

The reported acceptance rerun used main commit
`e1037dc4b01b4b091e30a8f3806b363d5ef12cc0`, which contains both merged changes.

## 3. Acceptance scope and workflow

The accepted standalone A2 path is:

> Komae Tokyo 0.50 m bare-earth DEM → OUEM Native Terrain acceptance manifest
> → OUEM Standard Terrain v0.1 GeoTIFF and manifest

The local helper first ran the automated test suite, then accepted the real
source raster as Native Terrain, generated Standard Terrain, and validated the
written output. The terminal result reported:

- automated tests: **62 passed, 8 warnings**;
- Native Terrain accepted;
- Standard Terrain generated and validated;
- Grid preservation: **PASS**;
- Elevation preservation: **PASS**; and
- Result: **PASS**.

## 4. Accepted local artifacts

| Role | Repository-relative local path |
| --- | --- |
| Input | `data/raw/terrain/tokyo_23ku_dem_050m/komae/09LD3451.tif` |
| Native manifest | `data/native/terrain/komae_09LD3451.json` |
| Standard output | `data/standard/terrain/komae_09LD3451.tif` |
| Standard manifest | `data/standard/terrain/komae_09LD3451.tif.manifest.json` |

These are local acceptance artifacts and are not committed to Git. Their
absence from the repository is consistent with the repository data policy.
This record preserves the verified metadata and hashes needed to identify the
fresh acceptance baseline without adding the terrain data or generated
manifests themselves.

## 5. Verified fresh-run results

| Property | Verified value |
| --- | --- |
| Dataset | Tokyo 0.50 m bare-earth DEM tile 09LD3451 |
| Provider | Tokyo Metropolitan Government |
| Source CRS | `EPSG:6677` |
| Standard CRS | `EPSG:6677` |
| Dimensions | `800 x 600` |
| Source resolution | `0.5 x 0.5 m` |
| Standard resolution | `0.5 x 0.5 m` |
| Extent | `[-23600.0, -40800.0, -23200.0, -40500.0]` |
| Standard dtype | `float32` |
| Standard NoData | `-9999.0` |
| Valid cells | `480000` |
| NoData cells | `0` |
| NoData proportion | `0.00%` |
| Valid elevation minimum | `19.577999114990234 m` |
| Valid elevation maximum | `25.29599952697754 m` |
| Grid preservation | **PASS** / `true` |
| Elevation preservation | **PASS** / `true` |
| Vertical reference status | `source-declared` |
| Vertical reference name | `T.P. (Tokyo Peil / Tokyo Bay mean sea level)` |
| Source SHA-256 | `c747f2ae2ee30f67da98c1c90961f6a094fa0fca8ba3f15a1131c09783d73824` |
| Standard output SHA-256 | `0afb6d1706b97bd39c8c93ff8feb580094fe585f567e2de1f2081c082602f90a` |
| Final result | **PASS** |

The recorded hashes identify the source and generated Standard output used by
this fresh 2026-10-06 standalone A2 acceptance baseline.

## 6. Grid and elevation preservation

The Standard output retained the source CRS, dimensions, resolution, and
extent. Grid preservation therefore passed. The workflow also compared the
valid source elevations with the values reopened from the written Standard
GeoTIFF; elevation preservation passed.

The accepted Standard output is a single-band `float32` GeoTIFF with the
Standard NoData value `-9999.0`. This source tile contained no NoData cells, so
all `480000` cells were valid and the NoData proportion was `0.00%`.

## 7. Vertical provenance

The accepted vertical reference status is **source-declared**, and its name is
**T.P. (Tokyo Peil / Tokyo Bay mean sea level)**. This records the provider
declaration supported by the Tokyo Metropolitan Government source metadata and
release documentation already identified by the Standard Terrain v0.1 contract
and the accepted local workflow.

`source-declared` does not mean that OUEM independently surveyed or verified the
vertical datum. OUEM does not infer vertical meaning from the horizontal
`EPSG:6677` CRS, and this acceptance makes no broader vertical-datum claim.

## 8. Historical manifest status and repository acceptance state

The generated Standard Terrain manifest contains this historical status string:

```text
PROVISIONAL pending local real-data and downstream adapter validation
```

That value is emitted by the Standard Terrain v0.1 generation workflow. It was
not edited as part of this documentation-only acceptance record and remains
part of the generated local manifest. The string is now historically stale with
respect to the repository-level acceptance state:

1. the standalone A2 Komae real-data workflow passed on 2026-10-06 and is
   accepted by this record; and
2. downstream use of the Komae Standard Terrain family/path was separately
   accepted by the A3 record
   `docs/acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md`.

These are distinct bodies of evidence. This record establishes the fresh A2
standalone result. The earlier A3 record establishes downstream usability in
the accepted VoxCity Komae integration. Repository evidence does not establish
that the exact Standard Terrain bytes produced by this 2026-10-06 rerun are
identical to the artifact used in the earlier A3 run; no such byte-identity
claim is made here.

## 9. What this acceptance establishes

For the frozen/local Komae 09LD3451 baseline represented by the metadata and
hashes in this record, acceptance establishes that:

- real Komae terrain can pass OUEM Native Terrain acceptance;
- OUEM Standard Terrain v0.1 can be generated successfully;
- the expected CRS, dimensions, resolution, and extent are retained;
- the raster grid is preserved;
- valid elevation values are preserved;
- the Standard output uses `float32` and `-9999.0` NoData;
- vertical-reference provenance is retained as source-declared T.P.; and
- deterministic provenance hashes are recorded for the fresh input and output.

## 10. Acceptance limitations

This acceptance does **not** establish:

- nationwide terrain acceptance;
- acceptance of every Tokyo DEM tile;
- acceptance of other terrain providers;
- universal or independently surveyed vertical-datum correctness; or
- validity of downstream environmental simulations.

The separate A3 acceptance is downstream integration evidence and is referenced
by this record; it is not folded into the standalone A2 decision.

## 11. References

- `docs/OUEM_Standard_Terrain_v0.1.md`
- `scripts/work/terrain_komae_local_acceptance.cmd`
- `scripts/work/README.md`
- `tests/test_standard_terrain.py`
- `docs/acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md`

## 12. Decision

**Decision: ACCEPTED**

The OUEM Phase A2 Standard Terrain v0.1 Komae real-data workflow is accepted for
the frozen/local Komae 09LD3451 acceptance baseline represented by the recorded
hashes and metadata.
