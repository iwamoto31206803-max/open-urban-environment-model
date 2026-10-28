# Real Komae source-H Building results — 2026-10-28

Status: **COMPLETED technical experiment**. Real PLATEAU CityGML → fixed
Converter → source-H Native → source-H Standard → independent Consumer
Validator completed on local Windows. All selected H ordinates were retained
exactly; numerical Terrain correspondence was checked without a Z correction.
This is a small-area experiment, not formal acceptance or nationwide evidence.
Source-H eligibility remains NOT_ESTABLISHED; Phase 5 A1–A4 remain OPEN.

Run: `data/work/real-komae-source-h/run-20261028-04/`.
[Reproduction procedure](README.md). Interpreter: repository
`.venv/Scripts/python.exe`, Python 3.11.9, Windows 10.0.26300 AMD64. No GIS Python
or QGIS runtime was used. The baseline worktree was `5eb774e` (PR #96 content;
subsequently merged as `b75a9c6`). Runtime/code/input fingerprints are in the
local report and manifests. Inputs were unchanged by pre/post SHA-256 checks.

## Inputs and bounded compatibility

Source ZIP:
`data/raw/building/plateau_komae/2025_v5_api/13219_komae-shi_pref_2025_citygml_1_op.zip`.
Members: `udx/bldg/53393456_bldg_6697_op.gml` (238,819,640 bytes) and
`udx/bldg/53393466_bldg_6697_op.gml` (199,626,757 bytes).
AOI: `config/study_areas/komae_09LD3451.yaml`, EPSG:6677,
400 × 300 m. Terrain: existing
`data/work/terrain-reproducibility/komae-20261026-01/generated/standard.tif`,
800 × 600 cells at 0.5 m; source-declared Tama T.P. provenance. Its historical
pending-status text is interpreted through the existing A2 provenance record,
not promoted to a new acceptance decision.

The source inspection found 174,195 and 141,408 xlinks respectively. All are
`gml:surfaceMember xlink:href="#pol_…"` in LoD2 Solid CompositeSurface exteriors,
pointing to inline boundary Polygons in the same Building. No missing target
or duplicate XML ID was found. The bounded reader resolves these forward
references, requires a bijection with the Building's LoD2 boundary Polygons,
and counts each face once. Unknown, repeated, missing, external, cross-building
or mixed reference forms fail. Dimension 3 is inherited from explicit geometry
ancestors where posList omits it. This adds no general CityGML parser.

Fixed Converter: `nusamai.exe` 0.1.19, recorded upstream commit
`ce7766df9788ce391b149c55df16d33082d0bc72`. SHA below identifies the actual
previously fixed binary; this experiment does not independently certify its build.
The executed command supplies both target members and
`--sink gpkg --epsg 6697 -t use_lod=lod2`. Exit code: **0**.
ZIP codelists retain their original relative placement. The six remaining
Converter warnings concern unsupported Point-valued attributes `location`,
`startPoint`, `endPoint`, `origin`, `elevationValue`, and `pos`; these attribute
types are not independently preserved/accepted by this experiment. Required
building geometry, ID and Standard provenance checks passed.

## Geometry and H results

| Artifact / scope | Buildings | LoD2 Polygon faces | Vertex occurrences |
| --- | ---: | ---: | ---: |
| Converter / Native, both full members | 7,312 | 315,603 | 1,420,021 |
| Standard, complete geometries intersecting AOI | 173 | 7,247 | 32,689 |

Vertex counts include ring closures. No interior rings occur in these selected
LoD2 faces. The two members contain another 487 buildings without source LoD2;
their IDs are inventoried as exclusions. AOI selection excludes 7,139 eligible
buildings; geometry is not clipped. These are the 2025 source counts, separate
from the historical accepted 111-building dataset.

Raw → Converter: exact lon/lat/H, face/ring/multiplicity and ID correspondence
PASS, allowing only face order, cyclic ring starts and reversal. Actual GPKG
CRS/WKT/BLOB SRID is compound EPSG:6697 with Z. Converter → Native:
all XYZ, IDs, nested order and geometry BLOB preservation PASS.
Native → Standard: horizontal-only EPSG:6668 → EPSG:6677; **all H binary64
ordinates exactly unchanged, maximum H difference 0 m**. H never enters PROJ;
EPSG:4979 is not used. Independent Consumer validation: **PASS**, 173 buildings,
32,689 vertices, ordered geometry and H exact, maximum XY error 0 m against
its independent traversal (computational tolerance 1e-7 m).

Building IDs, deterministic OUEM IDs and source provenance are retained.
Thirteen `measuredHeight` values are nonpositive source sentinels; they are
retained as source attributes and were not used to infer or adjust geometry H.

## Terrain Z comparison

| Quantity (metres) | Min | P05 | Median | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| Selected building vertex H | 20.362318 | 23.000252 | 28.228203 | 34.903198 | 47.520199 |
| Existing DEM, whole AOI | 19.578 | 21.383 | 24.017 | 24.772 | 25.296 |
| Per-building top H − sampled DEM mean | 1.986684 | 2.732527 | 7.927735 | 12.204077 | 23.489750 |

Per-building geometric height (maxH−minH) ranges 2.040023–23.806095 m.
Bottom H−sampled DEM mean ranges −1.443947–0.003582 m. All sampled roof tops
are above terrain; no bottom-offset magnitude exceeds the exploratory 3 m
review flag. These diagnostics show no obvious large uniform vertical offset
or negative/zero geometric building height in this selected area. They do not
establish individual surveyed height accuracy or explain every bottom offset.

Sampling uses all existing cells touched by each complete geometry's XY
surfaces, without topology repair, resampling, fill or height adjustment.
All sampled cells are valid. **152 buildings have complete DEM coverage;
21 cross the DEM boundary** and carry `PARTIAL_DEM_COVERAGE`. Their statistics
describe the covered portion only; correspondence outside the DEM is untested.
Every building's H extrema, geometry height, original measuredHeight, DEM
sample count/distribution, top/bottom differences and flags are in `report.json`.
This diagnostic ground mean is not a VoxCity effective-ground estimate.

Building EPSG:6695 H and Terrain T.P. remain source declarations. Numerical
correspondence is not independent verification of datum realization, survey
accuracy or observation-date consistency. No constant Z correction, H→h
conversion, ground snapping or unsupported height adjustment was performed.
No visual QGIS acceptance, voxelization, canopy integration or solar run was
performed; existing formal acceptance records and eligibility/gates are unchanged.

## Local evidence and fingerprints

The run directory retains `converter.gpkg`, Converter stdout/stderr and
`converter-run.json`; source evidence/ZIP-member hashes and `plan.json`;
`native/native.gpkg` and `standard/standard.gpkg` with adjacent manifests and
receipts; `report.json` with Consumer/Terrain details; and `RESULTS.md`.
Large data and generated manifests remain ignored and are not committed.

| Evidence | SHA-256 |
| --- | --- |
| Input ZIP | `659fe9f96eb8a45b57e788b52d6e80edef154ddc3aa9b4f2c1ea117c61a5a555` |
| Fixed Converter | `0195a11df4fd0ef30dcd5578175035a918c41285b1fcc329f3399f5337326f1b` |
| Existing Standard Terrain | `0afb6d1706b97bd39c8c93ff8feb580094fe585f567e2de1f2081c082602f90a` |
| Native GPKG | `b18175e78ee5beafde1bf8fb7839f48ebff67930625d9cd4f25811bd3434b3cd` |
| Standard GPKG | `a23829bbcb689a3e830535b7654f0c5b892554b0ad26e0222eaf146e5b9aca3c` |
| Completed report.json | `fe2cf29385ad49b203889e66cc3604086fcd9bf0487ea18ac6214c4862c36f77` |

Earlier failed/partial runs are retained separately. `run-20261028-01` had
misplaced codelists and is not completion evidence; `02` failed on ZIP directory
entries; `03` generated Native/Standard but failed at the Consumer configuration
locator. These are not reported as successful integrations. The final `04` run
completed the whole path with corrected extraction and explicit configuration.

## Tests

New focused tests: **14 passed**, 3 Rasterio PendingDeprecationWarnings.
They cover forward internal references and exact H/faces, missing/unknown/
duplicate/external/wrong-type targets, duplicate XML IDs, mixed references and
dimension conflicts; diagnostic DEM coverage/NoData; and orchestrator ZIP
layout, explicit configuration path, report creation and no-overwrite behavior.
Synthetic regression tests remain distinct from the real-data evidence above.

Final whole-suite command: `.venv/Scripts/python.exe -m pytest -q -ra --tb=short`.
Result: **878 passed, 5 skipped, 254 warnings in 239.93 s**, no failures.
All five skips are Windows symlink privilege/Developer Mode cases (WinError
1314 / unavailable privilege). Warnings comprise Rasterio/Affine matrix-operation
PendingDeprecationWarnings and the existing source-H stat/fstat clock diagnostic.
Full log: `data/work/real-komae-source-h/pytest-final.log`. Existing source-H
Native/Standard/Consumer and synthetic 2.5D/voxel/solar regression tests passed;
the new forward-reference focused suite was also rerun after its fixture order
was aligned to the actual Komae forward references (14 passed, 3 warnings).
The initial sandbox run encountered existing hard-link publication permission
failures; validation was rerun outside the sandbox using the same OUEM venv,
without weakening publication safeguards. Cloud/Linux and QGIS visual acceptance
were not run.
