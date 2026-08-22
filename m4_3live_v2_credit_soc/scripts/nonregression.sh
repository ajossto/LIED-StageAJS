#!/bin/bash
# Non-régression de simulation_lab après l'ajout de l'aiguillage /live2.
# Les deux lignées coexistent : /live (v1) et /live2 (v2) doivent répondre.
# On EXÉCUTE réellement les commandes et les routes, on ne relit pas le code.
# Sortie : results/analysis/nonregression.txt
set -u
PY=/home/anatole/jupyter/.venv/bin/python3
PORT=8898
OUT=/home/anatole/jupyter/m4_3live_v2_credit_soc/results/analysis
mkdir -p "$OUT"
cd /home/anatole/jupyter
REPORT="$OUT/nonregression.txt"
: > "$REPORT"

say() { echo "$@" | tee -a "$REPORT"; }

say "Non-régression simulation_lab — $(date -Iseconds)"
say ""

say "## CLI"
n=$($PY -m simulation_lab.cli list-models --scope all 2>&1 | $PY -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null)
say "list-models        : $n modèles"
n=$($PY -m simulation_lab.cli list-runs --scope active 2>&1 | $PY -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null)
say "list-runs (active) : $n runs"

say "run  (m4b_credit_soc_mini, T=60, seed 424242)"
RUN=$($PY -m simulation_lab.cli run --model m4b_credit_soc_mini \
      --params '{"T":60,"lam":5,"pop_max":2000}' --seed 424242 --label nonregression_live 2>&1)
echo "$RUN" | $PY -c "
import json,sys
d=json.load(sys.stdin)
print('  statut       :', d.get('status'))
print('  run_id       :', d.get('run_id'))
print('  artefacts    :', len(d.get('summary',{}).get('artifacts',[]) or d.get('artifacts',[]) or []))
" 2>&1 | tee -a "$REPORT" || echo "$RUN" | head -5 | tee -a "$REPORT"

say "batch (2 runs, 2 workers)"
BATCH=$($PY -m simulation_lab.cli batch --model m4b_credit_soc_mini \
        --params '{"T":40,"lam":5,"pop_max":2000}' --runs 2 --workers 2 \
        --base-seed 424243 --label nonregression_live_batch 2>&1)
echo "$BATCH" | $PY -c "
import json,sys
d=json.load(sys.stdin)
print('  batch_id     :', d.get('batch_id'))
print('  run_ids      :', len(d.get('run_ids',[])))
print('  postprocess  :', d.get('postprocess',{}).get('status'), d.get('postprocess',{}).get('errors'))
" 2>&1 | tee -a "$REPORT" || echo "$BATCH" | head -5 | tee -a "$REPORT"

say ""
say "## Serveur (routes existantes ET /live)"
$PY -m simulation_lab.cli gui --port $PORT >/dev/null 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
sleep 4
for u in / /launch /results /static/app.css /static/app.js /api/models /api/system \
         "/api/runs?scope=active" /api/jobs \
         /live /live/static/live.js /live/static/live.css /api/live/meta /api/live/sessions \
         /live2 /live2/static/live.js /live2/static/live.css /api/live2/meta /api/live2/sessions \
         /inexistant; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT$u")
  printf "%-28s %s\n" "$u" "$code" | tee -a "$REPORT"
done
say ""
say "(404 attendu sur /inexistant ; tout le reste doit être 200.)"
kill $SERVER 2>/dev/null
wait $SERVER 2>/dev/null
say ""
say "Terminé."
