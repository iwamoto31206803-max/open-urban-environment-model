# OUEM A2 Terrain reproducibility verification — 2026-10-26

## 1. Record status, purpose and scope

| Field | Recorded value |
|---|---|
| Record type | Dated technical reproducibility verification; additive to existing records |
| Proposed technical verdict | **PASS**, for this tile and execution only |
| Formal acceptance approval | **Pending independent review**; not conferred by this record or a CLI exit code |
| Subject | Tokyo Tama ground DEM `09LD3451`, retained Raw → Native registration → Standard Terrain |
| Processing interval | 2026-10-26 11:36:00.983769–11:38:37.600508 JST |
| Execution commit on main | `9178c9f1eb04f11623c07522de4c53d38a33ecbd` |

This record documents the existing real-data execution and independent checks
retained in `data/work/terrain-reproducibility/komae-20261026-01/RESULTS.md`
and its associated evidence. Its purpose is to make that bounded result
auditable in Git without committing local datasets/manifests. During preparation
of this document, the actual retained ZIP, TIFFs and JSON manifests were read
again and their hashes, lineage, grid, masks and valid samples rechecked. This
preparation did **not** perform another download, generation or pytest run.

The [2026-10-06 A2 acceptance](OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md),
[A3 acceptance](OUEM_A3_VoxCity_Komae_Acceptance_20261005.md), and
[2026-10-26 source correction](OUEM_A2_Terrain_Source_Provenance_Correction_20261026.md)
are preserved unchanged. Technical reproducibility PASS is distinct from a new
formal acceptance approval. No nationwide/provider-wide or downstream acceptance
is proposed here.

## 2. Execution identity and environment

PR #66 (acquisition) and PR #67 (source correction/helper) were confirmed to be
ancestors of execution main `9178c9f1eb04f11623c07522de4c53d38a33ecbd`. The
checkout used that commit in detached HEAD; Git worktree status was empty before
and after processing, and the recorded implementation/config hashes were unchanged.

| Runtime observation | Value |
|---|---|
| OS/runtime | Windows, ordinary repository OUEM venv; not OSGeo4W Shell |
| Python | 3.11.9 |
| Rasterio / GDAL | 1.4.4 / 3.10.3 |
| NumPy | 2.4.6 |
| Python executable, historical location | `C:\dev\open-urban-environment-model\.venv\Scripts\python.exe` |
| Helper pytest result | **526 passed, 5 skipped, 243 warnings**, 153.83 s, exit 0 |

Warnings in `execution.log` are Rasterio/Affine `PendingDeprecationWarning`.
The helper invoked pytest with `-q`, so this particular log does **not** list
the five individual skip reasons; no per-case reason is inferred from prior
runs. Synthetic pytest success is supporting regression evidence, separate
from the real TIFF/hash/sample checks below.

Execution module SHA-256 (on-disk bytes, distinct from Git blob identities):

| File | SHA-256 |
|---|---|
| `src/ouem/native/terrain/__init__.py` | `79abb3cde477f4561e6df64b07979a2a85be5ce7d724aa553db1e13f910c14fd` |
| `src/ouem/standardize/terrain/__init__.py` | `6c9ce8fbbccced65d8889b1d3f45d17c197356b14ee6967692d2188e5641e664` |
| `src/ouem/terrain_local_acceptance.py` | `c628ba7ecdb908d7d262aca87f7694f2c751c90d597624a731f9e9e2950fa5ee` |
| CMD helper | `3f65e0c48a0d230e0a2782dac82f7f07fddec6a3ae4a9962c4a2c5a68676b907` |

Compared with the earlier A2 execution commit `e1037dc4b01b4b091e30a8f3806b363d5ef12cc0`,
the observed Terrain code difference was extraction of shared input prerequisites
in `607c2c3`; the write/value-conversion body and Native implementation had no
diff. No transformation implementation was changed for the recorded rerun.

## 3. Source, original data and licence

Provider: **Tokyo Metropolitan Government, Bureau of Digital Services**.
Dataset: **東京都デジタルツイン実現プロジェクト 多摩地域点群データ**, **グリッドデータ（0.50m）**,
tile `09LD3451`, a ground-derived elevation DEM, not DSM.

- [Tokyo Tama catalogue](https://catalog.data.metro.tokyo.lg.jp/dataset/t000029d0000000020)
- [G Spatial Information Center dataset](https://www.geospatial.jp/ckan/dataset/tokyopc-tama-2023)
- [0.50 m resource](https://www.geospatial.jp/ckan/dataset/tokyopc-tama-2023/resource/fc69d49b-dd22-43e0-b52e-2fad4da7bcfa)
- [Original ZIP](https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2023/dig/grd50/09LD3451.zip)
- [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) and
  [distribution terms](https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2023/dig/doc/license.pdf)

The catalogue's licence declaration and required attribution/source links are
recorded in the acquisition manifest and [acquisition procedure](../Terrain_Acquisition_PoC_v0.1.md).
The ZIP and extracted original TIFF are unchanged. Source attribution is Tokyo
Metropolitan Government / Tokyo Digital Twin Tama dataset; Standard generation
is OUEM processing and must not be represented as an unmodified provider product.

The Tama catalogue declares JGD2011 / Plane Rectangular CS IX and elevation
relative to Tokyo Bay mean sea level. The recorded vertical status is
**source-declared T.P. (Tokyo Peil / Tokyo Bay mean sea level)**, with the Tama
catalogue citation. The correction supplies the geographic/source context;
EPSG:6677 alone is not vertical evidence. Neither this rerun nor preparation
of this document re-fetched the live catalogue or independently surveyed heights.

PR #66's original acquisition occurred at `2026-10-26T01:49:49.559040+00:00`
(10:49:49 JST). The later 11:36 rerun used those retained files; it was not a
new network acquisition.

## 4. Locations and executed procedure

Historical repository root: `C:\dev\open-urban-environment-model`. The following
paths are relative to that historical root and identify the recorded local files:

| Role | Recorded path |
|---|---|
| Raw bundle | `data/raw/terrain/tokyo_tama_dem_050m/komae/acquisition-20261026-01/` |
| Execution evidence | `data/work/terrain-reproducibility/komae-20261026-01/` |
| Native manifest | evidence directory + `generated/native.json` |
| Standard TIFF | evidence directory + `generated/standard.tif` |
| Standard manifest | evidence directory + `generated/standard.tif.manifest.json` |

Absolute paths embedded in manifests record that execution location; they are
not universal installation requirements. For reproduction, use a local checkout,
independently validated original bundle and an explicitly **new, nonexistent**
output directory. Do not reuse the historical directory names or patch old
manifest paths. The existing Native registration creates a fresh manifest for
the actual local Raw path.

The existing `scripts/work/terrain_komae_local_acceptance.cmd` was invoked first
with `--check`, then without it, using the recorded Raw TIFF and the new
`data/work/terrain-reproducibility/komae-20261026-01/generated` output directory.
The read-only preflight returned exit 0, created no generated directory and
left inputs unchanged. The subsequent execution ran full pytest and the existing
Native and Standard CLIs, also returning exit 0.

Replay template (replace both placeholders; this is not another executed run):

```bat
scripts\work\terrain_komae_local_acceptance.cmd "<validated-raw-dir>\09LD3451.tif" --run-dir "<new-run-dir>" --check
scripts\work\terrain_komae_local_acceptance.cmd "<validated-raw-dir>\09LD3451.tif" --run-dir "<new-run-dir>"
```

The helper does not validate the acquisition manifest or independently verify
its generated outputs. `PROCESSING_COMPLETED_PENDING_REVIEW` only records
successful Native/Standard subprocess exits. The independent checks in this
record were performed separately; no helper completion flag is an acceptance
decision. See the [current work procedure](../../scripts/work/README.md#komae-terrain-local-acceptance).

## 5. Acquisition → Raw → Native → Standard verification

| Independent check | Recorded result |
|---|---|
| Acquisition manifest | Expected schema, **COMPLETED**, correct bundle path/source; only expected ZIP/TIFF/manifest present; no FAILED or staging residue |
| Retained originals | Actual sizes/hashes match acquisition manifest; ZIP CRC passes; sole root member `09LD3451.tif` hashes identically to retained TIFF and A2 Source SHA |
| Native registration | Manifest readable, expected schema; Raw path/hash and raster inspection match actual input; no redundant Raw raster copy |
| Standard input lineage | Readable manifest references this Native manifest and the same Raw input/hash; provider/dataset match Native |
| Standard output identity | Manifest output path/hash, metadata and all validation fields match the actual reopened Standard TIFF |
| Vertical provenance | Native/Standard retain Tama source-declared T.P. and catalogue evidence; Standard TIFF vertical name/status tags agree |
| Preservation of older evidence | Pre/post hashes of retained Raw, earlier Native-compatibility evidence and existing A2/A3 records unchanged |

Artifact SHA-256 identities:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Raw ZIP | 837282 | `8b54c4cd58e17a6edf86ca7ad9e71672776c90669d116981d1368e871e7c393d` |
| Raw TIFF | 1922867 | `c747f2ae2ee30f67da98c1c90961f6a094fa0fca8ba3f15a1131c09783d73824` |
| Acquisition manifest | 4524 | `ea0c54d798db06274cef95b33c43439924742ea8707fb24a3c1de8e5f0180e9d` |
| New Native manifest | 1478 | `1226640017845ef9f4858d970b70b947700c706ca90431f15d2668e11fefef92` |
| New Standard TIFF | 1080470 | `0afb6d1706b97bd39c8c93ff8feb580094fe585f567e2de1f2081c082602f90a` |
| New Standard manifest | 2738 | `5e96bf3e0ababad7e2f79a0d2090d0356fdc707dff6115575c8b0ba8b88f5dbb` |

Manifest bytes include paths/timestamps and corrected source text; their hashes
identify this execution and are not claimed to reproduce old manifest bytes.

## 6. Past A2 comparison and independent numeric checks

The historical A2 Standard SHA-256 is
`0afb6d1706b97bd39c8c93ff8feb580094fe585f567e2de1f2081c082602f90a`.
The new Standard TIFF has **exactly the same SHA-256**. This establishes
byte-level reproducibility against the authoritative recorded fingerprint.
The historical Standard TIFF was not locally available for a separate direct
file/array diff. Whole-array numeric comparison was instead performed between
the hash-identical original Raw TIFF and this new Standard, and the resulting
statistics also match the historical A2 record.

| Property | Independent observation |
|---|---|
| CRS | EPSG:6677 |
| Resolution / dimensions | 0.5 × 0.5 m; 800 columns × 600 rows; one Float32 band |
| Bounds | `[-23600,-40800,-23200,-40500]` |
| Affine | `[0.5,0,-23600,0,-0.5,-40500]`, north-up/unrotated |
| Valid / missing cells | 480000 / 0 |
| Valid minimum / maximum | 19.577999114990234 / 25.29599952697754 m |
| Grid / mask comparison | Raw and Standard exactly equal |
| Valid sample comparison | All valid Float32 samples exactly equal; maximum absolute difference **0 m** |
| NoData declaration | Original `1.701410009187828e38`; Standard **-9999.0** |

NoData declaration normalization was verified. Because this original tile has
zero missing cells, actual missing-pixel replacement is **not exercised** by
this real-data run; a vacuously true mask check does not establish that case.

## 7. Local evidence inventory and document-preparation checks

The evidence directory retains the following local-only files. They are not
Git attachments; hashes allow an authorized reviewer with access to the local
files to check the precise evidence used here. Hashes alone do not make the
uncommitted evidence publicly retrievable or establish independent custody.

| Local evidence filename | SHA-256 |
|---|---|
| `RESULTS.md` | `577d994308dbd0b379b348a156f324286c711f8c608b9258d4de4d64b0f50b5b` |
| `input-verification.json` | `096a2507a78e81fbf41e23ebe98d2664dba2a79549e2807b8d792c1db23003a2` |
| `preflight.json` | `d52f0ae773209c3ec49cb7244f465b3e726bef9a1c24e72c23ee9faa76572350` |
| `execution.json` | `7946346684c9f9cb5d0d491343d647be139bea7cd8067355e2bab39a2789efbf` |
| `execution.log` | `3ffe2a78a58a407e6dbddcc39b5ec31dfd7528ff339c79a6e05bd5170613b4bb` |
| `independent-verification.json` | `701182f6a88f7d4333a6839c96bd895630adc586405874bb64359a9c83643eca` |
| `manifest-cross-check.json` | `4e77203d164d7c67ae6e531081a8918bb56b8bde9056a74a203f0685d61164d0` |
| `verify_run.py` (local verification, not transformation implementation) | `c0f8bc9d7b4937ef25c36e0549a23c9f156f66559f9bc4f2b4a1253e6aeb2481` |

During document preparation, retained artifact/evidence hashes were rechecked
against these records; ZIP member CRC/hash, manifest lineage, all valid samples,
masks/grid and vertical provenance were read again. Recorded execution identities,
test summary and protected-file fingerprints were also checked. This read-only
recheck passed; it is distinct from the earlier generation and does not imply
a new committed-code execution or another full pytest run.

## 8. Proposed decision, relationship and limits

**Proposed technical verdict: PASS.** The public original matches A2's source
fingerprint; the regenerated Standard matches A2's output fingerprint; separate
numeric/grid/mask and provenance checks pass. There is no unresolved byte or
numeric mismatch for this identified run.

**Formal acceptance approval: pending independent review.** This document
records evidence and a proposed verdict, not automatic approval. The existing
A2 ACCEPTED decision remains scoped to its original record, and the source
correction remains an additive clarification. Neither is rewritten or expanded.

Not established by this record:

- independent survey/benchmark validation of vertical accuracy, or a `verified`
  upgrade from source-declared T.P.;
- actual missing-pixel replacement on this zero-NoData real tile;
- general reproducibility across other datasets, tiles, environments, library
  versions or future provider revisions;
- exact measurement date/version for this tile or a frozen live catalogue;
- byte identity between the earlier A3 input and the A2 output, downstream
  environmental validity, or any Building/Canopy/Adapter acceptance.

No old manifest/data or conversion implementation was modified. This formal
record PR includes only this Markdown document; no Raw, TIFF, local JSON,
runtime snapshot or execution log is added to Git.
