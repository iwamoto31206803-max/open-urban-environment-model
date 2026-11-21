#Requires -Version 7.0
param([Parameter(Mandatory)] [string]$RunnerPath)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
. $RunnerPath

function Assert-Throws([scriptblock]$Action, [string]$Message) {
    try { & $Action } catch {
        if ($_.Exception.Message -like "*$Message*") { return }
        throw
    }
    throw "Expected failure: $Message"
}

if ((Invoke-CheckedGit --version) -notlike 'git version *') { throw 'Git invocation failed' }
Assert-Throws { Invoke-CheckedGit -C 'path that does not exist' rev-parse HEAD } 'failed (exit'

$root = Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($root)
try {
    $inputFile = Join-Path $root 'source.txt'
    [IO.File]::WriteAllText($inputFile, "provider HAG statement`n")
    $hash = (Get-FileHash -LiteralPath $inputFile).Hash
    Assert-PinnedFile $inputFile $hash
    [IO.File]::WriteAllText($inputFile, "provider HAG statement`r`n")
    Assert-Throws { Assert-PinnedFile $inputFile $hash } 'SHA-256 mismatch'
    Assert-Throws { Assert-FreshOutput $inputFile } 'already exists'

    # Model an autocrlf checkout and verify that the scoped override keeps raw LF bytes.
    $fixtureRepo = Join-Path $root 'git fixture'
    $fixtureTree = Join-Path $root 'detached fixture'
    Invoke-CheckedGit init -q $fixtureRepo
    $fixtureFile = Join-Path $fixtureRepo 'snapshot.txt'
    [IO.File]::WriteAllText($fixtureFile, "provider HAG statement`n")
    Invoke-CheckedGit -C $fixtureRepo -c core.autocrlf=false add snapshot.txt
    Invoke-CheckedGit -C $fixtureRepo -c user.name=Fixture -c user.email=fixture@example.invalid `
        -c core.hooksPath=NUL -c commit.gpgsign=false commit -qm fixture
    Invoke-CheckedGit -C $fixtureRepo -c core.autocrlf=false worktree add --detach $fixtureTree HEAD
    Assert-PinnedFile (Join-Path $fixtureTree 'snapshot.txt') $hash
    $crlfTree = Join-Path $root 'CRLF fixture'
    Invoke-CheckedGit -C $fixtureRepo -c core.autocrlf=true worktree add --detach $crlfTree HEAD
    Assert-Throws { Assert-PinnedFile (Join-Path $crlfTree 'snapshot.txt') $hash } 'SHA-256 mismatch'

    # The real launcher receives a stub instead of Python. It must never retry or touch the target.
    function FakePython {
        $script:stubCalls++
        $global:LASTEXITCODE = 7
    }
    $script:stubCalls = 0
    $fakeInputs = @{Chm='fake'; Acquisition='fake'; Terrain='fake'; Manifest='fake'
                    Acceptance='fake'; Area='fake'; Evidence='fake'}
    Assert-Throws { Invoke-EnvelopePreflight FakePython $root $fakeInputs } 'preflight failed (exit 7)'
    Assert-Throws { Invoke-EnvelopeCli FakePython $root $fakeInputs $inputFile } 'preserve diagnostics'
    if ($script:stubCalls -ne 2 -or [IO.File]::ReadAllText($inputFile) -ne "provider HAG statement`r`n") {
        throw 'Subprocess failure handling changed the fixture or retried'
    }

    function Invoke-CheckedGit {
        param([Parameter(ValueFromRemainingArguments)] [string[]]$Arguments)
        $joined = $Arguments -join ' '
        switch -Regex ($joined) {
            'remote get-url origin$' { 'https://github.com/iwamoto31206803-max/open-urban-environment-model.git' }
            'fetch ' { if ($script:failure -eq 'fetch') { throw 'synthetic fetch failure' } }
            'worktree add' {
                if ($script:failure -eq 'checkout') { throw 'synthetic checkout failure' }
                if ($joined -notmatch '-c core.autocrlf=false') { throw 'LF checkout option missing' }
                $script:code = $Arguments[-2]
                [void][IO.Directory]::CreateDirectory($script:code)
            }
            'rev-parse HEAD$' {
                if ($script:failure -eq 'stale') { 'old-head' }
                else { 'dc477ad6c6bb3d99e2b039fc319fa3b2f438cf43' }
            }
            'rev-parse --show-toplevel$' { $script:code }
            'status --porcelain' { if ($script:failure -eq 'dirty') { ' M source.py' } }
            'hash-object --no-filters' {
                if ($script:failure -eq 'module') { 'wrong-blob' }
                else { '40bc462e1b944e9fbd02f6e456e907905551ffee' }
            }
            default { throw "Unexpected Git arguments: $joined" }
        }
    }
    function Assert-RunnerProvenance($Repo, $Runner, $Pin, [switch]$Execute) {}
    function Assert-OperatorSession {}
    function Assert-PinnedFile($Path, $Expected) {
        if ((Split-Path -Leaf $Path) -eq $script:failure) { throw "fixture SHA mismatch: $Path" }
    }
    function Invoke-EnvelopePreflight($Python, $Code, $Inputs) {
        $script:preflights++
        if ($env:GDAL_PAM_ENABLED -ne 'NO') { throw 'PAM guard missing' }
        if ($script:failure -eq 'import') { throw 'Unexpected Height Envelope import origin' }
        if ($script:failure -eq 'destination') {
            $name = (Split-Path -Leaf $Code).Replace('envelope-code-', 'height-envelope-64m-')
            [void][IO.Directory]::CreateDirectory((Join-Path (Split-Path -Parent $Code) $name))
        }
    }
    function Invoke-EnvelopeCli($Python, $Code, $Inputs, $Output) {
        $script:launches++
        throw 'synthetic CLI failure'
    }

    $pam = $env:GDAL_PAM_ENABLED
    $script:preflights = 0
    $script:launches = 0
    $script:failure = ''
    [void][IO.Directory]::CreateDirectory((Join-Path $root 'data/work'))
    Invoke-KunitachiEnvelope $root $RunnerPath
    if ($script:preflights -ne 1 -or $script:launches -ne 0 -or
        (Get-ChildItem -LiteralPath (Join-Path $root 'data/work') -Filter 'kunitachi-height-envelope-*')) {
        throw 'Default mode created output or launched the CLI'
    }
    foreach ($name in @('python.exe','chmv2_aoi.tif','acquisition-record.json','standard.tif',
        'standard.tif.manifest.json','OUEM_A2_Standard_Terrain_Kunitachi_09LD1122_Acceptance_20261121.md',
        'kunitachi_09ld1122_canopy_64m.yaml','kunitachi_09ld1122_64m.json','kunitachi_meta_chmv2_hag_excerpt.txt')) {
        $script:failure = $name
        Assert-Throws { Invoke-KunitachiEnvelope $root $RunnerPath -Execute } 'fixture SHA mismatch'
    }
    foreach ($mode in @('stale','dirty','module')) {
        $script:failure = $mode
        Assert-Throws { Invoke-KunitachiEnvelope $root $RunnerPath -Execute } 'stale, dirty, or'
    }
    foreach ($mode in @('fetch','checkout')) {
        $script:failure = $mode
        Assert-Throws { Invoke-KunitachiEnvelope $root $RunnerPath -Execute } "synthetic $mode failure"
    }
    $script:failure = 'import'
    Assert-Throws { Invoke-KunitachiEnvelope $root $RunnerPath -Execute } 'unexpected Height Envelope import'
    $script:failure = 'destination'
    Assert-Throws { Invoke-KunitachiEnvelope $root $RunnerPath -Execute } 'output already exists'
    if ($script:launches -ne 0) { throw 'Failed preflight called CLI' }
    $script:failure = ''
    Assert-Throws { Invoke-KunitachiEnvelope $root $RunnerPath -Execute } 'synthetic CLI failure'
    if ($script:launches -ne 1 -or $env:GDAL_PAM_ENABLED -ne $pam) {
        throw 'CLI retried or environment was not restored'
    }
    Write-Host 'Synthetic operator checks PASS'
} finally {
    if ((Split-Path -Parent (Resolve-Path -LiteralPath $root).Path) -ne
        (Resolve-Path -LiteralPath ([IO.Path]::GetTempPath())).Path.TrimEnd('\', '/')) { throw 'Unsafe fixture cleanup path' }
    Remove-Item -LiteralPath $root -Recurse -Force
}
