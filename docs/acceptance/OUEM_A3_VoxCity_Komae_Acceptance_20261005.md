# OUEM A3 VoxCity Komae Acceptance Record

## 1. Record metadata

| Field | Value |
| --- | --- |
| Acceptance date | 2026-10-05 |
| Status | **ACCEPTED** |
| Phase | Phase A / A3 |
| Scope | OUEM Standard Building + Standard Terrain → VoxCity adapter |
| Accepted implementation | PR #21 |
| PR #21 merge commit | `ebd537fca052065d2b611f487a75a4faf2c6e4b6` |
| Repository | `open-urban-environment-model` |

## 2. Acceptance scope

This record accepts the following integration path:

> OUEM Standard Building + OUEM Standard Terrain → OUEM VoxCity adapter →
> VoxCity precise building rasterization → VoxCity voxel generation

Acceptance is limited to the A3 adapter boundary and its frozen Komae
real-data end-to-end integration. It does not accept VoxCity as a whole, nor
does it accept the full set of current or future OUEM environmental
simulations.

## 3. Pinned VoxCity dependency

This acceptance applies only to:

- VoxCity version: `1.7.0`
- Pinned commit: `fa212656305328a9a657973bae26f352bfe813bc`

## 4. Frozen Komae acceptance inputs

The local acceptance environment used these frozen artifacts:

| Input | Value |
| --- | --- |
| Standard Building | `data/standard/building/komae.gpkg` |
| Standard Terrain | `data/standard/terrain/komae_09LD3451.tif` |
| Expected buildings | 111 |
| Mesh size | 1 m |

These are local, frozen acceptance artifacts. The input paths are not tracked
in this repository at the time of this record. No artifact hash or additional
provenance is asserted here.

## 5. Final acceptance results

The following results were recorded from the 2026-10-05 real-data run in the
OUEM local acceptance environment. This record does not claim that the run was
re-executed in the environment used to author this document.

| Result | Value |
| --- | --- |
| `input_buildings` | `111` |
| `building_id_grid_produced` | `true` |
| `building_voxels_produced` | `true` |
| `no_unexplained_loss` | `true` |
| `adapter_serialization_deterministic` | `true` |
| `grid_and_voxel_deterministic` | `true` |
| `building_specific_absolute_invariant_max_error_m` | `0.0` |
| `vertical_geometry_consistent` | `true` |
| `vertical_tolerance_m` | `2.0` |
| `max_absolute_roof_error_m` | `1.7814643352673158` |
| `overlap_cell_count` | `11` |
| `prior_per_building_max_absolute_roof_error_m` | approximately `6.7762` |
| `prior_roof_failure_was_overlap_contamination` | `true` |

**Final result: ACCEPTED.**

## 6. Building preservation

All **111 / 111** expected building IDs were preserved after precise
rasterization. The building ID grid and building voxels were both produced
successfully; no unexplained building loss remained.

## 7. Determinism

Repeated execution confirmed that:

- adapter serialization was deterministic;
- grid generation was deterministic; and
- voxel generation was deterministic.

## 8. Vertical geometry

The building-specific absolute vertical invariant was checked as:

```text
ground_eff_abs + height = z_top_abs
```

The resulting
`building_specific_absolute_invariant_max_error_m` was `0.0`.

For final voxel geometry, `max_absolute_roof_error_m` was
`1.7814643352673158 m`, within the accepted `vertical_tolerance_m` of `2.0 m`.
The vertical geometry check therefore passed.

## 9. Precise rasterization decision

During acceptance, the VoxCity fast/Rasterio building-rasterization path
produced zero cells for the Komae building with `voxcity_id = 11`. The precise
geometry-intersection path rasterized that building successfully.

Consequently, A3 production integration formally adopts precise
rasterization using:

```python
overlapping_footprint=True
```

This is accepted A3 integration behavior, not an incidental diagnostic
setting.

## 10. Overlap-related false failure and resolution

Earlier acceptance logic reported
`prior_per_building_max_absolute_roof_error_m` of approximately `6.7762 m`.
Investigation established
`prior_roof_failure_was_overlap_contamination = true`.

VoxCity precise rasterization can represent multiple building segments in a
single cell. The final voxel grid, however, represents building volume with
the generic `BUILDING_CODE = -3` and retains no individual-building identity
provenance. The former acceptance logic used a last-wins `building_id_grid` to
assign generic building voxels in an overlap cell to one building. It thereby
misidentified a taller voxel from a different building as the target
building's roof. This was not a vertical error in the production adapter.

The corrected acceptance logic passed by:

- validating the building-specific absolute invariant from adapter output and
  effective ground;
- validating final voxel geometry against the full per-cell building-segment
  envelope; and
- not inferring an individual building identity from generic `BUILDING_CODE`.

The accepted run contained `11` overlap cells.

## 11. Production / diagnostic boundary

Production implementation is located at:

- `src/ouem/adapters/voxcity/`

Acceptance and diagnostic tooling is located at:

- `scripts/work/voxcity_komae_a3_acceptance.py`
- `scripts/work/diagnose_voxcity_building_ids.py`
- `scripts/work/diagnose_voxcity_id11.py`
- `scripts/work/diagnose_voxcity_id37_overlap.py`

These diagnostic scripts support acceptance investigation and reproduction;
they are not the production contract.

## 12. Evidence and provenance

PR #21 and its merge commit
`ebd537fca052065d2b611f487a75a4faf2c6e4b6` are the formal implementation
provenance for this acceptance. Repository evidence available at the time of
this record includes:

- `docs/OUEM_VoxCity_Adapter_v0.1.md`
- `tests/test_voxcity_adapter.py`
- `scripts/work/voxcity_komae_a3_acceptance.py`

The numerical Komae real-data results in this record are the results of the
run performed in the OUEM local acceptance environment on 2026-10-05. No
additional execution log, input hash, or provenance artifact is claimed by
this record.

## 13. Acceptance limitations

- Acceptance covers the frozen Komae dataset only.
- Acceptance is specific to VoxCity `1.7.0` at pinned commit
  `fa212656305328a9a657973bae26f352bfe813bc`.
- Nationwide scalability is outside this acceptance scope.
- Downstream environmental simulations are outside this acceptance scope.
- Generalization to other municipalities or datasets requires separate future
  validation.

## 14. Decision

**Decision: ACCEPTED**

The OUEM Phase A3 Standard-to-VoxCity adapter is accepted for the frozen Komae
integration baseline under the pinned VoxCity version and commit.

This decision accepts the A3 adapter boundary, precise-rasterization behavior,
and Komae frozen real-data end-to-end path through voxel generation. It does
not accept VoxCity as a whole, nationwide operation, other municipalities or
datasets, or downstream OUEM environmental simulations.
