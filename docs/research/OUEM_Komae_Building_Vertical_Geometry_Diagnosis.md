# Komae building vertical-geometry diagnosis (pending local evidence)

**Status:** UNRESOLVED. This is an implementation and evidence-path review, not
a Komae real-data result or acceptance record. The developer-local CityGML,
Converter GeoPackage, Native/Standard GeoPackages, and integration run are not
available in Codex Cloud. No geometry or height-generation code was changed.

## 1. Target and reported observations

The reported target has PLATEAU `gml:id` beginning `bldg_5f2d3f6c-`, a
`measuredHeight` of 4.4 m, and at least one CityGML vertex near 24.44 m. The
reported Standard Building `z_min` is about 61.70 m; Adapter
`ground_eff_abs` is about 24.76 m and derived `height` about 39.41 m. The
Adapter formula implies `z_top_abs` of about 64.17 m. The **full** CityGML
Z range and matching Converter/Native Z range have not been measured here;
24.44 m is only one observed vertex. The earlier local DEM diagnosis reportedly
found no selected 0 m or NoData cells for this building; its report was not
available for independent review here.

## 2. Verified implementation path

| Stage | Code or contract | Observed implementation behavior |
| --- | --- | --- |
| CityGML | `docs/OUEM_Standard_Building_v0.1.md`, §3 | PLATEAU source profile declares EPSG:6697 and absolute T.P.-interpreted Z. EPSG:6697's formal third axis is gravity-related height. The actual file must be checked. |
| Converter | `scripts/work/plateau_komae_local_acceptance.cmd`, `src/ouem/native/building/plateau.py` | PLATEAU GIS Converter is a **manual external step**. OUEM does not implement or record its CityGML-to-GeoPackage coordinate operation. Its output's recorded CRS is EPSG:4979, whose formal third axis is ellipsoidal height; the OUEM contract instead treats retained Z as T.P. The actual numerical operation is unknown. |
| Native ingest | `src/ouem/native/building/_plateau_gdal_worker.py` (`_ingest`) | Copies Converter geometries and attributes to Native without a coordinate transformation. It checks presence of Z, geometry type, count and CRS, but not every source/output Z numerically. |
| Standard | `src/ouem/standardize/building/_gdal_worker.py` (`_horizontal_transform`, `_restore_z`, `_run`) | Uses the horizontal EPSG:4326 component of Native EPSG:4979 to reach EPSG:6677, restores each input Z, and checks the original and written values within `1e-9` m. `id` maps to `source_id`; `ouem_id` is deterministic. `measuredHeight` is copied as `measured_height`. |
| Adapter | `src/ouem/adapters/voxcity/__init__.py` (`derive_attributes`, `_run_voxcity_grids`) | `z_top_abs` is the maximum **all-surface Standard vertex Z**. `ground_eff_abs` is the mean of pinned VoxCity DEM cells assigned to the building ID. `height = z_top_abs - ground_eff_abs`. `measured_height` and the geometry minimum do not set height. `min_height` is 0.0. |

EPSG axis metadata and GIS array order must be distinguished. EPSG:6697 and
4979 formally list latitude, longitude, then height; EPSG:6677 formally lists
northing then easting. The Standardizer explicitly requests traditional GIS
XY order for its **horizontal-only** transform and restores Z. Its check
cannot verify what the external Converter did before Native ingest.

The approximately 37 m gap between the one reported CityGML vertex and
Standard `z_min` makes an unintended gravity-related-to-ellipsoidal height
conversion at the manual Converter boundary a **specific hypothesis**. It is
not established: those figures are not a matched vertex pair, and the source
maximum, source layer CRS, Converter output coordinates, and Converter
settings have not yet been inspected. Another possibility is that the full
CityGML geometry already contains high-Z surfaces or a different LoD/feature
than the inspected vertex. DEM zero-fill is less supported by the user's
reported local observation, but the saved DEM evidence still needs linkage.

## 3. Reproducible local diagnosis

On the company PC, from the repository root in an ordinary Windows terminal,
use the merged diagnostic code with the original local files present:

```cmd
.venv\Scripts\python.exe -m ouem.komae_vertical_provenance komae-canopy-002 bldg_5f2d3f6c --citygml data\raw\building\plateau_komae\53393465_bldg_6697_op.gml --output-base data\work\vertical-diagnostics
```

Use a run ID that actually contains the target. The source-ID prefix must
resolve to exactly one Standard `source_id`, equal the CityGML `gml:id`, and
reproduce its `ouem_id`. If the target was not in this run, choose the
appropriate saved integration run; do not rerun A1/A2/A3 to make a diagnosis.
The tool selects the target, a low and a higher valid `measured_height`
representative, and a `-9999` representative if present. Additional exact
IDs can be passed with `--extra-source-id ID`.
The supplied CityGML tile must contain the primary target. A representative
may come from another tile; its unavailable CityGML geometry is reported as
`NOT_CHECKED` with a reason and does not change a complete target's CLI exit
status. Missing target evidence, failed input integrity, or inconsistent target
repeats still block diagnosis (exit code 2). The report gives separate
`target_completeness` and `representatives_completeness` results.

It creates a **new**, independent ignored directory with `diagnosis.json` and
`summary.md`, or prints JSON without creating a file if `--output-base` is
omitted. It reads the existing report and hash-bound manifests, validates
Native/Standard/Adapter ID lineage in both repeats, streams *all* `gml:pos`
and `gml:posList` coordinates of the selected Building elements, and compares
full vertex Z counts, extrema, and sorted-value hashes across stages. Unknown
coordinate encodings, mixed/missing CRS, XLinks, missing target IDs, or modified
inputs block diagnosis; unavailable optional representative geometry is
explicitly `NOT_CHECKED`. The Converter GeoPackage comes
from the recorded Native manifest, not from a guessed filename. CityGML is an
explicit input: the manual Converter receipt does **not** record the CityGML
SHA-256, so that file-to-Converter provenance needs independent review.

For independent DEM and NoData replay against the saved A3 array hashes, also
run the existing `scripts\work\diagnose_komae_building_heights.cmd` helper
against the same run ID and compare `ouem_id`, `voxcity_id`,
`ground_eff_abs`, source-pixel NoData/zero counts, and derived height. The new
report includes the Adapter's saved ground mean, min/max and sample count;
it does not claim a second DEM replay.

## 4. Decision and repair candidates

If the frozen integration run has a byte mismatch, the strict diagnostic
correctly blocks. The separate `ouem.komae_vertical_exploratory` mode can read
the current CityGML, Converter, Native, full A1 Standard and saved Adapter
evidence without changing them. It lists every inspected byte mismatch and
compares the full A1 XYZ geometry and contract fields with the report's saved
semantic digest and the second repeat. Any changed artifact makes its Z trace
**exploratory**, not provenance-verified or accepted. A matching digest does
not establish that `z_min` was the only edit; GeoPackage metadata and other
untracked fields may differ. Divergent geometry or lineage is reported
explicitly, and the cause remains unresolved until source/Converter coordinate
pairs and conversion settings are reviewed. This mode does not change the
strict workflow or its acceptance criteria.

The report separates `transition_status` (observed numerical extrema change
and its first interval) from `root_cause_status` (whether the height anomaly's
mechanism is established). The legacy `classification.level=CONFIRMED` applies
**only** to a numerical transition between checked saved stages; the root cause
remains `UNRESOLVED`. CityGML-to-Converter changes have at most `LIKELY`
transition evidence without independent proof that the supplied CityGML
produced the recorded Converter GeoPackage. A complete target diagnosis can
therefore exit successfully while root cause remains unresolved.

Vertex counts and sorted-Z multiset hashes remain useful evidence, but a
difference alone does not prove an incorrect vertical transformation:
deduplication or reconstruction can change them. Pure vertex reordering does
not change the sorted hash, although it prevents positional comparison by
vertex index. The suspected approximately 37 m shift is still a hypothesis
until comparable source and Converter coordinates, source-file identity, and
the Converter's transformation settings are verified.

If the complete CityGML Z values are near the DEM and the Converter Z values
are shifted, obtain the actual Converter CRS/vertical-operation settings and
source-file provenance. A separate reviewed fix could preserve the declared
source vertical ordinate through conversion, or perform an explicitly
documented datum operation and retain the correct CRS/vertical semantics.
Do **not** subtract an assumed constant, relabel EPSG:4979, or replace heights
with `measuredHeight` from this report. If CityGML itself has high roof Z,
inspect the full CityGML Building/BuildingPart, LoD and measured-height meaning
before changing the Adapter formula.

Any later fix needs synthetic regression tests for horizontal versus vertical
transforms, full-vertex Z preservation, `-9999` handling, ID mapping, and the
existing A1/A2/A3 quality gates. It also needs a **new**, isolated local
CityGML→Converter→Native→Standard→Adapter run against frozen inputs; compare
several representative buildings to independent ground and roof evidence,
verify both repeats and all hashes, inspect QGIS 3D placement, and record a
separate formal acceptance decision. Existing accepted artifacts and records
must remain untouched.
