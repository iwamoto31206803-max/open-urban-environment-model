# OUEM Data Pipeline Generalization Audit v0.1 — Phase 1

Audit date: **2026-10-30**. Inspected current main:
**`2a0170da13c17f552e2c67cd99748e153ede9c1d`** (PR #129 merged).
Status: **read-only architectural/implementation audit and recommendations**.
Only this document is added. No implementation, acquisition, conversion,
simulation, dependency, contract, Acceptance or backlog-state change is made.
Line references below refer to this baseline; future source edits can move them.

## 1. Executive Summary

OUEM has working, bounded upstream components, rather than a municipality-neutral
acquisition-to-Standard product. Existing CLIs can be used without Codex for their
documented inputs. A new municipality cannot in general be supported by changing
the study-area YAML: source selection, coordinate profiles, semantic evidence,
and downstream compatibility must also be established.

The principal geographic barriers are **EPSG:6677-only Standardization/execution
profiles**, fixed DEM tile identity, fixed Building member selection in the
real-data Source-H runner, and incomplete portable source-selection/preflight
tooling. Rectangular AOIs and prepared local inputs are common prerequisites.
Komae filenames in examples are not themselves all hard-coded limitations.

The principal source barriers are **source-specific coordinate/height profiles
and evidence schemas**, not GeoPackage/GeoTIFF readability. Building's legacy
EPSG:4979-labelled/T.P.-claimed route and experimental EPSG:6697 Source-H route
must remain separate. Terrain registration is structurally reusable but does not
constitute universal DEM semantic validation. Height Envelope explicitly requires
a CHMv2 lineage bridge and accepted Terrain bytes; LiDAR-derived CHM is not an
already supported replacement. Native/Standard Canopy remain unimplemented.

| Dimension | Building | Terrain | Canopy |
|---|---|---|---|
| Acquisition | Manual Converter route; dated 2025 PLATEAU acquisition evidence, no tracked general downloader | Implemented downloader for exactly Tama `09LD3451` | Implemented Meta CHMv2 index/COG acquisition and native-grid AOI crop |
| Native | Legacy Converter GPKG ingest; separate Source-H provenance/geometry-preserving ingest | Manifest registration of original raster, no redundant raster copy | Namespace only; acquisition crop is not Native |
| Standardizer | Legacy v0.1 and separate experimental Source-H implementation | v0.1 NoData normalization, grid/valid values retained | No full Standardizer; experimental Height Envelope precursor only |
| Contract / evidence maturity | Standard v0.1 **PROVISIONAL**, bounded Komae local acceptance; Source-H tested/executed **experimental**, eligibility NOT_ESTABLISHED | Standard v0.1 **PROVISIONAL**, original Komae A2 accepted; later reproducibility record is technical, review pending | Standard Canopy **DRAFT**; acquisition/Envelope have synthetic and bounded real execution evidence, no full Canopy acceptance |
| Configurable today | Paths/layer/AOI; Source-H low-level plan/artifact locators | Provider/dataset/vertical declarations and input/output locators; compliant raster dimensions/pixel size | Acquisition AOI/limits/offline files; Envelope explicit aligned resolution/CR and input evidence |
| Main boundary | Fixed coordinate/attribute profile; runner fixes two members | Fixed downloader; Standard requires EPSG:6677/Float32/north-up | CHMv2-only source gate; Envelope output grid EPSG:6677; missing polygons/coverage/presence lifecycle |

Use the [Concept v0.2](../OUEM_Concept_Architecture_v0.2.md) for intended boundaries,
the actual Standards for current contracts, and dated execution/acceptance records
for evidence. The [Phase A design](../Phase_A_Implementation_Design_v0.1.md) has an
explicit historical current-status note. Conceptual A1/A2/A3 profiles do not mean
the same things as implementation/acceptance stage A1 Building, A2 Terrain,
A3 Adapter. Neither set of labels establishes nationwide implementation.

## 2. Current Pipeline Map

```text
Building, accepted bounded v0.1 lane:
  acquired PLATEAU CityGML -> manual Converter GUI -> work 3D GPKG
  -> Native GPKG + ingest manifest/receipt -> Standard GPKG + manifest

Building, separate experimental Source-H lane:
  retained 2025 ZIP -> fixed two-member extraction + codelists -> fixed Converter CLI
  -> Source-H plan/Native GPKG + manifest/receipt
  -> Source-H Standard GPKG + manifest/receipt -> independent Consumer

Terrain:
  fixed Tama ZIP downloader -> original Raw ZIP/TIFF + acquisition manifest
  OR explicitly supplied local DEM -> Native JSON registration -> Standard TIFF/manifest
  [acquisition evidence is not automatically validated end-to-end by the local helper]

Canopy, implemented partial experiment:
  Meta CHMv2 index/COGs -> Raw originals + work AOI crop/acquisition record
  + reviewed HAG evidence/snapshot + accepted Standard Terrain/evidence
  -> Height Envelope top-Z/bottom-Z/height-validity rasters + PoC manifest

Canopy, proposed full lifecycle:
  source-specific Native (including CHM/polygons/coverage) -> Standard Canopy
  -> engine Adapter                                     [not implemented as a full path]
```

### Entry points and execution dependencies

| Stage | Actual callable entry / arguments | Runtime and owner |
|---|---|---|
| Legacy Building Native | Console `ouem-plateau-buildings` or `-m ouem.native.building.plateau`: source GPKG, `--output`, `--gis-runtime`; optional `--source-layer`, `--expected-count`, `--force` | OUEM parent, standalone OGR GIS child; [plateau.py](../../src/ouem/native/building/plateau.py#L227), `_parser` L298 |
| Legacy Building Standard | `ouem-standardize-buildings` / `-m ouem.standardize.building`: source GPKG, `--output`, `--study-area`, `--gis-runtime`, optional layer | OUEM parent + separate GIS worker; [Standardizer](../../src/ouem/standardize/building/__init__.py#L102) |
| Source-H Native | Python API `ingest_source_h(record, artifact_root=...)`; no standalone Native CLI in that module | Ordinary OUEM Python; [ingestion](../../src/ouem/native/building/source_h.py#L50), provenance plan and SQLite/geometry readers |
| Source-H Standard | `-m ouem.standardize.building.source_h`: `--profile`, `--native-manifest`, `--artifact-root`, `--output`, `--study-area` | Ordinary OUEM Python/PyProj; [main](../../src/ouem/standardize/building/source_h.py#L201) |
| Source-H real-data orchestration | `-m ouem.real_komae_source_h`: `--artifact-root`, `--run-dir`, `--zip`, `--converter`, `--terrain`, `--study-area` | Ordinary OUEM Python + previously fixed external `nusamai.exe`; [run](../../src/ouem/real_komae_source_h.py#L81) |
| Terrain acquisition | `-m ouem.acquire.tokyo_tama_dem`: `--raw-dir`, optional timeout/byte limit | OUEM Rasterio/stdlib HTTPS/ZIP; [acquire](../../src/ouem/acquire/tokyo_tama_dem.py#L148) |
| Terrain Native | `ouem-accept-terrain` / `-m ouem.native.terrain`: source TIFF, `--output`, `--provider`, `--source-dataset`, explicit vertical options | OUEM NumPy/Rasterio; [accept_native_terrain](../../src/ouem/native/terrain/__init__.py#L110) |
| Terrain Standard | `ouem-standardize-terrain` / `-m ouem.standardize.terrain`: Native JSON, `--output`, `--study-area` | OUEM NumPy/Rasterio; [standardize_native_terrain](../../src/ouem/standardize/terrain/__init__.py#L78) |
| CHMv2 acquisition | `-m ouem.acquire.meta_chmv2`: `--study-area`, new `--raw-dir` / `--work-dir`; optional local index/tiles and limits | OUEM NumPy/Rasterio/Shapely + stdlib HTTPS; [acquire](../../src/ouem/acquire/meta_chmv2.py#L264) |
| Height Envelope | `-m ouem.height_envelope`: CHM, acquisition record, evidence, Terrain, Terrain manifest/acceptance, study area, new output directory; optional CR/resolution/nearest DEM sampling | OUEM NumPy/Rasterio/PyProj; [main](../../src/ouem/height_envelope.py#L366) |

The five console scripts in [pyproject](../../pyproject.toml) include the separate
VoxCity Adapter, not acquisition/Envelope/Source-H orchestration aliases. Module
CLIs above are real interfaces, not missing merely because they lack aliases.
Legacy Windows launchers and [work runbook](../../scripts/work/README.md) provide
additional operational paths. No CLI, including `--help`, was executed here.

## 3. Building Assessment

### Implemented paths, outputs and acceptance

Legacy Native ingestion copies the Converter's 3D MultiPolygon layer without
reprojection, clipping or dimensional reduction. `_resolve_layer`, `_validate_layer`
and `_require_3d_multipolygon` in the [OGR worker](../../src/ouem/native/building/_plateau_gdal_worker.py#L14)
require an unambiguous building layer (or explicit selection), defined CRS,
nonempty 3D geometry and `measuredHeight`. Native output is a `building` layer
plus `ouem-plateau-native-ingest/v0.1` manifest and
`ouem-plateau-native-receipt/v0.1`. These checks establish structural suitability,
not original-source vertical truth.

The [v0.1 Standard contract](../OUEM_Standard_Building_v0.1.md) is conceptually
provider-independent, but its implemented PLATEAU mapping is narrow:
`id` -> `source_id`, constant dataset `PLATEAU CityGML`, deterministic UUIDv5
`ouem_id`, nullable LoD and measured height. The
[worker](../../src/ouem/standardize/building/_gdal_worker.py#L105) requires Native
EPSG:4979, transforms its EPSG:4326 horizontal component to 6677, restores every
numeric Z, selects whole intersecting buildings and reopens the written GPKG
to verify IDs/3D/Z. It writes `ouem-standard-building-manifest/v0.1`.
Numeric Z retention is not proof that upstream Converter Z is T.P.

[A1 pilot acceptance](../../experiments/a1_e2e_pilot/README.md) records 3,637
Native -> 111 Standard buildings and zero maximum Z difference. The separate
[A3 acceptance](../acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md) covers
the recorded downstream integration, not all Building providers. Contract remains
PROVISIONAL. Direct generic GDAL CityGML conversion is not the accepted replacement:
the pilot records empty PolyhedralSurface results; the later
[GDAL feasibility audit](../experiments/plateau_converter/GDAL_ALTERNATIVE_FEASIBILITY_20261027.md)
is separate bounded evidence, not a new accepted ingest path.

Source-H is implemented separately, not a fix retroactively applied to v0.1.
[Provenance foundation](../../src/ouem/native/building/provenance.py#L19) dispatches
exact profile `ouem-native-building/plateau-source-h/v0.1`, Native manifest v0.2,
Converter receipt, artifact hashes and explicit compound 6697 / horizontal 6668 /
vertical 6695 gravity-related H declarations. `ingest_source_h` independently
checks Raw/Converter LoD2 correspondence and preserves actual geometry BLOBs.
[Source-H Standardization](../../src/ouem/standardize/building/source_h.py#L97)
uses horizontal-only 6668 -> 6677 with H unchanged, whole-feature intersection,
Standard manifest/receipt v0.2, then a separately implemented Consumer.

[Real Source-H results](../experiments/real_komae_source_h/RESULTS.md) record 7,312
Converter/Native buildings -> 173 Standard, 487 source no-LoD2 exclusions, and
exact retained H. This differs from the accepted 111-building source. It is
**executed/tested experimental functionality**, eligibility NOT_ESTABLISHED and
Formal Acceptance NOT_VERIFIED, not an accepted v0.2 replacement.

### Geographic and source limitations

- **Actual code limits:** legacy `standardize_native_buildings` L118 and
  Source-H `standardize_source_h` L118 reject study-area CRS other than 6677.
  [real_komae_source_h](../../src/ouem/real_komae_source_h.py#L24) fixes binary SHA
  and the two members `53393456` / `53393466`; `run` requires exactly those two.
  Changing ZIP path or YAML cannot select another municipality's meshes.
- **Configurable rather than fixed:** low-level legacy paths, layer and AOI bounds;
  optional expected count; Source-H artifact plan/root/output and study-area
  locators. Native legacy accepts a defined CRS structurally, but Standard does
  not support every CRS that Native can retain. No nationwide success is implied.
- **Launcher-specific:** [plateau_komae_local_acceptance.cmd](../../scripts/work/plateau_komae_local_acceptance.cmd)
  fixes Komae output paths/YAML/runtime-snapshot name and 3,637 expected input
  features, even when its Converter path is supplied. That count is not a core
  `ingest_converter_geopackage` requirement. Contained PoC's
  [92 selected / 19 excluded](../../src/ouem/komae_contained.py#L8) is another
  actual execution constraint, not the general whole-intersection selector.
- **Source-specific:** [read_lod2](../../src/ouem/native/building/source_h_lod2.py#L29)
  supports bounded CityGML 2, explicit 6697, latitude/longitude/H, inline 3D rings
  and a restricted internal LoD2 Solid xlink correspondence. BuildingPart,
  external/cross-building references, other representations and members >256 MiB
  fail rather than being silently repaired. This is not a general CityGML reader.
- **Alternative sources:** a source already satisfying the exact legacy GPKG
  profile can enter low-level ingest, subject to genuine source evidence. LoD1,
  footprints plus height, CityJSON, other coordinate/vertical profiles or LiDAR
  roof surfaces have no demonstrated general Native-to-Standard mapping here.
  Relabelling a file as PLATEAU/4979/6697 is not a valid adapter.
- **Identity:** UUID rules bind the dataset literal and source feature ID, not
  automatically municipality/release/mesh identity. Whether every future source
  keeps globally unique/stable IDs is Unknown; assess collisions/version meaning
  before widening source dispatch. Do not change existing IDs to solve a future case.

### Operations and missing stages

A trained user can run documented legacy commands without editing Python, after
manual acquisition/GUI conversion and GIS snapshot preparation. The
[2025 Raw acquisition record](../experiments/voxcity_canopy_shadow/PHASE5_PLATEAU_ACQUISITION_20261027.md)
documents actual ZIP acquisition, license/source inspection and CRC checks using
ignored local helpers; it does not supply a tracked general PLATEAU downloader.
Older acquisition inventories' missing-source claims describe their older dates.
The [Source-H procedure](../experiments/real_komae_source_h/README.md) provides a
fixed-binary CLI, but new member selection still needs source edits in that runner
or manually authored calls/plans around the lower-level APIs. Converter availability
and its build identity are external prerequisites, not installed by pyproject.

Legacy ingest reuses matching source receipts only after actual source/output
comparison; a nonmatching receipt or `--force` enters the worker's replacement
path. Legacy Standard worker also deletes an existing output before creating it.
Terrain-style fresh-run safety must not be assumed for these APIs. Expected-count
failure can occur after Native output/manifest creation. The legacy Standardizer
reads the GPKG directly, not an enforced complete Raw/Converter/Native hash chain.
Use explicit fresh destinations and preserve old records; these are observed
operational limits, not evidence that an accepted artifact is currently corrupt.
Source-H instead uses confined artifact locators, new child directories, closed
staging files, no-clobber hard-link publication and completion receipts, with
rollback/error reporting. It retains Raw, Converter and provenance requirements.

Relevant existing tests inspected, not run: [legacy Native](../../tests/test_plateau_building.py),
[legacy Standard](../../tests/test_standard_building.py),
[Source-H ingestion](../../tests/test_source_h_ingestion.py),
[Source-H Standard](../../tests/test_source_h_standard.py),
[xlinks](../../tests/test_source_h_xlink.py), [real-run orchestration](../../tests/test_real_komae_source_h.py).
Mocked worker contracts and synthetic geometry tests do not establish other-city
OGR/Converter success or general source coverage.

## 4. Terrain Assessment

### Stages, contracts and outputs

[tokyo_tama_dem](../../src/ouem/acquire/tokyo_tama_dem.py#L24) fixes provider,
one HTTPS URL, root ZIP member, original TIFF SHA and tile metadata.
`validate_original` L130 requires 800x600, 0.5 m, bounds
`[-23600,-40800,-23200,-40500]`, EPSG:6677, Float32, one band, identity scale/offset
and 480,000 valid cells. This is a deliberate original-retrieval recipe, not a
generic DEM downloader. URL/tile/hash cannot be overridden by arguments.
It publishes original ZIP/TIFF plus `ouem-tokyo-tama-dem-acquisition-poc/v0.1`
acquisition manifest, using new directories and bounded transfer/extraction.
TIFF identity is mandatory; ZIP repacking can be recorded without identical ZIP SHA.

[Native Terrain](../../src/ouem/native/terrain/__init__.py#L54) accepts an explicitly
provided single-band, north-up/unrotated GeoTIFF with unambiguous horizontal EPSG,
finite declared NoData and finite nonempty valid samples. It writes
`ouem-native-terrain-manifest/v0.1`, recording provider/dataset, absolute Raw
locator/SHA, raster statistics and declared/verified/unresolved vertical semantics.
It registers rather than copies the source. `load_native_manifest` L147 rechecks
source bytes and metadata; a JSON file alone is not a portable input bundle.

[Standardizer](../../src/ouem/standardize/terrain/__init__.py#L66) requires source
and study-area CRS 6677 and input Float32. It normalizes mask/NoData to -9999,
preserves dimensions, affine, extent, resolution and all valid values, reopens
the output, and writes `ouem-standard-terrain-manifest/v0.1` plus vertical tags.
It does not crop to the YAML extent, enforce its coverage, mosaic, reproject,
resample or transform vertical coordinates. The YAML CRS check is not an AOI
coverage check. **0.5 m is the accepted source resolution, not a universal
Standardizer resolution check**; another already compliant resolution is not
the same as a newly accepted dataset.

[Standard Terrain](../OUEM_Standard_Terrain_v0.1.md) remains PROVISIONAL and scoped
to the initial Komae bare-earth surface. [A2 2026-10-06](../acceptance/OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md)
is the existing accepted run; [source correction](../acceptance/OUEM_A2_Terrain_Source_Provenance_Correction_20261026.md)
identifies **Tama**, despite historical `tokyo_23ku` local paths.
[Later reproducibility verification](../acceptance/OUEM_A2_Terrain_Reproducibility_Verification_20261026.md)
is a technical PASS proposal with formal approval pending independent review.
Do not promote it, or change old generated pending-status strings, via this audit.

### Reuse, source semantics and user obstacles

Native's provider/dataset and vertical declarations are arguments, not Tokyo-only
hard-coded dispatch. A user can register an alternative compliant local DEM and
run the Standard CLI without Codex. Structural success does not verify bare-earth
versus DSM, unit/scale meaning, measurement age, geographic validity or surveyed
vertical accuracy. The generic Native inspection does not implement the fixed
downloader's complete scale/offset profile or a general semantic source catalogue.
These need explicit review/preflight for new providers, not silent normalization.

Unresolved vertical status is allowed in Terrain registration/Standardization;
it does not authorize numerical combination with Building/canopy absolute Z.
The fixed source declares T.P.; horizontal EPSG does not establish it for other
providers. Another projection, datatype, rotated raster, NaN-only NoData, national
GSI product or point cloud needs an approved preparation/contract path; simply
changing EPSG tags or treating DSM as bare earth is invalid.

[terrain_local_acceptance.preflight](../../src/ouem/terrain_local_acceptance.py#L28)
and its [CMD launcher](../../scripts/work/terrain_komae_local_acceptance.cmd) are
Komae-only: fixed original SHA/profile, study YAML and provider/vertical text.
`--check` is a real read-only planning mode; processing mode invokes tests and
existing CLIs into a new directory. Its successful exit is
PROCESSING_COMPLETED_PENDING_REVIEW, not Formal Acceptance. The module explicitly
does not validate the acquisition manifest or independently reopen all outputs.
The later reproducibility record performs separate evidence checks.

Direct Native manifest/Standard output writes do not implement the fresh-output
directory/atomic bundle protocol of the acquisition and Source-H paths. Repeated
direct commands can replace manifests/TIFFs. Source registration is absolute-path
bound. Keep fresh output names and original manifests; migration/relocation needs
new evidence without rewriting accepted old locators.

Existing [Terrain tests](../../tests/test_standard_terrain.py),
[acquisition tests](../../tests/test_tokyo_tama_dem_acquisition.py) and
[helper tests](../../tests/test_terrain_local_acceptance.py) cover synthetic
preservation, fingerprints, vertical declarations, archive/transfer safety and
local-helper boundaries. They were inspected only. No provider-wide, multi-tile,
cross-zone or new-DEM acceptance is inferred.

## 5. Canopy Assessment

### Actual acquisition and partial preparation

[meta_chmv2.select_tiles](../../src/ouem/acquire/meta_chmv2.py#L90) transforms a
configured rectangular AOI to a densified WGS84 envelope and selects actual
zoom-10 index features, requiring coverage. `mosaic_crop` L174 requires aligned
single-band north-up EPSG:3857 COGs, compatible pixels/masks/metadata, consistent
overlaps and complete snapped-envelope raster support. It copies native samples
without resampling. Output keeps the source Web Mercator grid, not the study
area's projected grid; Web Mercator pixel spacing is not automatically a local
ground-distance resolution. Acquisition's fixed Meta release/index schema is a source
profile; its AOI is not hard-coded to Komae and is not an arbitrary polygon AOI.

Raw contains the index and complete original selected COGs. Work contains
`chmv2_aoi.tif` and `ouem-chmv2-acquisition-poc/v0.1` acquisition-record JSON.
Offline index/tile replay records local copies, not a successful new HTTP event.
Defaults cap one tile at 1 GiB, index at 128 MiB, output at 16 million pixels;
there is no aggregate source-tile count/total-download budget argument. A large
AOI can need substantial transfer/storage even if output limits are respected.
Per-tile grid checks are not proof all remote tiles or new municipalities work.
[Acquisition evidence](../Meta_CHMv2_AOI_Acquisition_PoC.md) records bounded Komae
download/replay and synthetic multi-tile tests; no live endpoints were checked here.

[height_envelope.validate_sources](../../src/ouem/height_envelope.py#L109) requires
matching completed **CHMv2** acquisition lineage, a separate hash-bound HAG-in-metre
evidence bridge/source-text snapshot, documented CHM/DEM compatibility review,
matching Standard Terrain vertical metadata/tags, and an authoritative Markdown
acceptance record explicitly identifying the exact accepted Terrain output hash.
It parses the existing status/hash table format: an arbitrary completed Terrain
manifest is not sufficient. A new region's Terrain bytes therefore need applicable
reviewed acceptance evidence under this experimental gate. Do not weaken the gate
or edit old Acceptance records to make new inputs pass.

`GridSpec` L40 supports only aligned EPSG:6677 metre bounds, explicit positive
resolution (default 1 m), <=16 million cells. `sample_raster` L181 transforms
output centres to each source CRS and uses inverse affine/floor nearest lookup;
it accepts numeric single-band rasters with identity scale/offset and acceptable
unit metadata. That reusable sampler does not broaden the provenance gate.
`ConstantCR` defaults to 0.60; the versioned model interface permits explicit
alternative ratio arrays but the CLI instantiates only the constant model.
`calculate` L213 derives top=DEM+CHM and bottom=DEM+CHM*(1-CR), records missing,
outside, invalid and zero-height-valid separately, then stores Float32 heights.
No valid state establishes trees' ecological presence or absence.

Outputs are `canopy_top_z.tif`, `canopy_bottom_z.tif`,
`height_envelope_state.tif`, `height_envelope_manifest.json` under
`ouem-height-envelope-poc/v0.1`. They use staged verification, no-clobber hard
links, input rechecks and manifest-last completion. Filesystems lacking hard-link
support fail; this operational prerequisite is documented, not solved by overwrite.

The [PoC contract](../CHM_Height_Envelope_PoC_v0.1.md) retains its original
missing-input execution statement. Later [3D verification](../verification/OUEM_Height_Envelope_3D_Visualization_Komae_20261026.md)
and [B1 results](../experiments/real_komae_solar/RESULTS.md) record subsequent
real exploratory Envelope use. These are different dates, not grounds to claim
the route is still entirely synthetic or to rewrite earlier evidence. The later
verification remains review/evidence with its stated limits, not full Canopy
acceptance or proof that every local helper is a committed reusable entry point.

### Meta CHMv2 versus alternative CHM / LiDAR

Meta acquisition is coupled to a specific public prefix, index property `tile`,
quadkey length, EPSG:3857 COG layout and pixel-preserving merge rules. Existing
offline overrides supply the same profile's index/COGs; they are not a generic
source/URL override. The acquisition record itself does not prove HAG semantics.

A LiDAR-derived raster might be HAG, DSM, absolute canopy-top Z or normalized
returns; GeoTIFF readability cannot decide which. Alternative use needs explicit
source identity, units, scale/offset, bare-earth normalization method and source
DEM, horizontal/vertical reference, surveyed footprint/coverage, classification,
date/density, masks and estimation/uncertainty provenance as applicable. Whether
and how those fields become required is a future contract decision. Do not add
an absolute top-Z raster to a DEM as though it were HAG, or infer surveyed absence
from a pixel mask. No tracked LAS/LAZ-to-CHM/DTM provider/PDAL processing pipeline
was found in src/scripts/config; external installed tools are not implementation.

The separate [legacy canopy experiment](../../src/ouem/komae_canopy.py#L30) requires
`ouem-meta-chm-provenance/v0.1`, <=2 m sampled source spacing and default 3 m
cutoff / bottom=0.4*height; it produces engine scenario arrays. It is neither
the acquisition bridge nor full Standard Canopy. Those assumptions must not be
silently copied into a provider-neutral Standardizer.

### Full Standard readiness

[Standard Canopy](../OUEM_Standard_Canopy_v0.1_Draft.md) is DRAFT. It proposes
original polygons/stable IDs, explicit coverage/presence versus unknown states,
absolute top/bottom surfaces, shared GridSpec, replaceable crown-base inference
and provenance. Polygon sourcing/validity/IDs, coverage encoding and boundary
rules, final state semantics and acceptance remain incomplete. Native and
Standardize Canopy `__init__.py` files are one-line namespaces, with no production
entry point. Height Envelope lacks canonical polygons, surveyed-presence evidence
and the full Native/Standard chain; it cannot be renamed Standard to fill that gap.
The earlier [Canopy consistency review](../reviews/OUEM_Standard_Canopy_Consistency_Review_20261027.md)
independently documents these partial-lifecycle, state and source-evidence limits;
this audit does not resolve its findings.

Users can execute acquisition and Envelope CLIs without source edits **when all
reviewed inputs already exist**. They must currently author/review the evidence
packet and manage source snapshots/acceptance locators themselves. No generic
Canopy Native CLI, source-selection workflow, LiDAR preparation CLI or full
Standardizer can be offered as an implemented user path. Existing
[acquisition](../../tests/test_meta_chmv2_acquisition.py) and
[Envelope tests](../../tests/test_height_envelope.py) cover synthetic masks,
grids, formulas, semantic gates, mutation and safe publication; not nationwide
or ecological validity. No tests were executed for this audit.

## 6. Cross-Cutting Generalization Issues

1. **Configuration has different scopes.** [study_area.py](../../src/ouem/study_area.py#L28)
   parses a deliberately small two-level rectangular YAML (ID/name/EPSG/bounds).
   Only one tracked study-area example exists. Extra phase/size fields are not a
   general pipeline configuration; full polygon AOIs, per-stage buffers, mesh
   ownership/deduplication and provider selection in Concept are not implemented
   by this parser. Existing fixtures/Komae defaults are not evidence of universal
   constraints; explicit validators/constants above are.
2. **B1/B2 configuration starts downstream.** [e2e_config.RunConfig.load](../../src/ouem/e2e_config.py#L86)
   and [example JSON](../../config/experiments/komae_e2e.json) bind prepared
   Building/Terrain/Envelope paths and hashes, EPSG:6677 extent and context.
   They do not discover/download/standardize a new municipality. The configured
   A/B success demonstrates reuse inside prepared coverage, not upstream generality.
3. **CRS is a contract issue as well as a constant.** Building's upper contract
   permits a study-area projected CRS, but accepted implementation and consumers
   are 6677-bound; Terrain v0.1 explicitly specifies 6677. Removing an `if` is not
   a safe cross-zone implementation. Vertical transformations and national datum
   revision policies are unresolved; identity-H and source-declared T.P. are
   bounded evidence, not universal surveyed compatibility.
4. **Sources and Standard responsibilities are only partly separated.** Legacy
   Building Standard owns PLATEAU attribute/CRS mapping and dataset literal;
   Source-H has explicit independent dispatch. Terrain's numeric Standardizer
   is less provider-specific, but semantic review and generic acquisition are
   missing. Envelope currently owns Meta-specific evidence validation beside
   reusable sampling/calculation. These are concrete seams for scoped future work,
   not a reason to build a universal provider framework now.
5. **Provenance/safe reruns differ by stage.** Absolute locators, receipts,
   completion markers, source-code hashes, human evidence and generated pending
   labels are not interchangeable. Plan relocatable *new* bindings with hashes;
   never repair historical manifests to match moved files/new code. Fresh outputs
   are a user convention in some old APIs and an enforced invariant in newer ones.
6. **Runtime remains two environments.** Follow [architecture](../architecture.md),
   [Windows setup](../development/OUEM_Windows_Development_and_Remote_Setup_20261025.md)
   and [CI evidence](../development/OUEM_CI_Runtime_Evidence.md). Legacy OGR workers
   use separate GIS Python via explicit files/arguments/environment; Source-H
   uses an external fixed Converter plus ordinary OUEM SQLite/PyProj/geometry
   libraries. Terrain/CHMv2/Envelope run in OUEM, not QGIS Python. Ordinary CI
   metadata/tests do not install QGIS, supply source data or verify GUI operation.
   Pyproject has minimum versions plus pinned VoxCity, not a complete environment lock.
7. **Downstream constraints must stay downstream.** [v0.1 Adapter](../../src/ouem/adapters/voxcity/__init__.py#L461)
   accepts specified v0.1 manifests and 6677 inputs; experimental Source-H v0.2
   is not in that whitelist. B1/B2 consume saved geometry, context and masks under
   separate paths. Do not redefine Standard around VoxCity grids/TREE thresholds
   or widen accepted Adapter dispatch as incidental upstream cleanup.
8. **Dated status is not current capability proof.** Building/Canopy status pages
   at PR #121 still say B2 unimplemented; [B2 Closeout](../status/B2_TECHNICAL_MILESTONE_CLOSEOUT.md)
   records subsequent CPU Technical E2E. Older acquisition/Envelope absence
   statements likewise have later evidence. This audit reports those date limits
   without editing the owners. [B1 Closeout](../status/B1_TECHNICAL_MILESTONE_CLOSEOUT.md),
   [B1 backlog](OUEM_B1_Deferred_Validation_Backlog.md) and
   [B2 backlog](OUEM_B2_Deferred_Validation_Backlog.md) retain scientific Unknowns.

The [Repository Inventory](OUEM_Repository_Inventory_v0.1.md) / [Cleanup Plan](OUEM_Repository_Cleanup_Plan_v0.1.md)
and earlier [acquisition inventory](OUEM_Data_Acquisition_and_Reproducibility_Inventory_20261025.md)
remain useful baselines. [Acquisition/preparation design](OUEM_Data_Acquisition_and_Preparation_Design_v0.1_Draft.md)
and [catalogue/recipe draft](OUEM_Source_Catalog_and_Acquisition_Recipes_v0.1_Draft.md)
are proposals, not existing generic schemas or execution frameworks.

## 7. Prioritized Improvement Backlog

Priorities express maintenance/generalization benefit versus compatibility risk,
not new Acceptance gates. Effort is qualitative: Small = one narrow interface/docs
change; Medium = bounded implementation with failure/compatibility tests; Large =
multiple stages or unresolved contract work. Each candidate needs a separate task.

| ID / priority / effort | Problem, affected owner and evidence | Proposed improvement / benefit | Risk, prerequisites and required future checks |
|---|---|---|---|
| G01 / P1 / Medium | Users must infer supported profiles from `study_area.py`, Terrain validators, Source-H plans and Envelope gates; current preflight is a Komae integration/helper path | One read-only capability/input report for an explicitly selected existing upstream stage/profile. Report supported constraints, files/adjacent evidence, intended new destinations and blockers; no execution or auto-selection. First slice below | Low/moderate: avoid a new shadow contract or false semantic PASS. Reuse applicable validators, keep unresolved facts explicit, test no writes/subprocess/network and byte-preserved fixtures; no new formal manifest required |
| G02 / P1 / Medium | `real_komae_source_h.MEMBERS` and two-member count force source edits for new meshes despite reusable lower-level APIs | Explicit ordered member-list configuration and safe selection for the existing Source-H profile; retain the legacy two-member invocation. Record ZIP/member/codelist identities and actual exclusions | Moderate/high: archive safety, duplicate IDs, LoD2 support and source-code fingerprints. Needs an identified source/release with reviewed 6697/H semantics; synthetic ZIP/xlink/rejection tests, unchanged legacy arguments/outputs/IDs, later separately authorized new-area smoke. Do not add arbitrary CityGML parsing |
| G03 / P1 / Medium | `tokyo_tama_dem` and `terrain_local_acceptance` retrieve/validate only one original; valid local alternative inputs lack reusable acquisition recipes | Add one separately reviewed tile recipe in the same source/coordinate profile, or explicit local supplied-input onboarding, retaining the original recipe unchanged. Declare expected identity/coverage/quantity/vertical evidence and bounded transfer; improve same-zone geographic reach | Moderate: never expose unchecked URL/hash override as acceptance. Requires new tile/provider evidence, terms and expected profile. Test archive/limits/new-directory safety and unchanged original bytes/gates; no mosaicking, reprojection or new automatic acceptance in this PR |
| G04 / P2 / Small–Medium | Komae CMD output/count defaults, raw CLI discoverability and fresh-output rules are spread across runbook/provider guides | Add parameterized *new* operational examples or thin argument-forwarding launcher only where G01–G03 expose an actual use; clearly separate local acceptance from processing | Low/moderate: do not replace cited historical commands or manufacture a generic accepted path. Requires stable stage arguments. Check spaces/cwd/error exits and existing launchers; docs links, no automatic run/overwrite |
| G05 / P2 / Medium | Legacy Building and direct Terrain APIs can replace outputs; some provenance edges rely on human linkage | Independently propose explicit no-clobber/new-run options and a stage-completion/lineage check, preserving existing interfaces by default until reviewed | Moderate/high behavior change. First characterize replacement/receipt/failure behavior and callers. Test partial failure, concurrent outputs, changed inputs, deterministic bytes and old entry compatibility. Do not retrofit old manifests or batch-refactor all writers |
| G06 / P2 / Medium (decision first) | `height_envelope.validate_sources` requires Meta acquisition schema even though sampler/formula are separable | Design one explicit alternative CHM evidence/profile mapping (e.g. already derived LiDAR HAG), preserving the existing Meta route. Normalize semantics/evidence before sharing numeric Envelope calculation | High semantic/provenance risk. User review of source meaning/normalization/ground/coverage first; actual source/DEM/evidence needed. Test HAG versus absolute-Z rejection, units/scale/masks/vertical compatibility and original Meta gates. No fabricated CHMv2 receipts for other sources |
| G07 / P2 / Large (contract/architecture) | Multiple 6677 gates, Terrain no-reprojection contract, legacy/source-H CRS separation and Adapter consumers | Specify one additional projected-CRS execution profile with horizontal/vertical semantics, resampling only where authorized, and consumer compatibility plan | High: CRS/axis/value/ID/provenance/contract impact. User-reviewed versioned contract/profile decision before implementation; cross-zone asymmetric fixtures, exact-Z and raster masks/grid tests, baseline regressions and separately scoped data evidence. No blanket removal of checks |
| G08 / P2 / Large (contract/architecture) | Full Native/Standard Canopy absent; polygon/coverage/state/ID choices unresolved in Draft | Resolve one minimal source-specific Native contract and full Standard Canopy decision set before implementing canonical polygons/top/bottom/coverage | High scientific/contract risk. User review and real polygon/coverage source evidence; independent geometry/absence/missing/height tests, CR applicability, controlled acceptance. Height Envelope remains an experimental precursor throughout |
| G09 / P3 / Large (source preparation) | No tracked LiDAR -> DTM/CHM provider, and GSI/alternative Building mappings are not implemented | Once a concrete dataset/use case is chosen, define one provider-specific Native derivation, recording input point classes, normalization DEM, algorithms/grid and lineage | High: new native tooling/runtime, quality assumptions and possibly dependencies. Requires G06/G08 decisions as applicable, provider terms/reference data and resource budget; no speculative national framework or wholesale environment merge |
| G10 / P2 / Small (docs) | Dated Current State statements can mislead new users about B2 and early missing-input checks | Add narrowly scoped later-status pointers at owning indexes when separately authorized; keep original execution claims, dates and hashes | Low: preserve history/anchors/authority. Needs owner/evidence review and link checks, no relabelling of Formal/Provisional/Draft or backlog closure |

G01–G04 are operational improvements inside declared profiles; they do not unlock
all other municipalities. G06–G09 require source/contract/architecture decisions.
Do not bundle them with general cleanup C03, rewrite old runners wholesale, or
create a catalogue database/plugin framework without a demonstrated second case.

## 8. Recommended First Implementation Slice

**Recommend G01: an ordinary-Python, read-only preflight for explicitly supplied
existing-profile inputs**, initially Native/Standard Terrain onboarding. It offers
an immediate user-facing answer to “can these files enter the current path?”
without a network operation, GIS worker, model run or broader Standard contract.

Proposed boundary, for future review: explicit source TIFF, provider/dataset,
vertical declaration/evidence, study-area file, intended Native/Standard output
locators. Report the existing structural requirements and a distinction between
Native-registerable, current-Standard-profile-compatible, coverage/semantic facts
and unresolved provenance. Reuse `inspect_dem` and `validate_terrain_input` where
applicable rather than create competing numeric rules. Report source unit/scale,
quantity and coverage evidence as observed/unknown; do not infer bare earth or
datum compatibility from raster values. Missing evidence must not become PASS.
No acquisition, registration, TIFF generation, Acceptance decision or new
required manifest/schema is part of this slice.

Future completion checks: fresh synthetic fixtures for compliant/noncompliant
CRS/dtype/NoData/vertical cases, explicit output-collision reporting, absent versus
unresolved evidence, immutability/no filesystem writes or subprocess/network,
and unchanged current validators/CLI behavior. Run focused and full OUEM tests
for that implementation; independently document any GIS validation boundaries.
Do not invoke the Komae local acceptance helper to generalize its fixed hash.

Recommended next three implementation tasks are **G01 preflight**, **G02 explicit
Source-H member selection**, **G03 one reviewed Terrain recipe/onboarding case**,
in separate PRs. They improve operability and geographic reach in existing
profiles before asking for cross-zone or alternative-source scientific changes.
For rollback, revert only the new interface/configuration code and docs; retain
all prior source snapshots, manifests, receipts and datasets. Any authorized
future evidence run uses new IDs, never overwritten B1/B2 outputs or repaired hashes.

## 9. Open Questions and Evidence Limitations

- Which next municipality, coordinate zone, PLATEAU release/LoD and DEM source
  should define the first real generalization case? A same-zone case tests a
  different scope from additional CRS support. No new data selection is made here.
- Should source-H become a future primary Building profile, or remain parallel?
  Its eligibility/acceptance and v0.1 Adapter whitelist cannot be changed by this
  audit. Broader geometry, dataset/ID versioning and source dates need review.
- What semantic evidence/acceptance mechanism should a generalized Envelope use
  instead of relying on a particular Markdown status/hash table shape? This is
  an approval/contract question, not permission to bypass the existing gate.
- What are canonical Canopy coverage/presence/IDs, accepted polygon sources,
  alternative CHM normalization and ground compatibility, grid policy, CR evidence
  and datum revision rules? These need user review before implementation; current
  estimated crowns or readable LiDAR GeoTIFFs cannot settle them.
- Evidence is tracked source, static CLI/parser/import/launcher/test inspection,
  contracts, dated status/acceptance/results and inventories. No local dataset
  inventory, hash revalidation, source catalogue refresh, URL/terms availability
  check, acquisition, GIS subprocess, Converter, VoxCity or real-data run occurred.
  Manual/external invocations, untracked acquisition helpers and fresh-machine
  compatibility remain Unknown. Recorded license/source facts are attributed to
  repository evidence, not fresh legal/provider verification.
- Ordinary Python remains separate from QGIS/OSGeo4W GIS Python. No dependencies,
  environments, CI, test files, accepted contracts, existing documents, data or
  B1/B2 statuses were changed. The engine pin remains VoxCity 1.7.0 at
  `fa212656305328a9a657973bae26f352bfe813bc`.
- Verification for this audit is document/link/path and exact diff-scope checking,
  plus `git diff --check`. Pytest is not rerun because only a new audit document
  is added and no execution behavior is changed. Referenced test names describe
  inspected coverage, not fresh PASS results. Formal Acceptance and scientific
  validation remain the responsibility of their existing records and future
  separately authorized verification.
