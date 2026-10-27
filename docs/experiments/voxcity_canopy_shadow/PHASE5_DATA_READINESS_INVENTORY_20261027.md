# Phase 5 data readiness inventory — 2026-10-27

## Executive Summary

**Data readiness: incomplete; Phase 5 execution remains blocked by the existing
pre-start Gate.** Terrain and the experimental Height Envelope chain are locally
available and hash-consistent. The selected ROI and initial halo have valid
numeric samples. Building source/Converter/Native/Standard files were not found
within the bounded search. That is a planning input, not a failure of historical
A1/A3 acceptance: their exact input bytes are not supplied by their path records.
No download, conversion, data generation, Phase 5 implementation or gate closure
was performed. Proposed actions below require separate authorization/review.

## 1. Baseline, authority and bounded discovery

Fetched main: `9463d7fbd5ac0f26be78106d794ed97a277c8c41`; GitHub confirms PR #79
merged at that commit. Read-only observation: **2026-10-27 14:30 JST** on Windows.
This is an Experimental discovery record under [Documentation Governance](../../OUEM_Documentation_Governance_v0.1.md),
not a replacement for [Building Current State](../../status/BUILDING_CURRENT_STATE.md),
[Canopy Current State](../../status/CANOPY_CURRENT_STATE.md), Standards or acceptance.

Search root was this repository (`C:\dev\open-urban-environment-model` on this
workstation). Discovery included ignored `data/raw`, `data/native`,
`data/standard`, `data/model`, `data/output`, `data/work` where present, and known
run directories; a bounded repository walk checked `.gml`, `.citygml`, `.gpkg`
candidates. `.git`, `.venv`, caches, `node_modules`, `.codex`, `.aws`, `.agents`
and reparse directories were excluded from that walk. Separately, only known
venv metadata/installed source files and executables explicitly named in the
existing GIS runtime snapshot were read/existence-checked. No Downloads folder,
unrelated user directory, external drive or whole-PC search was performed.
No search read errors were reported. Outside these scopes, availability is
**Unverified**, not Missing.

The sole GeoPackage candidate in that walk was
`data/work/height-envelope-3d/komae-20261026-01/canopy_cells_visualization.gpkg`;
it is visualization geometry, not a Building dataset or accepted canopy source.
Existing raster/JSON inputs were opened read-only; nearest sample and mask counts
were calculated in memory without writing rasters or running generation CLIs.
Selected-file hashes were checked before/after inspection and unchanged. An
ignored discovery receipt (not a formal record) is retained at
`data/work/phase5-data-readiness/20261027-01/readonly-inventory.json`.
Local absolute paths inside historical manifests refer to this workstation;
repository-relative identities below are preferred for reproduction planning.

## 2. Required data and local presence

### Building and historical canonical paths

Missing means absent at the stated expected path and no Building candidate found
in the bounded repository search. Size/hash are N/A for missing files. No past
acceptance hash is invented; these rows are **not currently usable** for Phase 5.

| Required item / expected repository-relative path | Actual path | State | Bytes / SHA-256 | Historical correspondence / Phase 5 use |
|---|---|---|---|---|
| PLATEAU archive/release: UNKNOWN | Not identified | Unverified | UNKNOWN | Dataset release/year, archive and tile list must be identified before acquisition |
| `data/raw/building/plateau_komae/53393465_bldg_6697_op.gml` | None found | Missing | N/A | Recorded input example; not proof of the exact archived A1 release |
| `data/work/building/plateau_komae/53393465_bldg_6697_op_convert.gpkg` | None found | Missing | N/A | Manual Converter intermediate; cannot serve as Native without ingest |
| `data/native/building/komae.gpkg` | None found | Missing | N/A | A1 Native `building`, historically 3,637 features |
| `data/native/building/komae.gpkg.manifest.json` | None found | Missing | N/A | Need actual source/output identity, layer and runtime evidence |
| `data/native/building/komae.gpkg.receipt.json` | None found | Missing | N/A | Ingest reuse receipt; does not itself prove CityGML-to-Converter identity |
| `data/standard/building/komae.gpkg` | None found | Missing | N/A | A1/A3 historical 111-feature Standard; no selected current bytes |
| `data/standard/building/komae.gpkg.manifest.json` | None found | Missing | N/A | No current ID/Z/selection/hash chain to inspect |
| `data/standard/terrain/komae_09LD3451.tif` and adjacent `.manifest.json` | None at these paths; actual retained pair below | Missing at historical paths | N/A at these paths | Retained reproduction bytes provide an alternative location; do not move old files or rewrite old manifests |

The [A1 record](../../../experiments/a1_e2e_pilot/README.md) accepts its recorded
3,637-feature Native / 111-feature Standard conversion. The [A3 record](../../acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md)
accepts frozen Komae Building/Terrain through voxelization, but explicitly asserts
no artifact hashes. Counts and paths alone cannot establish that regenerated
files are the same historical dataset. The narrower [contained E2E record](../../acceptance/OUEM_Komae_Contained_E2E_Acceptance_20261018.md)
is not a substitute identity for the full 111-feature baseline.

### Existing selected files

Every row below is **Exists** at the actual repository-relative path listed;
expected retained-run location equals actual location. Sizes are bytes and hashes
were computed from actual files in this discovery. These are candidates for
reuse, not blanket Phase 5 approval. Acquisition/Native/Standard and bridge
relationships are assessed in section 3; run JSONs and diagnostics are supporting
evidence, not canonical replacements. GIS snapshot contents are environment
specific and its existence does not validate executing its recorded interpreter.

| Item | Expected = actual path | Bytes | SHA-256 |
|---|---|---:|---|
| Terrain Raw ZIP | `data/raw/terrain/tokyo_tama_dem_050m/komae/acquisition-20261026-01/09LD3451.zip` | 837,282 | `8b54c4cd58e17a6edf86ca7ad9e71672776c90669d116981d1368e871e7c393d` |
| Terrain Raw TIFF | `data/raw/terrain/tokyo_tama_dem_050m/komae/acquisition-20261026-01/09LD3451.tif` | 1,922,867 | `c747f2ae2ee30f67da98c1c90961f6a094fa0fca8ba3f15a1131c09783d73824` |
| Terrain acquisition manifest | `data/raw/terrain/tokyo_tama_dem_050m/komae/acquisition-20261026-01/acquisition-manifest.json` | 4,524 | `ea0c54d798db06274cef95b33c43439924742ea8707fb24a3c1de8e5f0180e9d` |
| Terrain Native registration | `data/work/terrain-reproducibility/komae-20261026-01/generated/native.json` | 1,478 | `1226640017845ef9f4858d970b70b947700c706ca90431f15d2668e11fefef92` |
| Terrain Standard TIFF | `data/work/terrain-reproducibility/komae-20261026-01/generated/standard.tif` | 1,080,470 | `0afb6d1706b97bd39c8c93ff8feb580094fe585f567e2de1f2081c082602f90a` |
| Terrain Standard manifest | `data/work/terrain-reproducibility/komae-20261026-01/generated/standard.tif.manifest.json` | 2,738 | `5e96bf3e0ababad7e2f79a0d2090d0356fdc707dff6115575c8b0ba8b88f5dbb` |
| CHMv2 retained tile index | `data/raw/canopy/meta_chmv2_komae_committed_audit_20261025/tiles.geojson` | 58,856,501 | `3f3d102d4a4d2d221125744c9c081b2420ce1cf1322e08c568ebf48678e84c2e` |
| CHMv2 retained COG | `data/raw/canopy/meta_chmv2_komae_committed_audit_20261025/1330021123.tif` | 68,699,950 | `6313f286dca3b9f760be95d998e9648d0dd77b0a9305081b67422150340af862` |
| CHMv2 acquisition record | `data/work/meta_chmv2_komae_committed_audit_20261025/acquisition-record.json` | 6,132 | `ab83b9b466b85a4dd2a4a73749b1c2fffb68104b88f9d630ea88f2da76c956e0` |
| CHMv2 AOI crop | `data/work/meta_chmv2_komae_committed_audit_20261025/chmv2_aoi.tif` | 18,861 | `c5f99a4e9b21e8f419825ef2cac25ec7b36bafbe8a79a89b062201343f0ef880` |
| Height Envelope manifest | `data/work/height-envelope/komae-exploratory-20261026-01/generated/height_envelope_manifest.json` | 11,829 | `6121cbf732f8ece9553013be2483203f08faf9a8d364136a919c184b46738d68` |
| Absolute top Z | `data/work/height-envelope/komae-exploratory-20261026-01/generated/canopy_top_z.tif` | 308,739 | `65263bb32aa846688b3fecee3e7b0893c6a9d6f2e8fa9eebaf95c0bc576aed17` |
| Absolute bottom Z | `data/work/height-envelope/komae-exploratory-20261026-01/generated/canopy_bottom_z.tif` | 298,845 | `61e82f1d8e9c1c4afc653bf6d850cc35052535fd643462da0b89403efeda158e` |
| Envelope validity state | `data/work/height-envelope/komae-exploratory-20261026-01/generated/height_envelope_state.tif` | 1,724 | `6a3debfbcd220d6bef9cdb736cc7d8abd545ee3156121746e019093edef71992` |
| HAG/compatibility evidence bridge | `data/work/height-envelope/komae-exploratory-20261026-01/inputs/source-evidence.json` | 2,315 | `afdf8560ac1d7a94cf599ffaa7fe17bbba29df5fca7a61df994052cdc04bf6a9` |
| Primary-source text snapshot | `data/work/height-envelope/komae-exploratory-20261026-01/inputs/hag-source-statement.txt` | 868 | `213860b4fe980cc1fed0857dfa36ccffa0f5c5d5fd5db65699f583fe9de8a32d` |
| Limited compatibility approval record | `data/work/height-envelope/komae-exploratory-20261026-01/inputs/limited-compatibility-review.md` | 1,669 | `066cbd000f58bdb7aa4e791cdb8a7ba01750ff19bef9a40fbff3b7e3f2c3bcdd` |
| Retained sampled DEM diagnostic | `data/work/height-envelope/komae-exploratory-20261026-01/diagnostics/sampled_dem_z_nearest.tif` | 271,842 | `f456fd5a94e7f0b9a94398281d9b0db35835f4959f23fede09e143ccefe7bd33` |
| Retained sampled CHM diagnostic | `data/work/height-envelope/komae-exploratory-20261026-01/diagnostics/sampled_chm_hag_nearest.tif` | 29,004 | `a96d8cbc578e5d56cfd2c42387780f44fbc4218ba14b0ba22d9f826ace31f9a8` |
| Study-area configuration | `config/study_areas/komae_09LD3451.yaml` | 239 | `ccb6f29d713286bee12f6cd041b2085057b41b7d17f389c0422c8146dd984899` |
| Phase 2 existing run record | `data/work/voxcity-canopy-shadow/komae-phase2-20261027-01/run.json` | 12,761 | `e153e8da170d6dc34cfaf76bd6b1564f7924e208695e4fef75208d664bcf571d` |
| Phase 3 existing run record | `data/work/voxcity-canopy-shadow/komae-phase3-20261027-01/run.json` | 34,737 | `5ffea2f0aaad4a005bd8eaa768371aff3b2056bd73b6ea14918df7d6597fadcd` |
| GIS runtime snapshot | `scripts/work/.runtime/plateau_komae_gis.json` | 3,728 | `f9760fad0f9c5317b4bf79f671b7575b7f979e51441e81d127cb0d041fd2f0a7` |

## 3. Terrain / Canopy lineage and reuse eligibility

**Terrain:** acquisition status is COMPLETED; actual ZIP/TIFF hashes match its
manifest. The TIFF hash matches the original [2026-10-06 A2 acceptance](../../acceptance/OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md).
Native registration points to that Raw TIFF and hash; Standard manifest points to
that Native registration, the same Raw source, and its actual output hash.
Standard TIFF SHA-256 equals the historical A2 Standard output hash. This supports
reuse of those bytes at their retained run location, without new generation or
formal re-acceptance. The generated manifest's pending/provisional status string
is preserved; the existing [reproducibility verification](../../acceptance/OUEM_A2_Terrain_Reproducibility_Verification_20261026.md)
separately records technical PASS and pending formal approval. Do not rewrite
that status based on this inventory.

Source is Tokyo Digital Twin **Tama** ground grid 0.50m, tile 09LD3451; the
[source correction](../../acceptance/OUEM_A2_Terrain_Source_Provenance_Correction_20261026.md)
explains older 23-ku references. Actual Standard raster: EPSG:6677, Float32,
800 columns x 600 rows, 0.5m, bounds `[-23600,-40800,-23200,-40500]`, NoData -9999;
480,000 mask-valid finite cells. TIFF tags and manifest retain **source-declared
T.P. (Tokyo Peil / Tokyo Bay mean sea level)**, not independent survey validation.
The original TIFF retains its different source NoData sentinel. No file was
relocated to the historical canonical path.

Recorded source/terms, not newly contacted URLs:
[original ZIP](https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2023/dig/grd50/09LD3451.zip),
[Tama catalogue](https://catalog.data.metro.tokyo.lg.jp/dataset/t000029d0000000020),
[distribution catalogue](https://www.geospatial.jp/ckan/dataset/tokyopc-tama-2023),
[terms](https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2023/dig/doc/license.pdf).
The acquisition manifest records CC BY 4.0 and attribution. Live availability
and current terms were not reverified online in this task; retain the prior
license/source evidence in [Terrain acquisition documentation](../../Terrain_Acquisition_PoC_v0.1.md).

**Canopy:** the selected committed-audit acquisition record is COMPLETED. Its
retained index, tile and crop actual hashes match the record. This record says
`local_copy` / `acquired_at=null` for the replayed inputs; it is evidence of an
offline committed-code replay, not a new external download. The separate original
acquisition chronology remains in [CHMv2 acquisition/audit documentation](../../Meta_CHMv2_AOI_Acquisition_PoC.md).
Its recorded provider release is `dinov3_global_chm_v2_ml3`, tile `1330021123`.
Actual crop is EPSG:3857, UInt8, 414 columns x 313 rows, about 1.194328567m pixels,
NoData tag None with effective source masks; all 129,582 crop pixels are valid.
Recorded source is the [AWS registry](https://registry.opendata.aws/dataforgood-fb-forestsv2/)
and the tile/index URLs under the acquisition record's prefix. Prior acquisition
documentation records CC BY 4.0; live source/terms were not reverified here.

Envelope status is COMPLETED. All eight input-file hashes and three output hashes
match; bridge CHM/acquisition identities, quoted snapshot/hash, limited-review
hash and DEM identity/reference agree. The snapshot establishes a recorded HAG
metres declaration; its reviewer is the requesting human's limited exploratory
approval, not an independent expert survey. Scientific source accuracy, CHM
model-ground versus DEM differences, source timing and horizontal alignment
remain unresolved. The bridge cannot authenticate scientific truth by hashing.

Envelope rasters are EPSG:6677, north-up 1m, 400 columns x 300 rows at the same
400x300m AOI. Top/bottom are Float32 absolute elevations with -9999 NoData; state
is UInt8 without a NoData tag, and the actual state histogram is **1:120,000**.
State=1 means numeric validity, not canopy presence. CR=0.60 and nearest/nearest
are the retained PoC choices. There are no accepted canopy polygons or independent
assessment coverage. Neither CHM=0 nor TREE=0 establishes absence; keep source
samples/masks/state and evidence alongside any future voxel arrays. See
[Height Envelope contract](../../CHM_Height_Envelope_PoC_v0.1.md),
[Standard Canopy DRAFT](../../OUEM_Standard_Canopy_v0.1_Draft.md), and
[Phase 4B audit](PHASE4B_CANOPY_PRESENCE_AND_COVERAGE_AUDIT.md).

Existing Phase 2 and Phase 3 run records are COMPLETED. Their recorded input
hashes were rechecked read-only (34 and 48 entries respectively), with no mismatch.
This did not rerun their fixtures/voxelization/solar computations or revalidate
all historical output arrays. [Phase 2 results](PHASE2_RESULTS_20261027.md),
[Phase 3 results](PHASE3_RESULTS_20261027.md) and [Phase 4A](PHASE4A_OBSERVER_GEOMETRY_AND_VERTICAL_CONTRACT.md)
remain bounded historical verification, not Building readiness evidence.

## 4. ROI / halo coverage: observations, not bounding-box inference

Use the proposed [Phase 5 profile](PHASE5_INTEGRATION_PLAN_v0.1_Draft.md):
EPSG:6677, 1m; ROI `[-23320,-40760,-23256,-40696]` (64x64);
initial halo domain `[-23352,-40792,-23224,-40664]` (128x128).

Read-only checks transformed every 1m target centre into each source CRS, tested
inverse-affine raster support, read effective masks and inspected finite values
(CHM additionally nonnegative). The state check used **state==1**, not its storage
mask. All top/bottom pixels were finite and unmasked; no masked cells were filled.
All native 0.5m Standard Terrain pixels in each rectangle were also inspected.

| Source / check | ROI | Initial halo domain | Meaning / use limit |
|---|---:|---:|---|
| Raw/Standard DEM usable at 1m centres | 4,096 / 4,096 | 16,384 / 16,384 | No outside/masked/nonfinite samples |
| Standard Terrain native 0.5m usable pixels | 16,384 / 16,384 | 65,536 / 65,536 | Full numeric support within both rectangles |
| CHM crop usable at target centres | 4,096 / 4,096 | 16,384 / 16,384 | No outside/masked/negative/nonfinite samples; not independent assessment coverage |
| CHM positive / zero estimates | 3,842 / 254 | 11,741 / 4,643 | Source height classes, not presence/absence |
| Top/bottom valid mask and finite values | 4,096 / 4,096 each | 16,384 / 16,384 each | Retained diagnostic DEM/CHM samples also usable throughout |
| Envelope state==1 | 4,096 | 16,384 | No missing/invalid/outside bits here; real missing-data behavior is not tested by this all-valid population |
| Building source/geometry coverage | UNKNOWN | UNKNOWN | No selected source or footprints; cannot claim no buildings or complete coverage |

The full numeric support of these samples does not prove all real occluders are
represented. **32m halo sufficiency is not established here.** Selected Building
height/geometry, actual sun elevation/direction, engine ground and observer
coordinates require a scene-specific shadow-reach bound and a covered larger
halo comparison. A canopy-only bound cannot certify the mixed scene. Source
coverage farther outside this initial domain and outside the retained AOI must
be checked explicitly before extending the domain.

## 5. Building reacquisition and reproduction plan (not executed)

Use [A1 acceptance](../../../experiments/a1_e2e_pilot/README.md),
[Windows runbook](../../../scripts/work/README.md), the [existing acquisition inventory](../../planning/OUEM_Data_Acquisition_and_Reproducibility_Inventory_20261025.md)
and [vertical diagnosis](../../research/OUEM_Komae_Building_Vertical_Geometry_Diagnosis.md)
as the historical basis. Distinguish what is known from what must be recovered:

| Question | Known evidence | UNKNOWN / required collection before processing |
|---|---|---|
| Dataset / municipality / release | PLATEAU CityGML, Komae; recorded example `53393465_bldg_6697_op.gml` | Publication year/version, original archive/hash, exact distribution authority and full tile list |
| Download source / license | [Source Catalog DRAFT](../../planning/OUEM_Source_Catalog_and_Acquisition_Recipes_v0.1_Draft.md) lists the generic PLATEAU open-data entry point | Exact historical release URL, file URL, live availability, license/attribution are UNKNOWN; generic project URL is not that release's identity or license evidence |
| Geometry / AOI / LoD | Historical Native count 3,637; Standard count 111 intersecting `[-23600,-40800,-23200,-40500]`; boundary buildings keep full geometry | Exact available per-building LoD, contributing files/BuildingParts and whether one tile covers future halo/exterior occluders |
| Converter | Manual GUI, maximum available LOD, retain 3D/Z; source layer `bldg:Building`, String `id`; direct GDAL conversion had empty-surface failures | Actual version, installation/license terms, precise LoD choices, horizontal/vertical operation, CRS options, screenshots/logs; no assumption that maximum LOD identifies a fixed LoD number |
| Native / Standard identity | Native retains Converter Z; Standard horizontal EPSG:4979 component to EPSG:6677 with Z restored | Actual matching source/Converter vertex pairs and source bytes. EPSG:4979's formal ellipsoidal axis versus retained T.P. interpretation remains unresolved |

No provider was contacted in this task; online identification is **pending**, not
a claimed network failure. First recover the historical release information from
operator notes/archives if available; otherwise select an explicit new candidate
and record the difference. Do not download automatically or silently substitute
a newer release. Missing local files do not require changing historical acceptance.

Existing CLI interfaces, for a **future authorized run only** (not executed here):

```text
.venv/Scripts/python.exe -m ouem.native.building.plateau <converter.gpkg> --output data/native/building/<new-run>/komae.gpkg --source-layer bldg:Building --gis-runtime scripts/work/.runtime/plateau_komae_gis.json
.venv/Scripts/python.exe -m ouem.standardize.building data/native/building/<new-run>/komae.gpkg --output data/standard/building/<new-run>/komae.gpkg --study-area config/study_areas/komae_09LD3451.yaml --source-layer building --gis-runtime scripts/work/.runtime/plateau_komae_gis.json
```

These are templates, not evidence that the selected files or runtime pass checks.
Use new output directories; do not use `--force` or overwrite older manifests.
Only add Native `--expected-count 3637` if reproducing an evidenced identical
input; other releases need their own reviewed expectation. The existing launcher
uses historical default paths/counts and its `ouem` stage also runs pytest, so
it must not be invoked as a read-only discovery command. Manual Converter and
GIS runtime capture are separate steps. Native CLI writes `.gpkg.manifest.json`
and `.gpkg.receipt.json`; Standard writes `.gpkg.manifest.json`.

Source and CLI owners: [Native ingest](../../../src/ouem/native/building/plateau.py),
[Standardizer](../../../src/ouem/standardize/building/__init__.py),
[Building Standard](../../OUEM_Standard_Building_v0.1.md),
[Terrain Standard](../../OUEM_Standard_Terrain_v0.1.md) and
[accepted Building Adapter](../../OUEM_VoxCity_Adapter_v0.1.md).
Inspect [Native tests](../../../tests/test_plateau_building.py),
[Standard tests](../../../tests/test_standard_building.py),
[Adapter tests](../../../tests/test_voxcity_adapter.py) and
[vertical diagnostic tests](../../../tests/test_komae_vertical_provenance.py)
when designing later validation. Their presence does not establish a new run.

To reproduce identity, freeze CityGML/archive/Converter/Native/Standard hashes,
converter settings/version, GIS snapshot, main/module versions, exact source
layer and `id` values, study-area configuration and complete selected geometries.
Standard `source_id` copies Native `id`; deterministic `ouem_id` is UUIDv5 over
`ouem-standard-building-v0.1|PLATEAU CityGML|<source_id>`. Same IDs do not prove
same geometry or release. Manifest timestamps/paths/runtime are variable, so
byte-identical manifest reproduction is not promised.

Compare a future result with the 111-building baseline by matching the actual
old source_id/ouem_id list, per-feature geometry/attributes/Z, AOI selection and
manifests/hashes, if old bytes or a trusted complete inventory are recovered.
Counts alone cannot prove equality. Without them, report **historical byte/ID-set
comparison UNVERIFIED**, and treat newly frozen output as a candidate requiring
separate review. The contained 92-building subset cannot silently replace 111.

For the roughly 37m hypothesis, obtain the full source target ID (the recorded
prefix is `bldg_5f2d3f6c-`), complete CityGML surfaces/BuildingParts/LoD, matched
Converter vertices, Native/Standard geometry, and any saved Adapter per-building
height/ground evidence. The reported single source vertex near 24.44m and
Standard minimum near 61.70m are not a matched-vertex proof. Source-to-Converter
identity needs evidence beyond the Native receipt. The [existing diagnostic](../../../src/ouem/komae_vertical_provenance.py)
requires an existing compatible integration run plus a uniquely matching source
ID and CityGML; these inputs were not found for execution here. Do not subtract
37m, change T.P. labels, or replace geometry height with measuredHeight.

## 6. Runtime and reproduction boundaries

Read-only environment inspection used the repository ordinary Windows OUEM venv:
Python **3.11.9**, Rasterio **1.4.4**, GDAL **3.10.3**, NumPy **2.4.6**,
PyProj **3.7.2**, Numba **0.68.0**, Astral **3.2** (installed pytest **9.1.1**,
not executed). VoxCity installed metadata reports **1.7.0** and PEP 610 commit
`fa212656305328a9a657973bae26f352bfe813bc`, matching [pyproject.toml](../../../pyproject.toml).
All **136 installed Python source RECORD hashes** match their installation
metadata. This is not an independent comparison to the upstream Git tree or
proof that all runtime/solar APIs execute today.

The GIS snapshot and its explicitly recorded Python/ogr2ogr/ogrinfo executables
exist at workstation-specific OSGeo4W paths. Only existence was checked; neither
GIS execution nor Converter installation/version was verified. Snapshot bytes
from this PC are not a portable environment setup. Keep GUI/GIS capture and
ordinary-terminal OUEM execution separate; follow [runtime architecture](../../architecture.md)
and the [Windows environment record](../../development/OUEM_Windows_Development_and_Remote_Setup_20261025.md).
Do not install OUEM into GIS Python or merge runtimes.

Future replays should use existing acquisition/Native/Standard/Height Envelope
CLIs and [Phase 2 usage](PHASE2_USAGE.md), [Phase 3 method](PHASE3_API_AND_METHOD.md),
not duplicate algorithms. This discovery ran none of those launchers, fixtures,
voxel or solar APIs. Phase 5 projected Building mapping/common-ground assembly
has not been implemented or approved by this inventory.

## 7. A1-A4 evidence and dependencies (no closure)

These IDs are the [Completion Gate](PHASE4_COMPLETION_GATE_REVIEW_20261027.md)
pre-start conditions, not historical acceptance milestone names. All stay **OPEN**;
A3 explicitly stays OPEN until chosen Building bytes, hashes, source chain and
vertical evidence are present and reviewed.

| Gate / current state | Existing evidence | Missing evidence / design decision | Acquisition dependency and next step |
|---|---|---|---|
| A1 observer interpretation — OPEN | Phase 4A actual-origin fixtures and option C; Phase 2/3 model-surface observations | Approval to use the public model-surface map with actual XYZ reporting; exact physical DEM+1.5m is not established | Can review before Building download; if exact physical points required, separately resolve the tracer issue before integration |
| A2 common grid / conditioning — OPEN | Proposed EPSG:6677 1m grid, retained Terrain/envelope and [Phase 5 plan](PHASE5_INTEGRATION_PLAN_v0.1_Draft.md) | Approve projected Building mapping/reference-ID policy; future fixtures must show same D_raw/D_eff/D0/ground in A/B/C | Select real Building geometry to determine assignments/halo, then validate the approved mapping; accepted geographic Adapter arrays are not automatically interchangeable |
| A3 selected Building identity / Z — OPEN | Historical A1/A3 scope, CLI/source diagnosis, present Terrain identities | Building source/release/license/bytes/manifests/IDs/LoD, matched Z evidence, selected ROI/halo membership; resolve selected-data implications or demonstrate an unaffected subset with review | First identify/reacquire source and Converter settings, then separately authorize regeneration and evidence checks. Missing files are a dependency, not reason to alter old acceptance |
| A4 state / collision / masks — OPEN | Present validity-state and retained CHM/DEM/bridge; Phase 4B factorized diagnostics | Approve source retention, positive-to-zero/rounded-loss/expansion accounting, Building-over-TREE modeling order, common observer mask and exclusion denominator | Preserve evidence before transformation; actual collision counts and paired geometry require later implementation, never infer absence from overwritten TREE |

Later Gate class B checks remain mandatory: actual common processed DEM and D0,
pre/post collision occupancy, Float32/rounding, common observer/mask parity and
mixed-scene halo sufficiency. Class C scientific/ecological deferrals apply only
within reviewed limited claims. No class A or B condition closes from this table.

## 8. Unknowns and prioritized next actions

Unknowns: exact historical PLATEAU release/archive/license/full file list and LoD;
Converter version/operation and source-to-Converter numerical history; old complete
111-building ID/geometry/hash inventory; availability outside the bounded search;
selected Building ROI/halo coverage; current live provider availability/terms;
mixed-scene halo needs, observer eligibility and collision counts; independent
canopy presence/assessment coverage and scientific height/registration/optical
accuracy. Current all-valid raster support does not resolve those questions.

| Priority / actor | Next action | Required outcome / boundary |
|---|---|---|
| P0 — User manual action | Locate historical release/archives/operator notes outside the bounded repository search, or identify an explicit new PLATEAU candidate; provide exact edition, files, URL and terms | Source identity and permission evidence before download; do not assume an old acceptance path is available |
| P0 — Design review / approval | Decide A1 interpretation, A2 common-grid/ground policy and A4 source/mask/overlap policy; review Building selection and Z-evidence plan | Recorded decisions, not automatic Gate closure; A3 remains OPEN until actual selected-data evidence is reviewed |
| P1 — User manual action, after acquisition authorization | Use the required Converter GUI with recorded version, license and all CRS/LoD/Z settings; preserve raw data and screenshots/receipts | Hash-bound source/Converter correspondence; manual conversion is not hidden in an OUEM CLI |
| P1 — Codex in a separately authorized next PR/run | Verify supplied/acquired source identities and terms evidence, inspect source/Converter matched coordinates, then use existing Native/Standard CLI in fresh directories | Full provenance/ID/geometry comparison and explicit unresolved Z results; no new transformation algorithm or guessed offset |
| P1 — Codex in a separately authorized next PR | Record selected Building inventory, exact ROI/halo membership and historical 111 comparison limits; validate existing runtime boundary | Evidence for A3 review, including UNKNOWN if old bytes cannot be recovered; no claim of historical equality from counts |
| P2 — Design review / approval | Close pre-start items only after evidence/decisions; authorize the limited Phase 5 implementation separately | Review raw/effective DEM, D0, shared masks/observers and model-ground interpretation |
| P2 — Codex after that authorization | Implement/test only the approved mixed-scene Adapter, audit collision/losses and halo, then A/B/C CPU direct comparisons | Later work, not part of this inventory; no scientific accuracy or Standard Canopy acceptance implied |

## 9. Validation and Documentation Impact

This task rechecked actual existence/sizes/SHA-256, selected manifest links,
source evidence integrity, ROI/halo masks/numeric validity and installed metadata.
Existing results were read, not rerun. No provider data were downloaded; no
GeoPackage/GeoTIFF/NPZ, source, test, Standard, Current State, acceptance record,
old manifest or experimental artifact was created/modified. Only new local
non-authoritative discovery/validation receipts and this Markdown were written.

Architecture/Standard and Implementation/Interface owners need no amendment:
contracts/behavior did not change. Verification adds this discovery record,
without extending acceptance or rewriting history. Current State and Gate need
no update because implementation status and pre-start decisions are unchanged.
Markdown links and one-file Git scope are checked for the Draft PR; Python tests
are not run for this documentation/read-only inventory. Independent review must
judge the next acquisition/reproduction authorization; this is not Phase 5 entry.
