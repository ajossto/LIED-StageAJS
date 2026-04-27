from __future__ import annotations

import json
import mimetypes
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from simulation_lab.jobs import JobManager
from simulation_lab.models.discovery import ModelRegistry
from simulation_lab.runs.storage import RunStorage
from simulation_lab.settings import APP_NAME, DEFAULT_HOST, DEFAULT_PORT, ROOT_DIR, cpu_count, recommended_workers


class SimulationLabHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address):
        super().__init__(server_address, SimulationLabHandler)
        self.registry = ModelRegistry()
        self.storage = RunStorage()
        self.jobs = JobManager(self.storage, self.registry)


class SimulationLabHandler(BaseHTTPRequestHandler):
    server: SimulationLabHTTPServer

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/launch"}:
            return self._serve_file(ROOT_DIR / "simulation_lab" / "web" / "templates" / "launch.html", "text/html; charset=utf-8")
        if parsed.path == "/results":
            return self._serve_file(ROOT_DIR / "simulation_lab" / "web" / "templates" / "results.html", "text/html; charset=utf-8")
        if parsed.path.startswith("/static/"):
            return self._serve_file(ROOT_DIR / "simulation_lab" / "web" / parsed.path.lstrip("/"))
        if parsed.path == "/api/models":
            return self._json_response([model.describe() for model in self.server.registry.list_models()])
        if parsed.path == "/api/system":
            return self._json_response({
                "cpu_count": cpu_count(),
                "recommended_workers": recommended_workers(),
                "reserved_cores": max(0, cpu_count() - recommended_workers()),
            })
        if parsed.path == "/api/runs":
            scope = parse_qs(parsed.query).get("scope", ["active"])[0]
            if scope == "trash":
                return self._json_response(self.server.storage.list_trash())
            if scope == "all":
                return self._json_response(self.server.storage.list_runs() + self.server.storage.list_trash())
            return self._json_response(self.server.storage.list_runs())
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

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            body = self._read_json_body()
        except ValueError as exc:
            self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        if parsed.path == "/api/jobs/run":
            payload = self.server.jobs.submit_single(
                model_id=body["model_id"],
                parameters=body.get("parameters", {}),
                seed=int(body["seed"]),
                label=body.get("label", ""),
            )
            return self._json_response(payload, status=HTTPStatus.CREATED)
        if parsed.path == "/api/jobs/batch":
            payload = self.server.jobs.submit_batch(
                model_id=body["model_id"],
                parameters=body.get("parameters", {}),
                run_count=int(body["run_count"]),
                max_workers=int(body["max_workers"]),
                base_seed=body.get("base_seed"),
                label=body.get("label", ""),
            )
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
        if parsed.path.startswith("/api/runs/") and parsed.path.endswith("/locate"):
            run_id = unquote(parsed.path.split("/")[3])
            payload = self.server.storage.locate_run(run_id)
            return self._json_response(payload)
        if parsed.path.startswith("/api/runs/") and parsed.path.endswith("/trash"):
            run_id = unquote(parsed.path.split("/")[3])
            self.server.storage.delete_run(run_id)
            return self._json_response({"trashed": run_id})
        if parsed.path.startswith("/api/trash/") and parsed.path.endswith("/restore"):
            run_id = unquote(parsed.path.split("/")[3])
            payload = self.server.storage.restore_run(run_id)
            return self._json_response(payload)
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_DELETE(self) -> None:
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
        data = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
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
