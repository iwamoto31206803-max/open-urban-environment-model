# Kunitachi 64 m Height Envelope operator

Use PowerShell 7 on Windows with the pinned OUEM `.venv`. Run these commands
from the OUEM repository root. Execution is for the owner on GEEKOM-A6 in
ordinary non-administrator PowerShell after review and merge.

```powershell
.\scripts\operations\run_kunitachi_envelope.ps1
.\scripts\operations\run_kunitachi_envelope.ps1 -Execute
```

The first command checks the saved inputs and the 4,096 grid centres. It
fetches `origin/main` and creates a unique detached code worktree under
`data/work`. The checkout uses command-scoped `core.autocrlf=false` so the
accepted manifest inputs retain their pinned LF bytes. Keep the code
worktree for provenance. Fetch updates Git metadata and requires network
access. The current checkout, saved inputs and Git configuration are unchanged.
Default mode creates no raster output directory.

`-Execute` repeats verification and calls the existing CLI once. The
runner must match its committed copy on fetched `origin/main`; the code
worktree is pinned independently. An error stops the attempt and leaves any
diagnostics at the printed path. A provisional completion requires the three
rasters and a `COMPLETED` manifest. Share the console result and manifest path
for separate read-only QA. The scenario remains an uncalibrated engineering
trial. CHM zero is a valid sample; ecological absence is outside the result.

Windows PowerShell 5.1 is unsupported. If execution policy blocks the script,
report that to the owner. No execution-policy override is required by the runner.

Synthetic checks (Windows PowerShell 7):

```powershell
.\tests\kunitachi_envelope_operator.ps1 -RunnerPath .\scripts\operations\run_kunitachi_envelope.ps1
```

See [Issue #215](https://github.com/iwamoto31206803-max/open-urban-environment-model/issues/215) for the approved scope.
