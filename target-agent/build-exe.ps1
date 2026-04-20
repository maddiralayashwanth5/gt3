param(
  [string]$Python = "python",
  [switch]$Clean
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if ($Clean) {
  Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
}

& $Python -m pip install -r requirements.txt
& $Python -m pip install -r requirements-build.txt
& $Python -m PyInstaller --clean agent.spec

Write-Host ""
Write-Host "Built: $root\dist\remote-desktop-agent.exe"
Write-Host "This EXE bundles Python. The target machine does not need Python installed."
Write-Host "Send that single EXE to the target Windows machine."
