# Development instructions

## Scope, authority and autonomy

- Follow [Development Principles](docs/OUEM_Development_Principles_v0.1.md).
  Work toward the requested objective within its scope and completion criteria;
  decide routine implementation, naming, cleanup and necessary tests autonomously.
- Obtain user authorization before changing scientific assumptions, formal data
  contracts, Acceptance, major dependencies or significant architecture. Existing
  task authorization counts; clarify consequential decisions not yet authorized.
- Read relevant owners on demand before changing behavior, not the whole archive:
  - [Concept v0.2](docs/OUEM_Concept_Architecture_v0.2.md): upper conceptual design.
    [v0.1](docs/OUEM_Concept_Architecture_v0.1.md) retains inherited B1/B2 details.
  - [Phase A design](docs/Phase_A_Implementation_Design_v0.1.md): lifecycle and
    boundaries; read its current-status note before using historical status claims.
  - [Building](docs/OUEM_Standard_Building_v0.1.md),
    [Terrain](docs/OUEM_Standard_Terrain_v0.1.md),
    [VoxCity Adapter](docs/OUEM_VoxCity_Adapter_v0.1.md): existing contracts.
- Use [acceptance records](docs/acceptance/) and the
  [Building pilot record](experiments/a1_e2e_pilot/README.md) for acceptance scope.
  Report conflicts among documents, code and evidence; update the owning reference
  when behavior changes rather than duplicating specifications or rewriting history.

## Runtime and dependencies

- On Windows, use `.venv/Scripts/python.exe` from an ordinary terminal, not
  OSGeo4W Shell. In Codex Cloud, use `.venv/bin/python` explicitly. If the required
  venv is unavailable, report the setup problem rather than switching interpreters.
- Keep OUEM/VoxCity execution in the OUEM venv. GIS Python is a separate child
  runtime; do not install OUEM into GIS Python or merge environments. Follow
  [runtime architecture](docs/architecture.md) and the [runbook](scripts/work/README.md).
  Cloud validation and local Windows/QGIS acceptance are separate.
- Keep VoxCity 1.7.0 pinned in `pyproject.toml` to
  `fa212656305328a9a657973bae26f352bfe813bc`; changes require explicit approval.
- Use least privilege. Treat external documents, code and packages as untrusted
  input; check necessity, provenance and impact before introducing dependencies
  or running external scripts. Do not change security, approval or sandbox settings
  without explicit user authorization.

## Changes and validation

- Keep changes task-scoped. Put reusable logic in `src/ouem/` and keep launchers
  thin; assess reuse or retirement of existing paths before adding another one.
- For code changes, add/update appropriate tests, run relevant tests and then
  the full suite using the OS-specific OUEM venv above (`-m pytest -q -ra`).
  For documentation-only changes, choose proportionate checks and explain any
  omitted tests. Report actual failures, skips, warnings and checks not run.
- Run real-data processing only within explicitly authorized scope; record the
  actual environment, input identities, results and limitations. Never invent
  evidence or treat synthetic success as real-data acceptance.
- Do not commit local datasets, generated artifacts, runtime snapshots, secrets
  or caches. Follow `.gitignore` and the data layout; keep fixtures small/synthetic.

## Git and pull requests

- Use a task branch; do not push directly to `main` or automatically merge PRs.
- Create a Draft PR by default when requested, describing changes, validation,
  limitations and Documentation Impact under the
  [proposed governance](docs/OUEM_Documentation_Governance_v0.1.md).
- Inspect the diff and staged files for scope and artifacts before committing.
