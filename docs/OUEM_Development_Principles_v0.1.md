# OUEM Development Principles v0.1

Status: **Adopted development policy**, agreed by the user on 2026-10-28.
This is the shared reference for User, ChatGPT and Codex throughout OUEM
development. It defines how to develop, not a new implementation milestone.

## P1. Purpose & Evidence Driven

Prioritize capabilities needed for urban environmental assessment. Judge
technical feasibility, scientific validity and applicability using evidence
appropriate to each claim. Distinguish future proposals from implemented,
available functionality.

## P2. Iterative Exploration & Stabilization

Alternate exploration with generalization and stabilization. During exploration,
consider reuse and responsibility boundaries without building for unconfirmed
requirements. Stabilize through shared logic, configuration and validation as
usage is demonstrated. Adjust the emphasis to purpose and maturity rather than
separating these activities into rigid stages.

## P3. Minimum Sufficient Complexity

Choose a structure that is understandable, changeable and verifiable across
code, abstractions, dependencies, configuration, execution and documentation.
Keep changes localized and understandable, with their effects traceable to the
responsible processing and tests. Make supported functions and execution steps
easy for users to find and use, with prerequisites and limits visible.
Avoid elaborate handling of hypothetical rare exceptions and abstractions built
only for the future; fail clearly for unsupported inputs when appropriate.
When adding an implementation, consider consolidation or retirement of older
paths. Retain complexity required for scientific reliability, reproducibility
and safety.

## P4. Clear Boundaries & Reusability

Respect Raw / Native / Standard / Adapter responsibilities. Use configuration
for regional, input-data and analysis-condition differences where actually needed.
Avoid copying implementations per region; share logic when it improves real
reuse, not to create abstractions for their own sake.
Give new functionality a clear user entry point and an owning module. Keep
module responsibilities, dependencies and related tests discoverable so developers
can locate the cause and impact of errors or improvement requests.

## P5. Reproducibility & Controlled Change

Keep inputs, configuration, processing conditions and output provenance traceable.
Respect existing formal contracts and the scope of Acceptance; identify and
validate the impact of changes. Distinguish automated tests, technical E2E
success, scientific validity and formal Acceptance.

## P6. Maintainable Knowledge

Identify the authoritative references for specifications, implementation and
verification. Update or link existing owners before adding documents; avoid
unnecessary duplicate specifications and temporary development records. Use
README and existing usage guides as concise routes to available functionality,
its owning implementation and verification; update these routes when behavior
or entry points change. Keep AI starting context small and retrieve relevant
knowledge when needed, rather than supplying the entire history for every task.

For each addition or change, briefly check: which existing module owns it, and
is a new module necessary? Where will users access it? Can a developer locate
the responsible processing and tests when it fails? Does README or an existing
execution guide need updating? Use these questions in ordinary work and review,
without introducing a separate approval gate or mandatory document.

## Collaboration and decision boundaries

| Role | Responsibility |
|---|---|
| User | Objectives, priorities, scientific judgment and approval of consequential design changes. |
| ChatGPT | Organize design proposals, compare options, discuss work direction and support PR review. |
| Codex | Repository investigation, concrete implementation design, code changes, tests, documentation and PR creation. |

Delegate coherent objectives with scope, constraints and completion criteria.
Codex decides routine implementation methods, naming, task-scoped cleanup and
necessary tests autonomously. Changes to scientific assumptions, formal data
contracts, Acceptance, major dependencies or significant architecture require
explicit user authorization; use authorization already given in the task.

## Relationship to existing documents

[Concept & Architecture v0.2](OUEM_Concept_Architecture_v0.2.md) remains the
formally registered upper conceptual design. Standards and acceptance records
retain their own authority and scope. These principles neither amend them nor
close source-H eligibility, scientific-validation or Phase 5 gates.
[Documentation Governance](OUEM_Documentation_Governance_v0.1.md) remains
**proposed**; adopting these principles does not ratify that policy.
[AGENTS.md](../AGENTS.md) contains daily Codex instructions; the
[README](../README.md) and Current State documents navigate implementation and
evidence. This policy authorizes no E2E refactoring, extent configuration,
new source integration or algorithm change by itself.
