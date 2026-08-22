"""Aiguillage vers l'IHM « direct » de M4.3Live-v2 (`/live2`, `/api/live2/*`).

Ce module est la SEULE addition de `simulation_lab` pour M4.3Live-v2. Il est
volontairement minuscule et sans effet de bord à l'import : le routeur réel
vit dans `m4_3live_v2_credit_soc/web/router.py`, avec le reste du programme
M4.3Live-v2, et n'est chargé qu'à la première requête `/live`. Les branches
existantes de `do_GET`/`do_POST` ne sont pas touchées ; si le dossier
M4.3Live-v2 est absent ou cassé, `simulation_lab` continue de fonctionner
exactement comme avant (le routeur renvoie alors 503, jamais une
exception qui tuerait le serveur).

Le routeur est chargé PAR CHEMIN DE FICHIER plutôt que comme paquet
`web.router` : cela évite d'introduire un nom de premier niveau générique
(`web`) dans `sys.modules`, qui entrerait en collision avec n'importe quel
autre paquet du dépôt portant ce nom.
"""

from __future__ import annotations

import importlib.util
import sys
import traceback
from http import HTTPStatus

from simulation_lab.settings import ROOT_DIR

ROUTER_PATH = ROOT_DIR / "m4_3live_v2_credit_soc" / "web" / "router.py"
MODULE_NAME = "m4_3live_v2_web_router"

_module = None
_load_error: str | None = None


def available() -> bool:
    return ROUTER_PATH.exists()


def owns(path: str) -> bool:
    """Vrai pour les seules routes de M4.3Live-v2."""
    return path == "/live2" or path.startswith("/live2/") or path.startswith("/api/live2/")


def _load():
    global _module, _load_error
    if _module is not None or _load_error is not None:
        return _module
    try:
        spec = importlib.util.spec_from_file_location(MODULE_NAME, ROUTER_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules[MODULE_NAME] = module
        spec.loader.exec_module(module)
        _module = module
    except Exception:  # noqa: BLE001 - le serveur ne doit pas tomber
        _load_error = traceback.format_exc()
    return _module


def dispatch(handler, parsed, method: str) -> None:
    """Traite une route `/live`. Ne lève jamais vers le serveur."""
    if not available():
        handler.send_error(
            HTTPStatus.SERVICE_UNAVAILABLE,
            "M4.3Live-v2 n'est pas installé dans ce dépôt (m4_3live_v2_credit_soc/web/router.py absent)",
        )
        return
    module = _load()
    if module is None:
        handler.send_error(
            HTTPStatus.SERVICE_UNAVAILABLE,
            f"chargement de l'IHM M4.3Live-v2 impossible : {(_load_error or '').strip().splitlines()[-1:]}",
        )
        return
    router = module.get_router(getattr(handler.server, "storage", None))
    if method == "GET":
        router.handle_get(handler, parsed)
    else:
        router.handle_post(handler, parsed)
