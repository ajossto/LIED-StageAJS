#!/usr/bin/env bash
PYTHON=/home/anatole/jupyter/.venv/bin/python3
PORT=8777

OLD_PID=$(lsof -ti tcp:$PORT 2>/dev/null)
if [ -n "$OLD_PID" ]; then
  echo "Instance précédente (PID $OLD_PID) arrêtée."
  kill "$OLD_PID" 2>/dev/null
  sleep 1
fi

cd /home/anatole/jupyter
exec "$PYTHON" -m simulation_lab.cli gui --open-browser
