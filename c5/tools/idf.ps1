param(
    [Parameter(Position=0,ValueFromRemainingArguments=$true)][string[]]$IdfArguments,
    [Alias('p')][string]$Port,
    [string]$IdfRoot = 'D:\Espressif\frameworks\esp-idf-v5.5.1',
    [string]$ToolsRoot = 'D:\Espressif'
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pythonRoot = Join-Path $ToolsRoot 'python_env\idf5.5_py3.11_env'
$pythonExe = Join-Path $pythonRoot 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw "IDF Python not found: $pythonExe" }
if (-not (Test-Path -LiteralPath (Join-Path $IdfRoot 'export.ps1'))) { throw "ESP-IDF not found: $IdfRoot" }
$env:IDF_TOOLS_PATH = $ToolsRoot
$env:IDF_PYTHON_ENV_PATH = $pythonRoot
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:CCACHE_DISABLE = '1'
# Scope Git ownership exceptions to this build process, never the global user config.
$count = if ($env:GIT_CONFIG_COUNT) { [int]$env:GIT_CONFIG_COUNT } else { 0 }
Set-Item -Path "Env:GIT_CONFIG_KEY_$count" -Value 'safe.directory'
Set-Item -Path "Env:GIT_CONFIG_VALUE_$count" -Value $IdfRoot.Replace('\','/')
$count++
Set-Item -Path "Env:GIT_CONFIG_KEY_$count" -Value 'safe.directory'
Set-Item -Path "Env:GIT_CONFIG_VALUE_$count" -Value (Split-Path $projectRoot -Parent).Replace('\','/')
$env:GIT_CONFIG_COUNT = [string]($count + 1)
$env:Path = (Join-Path $pythonRoot 'Scripts') + ';' + $env:Path
Push-Location $projectRoot
try {
    . (Join-Path $IdfRoot 'export.ps1')
    if (-not $IdfArguments) { $IdfArguments = @('build') }
    if ($Port) { $IdfArguments = @('-p', $Port) + $IdfArguments }
    & $pythonExe (Join-Path $IdfRoot 'tools\idf.py') '--no-ccache' @IdfArguments
    $result = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $result
