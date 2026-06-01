$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " TruthKeep Enterprise Easy Installer - Windows" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Local-only. No HTTP daemon. No open ports. OpenClaw MCP stdio." -ForegroundColor Gray
Write-Host ""

function Fail($msg) {
  Write-Host "[ERROR] $msg" -ForegroundColor Red
  Write-Host ""
  Write-Host "Try: python -m truthkeep.cli repair" -ForegroundColor Yellow
  exit 1
}

try { $py = Get-Command python -ErrorAction Stop } catch { Fail "Python was not found. Install Python 3.11+ and add it to PATH." }

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if ($LASTEXITCODE -ne 0) { Fail "Python 3.11+ is required." }

python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { Fail "pip upgrade failed." }

python -m pip install -e .
if ($LASTEXITCODE -ne 0) { Fail "TruthKeep package install failed." }

python -m truthkeep.cli easy install
if ($LASTEXITCODE -ne 0) { Fail "TruthKeep Easy Mode setup failed." }

python -m truthkeep.cli openclaw install
if ($LASTEXITCODE -ne 0) { Fail "OpenClaw configuration failed." }

python -m truthkeep.cli openclaw doctor
if ($LASTEXITCODE -ne 0) { Fail "OpenClaw doctor found a problem." }

Write-Host ""
Write-Host "[OK] TruthKeep is installed and OpenClaw Easy Mode is ready." -ForegroundColor Green
Write-Host "Restart OpenClaw, then use the five Easy Mode tools." -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to close"
