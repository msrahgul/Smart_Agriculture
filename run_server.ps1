$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
  Write-Host "ERROR: Virtual environment not found at .venv" -ForegroundColor Red
  Write-Host "Create it first:" -ForegroundColor Yellow
  Write-Host "  python -m venv .venv"
  Write-Host "  .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
  exit 1
}

Write-Host "Using: $venvPython"
& $venvPython -c "import sys; print('python:', sys.executable); print('version:', sys.version.split(' ',1)[0])"
& $venvPython -c "import google.protobuf as pb; print('protobuf:', getattr(pb,'__version__',None))"
& $venvPython -c "import tensorflow as tf; print('tensorflow:', getattr(tf,'__version__',None))"

Write-Host ""
Write-Host "Starting Flask server..." -ForegroundColor Green
& $venvPython (Join-Path $root "app.py")

