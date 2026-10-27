# Phase 5 PLATEAU Raw acquisition and source verification — 2026-10-27

## 1. Result and scope

**Raw acquisition: PASS for the identified bytes and all-member CRC checks.**
**Direct-source verification: CONDITIONAL PASS within the checks below.** This
is a dated Experimental execution record, not Native/Standard acceptance, a
scientific accuracy guarantee or closure of any Phase 5 Gate.

The authorized 2025 v5 official API asset was acquired without substitution.
Primary mesh 53393456 and three relevant neighboring/historical meshes were
inspected directly. Source declaration/metadata supports EPSG:6697 and T.P.
semantics, and actual coordinates were read. LoD0 zero Z is kept separate from
LoD1/2 elevations. A neighboring mesh contributes an actual projected building
intersection to the initial halo. Converter preservation, full XSD/topology,
complete exterior occluder coverage, independent vertical accuracy and historical
input identity remain unverified.

## 2. Baseline, preflight and safety

Main `d8ca5965eca67bab4e07ca46f35c3da4ded31659`; PR #81 confirmed merged.
Basis: [Source Selection](PHASE5_PLATEAU_SOURCE_SELECTION_20261027.md),
[Data Readiness Inventory](PHASE5_DATA_READINESS_INVENTORY_20261027.md),
[Building Current State](../../status/BUILDING_CURRENT_STATE.md),
[Standard Building](../../OUEM_Standard_Building_v0.1.md),
[Phase 5 DRAFT](PHASE5_INTEGRATION_PLAN_v0.1_Draft.md) and
[Documentation Governance](../../OUEM_Documentation_Governance_v0.1.md).

Preflight re-read official CKAN/catalogue JSON and checked the exact fixed URL
with HEAD. Municipality/year/specification/asset matched the request. Content-Length
**1,192,172,043**, ETag `896e0706da7de84861976a3e39e31cd7`, and Last-Modified
**2026-03-27 01:29:32 GMT** matched PR #81. The catalogue's slightly different
size field is not an actual received-byte count. No CKAN alternate asset or
latest alias was requested as a fallback. Individually approved network commands
were used outside the DNS-restricted sandbox; no credentials/settings changed.

The destination did not exist. Recorded free space was **929,917,104,128 bytes**.
A conservative 24GiB planning budget covered ZIP, up to 16GiB total expanded
members, up to 2GiB selected extraction and headroom; actual sizes are below.
Limits: 45s socket timeout, 1,800s download deadline, 1.3GB download cap, maximum
2 attempts from byte zero, no automatic partial resume, no alternate URL.
Only one network transfer attempt was needed. Incomplete bytes used a hidden
`.part` name. The final ZIP was published only after size/hash/path/all-member
CRC validation, with closed handles and Windows same-volume no-replace rename;
its completion manifest was written last. Existing data were not overwritten.

## 3. Acquired ZIP, time and provenance

Fixed source:
[13219_komae-shi_pref_2025_citygml_1_op.zip](https://assets.cms.plateau.reearth.io/assets/6c/9c8c10-16b2-4a21-b971-c9330d4c20f4/13219_komae-shi_pref_2025_citygml_1_op.zip).
This receipt makes no claim of equality with the separate CKAN asset.

| Field | Actual result |
|---|---|
| Raw directory | `data/raw/building/plateau_komae/2025_v5_api/` |
| Filename | `13219_komae-shi_pref_2025_citygml_1_op.zip` |
| Received size | 1,192,172,043 bytes; matches response and requested preflight value |
| SHA-256 | `659fe9f96eb8a45b57e788b52d6e80edef154ddc3aa9b4f2c1ea117c61a5a555` |
| HTTP status | 200, fixed URL unchanged, no redirect |
| Transfer interval | 2026-10-27 16:53:55–17:02:02 JST; 487.391s |
| Raw completion | 2026-10-27 17:04:09 JST after local layout/CRC validation |
| Acquisition Manifest | `data/raw/building/plateau_komae/2025_v5_api/acquisition-manifest.json`, status COMPLETED |
| All ZIP entries / CRC | 22,889 entries, every entry CRC passed; path/duplicate-case/link/encryption/size checks passed |
| Total uncompressed members | 3,991,443,524 bytes; inventory only, not full extraction |

No general PLATEAU acquisition CLI/schema existed to reuse. Existing
[Terrain acquisition](../../../src/ouem/acquire/tokyo_tama_dem.py) and
[CHMv2 acquisition](../../../src/ouem/acquire/meta_chmv2.py) are provider-specific;
their schema names/acceptance rules were not relabelled for Building. The local
manifest reuses source/http/archive/limits/implementation/status conventions and
explicitly identifies itself as experimental execution evidence, not a new formal
schema. Input URL, times, response headers, source/license metadata and actual
ZIP identity are retained in it.

Acquisition orchestration used ignored local helpers, identified by SHA-256,
over the main commit above; their bytes are not claimed to be committed code.
Tracked worktree status was clean at acquisition start. Python was 3.11.9.
Source checks used existing NumPy, lxml, PyProj, Shapely and Rasterio in the ordinary
OUEM venv (2.4.6 / 6.1.3 / 3.7.2 / 2.2.0 / 1.4.4 respectively), keeping the GIS
runtime separate; the local `environment.json` records these versions. No existing production module or
test was changed; no Converter/Native/Standard/engine command was executed.

## 4. ZIP composition and selective extraction

The ZIP uses **root-level `udx/`**, not an enclosing package directory. Building
GML members are under `udx/bldg/`; all 15 are listed below. Other contents include
301 selected metadata/schema/codelist/specification/notice files (including
README, three metadata XMLs, original-source CSV, XSDs, codelists, PDF and XLSX
extended specifications). Other theme GMLs, textures and unrelated outputs were
not expanded. Appearance files were CRC-checked as ZIP entries, not rendered.

| Building GML member (prefix `udx/bldg/`) | Uncompressed bytes | CRC32 |
|---|---:|---|
| `53393445_bldg_6697_op.gml` | 1,293,993 | `b3cf94e1` |
| `53393446_bldg_6697_op.gml` | 82,082,226 | `e5724fb0` |
| `53393447_bldg_6697_op.gml` | 54,814,679 | `337344f0` |
| `53393455_bldg_6697_op.gml` | 83,731,855 | `0020a75f` |
| `53393456_bldg_6697_op.gml` | 238,819,640 | `3b0eac55` |
| `53393457_bldg_6697_op.gml` | 148,966,151 | `4f2d60ab` |
| `53393464_bldg_6697_op.gml` | 16,799,096 | `14113fcc` |
| `53393465_bldg_6697_op.gml` | 210,083,285 | `15c6d5cb` |
| `53393466_bldg_6697_op.gml` | 199,626,757 | `a28524dd` |
| `53393467_bldg_6697_op.gml` | 50,449,703 | `86cab098` |
| `53393475_bldg_6697_op.gml` | 142,391,506 | `3271c65e` |
| `53393476_bldg_6697_op.gml` | 194,744,459 | `294c1324` |
| `53393477_bldg_6697_op.gml` | 44,579,582 | `55bcf1c3` |
| `53393485_bldg_6697_op.gml` | 43,335,773 | `c84be28f` |
| `53393486_bldg_6697_op.gml` | 40,198,860 | `e8a56056` |

Only four Building GMLs and those 301 supporting files were extracted:
**305 files / 751,919,346 bytes** under the new work directory
`data/work/plateau-source-verification/komae-2025-v5-api-20261027-01/extracted/`.
Mesh 56 is primary; 65 supports historical comparison; 55 and 66 check nearby
boundaries. Targets were matched by validated path components, rejecting absolute,
parent-traversal, backslash/drive/device, duplicate/case-colliding, encrypted and
nonregular/link members. Destinations were checked to remain inside the new
extraction directory; exclusive temporary files were read through EOF for CRC,
closed, then renamed without replacement. No extractall was used. ZIP and every
selected file were rehashed unchanged after source inspection.

| Selected original GML | Bytes | CRC32 | SHA-256 |
|---|---:|---|---|
| `udx/bldg/53393456_bldg_6697_op.gml` | 238,819,640 | `3b0eac55` | `eaff3868a122e28e8c23810a45165675591ddfa72e1077a1948aa04bd0d89c30` |
| `udx/bldg/53393465_bldg_6697_op.gml` | 210,083,285 | `15c6d5cb` | `32f8912b2c3f8b09a2c76211b8ea22c9402f5b1357d36843dcfd5c93616ff613` |
| `udx/bldg/53393455_bldg_6697_op.gml` | 83,731,855 | `0020a75f` | `07245d14727d83c769a7809e3b135bf651ace6c3a18293b35c6a7ffe33b45b1f` |
| `udx/bldg/53393466_bldg_6697_op.gml` | 199,626,757 | `a28524dd` | `6128aa2a2bd637e51dbef89ee42bd54620eae6a2fab82b082149a4dc4924c0c9` |

## 5. XML, Building IDs, LoD and bounded geometry inspection

Streaming inspection retained one Building subtree at a time and released prior
siblings; full XML trees/all dataset vertices were not accumulated. Per-building
coordinate/node caps and per-file/extraction caps bounded the local audit.
Detailed per-feature summaries and future correspondence-point candidates stay
local, outside Git. Existing
[`_building_positions`](../../../src/ouem/komae_vertical_provenance.py) read
complete supported inline 3D coordinates with explicit unresolved-reference checks.

All four selected files are XML-well-formed and all **12,847** Building elements
have supported finite coordinate readings. Building IDs are non-null and unique
within and across these four files; per-Building internal duplicate-ID checks
found none. This is not a global all-XML-ID or full XSD/topological validity claim.
No XML external entities/network schemas were resolved. Full schema validation,
solid closure, self-intersection and rendering acceptance were not performed.

| Mesh | Building count | LOD0 property | LOD1 property | LOD2 property | ROI / halo bbox candidates |
|---|---:|---:|---:|---:|---|
| 53393456 | 4,021 | 4,021 | 4,021 | 4,021 | 7 / 42 |
| 53393465 | 3,637 | 3,637 | 3,637 | 3,609 | 0 / 0 |
| 53393455 | 1,411 | 1,411 | 1,411 | 1,411 | 0 / 0 |
| 53393466 | 3,778 | 3,778 | 3,778 | 3,291 | 0 / 1 |

Counts refer to actual `bldg:Building` elements and LoD property presence, not
accepted Converter feature counts or independent roof-quality validation. No
LOD3/4 properties were found. For primary 56 the counts match the published API's
4,021; all 4,021 also contain inline LoD0/1/2 coordinates. Readable primary
RoofSurface count is **21,036**; roof-coordinate Z spans **19.198599..56.229689m**.
CityGML namespaces actually identify **CityGML 2.0** and `uro/3.2`; product-spec
v5 is a different version dimension and was not mistaken for CityGML 5.0.

## 6. CRS, axes, Z distribution and vertical evidence

Every inspected source CRS declaration was
`http://www.opengis.net/def/crs/EPSG/0/6697`; declared dimensions were 3.
There were no XML axisLabels/uomLabels in the inspected files. The declared
EPSG definition supplies latitude (north, degrees), longitude (east, degrees),
and gravity-related height (up, metres); source tuples/envelope numeric ranges
are consistent with that order. Source metadata explicitly includes
`JGD2011, TP / (B, L), H` alongside its 2D reference. This is declared vertical
semantics, not an independent accuracy/epoch verification.

The read-only horizontal comparisons used longitude/latitude order with explicit
XY transformation into EPSG:6677; source Z was never transformed or offset.
The initial primary envelope is latitude/longitude/Z, including min Z=0;
zeros must not be mistaken for surveyed ground elevations:

| Primary inline coordinate class | Vertices | Z range (m) | Zero Z |
|---|---:|---|---:|
| LOD0 | 59,074 | 0..0 | 59,074 |
| LOD1 | 393,393 | 17.865949..49.536940 | 0 |
| LOD2 | 781,957 | 17.865949..56.229689 | 0 |

LoD0 all-zero geometry is an observed source representation; it was not filled,
removed or promoted to physical ground truth. Future Converter LoD selection and
Z correspondence must be explicit. Mixing all LoDs when reporting minimum Z
would hide this distinction. No nonfinite supported geometry coordinates or
geometry -9999 sentinels were found by these checks.

Primary per-Building maximum absolute Z: median **27.815400m**, p95 **32.171290m**,
p99 **37.841606m**, maximum **56.229689m**. These are source elevation distributions,
not building heights above ground or universal outlier thresholds. Extreme-tail
IDs/coordinates were retained; the maximum belongs to
`bldg_15d00a00-e20b-47b7-8d1d-59538a9d5e7a`, outside the initial halo. No extreme
value was silently rejected, corrected or accepted as scientifically accurate.

For 43 halo-bbox candidates, the lowest available LoD2 vertex was compared with
nearest accepted Terrain at that vertex's XY. All 43 samples were usable; the
source-vertex-minus-DEM range is **-0.485584..0.078550m**, median **-0.097710m**.
Terrain hash remained
`0afb6d1706b97bd39c8c93ff8feb580094fe585f567e2de1f2081c082602f90a`.
This is a numerical diagnostic, not proof the vertex is bare-earth, independent
survey accuracy, datum-epoch identity, or a source-to-Converter test. Neither
source's declaration nor numeric proximity upgrades Terrain's source-declared T.P.

The bundled source CSV identifies Building LoD0/1/2/measuredHeight material from
2022 Komae-area photogrammetry, and also lists a 2025 Tokyo/Midmap source with
2022 photography for LoD2. These are broad material-lineage rows, not exact
per-Building acquisition times. README is dated 2026-03-13; metadata describes
R5 specification 3.4, upgrade to 4.1, and R7 updates. Package year 2025 is not
proof of a 2025 observation at every building. Metadata/template dates and
feature-level provenance need further review before temporal/accuracy claims.

### Historical diagnostic target and future Converter correspondence

Acquired mesh 65 contains
`bldg_5f2d3f6c-63de-42a1-8c63-5a4fa79c0239`, measuredHeight=4.4m:

| Actual source LoD | Z range (m) |
|---|---|
| 0 | 0..0 |
| 1 | 24.441737..27.841737 |
| 2 | 24.441737..28.842700 |

A retained LoD2 minimum point in source axis order is
`(35.63410200036968, 139.57296304805652, 24.441737)`; a maximum point is
`(35.634058020618134, 139.57296984178961, 28.842700)`.
These and per-feature samples provide candidates for future matched-coordinate
inspection, with surface/LoD correspondence still required. Same ID, filename and
measuredHeight do not prove this ZIP equals the old A1/A3 input. No old Converter,
Native or Standard bytes were compared. The [approximately 37m diagnosis](../../research/OUEM_Komae_Building_Vertical_Geometry_Diagnosis.md)
remains **UNRESOLVED**; no offset or measuredHeight substitution was applied.

## 7. ROI / initial halo: bbox screening and source-polygon projection

Profiles remain EPSG:6677, ROI `[-23320,-40760,-23256,-40696]`, halo
`[-23352,-40792,-23224,-40664]`. Bbox screening is conservative and is **not**
reported as complete footprint coverage. Its 43 halo candidates were additionally
checked in memory using the highest available LoD with positive-area inline
source polygon projections, preserving interiors. Vertical zero-XY-area surfaces
were omitted from the projection diagnostic, not repaired or changed in the
source. All 43 candidates were checked without invalid positive-area polygon
repair. No GeoPackage, canonical footprint, raster, voxel or model artifact was
produced by this diagnostic.

| Scope | Bbox candidates | Positive-area source-projection intersections | Crossing scope boundary |
|---|---:|---:|---:|
| ROI | 7 | 6 (all mesh 56) | 2 |
| Initial halo | 43 | 41 (40 mesh 56 + 1 mesh 66) | 16 |

The mesh 66 contributor is
`bldg_aa680eae-dbbd-426c-9d7a-1f5efaaab316`, projected extent approximately
`[-23266.968281,-40669.615315,-23238.339257,-40624.997843]`, with **35.387680m²**
positive-area overlap into the initial halo. Thus **mesh 56 alone is insufficient
for even this initial domain**. Meshes 55/65 provided no bbox candidates here.
Retain whole crossing geometries for later policy review; do not clip them into
accepted Standard artifacts in this task.

These counts are geometry diagnostics on four source tiles, not an accepted
Building occupancy grid or all-city completeness test. Eleven other Building
GMLs were inventoried/CRC-checked but not geometry-parsed. Unknown exterior
occluders and actual selected roof heights/sun/observer geometry require renewed
halo analysis; **32m sufficiency is not established**. No assumption of no
buildings outside these counts, new common-grid mapping or A/B/C comparability.

## 8. Metadata, rights and evidence limitations

Included README explicitly offers government standard terms 2.0, CC BY 4.0,
ODC BY and ODbL as alternatives. CC BY 4.0 is the documented basis retained for
this source verification; the [current PLATEAU policy](https://www.mlit.go.jp/plateau/site-policy/)
references PDL1.0 and permits CC BY use for covered content. No material
contradiction preventing this Raw acquisition was found. Preserve attribution
to PLATEAU, Tokyo/Komae dataset year/specification and the exact source URL;
state any subsequent processing separately, without implying provider approval.
Special source/third-party and survey-use restrictions still require attention
for later uses. No global license/accuracy acceptance is conferred by this check.

The README's original-source CSV link omits `_op`, while the actual member is
`metadata/udx_13219_2025_resource_op.csv`. This documentation discrepancy is
recorded; provider bytes were not edited. Source material CSV, 3 metadata XMLs,
codelists, XSDs and extended specification PDF/XLSX were preserved by exact member
hash. The extended specification PDF/XLSX were not fully interpreted, external
schemas/code lists were not fetched, and no full XSD/3D validity test was performed.
The README's municipal aggregate coverage/count declarations were not independently
validated against a municipal boundary or all 15 Building tiles.

## 9. Execution notes and evidence locations

Local evidence root:
`data/work/plateau-source-verification/komae-2025-v5-api-20261027-01/`.
Paths are workstation/run identifiers, not portable downloads or formal inputs.

- `preflight.json`, acquisition metadata snapshots, `zip-member-inventory.json`:
  identification, transfer/storage limits, complete member paths/sizes/CRCs.
- `selected-extraction.json`: exact selected member-to-file hashes.
- `source-verification.json`, four `*-feature-summaries.json` files:
  streaming XML/ID/LoD/coordinate/roof/bbox checks and correspondence candidates.
- `source-spatial-lod-check-v2.json`: final positive-area geometry and per-LoD /
  Terrain diagnostic; `historical-target-source-check.json`: target source sample.
- `source-metadata-review.json`, `source-verification-manifest.json`:
  rights/source dates and hash-linked final checks; status is
  SOURCE_CHECKS_COMPLETED_WITH_LIMITS, not Standard acceptance.
- `execution-notes.json`: retained local-helper failures and corrected continuations.

The initial acquisition helper incorrectly required a leading package folder and
stopped before CRC/publication. Its FAILED record remains intact; the fully received
bytes were reverified locally with root-relative matching, then passed all CRCs
and publication without a second network transfer. The first XML iterator helper
also stopped while deleting the active member; a separate continuation used safe
previous-sibling cleanup, with an independent simple parse confirming all 4,021
primary Buildings. The first standalone-ring diagnostic lacked inherited dimension
context; it was retained as unverified, then superseded by the explicitly
ancestor-aware final projection check. These are local execution-helper issues,
not evidence that source bytes were repaired or the failed diagnostics passed.
All helper versions/receipts remain local and distinguish committed code from
ignored execution scripts. No existing formal record was overwritten.

### Hash-linked evidence (local artifacts, not committed)

| Evidence | SHA-256 |
|---|---|
| `acquisition-manifest.json` | `4322fbce9d084acdd51a5995a758df5426658d2fe6c498345f7220bd7e2f019d` |
| `zip-member-inventory.json` | `7b130a51ee1753d059fd7d0338ebd56dab3ab7878ca11309d510bcbfabff2d19` |
| `selected-extraction.json` | `5e5539757eea49db5d73ccba439341f0ab52482435a524e73d0d8ac7b279d7a5` |
| `source-verification.json` | `625c662dc0c974a8ed4dce3293a2057bbe66d30a10f4dd3d5b43712593dfa76c` |
| `source-spatial-lod-check-v2.json` | `7ca776fd34ed235f97b1a6bf3d444d6533da6916aa45bbb5bd5ddf8c15fe9891` |
| `source-verification-manifest.json` | `1a1362d8f0194c77da8cd87e78440d3109b3dce6471d3636ea21fa5ea3f3fcf1` |
| `source-metadata-review.json` | `743c75067478e3170df0290e195c2ad4ffe8aebf69a0dae4ddf25c5e83f2e5df` |
| `historical-target-source-check.json` | `78fc2ffa5f36000635d6784b989746a3c83621cd2eac616f37ba6b0629fcfc80` |
| `execution-notes.json` | `c2e5c393b1e18b0ccd48493c71753886e28effe60bb3e07533fbaa3068e70f4e` |

## 10. Next steps, Gate and Documentation Impact

1. Independently review this exact ZIP/source identity, bounded coverage evidence
   and remaining source/vertical/rights limitations. Keep historical identity
   UNVERIFIED and source-to-Converter preservation NOT CHECKED.
2. Before any future Converter run, authorize and record version, actual LoD /
   CRS/vertical settings, selected mesh set including mesh 66 and matched source
   surfaces/coordinates. Retain the original source bundle and separate outputs.
3. Later use the existing Native/Standard workflow only after that approval;
   compare chosen source and output IDs/coordinates and actual heights. Do not
   apply the old 3,637 expectation to mesh 56 or infer 111-building equivalence.
4. Complete the separate [Phase 5 pre-start review](PHASE4_COMPLETION_GATE_REVIEW_20261027.md)
   and common-ground/grid/observer/mask decisions. All A1–A4 remain OPEN, including
   A3; Raw identity plus source inspection alone does not close the full chain.

This task added no reusable Python implementation/tests, and did not run pytest.
It executed source-specific local acquisition/verification checks only. The final
integrity checks confirm ZIP identity, all CRCs, 305 selected file hashes, source
reader identities/LoD counts and the unchanged Terrain diagnostic input. Markdown
links and one-document Git scope are checked for the Draft PR; no Raw/expanded
files, local helpers or manifests are committed.

Documentation Impact: Verification adds this bounded experimental record.
Architecture/Standard and Implementation/Interface remain unchanged. Current State
is intentionally preserved under the task constraint: its dated historical path
checks are not rewritten to assert new Native/Standard availability. This record
identifies the newly available Raw bytes; no Gate or acceptance state changes.
No Converter, Native/Standard Building, VoxCity Adapter, Phase 5 implementation or
solar analysis was executed. Draft PR; independent review required, no merge.
