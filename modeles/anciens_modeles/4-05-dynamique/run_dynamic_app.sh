#!/usr/bin/env bash
set -euo pipefail

cd /home/anatole/jupyter/modeles/anciens_modeles/4-05-dynamique

PORT="${1:-8766}"
PYTHON="${PYTHON:-/home/anatole/jupyter/.venv/bin/python3}"

echo "Dynamic control app: http://127.0.0.1:${PORT}/"
exec "$PYTHON" scripts/dynamic_control_server.py --port "$PORT" --open
