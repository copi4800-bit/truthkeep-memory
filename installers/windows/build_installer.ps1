<#
Builds a Windows installer package folder for IT distribution.
This script does not sign anything by itself. Use sign_installer.ps1 after build.
Requires: PowerShell 5+, Python 3.11+, optional Inno Setup if you want EXE output.
#>
$ErrorActionPreference = "Stop"
$Root = Resolve-Path "$PSScriptRoot\..\.."
$Out = Join-Path $Root "dist-enterprise\windows"
New-Item -ItemType Directory -Force -Path $Out | Out-Null

Copy-Item (Join-Path $Root "INSTALL_TRUTHKEEP_WINDOWS.cmd") $Out -Force
Copy-Item (Join-Path $Root "INSTALL_TRUTHKEEP_WINDOWS.ps1") $Out -Force
Copy-Item (Join-Path $Root "README.md") $Out -Force
Copy-Item (Join-Path $Root "START_HERE.md") $Out -Force

$Zip = Join-Path $Root "dist-enterprise\truthkeep-windows-enterprise-payload.zip"
if (Test-Path $Zip) { Remove-Item $Zip -Force }
Compress-Archive -Path (Join-Path $Root "*") -DestinationPath $Zip -Force

python (Join-Path $Root "scripts\make_enterprise_release_manifest.py") --root $Root --out (Join-Path $Root "dist-enterprise\ENTERPRISE_RELEASE_MANIFEST.json")
Write-Host "[OK] Windows enterprise payload built at $Zip"
Write-Host "Next: installers\windows\sign_installer.ps1 -FilePath $Zip -CertPath <pfx>"
