#!/usr/bin/env bash
set -euo pipefail

cd /workspace

test -f .env || cp .env.example .env
mkdir -p instance/portfolio

if [[ ! -d .venv ]]; then
  echo "Missing .venv; run install first." >&2
  exit 1
fi

exec .venv/bin/python backend/run.py
