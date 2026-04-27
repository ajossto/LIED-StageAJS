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
URL="http://${HOST}:${PORT}"
REQUIRED_MODEL_IDS="modele_27_04_wip,modele_27_04_minimal_candidate"

cd "${ROOT_DIR}"

SERVER_STATUS="$("${PYTHON_BIN}" - <<PY
import json
from urllib.request import urlopen

required = set("${REQUIRED_MODEL_IDS}".split(","))
url = "${URL}/api/models"
try:
    with urlopen(url, timeout=1.0) as response:
        if response.status != 200:
            print("down")
            raise SystemExit
        models = json.load(response)
except Exception:
    print("down")
else:
    model_ids = {model.get("model_id") for model in models}
    print("current" if required <= model_ids else "stale")
PY
)"

if [[ "${SERVER_STATUS}" == "current" ]]; then
  echo "Simulation Lab est déjà disponible sur ${URL}"
  "${PYTHON_BIN}" - <<PY
import webbrowser
webbrowser.open("${URL}")
PY
  exit 0
fi

if [[ "${SERVER_STATUS}" == "stale" ]]; then
  echo "Simulation Lab tourne déjà sur ${URL}, mais son registre est ancien."
  echo "Redémarrage de l'instance locale pour charger les nouveaux modèles..."
  pkill -f "${PYTHON_BIN} -m simulation_lab.cli gui --host ${HOST} --port ${PORT}" 2>/dev/null || true
  sleep 1
fi

if "${PYTHON_BIN}" - <<PY
from urllib.request import urlopen

url = "${URL}/api/models"
try:
    with urlopen(url, timeout=1.0) as response:
        raise SystemExit(0 if response.status == 200 else 1)
except Exception:
    raise SystemExit(1)
PY
then
  echo "Le port ${PORT} répond encore mais n'a pas pu être redémarré automatiquement." >&2
  echo "Fermez l'ancien Simulation Lab puis relancez ce script." >&2
  exit 1
fi

echo "Démarrage de Simulation Lab sur ${URL}"
exec "${PYTHON_BIN}" -m simulation_lab.cli gui --host "${HOST}" --port "${PORT}" --open-browser
