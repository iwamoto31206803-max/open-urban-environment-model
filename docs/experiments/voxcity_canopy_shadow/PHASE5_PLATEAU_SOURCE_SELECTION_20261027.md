# Phase 5 PLATEAU Building source selection proposal — 2026-10-27

## 1. Executive Summary

**Selection proposal only; no Building data downloaded or processed.** Both
requested CKAN datasets exist. The 2023 dataset has **two CityGML editions, v3
and v4**, while 2025 lists v5. Year, specification edition, resource and actual
bytes must be pinned separately. The published 2025 API catalogue ZIP and CKAN
ZIP have the same filename but different URLs, HTTP ETags and modification times;
their byte identity is **UNVERIFIED**.

The Phase 5 ROI/initial halo lies in mesh **53393456**, not the historical input
filename's **53393465**. Official API metadata lists both 2025 files. For a new
Phase 5 baseline, propose **2025 / official API distribution / mesh 53393456**,
subject to the checks and approval below. For historical investigation, the API's
53393465 entry is the first directly corroborated filename/count candidate, not
an identified historical source. It lists 3,637 features, matching the old Native
count, but that does not prove release, feature identity, geometry or Z equality.
**Historical Identity = UNVERIFIED for both years and all editions.**

The 2023 file membership, real ROI roof geometry, source dates/vertical epoch,
Converter behavior, complete halo occluders and actual old 111-feature set remain
unverified. No A1–A4 condition closes; the approximately 37m difference remains an
unresolved hypothesis, never a correction.

## 2. Baseline, method and primary sources

Latest fetched main: `ac4a314c86e42cd7e8ab73273857a9773eb91c96`; GitHub confirms
PR #80 merged at that commit. Repository basis: [Data Readiness Inventory](PHASE5_DATA_READINESS_INVENTORY_20261027.md),
[Phase 5 DRAFT](PHASE5_INTEGRATION_PLAN_v0.1_Draft.md), [Building Current State](../../status/BUILDING_CURRENT_STATE.md),
[vertical diagnosis](../../research/OUEM_Komae_Building_Vertical_Geometry_Diagnosis.md),
[source-catalog proposal](../../planning/OUEM_Source_Catalog_and_Acquisition_Recipes_v0.1_Draft.md),
[A1](../../../experiments/a1_e2e_pilot/README.md) and [A3](../../acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md).

Checked **2026-10-27, approximately 16:23–16:30 JST**:

| Evidence ID / primary source | Access and meaning |
|---|---|
| S23: [2023 CKAN package_show](https://www.geospatial.jp/ckan/api/3/action/package_show?id=plateau-13219-komae-shi-2023) / [dataset page](https://www.geospatial.jp/ckan/dataset/plateau-13219-komae-shi-2023) | API HTTP 200, 16:25:58 JST; dataset/resource descriptions and published URLs |
| S25: [2025 CKAN package_show](https://www.geospatial.jp/ckan/api/3/action/package_show?id=plateau-13219-komae-shi-2025) / [dataset page](https://www.geospatial.jp/ckan/dataset/plateau-13219-komae-shi-2025) | API HTTP 200, 16:25:58 JST |
| SC: [official PLATEAU catalogue JSON](https://api.plateauview.mlit.go.jp/datacatalog/plateau-datasets) | HTTP 200, 16:26:04 JST; selected city_code=13219, year=2025, spec=5.0 |
| SF: [official Building filename-list JSON](https://api.plateauview.mlit.go.jp/datacatalog/citygml/13219?types=bldg) | HTTP 200, 16:27:06 JST; response explicitly identifies year=2025/spec=5.0 and per-file metadata, not 2023 |
| SD: [API field definitions](https://docs.plateauview.mlit.go.jp/api/rest/operations/datacatalogplateau-datasets/) / [CityGML service guidance](https://docs.plateauview.mlit.go.jp/datasets/citygml/) | Official documentation; service is experimental, catalogue and G-spatial assets can differ |
| SL: [PLATEAU site policy](https://www.mlit.go.jp/plateau/site-policy/) | Viewed through web tool; current section 3, not a frozen historical license |
| SN: [official filename guidance](https://www.mlit.go.jp/plateau/learning/tpc03-1/) / [coordinate/height guidance](https://www.mlit.go.jp/plateau/learning/tpc03-4/) | General filename and EPSG:6697/Tokyo Bay mean-sea-level explanation; not inspection of these files |
| SM: [Statistics Bureau mesh definition](https://www.stat.go.jp/data/mesh/m_tuite.htm) | Basis for geographic mesh calculation from supplied ROI coordinates |

Initial web requests to G-spatial failed (403/inaccessible); sandbox urllib
requests failed DNS resolution. Individually approved, metadata-only access
outside the sandbox succeeded for S23/S25/SC/SF. The local site-policy request
failed certificate verification; verification was not disabled, and the web tool
successfully retrieved SL. A search mirror was only a discovery lead; dataset
facts below use the successful primary API responses, not that mirror.

Only JSON metadata, web pages and **HEAD headers** were read. Four ZIP URLs
received HEAD requests at 16:29:15 JST, all HTTP 200, with **zero response-body
bytes read**; no redirects were followed. No ZIP/CityGML GET, range request,
archive listing, pack-generation API, Converter, ingest, Standard or solar run.
Local ignored metadata snapshots/access receipts and coordinate arithmetic are
under `data/work/phase5-plateau-source-selection/20261027-01/`; they are not
committed or formal acceptance evidence. Snapshot hashes are in section 11.

## 3. Komae 2023: two resource editions

S23 title: **3D都市モデル（Project PLATEAU）狛江市（2023年度）**;
package ID `8b52fadc-c0ca-43d2-865d-ec1e59e3db8c`, publishing organization
国土交通省 都市局. The CKAN `version` field is null. Its current notes describe
standard product specification **4.1**, while the older CityGML v3 resource is
still listed. Do not treat that dataset-level note as the edition of every resource.
Here v3/v4/v5 are PLATEAU product-specification resource labels, not proof of an
OGC CityGML language version; actual schema dependencies were not inspected.

- CityGML v3 is described as the 2023 data under product specification V3;
  filename `13219_komae-shi_city_2023_citygml_1_op.zip`.
- CityGML v4 is described as V3 data adapted to product specification V4;
  filename `13219_komae-shi_city_2023_citygml_2_op.zip`. Dataset notes say V4 was
  added on 2025-03-21. This is not proof of a new aerial survey or unchanged geometry.
- Both resource descriptions list Building **LOD0, LOD1, LOD2.0**, textures,
  metadata, source-material lists, schemas and extended specifications. Per-tile
  LoD counts, roof validity, exact survey dates and real coverage are UNKNOWN.
- Both are described as approximately 1.2GB. CKAN `size=null`, `hash=""` and
  `last_modified=null`; exact observed HEAD sizes/dates are separately below.
- Dataset metadata_created=`2024-03-13T09:59:53.096020`,
  metadata_modified=`2026-04-06T06:58:55.606119`. These are CKAN field strings,
  not survey dates or proof of object-byte changes; API timezone is not stated.

Neither S23 resource description enumerates individual GML files. Presence of
`53393465_bldg_6697_op.gml` or `53393456_bldg_6697_op.gml` inside either ZIP is
**UNVERIFIED**. Do not construct an individual-file URL by replacing a year or
asset UUID. The official API list obtained here resolves 2025 only.

## 4. Komae 2025: catalogue route versus CKAN route

S25 title: **3D都市モデル（Project PLATEAU）狛江市（2025年度）**;
package ID `faa6e15a-7223-4953-8ae9-130131d32dc6`, publishing organization
国土交通省 都市局, null CKAN `version`. Notes identify product specification
**5.0**; CityGML resource is v5, filename
`13219_komae-shi_pref_2025_citygml_1_op.zip`.
S25 lists LOD0/1/2.0 Buildings and associated metadata/specifications, not proof
that every ROI building has LOD2. Dataset metadata_created is
`2026-03-16T05:53:58.971269`, metadata_modified is
`2026-04-06T07:00:29.744696` (raw CKAN strings).

SC year/registration_year=2025, spec=5.0 points at a different CMS asset from the
CKAN resource; SF's per-file URLs belong to the **SC API asset**, not the CKAN
asset. SC advertises file_size=1,192,172,000 bytes, while HEAD of its actual object
reports **1,192,172,043**. Preserve both measurements and use actual received size
when acquisition is authorized; do not silently treat catalogue metadata
as an exact transfer count. No published SHA-256 was found in these responses.

### Exact published URLs and header observations

The links below are **published metadata URLs**, not guesses. They were checked
with HEAD only; none of their archive bodies were retrieved.

| Edition / resource ID | Published download URL | HEAD Content-Length / Last-Modified (UTC) |
|---|---|---|
| 2023 v3; `769f917d-b7e6-42bd-b5bf-29db91ff9495` | [13219_komae-shi_city_2023_citygml_1_op.zip](https://assets.cms.plateau.reearth.io/assets/ad/363cfd-b343-4306-9e74-d39996282eb0/13219_komae-shi_city_2023_citygml_1_op.zip) | 1,194,527,832 / Sat, 01 Feb 2025 01:22:38 GMT |
| 2023 v4; `3ad1779b-fef9-47de-b14d-51b6643d76b4` | [13219_komae-shi_city_2023_citygml_2_op.zip](https://assets.cms.plateau.reearth.io/assets/6b/96a5e5-6084-4555-8b51-aadc8695fdd0/13219_komae-shi_city_2023_citygml_2_op.zip) | 1,226,609,008 / Wed, 19 Mar 2025 10:06:25 GMT |
| 2025 v5 CKAN; `54aa690a-ffe8-4541-91be-86b4c214a3d5` | [13219_komae-shi_pref_2025_citygml_1_op.zip](https://assets.cms.plateau.reearth.io/assets/49/4cfcc7-5169-44ae-8f0a-c0fb9243673a/13219_komae-shi_pref_2025_citygml_1_op.zip) | 1,192,172,043 / Tue, 24 Mar 2026 06:39:56 GMT |
| 2025 v5 API catalogue | [13219_komae-shi_pref_2025_citygml_1_op.zip](https://assets.cms.plateau.reearth.io/assets/6c/9c8c10-16b2-4a21-b971-c9330d4c20f4/13219_komae-shi_pref_2025_citygml_1_op.zip) | 1,192,172,043 / Fri, 27 Mar 2026 01:29:32 GMT |

The v3/v4/v5 CKAN CityGML resource metadata_modified values respectively are
`2026-04-06T06:58:55.614656`, `2025-03-28T00:07:03.835248` and
`2026-03-24T07:31:16.407654`; all resource last_modified fields are null.
These differ from HTTP Last-Modified and must not be substituted for each other.
For 2025, CKAN object's ETag is `e9ab38a0a6007e0d08f2235ed5040cab`, API object's
ETag is `896e0706da7de84861976a3e39e31cd7`. Same size/name is insufficient;
ETag is not a declared SHA-256 or verified content identity. Archive equality,
member hashes and code-list equivalence remain UNVERIFIED.

### Published 2025 Building file metadata

SF lists 15 Building tiles. The two relevant entries are:

| API-listed file | Bytes / features | Published LOD counts | Scope of evidence |
|---|---|---|---|
| `53393456_bldg_6697_op.gml` | 238,819,640 / 4,021 | LOD0=4,021; LOD1=4,021; LOD2=4,021; LOD3/4=0; maxLod=2 | Primary tile for supplied Phase 5 ROI/halo; actual geometry not inspected |
| `53393465_bldg_6697_op.gml` | 210,083,285 / 3,637 | LOD0=3,637; LOD1=3,637; LOD2=3,609; LOD3/4=0; maxLod=2 | Historical-filename comparison candidate; not every feature has published LOD2 |

Direct published [53393456 GML URL](https://assets.cms.plateau.reearth.io/assets/6c/9c8c10-16b2-4a21-b971-c9330d4c20f4/13219_komae-shi_pref_2025_citygml_1_op/udx/bldg/53393456_bldg_6697_op.gml)
and [53393465 GML URL](https://assets.cms.plateau.reearth.io/assets/6c/9c8c10-16b2-4a21-b971-c9330d4c20f4/13219_komae-shi_pref_2025_citygml_1_op/udx/bldg/53393465_bldg_6697_op.gml)
were read **as JSON strings only**, not fetched. Their listing supports
availability in the API-distributed 2025 dataset; independent ZIP member listing
and inclusion in the different CKAN ZIP were not verified.

## 5. Historical A1/A3 correspondence and vertical meaning

The official [filename rule](https://www.mlit.go.jp/plateau/learning/tpc03-1/)
explains mesh / `bldg` / CRS / optional suffix / `op`. Eight-digit 53393465 is
consistent with a third-order mesh, `bldg` with Buildings, and `6697` with the
JGD2011 geographic + Tokyo Bay mean-sea-level height convention described by
[official coordinate guidance](https://www.mlit.go.jp/plateau/learning/tpc03-4/).
The filename does not encode release year, survey date, CRS axis order actually
written, Converter operation or per-building LoD. No specific file's srsName,
extended specification, vertical epoch or numeric Z was inspected.

| Historical question | 2023 v3/v4 | 2025 |
|---|---|---|
| Historical filename present? | UNVERIFIED; CKAN descriptions lack member lists | Official API lists exact filename in its 2025 asset; CKAN ZIP membership unverified |
| Native 3,637 connection | No per-file count obtained | API mesh 65 feature count equals 3,637; a corroborating clue, not identity proof |
| Standard 111 connection | UNVERIFIED | UNVERIFIED; actual AOI selection, source IDs/geometry and hashes not compared |
| Converter maximum LOD | Historical GUI instruction only; exact version/options unknown | Same uncertainty; published 3,609/3,637 LOD2 count shows why maximum LOD is not synonymous with all-LOD2 |
| Historical release / byte identity | UNVERIFIED | UNVERIFIED |

[A1 acceptance](../../../experiments/a1_e2e_pilot/README.md) retains 3,637 Native
and 111 Standard features within its input/AOI scope. [A3](../../acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md)
explicitly supplies paths and no input hashes. Repeated filename/counts do not
recover the old release, UUIDs, selected ID set or Converter settings. The 2025
edition being available before the recorded acceptance date also does not prove
it was used; conversely 2023 is not historical merely because its year is older.

[Standard Building](../../OUEM_Standard_Building_v0.1.md) retains T.P.-interpreted
Z through EPSG:4979 Native and horizontal-only Standard conversion to EPSG:6677.
[Native ingest](../../../src/ouem/native/building/plateau.py) and
[Standardizer](../../../src/ouem/standardize/building/__init__.py), with
[Native tests](../../../tests/test_plateau_building.py) and
[Standard tests](../../../tests/test_standard_building.py), establish downstream
behavior, not the external Converter's numerical operation. [Terrain](../../OUEM_Standard_Terrain_v0.1.md)
is source-declared T.P. Matching labels must be followed by actual metadata,
source epoch/height reference, corresponding full surfaces/LoD/vertices and
Converter-operation checks. Neither edition is independently vertically verified.
The roughly 37m [diagnosis](../../research/OUEM_Komae_Building_Vertical_Geometry_Diagnosis.md)
is unresolved; do not apply it as an offset or assume 2025 fixes it.

## 6. ROI / halo and tile selection

Provided EPSG:6677 bounds: ROI `[-23320,-40760,-23256,-40696]`, initial halo
`[-23352,-40792,-23224,-40664]`. Coordinate-only analysis used existing PyProj
3.7.2 with always_xy, EPSG:6677 -> EPSG:6668, sampling each projected edge at
129 points (516 samples per rectangle). No source geometry was transformed.

| Region | Derived JGD2011 longitude range | Derived latitude range | Mesh result |
|---|---|---|---|
| ROI | 139.5758550..139.5765635 | 35.6323340..35.6329123 | 53393456 |
| Halo | 139.5755008..139.5769177 | 35.6320448..35.6332015 | 53393456 |

Using the [Statistics Bureau mesh definition](https://www.stat.go.jp/data/mesh/m_tuite.htm),
mesh 53393456 spans longitude [139.575,139.5875), latitude [35.625,35.6333333).
Mesh 53393465 spans [139.5625,139.575), [35.6333333,35.6416667). This is a derived
geographic selection result, not verification of any file's contents. Both CKAN
spatial metadata boxes enclose the ROI/halo, but those city-level boxes do not
prove complete valid building coverage or roof geometry.

**Minimum primary tile candidate is 53393456.** 2025 API positively lists it with
LOD2 counts; 2023's corresponding tile is an expected *candidate name*, not a
verified archive member or guessed URL. Mesh 65 alone cannot demonstrate ROI/halo
completeness. Cross-boundary buildings may have full geometry extending outside
their nominal tile, so neither absence nor exact AOI feature count follows from
tile boxes. Inspect actual geometry/index/source coverage and any adjacent files
needed for crossing objects or larger shadow halo. Initial 32m halo sufficiency
remains open, especially after Building height and actual observer/sun are known.
The historical 111-feature set must not silently be used as complete Phase 5
coverage without that check.

## 7. Comparison and recommendations

| Axis | 2023 v3/v4 | 2025 v5 |
|---|---|---|
| Historical reproduction | Original V3 and V3-to-V4 adaptation are explicitly identified; actual old edition unknown | Filename and 3,637 metadata match available for mesh 65; byte/ID/Z identity still unverified |
| Acquisition | Two live HEAD-200 ZIP candidates; edition ambiguity must be resolved | CKAN and API HEAD-200 routes; freeze one because URL/ETag/date differ |
| LoD / geometry | Advertised LOD0/1/2.0; per-target tile counts/validity unknown | Per-tile counts published; primary mesh 56 lists all 4,021 with LOD2; actual quality/ROI subset unknown |
| Vertical validation | General EPSG:6697 convention is compatible in meaning; actual epoch/Z/Converter chain unknown | Same requirement; newer specification is no proof of better Z or matching Terrain epoch |
| License/source | CKAN points to current PLATEAU policy; keep per-release special notices | Same; rights and dependencies still need inspection after authorized acquisition |
| Phase 5 fit | Potential candidate if mesh 56/coverage/LoD can be confirmed; cannot claim readiness | Better metadata-backed new-input candidate for mesh 56; full geometry/provenance checks remain |
| Reproducibility / national reuse | Explicit old-edition comparison useful; two editions and missing hashes complicate identity | Official file-list metadata helps systematic mesh selection; experimental API/latest changes demand snapshots and pinned bytes, not universal compatibility |

**A — Historical first investigation candidate, not accepted reproduction:**
2025 **API-distributed mesh 65** is the first *directly corroborated* file to
compare because both filename and 3,637 count are publicly listed. That is an
investigation priority only, not evidence it produced A1/A3. The 2023 v3 and v4
remain competing candidates; operator records must decide historical edition.
If those records specify 2023, first inspect original v3 then the documented v4
adaptation, preserving both identities. No edition presently qualifies as an
identified historical replacement, and no claim that 2023 equals 2025 is made.

**B — First proposal for a new Phase 5 Building input:** 2025 v5, **API catalogue
asset rooted at `6c/9c8c10-16b2-4a21-b971-c9330d4c20f4`**, primary
`udx/bldg/53393456_bldg_6697_op.gml`. Prefer the pinned whole-city ZIP when later
authorized so required metadata/codelists/schemas/source lists remain available;
an individual GML alone is not the complete provenance package. This route is
proposed because its file-list evidence and bundle URL align, not because it is
proved scientifically newer/better or identical to the CKAN resource. New baseline
means new input identities and review, not automatic inheritance of 111 buildings.

**C — Before any download:** approve objective (historical investigation versus
new baseline), exact edition/route/URLs, approximately 1.2GB transfer and larger
uncompressed storage budget, source/terms capture, required companion files and
adjacent coverage, actual CRS/vertical/epoch verification and matched-Z plan,
Converter version/settings and new immutable Raw/work locations. Do not use
`latest` for a reproducibility run, and do not impose the old launcher's 3,637
expected count on mesh 56. API 4,021 is a future preflight comparison, not an
accepted Converter/Native count. A1–A4 remain OPEN.

## 8. Unverified items

No ZIP checksum, actual GML SHA-256, archive member inventory, 2023 tile LoD/count,
2023/2025 equality, old Converter settings, historical 111 IDs/geometries,
real ROI building completeness or roof surfaces, source survey dates, actual
srsName/axis/unit/vertical epoch, source-to-Converter Z preservation, 32m halo
sufficiency or Phase 5 A/B/C geometry was verified. CKAN hash fields are blank;
HTTP ETags and metadata snapshot hashes are not data hashes. The `op` suffix and
specification labels do not establish the right to ignore special/third-party
notices or prove no missing source content.

## 9. Concrete acquisition procedure proposal (not executed)

1. Review A/B/C above and record a selection decision with dataset, resource ID,
   product-spec edition, exact asset path and role. Recover old operator logs
   before asserting historical identity.
2. Re-read CKAN/API metadata and the license at acquisition time; save dated
   source receipts, direct URL and headers. Current policy covers G-spatial open
   3D models under PDL1.0 by default unless otherwise marked, requires source and
   modification attribution, and permits CC BY 4.0 use for covered content.
   Check special/third-party notices and applicable survey-use conditions; this
   is not a newly approved license determination for an unseen archive. A proposed
   attribution names the dataset, municipality/year/spec edition and source URL,
   and says OUEM processed it when applicable. See [SL](https://www.mlit.go.jp/plateau/site-policy/).
3. **Only after separate acquisition authorization**, download the selected ZIP
   to a new source/year/edition/asset-specific Raw directory using bounded transfer,
   timeout and no-overwrite handling; record actual size/SHA-256 and response
   headers. Do not reuse a mutable latest alias or merge different assets by name.
4. Validate ZIP integrity and safe paths; inventory exact GML members and companion
   metadata. Freeze actual hashes for mesh 56 and any required neighbors; retain
   mesh 65 separately for historical comparison if authorized. Parse full source
   metadata/srsName/Z/LoD/IDs before conversion and determine actual ROI coverage.
5. In a separate approved manual Converter step, capture version, all LoD and CRS/
   vertical settings and matched source/output coordinates. The source mesh 56
   count is not a reason to change the accepted contract or silently normalize Z.
6. Reuse existing Native/Standard CLI and runtime separation in the [runbook](../../../scripts/work/README.md)
   and PR #80 plan, with fresh output directories and reviewed counts. Preserve
   ID/geometry/Z and manifests; compare to old bytes if available. No 37m offset.
7. Submit selected source chain and vertical/coverage evidence to A3 review;
   complete the separate common-grid/ground, observer and mask decisions before
   any Phase 5 integration. Selection alone does not authorize execution.

## 10. Next actions

| Priority / actor | Action / decision boundary |
|---|---|
| P0 — Design review / requesting user | Choose the new 2025 API/mesh56 baseline proposal or request 2023 member investigation; distinguish that from historical reconstruction and approve no download implicitly |
| P0 — User historical evidence | Locate original release/ZIP hash, full 111 ID set and Converter screenshots/logs if recoverable; otherwise retain Historical Identity=UNVERIFIED |
| P1 — Codex, next separately authorized acquisition task | Pin selected metadata/license, acquire only approved inputs and companions, hash/inventory, verify coverage/LoD/CRS/Z before any generation |
| P1 — User / subsequent authorized conversion task | Record actual Converter operation and source/Converter matched geometry; use existing Native/Standard processing only after inputs and runtime are reviewed |
| P2 — Independent review | Assess A3 source identity and Z evidence, and A1/A2/A4 policies; this source proposal changes none of those gates |

## 11. Validation, evidence receipts and Documentation Impact

Repository code/interfaces and existing assertions were inspected, not executed.
No Python tests or new experiment; no Python/test/Standard/Current State/acceptance
or Gate file modified. This PR adds only this selection proposal. Local metadata
receipts are temporary evidence outside Git, not datasets or acceptance artifacts.
The four ZIP HEAD receipts explicitly record body_read_bytes=0.

| Local primary JSON snapshot | Bytes | SHA-256 (metadata only) |
|---|---:|---|
| `ckan_2023.json` | 226,965 | `c989c3ecf8a001b69aeee73b00c9bf7898cdfd348f7bb74dfd0392e6661e4d60` |
| `ckan_2025.json` | 198,622 | `db95d06205d61ce91b7caee0398794159717efafa7c38f8ff8246d70f4d7bfee` |
| `plateau_catalog.json` | 9,478,103 | `0eef73b8409635341689267d0e1847da4b593ea7a4f463d90850f18761c3aea8` |
| `citygml_file_list.json` | 5,294 | `f98840f37e21fc96281450a3ad9cdb3464199e5e0f7d1ef21453e47c4fcda8c0` |

Documentation Impact: Architecture/Standard and Implementation/Interface need no
amendment; this adds discovery/selection evidence only. Historical acceptance,
Current State and Gate need no update because implementation/acceptance/gate
state did not change. Markdown links, metadata-to-table values and one-file Git
scope are checked for the Draft PR. Independent review is required; no merge.
