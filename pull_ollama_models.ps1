$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$env:OLLAMA_HOST = "127.0.0.1:11435"
$tags = Invoke-RestMethod -Uri "http://127.0.0.1:11435/api/tags" -TimeoutSec 5
if ($null -eq $tags) {
  throw "Project Ollama service is not responding on port 11435. Start it with .\run_ollama.ps1 first."
}

$ollama = Get-Command ollama -ErrorAction Stop
foreach ($model in @("qwen2.5:0.5b-instruct", "qwen2.5:1.5b-instruct")) {
  Write-Host "Pulling $model into the project Ollama store..." -ForegroundColor Cyan
  & $ollama.Source pull $model
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to pull $model (exit code $LASTEXITCODE)."
  }
}

& $ollama.Source list
