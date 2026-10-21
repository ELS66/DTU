[CmdletBinding(PositionalBinding=$false)]
param(
    [switch]$SelfTest,
    [string]$Port,
    [string]$Python = 'D:\Espressif\python_env\idf5.5_py3.11_env\Scripts\python.exe',
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$SimulatorArguments
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not (Test-Path -LiteralPath $Python)) { throw 'Python not found; provide -Python <path>.' }
$env:PYTHONDONTWRITEBYTECODE = '1'
if ($SelfTest) {
    & $Python -m unittest discover -s (Join-Path $projectRoot 'tests') -p 'test_bench.py' -v
} else {
    if (-not $Port) { throw 'Provide -Port for the USB-to-3.3V-TTL adapter, not the ESP USB console.' }
    & $Python (Join-Path $PSScriptRoot 'board_simulator.py') --port $Port @SimulatorArguments
}
exit $LASTEXITCODE
