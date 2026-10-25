# CHM Height Envelope PoC v0.1

Status: **experimental / partial**, standalone implementation. This is a precursor to Standard Canopy, not its contract or acceptance. It implements no polygons, surveyed-coverage footprint, canopy-presence classification, voxelization, or environmental assessment.

Authority: [Concept v0.2](OUEM_Concept_Architecture_v0.2.md), [Canopy draft](OUEM_Standard_Canopy_v0.1_Draft.md), and the unchanged [Terrain](OUEM_Standard_Terrain_v0.1.md), [Building](OUEM_Standard_Building_v0.1.md), and [Adapter](OUEM_VoxCity_Adapter_v0.1.md) contracts. The Canopy draft §§8–9A explicitly permit a height-only experiment before polygon integration. Its provisional full-Canopy state codes are not adopted or ratified here.

## Usage

Use the repository OUEM venv in ordinary Windows PowerShell, following the [workstation record](development/OUEM_Windows_Development_and_Remote_Setup_20261025.md). No new dependencies or GIS-runtime merge is needed.

```powershell
.venv\Scripts\python.exe -m ouem.height_envelope `
  --study-area config/study_areas/komae_09LD3451.yaml `
  --chm data/work/meta_chmv2_komae_committed_audit_20261025/chmv2_aoi.tif `
  --acquisition-record data/work/meta_chmv2_komae_committed_audit_20261025/acquisition-record.json `
  --chm-evidence data/work/height-envelope-inputs/source-evidence.json `
  --terrain data/standard/terrain/komae_09LD3451.tif `
  --terrain-manifest data/standard/terrain/komae_09LD3451.tif.manifest.json `
  --terrain-acceptance docs/acceptance/OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md `
  --cr 0.60 --resolution 1 --dem-sampling nearest `
  --output-dir data/work/height-envelope/komae-new-run
```

This example names required inputs; it does **not** assert they are all available. Output directory must be new and separate from every input. Input byte hashes are checked again before publication. Existing inputs, Terrain's 0.5 m grid, Building artifacts, and `komae_canopy.py` are never written. Files remain outside Git under the documented local data layout.

## Input and semantic gates

Required input files are the CHM crop, its actual acquisition record, a reviewed evidence bridge and source-text snapshot, the accepted Standard Terrain TIFF and adjacent manifest, a formal Terrain acceptance record identifying its exact output hash, and the study-area YAML.

The merged [acquisition implementation](../src/ouem/acquire/meta_chmv2.py) emits `ouem-chmv2-acquisition-poc/v0.1`, with `status`, `output.sha256`, `tiles`, and source metadata. It does **not** emit the legacy `ouem-meta-chm-provenance/v0.1` HAG declaration. The generator checks a COMPLETED record and matching CHM bytes, then separately requires the following **PoC-only evidence bridge**, using actual hashes and reviewed facts:

```json
{
  "schema": "ouem-height-envelope-evidence/v0.1",
  "chm_sha256": "<actual CHM output SHA-256>",
  "acquisition_record_sha256": "<actual acquisition record SHA-256>",
  "height_semantics": "height_above_ground_m",
  "height_reference": "local_ground",
  "dem_quantity": "absolute_elevation_m",
  "evidence": {
    "source": "<source dataset and release>",
    "citation": "<supporting source URL/document identifier>",
    "statement": "<exact source statement establishing HAG in metres>",
    "snapshot_path": "source-statement.txt",
    "snapshot_sha256": "<actual UTF-8 source-text snapshot SHA-256>"
  },
  "compatibility_review": {
    "reviewer": "<reviewer>",
    "reviewed_at": "<review date>",
    "basis": "<why this relative-height source can be combined with this DEM; limitations>",
    "vertical_combination": "relative_height_plus_dem_no_offset",
    "dem_vertical_reference": "<exact Standard Terrain vertical_reference.name>",
    "dem_sha256": "<actual accepted Standard Terrain SHA-256>"
  }
}
```

Snapshot path is relative to the evidence JSON (absolute paths also work). Snapshot hash and exact quoted statement must match. Evidence packet and snapshot hashes are retained in the envelope manifest. This validates integrity and explicit declarations, **not** authorship or the truth of arbitrary supplied prose: a responsible reviewer must establish the source meaning, applicability, and compatibility from the cited source. The program cannot independently establish ecological accuracy or that a global model's ground surface exactly matches the local DEM. Do not fabricate that review. Missing evidence or unresolved compatibility blocks generation.

Terrain must match `ouem-standard-terrain-manifest/v0.1`, its `standard.sha256` and raster metadata, preservation-validation booleans, and explicit `source-declared` or `verified` vertical name/source. TIFF vertical tags must agree. EPSG:6677 never supplies the vertical datum. Absolute elevation in metres is an explicit bridge declaration grounded in the existing Terrain contract; it is not inferred from coordinate magnitudes. A resolved source-declared T.P. is allowed by the existing contract and is not upgraded to independently surveyed `verified`.

Historical pending-status strings in generated Terrain manifests are **not** acceptance decisions. For the initial boundary, `--terrain-acceptance` is an authoritative Markdown record with an explicit `| Status | **ACCEPTED** |` row and a `| Standard output SHA-256 | <backtick-wrapped hash> |` row, matching the existing A2 record. A3's un-hashed input-path reference alone is insufficient. Different record formats or a newly regenerated hash need reviewed acceptance evidence; do not edit existing records to make them pass. The supplied record's authority remains a reviewer responsibility.

Only one numeric band and identity scale=1 / offset=0, with unit metadata absent or explicitly metres, are supported. Nonidentity scale/offset is blocked rather than silently changing elevations. No datum transform or offset is implemented. The evidence bridge is deliberately stricter than possession of a plausible raster or the old handoff file; it does not modify acquisition or legacy Canopy provenance schemas.

## GridSpec and sampling contract

Initial Komae profile: EPSG:6677, bounds `[-23600,-40800,-23200,-40500]`, 1 m, 400 columns × 300 rows, north-up/unrotated, affine `[1,0,-23600,0,-1,-40500]`. First centre is `(-23599.5,-40500.5)`, last `(-23200.5,-40799.5)`. Resolution is an explicit PoC argument, **not** a nationwide Standard requirement. Bounds must align to it; no silent extent expansion. Current GridSpec supports EPSG:6677 only and limits in-memory grids to 16 million cells.

CHM and DEM have separate calls through `sample_raster(..., method="nearest")`. Output centres are transformed horizontally to each source CRS with traditional XY order, then mapped by inverse affine and floor to the containing source pixel. Left/top source edges are inclusive; right/bottom edges are exclusive. No extrapolation, missing-value fill, or source modification occurs. Masks and declared NoData are read independently of values. A declared NaN NoData is missing; an unmasked NaN/Inf is invalid. Finite negative DEM elevations are allowed; negative CHM is invalid.

The DEM remains at its accepted native grid. Only sampled copies are used. The sampling strategy boundary supports a future bilinear implementation, but current non-nearest requests fail: masked-neighbour rules and a comparison must be reviewed first.

## CR and numeric output contract

`CrownRatioModel` exposes `specification()` and `ratios(grid, chm, dem)`. A model returns one ratio per output cell and JSON metadata with ID/version/parameters. Models receive copies of sampled heights and terrain. The initial `ConstantCR` is `constant_cr_v0.1`, version `0.1`, configurable default `0.60`, finite `0 < CR <= 1`. This is an experimental continuity parameter, not ecological validation. A later class/spatial model can supply ratio arrays without changing the output bundle. Such a model must enumerate its own source identities and applicability in its specification; the current CLI only constructs the constant model.

For finite valid samples and CR:

```text
Z_top    = DEM + CHM
Z_bottom = DEM + CHM * (1 - CR)
```

Calculation uses Float64 then stores Float32. Valid stored outputs must remain finite, avoid the reserved NoData value, and obey `DEM <= Z_bottom <= Z_top`. Float32 overflow, sentinel collision, or invalid model results get a numeric/model error flag. Numeric rounding errors are reported, not hidden behind an invented accuracy tolerance. There is no 3 m cutoff or other minimum-tree-height threshold. Zero height is a mathematically valid zero-depth envelope at ground and **does not establish canopy absence**.

| Output | Contract |
|---|---|
| `canopy_top_z.tif` | Float32 absolute top elevation, explicit NoData `-9999.0`, output GridSpec |
| `canopy_bottom_z.tif` | Float32 estimated absolute bottom elevation, same NoData/GridSpec |
| `height_envelope_state.tif` | UInt8 flags below, no raster NoData tag, output GridSpec |
| `height_envelope_manifest.json` | PoC schema `ouem-height-envelope-poc/v0.1`, COMPLETED marker and evidence/QA |

The -9999 sentinel is a PoC representation choice, not a newly ratified Canopy Standard. Nonvalid heights are always NoData. All three rasters are staged, closed, reopened and verified before any final file is linked into the new output directory. Hard links avoid replacing existing names; unsupported filesystems fail closed. If publication fails, links created by this run are removed. The manifest is published last as the bundle completion marker; an interrupted run without it is incomplete, even if some TIFFs exist. Empty/incomplete run directories are not automatically reused.

## State encoding: validity flags, never canopy presence

| Code/bit | Meaning |
|---|---|
| 1 | Valid numeric height envelope, including zero height |
| 2 | CHM missing: masked / declared NoData at an inside-source cell |
| 4 | DEM missing: masked / declared NoData at an inside-source cell |
| 8 | CHM invalid: unmasked negative or nonfinite value |
| 16 | DEM invalid: unmasked nonfinite value |
| 32 | Outside CHM raster support |
| 64 | Outside DEM raster support |
| 128 | Invalid CR/model result or unrepresentable/inconsistent Float32 result |

Nonvalid flags combine with bitwise OR (e.g. 6 = missing both CHM and DEM). Valid=1 never combines with an error. Outside suppresses missing/invalid for that **source**, and missing suppresses invalid for that source; errors from the other source remain visible. Model/numeric checks apply to otherwise usable samples. Every cell has either 1 or a nonzero combination of error bits. State 0 is unused. Source raster support is not surveyed ecological coverage. There is no no-canopy code, polygon mask, or thresholded presence claim.

## QA, manifest, and reproducibility

Manifest records all input file paths/sizes/SHA-256, source evidence and acquisition lineage, vertical reference, GridSpec, source raster metadata, independent sampling methods, CR specification, state encoding, per-bit counts and valid/nonvalid totals, zero-height valid count, ranges, Float32 rounding diagnostics, inequality/finite/NoData checks, and output file hashes. Per-bit counts can overlap; valid+nonvalid equals total. An all-missing grid can complete as an accurately classified empty envelope; zero valid cells and null ranges remain explicit and do not imply analysis suitability.

`reproducibility_sha256` hashes the stable contract/input hashes/grid/model/QA/source metadata/output hashes. Input identities change it. Runtime paths, recorded timestamp and implementation environment are recorded separately; the full manifest's bytes are not claimed deterministic. TIFF hashes and the stable fingerprint must match repeated runs with identical inputs/config/model/environment. Code revision, dirty state, disk module hash, optional HEAD module hash/byte comparison, supporting-module hashes, Python/NumPy/Rasterio/GDAL/PyProj versions identify execution. A nominal HEAD with dirty/untracked implementation does not establish committed-code identity. Input and implementation identities are checked again before final publication.

## Conflicts, execution evidence, and deferred work

- The Canopy draft's polygon/presence classes and unresolved encoding are not silently finalized. This partial PoC uses height-validity bits under its own versioned schema.
- The acquisition record is not HAG semantic proof. The old handoff JSON has a different raster SHA and cannot be applied to this crop. No automatic legacy conversion or source-evidence fabrication is implemented.
- The accepted Terrain remains canonical at 0.5 m. This PoC's 1 m samples do not revise its contract or acceptance.
- On the inspected workstation, the actual CHM crop and acquisition records exist, but there is **no Terrain TIFF anywhere under repository data/**; `data/standard/terrain/` and `data/native/terrain/` contain only markers. Therefore no real CHM+accepted-DEM smoke test was run and no real height-envelope outputs were generated. An actual hash-bound reviewed evidence bridge is also not present. Synthetic test results are not real-data acceptance.
- Subsequent work: supply the exact accepted Terrain bytes+manifest and reviewed bridge; run an isolated Komae smoke test, inspect vertical relationships and missing cells; compare DEM sampling strategies; then separately design the VoxCity conversion from absolute envelope to engine-relative arrays with state/NoData policy. No existing VoxCity integration is changed here. Full Standard Canopy additionally needs polygons, verified coverage/presence semantics, and independent acceptance.

## Validation record

Static baseline: main `a405ed2` fetched before implementation. Validation used repository OUEM Python on Windows, with individually approved ordinary-environment execution because sandbox hard-link publication returned WinError 5.

- `.venv/Scripts/python.exe -m pytest -q tests/test_height_envelope.py`: **31 passed, 59 warnings**, 8.65 s.
- `.venv/Scripts/python.exe -m pytest -q`: **462 passed, 5 skipped, 225 warnings**, 190.92 s. Existing Building, Terrain, acquisition, Adapter and experimental Canopy tests remain passing. Warnings are Rasterio Affine PendingDeprecationWarning messages.
- Initial sandbox run: 18 passed, 6 failed because final-file hard links were denied. The approved ordinary-environment rerun passed; tests and expected values were not weakened to bypass that boundary.
- Tests cover canonical GridSpec, native 0.5 m centre selection, formulas and CR changes, zero/negative/nonfinite heights, CHM and DEM masks/NoData, separate CHM/DEM outside flags, EPSG:3857 source lookup, missing/incompatible semantic evidence, invalid model/Float32 results, a replaceable class CR model, TIFF/fingerprint determinism, byte-preserved synthetic Terrain and 3D Building artifacts, input mutation, and staged-publication rollback.

Local readiness check found the real CHM at `data/work/meta_chmv2_komae_committed_audit_20261025/chmv2_aoi.tif` (SHA-256 `c5f99a4e9b21e8f419825ef2cac25ec7b36bafbe8a79a89b062201343f0ef880`), matching its COMPLETED acquisition record (SHA-256 `ab83b9b466b85a4dd2a4a73749b1c2fffb68104b88f9d630ea88f2da76c956e0`). Neither `data/standard/terrain/komae_09LD3451.tif` nor its adjacent manifest exists. Thus **real Komae envelope execution was not performed**. No synthetic DEM was substituted for the missing accepted dataset, and no evidence bridge for real inputs was fabricated.

Only the standalone module, its synthetic tests, and this PoC document are added. Existing contracts, acceptance records, canonical data, VoxCity integration and `src/ouem/komae_canopy.py` remain unchanged. The validation results establish the experimental implementation's tested behaviour, not full Standard Canopy acceptance.
