# Tokyo Tama Terrain Acquisition PoC v0.1

Status: experimental acquisition of **one original tile only**. Raw completion
is not Native registration, Standard regeneration, formal A2 re-acceptance,
VoxCity integration, or acceptance of other tiles. No accepted implementation,
contract, or acceptance record is changed by this PR.

## Source and licence

- Provider: Tokyo Metropolitan Government, Bureau of Digital Services.
- Dataset: 東京都デジタルツイン実現プロジェクト 多摩地域点群データ,
  グリッドデータ（0.50m）, ground-derived DEM, **not DSM**.
- [Tokyo catalogue](https://catalog.data.metro.tokyo.lg.jp/dataset/t000029d0000000020),
  [G Spatial Information Center](https://www.geospatial.jp/ckan/dataset/tokyopc-tama-2023),
  [0.50 m resource](https://www.geospatial.jp/ckan/dataset/tokyopc-tama-2023/resource/fc69d49b-dd22-43e0-b52e-2fad4da7bcfa).
- [Original ZIP](https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2023/dig/grd50/09LD3451.zip).
- [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) is explicitly declared
  by the Tokyo catalogue. Retain provider attribution and source/licence links;
  identify processing when distributing derivatives. Suggested credit:
  “Tokyo Metropolitan Government, Tokyo Digital Twin Tama point cloud dataset,
  ground grid 0.50 m, CC BY 4.0”. Acquired ZIP/TIFF bytes are unchanged.
- [Distribution terms](https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2023/dig/doc/license.pdf)
  must also be reviewed. The distribution page treats downloading as agreement.
  Reviewed terms describe disclaimers/prohibited conduct; no express prohibition
  on this single-object automated retrieval was found. This does not establish
  permission or operating limits for bulk/parallel crawling. No such mode exists.

The catalogue declares JGD2011 / Japan Plane Rectangular CS IX and elevation
relative to Tokyo Bay mean sea level. Record **source-declared T.P.**, not
independently verified vertical accuracy. EPSG:6677 is horizontal only. The TIFF
does not itself establish its vertical semantics. These are fixed, previously
reviewed source declarations and links, not a new live semantic verification on
each run. The manifest neither authenticates every statement nor accepts data
scientifically. The implementation does not fetch or snapshot the catalogues.

Dataset metadata gives measurement July 2022–January 2023, and the official
[release](https://www.spt.metro.tokyo.lg.jp/tosei/hodohappyo/press/2023/09/01/16.html)
announces publication on 2023-09-01. Exact measurement date for this tile,
version identifiers and treatment of subsequent elevation-reference revisions
remain unconfirmed. The G Spatial catalogue notes GeoTIFF header updates;
object/member timestamps are not measurement dates.

## Windows usage

Use the repository venv from ordinary PowerShell, following the existing
[workstation record](development/OUEM_Windows_Development_and_Remote_Setup_20261025.md)
and [runtime boundary](architecture.md). No new dependency is needed. Read the
source terms above before downloading. Choose a **new** run directory:

```powershell
.venv\Scripts\python.exe -m ouem.acquire.tokyo_tama_dem `
  --raw-dir data/raw/terrain/tokyo_tama_dem_050m/komae/run-20261026-01 `
  --timeout 60 --max-bytes 10000000
```

The URL, member, source profile and expected TIFF hash are fixed. There is no
alternate tile/URL/hash switch. `--timeout` is the socket timeout and an elapsed
budget checked between read operations; a blocked read may take its socket
timeout, so this is not an exact total wall-clock deadline. Streamed bytes are
bounded even without Content-Length; declared lengths and truncation are checked.
Unexpected final redirect URLs/statuses are rejected. No retries or concurrency.

Default download cap is 10 MB; expanded TIFF cap is 4 MB. ZIP must contain
exactly the regular, unencrypted root member `09LD3451.tif`. Extra/duplicate
entries, directories, alternate paths, symlinks and oversized members fail.
The program never calls `extractall`: it copies only the validated member into
a fixed staged filename. Full member reads verify CRC. SHA-256 is computed on
the **decompressed original TIFF bytes**, not the ZIP, then existing read-only
`ouem.native.terrain.inspect_dem` and tile-specific structural checks run.

Required original profile: EPSG:6677, Float32, one band, 800 columns × 600 rows,
0.5 m, bounds `[-23600,-40800,-23200,-40500]`, affine
`[0.5,0,-23600,0,-0.5,-40500]`, identity scale/offset, finite declared source
NoData `1.701410009187828e38`, 480000 valid cells / zero missing cells.
This is the identified original's profile, not a universal Terrain contract.
Source NoData is **not** changed to Standard's `-9999` during acquisition.

Original TIFF SHA-256, pinned to the [A2 record](acceptance/OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md):

```text
c747f2ae2ee30f67da98c1c90961f6a094fa0fca8ba3f15a1131c09783d73824
```

Survey ZIP SHA-256:

```text
8b54c4cd58e17a6edf86ca7ad9e71672776c90669d116981d1368e871e7c393d
```

The TIFF hash is a mandatory identity gate. A mismatch records a different-version
candidate in FAILED evidence and stops; no candidate TIFF becomes a completed
Raw artifact. ZIP hash is recorded and compared, but is not a mandatory gate:
a repacked ZIP with identical validated TIFF bytes may complete with
`matches_survey_zip=false`. Review that difference; never claim ZIP byte identity.

## Raw publication and failure contract

The new directory contains, on success:

```text
09LD3451.zip
09LD3451.tif
acquisition-manifest.json
```

Use the new `tokyo_tama_dem_050m` tree. The historical `tokyo_23ku_dem_050m` tree
is neither migrated nor deleted; explicitly targeting that named tree is refused.
Any existing run directory (even empty) is refused before network access.

The process reserves a fresh directory and downloads/extracts into `.staging-*`.
Unvalidated bytes there are intermediate files, not completed Raw artifacts.
Only after all hash/metadata checks and closed readers/writers does it publish
same-filesystem `os.link` names without replacement, manifest last. A consumer
must require a COMPLETED manifest, matching ZIP/TIFF hashes, and absence of a
FAILED record or staging directory. A FAILED record overrides a residual success
manifest after incomplete rollback. Native registration, Standard generation,
or formal acceptance must not be inferred from the completion flag.

Hard links preserve verified bytes and refuse competing names. This follows the
local Windows NTFS publication approach in the existing acquisition PoCs; it
is not guaranteed on FAT/exFAT, arbitrary network shares, restrictive ACLs,
security software, or sandboxed environments. There is no copying/replace
fallback that could expose partially written final files or clobber a target.
Stage and final paths reside in the same run directory; GDAL handles close
before linking. This is a single-writer workflow, not protection against a
hostile concurrent process replacing files after publication.

On exceptions, staging cleanup is attempted and every final link created by
this run is targeted for rollback, in reverse order. Competing existing files
are not rollback targets. `acquisition-failed.json` records FAILED, error,
available hashes/HTTP evidence, candidate flag and retained final paths. It is
not a success manifest. Denied rollback removes neither the error nor the
remaining cleanup attempts. A crash, power loss, cleanup/ACL failure, or disk
failure can leave staging/residual files; quarantining the failed run is required.
FAILED-record write failure is reported on stderr. Do not auto-reuse failed
directories, and do not treat residual TIFFs as a completed acquisition.

Manifest schema `ouem-tokyo-tama-dem-acquisition-poc/v0.1` records source,
attribution/licence/terms/vertical evidence links, run directory, HTTP URL,
status/times/length/ETag/Last-Modified/type, ZIP/TIFF hashes and sizes, member CRC,
source raster metadata, baseline identity and transfer limits. Implementation
start/end capture disk acquisition/Native-inspection module hashes, Git commit
and worktree status (nullable if unavailable), Python/Rasterio/GDAL versions.
Changing code/worktree state during the run blocks completion. A dirty Git HEAD
does not establish committed-code identity. Timestamps/path/runtime records make
the manifest's full bytes nondeterministic; original file hashes identify data.

## Connection to unchanged Native / Standard processing

The generator itself stops at Raw. Synthetic tests separately call existing
`accept_native_terrain` and `load_native_manifest`, verifying source bytes stay
unchanged. For a later reviewed run, use the existing Native CLI with explicit
Tama evidence and a **fresh noncanonical output path**, for example:

```powershell
.venv\Scripts\python.exe -m ouem.native.terrain `
  data/raw/terrain/tokyo_tama_dem_050m/komae/run-20261026-01/09LD3451.tif `
  --output data/work/terrain-acquisition-native-check/new-run/native.json `
  --provider "Tokyo Metropolitan Government, Bureau of Digital Services" `
  --source-dataset "Tokyo Digital Twin Tama ground grid 0.50 m / 09LD3451" `
  --vertical-reference-status source-declared `
  --vertical-reference "T.P. (Tokyo Peil / Tokyo Bay mean sea level)" `
  --vertical-reference-source "Tokyo Metropolitan Government Tama dataset: elevation = Tokyo Bay mean sea level; https://catalog.data.metro.tokyo.lg.jp/dataset/t000029d0000000020"
```

Native writes a registration manifest referencing Raw and rechecks its hash and
structure when loaded. Its CLI does not promise no-overwrite outputs: the
operator must select fresh paths. Acquisition does not invoke or wrap it.
Future Standard generation should call the unchanged `ouem.standardize.terrain`
with that Native manifest and the existing study-area YAML, retaining the
0.5 m grid/elevations. It is outside this PR's execution scope.

## Additive source clarification and outstanding correction plan (2026-10-26)

The public **Tama** TIFF exactly matches the original SHA in the frozen A2
record. Tokyo's Tama catalogue supplies the appropriate Tokyo Bay mean sea
level declaration. This clarifies geographic/source provenance; it neither
changes accepted bytes nor independently verifies elevations.

| Owning location (unchanged here) | Follow-up requiring review |
|---|---|
| `docs/OUEM_Standard_Terrain_v0.1.md` §3 | Add a dated clarification linking Tama source/hash evidence and distinguish the historical 23-ku explanation. Do not silently rewrite the old account or change the contract. |
| `scripts/work/terrain_komae_local_acceptance.cmd` default path and fixed vertical-source argument | In a separate reviewed change, accept explicit source provenance / use Tama default for new runs; retain historical invocation information. Path override alone does not correct the fixed 23-ku citation. |
| `scripts/work/README.md` Terrain instructions | Document new acquisition path and revised helper procedure once approved. |
| Planning acquisition/reproducibility inventory's old Raw path | Add a dated source correction referencing the original inventory and this clarification; preserve its historical context. |
| Formal A2 record and old generated manifests/Raw paths | Preserve unchanged. Add a separate dated correction/addendum referencing the frozen record, matching original hash, catalogue evidence and limitations. Do not overwrite old manifests or rename/delete old data. |

This document is an additive acquisition-level clarification and correction
plan, **not a newly approved formal acceptance addendum**. A future re-acceptance
must capture new execution commit/dirty state, source/licence evidence, Native
and Standard manifests, input/output hashes, grid/elevation checks and environment
in a new record. Compare Standard output against the historical
`0afb6d1706b97bd39c8c93ff8feb580094fe585f567e2de1f2081c082602f90a`;
investigate differences rather than changing old records or forcing byte identity.
No A3-input byte identity or downstream validation follows automatically.

## Validation evidence

Offline tests: `.venv\Scripts\python.exe -m pytest -q tests/test_tokyo_tama_dem_acquisition.py`.
They use generated Float32 DEMs and synthetic ZIPs with the production TIFF hash
monkeypatched **only in tests**. No CLI hash override or network-dependent unit
test exists. They establish control-flow/profile validation, not real acceptance.

Windows ordinary OUEM venv results on 2026-10-26: focused **44 passed**, no warnings,
6.02 s; full `.venv\Scripts\python.exe -m pytest -q`: **515 passed, 5 skipped,
243 warnings**, 164.74 s, exit 0. Warnings are Rasterio/Affine
`PendingDeprecationWarning`. No skip condition or existing test was changed.
Hard-link publication and rollback succeeded on this local Windows filesystem;
unsupported/denied storage remains an explicit limitation, not a portability claim.

### Separate real acquisition and Native compatibility check

On 2026-10-26, the usage command above was executed with
`--raw-dir data/raw/terrain/tokyo_tama_dem_050m/komae/acquisition-20261026-01`.
Run commit: `df0157e71f3d6795787a814fa76c00b70fb474f7`; acquisition and Native
check start/end Git status both empty; implementation identities unchanged.
Environment: Windows, OUEM Python 3.11.9, Rasterio 1.4.4 / GDAL 3.10.3.
The acquisition command ran with individual approval outside the network-restricted
Codex sandbox; this does not establish connectivity within that sandbox.

Result: **Raw acquisition COMPLETED**, HTTP 200, 837282 bytes ZIP / 1922867 bytes
TIFF. ZIP hash matches the survey ZIP above; TIFF hash exactly matches the
formal A2 original above. Metadata matches the pinned profile, 480000 valid /
0 missing cells, min/max `19.577999114990234` / `25.29599952697754` m.
HTTP acquired time: `2026-10-26T01:49:49.559040+00:00`; ETag
`7679bf8552f7b91a3bb25959c5b81a02`; Last-Modified `2023-10-02 07:52:31 UTC`.
No `.staging-*` directory or FAILED record remained. These results establish
this acquisition and identity check, not independent accuracy or new acceptance.

The unchanged `accept_native_terrain` API then registered this Raw TIFF to the
fresh local path
`data/work/terrain-acquisition-native-check/acquisition-20261026-01/native.json`;
`load_native_manifest` revalidated it. Result **PASS**; TIFF hashes before/after
equal the accepted original. The check used Tama source-declared T.P. evidence,
and left canonical Native/Standard artifacts untouched. A separate local
`native-compatibility-check.json` records the source/Native/record hashes and
execution identity. No acquisition record was overwritten by the Native check.

| Evidence | SHA-256 |
|---|---|
| Acquisition module disk bytes at execution | `2e424ac0e2977551495ee97461b6fa672323f590b6b130114b399723b6770705` |
| Existing Native inspection module disk bytes | `79abb3cde477f4561e6df64b07979a2a85be5ce7d724aa553db1e13f910c14fd` |
| Raw acquisition manifest | `ea0c54d798db06274cef95b33c43439924742ea8707fb24a3c1de8e5f0180e9d` |
| Separate Native compatibility manifest | `dff97a78dd111d240ba9bbc7af2a74f5c3b9d8aa7292d4f7792f468f4853aef9` |

Git revision and disk hashes are separate evidence (Git line-ending conversion
can differ from on-disk bytes). The subsequent documentation-only evidence
commit does not change the code used for these runs. Raw data, generated JSONs,
and runtime artifacts remain local/ignored and are not PR contents.
**Standard regeneration and formal re-acceptance were not performed.**
