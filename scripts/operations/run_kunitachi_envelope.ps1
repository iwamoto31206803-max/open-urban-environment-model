#Requires -Version 7.0
[CmdletBinding()]
param([switch]$Execute)

function Invoke-CheckedGit {
    param([Parameter(ValueFromRemainingArguments)] [string[]]$Arguments)
    $result = & git @Arguments
    if ($LASTEXITCODE -ne 0) { throw "git $($Arguments -join ' ') failed (exit $LASTEXITCODE)" }
    $result
}

function Assert-PinnedFile($Path, $Expected) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf) -or
        (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash -ne $Expected) {
        throw "Missing file or SHA-256 mismatch: $Path"
    }
}

function Assert-FreshOutput($Path) {
    # Include broken symbolic links and other directory entries.
    if (Get-ChildItem -LiteralPath (Split-Path -Parent $Path) -Force |
        Where-Object Name -EQ (Split-Path -Leaf $Path)) {
        throw "Output already exists: $Path"
    }
}

function Assert-PinnedWorktree($Code, $Pin, $Blob) {
    if ((Invoke-CheckedGit -C $Code rev-parse HEAD) -ne $Pin -or
        (Resolve-Path -LiteralPath (Invoke-CheckedGit -C $Code rev-parse --show-toplevel)).Path -ne $Code -or
        (Invoke-CheckedGit --no-optional-locks -C $Code status --porcelain --untracked-files=all) -or
        (Invoke-CheckedGit -C $Code hash-object --no-filters src/ouem/height_envelope.py) -ne $Blob) {
        throw 'Pinned worktree is stale, dirty, or has unexpected implementation bytes'
    }
}

function Assert-RunnerProvenance($Repo, $Runner, $Pin, [switch]$Execute) {
    $relative = 'scripts/operations/run_kunitachi_envelope.ps1'
    Invoke-CheckedGit -C $Repo merge-base --is-ancestor $Pin origin/main
    $runnerBlob = Invoke-CheckedGit -C $Repo hash-object --path=$relative -- $Runner
    if ($runnerBlob -ne (Invoke-CheckedGit -C $Repo rev-parse "HEAD:${relative}")) {
        throw 'The runner differs from its committed version'
    }
    if ($Execute -and $runnerBlob -ne (Invoke-CheckedGit -C $Repo rev-parse "origin/main:${relative}")) {
        throw 'The execution runner must match the reviewed version on origin/main'
    }
    Write-Host "Runner HEAD: $(Invoke-CheckedGit -C $Repo rev-parse HEAD)"
}

function Invoke-EnvelopePreflight($Python, $Code, $Inputs) {
    @'
from pathlib import Path
import sys

if sys.version_info[:3] != (3, 11, 9):
    raise SystemExit("Unexpected Python version")
code, chm, acquisition, terrain, manifest, acceptance, area, evidence = map(
    Path, sys.argv[1:]
)
source = code / "src"
sys.path.insert(0, str(source))
import numpy as np
import ouem.height_envelope as envelope

if Path(envelope.__file__).resolve() != source / "ouem/height_envelope.py":
    raise SystemExit("Unexpected Height Envelope import origin")

envelope.validate_sources(chm, acquisition, evidence, terrain, manifest, acceptance)
grid = envelope.GridSpec.from_study_area(area, 1.0)
if (grid.epsg, grid.bounds, grid.width, grid.height) != (
    6677, (-35032, -33782, -34968, -33718), 64, 64
):
    raise SystemExit("Unexpected pilot grid")
for label, path in (("CHM", chm), ("DEM", terrain)):
    samples = envelope.sample_raster(path, grid, method="nearest")
    if (samples.values.size != 4096 or not np.isfinite(samples.values).all()
            or (label == "CHM" and (samples.values < 0).any())
            or samples.missing.any() or samples.outside.any()):
        raise SystemExit(f"{label}: unexpected coverage or values")
    print(f"{label}: 4096 valid centres; {int((samples.values == 0).sum())} valid zeros")
print(f"PREFLIGHT PASS: {envelope.__file__}")
'@ | & $Python -B -I - $Code $Inputs.Chm $Inputs.Acquisition $Inputs.Terrain $Inputs.Manifest $Inputs.Acceptance $Inputs.Area $Inputs.Evidence
    if ($LASTEXITCODE -ne 0) { throw "Height Envelope preflight failed (exit $LASTEXITCODE)" }
}

function Invoke-EnvelopeCli($Python, $Code, $Inputs, $Output) {
    # Use the same isolated import path as preflight, then invoke the existing CLI.
    @'
from pathlib import Path
import sys

source = Path(sys.argv.pop(1)) / "src"
sys.path.insert(0, str(source))
import ouem.height_envelope as envelope
if Path(envelope.__file__).resolve() != source / "ouem/height_envelope.py":
    raise SystemExit("Unexpected Height Envelope import origin")
sys.argv[0] = "ouem.height_envelope"
raise SystemExit(envelope.main())
'@ | & $Python -B -I - $Code --chm $Inputs.Chm --acquisition-record $Inputs.Acquisition `
        --terrain $Inputs.Terrain --terrain-manifest $Inputs.Manifest --terrain-acceptance $Inputs.Acceptance `
        --study-area $Inputs.Area --chm-evidence $Inputs.Evidence --output-dir $Output `
        --cr 0.60 --resolution 1 --dem-sampling nearest
    $runExit = $LASTEXITCODE
    Write-Host "Height Envelope exit code: $runExit"
    if ($runExit -ne 0) { throw "Generation failed; preserve diagnostics at $Output" }
    foreach ($name in @('canopy_top_z.tif','canopy_bottom_z.tif','height_envelope_state.tif','height_envelope_manifest.json')) {
        if (-not (Test-Path -LiteralPath (Join-Path $Output $name) -PathType Leaf)) {
            throw "Missing output: $name"
        }
    }
    $manifest = Join-Path $Output 'height_envelope_manifest.json'
    if ((Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json).status -ne 'COMPLETED') {
        throw 'Manifest is not COMPLETED'
    }
    Write-Host "Provisional completion: $manifest"
}

function Assert-OperatorSession {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    try {
        if (([Security.Principal.WindowsPrincipal]::new($identity)).IsInRole(
            [Security.Principal.WindowsBuiltInRole]::Administrator) -or
            $env:COMPUTERNAME -ne 'GEEKOM-A6' -or $env:CODEX_SESSION_ID) {
            throw 'Execute is for ordinary non-admin PowerShell on GEEKOM-A6'
        }
    } finally { $identity.Dispose() }
}

function Invoke-KunitachiEnvelope($Repo, $Runner, [switch]$Execute) {
    if (-not $IsWindows) { throw 'PowerShell 7 on Windows is required' }
    if ($Execute) { Assert-OperatorSession }
    if ((Invoke-CheckedGit -C $Repo remote get-url origin) -ne
        'https://github.com/iwamoto31206803-max/open-urban-environment-model.git') {
        throw 'Unexpected repository origin'
    }
    $pin = 'dc477ad6c6bb3d99e2b039fc319fa3b2f438cf43'
    $blob = '40bc462e1b944e9fbd02f6e456e907905551ffee'
    $work = (Resolve-Path -LiteralPath (Join-Path $Repo 'data/work')).Path
    $suffix = [guid]::NewGuid().ToString('N')
    $code = Join-Path $work "kunitachi-envelope-code-$suffix"
    $output = Join-Path $work "kunitachi-height-envelope-64m-$suffix"
    Assert-FreshOutput $code
    Assert-FreshOutput $output
    $python = Join-Path $Repo '.venv/Scripts/python.exe'
    Assert-PinnedFile $python '21bb438c0d4a6f1f164b9a646f6ee000340185e5871180aec06db8d3f07c0082'
    Invoke-CheckedGit -C $Repo fetch --no-tags origin 'refs/heads/main:refs/remotes/origin/main'
    Assert-RunnerProvenance $Repo $Runner $pin -Execute:$Execute
    Invoke-CheckedGit -C $Repo -c core.autocrlf=false worktree add --detach $code $pin
    Assert-PinnedWorktree $code $pin $blob
    Write-Host "Pinned code: $code ($pin)"
    Write-Host "Proposed output: $output"

    $chm = Join-Path $work 'kunitachi-source-preflight/20261030-01/chm'
    $terrain = Join-Path $work 'kunitachi-terrain-09ld1122-0ae94113b7'
    $inputs = @{
        Chm = Join-Path $chm 'chmv2_aoi.tif'
        Acquisition = Join-Path $chm 'acquisition-record.json'
        Terrain = Join-Path $terrain 'standard.tif'
        Manifest = Join-Path $terrain 'standard.tif.manifest.json'
        Acceptance = Join-Path $code 'docs/acceptance/OUEM_A2_Standard_Terrain_Kunitachi_09LD1122_Acceptance_20261121.md'
        Area = Join-Path $code 'config/study_areas/kunitachi_09ld1122_canopy_64m.yaml'
        Evidence = Join-Path $code 'config/canopy_evidence/kunitachi_09ld1122_64m.json'
        Snapshot = Join-Path $code 'config/canopy_evidence/kunitachi_meta_chmv2_hag_excerpt.txt'
    }
    $pins = @{
        Chm = '2355b33f4d14a728620ac7b9543c44cf85f0c7039c4efb6c426a61207d66982a'
        Acquisition = 'ddea23791505db046e42ef016d2759de308563e7ab7a15027b24f36f1dc9b4de'
        Terrain = 'e361663312a7d2c72308ba6a97bbf67411b7d0fffdefa871301684821147c124'
        Manifest = 'b7bafcf13d66e2991f7cc1fce364b116149cde4aaa83474d68b4b43bee54840b'
        Acceptance = '82fdf300062eed5e0758d3ab4dbd4a5fd70f126247c432dd36a18415bc9e898a'
        Area = '9161b2e24068dae6eee09494b76f8f74d4e68ec1e70881caae16f5c56904a438'
        Evidence = 'd06405d3c6272fdceaf271500621f4779d134e2dcbbdcb1fa3550b457c4caeba'
        Snapshot = 'e12f14a85773924a6a1d1e0cf78abec037b20e8d27b2752e529b6cace515b828'
    }
    $oldPam = $env:GDAL_PAM_ENABLED
    try {
        $env:GDAL_PAM_ENABLED = 'NO'
        foreach ($key in $pins.Keys) { Assert-PinnedFile $inputs[$key] $pins[$key] }
        Invoke-EnvelopePreflight $python $code $inputs
        if ($Execute) {
            Assert-PinnedWorktree $code $pin $blob
            Assert-PinnedFile $python '21bb438c0d4a6f1f164b9a646f6ee000340185e5871180aec06db8d3f07c0082'
            foreach ($key in $pins.Keys) { Assert-PinnedFile $inputs[$key] $pins[$key] }
            Assert-FreshOutput $output
            Invoke-EnvelopeCli $python $code $inputs $output
        }
    } finally {
        $env:GDAL_PAM_ENABLED = $oldPam
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    $ErrorActionPreference = 'Stop'
    # Handle native failures explicitly, including on hosts with this preference enabled.
    $PSNativeCommandUseErrorActionPreference = $false
    $repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
    Invoke-KunitachiEnvelope $repo $PSCommandPath -Execute:$Execute
}
