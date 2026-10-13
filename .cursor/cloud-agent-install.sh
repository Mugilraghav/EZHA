#!/usr/bin/env bash
set -euo pipefail

cd /workspace

if ! python3 -m venv /tmp/ezha-venv-probe 2>/dev/null; then
  sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv python3-pip
fi
rm -rf /tmp/ezha-venv-probe

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

.venv/bin/pip install -r requirements.txt
test -f .env || cp .env.example .env
mkdir -p instance/portfolio
