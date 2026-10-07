"""Test §10 — l'IHM « direct » de v2 fonctionne de bout en bout.

Ce test DÉMARRE le serveur `simulation_lab`, crée une session en direct par
HTTP, la fait tourner, lui soumet une intervention, puis relit l'état par la
même route que le navigateur. Il vérifie le CONTRAT DE DONNÉES sur lequel
l'IHM est bâtie : chaque clef que `web/static/live.js` lit doit exister dans
la charge utile, et chaque série qu'il trace doit être présente dans les
lignes envoyées.

Il vérifie aussi que l'aiguillage v2 est ADDITIF : les routes de
`simulation_lab` et celles de M4.3Live v1 répondent toujours 200.

Ce qu'il ne fait PAS, et il faut le dire : il n'ouvre pas de navigateur et ne
regarde pas les pixels. Il contrôle le HTML servi, le JavaScript servi et la
charge utile ; le rendu graphique lui-même n'est pas testé ici.

    /home/anatole/jupyter/.venv/bin/python3 m4_3live_v2_credit_soc/tests/test_web_live.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

PORT = 8899
BASE = f"http://127.0.0.1:{PORT}"
PYTHON = "/home/anatole/jupyter/.venv/bin/python3"


def get(path: str, raw: bool = False):
    with urllib.request.urlopen(BASE + path, timeout=30) as response:
        body = response.read()
        if raw:
            return response.status, body.decode("utf-8", "replace")
        return response.status, json.loads(body)


def post(path: str, payload: dict):
    request = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
        return response.status, (json.loads(body) if body else None)


def status_of(path: str) -> int:
    try:
        with urllib.request.urlopen(BASE + path, timeout=30) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except (urllib.error.URLError, OSError):
        return 0


def wait_until(predicate, timeout: float = 90.0, period: float = 0.5):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(period)
    return last


def main() -> int:
    print("test_web_live.py — IHM en direct de v2, de bout en bout (§10)")
    server = subprocess.Popen(
        [PYTHON, "-m", "simulation_lab.cli", "gui", "--port", str(PORT)],
        cwd="/home/anatole/jupyter",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        ready = wait_until(lambda: status_of("/api/system") == 200, timeout=60)
        assert ready, "le serveur n'a pas démarré"

        # 1. Non-régression : rien n'est débranché par l'aiguillage v2.
        for route in ("/", "/launch", "/results", "/static/app.css", "/api/models",
                      "/api/system", "/api/runs?scope=active", "/api/jobs",
                      "/live", "/api/live/meta"):
            code = status_of(route)
            assert code == 200, (route, code)
        assert status_of("/inexistant") == 404
        print("  routes existantes et routes v1 : toutes 200, /inexistant en 404  OK")

        # 2. Les pages et fichiers statiques de v2.
        code, html = get("/live2", raw=True)
        assert code == 200 and "M4.3Live-v2" in html, html[:200]
        for identifier in ("chart-prod", "chart-kpop", "chart-deaths", "chart-market",
                           "chart-creditors", "intervene-param", "intervene-scope",
                           "session-select"):
            assert f'id="{identifier}"' in html, identifier
        code, script = get("/live2/static/live.js", raw=True)
        assert code == 200 and "loan_direction" in script and "phase_order" in script
        assert status_of("/live2/static/live.css") == 200
        print("  page /live2 : 8 éléments d'IHM présents, live.js et live.css servis  OK")

        # 3. Métadonnées : les paramètres exposés au formulaire.
        code, meta = get("/api/live2/meta")
        assert code == 200
        fields = meta["create_fields"] if "create_fields" in meta else meta.get("fields", [])
        assert "loan_direction" in json.dumps(meta), meta
        assert "transfer_cap" not in json.dumps(meta), "transfer_cap n'aurait pas dû survivre"
        print(f"  /api/live2/meta : {len(json.dumps(meta))} octets, `loan_direction` exposé, "
              "`transfer_cap` absent  OK")

        # 4. Créer une session, la faire tourner.
        code, created = post("/api/live2/sessions", {
            "mode": "fresh",
            "label": "verification v2",
            "parameters": {"seed": 7, "T": 120, "lam": 30.0, "K0": 25.0,
                           "loan_direction": "free"},
        })
        assert code in (200, 201), (code, created)
        session_id = created["session_id"]
        post(f"/api/live2/sessions/{session_id}/play", {})
        state = wait_until(
            lambda: (lambda s: s if s["t"] >= 40 else None)(get(
                f"/api/live2/sessions/{session_id}?since=0")[1]),
            timeout=120,
        )
        assert state and state["t"] >= 40, state
        print(f"  session {session_id[:8]} : {state['t']} pas simulés, "
              f"{state['steps_per_second']:.1f} pas/s  OK")

        # 5. Le contrat de données que le JavaScript consomme.
        for key in ("series", "tech", "cohorts", "journal", "kernel", "parameters",
                    "default_A", "default_gamma", "paused", "running", "status"):
            assert key in state, key
        first = state["series"][0]
        for column in ("t", "pop", "prod_tot", "K_tot", "deaths", "defaults",
                       "loan_volume", "mkt_volume_rev", "mkt_reversed",
                       "K_share_creditors", "corr_marg_net", "mkt_blocked_dir"):
            assert column in first, column
        assert state["parameters"]["loan_direction"] == "free"
        assert "transfer_cap" not in state["parameters"]
        print(f"  charge utile : {len(state['series'])} lignes, 12 colonnes tracées "
              "présentes, `loan_direction` dans les paramètres  OK")

        # 6. Une intervention, soumise comme le ferait le panneau de contrôle.
        code, queued = post(f"/api/live2/sessions/{session_id}/intervene", {
            "param": "A", "value": 1.5, "scope": "all", "note": "verification",
        })
        assert code in (200, 201), (code, queued)
        journal = wait_until(
            lambda: (lambda s: s["journal"] if s["journal"] else None)(get(
                f"/api/live2/sessions/{session_id}?since=0")[1]),
            timeout=90,
        )
        assert journal, "l'intervention n'est jamais apparue au journal"
        entry = journal[-1]
        assert entry["param"] == "A" and entry["value"] == 1.5
        assert "amplitude" in entry, entry
        assert abs(entry["amplitude"]["m_exact"] - 1.5) < 1e-9, entry["amplitude"]
        print(f"  intervention appliquée à t={entry['t']} sur {entry['n_selected']} entités ; "
              f"amplitude exacte enregistrée m = {entry['amplitude']['m_exact']:.12f}  OK")

        # 7. Pause, puis écriture des fichiers de sortie.
        post(f"/api/live2/sessions/{session_id}/pause", {})
        code, written = post(f"/api/live2/sessions/{session_id}/save", {})
        directory = state["directory"]
        for name in ("series.csv", "tension.csv", "tension_agg.csv", "config.json"):
            assert os.path.exists(os.path.join(directory, name)), name
        with open(os.path.join(directory, "tension_agg.csv"), encoding="utf-8") as handle:
            header = handle.readline().strip()
        assert "tension" in header and "basis" not in header, header
        print("  écriture : series.csv, tension.csv, tension_agg.csv, config.json — "
              "et plus de colonne `basis`  OK")

        # 8. La page de v1 est intacte et pointe toujours sur ses propres routes.
        code, html_v1 = get("/live", raw=True)
        assert code == 200 and "/live/static/live.js" in html_v1
        assert "/live2/static" not in html_v1
        print("  l'IHM v1 est intacte et sert toujours ses propres fichiers  OK")
    finally:
        server.terminate()
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server.kill()
    print("test_web_live.py : tout est passé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
