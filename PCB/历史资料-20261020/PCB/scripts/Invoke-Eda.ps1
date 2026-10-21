param([Parameter(Mandatory=$true)][string]$CodeFile,[string]$OutputFile)
$ErrorActionPreference='Stop'
$health=Invoke-RestMethod -Uri 'http://127.0.0.1:49620/health' -TimeoutSec 3
if($health.service -ne 'easyeda-bridge' -or -not $health.edaConnected){throw 'Bridge or EDA unavailable'}
$payload=@{code=(Get-Content -LiteralPath $CodeFile -Raw -Encoding utf8);windowId=$health.activeWindowId}|ConvertTo-Json -Compress
$result=Invoke-RestMethod -Uri 'http://127.0.0.1:49620/execute' -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($payload)) -TimeoutSec 50
if(-not $result.success){throw ($result|ConvertTo-Json -Compress)}
$json=$result|ConvertTo-Json -Depth 50
if($OutputFile){Set-Content -LiteralPath $OutputFile -Value $json -Encoding utf8}
$json


