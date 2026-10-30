# OUEM Repository Cleanup Plan v0.1

2026-10-30; baseline main **`19368049831e43a4c5fb3149824ae0533dcee3db`**
(PR #126 merged). Status: **proposal for review, no cleanup execution**.
Read with the [Repository Inventory](OUEM_Repository_Inventory_v0.1.md), which
owns counts, references and U01–U07 Unknowns. Current work adds only these two
planning documents. No existing code/tests/docs, artifacts, dependencies,
Acceptance or backlog state is changed. Suggested tests below are future checks,
not tests performed by this inventory.

## Decision and sequencing

Prioritize clear ownership/navigation and verified compatibility over reducing
file counts. A source file's old name, an empty namespace or absent static caller
does not establish safe deletion. Independent producer/consumer and synthetic
oracles have value even when their code looks similar. **No immediate file
retirement, mass move/rename, generic runner/output framework, environment merge
or scientific refactor is recommended.** Existing B1/B2 Technical E2E is complete
within its recorded scope; this plan does not reopen it as a new cleanup gate.

P1 means high maintainability value with limited behavior risk; P2 is a scoped
structural improvement after checks; P3 is conditional/later investigation.
These are maintenance priorities, not Acceptance or scientific priorities.
New work requires a separate authorized task/PR. Scientific assumptions, formal
contracts, major dependencies and significant architecture still follow
[AGENTS](../../AGENTS.md) and
[Development Principles](../OUEM_Development_Principles_v0.1.md).

Recommended next **four independent PRs**, in this order; labels are proposed
units, not assigned GitHub numbers:

| Unit | Candidate / purpose | Scope and completion condition |
|---|---|---|
| PR-A / P1 | C01: current navigation and owner map | Add a current contents/route to the existing long runbook/Solar guide and a route to the GIS output audit. Link this inventory/plan from an appropriate current index after review. Keep old sections/anchors/results; finish with link and authority checks. No source change. |
| PR-B / P1 | C02: CI/runtime evidence visibility | Add bounded version/origin reporting and explain which checks require separate GIS Python. Preserve existing install/test commands and matrix unless separately authorized. No package upgrade/pin change, external GIS install or new real-data execution. |
| PR-C / P2, conditional on C03 prechecks | C03: one narrow shared provenance owner | Move only the demonstrated engine environment/provenance responsibility out of the broad integration runner, preserving old imports and exact behavior. Bind any new source owner in new-run provenance. No runner lifecycle or metric change. If compatibility/source-identity conditions cannot be met, defer. |
| PR-D / P2 | C06: launcher contracts and external-use resolution | Document actual uses and add targeted missing contract checks before discussing wrapper deprecation. Resolve U01/U03 where evidence is available; leave others explicitly Unknown. Do not combine with deletion or A3 execution relocation. |

PR-A/B are useful without PR-C/D. PR-C/D are not prerequisite refactors for
new scientific work. C04/C05/C07/C08/C09 below are later options; do not bundle
them just to enlarge a cleanup PR. If a candidate has no demonstrated benefit
after prechecks, retain it and record that conclusion.

## Candidate assessments

### C01 — Documentation routes and authority (P1 / PR-A)

**Current role/evidence:** root README, the 852-line
[work runbook](../../scripts/work/README.md), 821-line
[Solar guide](../experiments/real_komae_solar/README.md), B1/B2 closeouts and prior
inventories jointly provide operation/history. The inventory's link graph finds
the [GIS output audit](OUEM_GIS_Output_Visualization_Audit_v0.1.md) is the sole
docs Markdown file not reachable by Markdown links from README. This is a
navigation gap under that scanner, not an orphan/invalid document finding.

**Proposed change / dependencies / risk:** add concise current routes and a
contents section at existing owners; keep numeric results and hashes at their
experiment/Acceptance owners. No split/move or rewritten chronology. Root
README/current status/runbook links are the affected callers. Risk is low but
anchor changes or treating a dated status as a current specification can break
reproduction or misstate authority.

**Tests / acceptance / rollback:** local link+heading checks from all tracked
Markdown, manual review of dated vs current claims and formal/provisional/draft
labels, exact diff scope. No pytest for pure navigation. All old anchors and
records remain valid; no new interface/Acceptance meaning. Revert only added
navigation if it introduces ambiguity; never “restore” history by rewriting it.

### C02 — Explicit environment and CI evidence (P1 / PR-B)

**Current role/evidence:** [pyproject](../../pyproject.toml) owns direct minimum
dependencies and five console CLIs; [CI](../../.github/workflows/pytest.yml) runs
Python 3.12 on Ubuntu/Windows. Local evidence uses OUEM 3.11.9 and separate GIS
3.12.15. Matplotlib/Numba/affine imports rely on installed dependency resolution,
with no direct declarations or tracked lock. No missing-package defect was
observed. GIS-only tests intentionally skip outside that runtime.

**Proposed change / dependencies / risk:** report bounded Python/selected-package
versions and the public pinned VoxCity origin/commit alongside existing tests;
document separate-GIS checks/skips. Keep install commands, versions and runtime
separation unchanged. Determine U04/U05 before proposing a matrix, packaging or
lock policy; dependency changes are a separate decision, not part of this PR.
Risk is low for reporting, higher if it inadvertently imports/initializes the
engine, leaks runtime details beyond the intended report or changes dependencies.

**Tests / acceptance / rollback:** review YAML, run the unchanged configured CI
jobs when authorized, verify metadata reporting does not import simulators and
skips are clearly distinguished from coverage. No claim that ordinary CI covers
QGIS GUI/real data. Revert the reporting change independently; retain logs from
each version of the job instead of overwriting older evidence.

### C03 — Shared runtime/provenance ownership (P2 / PR-C)

**Current role/evidence:** `komae_integration.environment/voxcity_provenance`
live in a 782-line orchestrator yet are imported by configured B1, B2 and earlier
canopy/diagnostics. The [reuse audit](OUEM_E2E_Reuse_Audit_v0.1.md) and B1
housekeeping already identify this coupling. The B2 caller makes it a current
multi-consumer concern, not a speculative future framework need.

**Proposed change / dependencies / risk:** first inspect whether existing
`runtime.py` is a suitable narrow owner; otherwise justify one leaf module.
Move definitions rather than copy them; preserve old import paths/signatures
and exceptions through compatibility aliases/wrappers where required. Inventory
package constants, patch points, metadata/PEP 610/RECORD checks, Git-state
reporting and code fingerprint consumers before editing. Do not move lifecycle,
path guards or Consumer validation. Moderate behavior/provenance risk: moving a
definition changes watched bytes even if return values match, and tests may
patch old module bindings.

**Tests / acceptance / rollback:** characterize current returns/errors and
import dependencies first; exercise provenance tampering/pin/shadowing cases,
fresh-process imports and affected integration/B1/B2 tests, then full OUEM pytest
in its prescribed interpreter. Keep old imports usable; new runs capture the new
owner. Do not rerun historical real scenes merely to refresh source hashes.
Retain old executed snapshots/commits; never update historical receipts to match
new code. Revert the code PR if observable behavior or provenance coverage drifts;
retain any new diagnostic outputs under separate IDs.

### C04 — File/JSON/statistics helpers (P2, defer until relevant owner change)

**Current role/evidence:** `e2e_config` imports `digest/write` through
`real_komae_source_h`; Voxel/Solar import its distribution helper; Standardizer,
Adapter, acquisition, B2 and probes have additional hash/writer functions. One
exact AST duplicate is the file `sha256` in CHMv2 acquisition and legacy canopy.
But A3 array digest, repair JSON digest, frozen-input `Watch`, exclusive JSON
writers and output-replacement checkpoints have different contracts.

**Proposed change / dependencies / risk:** if actual maintenance requires it,
extract one genuinely shared primitive with a narrow owner and compatibility
imports. Do not unify all methods named digest/write or turn `Watch` into a
producer serializer. First specify input type, streaming/array order, JSON bytes,
nonfinite policy, exclusive-create/replace and exception behavior. The low line
count of duplicated hashes alone does not justify a standalone deletion-count PR.
Moderate risk to recorded hashes, invalid-JSON handling and failure ordering.

**Tests / acceptance / rollback:** byte-for-byte fixtures for canonical JSON,
unicode/nonfinite rejection, array vs file digests, exclusive creation and partial
failure; affected configuration/Voxel/Solar/acquisition/B2 tests and full suite.
Preserve existing API and historic identities as for C03. Roll back a primitive
and its callers as one unit if any serialized/provenance contract changes.

### C05 — Large orchestrator and substantive A3 work script (P3 / later PR)

**Current role/evidence:** integration coordinates guards, runtime, repeat
semantics and child commands; `scripts/work/voxcity_komae_a3_acceptance.py`
contains 376 lines of actual engine/voxel checks. Integration fingerprints and
executes that exact path; canopy export and `runpy` tests also depend on it.
The 525-line accepted Adapter and other sizeable modules may be cohesive;
line count alone is not an implementation defect.

**Proposed change / dependencies / risk:** after C03, consider one demonstrated
responsibility boundary at a time. Moving reusable A3 logic into `src` would
require preserving the file entry as a compatible thin launcher and explicitly
tracking all executed source bytes in new runs. **Do not schedule this as routine
cleanup until the A3 evidence/patching/CLI dependencies are mapped.** High risk:
accepted-path oracle, runpy namespace, cwd, pin checks and historical source hashes.

**Tests / acceptance / rollback:** exact old-file CLI/runpy and subprocess
contracts, synthetic pin/ID/ground/voxel comparisons, retained failure cases,
integration/Adapter/canopy tests and full suite. No Standard whitelist, geometry,
observer, optical or Acceptance change. A newly authorized real smoke, if ever
needed, is a separate evidence run; not an overwrite. Restore original entry and
implementation by reverting the PR, leaving old artifacts untouched.

### C06 — Wrappers and historical diagnostic use (P2 investigation; P3 retirement)

**Current role/evidence:** the inventory lists all 14 CMD and 8 Python helpers,
their CLI/test/doc references and U01–U03 uncertainty. Three ID scripts have a
narrow historical purpose and acceptance citations but no tracked automated
caller. Other wrappers have active dispatch, input validation and quoting tests.

**Proposed change / dependencies / risk:** PR-D resolves actual use, documents
replacement equivalence if any and adds missing focused launcher checks. A
later **separate** deprecation/retirement PR is possible only for a specifically
proven superseded entry. No broad wrapper abstraction or guessed removal. Do not
infer zero users from zero static imports. Breaking CLI/manual workflow risk is
moderate/high; cited historical source must remain accessible by immutable commit
and linked explanation, with explicit agreement on preservation before removal.

**Tests / acceptance / rollback:** Windows execution from another cwd, spaces and
metacharacters, arity, `.venv` selection, rejection paths, exit propagation and
new-output-only behavior; related module/launcher tests plus full suite for code
changes. External usage still Unknown means retain/defer. Roll back deprecation
or restore the identical public launcher if a caller is discovered; do not erase
the finding or alter old acceptance evidence. No retirement is approved here.

### C07 — GIS/raster shared primitives (P3 / separate per-primitive PR)

**Current role/evidence:** Voxel/Solar/B2 write geographic rasters; their readers
and independent diagnostics repeat some affine/mask/hash checks. `gis_project`
and `b2_gvi_qgis` deliberately run as standalone GIS files. Solar has its own
seven-layer contract; B2 has four layers/site. B2 uses a completed-B1 reader.

**Proposed change / dependencies / risk:** extract a small serialization primitive
only when more than one owner genuinely needs a change; do not replace independent
readback or invent a common analysis/output framework. Any shared GIS helper must
remain usable by file in existing GIS Python without importing/installing OUEM.
Preserve source-cell versus provider-grid distinction and provider alpha.
Moderate/high risk to ABI/import context, NoData, raster orientation and QGZ paths.

**Tests / acceptance / rollback:** non-square/rotated/translated arrays, zeros vs
NaN, TIFF CRS/affine/masks/values, context-before-crop, existing GIS alpha tests,
standalone GIS save/reopen/relocation and separate GUI checks if presentation
changes, plus full OUEM suite. Keep independent numeric oracles independent.
Rollback code/helper use together; old TIFFs/QGZ/topology/receipts stay frozen.

### C08 — Test fixture ownership (P3 / only when concrete test moves need it)

**Current role/evidence:** large integration tests and cross-test fixture imports
support source-chain and authored scene checks. New B2 tests import the existing
authored saved-run fixture. These references are valid but make a future test-file
reorganization less local than it appears.

**Proposed change / dependencies / risk:** if repeatedly modified shared setup
warrants it, move only that setup to a test-only owner; retain independent scalar,
geometry and mask expectations and all regression cases. No blanket fixture
centralization, test deletion or production-oracle reuse. Moderate discovery,
monkeypatch and correlated-oracle risk.

**Tests / acceptance / rollback:** compare collection and case coverage before/
after, fresh-process imports, selective and full pytest, separate GIS execution
where relevant. Fixture LF/hashes and opt-in `run_*` semantics stay unchanged.
Revert fixture relocation as a unit if discovery or independence is weakened.

### C09 — Generated-asset policy visibility (P2, independent later PR if needed)

**Current role/evidence:** only markers are tracked in data; three PNGs/five docs
JSONs and the tiny GML fixture are intentional evidence. No accidental generated
Raster/NPY/QGZ/log was found. Some output extensions remain trackable outside
ignored work directories; ignore rules do not protect against deliberate adds.

**Proposed change / dependencies / risk:** consider a narrow documented staged-
asset review or opt-in CI check with explicit evidence/fixture exceptions. Do not
blindly ignore/untrack all GML/JSON/PNG or delete local caches/data. First resolve
U06 for any proposed local pruning; local data cleanup is a separate task.
Low code risk for visibility, potentially high reproducibility risk for exclusion
rules that hide required fixtures or executed source snapshots.

**Tests / acceptance / rollback:** `git ls-files`, `git check-ignore`, known marker/
fixture/evidence allow cases and generated-work reject examples; no real data
generation. Preserve existing tracked evidence and verify a Git-only checkout
still contains required small test assets. Revert a misclassifying guard/ignore
change; do not erase evidence to satisfy a rule.

## Protection conditions before any implementation PR

1. Freeze the new PR's baseline commit, exact changed-file list, affected public
   module/CLI/file-path entry points, dynamic/Windows/GIS references and unresolved
   users. Treat U01–U07 as unknown until investigated; no “not referenced = safe.”
2. Keep accepted v0.1 and experimental source-H/Canopy/B1/B2 boundaries separate.
   Preserve deterministic IDs, manifest schemas/whitelists, CRS/Z/axis conventions,
   mask/NoData policies and failure behavior. Do not change settings, add GPU or
   broaden Acceptance under the cleanup label.
3. Preserve B1/B2 original runs, Current/No-Canopy/Solar/B2 arrays, manifests,
   receipts, frozen submitted settings, logs/source snapshots, hashes and QGZ
   relative topology. Identify affected recorded implementation hashes before
   moving code; preserve immutable old sources and capture new owners for new
   runs. **Never repair historical manifests/hashes to match new code.**
4. Keep [B1](../status/B1_TECHNICAL_MILESTONE_CLOSEOUT.md) /
   [B2](../status/B2_TECHNICAL_MILESTONE_CLOSEOUT.md) scope and
   [B1](OUEM_B1_Deferred_Validation_Backlog.md) /
   [B2](OUEM_B2_Deferred_Validation_Backlog.md) unresolved states. Do not convert
   scientific Unknown into pass/fail or close CPU/GPU/height/context/photo issues.
5. Keep VoxCity 1.7.0 at `fa212656305328a9a657973bae26f352bfe813bc`; ordinary
   Windows OUEM `.venv/Scripts/python.exe` / Cloud `.venv/bin/python` stays separate
   from existing GIS Python. No installation, lock/pin change, runtime/security/
   sandbox change or external script acquisition follows from this plan.
6. Prefer fresh synthetic/contract checks over real replay for behavior-preserving
   changes. Follow AGENTS: appropriate focused tests then full `-m pytest -q -ra`
   for code, proportionate links/scope checks for docs. Report actual failures,
   skips, warnings and checks not run; GIS/GUI is separate from ordinary CI.

## Common acceptance and rollback rules

Each future PR must explain the concrete maintenance benefit, owning module/docs,
unchanged observable contracts, retained Unknowns and Documentation Impact.
Acceptance of a cleanup PR requires scoped diff/artifact checks, no lost public
entry path or regression case, matching serialization/geographic semantics where
applicable, and preservation of existing evidence. Use an independent review for
any consequential contract/scientific/architecture decision. This does not itself
adopt the [proposed governance](../OUEM_Documentation_Governance_v0.1.md).

Keep PRs independently revertible; retain compatibility entry points until use
and deprecation policy are settled. If a regression or unexpected external caller
appears, stop that candidate, revert its code/navigation change and restore the
old interface from the baseline commit. Do not roll back by deleting new evidence,
recalculating old outputs or overwriting an existing run. Record unsuccessful
attempts separately. If original provenance/topology cannot be preserved, reject
or defer the candidate instead of silently changing the meaning of reproduction.

## Validation of this planning-only PR

The [Inventory](OUEM_Repository_Inventory_v0.1.md) records baseline counts, imports,
CLI/CMD/file-path references, CI and environment metadata, ignored-file checks
and the bounded link scan. No candidate, test, CLI, GIS tool or simulation is
executed here. Validate these two new documents' links, cross-references and
candidate/Unknown IDs, run `git diff --check`, inspect staged files and confirm
the baseline diff contains **only two added Markdown files**. No README,
existing documentation, tests, source, dependency, artifact or backlog change is
part of this PR; navigation implementation is intentionally deferred to PR-A.
