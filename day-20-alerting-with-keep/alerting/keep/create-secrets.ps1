# Creates the Kubernetes Secrets Keep needs, with generated values. Nothing secret is written to a file or to git.
# Requires: kubectl pointed at kind-ai-ops-training and the ClickHouse Secret from Day 17. Works in Windows PowerShell 5.1 and PowerShell 7.
# Secrets are sent to kubectl on stdin as JSON, which avoids the quote-mangling Windows PowerShell 5.1 applies to
# command-line arguments that contain double quotes (the providers value is JSON).
# Re-running replaces the Secrets with NEW random values (and invalidates old API keys): re-run on purpose only.
$ErrorActionPreference = 'Stop'
$ctx = 'kind-ai-ops-training'

function New-RandomHex([int]$bytes) {
  $b = New-Object byte[] $bytes
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
  -join ($b | ForEach-Object { $_.ToString('x2') })
}
function Set-K8sSecret([string]$name, [hashtable]$data) {
  @{ apiVersion = 'v1'; kind = 'Secret'; metadata = @{ name = $name; namespace = 'keep' }; stringData = $data } |
    ConvertTo-Json -Depth 8 | kubectl --context $ctx apply -f -
}

kubectl --context $ctx create namespace keep --dry-run=client -o yaml | kubectl --context $ctx apply -f -

$adminPassword = New-RandomHex 12
$gatusKey      = New-RandomHex 24
$adminKey      = New-RandomHex 24
$b64 = kubectl --context $ctx -n observability get secret clickhouse-credentials -o jsonpath='{.data.password}'
$chPassword = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64))

Set-K8sSecret 'keep-auth' @{
  AUTH_TYPE             = 'DB'
  KEEP_JWT_SECRET       = (New-RandomHex 32)
  KEEP_DEFAULT_USERNAME = 'keep'
  KEEP_DEFAULT_PASSWORD = $adminPassword
  KEEP_DEFAULT_API_KEYS = "gatus:webhook:$gatusKey,admin-cli:admin:$adminKey"
  KEEP_GATUS_API_KEY    = $gatusKey
}
Set-K8sSecret 'keep-ui' @{ AUTH_TYPE = 'DB'; NEXTAUTH_SECRET = (New-RandomHex 32) }

$providers = [ordered]@{
  'clickhouse-otel' = @{ type = 'clickhouse'; authentication = @{ host = 'clickhouse.observability'; port = 9000; username = 'otel'; password = $chPassword; database = 'otel'; protocol = 'clickhouse' } }
  'mailpit'         = @{ type = 'smtp';       authentication = @{ smtp_server = 'mailpit.keep'; smtp_port = 1025; encryption = 'None' } }
  'echo-sink'       = @{ type = 'webhook';    authentication = @{ url = 'http://echo-sink.keep'; method = 'POST'; verify = $false } }
} | ConvertTo-Json -Depth 6 -Compress
Set-K8sSecret 'keep-providers' @{ KEEP_PROVIDERS = $providers }

Write-Host "Secrets created in namespace keep: keep-auth, keep-ui, keep-providers."
Write-Host "Admin login: user 'keep'. Read the password with:"
Write-Host "  `$p = kubectl -n keep get secret keep-auth -o jsonpath='{.data.KEEP_DEFAULT_PASSWORD}'; [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String(`$p))"
