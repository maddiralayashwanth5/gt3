$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "Installing Python dependencies for the target agent..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if (-not (Test-Path ".\config.json")) {
  Copy-Item ".\config.sample.json" ".\config.json"
  Write-Host "Created config.json from config.sample.json"
}

Write-Host ""
Write-Host "Install complete."
Write-Host "Next: run .\list-audio-devices.ps1, edit config.json if needed, then run .\run-agent.ps1"
