# OUEM Komae Contained E2E — Local Acceptance Record

## 1. Record metadata and purpose

| Field | Value |
| --- | --- |
| Date | 2026-10-18 |
| Run ID | `komae-contained-002` |
| Scope | A1 Building + A2 Terrain + A3 VoxCity Adapter |
| Review verdict | **PASS — within reviewed evidence** |
| Automated status | `AUTOMATED_PASS` |
| Artifact acceptance field | `PENDING_LOCAL_REVIEW` (unchanged) |

This local review verifies the reported integrated processing of accepted
Native/Standard building and terrain inputs through the OUEM VoxCity Adapter,
including the conditional post-CRS geometry repair introduced in
[PR #46](https://github.com/iwamoto31206803-max/open-urban-environment-model/pull/46).
It applies only to the Komae contained-building proof of concept. It does not
constitute nationwide validation or Phase B acceptance.

## 2. Test configuration

| Item | Value |
| --- | --- |
| Study area | `komae_09LD3451` |
| CRS | `EPSG:6677` |
| Extent | `[-23600, -40800, -23200, -40500]` |
| Mesh size | 1 m |
| Baseline building count | 111 |
| Selected contained buildings | 92 |
| Expected Native buildings | 3,637 |
| Independent repeats | 2 |
| VoxCity version | 1.7.0 |

## 3. Automated validation

The supplied local report records `status = AUTOMATED_PASS`, `quality = PASS`,
and `reproducibility = PASS`. Both repeats passed all reported quality and
determinism checks, including:

- A1/A2 consistency;
- building count and ID consistency;
- Building ID grid and voxel generation;
- vertical geometry consistency and no unexplained building loss;
- Adapter content, contract, repair summary, diagnostics, geometry, and
  projected-metric checks; and
- input lineage and deterministic output checks.

All nine reported repeat-comparison fields were `true`.

## 4. Post-CRS geometry repair

The reported repaired building is
`oub-21a29be1-9794-593f-b22c-e3639a7d9d45`. The repair method is conditional
`shapely.make_valid` after transformation to `EPSG:4326`.

| Metric | Reported result |
| --- | --- |
| Repaired building count | 1 |
| Before | Invalid Polygon; self-intersection |
| After | Valid Polygon |
| After polygon count | 1 |
| After ring count | 3 |
| After vertex count | 26 |
| After area | Approximately 115.847486716 m² |
| Area difference vs source | Approximately −3.226 × 10⁻⁹ m² |
| Symmetric difference vs source | 0.0 m² |
| Hausdorff distance vs source | Approximately 1.412 × 10⁻⁹ m |

The local review assessed the observed geometric changes as negligible for
the intended 1 m mesh PoC. The reported repaired structure agrees with the
earlier [PR #45](https://github.com/iwamoto31206803-max/open-urban-environment-model/pull/45)
QGIS inspection (Polygon, one part, 26 vertices). The historical discrepancy
with [PR #42](https://github.com/iwamoto31206803-max/open-urban-environment-model/pull/42)
(MultiPolygon, two parts) remains unexplained and is retained as a non-blocking
historical observation.

## 5. Review decision

**PASS — within reviewed evidence.** The automated integration, quality,
repeatability, and geometry-repair checks passed. The post-CRS repair
diagnostics were also manually reviewed from local report screenshots.
This review verdict does not assert that the artifact's acceptance field was
formally updated; it remains `PENDING_LOCAL_REVIEW`.

## 6. Remaining limitations

- QGIS visual inspection of the specific `komae-contained-002` repaired
  output has not been performed.
- The original integration report retains `acceptance = PENDING_LOCAL_REVIEW`.
- This record does not establish nationwide applicability, canopy integration,
  shade-map accuracy, or green-view accuracy.
- The previous PR #42/#45 geometry-type discrepancy remains unexplained.

## 7. Evidence and provenance

The primary local artifact is
`data/work/integration/komae-contained-002/integration-report.json`.
Relevant implementation changes are [PR #46](https://github.com/iwamoto31206803-max/open-urban-environment-model/pull/46)
for conditional post-CRS geometry repair and
[PR #47](https://github.com/iwamoto31206803-max/open-urban-environment-model/pull/47)
for contained-E2E repair acceptance checks and the Windows launcher.

The local report and associated output artifacts remain the primary evidence.
This Markdown record summarizes the supplied, reviewed results; it does not
replace or modify those artifacts. No real-data processing was performed while
authoring this record.

## 8. Next phase

Proceed to canopy integration using 2D canopy geometry and CHM-derived height
information, followed by a Komae-scale shade-map proof of concept. Preserve
the current accepted building/terrain integration behavior as the regression
baseline.
