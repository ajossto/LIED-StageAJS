"""Routeur HTTP de l'IHM « direct » de M4.3Live (prompt §5, §6).

Isolation : tout le code de M4.3Live vit dans `m4_3live_v2_credit_soc/`. Le
serveur de `simulation_lab` ne gagne qu'un aiguillage additif de quelques
lignes en tête de `do_GET`/`do_POST` (`simulation_lab/live/__init__.py`,
branché dans `simulation_lab/web/app.py:48,94`), qui ne touche AUCUNE
branche existante. Un seul serveur, donc une seule adresse pour
l'utilisateur, et la reprise (§4) lit `RunStorage` en lecture seule.

Ce module est chargé par chemin de fichier (`importlib`), pas comme paquet
de premier niveau nommé `web` : il n'ajoute aucun nom générique à
`sys.modules`. Il insère en revanche `m4_3live_v2_credit_soc/` dans `sys.path`
pour que le moteur soit importé sous l'unique nom `m4_3live_v2`, le même que
celui qu'utilisent les tests et le pilote sans tête.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import uuid
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs, unquote

_PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PACKAGE_ROOT not in sys.path:
    sys.path.insert(0, _PACKAGE_ROOT)

from m4_3live_v2.live import LiveSession  # noqa: E402
from m4_3live_v2.model import PARAM_SEMANTICS, SCOPES, Config, Simulation  # noqa: E402

WEB_DIR = Path(__file__).resolve().parent
TEMPLATES = WEB_DIR / "templates"
STATIC = WEB_DIR / "static"
SESSIONS_DIR = Path(_PACKAGE_ROOT) / "results" / "live"

# Paramètres exposés au formulaire de création (sous-ensemble utile de Config).
CREATE_FIELDS = (
    "gamma",
    "A",
    "lam",
    "delta",
    "sigma",
    "K0",
    "seed",
    "T",
    "pop_max",
    "rho",
    "eta_beta",
    "eta_n_ref",
    "transfer_cap",
    "rate_rule",
    "surplus_share_p",
    "kernel_policy",
    "lut_threshold",
)


class LiveRouter:
    """Gère les sessions en direct et sert les routes `/live2` et `/api/live2/*`."""

    def __init__(self, storage=None) -> None:
        self.sessions: dict[str, LiveSession] = {}
        self.order: list[str] = []
        self.lock = threading.Lock()
        self.storage = storage
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    # -- utilitaires -------------------------------------------------------
    def _session(self, session_id: str) -> LiveSession:
        with self.lock:
            session = self.sessions.get(session_id)
        if session is None:
            raise KeyError(session_id)
        return session

    def _stored_runs(self) -> list[dict]:
        """Runs M4.3 déjà stockés, éligibles à une reprise (lecture seule)."""
        if self.storage is None:
            return []
        runs = []
        for metadata in self.storage.list_runs(archived=False):
            if metadata.get("model_id") != "m4_3_credit_soc":
                continue
            series = Path(self.storage.run_dir(metadata["run_id"])) / "series.csv"
            if not series.exists():
                continue
            runs.append(
                {
                    "run_id": metadata["run_id"],
                    "label": metadata.get("label", ""),
                    "seed": metadata.get("seed"),
                    "T": metadata.get("parameters", {}).get("T"),
                    "parameters": metadata.get("parameters", {}),
                }
            )
        runs.sort(key=lambda item: item["run_id"])
        return runs

    # -- création ----------------------------------------------------------
    def create(self, body: dict) -> dict:
        mode = body.get("mode", "fresh")
        label = str(body.get("label", ""))
        raw = dict(body.get("parameters") or {})
        origin: dict = {"mode": mode}
        reference_path = None
        reference_upto = 0

        if mode == "resume":
            if self.storage is None:
                raise ValueError("stockage des runs indisponible")
            run_id = str(body["run_id"])
            t0 = int(body["t0"])
            metadata = self.storage.read_metadata(run_id)
            reference_path = Path(self.storage.run_dir(run_id)) / "series.csv"
            if not reference_path.exists():
                raise ValueError(f"le run {run_id} n'a pas de series.csv")
            known = set(Config.__dataclass_fields__)
            raw = {
                key: value for key, value in metadata.get("parameters", {}).items() if key in known
            }
            raw["T"] = t0
            reference_upto = t0
            origin = {
                "mode": "resume",
                "run_id": run_id,
                "t0": t0,
                "reference": str(reference_path),
                "warning": (
                    "M4.3Live est un fork d'institution différente : la reprise n'est "
                    "identique au run d'origine que dans le régime homogène, et l'écart "
                    "mesuré est rapporté ci-dessous."
                ),
            }

        parameters = {key: value for key, value in raw.items() if key in Config.__dataclass_fields__}
        config = Config(**parameters)
        session_id = time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
        session = LiveSession(
            Simulation(config),
            session_id,
            SESSIONS_DIR / session_id,
            label=label,
            origin=origin,
        )
        session.reference_path = reference_path
        session.reference_upto = reference_upto
        with self.lock:
            self.sessions[session_id] = session
            self.order.append(session_id)
        if mode == "resume":
            # Le rejeu jusqu'à t₀ se fait par la boucle NORMALE : la
            # progression est visible dans l'IHM, et le chemin de code est
            # exactement celui d'une session fraîche.
            session.set_speed(0.0)
            session.play()
        return session.describe()

    # -- HTTP --------------------------------------------------------------
    def handle_get(self, handler, parsed) -> bool:
        path = parsed.path
        if path == "/live2":
            handler._serve_file(TEMPLATES / "live.html", "text/html; charset=utf-8")
            return True
        if path.startswith("/live2/static/"):
            name = unquote(path[len("/live2/static/") :])
            candidate = (STATIC / name).resolve()
            if not str(candidate).startswith(str(STATIC.resolve())) or not candidate.exists():
                handler.send_error(HTTPStatus.NOT_FOUND)
                return True
            handler._serve_file(candidate)
            return True
        if path == "/api/live2/meta":
            handler._json_response(
                {
                    "params": PARAM_SEMANTICS,
                    "scopes": list(SCOPES),
                    "defaults": Config().to_dict(),
                    "create_fields": list(CREATE_FIELDS),
                    "runs": self._stored_runs(),
                }
            )
            return True
        if path == "/api/live2/sessions":
            with self.lock:
                payload = [self.sessions[key].describe() for key in self.order if key in self.sessions]
            handler._json_response(payload)
            return True
        if path.startswith("/api/live2/sessions/"):
            session_id = unquote(path.split("/")[4])
            try:
                session = self._session(session_id)
            except KeyError:
                handler.send_error(HTTPStatus.NOT_FOUND, f"session inconnue : {session_id}")
                return True
            since = int(parse_qs(parsed.query).get("since", ["0"])[0])
            handler._json_response(session.state(since=since))
            return True
        handler.send_error(HTTPStatus.NOT_FOUND)
        return True

    def handle_post(self, handler, parsed) -> bool:
        try:
            body = handler._read_json_body()
        except ValueError as exc:
            handler.send_error(HTTPStatus.BAD_REQUEST, str(exc))
            return True
        path = parsed.path

        if path == "/api/live2/sessions":
            try:
                payload = self.create(body)
            except (KeyError, ValueError, TypeError) as exc:
                handler.send_error(HTTPStatus.BAD_REQUEST, str(exc))
                return True
            handler._json_response(payload, status=HTTPStatus.CREATED)
            return True

        parts = path.strip("/").split("/")
        if len(parts) != 5 or parts[:3] != ["api", "live", "sessions"]:
            handler.send_error(HTTPStatus.NOT_FOUND)
            return True
        session_id, action = unquote(parts[3]), parts[4]
        try:
            session = self._session(session_id)
        except KeyError:
            handler.send_error(HTTPStatus.NOT_FOUND, f"session inconnue : {session_id}")
            return True

        try:
            payload = self._act(session, action, body)
        except (KeyError, ValueError, TypeError) as exc:
            handler.send_error(HTTPStatus.BAD_REQUEST, str(exc))
            return True
        handler._json_response(payload)
        return True

    def _act(self, session: LiveSession, action: str, body: dict) -> dict:
        if action == "play":
            session.play()
        elif action == "pause":
            session.pause()
        elif action == "stop":
            session.stop()
        elif action == "step":
            session.step_once(int(body.get("count", 1)))
        elif action == "speed":
            session.set_speed(float(body.get("speed", 0.0)))
        elif action == "extend":
            session.extend(int(body.get("steps", 1000)))
        elif action == "snapshot":
            return {"snapshot": str(session.snapshot(body.get("name") or None))}
        elif action == "save":
            return {"series": str(session.write_series())}
        elif action == "intervene":
            return session.submit(
                param=str(body["param"]),
                value=float(body["value"]),
                scope=str(body["scope"]),
                phi=None if body.get("phi") in (None, "") else float(body["phi"]),
                ids=body.get("ids") or None,
                note=str(body.get("note", "")),
            )
        else:
            raise ValueError(f"action inconnue : {action}")
        return session.describe()


_ROUTER: LiveRouter | None = None


def get_router(storage=None) -> LiveRouter:
    global _ROUTER
    if _ROUTER is None:
        _ROUTER = LiveRouter(storage=storage)
    elif storage is not None and _ROUTER.storage is None:
        _ROUTER.storage = storage
    return _ROUTER


def owns(path: str) -> bool:
    return path == "/live2" or path.startswith("/live2/") or path.startswith("/api/live2/")


def dump_meta() -> str:
    """Utilitaire de diagnostic en ligne de commande."""
    return json.dumps({"templates": str(TEMPLATES), "sessions_dir": str(SESSIONS_DIR)}, indent=2)
