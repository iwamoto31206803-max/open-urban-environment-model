# Development instructions

## Scope and authority

- Keep changes task-scoped; avoid unrelated refactoring and duplicated specs.
- Read the relevant authoritative documents before changing behavior:
  - `docs/OUEM_Concept_Architecture_v0.1.md`: conceptual baseline.
  - `docs/Phase_A_Implementation_Design_v0.1.md`: lifecycle and boundaries;
    read its current-status note before relying on historical status statements.
  - `docs/OUEM_Standard_Building_v0.1.md`
  - `docs/OUEM_Standard_Terrain_v0.1.md`
  - `docs/OUEM_VoxCity_Adapter_v0.1.md`
- Use `docs/acceptance/` for formal A2/A3 results and
  `experiments/a1_e2e_pilot/README.md` for Building acceptance. Acceptance is
  limited to recorded datasets and conditions; it does not prove nationwide
  applicability or make provisional contracts FINAL.
- Report conflicts between documents, code, and evidence. Update the owning
  document when behavior changes; link to existing procedures and records.

## Runtime and dependencies

- In Codex Cloud, use repository `.venv/bin/python` explicitly. If unavailable,
  report the setup problem rather than silently using another interpreter.
- Keep VoxCity 1.7.0 pinned in `pyproject.toml` to
  `fa212656305328a9a657973bae26f352bfe813bc`; changes require explicit approval.
- Codex Cloud validation and local Windows/QGIS acceptance are separate.
  On Windows, use `.venv\Scripts\python.exe` from an ordinary terminal, not
  OSGeo4W Shell. Follow `docs/architecture.md` and `scripts/work/README.md`;
  do not install OUEM into GIS Python or merge the runtimes.
- A3 VoxCity execution belongs in the OUEM venv, not the GIS runtime.

## Changes and validation

- Put reusable logic in `src/ouem/`; keep launchers thin.
- Add or update appropriate tests for code changes. Run relevant tests and
  `.venv/bin/python -m pytest -q` before handing off code changes. Report
  actual results, failures, skips, warnings, and checks that could not run.
- Synthetic tests do not establish real-data acceptance. Do not invent results
  or run real-data processing without explicit authorization. Record the
  actual environment, inputs, results, and limitations of authorized runs.
- Do not commit local datasets, generated artifacts, runtime snapshots,
  secrets, or caches. Follow `.gitignore` and the documented data layout;
  keep test fixtures small and synthetic.

## Git and pull requests

- Use a task branch. Do not push directly to `main` or automatically merge PRs.
- When PR creation is requested, create a Draft PR by default. Describe the
  change, validation, and any pending local acceptance.
- Before committing, inspect the diff and staged files for scope and artifacts.
