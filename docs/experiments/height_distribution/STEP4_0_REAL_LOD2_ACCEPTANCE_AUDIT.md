# STEP 4-0 — Real PLATEAU LoD2 Roof Geometry Acceptance Audit

2026-11-06. Main baseline **3db0154d6d008f5d2f5487910beabea14b46f313**
(PR #164 merged). **Read-only / EXPERIMENTAL**; this is not Formal Acceptance.

| Question | Executed result |
|---|---|
| Audit code and independent tests | Technical PASS; focused 44 passed |
| Real data present and audited? | **EXECUTED / AUDIT_COMPLETED**; saved Raw→Native→Standard and T5 identities rechecked |
| STEP 4-A eligibility | **0 ELIGIBLE, 32 CONDITIONAL, 0 per-building BLOCKED**; unrestricted transition **BLOCKED_PENDING_INPUT_CONDITIONS** |

`terrain_integration_ready=false`, `scientific_validation=NOT_VERIFIED`,
`formal_acceptance=NOT_VERIFIED`. No height-distribution Derived, voxelization,
Solar/Shadow or GVI was generated/executed by this audit. The unchanged CI gate
still runs its existing synthetic regression suite.

## Scope and owners

Reviewed [Concept v0.2](../../OUEM_Concept_Architecture_v0.2.md),
[H0 audit](../../planning/OUEM_H0_Height_Distribution_Design_Audit_v0.1.md),
[STEP 3-A](STEP3A_SYNTHETIC_HEIGHT_DISTRIBUTION.md),
[3-B](STEP3B_SYNTHETIC_VOXELIZATION.md),
[3-C](STEP3C_SYNTHETIC_SOLAR_SHADOW.md) and their implementations. Geometry
acceptance here is checked against the unchanged STEP 3-A planar-polygon
validator, without calling `derive`, Voxelizer or any environmental kernel.

Reviewed [Raw selector](../../../src/ouem/mixed_lod_selector.py),
[saved Converter bridge](../../../src/ouem/mixed_lod_converter_bridge.py),
[Native](../../../src/ouem/native/building/mixed_lod.py),
[Standard](../../../src/ouem/standardize/building/mixed_lod.py),
[independent Consumer](../../../src/ouem/consumers/mixed_lod.py) and Candidate B
T5 report/input references. [New auditor](../../../src/ouem/lod2_roof_audit.py)
reuses the Consumer's **read-only** provenance/selection/converter-output/
Native/Standard checks. `converter_passes` reads saved GeoPackages; it does
not invoke the Converter. SQLite uses `mode=ro&immutable=1`, query-only mode,
with live WAL/SHM/journal inputs rejected. XML/ZIP/raster inputs are opened for
reading only. No original file or existing cache is written.

## Discovered identity chain

Paths below are relative to `C:/dev/open-urban-environment-model`, except the
Converter executable. The report retains all **41** input identities and
same-API stat/SHA comparisons before/after the run, including supporting code,
T5 provenance inputs and acquisition record. IDs/LoDs are checked from actual
saved rows, not accepted from narrative counts.

| Artifact | SHA256 |
|---|---|
| `data/work/terrain-candidate-b/t5-23-02/report.json` | `1a4c3ed60bebcb92b00f5a28dbb52ceea78fd4b9eb4893cb87445dc17080695f` |
| `data/raw/building/plateau_komae/2025_v5_api/13219_komae-shi_pref_2025_citygml_1_op.zip` | `659fe9f96eb8a45b57e788b52d6e80edef154ddc3aa9b4f2c1ea117c61a5a555` |
| ZIP member `udx/bldg/53393466_bldg_6697_op.gml`, 199,626,757 bytes | `6128aa2a2bd637e51dbef89ee42bd54620eae6a2fab82b082149a4dc4924c0c9` |
| Adjacent Raw `acquisition-manifest.json` | `4322fbce9d084acdd51a5995a758df5426658d2fe6c498345f7220bd7e2f019d` |
| `data/work/mixed-lod-selector/run-pr136-rereview-01/manifest.json` | `eea7a117658208018fb0e12d212f7e63a6fef69a0c86c1265fd6692fda4b0785` |
| Adjacent `geometries.jsonl` | `51386b7fb5286e18bf5d310e09ddd7c438c92188efcd713fac7222cf3b9485ef` |
| `data/work/mixed-lod-converter-bridge/run-02/bridge.json` | `53e72d051136df1cc9d2c92701243a7f28b7a144123e52ba50ab81cff6a92900` |
| `data/work/mixed-lod-native/run-02/manifest.json` | `b7e932b9b6da9da98a59ccb6e1acb5a60a1cb7d50ea5c3d5e86782eccbcfc46d` |
| Adjacent `native.gpkg` | `1e2af898307e5f9bfbc4fbc86ab714dfad2557e2371ff98138171eb768ca7da7` |
| `data/work/mixed-lod-standard/run-02/manifest.json` | `9789d443e0286ad0c5da57156d7ba10ed19adafba5e42cec068e9deeead0f789` |
| Adjacent `standard.gpkg` | `954d01aad3004a0d2d69586036ef9961071064a39db4215d45577dee2f996f60` |
| `data/work/mixed-lod-consumer/run-04/receipt.json` | `1f9de8a7bdd7c92fd455f7c3897f45d8280dff05da90634f2aa677a86298e415` |
| `data/work/terrain-candidate-b/t5-23-02/t5-2/terrain.tif` | `ead7545fb2b50aaad9958aa8db647708a8ceba04f719ac6e8400150a17bb36a2` |

The original ZIP is 1,192,172,043 bytes, release `plateau-13219-komae-shi-2025`.
The existing acquisition identifies [MLIT/PLATEAU's exact catalogue asset](https://assets.cms.plateau.reearth.io/assets/6c/9c8c10-16b2-4a21-b971-c9330d4c20f4/13219_komae-shi_pref_2025_citygml_1_op.zip).
No new download occurred. Existing LoD1/LoD2 Converter outputs and executable
identity are checked as provenance, without execution: nusamai 0.1.19, commit
`ce7766df9788ce391b149c55df16d33082d0bc72`, binary SHA
`0195a11df4fd0ef30dcd5578175035a918c41285b1fcc329f3399f5337326f1b`.

The single Raw member contains **3,778** parent buildings. Selection is supported
valid LoD2 when present, otherwise supported LoD1 when LoD2 is absent; invalid
LoD2 is not silently replaced. Raw/selector geometry and decisions are replayed
against the saved member, including the original AOI predicate and no clipping.
Native/Standard contain **63** selected buildings, **31 LoD1 / 32 LoD2**;
T5 source_id/OUEM/LoD and positive numeric ID bijections agree. Original AOI is
`[-22575,-39925,-22475,-39825]`; T5 processing domain
`[-22588,-39938,-22461,-39811]`. This audit's roof population is only those
**32 LoD2 buildings**, not all LoD2 in the ZIP or municipality.

## Roof semantics and correspondence

| Stage | Observed retention / limitation |
|---|---|
| Original CityGML | Direct `bldg:boundedBy` → RoofSurface / WallSurface / GroundSurface → LoD2 MultiSurface → inline Polygon; building, semantic-surface and polygon IDs present |
| Raw selector | `source_id`, selected LoD, branch locators (including semantic ancestry), polygon ID/ordinal, original XYZ and source member |
| Native | Source/OUEM/LoD/provenance and 3D face/ring coordinates in GPKG; `manifest.decisions.raw_polygons` retains Raw IDs/locators externally |
| Standard | XY-only projected 3D faces/rings and building attributes; **no embedded per-face semantic/Raw ID fields or face table**. Manifest references Native provenance, not a per-face semantic schema |
| New audit crosswalk | Unique exact Raw↔Native XYZ/ring identity, followed by independently verified ordered Native↔Standard XY/H correspondence; records each Standard/Native face index and Raw polygon/semantic-surface ID |

For the 32 selected LoD2 buildings the source explicitly declares **429
RoofSurface, 896 WallSurface, 32 GroundSurface = 1,357 faces**. Other boundary
types and undetermined faces: **NOT_FOUND in this population**. All 1,357 face
correspondences are **VERIFIED within these frozen artifacts**, not merely
inferred from order, orientation or locator text.

Raw↔Native matching uses all XYZ IEEE bits, closed rings with cyclic-start/
winding invariance, and hole-ring order invariance. A match requires exactly
one Raw candidate, one Native occurrence and a unique nonmissing Raw polygon
ID. Duplicate/ambiguous/missing candidates retain unknown semantics and block
eligibility. Native↔Standard is checked independently for ordered faces/rings,
bit-identical H and XY against explicit GRS80 zone IX projection within the
existing **1e-7 m** numerical budget (observed maximum **0 m**). No H is sent
through the XY transform. This external crosswalk does not make semantic fields
part of the Standard contract or certify source physical correctness.

All faces are finite and closed. Roofs comprise **385 triangles and 44 polygons
with more vertices**, have valid positive-area XY projections and pass the
unchanged STEP 3-A planar-polygon check (`1e-8 m` numerical tolerance). The
separate SVD plane diagnostic has maximum roof residual
**3.1163852e-10 m**; it does not flatten/repair input. This is numerical geometry
compatibility, not survey accuracy or solid/watertight topology validation.

No exact duplicate faces or ring holes were found. Roof-union holes also:
**NOT_FOUND**. Ground/roof projections of different buildings have no overlaps
above the reported **1e-8 m²** threshold. Within-building roof projected
area-sum minus union reaches **2.337054e-6 m²**. Ground-candidate versus roof
union has maximum uncovered area **2.714317e-6 m²**, maximum outside/overhang
area **2.843822e-6 m²**. These tiny geometric residuals are recorded without
snapping, filling or attributing them to real physical gaps/eaves.

The diagnostic near-vertical threshold is `abs(unit_normal_z)<=1e-3`, not a
roof classifier. **894** WallSurface faces satisfy it; **2 do not**, and remain
WallSurface. Both are in sample M, polygon IDs
`pol_8ef25136-9cb6-4772-9dba-a19c76594307` and
`pol_46e06c08-5e12-4d69-bf01-9442183844fd`, projected areas about .001 m² each.
This directly demonstrates why nonvertical/positive-area faces cannot all be
called roofs. For unlabelled synthetic controls the auditor reports only
`geometric_candidate_only`, never a verified RoofSurface.

## Reproducible sample selection and classification

Category order: simple single flat roof, any sloped roof (> .01 m roof Z
variation and not near-vertical), multiple roof faces, holes/complex ground
outline (>4 exterior vertices), missing/duplicate/ambiguous case. Select first
lexical matching source_id not previously selected, or first matching ID if all
already selected. Candidate lists and NOT_FOUND categories are saved. This gives
four distinct buildings, with **no invented hole/problem sample**.

| Label / category | source_id | ouem_id | Roofs / ground-outline vertices | Classification |
|---|---|---|---:|---|
| F: simple flat | `bldg_09532951-4dab-457d-b1c6-56d509900d1b` | `oub-c56cb020-c11c-5f9c-a37f-73018266a333` | 1 / 4 | CONDITIONAL |
| S: slope | `bldg_040379e5-dffb-40b6-a392-6396158211f5` | `oub-664a9132-cf36-52a5-96f5-577e78c91e59` | 69 / 17 | CONDITIONAL |
| M: multiple roof faces | `bldg_2bd71700-a145-46ff-b14f-ad60394ff253` | `oub-cb250497-c12d-5fcc-9dca-e82c8b051398` | 30 / 14 | CONDITIONAL |
| C: complex outline | `bldg_2d5a9713-b02f-4903-9164-c5653e03494d` | `oub-10894413-4369-5131-ac0d-78ee9d234016` | 12 / 12 | CONDITIONAL |

All refer to the exact ZIP member and corresponding source building/polygon IDs
in the crosswalk. Physical roof completeness cannot be inferred from absence
of chain-loss or duplicate flags; **NOT_FOUND is not certification of completeness**.

| Sample | Ground projection candidate m² | Full-geometry absolute Z min–max m | measured_height m | Geometry minimum − diagnostic DEM m |
|---|---:|---|---:|---:|
| F | 23.263523 | 24.888792–27.085800 | NULL | −.137207 |
| S | 220.130069 | 24.877753–33.684600 | 8.8 | −.154247 |
| M | 97.015700 | 24.607191–32.380000 | 7.8 | −.119808 |
| C | 65.257051 | 24.821855–32.003400 | 7.2 | −.127144 |

All 32 have a valid Polygon **candidate** from semantic GroundSurface XY
projection, independent of RoofSurface projection. This is not an adopted
footprint policy. All 32 remain CONDITIONAL because that policy/boundary
treatment and the building/DEM common vertical basis have not been established.
Malformed geometry, absent verified roof, incomplete/nonunique mapping or no
valid independent footprint would instead be BLOCKED (tested with synthetic
controls). This audit has no path that silently promotes Candidate B's existing
vertical assumptions to ELIGIBLE.

## Vertical evidence and limits

CityGML declares compound EPSG:6697, latitude/longitude/H tuples. Existing
Native retains longitude/latitude/H with source declaration horizontal
EPSG:6668, vertical EPSG:6695, gravity-related height in metres. Standard
transforms only XY to EPSG:6677 (`always_xy`, no ballpark, best operation),
retaining every H **bit-for-bit** and its separate vertical declaration.
That preservation is verified; realization/epoch/physical accuracy are not.

The Candidate B DEM profile retains **T.P. inheritance inferred for ward data**,
not a verified common realization/epoch. Its horizontal EPSG label alone is not
vertical proof. T5's earlier `CONDITIONAL` evidence is not elevated here.
No HAG is VERIFIED. Raster samples are nearest pixels at the GroundSurface
candidate's interior representative point, explicitly a limited numerical
diagnostic, not full-footprint terrain validation or owner-average ground.
Across 32 buildings geometry minimum minus that sample ranges
**−.467880 to +.004483 m**. No Z offset, ground snapping or height correction is
applied. Building geometry Z spans **24.487057–34.077599 m** overall.

Two LoD2 measured heights are NULL; existing Raw sentinel/NULL normalization
is checked, not filled from roof or DEM. Geometry Z span minus measured height
for S/M/C is +.006847/−.027191/−.018455 m. These comparisons do not establish
survey accuracy, ground datum equality, observation epoch or a justified HAG.

## Source and licence declarations

The pinned local acquisition record names PLATEAU/MLIT Komae 2025 v5 and the
exact catalogue asset above. Its historical site-policy review summarizes
PDL1.0-default/CC BY attribution conditions. The **ZIP README itself instead
lists Government Standard Terms v2.0, CC BY 4.0, ODC BY and ODbL as choices**.
This discrepancy is retained, not silently resolved as current legal clearance.
No fresh web/terms review or new data acquisition was performed.

The README links `metadata/udx_13219_2025_resource.csv`, which is **NOT_FOUND**;
actual member is `metadata/udx_13219_2025_resource_op.csv`, read without extraction
or modification. The resource CSV lists building attributes from several
municipal/prefectural/survey sources (including 2022 survey references), which
does not by itself assign an exact roof/vertical epoch to these 32 buildings.
The stored record and original ZIP notices must be reconciled, appropriate
attribution selected and applicable third-party conditions checked before
future distribution/use beyond this audit. Neither licence nor scientific
acceptance is inferred from technical PASS.

README SHA: `c7362427da8af24c1b7d240b577e766058f789c5d6a3da1ca0f6a6f5a9c45497`.
Resource CSV SHA: `31171eabf2297493086189e7aa6518d5e6d374f3a8ea954b337f2d0dfb12fdd8`.
The ignored report preserves both declarations/source references in full.

## Reproduction, tests and STEP 4-A conditions

Windows ordinary terminal, repo cwd, OUEM `.venv/Scripts/python.exe`:
Python 3.11.9, NumPy 2.4.6, Shapely 2.2.0, PyProj 3.7.2, Rasterio 1.4.4.
Existing manifests contain canonical absolute Windows paths, including the
saved Converter executable under `C:/dev`; the artifact root deliberately
covers that read-only provenance dependency. No binary is executed.

```powershell
.venv/Scripts/python.exe -m ouem.lod2_roof_audit --t5-report data/work/terrain-candidate-b/t5-23-02/report.json --artifact-root C:/dev --output-dir data/work/step4-0-roof-audit/audit-final-e
.venv/Scripts/python.exe -m ouem.lod2_roof_audit --t5-report data/work/terrain-candidate-b/t5-23-02/report.json --artifact-root C:/dev --output-dir data/work/step4-0-roof-audit/audit-final-f
.venv/Scripts/python.exe -m pytest -q -ra tests/test_lod2_roof_audit.py tests/test_mixed_lod_consumer.py
```

Both real-data reports/manifests are **byte-identical**; all 41 tracked input
SHA/stat identities remain unchanged. Report SHA
`71de561a0644352654c4d30814259f3d42b1d31a18b9c1591652be88c1b3565e`;
manifest SHA `14498ba34826c2b68c2a22c29da6fcbeb8bc696e20b68f799d8a8cca0a41a852`;
auditor SHA `cf7d498875a9830e57b0db92566e62b3c278d6c6d7681666a1ad71b39bbf9356`.
Generated records remain outside Git, and never overwrite existing runs.

[19 independent new tests](../../../tests/test_lod2_roof_audit.py) cover semantic
vs nonsemantic faces, dimension inheritance, reordered/reversed rings, duplicate/
missing IDs/geometry, missing source faces, holes/vertical/nonplanar/invalid
geometry, selection/NOT_FOUND, HAG/eligibility limits, source immutability,
missing files/SHA mismatch, population bijection and failed publication.
Focused result: **44 passed, no skips/warnings, 12.08 s**. Full local pytest is
not run. Existing Windows/Ubuntu full CI, pip cache, `--durations=30` and all
prior assertions remain the acceptance gate; completed CI evidence is in the PR.

If files are unavailable elsewhere, restore the **existing saved snapshots**
listed above, verify every SHA and canonical manifest reference, then run the
audit in that compatible layout. The official asset URL identifies the source
ZIP; retrieval is not performed by this code. Do not regenerate or rewrite
old Native/Standard, silently rebase manifest paths, or claim a remote audit
from synthetic tests. Missing/incompatible snapshots produce **BLOCKED /
real_data_audit=NOT_COMPLETED**, with no completed manifest.

STEP 4-A may be considered only after an explicit limited input profile fixes
the independent footprint source, tiny boundary-residual policy, external
face crosswalk/SHA contract and vertical declaration/DEM limitations. A bounded
absolute-roof-Z experiment could be reviewed conditionally; HAG, voxel/solar
integration and physical height accuracy require separate evidence/gates.
No decision or next-stage processing is performed here. Standard/Adapter,
STEP 3 code/tests, original Raw/Native/Standard, T5 and STEP 2 results are unchanged.
