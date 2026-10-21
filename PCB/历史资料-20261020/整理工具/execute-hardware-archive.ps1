$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath('D:\DTU').TrimEnd('\')
$planPath = 'D:\DTU\PCB\历史资料-20261020\归档迁移计划.json'
$plan = Get-Content -LiteralPath $planPath -Raw -Encoding utf8 | ConvertFrom-Json
function Assert-WorkspacePath([string]$path) {
    $absolute = [IO.Path]::GetFullPath($path)
    if (-not $absolute.StartsWith($workspace + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "路径超出工作目录：$absolute"
    }
    return $absolute
}
# Validate every recursive move's exact source and destination before any mutation.
# Top-level moves rename directories without walking their dependency junctions.
foreach ($item in $plan.moves) {
    $source = Assert-WorkspacePath (Resolve-Path -LiteralPath $item.source).Path
    $destination = Assert-WorkspacePath $item.destination
    if ((Get-Item -LiteralPath $source -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "不移动顶层链接：$source"
    }
    if (Test-Path -LiteralPath $destination) { throw "目标已存在：$destination" }
}
foreach ($item in $plan.copyFiles) {
    $destination = Assert-WorkspacePath $item.destination
    if (-not (Test-Path -LiteralPath $item.source -PathType Leaf)) { throw "缺少源文件：$($item.source)" }
    if (Test-Path -LiteralPath $destination) { throw "目标已存在：$destination" }
}
$journal = Join-Path $plan.historyDirectory '已执行操作.ndjson'
foreach ($item in $plan.copyFiles) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $item.destination) -Force | Out-Null
    Copy-Item -LiteralPath $item.source -Destination $item.destination
    $hash = (Get-FileHash -LiteralPath $item.destination -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($hash -ne $item.sha256) { throw "复制校验失败：$($item.destination)" }
    @{action='copy';source=$item.source;destination=$item.destination;sha256=$hash} | ConvertTo-Json -Compress | Add-Content -LiteralPath $journal -Encoding utf8
}
foreach ($item in $plan.moves) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $item.destination) -Force | Out-Null
    Move-Item -LiteralPath $item.source -Destination $item.destination
    @{action='move';source=$item.source;destination=$item.destination} | ConvertTo-Json -Compress | Add-Content -LiteralPath $journal -Encoding utf8
}
Write-Output "已复制 $($plan.copyFiles.Count) 个最终文件，已归档 $($plan.moves.Count) 个目录或文件。"
