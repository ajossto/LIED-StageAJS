#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python introuvable dans ${PYTHON_BIN}" >&2
  echo "Activez ou recréez le virtualenv dans ~/jupyter/.venv." >&2
  exit 1
fi

HOST="${SIMULATION_LAB_HOST:-127.0.0.1}"
PORT="${SIMULATION_LAB_PORT:-8765}"

cd "${ROOT_DIR}"
exec "${PYTHON_BIN}" -m simulation_lab.cli gui --host "${HOST}" --port "${PORT}" --open-browser
