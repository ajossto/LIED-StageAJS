from __future__ import annotations

import json
import math
import mimetypes
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from simulation_lab import live as live_routes
from simulation_lab import live_v2 as live_v2_routes
from simulation_lab import live_v3 as live_v3_routes
from simulation_lab.jobs import JobManager
from simulation_lab.models.discovery import ModelRegistry
from simulation_lab.runs.storage import RunStorage
from simulation_lab.settings import APP_NAME, DEFAULT_HOST, DEFAULT_PORT, ROOT_DIR, cpu_count, recommended_workers


def _exception_message(exc: BaseException) -> str:
    # ``str(KeyError("x"))`` renvoie « 'x' » avec les guillemets.
    if isinstance(exc, KeyError) and exc.args:
        return str(exc.args[0])
    return str(exc) or exc.__class__.__name__


def _required_int(body: dict, name: str) -> int:
    value = body.get(name)
    if value is None or value == "":
        raise ValueError(f"{name} est requis (entier)")
    return int(value)


def _json_safe(value):
    """Convertit les flottants non finis en ``null`` JSON.

    Les fichiers de résultats scientifiques peuvent contenir des NaN lorsque
    certaines statistiques ne sont pas calculables.  Le module ``json`` de
    Python les émet par défaut sous forme de ``NaN``, alors que les navigateurs
    refusent cette extension non standard dans ``response.json()``.
    """
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


class SimulationLabHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, server_address):
        super().__init__(server_address, SimulationLabHandler)
        self.registry = ModelRegistry()
        self.storage = RunStorage()
        self.jobs = JobManager(self.storage, self.registry)


class SimulationLabHandler(BaseHTTPRequestHandler):
    server: SimulationLabHTTPServer

    # Toute exception qui s'échappe d'un handler fait fermer la connexion par
    # ``socketserver`` sans aucune réponse : le navigateur ne voit qu'une
    # erreur réseau. Les trois méthodes HTTP passent donc par ``_guarded``.
    def do_GET(self) -> None:
        self._guarded(self._handle_get)

    def do_POST(self) -> None:
        self._guarded(self._handle_post)

    def do_DELETE(self) -> None:
        self._guarded(self._handle_delete)

    def _guarded(self, handler) -> None:
        try:
            handler()
        except (BrokenPipeError, ConnectionResetError):
            return
        except (KeyError, FileNotFoundError) as exc:
            self._send_error_json(HTTPStatus.NOT_FOUND, _exception_message(exc))
        except (ValueError, TypeError) as exc:
            self._send_error_json(HTTPStatus.BAD_REQUEST, _exception_message(exc))
        except Exception as exc:  # noqa: BLE001 - le serveur doit toujours répondre
            self._send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, _exception_message(exc))

    def send_error(self, code, message=None, explain=None) -> None:
        # ``BaseHTTPRequestHandler.send_error`` écrit ``message`` dans la ligne
        # de statut encodée en latin-1 strict : un « — » ou un « ’ » y lève
        # UnicodeEncodeError. On répond en JSON, statut sans texte libre.
        self._send_error_json(HTTPStatus(code), message or HTTPStatus(code).phrase)

    def _send_error_json(self, status: HTTPStatus, message: str) -> None:
        self._json_response({"error": message}, status=status)

    def _handle_get(self) -> None:
        parsed = urlparse(self.path)
        # M4.3Live : aiguillage additif, isolé, avant toute branche existante.
        if live_routes.owns(parsed.path):
            return live_routes.dispatch(self, parsed, "GET")
        # M4.3Live-v2 : second aiguillage, routes /live2 — les deux lignées
        # coexistent, aucune n'est débranchée.
        if live_v2_routes.owns(parsed.path):
            return live_v2_routes.dispatch(self, parsed, "GET")
        # M4.4Rebond : troisième aiguillage, routes /live3. Le plan M4.4 §0
        # parle de « renommer » live_v2 en live_v3 ; ce serait débrancher
        # l'IHM de v2, dont 153 runs et deux rapports publiés dépendent.
        # C'est donc une ADDITION, comme les deux précédentes.
        if live_v3_routes.owns(parsed.path):
            return live_v3_routes.dispatch(self, parsed, "GET")
        if parsed.path in {"/", "/launch"}:
            return self._serve_file(ROOT_DIR / "simulation_lab" / "web" / "templates" / "launch.html", "text/html; charset=utf-8")
        if parsed.path == "/results":
            return self._serve_file(ROOT_DIR / "simulation_lab" / "web" / "templates" / "results.html", "text/html; charset=utf-8")
        if parsed.path.startswith("/static/"):
            static_root = (ROOT_DIR / "simulation_lab" / "web" / "static").resolve()
            candidate = (static_root / unquote(parsed.path[len("/static/"):])).resolve()
            if not candidate.is_relative_to(static_root):
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            return self._serve_file(candidate)
        if parsed.path == "/api/models":
            scope = parse_qs(parsed.query).get("scope", ["all"])[0]
            try:
                models = self.server.registry.list_models(scope=scope)
            except ValueError as exc:
                self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            return self._json_response([model.describe() for model in models])
        if parsed.path == "/api/system":
            return self._json_response({
                "cpu_count": cpu_count(),
                "recommended_workers": recommended_workers(),
                "reserved_cores": max(0, cpu_count() - recommended_workers()),
                "model_load_errors": self.server.registry.load_errors,
            })
        if parsed.path == "/api/runs":
            scope = parse_qs(parsed.query).get("scope", ["active"])[0]
            if scope == "trash":
                return self._json_response(self.server.storage.list_trash())
            if scope in {"archive", "archived"}:
                return self._json_response(self.server.storage.list_runs(archived=True))
            if scope == "all":
                return self._json_response(self.server.storage.list_runs() + self.server.storage.list_trash())
            if scope == "active":
                return self._json_response(self.server.storage.list_runs(archived=False))
            self.send_error(HTTPStatus.BAD_REQUEST, f"Périmètre de runs inconnu: {scope}")
            return
        if parsed.path == "/api/thumbnails":
            return self._json_response(self.server.storage.class_thumbnails())
        if parsed.path == "/api/jobs":
            return self._json_response(self.server.jobs.list_jobs())
        if parsed.path.startswith("/api/jobs/"):
            job_id = unquote(parsed.path.rsplit("/", 1)[-1])
            return self._json_response(self.server.jobs.get_job(job_id))
        if parsed.path.startswith("/api/runs/") and parsed.path.endswith("/artifact"):
            return self._serve_artifact(self.path)
        if parsed.path.startswith("/api/runs/"):
            run_id = unquote(parsed.path.rsplit("/", 1)[-1])
            return self._json_response(self.server.storage.read_metadata(run_id))
        self.send_error(HTTPStatus.NOT_FOUND)

    def _handle_post(self) -> None:
        parsed = urlparse(self.path)
        # M4.3Live : aiguillage AVANT la lecture du corps, que le routeur
        # lit lui-même (aucune branche existante n'est modifiée).
        if live_routes.owns(parsed.path):
            return live_routes.dispatch(self, parsed, "POST")
        if live_v2_routes.owns(parsed.path):
            return live_v2_routes.dispatch(self, parsed, "POST")
        if live_v3_routes.owns(parsed.path):
            return live_v3_routes.dispatch(self, parsed, "POST")
        try:
            body = self._read_json_body()
        except ValueError as exc:
            self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        if parsed.path == "/api/thumbnails":
            payload = self.server.storage.set_class_thumbnail(body.get("model_id"), body.get("label"))
            return self._json_response(payload)
        if parsed.path == "/api/jobs/run":
            try:
                payload = self.server.jobs.submit_single(
                    model_id=body["model_id"],
                    parameters=body.get("parameters", {}),
                    seed=_required_int(body, "seed"),
                    label=body.get("label", ""),
                )
            except (KeyError, ValueError, TypeError) as exc:
                self.send_error(HTTPStatus.BAD_REQUEST, _exception_message(exc))
                return
            return self._json_response(payload, status=HTTPStatus.CREATED)
        if parsed.path == "/api/jobs/batch":
            try:
                payload = self.server.jobs.submit_batch(
                    model_id=body["model_id"],
                    parameters=body.get("parameters", {}),
                    run_count=_required_int(body, "run_count"),
                    max_workers=_required_int(body, "max_workers"),
                    base_seed=None if body.get("base_seed") is None else int(body["base_seed"]),
                    label=body.get("label", ""),
                )
            except (KeyError, ValueError, TypeError) as exc:
                self.send_error(HTTPStatus.BAD_REQUEST, _exception_message(exc))
                return
            return self._json_response(payload, status=HTTPStatus.CREATED)
        if parsed.path.startswith("/api/jobs/") and parsed.path.endswith("/cancel"):
            job_id = unquote(parsed.path.split("/")[3])
            payload = self.server.jobs.cancel_job(job_id)
            return self._json_response(payload)
        if parsed.path.startswith("/api/runs/") and parsed.path.endswith("/keep"):
            run_id = unquote(parsed.path.split("/")[3])
            payload = self.server.storage.set_keep(run_id, bool(body.get("keep", True)))
            return self._json_response(payload)
        if parsed.path.startswith("/api/runs/") and parsed.path.endswith("/important"):
            run_id = unquote(parsed.path.split("/")[3])
            payload = self.server.storage.set_important(run_id, bool(body.get("important", True)))
            return self._json_response(payload)
        if parsed.path.startswith("/api/runs/") and parsed.path.endswith("/annotations"):
            run_id = unquote(parsed.path.split("/")[3])
            payload = self.server.storage.update_annotations(
                run_id,
                label=body.get("label"),
                comment=body.get("comment"),
            )
            return self._json_response(payload)
        if parsed.path.startswith("/api/runs/") and parsed.path.endswith("/refresh-artifacts"):
            run_id = unquote(parsed.path.split("/")[3])
            payload = self.server.storage.refresh_artifacts(run_id)
            return self._json_response(payload)
        if parsed.path.startswith("/api/runs/") and parsed.path.endswith("/clean-csv"):
            run_id = unquote(parsed.path.split("/")[3])
            try:
                payload = self.server.storage.clean_csv(run_id)
                return self._json_response(payload)
            except ValueError as exc:
                self.send_error(HTTPStatus.CONFLICT, str(exc))
                return
        if parsed.path.startswith("/api/runs/") and parsed.path.endswith("/regen-graphs"):
            run_id = unquote(parsed.path.split("/")[3])
            try:
                payload = self.server.storage.regen_graphs(run_id)
                return self._json_response(payload, status=HTTPStatus.ACCEPTED)
            except (ValueError, FileNotFoundError) as exc:
                self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
                return
        if parsed.path.startswith("/api/runs/") and parsed.path.endswith("/locate"):
            run_id = unquote(parsed.path.split("/")[3])
            payload = self.server.storage.locate_run(run_id)
            return self._json_response(payload)
        if parsed.path.startswith("/api/runs/") and parsed.path.endswith("/trash"):
            run_id = unquote(parsed.path.split("/")[3])
            try:
                self.server.storage.delete_run(run_id)
            except ValueError as exc:
                self.send_error(HTTPStatus.CONFLICT, str(exc))
                return
            return self._json_response({"trashed": run_id})
        if parsed.path.startswith("/api/trash/") and parsed.path.endswith("/restore"):
            run_id = unquote(parsed.path.split("/")[3])
            payload = self.server.storage.restore_run(run_id)
            return self._json_response(payload)
        self.send_error(HTTPStatus.NOT_FOUND)

    def _handle_delete(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/trash":
            return self._json_response(self.server.storage.empty_trash())
        if parsed.path.startswith("/api/trash/"):
            run_id = unquote(parsed.path.rsplit("/", 1)[-1])
            self.server.storage.permanently_delete_from_trash(run_id)
            return self._json_response({"deleted": run_id})
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, fmt: str, *args) -> None:
        return

    def _read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length) if content_length else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON invalide: {exc.msg}") from exc

    def _json_response(self, payload, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(
            _json_safe(payload),
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_file(self, path: Path, content_type: str | None = None) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = path.read_bytes()
        guessed = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", guessed)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_artifact(self, path: str) -> None:
        parsed = urlparse(path)
        run_id = unquote(parsed.path.split("/")[3])
        query = parse_qs(parsed.query)
        if "path" not in query or not query["path"]:
            self.send_error(HTTPStatus.BAD_REQUEST, "Paramètre path manquant")
            return
        relative_path = unquote(query["path"][0])
        try:
            artifact_path = self.server.storage.artifact_path(run_id, relative_path)
        except ValueError as exc:
            self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        self._serve_file(artifact_path)


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, open_browser: bool = False) -> None:
    httpd = SimulationLabHTTPServer((host, port))
    url = f"http://{host}:{port}"
    print(f"{APP_NAME} disponible sur {url}")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
    finally:
        httpd.server_close()
