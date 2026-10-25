$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$ollamaUrl = "http://127.0.0.1:11435/api/chat"

if (-not (Test-Path $venvPython)) {
  Write-Host "ERROR: Virtual environment not found at .venv" -ForegroundColor Red
  Write-Host "Create it first:" -ForegroundColor Yellow
  Write-Host "  python -m venv .venv"
  Write-Host "  .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
  exit 1
}

# Use an app-specific Ollama service and model store. The default Ollama
# installation stores models on C:, which may not have enough free space.
$env:OLLAMA_URL = $ollamaUrl
$ollamaReady = $false
try {
  Invoke-RestMethod -Uri "http://127.0.0.1:11435/api/tags" -TimeoutSec 2 | Out-Null
  $ollamaReady = $true
} catch {}

if (-not $ollamaReady) {
  $ollamaScript = Join-Path $root "run_ollama.ps1"
  $launch = "& '$ollamaScript'"
  $encodedLaunch = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($launch))
  Start-Process -FilePath (Join-Path $PSHOME "powershell.exe") `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $encodedLaunch) `
    -WindowStyle Hidden

  for ($attempt = 0; $attempt -lt 20; $attempt++) {
    Start-Sleep -Milliseconds 500
    try {
      Invoke-RestMethod -Uri "http://127.0.0.1:11435/api/tags" -TimeoutSec 2 | Out-Null
      $ollamaReady = $true
      break
    } catch {}
  }
}

if ($ollamaReady) {
  Write-Host "Ollama endpoint ready: $ollamaUrl" -ForegroundColor Green
} else {
  Write-Host "Ollama endpoint did not start. Chat data tools still work; LLM features need Ollama." -ForegroundColor Yellow
}

Write-Host "Using: $venvPython"
& $venvPython -c "import sys; print('python:', sys.executable); print('version:', sys.version.split(' ',1)[0])"
& $venvPython -c "import google.protobuf as pb; print('protobuf:', getattr(pb,'__version__',None))"
& $venvPython -c "from importlib.metadata import version; print('tensorflow:', version('tensorflow'))"

Write-Host ""
Write-Host "Starting Flask server..." -ForegroundColor Green
& $venvPython (Join-Path $root "app.py")

