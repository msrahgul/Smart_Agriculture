$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$modelStore = Join-Path $root ".ollama\models"
New-Item -ItemType Directory -Force -Path $modelStore | Out-Null

$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
  $defaultPath = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
  if (Test-Path $defaultPath) {
    $ollamaExe = $defaultPath
  } else {
    throw "Ollama executable not found. Install Ollama, then run this script again."
  }
} else {
  $ollamaExe = $ollama.Source
}

$env:OLLAMA_MODELS = $modelStore
$env:OLLAMA_HOST = "127.0.0.1:11435"
# The managed shell can inject a loopback proxy that is unavailable to this
# standalone service. Preserve real configured proxies; clear only that stub.
foreach ($proxyName in @("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy")) {
  $proxyValue = [Environment]::GetEnvironmentVariable($proxyName, "Process")
  if ($proxyValue -match "^https?://127\.0\.0\.1:9/?$") {
    [Environment]::SetEnvironmentVariable($proxyName, $null, "Process")
  }
}
Write-Host "Starting project Ollama service on $env:OLLAMA_HOST"
Write-Host "Model storage: $modelStore"
& $ollamaExe serve
