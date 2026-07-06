"""Explorateur web des simulations M3 — lecture seule sur experiments/m3/results.

Présente les 120+ runs archivés selon la structure du protocole de recherche
(calibration → baseline → ablations → grille → runs longs). Chaque run expose
des figures MATPLOTLIB au style simulation_lab (mpl_figures.py : vue macro,
histogrammes de densité avec barres de Poisson, rang-taille avec régression,
avalanches causales, structure d'âge), générées à la demande dans
<run>/figures/ et mises en cache, plus les extraits de validation statistique.

Même architecture serveur que simulation_lab (stdlib ThreadingHTTPServer),
strictement en lecture : aucune simulation n'est lancée d'ici.

Usage :
  /home/anatole/jupyter/.venv/bin/python3 webapp/serve.py [--port 8791] [--open-browser]
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from catalog import GROUPS, REPORTS, list_runs, run_paths  # noqa: E402
from mpl_figures import FIGURES, ensure_figures  # noqa: E402

HERE = Path(__file__).resolve().parent

_HEARTBEAT_INTERVAL = 5
_HEARTBEAT_TIMEOUT = 60


# ------------------------------------------------------------------ données

def run_detail(run_id: str) -> dict:
    run_dir = run_paths(run_id)
    out = dict(id=run_id)
    out["config"] = json.loads((run_dir / "config.json").read_text())
    out["summary"] = json.loads((run_dir / "summary.json").read_text())
    # figures matplotlib (style simulation_lab), générées à la demande
    try:
        out["figures"] = ensure_figures(run_dir)
    except Exception as exc:                    # run incomplet : pas bloquant
        out["figures"] = []
        out["figures_error"] = str(exc)
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
            rest = unquote(path[len("/api/run/"):])
            try:
                if "/fig/" in rest:
                    run_id, fig_name = rest.split("/fig/", 1)
                    fig_name = Path(fig_name).name
                    if fig_name not in FIGURES:
                        return self.send_error(HTTPStatus.NOT_FOUND)
                    return self._file(run_paths(run_id) / "figures" / fig_name,
                                      "image/png")
                return self._json(run_detail(rest))
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
