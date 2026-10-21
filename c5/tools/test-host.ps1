param([string]$Compiler)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $Compiler) { $Compiler = Join-Path $root 'build-host\tcc\tcc.exe' }
if (-not (Test-Path -LiteralPath $Compiler)) {
    throw 'Provide -Compiler <path-to-tcc-or-gcc>. See README for the portable test compiler.'
}
$output = Join-Path $root 'build-host'
New-Item -ItemType Directory -Path $output -Force | Out-Null
$executable = Join-Path $output 'test_core.exe'
$compileArguments = @(
    '-Wall', '-Werror', '-std=c99', '-I', (Join-Path $root 'components\module_core\include'),
    (Join-Path $root 'tests\test_core.c'),
    (Join-Path $root 'components\module_core\module_protocol.c'),
    (Join-Path $root 'components\module_core\module_record.c'),
    (Join-Path $root 'components\module_core\network_policy.c'),
    (Join-Path $root 'components\module_core\module_at.c'),
    (Join-Path $root 'components\module_core\module_lte.c'),
    (Join-Path $root 'components\module_core\module_indicator.c'),
    (Join-Path $root 'components\module_core\module_runtime_policy.c'),
    (Join-Path $root 'components\module_core\module_supervision.c'),
    (Join-Path $root 'components\module_core\module_blob.c'),
    (Join-Path $root 'components\module_core\module_events.c'),
    '-o', $executable
)
& $Compiler @compileArguments
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $executable
exit $LASTEXITCODE
