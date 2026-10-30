# B2 Technical E2E Milestone Closeout

Checked **2026-10-30**, main `b19bec4ee76ac246435c121956305c3c461e3be5`
(PR #125 merged). **The bounded Komae A/B B2 CPU Technical E2E Milestone is
complete.** Scientific validity remains unverified. This closes a technical
development increment, not Formal Acceptance, a primary scientific GVI definition
or authorization for further calculations, dependency changes or feature work.

## Evidence and completion scope

GitHub reports all three PRs below as merged; their merge commits are ancestors
of the fetched main above. Each record retains its original execution scope.

| Stage | Merged GitHub artifact / merge commit | Evidence owner and established scope |
|---|---|---|
| API audit | [PR #123](https://github.com/iwamoto31206803-max/open-urban-environment-model/pull/123), `0d441b5a8d9ba338d6377c8d4a3eedf33a093968` | [Audit](../planning/OUEM_B2_VoxCity_GVI_API_Audit_v0.1.md) identifies pinned CPU/GPU source paths, defaults, observer/sampling/score semantics and implementation risks. Static inspection, not runtime validation. |
| CPU synthetic characterization | [PR #124](https://github.com/iwamoto31206803-max/open-urban-environment-model/pull/124), `a19943a3e8b3af7ffde0989bc8fc4f922d9f55e0` | [Synthetic report](../experiments/b2_gvi/B2_CPU_GVI_Synthetic_Characterization_v0.1.md) and [tests](../../tests/test_b2_gvi_synthetic.py) compare actual CPU APIs against independent scalar formulas and hand-specified chords; diagnose masks, height, exits, corner differences and fallback. No real-data GVI or GPU execution in that stage. |
| Komae A/B Technical E2E | [PR #125](https://github.com/iwamoto31206803-max/open-urban-environment-model/pull/125), `b19bec4ee76ac246435c121956305c3c461e3be5` | [Results](../experiments/b2_gvi/RESULTS.md), [usage](../experiments/b2_gvi/README.md), [runner](../../src/ouem/b2_gvi.py), [GIS helper](../../src/ouem/b2_gvi_qgis.py) and [tests](../../tests/test_b2_gvi.py) establish saved Current Voxel → public CPU generic API → GeoTIFF → QGIS diagnostics, save/reopen and observed GUI, with source identities and immutability checks. |

The provisional result name is **CPU weighted first-TREE view index**. The tested
ordinary TREE contribution is `1-exp(-k*LAD*L)` for the first TREE-cell chord;
deeper crown cells do not add to that hit, and the tested T<0.01 branch returns
zero contribution. It is not binary canopy-hit fraction, full-crown transmission
integration, photograph-based green-view fraction or scientifically validated GVI.
Numerical consistency with this implementation does not calibrate crown optics.

PR #124 measured a particular corner-side Building case where generic and direct
fast traces disagree. Its public fast=True calls instead raised a Numba typing
error and completed through generic fallback in the recorded environment;
successful fallback values are not evidence of fast-map success. CPU/GPU source
differences remain **static leads**, not a completed execution comparison or a
confirmed measured CPU/GPU GVI difference.

The A/B technical scope is preserved prepared B1 Current geometry, CPU generic
only, TREE-only targets and finite saved domains. It includes:

- Frozen receipt/config/report and delivered-output identity checks, read-only
  Current loading, independent observer/capacity/class/mask diagnostics and
  before/after source checks. PR #125 records 136 protected original Run files.
- Full-domain computation before evaluation extraction. A/B full int8 arrays
  are **128×128×27 / 128×128×26**; the saved B1 evaluation ROI is **64×64**,
  u/v `[32:96,32:96]`, with **32 m context**. The earlier request's 128×128
  evaluation wording did not describe those inputs; full and ROI rasters are
  both delivered without inventing additional context or revoxelizing.
- Float64 dimensionless index, valid zero distinct from NaN NoData, and masks.
  Geographic EPSG:4326 affine/centres match B1; `row=nu-1-u`, `col=v`.
  ROI extraction translates that affine; no analytical reprojection occurs.
- Separate existing QGIS Python, project EPSG:6677, B2-specific A/B layer groups,
  original-file all-cell/spot checks, saved project/reopen and actual GUI
  observation. Solar's seven-layer presentation contract is not reused as B2.

Full statistics, performance measurements, numeric residuals, output hashes and
failure histories remain in the owning experiment reports, rather than becoming
new thresholds here. PR #125's completed full suite records **1080 passed,
10 skipped, 336 warnings**, with the new GIS test covered separately in GIS
Python. PR #124's earlier full-suite failure and initial fallback assertions
remain historical failures; subsequent completion does not rewrite them.

## Relationship to B1 and Acceptance

The [B1 closeout](B1_TECHNICAL_MILESTONE_CLOSEOUT.md) remains the dated technical
status for fixed-sun direct irradiance and its own Current/No-Canopy/Difference
products. Its statements that B2 had not yet been implemented described that
earlier checkpoint; PR #123–125 supply the subsequent B2 evidence. Neither
closeout changes the other's execution record or completes its scientific work.

B2 reuses saved B1 Current arrays, spatial metadata, provenance and bounded GIS
lessons. It does not rerun Solar, rebuild Voxel, alter B1 outputs or inherit
Solar's W/m² units, k=0.6 or seven-layer schema. B2's declared profile uses
k=0.5 and dimensionless values. Shared observer/D0, resolution, estimated
canopy/CHM/CR, 2.5D Building, exterior coverage and transfer/scaling concerns
remain in the [B1 backlog](../planning/OUEM_B1_Deferred_Validation_Backlog.md).
B1 radiation validation cannot stand in for visibility/photo validation.

No new Formal Acceptance is declared. Existing dataset-bounded Phase A acceptance,
source-H eligibility **NOT_ESTABLISHED**, mixed-lane Formal Acceptance
**NOT_VERIFIED**, Building/Terrain **PROVISIONAL**, Canopy **DRAFT** and
Phase 5 A1–A4 **OPEN** are not advanced by this closeout. The
[proposed documentation governance](../OUEM_Documentation_Governance_v0.1.md)
also remains proposed.

## Unresolved validation and handoff

The [B2 Deferred Validation Backlog](../planning/OUEM_B2_Deferred_Validation_Backlog.md)
owns all seven issue IDs. Each still records **Deferred / Unverified** for its
unresolved question; specified observed CPU facts are not erased or confused
with those open questions. No row is closed by successful A/B execution.

| Issue | Outstanding verification to carry forward |
|---|---|
| B2-V01 | CPU/GPU TREE-hit score comparison by actual matched execution, with independent expectations and declared metric definitions. No GPU runtime/device comparison has been performed. |
| B2-V02 | Backend start-cell/capacity parity and matching physical origins. A/B CPU index/capacity checks and counts of origins inside TREE do not resolve GPU behavior or physical viewpoint accuracy. |
| B2-V03 | CPU/GPU precision, axes, grid/Fibonacci sampling phase, near ties and cutoff-neighbourhood behavior under matched conditions. |
| B2-V04 | Scope and real-scene effect of the measured CPU fast/generic corner discrepancy; physically intended tangency policy and broader 3D/near-tie cases. Generic-only E2E does not resolve this. |
| B2-V05 | Public-fast typing/fallback resolution, actual-path observability and portability to other environments. Generic use avoids that path for this experiment, not a fix to the engine. |
| B2-V06 | TREE transmittance/extinction interpretation, k/LAD calibration, exact cutoff and first-chord versus binary/full-crown metric meaning. Tested Beer–Lambert arithmetic is not validated vegetation optics or a full-crown integral. |
| B2-V07 | Observation height/ground reference, origins in TREE, D0/grid phase, angular measure and finite-domain sufficiency. **32 m context is not certified sufficient** for all view rays. Independent measured photographs/field visibility, dates/season, viewpoints, image segmentation and weighting need a separate comparison design. |

Future work should select a question and evidence identities first, agree the
physical/metric definition, reference data, controlled conditions, tolerances and
resource scope, then obtain any required authorization for scientific assumptions,
data acquisition, real runs, dependencies/GPU or contracts. Use new output IDs
and retain old bytes. In particular, B's evaluation ROI lies west of A's and their
full context domains overlap, but differing D0/grid phase/finite boundaries do
not establish a common physical-observer comparison. No next phase or new
validation threshold is approved by this document.

## Local evidence, runtime and reproduction

Repository-relative locations (not included in a Git clone):

| Location | Role / owner |
|---|---|
| `data/work/shared-vertical-domain/phase3c-20261029-01/outputs/komae-{a,b}-3c-20261029-01/` | Preserved B1 inputs: frozen config, receipt, Voxel/Solar reports, `solar/current_voxels.npy`, grid, centres and masks. |
| `data/work/b2-gvi-phase3-20261030-01/a/`, `b/` | Final full/ROI index NPY/GeoTIFF, observer/ROI masks, observer indices, settings, preflight and final report. |
| Same B2 root: `benchmark-a/`, `benchmark-b/` | Pre-run subset cost/CPU/RSS and matching feasibility receipts; subset values are not evaluation results. |
| Same B2 root: `qgis/` | Final `project.qgz`, receipt, rendered overview and ROI outlines. QGZ references rasters; preserve relative directory topology. |
| Same B2 root: `gui-verification.json`, `gui-final-*.jpg`, `spatial-check.json`, `gis-spot-check.json`, `repeat-check.json` | Separate GUI evidence, centre/original-file/repeated-CPU diagnostics. Generation receipts' NOT_VERIFIED GUI fields were not retrospectively rewritten. |
| Same B2 root: `executed-b2_gvi*.py`, scripts and logs | Executed source snapshots, commands and validation logs. `full-api-*` / `full-domain-preview/` are preliminary checkpoints, not final delivery. |

Provenance is held in the frozen settings/preflight/report, benchmark receipt,
source identities, implementation hashes and output hashes. The
[results file](../experiments/b2_gvi/RESULTS.md) owns final report/raster/QGZ
hashes and the scope of the original validation. The reader checks recorded
handoffs and configured input identities; it is not fresh Consumer execution,
full upstream Raw revalidation or proof of scientific input accuracy.

Recorded runtime: ordinary Windows OUEM `.venv/Scripts/python.exe`, Python
3.11.9; VoxCity **1.7.0**, commit
`fa212656305328a9a657973bae26f352bfe813bc`; NumPy 2.4.6, Numba 0.68.0,
Matplotlib 3.11.2, two CPU threads. Existing separate GIS Python 3.12.15,
QGIS 4.2.3 and GDAL 3.13.3 performed GIS checks. Follow
[runtime architecture](../architecture.md); never merge the environments.
These are execution records, not a fresh runtime health certification.

For a future authorized reproduction, follow the canonical
[B2 usage commands](../experiments/b2_gvi/README.md): create a **new** ignored
output parent outside B1 Runs, run the same-profile subset benchmark for each
site, inspect its feasibility receipt, then pass that matching receipt to the
full runner. Its explicit profile is mode=None, hit_values=(-2,),
inclusion_mode=True, fast_path=False, tree_k=0.5, tree_lad=1.0,
view_point_height=1.5 m, grid 120×20, elevation −30/+30 degrees, roofs=False,
OBJ off. Retain all context until after calculation. Use the existing GIS
Python command to create a new B2 QGZ, verify it in a separate process and
record GUI observation separately. Do not execute the guide's historical
output paths as overwrite targets, change settings to force agreement, or
update an old report/hash to disguise a new run.

## This closeout's checks

GitHub merge metadata, local main ancestry, current source/settings definitions,
experiment records and all seven backlog rows were inspected read-only. Thirty
selected local B2 final/evidence files and selected B1 input locators exist at
this check; the two small final report JSON hashes match the published results.
This is **availability and record consistency**, not a fresh full-raster/source
rehash, replay of PR #125's 136-file immutability check or new GUI acceptance.

Only Markdown is changed. Local links and cross-document scope were checked,
with `git diff --check` and staged scope/artifact inspection. Pytest, simulator
imports, GVI/Solar calculations, revoxelization, GIS generation/reopen and GUI
work were not rerun for this documentation-only closeout. Existing experiment
results, code, artifacts, B1/B2 backlog states and Acceptance history are preserved.
