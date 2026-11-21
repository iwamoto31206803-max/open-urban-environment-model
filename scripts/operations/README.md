# Kunitachi 64 m Height Envelope operator

Use PowerShell 7 on Windows with the pinned OUEM `.venv`. On GEEKOM-A6,
open ordinary non-administrator PowerShell at the existing OUEM data
checkout root. After the reviewed runner is merged, fetch main and put the
operator in a separate detached worktree. The old checkout can remain on
its existing branch, with its local files and `.venv` in place.

```powershell
$dataRepo = (Get-Location).Path
git -C $dataRepo fetch --no-tags origin 'refs/heads/main:refs/remotes/origin/main'
if ($LASTEXITCODE -ne 0) { throw 'Could not fetch main' }
$operatorRepo = Join-Path $dataRepo ('data/work/kunitachi-operator-' + [guid]::NewGuid().ToString('N'))
git -C $dataRepo worktree add --detach $operatorRepo origin/main
if ($LASTEXITCODE -ne 0) { throw 'Could not create the operator worktree' }
$runner = Join-Path $operatorRepo 'scripts/operations/run_kunitachi_envelope.ps1'
& $runner -DataRepo $dataRepo
```

Review the preflight result. When ready to run, use the same session and
paths:

```powershell
& $runner -DataRepo $dataRepo -Execute
```

`-DataRepo` supplies the existing checkout's saved inputs, output parent,
and pinned Python. Runner provenance comes from the separate operator
checkout. Fetch/worktree commands update shared Git metadata without
switching, resetting or rebasing the original checkout. The operator
script itself may have CRLF line endings. Git compares its filtered blob
against its commits; the data and evidence SHA checks still use raw bytes.

The `COMPUTERNAME` and `CODEX_SESSION_ID` checks are operational safeguards.
They cannot establish the sandbox boundary. The owner must use ordinary
non-elevated PowerShell on GEEKOM-A6.

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
