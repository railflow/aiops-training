# Run k6 again and again from your laptop so dashboards always have fresh data. Stop with Ctrl+C.
# Usage: .\loop.ps1 -Rate 5 -Minutes 10
param([int]$Rate = 5, [int]$Minutes = 10)
Set-Location (Join-Path $PSScriptRoot '..\..\monitoring\k6')
while ($true) {
  Write-Host ("{0:HH:mm:ssZ} starting k6 round: {1}/s for {2}m" -f (Get-Date).ToUniversalTime(), $Rate, $Minutes)
  k6 run --quiet -e RATE=$Rate -e DURATION="${Minutes}m" loop.js
  if ($LASTEXITCODE -ne 0) { Write-Host "k6 exited non-zero (a threshold failed?); continuing" }
}
