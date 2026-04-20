#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${ROOT_DIR}/dist"
PKG_DIR="${OUT_DIR}/remote-desktop-target-agent"
ZIP_PATH="${OUT_DIR}/remote-desktop-target-agent.zip"

rm -rf "${PKG_DIR}" "${ZIP_PATH}"
mkdir -p "${PKG_DIR}" "${OUT_DIR}"

cp \
  "${ROOT_DIR}/target-agent/agent.py" \
  "${ROOT_DIR}/target-agent/audio_capture.py" \
  "${ROOT_DIR}/target-agent/screen_capture.py" \
  "${ROOT_DIR}/target-agent/input_control.py" \
  "${ROOT_DIR}/target-agent/requirements.txt" \
  "${ROOT_DIR}/target-agent/config.sample.json" \
  "${ROOT_DIR}/target-agent/install-windows.ps1" \
  "${ROOT_DIR}/target-agent/list-audio-devices.ps1" \
  "${ROOT_DIR}/target-agent/run-agent.ps1" \
  "${PKG_DIR}/"

cat > "${PKG_DIR}/README-TARGET.txt" <<'EOF'
Remote Desktop Target Agent

This package runs on the target desktop machine.

Windows quick start:
1. Install Python 3.11+ from https://www.python.org/downloads/windows/
2. Make sure the system-audio capture endpoint is enabled.
3. Open PowerShell in this folder.
4. Run: Set-ExecutionPolicy -Scope Process Bypass
5. Run: .\install-windows.ps1
6. Run: .\list-audio-devices.ps1
7. Edit config.json if needed.
8. Run: .\run-agent.ps1

Default server:
ws://13.205.19.192:8080/ws
EOF

(cd "${OUT_DIR}" && zip -qr "$(basename "${ZIP_PATH}")" "$(basename "${PKG_DIR}")")

echo "Built target package:"
echo "${ZIP_PATH}"
