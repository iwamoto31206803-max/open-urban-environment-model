# OUEM Documentation Governance v0.1

Status: proposed documentation policy for review; no data-contract or acceptance change.
Baseline checked: 2026-10-27, main `66f262f1e9d0d22d01b25ae73ce5a4a7fd9057e2`
(PRs #75 and #76 merged).

## Responsibilities and existing owners

| Role | Owns | Existing entry points |
|---|---|---|
| Architecture / Standard | Normative design, data meaning and contracts, subject to each document's status | [Concept v0.2](OUEM_Concept_Architecture_v0.2.md), [Building](OUEM_Standard_Building_v0.1.md), [Terrain](OUEM_Standard_Terrain_v0.1.md), [Building Adapter](OUEM_VoxCity_Adapter_v0.1.md), [Canopy DRAFT](OUEM_Standard_Canopy_v0.1_Draft.md) |
| Implementation / Interface | Implemented CLI, inputs, outputs and processing boundaries | [Height Envelope usage/contract](CHM_Height_Envelope_PoC_v0.1.md), [Phase 2 usage](experiments/voxcity_canopy_shadow/PHASE2_USAGE.md), [runtime architecture](architecture.md), [execution runbook](../scripts/work/README.md), and linked source/tests |
| Verification / Acceptance | What was executed, evidence identities, results, limits and approval scope | [Building acceptance](../experiments/a1_e2e_pilot/README.md), [acceptance records](acceptance/), [3D verification](verification/OUEM_Height_Envelope_3D_Visualization_Komae_20261026.md), [experiment index](experiments/voxcity_canopy_shadow/README.md) |
| Current State | Dated navigation to implementation, evidence, open issues and next gate | [Canopy](status/CANOPY_CURRENT_STATE.md), [Building](status/BUILDING_CURRENT_STATE.md) |

Reuse the owning document when it already fulfils a role. A document may cover
more than one role if the boundaries are explicit; do not create another interface
specification merely to fill a category. Source/tests establish implementation;
a planned feature in Architecture or a Draft does not establish implementation.
Current State is a summary and entry point, with no authority to override a
Standard, an acceptance record or its limits. Resolve discrepancies against the
owning sources and report conflicts rather than silently choosing a new meaning.

## Authority and status

| Label | Meaning and limit |
|---|---|
| Formal | Registered design, versioned authoritative contract or explicitly approved record, within its stated scope; not a universal data-accuracy claim |
| Provisional | Contract usable within recorded scope but not FINAL; bounded dataset acceptance does not finalize the contract |
| Draft | Proposal awaiting approval; design text is not implemented or accepted merely because it exists |
| Experimental | Bounded implementation, method or technical verification; technical PASS is not formal acceptance |
| Historical | Preserved account of a dated baseline, including superseded proposals; consult Current State before relying on its status statements |

These labels describe different dimensions and can coexist: a formal record can
be historical, and an authoritative versioned Standard can remain provisional.
Directory placement, update date, CLI completion and PR merge alone do not change
acceptance. Approval must identify its scope and evidence explicitly. This policy
does not relabel existing documents or ratify Standard Canopy.

## Documentation Impact in each PR

| Change | Review the owning documentation |
|---|---|
| Data semantics or schema | Architecture / Standard; obtain any required contract approval |
| CLI, input/output or processing boundary | Implementation / Interface and its source-linked usage |
| New verification results or corrected evidence | Verification / Acceptance, distinguishing technical results from approval |
| Gate, implementation status or unresolved issue | Relevant Current State and links to the owning evidence |

Include a **Documentation Impact** explanation in the PR description. State which
roles need updating and, for roles needing no update, why. Do not duplicate
numeric QA tables or hashes in Current State when a stable evidence link suffices.
When refreshing Current State, record the check date and full main commit; verify
implemented / verified / unimplemented claims against code and dated records.
Report local artifact availability separately from historical acceptance.

## History and restart procedure

Preserve past acceptance and experiment results by default. Corrections must
identify the erroneous statement, reason, target record and evidence correspondence;
prefer an additive correction record, as in the [Terrain source correction](acceptance/OUEM_A2_Terrain_Source_Provenance_Correction_20261026.md).
Do not retrospectively claim unexecuted verification. Deletion, relocation or
consolidation requires a separate review, preserving reproducibility and links;
the [repository inventory](experiments/voxcity_canopy_shadow/REPOSITORY_INVENTORY_20261027.md)
lists candidates, not authorized removals.

For a new chat/session, read [README](../README.md), the relevant Current State,
then the required Standard / Implementation and Verification / Acceptance sources.
An old plan or environment record is evidence of its date, not today's capability.
