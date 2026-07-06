#!/usr/bin/env bash
# Lance l'explorateur web des simulations M3 (m3_credit_soc/webapp).
# Lecture seule sur experiments/m3/results ; s'arrête tout seul à la
# fermeture du navigateur. Options passées telles quelles à serve.py
# (ex. : ./lancer_explorateur_m3.sh --port 8800 --no-auto-shutdown).
PYTHON=/home/anatole/jupyter/.venv/bin/python3
PORT=8791

OLD_PID=$(lsof -ti tcp:$PORT 2>/dev/null)
if [ -n "$OLD_PID" ]; then
  echo "Instance précédente (PID $OLD_PID) arrêtée."
  kill "$OLD_PID" 2>/dev/null
  sleep 1
fi

cd /home/anatole/jupyter/m3_credit_soc/webapp
exec "$PYTHON" serve.py --port "$PORT" --open-browser "$@"
