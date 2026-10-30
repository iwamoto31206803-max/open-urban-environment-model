# Real Komae source-H Building experiment

This opt-in Windows experiment uses the existing fixed Converter and experimental
source-H Native → Standard → Consumer path. Results are in [RESULTS.md](RESULTS.md).
It adds no VoxCity, canopy or solar processing and changes no acceptance or gate.

The separate [four-mesh representative-height PoC](FOUR_MESH_REPRESENTATIVE_HEIGHT_POC.md)
uses `python -m ouem.komae_four_mesh_poc` for the full 400 × 300 m AOI and
exploratory VoxCity execution. The original two-member procedure below retains
its scope and does not execute VoxCity.

Run from an ordinary terminal at the repository root with the OUEM venv. The
artifact root is the common ancestor of the repository and fixed binary; the
output must be a new directory with an existing parent. Preserve failed runs.

```powershell
.venv\Scripts\python.exe -m ouem.real_komae_source_h `
  --artifact-root C:/dev `
  --run-dir data/work/real-komae-source-h/<new-run-id> `
  --zip data/raw/building/plateau_komae/2025_v5_api/13219_komae-shi_pref_2025_citygml_1_op.zip `
  --converter C:/dev/plateau-gis-converter/target/x86_64-pc-windows-msvc/release-lto/nusamai.exe `
  --terrain data/work/terrain-reproducibility/komae-20261026-01/generated/standard.tif `
  --study-area config/study_areas/komae_09LD3451.yaml
```

Only the two requested members and their codelists are extracted, retaining ZIP
relative paths. The binary SHA-256 must match the previously fixed build.
Converter arguments are `--sink gpkg --epsg 6697 -t use_lod=lod2`.
Native verifies exact Raw/Converter faces, rings, XYZ and IDs, then preserves
Converter geometry BLOBs. Standard transforms XY from EPSG:6668 to EPSG:6677
without passing H to PROJ. No EPSG:4979 or vertical adjustment is used.

Local ignored outputs include extracted members, Converter GPKG/logs/run receipt,
source evidence and ZIP fingerprint, plan, Native and Standard GPKGs/manifests/
receipts, Consumer results and per-building Terrain diagnostics in `report.json`,
and a short `RESULTS.md`. Completed processing remains experimental. Failures
retain partial files and a FAILED report; fresh runs are required for retries.

Terrain statistics use finite existing DEM cells touched by the complete XY
surface geometry, without geometry repair or raster resampling. Boundary
buildings have partial DEM coverage explicitly flagged. This diagnostic mean is
not a VoxCity effective-ground estimate. The 3 m bottom-offset review flag is
exploratory, not a formal acceptance tolerance. Source-declared height semantics
and numerical agreement do not independently verify survey accuracy or datum
realization. Review any flagged buildings before downstream use.
