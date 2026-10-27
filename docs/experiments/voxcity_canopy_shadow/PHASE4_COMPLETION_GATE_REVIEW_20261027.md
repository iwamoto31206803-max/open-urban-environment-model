# Phase 4 Completion Gate review — 2026-10-27

**Gate proposal: CONDITIONAL PASS** for closing the canopy-only exploratory
Phase 2–4 work. The documented technical calculations and limits are coherent,
regression passes, and a bounded Phase 5 plan can be reviewed. This is **not a
Phase 5 execution approval**: pre-start class A items below remain open; actual
Building integration is BLOCKED until their evidence/decisions are closed.
No Standard Canopy or scientific accuracy acceptance is conferred.

This is a fresh source/evidence cross-audit for independent review, not a claim
that an independent human expert has approved the previous authors' work.
Only three audit documents are added:

- This Gate: consolidated verdict, evidence and A/B/C issue classification.
- [Repository inventory](REPOSITORY_INVENTORY_20261027.md): document roles,
  current link edges, module/test/launcher references and future cleanup candidates.
- [Phase 5 plan](PHASE5_INTEGRATION_PLAN_v0.1_Draft.md): common geometry, scenarios,
  state/observer policy and measurable acceptance gates. It is a draft experimental
  plan awaiting review, not an accepted Standard/Adapter amendment.

## 1. Baseline and authority

Fetched main: `56059467dde052ad95c8a666f18acb660c7622a4`.
GitHub status and local ancestry both confirm all five PRs are merged; no merge
operation was performed by this audit.

| PR | Scope | Merge commit |
|---|---|---|
| [#70](https://github.com/iwamoto31206803-max/open-urban-environment-model/pull/70) | Phase 0–1 API/design snapshot | `6c211654dc3ef6320c7426bd68b5bc702cbca513` |
| [#71](https://github.com/iwamoto31206803-max/open-urban-environment-model/pull/71) | Phase 2 real CPU direct A/B | `e625e03f0dd2b826e03380f941edca4aa2126199` |
| [#72](https://github.com/iwamoto31206803-max/open-urban-environment-model/pull/72) | Phase 3 resolution/observer sensitivity | `b6a0b08139a7a66d59b90c404cb21958bdcbb3e6` |
| [#73](https://github.com/iwamoto31206803-max/open-urban-environment-model/pull/73) | Phase 4A observer/Z proposal and counterexamples | `cace985675e921148781ccff8b31908fee4f7262` |
| [#74](https://github.com/iwamoto31206803-max/open-urban-environment-model/pull/74) | Phase 4B state/presence/coverage audit | `56059467dde052ad95c8a666f18acb660c7622a4` |

Authority: [Concept v0.2](../../OUEM_Concept_Architecture_v0.2.md) is the registered
upper conceptual design; it neither amends current contracts nor finalizes
unresolved decisions. [Concept v0.1](../../OUEM_Concept_Architecture_v0.1.md)
retains inherited B1/B2 details. Read the current-status note in
[Phase A implementation design](../../Phase_A_Implementation_Design_v0.1.md).
[Standard Terrain](../../OUEM_Standard_Terrain_v0.1.md) and
[Standard Building](../../OUEM_Standard_Building_v0.1.md) remain PROVISIONAL,
with bounded Komae data acceptance. The
[Building Adapter](../../OUEM_VoxCity_Adapter_v0.1.md) is authoritative for its
accepted Building boundary, not a generic canopy Adapter.
[Standard Canopy DRAFT](../../OUEM_Standard_Canopy_v0.1_Draft.md) and the
[Height Envelope PoC](../../CHM_Height_Envelope_PoC_v0.1.md) have different scopes
and state encodings; neither PoC merge ratifies full Canopy.

Original [A2](../../acceptance/OUEM_A2_Standard_Terrain_Komae_Acceptance_20261006.md),
[A3](../../acceptance/OUEM_A3_VoxCity_Komae_Acceptance_20261005.md),
[Building](../../../experiments/a1_e2e_pilot/README.md),
[source correction](../../acceptance/OUEM_A2_Terrain_Source_Provenance_Correction_20261026.md)
and [Terrain reproduction](../../acceptance/OUEM_A2_Terrain_Reproducibility_Verification_20261026.md)
records remain unchanged. Filing under acceptance, technical PASS, merged PR,
CLI completion and formal approval are not interchangeable.

## 2. Technical Gate assessment

PASS below means only the stated tested property; it does not expand the
underlying dataset/environment/sun/accuracy scope.

| Topic | Verdict | Evidence / reason / boundary |
|---|---|---|
| Envelope to TREE transformation | PASS | Phase 2 actual whole-field expected occupancy equals engine output; one DEM subtraction and row flip; A TREE=0, B=98,840 in 128m domain. Source presence is not proved |
| Canopy-only CPU direct comparison | PASS | 4,096 paired finite ROI cells; mean A=780.402577774, B=66.948346222 W/m²; 3,816 decreased, zero increased; fixed geometry/sun/optics, not global/annual radiation |
| Voxel resolution sensitivity | CONDITIONAL PASS | S1 exactly reproduces Phase 2; 0.5m isotropic mean B=67.393719842. Mean contrast +0.445373620 hides −168.120390..+222.380012 local changes; horizontal sampling and observer changes are inseparable |
| Observation height / actual origin | CONDITIONAL PASS | Public-map lattice measured; nominal h=1.5 gives about 2.001..3m above source DEM at 1m resolution. Internal fractional-origin counterexample blocks arbitrary physical-point claim; retain Phase 4A option C |
| Absolute Terrain/envelope/voxel Z | CONDITIONAL PASS | Ground +s, DEM/crown precision/rounding and thin expansion separated; effective ground re-origin with Building IDs remains to be tested on chosen real Building scene |
| Zero / missing / outside / invalid | PASS | Existing bits distinguish these; strict runners reject nonvalid state. New Phase 4B synthetic examples show zero and missing cannot be inferred from values alone; no missing-to-zero defect found in guarded Komae path |
| Height evidence versus TREE occupancy | PASS | Factorized audit; valid positive source can collapse/round to no TREE, or expand. Current Komae has 40,789 positive / 79,211 zero valid samples; presence remains unassessed |
| Test and byte evidence | PASS (bounded) | Current focused 150 and full 605 tests pass; historical packet hashes rechecked without regeneration. This does not reaccept Building source Z or scientific source accuracy |

Primary frozen records: [Phase 2 results](PHASE2_RESULTS_20261027.md) /
[usage](PHASE2_USAGE.md), [Phase 3 method](PHASE3_API_AND_METHOD.md) /
[results](PHASE3_RESULTS_20261027.md),
[Phase 4A](PHASE4A_OBSERVER_GEOMETRY_AND_VERTICAL_CONTRACT.md),
[Phase 4B](PHASE4B_CANOPY_PRESENCE_AND_COVERAGE_AUDIT.md).
[Phase 0 API](API_REVIEW.md) and [proposal](MINIMAL_ADAPTER_PROPOSAL.md) are
dated predecessors, not current no-implementation claims.

## 3. Unresolved issues: A / B / C

A = must close before Phase 5 integration starts (read-only discovery to close
A may occur first). B = must validate during implementation, before accepting
any real A/B/C comparison. C = may defer only within explicitly limited PoC
claims. A proposed plan is not evidence that an open item has passed.

| ID | Issue | Class / status | Required disposition |
|---|---|---|---|
| A1 | Scope and observer interpretation | A / OPEN for review | Approve model-surface public-map option C and actual XYZ reporting; requiring exact physical 1.5m instead makes entry BLOCKED |
| A2 | One common grid / Building ID mapping and conditioning | A / OPEN for review | Approve explicit projected-grid experiment and common reference-ID ground policy; accepted geographic arrays are not interchangeable |
| A3 | Chosen Building input identity / Z basis | A / OPEN evidence | Freeze actual bytes+manifest and chosen source-chain evidence; no path-only assumption from old A3. Resolve selected-data implications of the tracked vertical hypothesis or demonstrate an unaffected subset |
| A4 | State, overlap, masks and denominator policy | A / OPEN for review | Approve source retention, conversion-loss accounting, Building-over-TREE model order and fixed common non-building-column observers |
| B1 | Per-ID ground averaging / D0 re-origin | B / NOT IMPLEMENTED for Phase 5 | Pass same D_raw and reference IDs to all scenarios; verify actual D_eff/D0/g/ground/surface equality before solar |
| B2 | Building/canopy overlap and priority | B / NOT IMPLEMENTED | Audit pre/post TREE set relation and identical B/C BUILDING mask, counts/volumes/IDs; 2-D overlap alone is not blanket crown removal |
| B3 | Float32 and segment/voxel rounding | B / synthetic limits known, mixed scene unverified | Verify near-half cases, +s and expansion, absolute faces and model-ground conflicts; no silent clipping/offset |
| B4 | Post-building observers and A/B/C mask | B / NOT IMPLEMENTED | Freeze mask before looking at irradiance, verify same actual origins and finite paired cells; no post-hoc favourable filtering or NaN-to-zero |
| B5 | Halo with taller Buildings / reproducibility | B / NOT IMPLEMENTED | All-scene bound and covered larger halo; current canopy-only proof insufficient. Repeats and protected source bytes required |
| C1 | Arbitrary physical 3-D observers | C only if A1 accepts model-map limit | Existing low-level initialization is not generally safe; no new tracer or patch accepted. Do not claim physical DEM+1.5m |
| C2 | Independent canopy presence / assessment footprint | C for exploratory height-driven occupancy only | Preserve unknown/unassessed labels; no verified absence from CHM=0 or TREE=0; complete Standard Canopy stays deferred |
| C3 | Optical/CR calibration and scientific accuracy | C for fixed declared assumptions | k/LAD/CR, source timing/height/registration and field accuracy unverified; no ecological, thermal, annual or production claims |

### A3 evidence gap is concrete, not a proposed automatic correction

The tracked [Building vertical diagnosis](../../research/OUEM_Komae_Building_Vertical_Geometry_Diagnosis.md)
still says UNRESOLVED; the roughly 37m discrepancy is a hypothesis, not a matched
vertex proof or an approved datum shift. Existing Standard Building interprets
retained Z as absolute T.P.; neither that declaration nor historical acceptance
resolves the source-converter numerical question for a new selected file.
Do not subtract 37m or reinterpret all Building Z from this audit.

Read-only path checks on this checkout found neither
`data/standard/building/komae.gpkg` nor `data/native/building/komae.gpkg`, nor
`data/standard/building/komae.gpkg.manifest.json`. This is not an exhaustive claim
that no Building file exists elsewhere. Source discovery and hash/evidence
selection are outstanding; no chosen Building input was verified here. Old A3
explicitly records local paths without hashes, so it cannot identify new bytes.
This is why Phase 4 closure does not automatically open a real Phase 5 run.

## 4. Repository consolidation verdict

No missing baseline inline relative file target was found. A separate static
heading-slug check matched 5/7 existing local anchors and flagged 2 inherited
B1/B2 links in Concept v0.2: their fragments use four hyphens after B1/B2, while
the current literal heading yields five in the checked slug rule. Live GitHub
rendering was not verified, so treat these as unresolved anchor risks, not as
confirmed working links. Existing Concept text/links remain unchanged.
Discoverability is
weaker than file integrity: Phase 4A/4B and 3D verification had no baseline
inbound inline Markdown links; README lacks a Phase 2–4 index. The new three-file
audit index remedies reviewer navigation without editing historical records.

Recommended follow-ups (not executed): role-based README/runbook index; clarify
legacy 23-ku path versus Tama source and old environment notes; consider a
linked runtime explanation instead of duplicated architecture text; index Phase
0-1 proposal as superseded. Keep formal acceptance records immutable. Similar
formulas inside frozen experiments are audit context, not evidence of competing
formal contracts. The inventory lists all current in/out link edges and actions.

Code candidates are future versioned utility extraction (pin, hash/metadata,
publication) and careful contained-launcher consolidation. Freeze Phase 2/3
runner protocols: sensitivity imports Phase 2 helpers and old module hashes
bind execution evidence. Keep dataset-specific ID scripts cited by A3, even
when static imports show no caller. No deletion/relocation/refactoring is
performed or authorized as a side effect of this audit.

## 5. Current validation and evidence limits

Executed in ordinary Windows OUEM `.venv/Scripts/python.exe`:

```powershell
.venv\Scripts\python.exe -m pytest -q tests/test_canopy_presence_semantics.py tests/test_meta_chmv2_acquisition.py tests/test_height_envelope.py tests/test_canopy_shadow_poc.py tests/test_canopy_shadow_sensitivity.py tests/test_canopy_observer_geometry.py --junitxml=data/work/voxcity-canopy-shadow/completion-gate-focused-20261027-01.xml
.venv\Scripts\python.exe -m pytest -q --junitxml=data/work/voxcity-canopy-shadow/completion-gate-full-pytest-20261027-01.xml
```

Focused: **150 passed, 122 warnings in 19.24s**. Full: **605 passed, 5 skipped,
250 warnings in 160.81s**. Existing Windows symlink-privilege skips and
Rasterio/Affine pending deprecations remain. Passing characterization tests
include known API counterexamples; they do not mean arbitrary observers passed.
No new tests or production changes are introduced. New links/file references
and existing-file diff scope are checked; results are recorded below.

Local evidence ID:
`data/work/voxcity-canopy-shadow/phase4-completion-gate-20261027-01/`.
Static Markdown graph and AST imports are evidence of references, not a complete
dynamic call graph. Historical data/read-only hash checks are not new real-data
runs, a QGIS recheck or independent field/scientific acceptance. Environment:
Python 3.11.9, VoxCity 1.7.0 pin
`fa212656305328a9a657973bae26f352bfe813bc`. Full installed RECORD/source checks
and local packet identities are captured in the audit receipt.

Current receipt: **41 Markdown files / 312 local link occurrences** checked,
zero missing relative file targets. All new audit links resolve; new docs have
no fragment anchors. Existing local heading anchors: 5 static matches and
2 unresolved B1/B2 renderer/slug risks described above (not live-render verified).
87 historical input/result files rehashed unchanged; baseline tracked-file diff
is empty apart from the three new audit additions. Python/launcher inventory
covers 82 tracked Python paths and 15 CMD paths, not ignored local copies.

| Audit evidence (local only) | SHA-256 |
|---|---|
| Focused JUnit | `e963c7a423db8c873d15fa830c202dc5857e6eb6fb93ed9ab102b9fa3e5b0178` |
| Full JUnit | `83d1fddd5fed43ecb81cc3e37bb502855fffd539a527b7c76ffbcfdf76393b9e` |
| Historical Phase 4B audit rechecked | `a48c4449eb24e2dcff5c40d958e81cd185db0c717377b0e82026f353c9b12e2d` |


## 6. Completion decision

Close the canopy-only milestone with **CONDITIONAL PASS**, preserving all stated
limitations and old records. Review/close A1–A4 before Phase 5 integration work;
then implement B gates in an isolated experiment before interpreting any mixed
Building/canopy radiation. C items remain explicitly deferred. Until A closes,
Phase 5 real-data execution readiness is **BLOCKED**, not implicitly granted by
merged Phase 4 PRs or passing regression. No Standard, scientific precision,
source correction or production acceptance is changed by this review.
