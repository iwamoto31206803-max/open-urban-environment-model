# Candidate B Terrain integration decision plan v0.1

**Status:** DESIGN PROPOSAL / EXPERIMENTAL / NOT_FORMALLY_ACCEPTED  
**Updated:** 2026-11-04  
**Scope:** Mixed-LoD Candidate B only, EPSG:6677 bounds `[-22575,-39925,-22475,-39825]` (100 m × 100 m). **No permission to publish a fused Standard Terrain**, change A2/A3 accepted artifacts, or run VoxCity with incompatible vertical semantics.

## 1. Evidence baseline and what has actually passed

The source preflight in [PR #141](../../pull/141) is code-review PASS, but its actual data status is **CONDITIONAL** and `terrain_integration_ready=false`. Authoritative measured record: [MIXED_LOD_TERRAIN_CANDIDATE_B_PREFLIGHT.md](../experiments/real_komae_source_h/MIXED_LOD_TERRAIN_CANDIDATE_B_PREFLIGHT.md). The following are sourced from its real-data analysis, **not independently reconstructed in this document**:

- Existing Komae accepted tile `09LD3451` does not cover B.
- 0.5m grid: 200 × 200 = 40,000 cell centres, aligned per Rasterio/GDAL report.
- Tama 2023: 28,233 valid centres (70.5825%); 23-ku 2024: 16,103 (40.2575%).
- Conditional valid-cell union: 40,000; 4,336 shared valid centres (10.84%); Tama-only 23,897, ward-only 11,767.
- Four measured TIFFs: each source's `09LD3423` and `09LD3433`; the minimal complete set in this particular grid is all four.
- Difference `ward minus Tama` on overlap: `09LD3423` min -0.656 m, max +0.183 m, mean -0.0472 m, median -0.0020 m (n=3,261); `09LD3433` min -0.227 m, max +0.129 m, mean -0.0167 m, median +0.0010 m (n=1,075).
- No canonical mosaic, Terrain Native, Standard, voxel or VoxCity candidate-B integration was made.

Code and tests of the preflight are exploratory and Candidate-B specific. Retain the original four ZIP/TIFF hashes and run-03 raw receipts; do not replace or mutate their bytes.

## 2. Follow-up external source review (2026-11-04)

**Direct source evidence:**
- [Tokyo ward dataset, G-Spatial](https://www.geospatial.jp/ckan/dataset/tokyopc-23ku-2024) and [Tokyo public mirror](https://odm.bodik.jp/ja/dataset/t000029d00000000241): JGD2011 / Plane Rectangular CS IX and 0.5m ground DEM; **no ward-specific vertical datum declaration was found on the catalogues checked**. The actual ward TIFF has unnamed embedded datum, trailing EPSG:6677 authority, and Rasterio `to_epsg() is None`, per PR #141. This supports **conditional horizontal grid comparison only**, not silent CRS rewriting.
- [Tokyo Tama catalogue](https://catalog.data.metro.tokyo.lg.jp/dataset/t000029d0000000020): source-declares elevation relative to Tokyo Bay mean sea level (T.P.).
- [Tokyo island catalogue mirror](https://odm.bodik.jp/ja/dataset/t000029d0000000019) **explicitly** declares Tokyo Bay mean sea level, unlike the ward catalogue. Island/Tama declarations must **not** be inherited by wards.
- [Tokyo Bureau of Construction benchmark description](https://www.kensetsu.metro.tokyo.lg.jp/jimusho/tech/04-kijyun/kijyunsetu) and [GSI geodetic explanation](https://www.gsi.go.jp/sokuchikijun/datum-main.html) explain the ordinary T.P. height reference; neither attests that the exact ward source TIFFs use that datum/realization.
- [EPSG:6695](https://epsg.io/6695) designates JGD2011 (vertical) gravity-related height. Mixed Building records vertical EPSG:6695 and copies source H unchanged. The source declaration, actual survey realization, epoch, height correction and joint usability with each DEM are separate checks.
- The 2025-04-01 national elevation-revision context may affect *later* mixed-source work; it is **not** evidence of a particular correction to these 2023/2024 raw TIFFs and is not an instruction to shift their values. [GSI geodetic explanation](https://www.gsi.go.jp/sokuchikijun/datum-main.html).

**Review finding:** existing public references do **not** resolve the ward DEM's precise vertical datum, output epoch or projection-WKT mismatch. A numerical overlap median close to zero is a consistency clue, not provenance proof.

## 3. Decision framework (separate gates)

| Gate | Evidence required | Allowed outcome | Not allowed |
|---|---|---|---|
| T0 Source semantics | Ward provider-specific metadata: vertical datum, unit, geodetic realization/epoch; actual TIFF `AREA_OR_POINT=Point` and raw GeoTIFF grid semantics; relation to PLATEAU EPSG:6695 H | `VERIFIED`, `SOURCE_DECLARED`, or `UNRESOLVED`; documented exact limitation | Assume ward T.P. from other Tokyo products or EPSG:6677 |
| T1 Overlap & seam diagnostics | Replay original four hash-verified TIFFs, cell-based spatial distributions and simulated source-selection seam metrics | Diagnostic report with conditionally comparable values | Offset correction or fusion approval |
| T2 Source-selection review | Explicit deterministic, supported policy, justification, outside-overlap fallbacks, residual seam limits and vertical compatibility decision | Approved experimental prototype policy or `HOLD` | Treat greater source recency as automatic priority |
| T3 Terrain Native/Standard prototype | Fresh-run isolated preparation, consistent CRS/height semantics, 100% AOI coverage, full provenance and tests | Separate experimental prototype review | Silent reprojection, raster relabeling, old A2/A3 mutation, formal acceptance by implication |
| T4 Model integration | Building Z / terrain height compatibility and consumer/VoxCity grid agreement independently confirmed | Separate model readiness decision | Infer model success from 100% DEM coverage |

T0 and T1 may proceed independently. **T2 and later cannot be approved solely by T1 numeric agreement.** Existing `OUEM_Standard_Terrain_v0.1.md` is provisional and standardizes one GeoTIFF without mosaic/reprojection; a multi-source preparation, if approved, must be an explicit upstream stage with independent provenance, not an undocumented modification to the standardizer.

## 4. T0: metadata investigation (read-only)

1. Review the ward's dataset metadata, downloadable distribution documentation and any **small** relevant metadata sidecar of the source. Record original citation URLs, quotation/section and retrieval date.
2. If feasible without bulk download, inspect source LAS/LAZ *header/VLR* or delivery metadata, separating horizontal EPSG from actual vertical datum. Do not download large point-cloud archives merely to infer datum silently.
3. Assess `AREA_OR_POINT=Point`, raw tie point vs GDAL/Rasterio normalized affine, reference pixel centres and all four 0.5m grid origins. Do not shift any raster by half a pixel based on tag text alone.
4. Compare source-declared vertical identity and epoch to Mixed Building compound EPSG:6697 / vertical EPSG:6695. Document which assertions are **direct declarations**, **derived implications**, and **unknown**.
5. If ward provider-specific evidence remains missing, prepare a short precise inquiry to the Tokyo Digital Twin dataset owner. Request the exact vertical reference, height-generation method, any 2025 revision, horizontal WKT intent and applicable source metadata; **do not send without user approval**.

T0 is `UNRESOLVED` until direct ward evidence is obtained. Ordinary GSI/Tokyo benchmark conventions alone are insufficient.

## 5. T1: targeted real-data diagnostic (read-only)

Use existing candidate B raw TIFFs only; verify all four expected SHA-256 fingerprints from the PR #141 record. No new remote download is needed for this task.

**Overlap geometry and distribution:**
- Recompute all 40,000 masks and the 4,336 shared centres; require exact count agreement or stop.
- Produce georeferenced `ward-minus-Tama` diagnostic grid **with NoData outside overlaps**, source-validity map (Tama-only/ward-only/both/neither), and maps of differences by distance to source mask boundary. These are **diagnostic outputs**, not Terrain products.
- For each mesh and total overlap, compute n, min/max, mean, median, MAE, RMSE, P01/P05/P25/P75/P95/P99 and counts exceeding absolute thresholds 0.05/0.10/0.20/0.50m. Record extreme-cell coordinates and nearby source-mask/geographic context. Document numerical precision.
- Segment overlap spatially and assess whether differences are broadly constant, localized, or correlated with local slope. Do **not** interpret one extreme as a systematic datum offset.

**Selection-policy counterfactuals:**
- `TAMA_FIRST`: use Tama when valid, otherwise ward; `WARD_FIRST`: reverse. Both use original cell values, without adjustments. Do not assign scientific superiority to either.
- For each scenario, report counts by chosen source, number/location of source-switch edges, and adjacent-cell height jumps at every source-switch edge. Compare those jumps against local gradients in non-switch edges; distinguish natural slope from possible stitching artefacts.
- Distinguish north/south mesh boundaries, intra-source tile edges, and cross-source switches; the prior exclusive-cell adjacency statistic of zero does **not** establish a seamless future mosaic because it excludes the overlapping selection interface.
- In addition to absolute cross-source differences, calculate scenario differences and isolate maximum discontinuities. No universal 'acceptable height jump' threshold is to be invented for this PoC.
- Optional visual overlays may help review; record exact CRS, raster affine, source labels and masks.

**Expected local artifacts** (all under a fresh ignored `data/work/terrain-candidate-b/diagnostics-*/`): `diagnostic_report.json`, optional diagnostic raster maps and PNG, and input fingerprint receipts. Publish a concise findings MD in `docs/experiments/real_komae_source_h/`, with aggregation code/tests as needed. Do not commit raw ZIP/TIFF/PBF, or the candidate mosaic as a purported Standard Terrain. Failure should be `BLOCKED` with cause and no accepted outputs.

## 6. Deferred alternatives and decision criteria

- A hard administrative-boundary clip may create unsupported discontinuities and is not assumed equivalent to the actual validity masks.
- An overlap average or feather may smooth a visible join but produces *new* elevations with uncertain provenance; do not select before T0 and T1.
- A uniform vertical offset based on means/medians assumes a constant datum difference unsupported by the present min/median/maximum pattern.
- A higher-level DEM from another provider is a fallback to investigate only if T0/T1 cannot justify a bounded prototype. It requires its own source/accuracy/vertical audit.

**T1 diagnostic acceptance:** exact input hashes and masks; reproducible values/plots; all scenarios explicitly hypothetical; no source reassignment or Standard generation.  
**T2 readiness:** separate documented choice of source ranking/cutline and its scientific rationale; compatible vertical semantics and target year assessed; quantitative seam evidence and residual limitations; reviewed by a person.  
**Formal status:** T1 PASS does not turn `terrain_integration_ready` true. `CONDITIONAL / HOLD` remains valid and preferable to silent coordinate repair.

## 7. Next Codex task proposed

Implement T1 **read-only spatial-overlap diagnostics** by reusing the locally available four verified GeoTIFFs from #141. Include synthetic regression tests, source mask/index sanity checks and exact replay instructions. Also perform the bounded T0 public metadata check (no costly LAS downloads). Submit code and real-data diagnostic memo in a *separate implementation PR* for independent review. **Do not auto-merge, do not build a Standard Terrain or run VoxCity.**
