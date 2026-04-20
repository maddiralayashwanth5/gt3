$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path ".\config.json")) {
  Copy-Item ".\config.sample.json" ".\config.json"
}

python .\agent.py --config .\config.json
