# Candidate B Terrain integration decision plan v0.1

**Status:** DESIGN PROPOSAL / EXPERIMENTAL / NOT_FORMALLY_ACCEPTED  
**Updated:** 2026-11-04  
**Scope:** Mixed-LoD Candidate B only, EPSG:6677, `[-22575,-39925,-22475,-39825]`, 100 m × 100 m on the aligned 0.5 m grid.

## Evidence and gate status

| Gate | Status | Basis and boundary |
|---|---|---|
| T0 Source semantics | **CONDITIONAL PASS** | Use ward T.P. as an inherited assumption for isolated Candidate B experimentation. The exact DEM datum realization and epoch remain unverified. |
| T1 Spatial diagnostics | **PASS (diagnostics)** | Four original TIFFs were hash-verified, and the overlap and seam metrics were measured. |
| T2 Source selection | **WARD_FIRST proposed for review** | Prefer original ward values where valid and fall back to original Tama values. The proposal awaits design review. |
| T3 Experimental preparation | **Pending T2 review** | Separate fresh-run implementation and evidence review under the conditions below. |
| T4 Model integration | **HOLD** | Building/terrain height semantics and model grid compatibility require independent validation. |

`terrain_integration_ready=false`. This decision update leaves the historical preflight and T1 receipts as recorded. The accepted Komae tile 09LD3451 does not cover B. The measured inputs are the four PR #141 TIFFs for 09LD3423 and 09LD3433, two per source. [PR #141 preflight](../experiments/real_komae_source_h/MIXED_LOD_TERRAIN_CANDIDATE_B_PREFLIGHT.md) · [PR #143 T1 report](https://github.com/iwamoto31206803-max/open-urban-environment-model/blob/757730b/docs/experiments/real_komae_source_h/MIXED_LOD_TERRAIN_CANDIDATE_B_DIAGNOSTICS.md)

## T0 conditional vertical assumption

- The user supplied the official Tokyo Digital Twin 3D viewer citation for **世田谷区（ダウンロードメッシュ）**, where the airborne laser point-cloud elevation reference is stated as 東京湾平均海面 (T.P.). The viewer returned HTTP 403 from this session, so the layer wording is recorded as user-supplied official evidence. [Tokyo Digital Twin 3D viewer](https://3dview.tokyo-digitaltwin.metro.tokyo.lg.jp/)
- The ward 2024 catalogue describes the 0.50 m GeoTIFF as derived from ground point data. The catalogue establishes the data lineage and names JGD2011 / Plane Rectangular CS IX. The exact ward TIFFs lack a direct vertical declaration. **T.P. is inferred to carry through from the official point-cloud description to the derived DEM** under this Candidate B decision. The basis is the ward point-cloud description and DEM lineage. [Tokyo ward catalogue API](https://catalog.data.metro.tokyo.lg.jp/api/3/action/package_show?id=t000029d0000000024) · [Public catalogue mirror](https://odm.bodik.jp/ja/dataset/t000029d00000000241)
- Tama has a separate provider T.P. declaration. Mixed Building declares EPSG:6695 gravity-related H. Precise vertical datum realization, height epoch, treatment of any later revisions, and accuracy agreement between surveys and with Building remain unverified. Near-zero DEM overlap medians do not resolve those questions. [Tokyo Tama catalogue API](https://catalog.data.metro.tokyo.lg.jp/api/3/action/package_show?id=t000029d0000000020) · [Mixed Standard H declaration](../experiments/real_komae_source_h/MIXED_LOD_STANDARD_POC.md)
- The ward WKT still has an unnamed embedded datum despite the projected EPSG:6677 authority. T1 verified that the raw `Point` tiepoints are the GDAL-normalized cell centres. Use the same conditional horizontal interpretation for B, with the recorded aligned affine and without a further half-cell shift, silent CRS relabeling, or reprojection. [PR #143 T1 report](https://github.com/iwamoto31206803-max/open-urban-environment-model/blob/757730b/docs/experiments/real_komae_source_h/MIXED_LOD_TERRAIN_CANDIDATE_B_DIAGNOSTICS.md)

T0 permits work toward an isolated Candidate B experiment under those assumptions. Retain the original height values. A change to another vertical reference, a uniform offset, and a formal quality guarantee are outside this decision. Direct evidence for the precise DEM datum, realization and epoch remains valuable and should trigger review if it contradicts the assumption.

## T2 comparison

Both source catalogues describe ground-derived products. The reported acquisition windows are July 2022–January 2023 for Tama 2023 and March–April 2023 for ward 2024. These are catalogue windows, with no tile-specific survey epoch or demonstrated accuracy ranking. Tama has broader valid coverage and stronger direct metadata for horizontal/vertical interpretation. Ward is the later acquisition window, with a smaller valid footprint and a conditional vertical interpretation. Both have the original per-tile hashes and validity masks in the preflight. [Tama distribution catalogue](https://www.geospatial.jp/ckan/api/3/action/package_show?id=tokyopc-tama-2023) · [Ward distribution catalogue](https://www.geospatial.jp/ckan/api/3/action/package_show?id=tokyopc-23ku-2024) · [PR #141 provenance](../experiments/real_komae_source_h/MIXED_LOD_TERRAIN_CANDIDATE_B_PREFLIGHT.md)

| T1 metric | TAMA_FIRST | WARD_FIRST |
|---|---:|---:|
| Chosen Tama / ward cells | 28,233 / 11,767 | 23,897 / 16,103 |
| Source-switch edges, east / south | 200 / 83 | 200 / 84 |
| Switch-edge MAE, east / south (m) | 0.0705 / 0.0690 | 0.0439 / 0.0308 |
| Nearby same-source, same-tile edge MAE, east / south (m) | 0.0190 / 0.0192 | 0.0214 / 0.0151 |
| Maximum absolute switch-edge jump (m) | 0.345 | 0.172 |

Both counterfactuals cover 40,000 cells from the same four tiles. Both have higher directional switch-edge MAE than the local same-source reference, so a residual interface warrants review. Local gradients differ between the switch locations. A jump between adjacent cell centres includes actual terrain variation and cannot be attributed solely to stitching. At the north/south mesh boundary, TAMA_FIRST has one edge that also changes source, while WARD_FIRST has zero. [PR #143 seam definitions and measurements](https://github.com/iwamoto31206803-max/open-urban-environment-model/blob/757730b/docs/experiments/real_komae_source_h/MIXED_LOD_TERRAIN_CANDIDATE_B_DIAGNOSTICS.md)

The largest same-centre overlap difference (ward minus Tama) is −0.656 m at (−22512.75, −39870.75). All 47 cells exceeding 0.50 m absolute difference lie in the northern tile, within X −22515.25 to −22511.75 and Y −39872.25 to −39868.25. A read-only comparison of the saved T1 difference raster and the source-switch CSVs found **zero of those 47 cells at switch-edge endpoints** in either policy. The minimum Euclidean distance from those centres to any switch-edge midpoint was 4.70 m for TAMA_FIRST and 1.60 m for WARD_FIRST. The cluster is therefore an interior disagreement between source surfaces and is closer to the ward-first interface. It remains relevant to the selected surface even though it is separate from the measured switch-edge maxima. [PR #143 T1 output description](https://github.com/iwamoto31206803-max/open-urban-environment-model/blob/757730b/docs/experiments/real_komae_source_h/MIXED_LOD_TERRAIN_CANDIDATE_B_DIAGNOSTICS.md)

### Proposed selection rule

1. For each AOI centre, choose the ward tile sample if it is in bounds, valid by its mask and finite. Otherwise choose a valid, finite Tama sample at the same centre. Valid zero elevations are retained.
2. If neither source is valid, stop the T3 attempt with a gap diagnostic. If multiple valid tiles from the same source supply a centre, stop and record the ambiguity. Do not resolve it by file order.
3. Copy the selected source value exactly. Preserve source/tile identity per centre and the original input hashes. Use the existing aligned grid and the original masks. No interpolation, averaging, smoothing, vertical transformation or offset.

WARD_FIRST is the first candidate because it lowers the measured switch-edge MAE in both directions and the maximum observed jump, with essentially the same number of switches. The later ward acquisition window is context, and the stronger Tama metadata is a reason to retain TAMA_FIRST as the review comparator. The residual risks include the conditional ward datum and WKT, the localized 0.656 m disagreement, different survey conditions, and terrain variation along both interfaces. Revise or hold the proposal if design review finds those limitations unacceptable.

A simple priority rule preserves actual source values and makes each cell traceable. A mean or a feathered/smoothed join could reduce a visible step, but it would create synthetic values, risk blurring genuine microtopography and hide disagreement where datum or acquisition differences remain unresolved. It would require a separately reviewed blend width, mask handling and error evaluation. These approaches are deferred.

## Conditions for entering and reviewing T3

Before implementation, obtain T2 review of the proposed priority, fallback and no-adjustment rules, the inferred T.P. and conditional horizontal interpretation, and the residual seam and local outlier evidence. Record the decision explicitly. A contradictory datum or grid finding returns the design to HOLD. No universal jump tolerance is adopted from these measurements.

For the separately scoped T3 prototype review, require:

- New isolated run and experimental profile, with the four pinned TIFF SHA-256 values, source releases, masks, CRS/vertical assumption, grid and policy recorded. Accepted inputs and prior runs stay read-only.
- Exact 200×200 aligned grid with 40,000 finite covered centres, no extrapolation, and for the same WARD_FIRST inputs 16,103 ward and 23,897 Tama selections. Recompute the counts independently and report any mismatch. Preserve every selected value and its source/tile identity and verify both against the original data after reopening any prototype output.
- Reproduce the T1 switch counts and jumps for unchanged inputs and rule. Inspect the localized 0.50 m exceedance cluster and the mesh boundary alongside same-source gradients. If metrics differ, document why and return to review before relying on the product.
- Test fallback, valid zero, both missing, competing same-source tiles, CRS/grid/hash mismatch and publication failure. Require a fresh output, complete provenance and successful reopen audit before marking any prototype run complete.
- Keep multi-source preparation explicit and separate from the existing single-TIFF Standard Terrain contract. An experimental T3 result requires its own review. Any use with Building/VoxCity requires the separate T4 decision.

This PR updates the design only. Formal mosaic preparation, Native/Standard Terrain generation, VoxCity execution and Accepted artifact changes remain outside its scope.
