# Candidate B Terrain Preflight — Codex execution request (2026-11-04)

## Objective and boundary

Determine actual availability and valid-cell coverage of publicly distributed Tokyo 0.5 m **ground DEM** around the approved experimental Mixed-LoD Candidate B. This is a **read-only exploratory source preflight**, not Terrain Native/Standard production, mosaic approval, VoxCity execution, or formal Acceptance.

- Candidate B CRS: EPSG:6677, bounds `[-22575, -39925, -22475, -39825]` (100 m × 100 m).
- Mixed Standard / Consumer: PR #136–#140 merged; 63 buildings (31 LoD1, 32 LoD2). Do not alter those artifacts.
- Existing accepted Komae terrain `09LD3451`: bounds `[-23600,-40800,-23200,-40500]`; **does not cover B**.
- Source candidates: Tokyo Tama 2023 and Tokyo 23-ku 2024 **0.5 m ground-derived DEM**. Do not substitute DSM or use synthetic values as real evidence.
- The tile index is **not** the DEM itself. Predicted z14 XYZ index `14544/6453` is a lookup starting point, **not a verified source tile ID**.

## Source lookup

Catalogue:
- https://www.geospatial.jp/ckan/dataset/tokyopc-tama-2023
- https://www.geospatial.jp/ckan/dataset/tokyopc-23ku-2024

Candidate PBF templates (verify against live catalogue before relying on them):
- `https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2023/dig/Vectortile/tama/grd50/{z}/{x}/{y}.pbf`
- `https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2024/dig/Vectortile/23ku/grd50/{z}/{x}/{y}.pbf`

Inspect existing `docs/planning/OUEM_Kunitachi_Data_Source_Preflight_v0.1.md` for the tested PBF `MESH_NO`/`URL` → original ZIP → TIFF workflow, and `docs/planning/OUEM_Data_Pipeline_Generalization_Audit_v0.1.md` for Terrain compatibility limits.

An earlier chat prototype `ouem_candidate_b_terrain_preflight.py` and research memo `OUEM_Candidate_B_Terrain_Preflight_20261104.md` were prepared outside the repository. They are **unverified against real PBF/DEM**, and are not prerequisites. Implement or adapt a minimal, auditable read-only preflight in the repo as appropriate; do not trust untested parser assumptions.

## Execution steps

1. Check the current main, the existing preflight conventions and dependency availability. Preserve accepted artifacts and existing implementations.
2. Fetch/inspect **both** source indexes around Candidate B. Decode geometries with explicit CRS and inspect `MESH_NO` and `URL`; record index URLs, retrieval status, hashes, and selected source tile IDs. If a PBF cannot be reached, record network/DNS/HTTP evidence, do not invent IDs.
3. Download only candidate source ZIPs needed to establish actual coverage, using bounded size, safe ZIP member selection and integrity checks. Keep Raw bytes and receipts outside tracked Git. Preserve source identity, URL, hash, licence/attribution, original metadata.
4. Independently inspect each real GeoTIFF: CRS, bounds, affine alignment, resolution, shape, dtype, scale/offset, band count, NoData, ground-DEM semantics and provider-declared vertical datum. Do not infer T.P. from EPSG:6677.
5. For the exact 100m AOI, compute **valid-cell coverage**, not only bounding-box coverage. At 0.5m with aligned grid, expected 200×200=40,000 cell centres; if alignment differs, report actual grid and coverage method. Evaluate Tama and 23-ku separately and combined. Report uncovered cells, overlapping cells, source boundaries and any observed overlap elevation differences. No interpolation, extrapolation or unreviewed priority/merging.
6. Determine whether a **single source** suffices. If not, report the smallest source set and unresolved seams/vertical issues; do **not** generate a canonical mosaic without further approval.
7. Compare only source-declared vertical semantics with the Mixed Building EPSG:6697 H metadata. Declare actual survey/datum realization compatibility **unverified** unless independent evidence exists.
8. Record limitations and proposed next step: direct Native/Standard registration of one compliant tile vs reviewed AOI mosaic/other data. Native/Standard do not themselves mosaic or enforce AOI coverage.

## Deliverables

- Small reproducible source-preflight code/tests, if necessary, in a separate new path; no modifications to existing accepted pipelines.
- `docs/experiments/real_komae_source_h/MIXED_LOD_TERRAIN_CANDIDATE_B_PREFLIGHT.md` with actual URLs, tile IDs, byte SHA-256, valid coverage per source, overlap/seam findings, CRS/vertical provenance, failures, Windows execution commands, and explicit `EXPERIMENTAL / NOT_FORMALLY_ACCEPTED` status.
- Local new-run `report.json` and receipts under `data/work/terrain-candidate-b/<new-run>/` (gitignored; do not commit Raw ZIP/TIFF/PBF or local absolute paths containing private information).
- Tests: synthetic index/DEM and failure paths; report exact test commands and counts. Do not label synthetic success as real-data verification.
- If network access fails, produce a reproducible **BLOCKED** report and a precise next action; do not report 100% coverage without real source data.

## Review gates

PASS for preflight only if real data and provenance establish AOI valid-cell coverage, selected source(s), and all unresolved vertical/seam limitations are explicit. Otherwise report BLOCKED/CONDITIONAL with evidence. Never silently repair/clip/resample data or mutate earlier runs.

**Create/update the PR with code and results for review; do not auto-merge.**
