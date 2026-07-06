"""Explorateur web des simulations M3 — lecture seule sur experiments/m3/results.

Présente les 120+ runs archivés selon la structure du protocole de recherche
(calibration → baseline → ablations → grille → runs longs), avec pour chaque
run : séries temporelles (population, stocks, crédit, défauts, avalanches),
distributions au dernier instantané (CCDF log-log de NW, L, K, revenu),
distribution des tailles d'avalanches causales et extraits de validation.

Même architecture que simulation_lab (stdlib ThreadingHTTPServer + Plotly CDN),
mais strictement en lecture : aucune simulation n'est lancée d'ici.

Usage :
  /home/anatole/jupyter/.venv/bin/python3 webapp/serve.py [--port 8791] [--open-browser]
"""
from __future__ import annotations

import argparse
import csv
import json
import mimetypes
import os
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import numpy as np

from catalog import GROUPS, REPORTS, list_runs, run_paths  # noqa: E402

HERE = Path(__file__).resolve().parent

_HEARTBEAT_INTERVAL = 5
_HEARTBEAT_TIMEOUT = 60


# ------------------------------------------------------------------ données

def _read_series(run_dir: Path) -> dict:
    rows = []
    with open(run_dir / "series.csv") as fh:
        for row in csv.DictReader(fh):
            rows.append({k: (int(v) if "." not in v and "e" not in v.lower()
                             else float(v)) for k, v in row.items()})
    if not rows:
        return {}
    cols = list(rows[0].keys())
    return dict(columns=cols, data={k: [r[k] for r in rows] for k in cols})


def _ccdf(values: np.ndarray, max_points: int = 1200) -> dict:
    """CCDF des valeurs > 0, sous-échantillonnée (queue conservée exacte)."""
    v = np.sort(values[values > 0])
    n = len(v)
    if n < 5:
        return dict(x=[], y=[])
    ccdf = 1.0 - np.arange(1, n + 1) / (n + 1.0)
    if n > max_points:
        keep_tail = min(300, n // 4)
        body_idx = np.unique(np.linspace(0, n - keep_tail - 1,
                                         max_points - keep_tail).astype(int))
        idx = np.concatenate([body_idx, np.arange(n - keep_tail, n)])
    else:
        idx = np.arange(n)
    return dict(x=v[idx].tolist(), y=ccdf[idx].tolist(), n=int(n))


def _last_snapshot(run_dir: Path) -> tuple[int, dict] | None:
    snaps = sorted(run_dir.glob("snap_t*.npz"))
    if not snaps:
        return None
    p = snaps[-1]
    t = int(p.stem.split("t")[-1])
    with np.load(p) as z:
        return t, {k: z[k].copy() for k in z.files}


def _avalanche_histogram(run_dir: Path, t_min: int = 500) -> dict:
    path = run_dir / "avalanches.csv"
    if not path.exists():
        return {}
    sizes = []
    with open(path) as fh:
        for row in csv.DictReader(fh):
            if int(row["t"]) >= t_min:
                sizes.append(int(row["size"]))
    if not sizes:
        return {}
    arr = np.asarray(sizes)
    vals, counts = np.unique(arr, return_counts=True)
    return dict(sizes=vals.tolist(), counts=counts.tolist(), n=len(sizes),
                mean=float(arr.mean()), max=int(arr.max()),
                var_over_mean=float(arr.var() / arr.mean()),
                frac_multi=float((arr > 1).mean()), t_min=t_min)


def run_detail(run_id: str) -> dict:
    run_dir = run_paths(run_id)
    out = dict(id=run_id)
    out["config"] = json.loads((run_dir / "config.json").read_text())
    out["summary"] = json.loads((run_dir / "summary.json").read_text())
    out["series"] = _read_series(run_dir)
    snap = _last_snapshot(run_dir)
    if snap:
        t, data = snap
        out["distributions"] = dict(
            t=t, n_alive=int(len(data["id"])),
            ccdf={var: _ccdf(data[var]) for var in ("nw", "L", "K", "income")
                  if var in data},
        )
    out["avalanches"] = _avalanche_histogram(run_dir)
    vpath = run_dir / "validation.json"
    if vpath.exists():
        out["validation"] = json.loads(vpath.read_text())
    return out


# ------------------------------------------------------------------ serveur

class ExplorerServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, addr, auto_shutdown: bool):
        super().__init__(addr, ExplorerHandler)
        self._last_heartbeat: float | None = None
        if auto_shutdown:
            threading.Thread(target=self._watchdog, daemon=True).start()

    def _watchdog(self):
        while True:
            time.sleep(_HEARTBEAT_INTERVAL)
            if (self._last_heartbeat is not None
                    and time.time() - self._last_heartbeat > _HEARTBEAT_TIMEOUT):
                print("\nAucun navigateur connecté — arrêt automatique.")
                os._exit(0)


class ExplorerHandler(BaseHTTPRequestHandler):
    server: ExplorerServer

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            return self._file(HERE / "templates" / "index.html",
                              "text/html; charset=utf-8")
        if path == "/run":
            return self._file(HERE / "templates" / "run.html",
                              "text/html; charset=utf-8")
        if path.startswith("/static/"):
            name = Path(unquote(path[len("/static/"):])).name  # pas de traversée
            return self._file(HERE / "static" / name)
        if path == "/api/index":
            return self._json(list_runs())
        if path.startswith("/api/run/"):
            run_id = unquote(path[len("/api/run/"):])
            try:
                return self._json(run_detail(run_id))
            except (FileNotFoundError, ValueError) as exc:
                return self.send_error(HTTPStatus.NOT_FOUND, str(exc))
        if path.startswith("/reports/"):
            name = Path(unquote(path[len("/reports/"):])).name
            matches = sorted(REPORTS.glob(f"{name}*/main.pdf"))
            if matches:
                return self._file(matches[0], "application/pdf")
            return self.send_error(HTTPStatus.NOT_FOUND)
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        if urlparse(self.path).path == "/api/heartbeat":
            self.server._last_heartbeat = time.time()
            return self._json({"ok": True})
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, fmt, *args):
        return

    def _json(self, payload, status=HTTPStatus.OK):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _file(self, path: Path, content_type: str | None = None):
        if not path.is_file():
            return self.send_error(HTTPStatus.NOT_FOUND)
        data = path.read_bytes()
        ct = content_type or mimetypes.guess_type(path.name)[0] \
            or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8791)
    ap.add_argument("--open-browser", action="store_true")
    ap.add_argument("--no-auto-shutdown", action="store_true")
    args = ap.parse_args()
    httpd = ExplorerServer((args.host, args.port),
                           auto_shutdown=not args.no_auto_shutdown)
    url = f"http://{args.host}:{args.port}"
    print(f"Explorateur M3 disponible sur {url}")
    print(f"Groupes du protocole : {len(GROUPS)} ; résultats lus en lecture seule.")
    if args.open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
