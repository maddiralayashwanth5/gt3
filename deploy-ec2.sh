#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EC2_HOST="${1:-}"
EC2_USER="${EC2_USER:-ubuntu}"
EC2_KEY="${EC2_KEY:-}"
REMOTE_DIR="${REMOTE_DIR:-/home/${EC2_USER}/remote-desktop-webrtc}"

if [[ -z "${EC2_HOST}" ]]; then
  echo "Usage: ./deploy-ec2.sh <elastic-ip-or-hostname>"
  echo "Optional env: EC2_USER=ubuntu EC2_KEY=~/.ssh/key.pem REMOTE_DIR=/home/ubuntu/remote-desktop-webrtc"
  exit 1
fi

SSH_OPTS=(
  -o StrictHostKeyChecking=accept-new
  -o ServerAliveInterval=30
  -o ServerAliveCountMax=120
)

if [[ -n "${EC2_KEY}" ]]; then
  SSH_OPTS+=(-i "${EC2_KEY}")
fi

REMOTE="${EC2_USER}@${EC2_HOST}"

echo "==> Checking SSH connectivity to ${REMOTE}"
ssh "${SSH_OPTS[@]}" "${REMOTE}" "echo connected"

echo "==> Installing Docker and Docker Compose plugin on EC2"
ssh "${SSH_OPTS[@]}" "${REMOTE}" '
  set -euo pipefail
  export DEBIAN_FRONTEND=noninteractive
  if ! command -v docker >/dev/null 2>&1; then
    sudo apt-get update
    if apt-cache show docker-compose-plugin >/dev/null 2>&1; then
      sudo apt-get install -y docker.io docker-compose-plugin
    else
      sudo apt-get install -y docker.io docker-compose-v2
    fi
    sudo systemctl enable --now docker
  fi
  sudo mkdir -p "'"${REMOTE_DIR}"'"
  sudo chown -R "$USER":"$USER" "'"${REMOTE_DIR}"'"
'

echo "==> Uploading server-side files"
tar -C "${ROOT_DIR}" -czf - \
  docker-compose.yml \
  README.md \
  server \
  viewer \
  shared \
| ssh "${SSH_OPTS[@]}" "${REMOTE}" "mkdir -p '${REMOTE_DIR}' && tar -xzf - -C '${REMOTE_DIR}'"

echo "==> Starting containers"
ssh "${SSH_OPTS[@]}" "${REMOTE}" "
  set -euo pipefail
  cd '${REMOTE_DIR}'
  sudo docker compose up -d
  sudo docker compose ps
"

echo
echo "Deployment complete."
echo "Viewer URL: http://${EC2_HOST}:8080/?room=demo"
echo "Health check: http://${EC2_HOST}:8080/healthz"
echo
echo "Run the target agent on the machine you want to control:"
echo "  python3 agent.py --room demo --signaling-url ws://${EC2_HOST}:8080/ws --system-audio-device 3 --mic-output-device 5"
