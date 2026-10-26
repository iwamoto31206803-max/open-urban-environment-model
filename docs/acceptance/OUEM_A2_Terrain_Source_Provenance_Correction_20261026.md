# Komae Terrain source provenance correction — 2026-10-26

Record type: **dated additive source correction**, supplementing the
[formal A2 acceptance record of 2026-10-06](OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md).
This is not a new acceptance decision or a report of a new Standard rerun.
The frozen A2 record, [A3 record](OUEM_A3_VoxCity_Komae_Acceptance_20261005.md),
old Raw paths and generated manifests remain unchanged. This correction is
submitted for independent review with its accompanying Draft PR.

## 1. Corrected statements and their history

Earlier [Standard Terrain §3](../OUEM_Standard_Terrain_v0.1.md) described the
Komae source as a Tokyo 23-ku 0.5 m DEM and cited the 2024-10-31 23-ku release.
The old `terrain_komae_local_acceptance.cmd` also defaulted to
`data/raw/terrain/tokyo_23ku_dem_050m/komae/09LD3451.tif` and hard-coded 23-ku
metadata/release text in `--vertical-reference-source`. The work README and
2026-10-25 planning inventory repeated the old storage path. These descriptions
conflated a local historical path/source explanation with the actual public
distribution. The historical folder name does not prove source membership.

The A2 record documents that old invocation/path and the evidence available
at acceptance time. It is preserved as history, not rewritten to imply that
the original operator used the newly established acquisition procedure.
Historical 23-ku links in the Standard document are explicitly labelled as
earlier reasoning, not present distribution evidence for this tile.

## 2. Correct source and byte identity

Provider: **東京都デジタルサービス局 / Tokyo Metropolitan Government, Bureau of
Digital Services**. Distribution: **東京都デジタルツイン実現プロジェクト 多摩地域点群データ**,
**グリッドデータ（0.50m）**, ground-derived DEM tile `09LD3451` (not DSM).

- [Tokyo Tama catalogue](https://catalog.data.metro.tokyo.lg.jp/dataset/t000029d0000000020)
- [G Spatial Information Center dataset](https://www.geospatial.jp/ckan/dataset/tokyopc-tama-2023)
- [0.50 m resource](https://www.geospatial.jp/ckan/dataset/tokyopc-tama-2023/resource/fc69d49b-dd22-43e0-b52e-2fad4da7bcfa)
- [Public original ZIP](https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2023/dig/grd50/09LD3451.zip)
- [Tokyo publication notice, 2023-09-01](https://www.spt.metro.tokyo.lg.jp/tosei/hodohappyo/press/2023/09/01/16.html)
- [Official data-type explanation](https://www.spt.metro.tokyo.lg.jp/tosei/hodohappyo/press/2023/09/01/documents/16_01.pdf)

PR #66's [acquisition evidence](../Terrain_Acquisition_PoC_v0.1.md#separate-real-acquisition-and-native-compatibility-check)
records an actual HTTP 200 acquisition on 2026-10-26 at execution commit
`df0157e71f3d6795787a814fa76c00b70fb474f7`, with clean start/end worktree and
unchanged implementation identities. Its original ZIP contains one root TIFF.
That evidence, rather than a filename match, establishes:

| Artifact | SHA-256 | Relation |
|---|---|---|
| Public `09LD3451.tif`, 1922867 bytes | `c747f2ae2ee30f67da98c1c90961f6a094fa0fca8ba3f15a1131c09783d73824` | Exactly matches the frozen A2 Source SHA-256 |
| Public ZIP, 837282 bytes | `8b54c4cd58e17a6edf86ca7ad9e71672776c90669d116981d1368e871e7c393d` | Matches the investigation ZIP; not the TIFF hash |
| PR #66 acquisition manifest | `ea0c54d798db06274cef95b33c43439924742ea8707fb24a3c1de8e5f0180e9d` | Local evidence identified in the acquisition document |

This correction cites that existing execution; it does not claim another
download or another Standard generation. Local data/JSONs are not committed.
New Raw storage uses `data/raw/terrain/tokyo_tama_dem_050m/komae/<run>/`.
The old `tokyo_23ku_dem_050m` tree is neither renamed nor deleted.

## 3. Spatial and vertical evidence

| Property | Evidence and meaning |
|---|---|
| Horizontal reference | Tama catalogue declares JGD2011 / Plane Rectangular CS IX; actual original inspection reports EPSG:6677 |
| Ground DEM / resolution | Official description says 0.50 m elevation grid made from ground data; original inspection confirms 0.5 × 0.5 m |
| Dimensions / bounds | Original inspection: 800 columns × 600 rows; `[-23600,-40800,-23200,-40500]`, north-up/unrotated; matches A2 |
| Vertical reference | Tama catalogue explicitly declares elevation relative to Tokyo Bay mean sea level; **source-declared T.P. (Tokyo Peil / Tokyo Bay mean sea level)** |
| Original encoding | Float32, source NoData `1.701410009187828e38`; 480000 valid / 0 missing cells in the recorded original |

EPSG:6677 does not supply a vertical datum. The catalogue declaration is not an
OUEM benchmark comparison, independent survey, vertical transformation, offset
or proof of compatibility with every other source. T.P. interpretation retains
the [Tokyo public control point/benchmark explanation](https://www.kensetsu.metro.tokyo.lg.jp/jimusho/tech/04-kijyun/kijyunsetu)
as terminology support; the **Tama catalogue** supplies the tile's source
declaration. No `verified` upgrade or universal T.P. default is introduced.
Original NoData is not Standard's `-9999`; the unchanged Standardizer handles
that normalization while preserving valid elevations and grid.

## 4. Effect on acceptance and current procedure

The frozen A2 PASS / ACCEPTED decision remains limited to its identified bytes
and recorded conditions. This correction improves source identification and
the appropriate vertical-evidence citation. It changes no elevations, grid,
CRS, NoData contract or accepted output, and does not automatically revalidate
any previous acceptance result. The historical Standard output hash remains
`0afb6d1706b97bd39c8c93ff8feb580094fe585f567e2de1f2081c082602f90a`.
Exact A2-to-A3 input byte identity was not established and remains unestablished.

The updated helper requires an explicit original path and fresh run directory;
its Tama source evidence is fixed for the hash-pinned tile. `--check` only
inspects and prints a plan. Execution without `--check` calls the unchanged
Native/Standard CLIs into that new directory and reports pending review, not
formal acceptance. The [work procedure](../../scripts/work/README.md#komae-terrain-local-acceptance)
separates acquisition, Native registration, Standard generation and a later
human acceptance decision. No old manifest is patched in place.

## 5. Limits and remaining reproducibility work

- Exact tile measurement date/version and treatment of future elevation-reference
  revisions remain unconfirmed; measurement period and object timestamps are
  not interchangeable. Public URLs can change.
- Source-declared T.P. remains a provider statement. No independent vertical
  accuracy or ecological/downstream suitability was validated by this correction.
- The acquisition manifest links source/licence/terms evidence; it does not
  freeze live catalogue content. See the acquisition document for CC BY 4.0,
  attribution and distribution terms.
- The earlier planning inventory remains a dated snapshot; its old Raw path is
  historical and superseded for new acquisitions by this correction/procedure.
- A future authorized Standard rerun must capture commit/dirty state, environment,
  Raw/Native/Standard identities, corrected provenance, grid/elevation checks and
  output hashes in a **new** record. Compare the historical Standard hash and
  investigate differences; do not force equality or rewrite prior evidence.
- This PR performs no real-data Standard regeneration or formal re-acceptance.
  Read-only Windows preflight and synthetic tests do not replace that work.

## 6. Correction implementation validation (2026-10-26)

Base inspected: latest main `ce238ff16f35d8d173bcb2b6d0d323a08b637bb9`
(PR #66 merge). Source diffs confirm no changes to Native/Standard Terrain
conversion, acquisition, Building/Canopy/Adapter implementation or frozen
A2/A3 records. Only the existing helper-source-citation assertion was updated
in the Terrain tests; algorithm tests and their expectations remain intact.

Windows ordinary OUEM venv: Python 3.11.9, Rasterio 1.4.4 / GDAL 3.10.3.

- Related tests: `.venv\Scripts\python.exe -m pytest -q tests/test_terrain_local_acceptance.py tests/test_standard_terrain.py tests/test_tokyo_tama_dem_acquisition.py`
  — **64 passed, 8 warnings**, 7.25 s.
- Full regression: `.venv\Scripts\python.exe -m pytest -q -rs`
  — **526 passed, 5 skipped, 243 warnings**, 152.50 s, exit 0.
  All five skips concern unavailable Windows symlink creation privileges;
  warnings are existing Rasterio/Affine `PendingDeprecationWarning`.
  No privilege setting, skip condition or existing algorithm was changed.
- Windows CMD preflight on the candidate working-tree implementation used:

```bat
scripts\work\terrain_komae_local_acceptance.cmd "data\raw\terrain\tokyo_tama_dem_050m\komae\acquisition-20261026-01\09LD3451.tif" --run-dir "data\work\terrain-local-acceptance\source-correction-check-20261026" --check
```

It returned exit 0 / `READY_FOR_LOCAL_PROCESSING_NOT_ACCEPTED`. Source hash
before/after equalled the A2 original above; the pinned raster checks passed;
planned Native CLI arguments contained the Tama catalogue citation and
source-declared T.P. The specified run directory did not exist before or after.
The planned pytest/Native/Standard commands were **not executed by preflight**.
No new download, Native registration, Standard generation or acceptance run
was performed for this correction. Synthetic regression tests generate only
their temporary fixtures and do not establish real-data re-acceptance.
