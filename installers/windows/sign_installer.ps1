param(
  [Parameter(Mandatory=$true)][string]$FilePath,
  [string]$CertPath = $env:TRUTHKEEP_SIGNING_CERT_PFX,
  [string]$CertPassword = $env:TRUTHKEEP_SIGNING_CERT_PASSWORD,
  [string]$TimestampUrl = "http://timestamp.digicert.com"
)
$ErrorActionPreference = "Stop"
if (!(Test-Path $FilePath)) { throw "File not found: $FilePath" }
if (!$CertPath) { throw "No certificate provided. Set TRUTHKEEP_SIGNING_CERT_PFX or pass -CertPath." }
if (!(Test-Path $CertPath)) { throw "Certificate not found: $CertPath" }
$signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue
if (!$signtool) { throw "signtool.exe not found. Install Windows SDK." }

$args = @("sign", "/fd", "SHA256", "/tr", $TimestampUrl, "/td", "SHA256", "/f", $CertPath)
if ($CertPassword) { $args += @("/p", $CertPassword) }
$args += $FilePath
& $signtool.Source @args
if ($LASTEXITCODE -ne 0) { throw "Signing failed." }
& $signtool.Source verify /pa /v $FilePath
Write-Host "[OK] Signed and verified: $FilePath" -ForegroundColor Green
