"""Session « en direct » : boucle de pas pilotable, file d'interventions,
journal rejouable, snapshots, reprise depuis un run M4.3 stocké (prompt §4).

Choix d'architecture, justifiés dans `report/conception_m4_3live_v2.pdf` :

- UN THREAD, pas un sous-processus. `simulation_lab/jobs.py` utilise
  `multiprocessing.Process` pour ses runs batch (jobs.py:24-51) ; ce modèle
  est inadapté ici, car l'IHM interroge l'état à chaque demi-seconde et la
  population peut atteindre `pop_max=30000` entités : faire transiter cet
  état par une `Queue` à chaque pas coûterait davantage que le pas
  lui-même. Un `threading.Thread` partage l'état sans copie.
- PAS DE VERROU EN LECTURE. Le thread de boucle est le seul écrivain ;
  `Simulation.series` et `Simulation.tech_series` ne sont qu'APPENDÉES avec
  des dictionnaires déjà complets, et `list.append` / le découpage de liste
  sont atomiques sous le GIL. Un lecteur ne peut donc jamais voir un
  enregistrement partiel. Seule la file d'interventions, écrite par le
  thread HTTP et lue par le thread de boucle, est protégée
  (`Simulation._lock`).
- LA PAUSE NE CONSOMME AUCUN TIRAGE. C'est une porte (`threading.Event`)
  placée AVANT `step()` : N pas avec pauses produisent exactement la même
  trajectoire que N pas sans pause (testé, `tests/test_replay.py`).
- UN SEUL POINT D'ENTRÉE pour appliquer une intervention :
  `Simulation.submit`, appelé aussi bien par `LiveSession.submit` (IHM) que
  par le pilote sans tête. Le rejeu vérifie donc le chemin de code réel.
"""

from __future__ import annotations

import csv
import json
import pickle
import threading
import time
from dataclasses import replace
from pathlib import Path

from .model import Config, Intervention, Simulation

__all__ = [
    "LiveSession",
    "write_series",
    "save_snapshot",
    "load_snapshot",
    "replay",
    "resume_from_series",
    "divergence_report",
]


# Colonnes envoyées au navigateur : un sous-ensemble explicite de la série,
# pour garder la charge utile de sondage petite (§11, mécanisme de sondage).
STREAM_COLUMNS = (
    "t",
    "pop",
    "prod_tot",
    "K_tot",
    "nw_tot",
    "deaths",
    "defaults",
    "n_loans",
    "new_loans",
    "loan_volume",
    "interest_paid",
    "mkt_rounds",
    "mkt_blocked_dir",
    "mkt_blocked_tiny",
    "mkt_surplus",
    "n_avalanches",
    "max_avalanche",
    "mean_A",
    "mean_gamma",
    "n_tech_alive",
)


def write_series(simulation: Simulation, directory: str | Path) -> Path:
    """Écrit series.csv, tech_series.csv et kernel.json d'une simulation."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "series.csv"
    rows = simulation.series
    if not rows:
        return path
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    tech_rows = simulation.tech_series
    if tech_rows:
        with open(directory / "tech_series.csv", "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(tech_rows[0]))
            writer.writeheader()
            writer.writerows(tech_rows)
    (directory / "kernel.json").write_text(
        json.dumps(simulation.kernel.describe(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


# --------------------------------------------------------------------------
# Snapshots
# --------------------------------------------------------------------------
def save_snapshot(simulation: Simulation, path: str | Path) -> Path:
    """Sérialise l'état COMPLET d'une simulation à son t courant.

    Contenu : population, carnet de prêts, registre de technologies, caches
    du noyau de principal (y compris les COMPTEURS d'usage — sans eux, une
    branche restaurée compilerait ses tables à un indice d'appel différent
    de la branche continuée et divergerait), état du générateur, séries
    déjà mesurées et journal d'interventions.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "config": simulation.config,
        "rng": simulation.rng,
        "population": simulation.population,
        "book": simulation.book,
        "registry": simulation.registry,
        "kernel": simulation.kernel,
        "t": simulation.t,
        "status": simulation.status,
        "series": simulation.series,
        "tech_series": simulation.tech_series,
        "deaths": simulation.deaths,
        "avalanches": simulation.avalanches,
        "avalanche_members": simulation.avalanche_members,
        "intervention_log": simulation.intervention_log,
        "default_A": simulation.default_A,
        "default_gamma": simulation.default_gamma,
        "default_tech": simulation.default_tech,
        "avalanche_id_counter": simulation._avalanche_id_counter,
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as handle:
        pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
    tmp.replace(path)
    return path


def load_snapshot(path: str | Path, config: Config | None = None) -> Simulation:
    """Reconstruit une simulation depuis un snapshot.

    `config` permet de repartir du MÊME état avec des paramètres différents
    (typiquement un `T` plus long) : c'est ce qui permet de brancher
    plusieurs bras d'expérience sur un unique t₀ (§7).
    """
    with open(path, "rb") as handle:
        payload = pickle.load(handle)
    simulation = Simulation.__new__(Simulation)
    simulation.config = config if config is not None else payload["config"]
    simulation.rng = payload["rng"]
    simulation.population = payload["population"]
    simulation.book = payload["book"]
    simulation.registry = payload["registry"]
    simulation.kernel = payload["kernel"]
    simulation.t = payload["t"]
    simulation.status = payload["status"]
    simulation.series = list(payload["series"])
    simulation.tech_series = list(payload["tech_series"])
    simulation.deaths = list(payload["deaths"])
    simulation.avalanches = list(payload["avalanches"])
    simulation.avalanche_members = list(payload["avalanche_members"])
    simulation.loan_events = []
    simulation.intervention_log = list(payload["intervention_log"])
    simulation.default_A = payload["default_A"]
    simulation.default_gamma = payload["default_gamma"]
    simulation.default_tech = payload["default_tech"]
    simulation._avalanche_id_counter = payload["avalanche_id_counter"]
    simulation._pending = []
    simulation._lock = threading.Lock()
    return simulation


# --------------------------------------------------------------------------
# Rejeu sans tête
# --------------------------------------------------------------------------
def replay(
    config: Config,
    journal: list[dict],
    steps: int | None = None,
    simulation: Simulation | None = None,
    on_step=None,
) -> Simulation:
    """Rejoue (graine, paramètres, journal) et doit reproduire la trajectoire.

    Chaque entrée du journal est soumise AVANT le pas dont elle porte le t :
    `submit` la met en file, `step` la vide en tout début de pas. C'est
    exactement le chemin suivi par une intervention arrivée en HTTP.
    """
    simulation = Simulation(config) if simulation is None else simulation
    planned: dict[int, list[Intervention]] = {}
    for entry in journal:
        planned.setdefault(int(entry["t"]), []).append(Intervention.from_dict(entry))
    target = config.T if steps is None else simulation.t + steps
    while simulation.t < target and simulation.status == "ok":
        for intervention in planned.get(simulation.t + 1, ()):
            simulation.submit(intervention)
        simulation.step()
        if on_step is not None:
            on_step(simulation)
    return simulation


# --------------------------------------------------------------------------
# Reprise depuis un run M4.3 stocké et mesure de divergence
# --------------------------------------------------------------------------
DIVERGENCE_COLUMNS = (
    "pop",
    "K_tot",
    "nw_tot",
    "prod_tot",
    "n_loans",
    "new_loans",
    "loan_volume",
    "interest_paid",
    "deaths",
    "defaults",
)


def divergence_report(
    simulation: Simulation, reference_rows: list[dict], upto: int
) -> dict:
    """Compare la trajectoire rejouée à une série stockée, jusqu'à `upto`.

    M4.3Live est un fork d'institution différente (§3) : rejouer un run M4.3
    avec ce moteur ne reproduit sa trajectoire QUE dans le régime homogène,
    et rien ne le garantit hors de ce régime. Cette fonction MESURE l'écart
    au lieu de le supposer ; l'appelant est tenu de le rapporter.
    """
    compared = min(upto, len(simulation.series), len(reference_rows))
    worst: dict[str, float] = {}
    worst_relative = 0.0
    first_difference = None
    for index in range(compared):
        row = simulation.series[index]
        reference = reference_rows[index]
        for column in DIVERGENCE_COLUMNS:
            if column not in reference:
                continue
            value = float(row[column])
            expected = float(reference[column])
            gap = abs(value - expected)
            if gap > worst.get(column, 0.0):
                worst[column] = gap
            scale = max(1.0, abs(expected))
            if gap / scale > worst_relative:
                worst_relative = gap / scale
            if value != expected and first_difference is None:
                first_difference = {
                    "t": index + 1,
                    "column": column,
                    "obtained": value,
                    "expected": expected,
                }
    return {
        "n_compared": compared,
        "bit_identical": first_difference is None,
        "first_difference": first_difference,
        "max_absolute": {k: v for k, v in sorted(worst.items()) if v > 0.0},
        "max_relative": worst_relative,
    }


def read_series_csv(path: str | Path) -> list[dict]:
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def resume_from_series(
    parameters: dict,
    series_path: str | Path,
    t0: int,
    overrides: dict | None = None,
) -> tuple[Simulation, dict]:
    """Rejoue un run M4.3 stocké jusqu'à t₀ et MESURE l'écart obligatoirement.

    Retourne la simulation amenée à t₀ et le rapport de divergence, qui doit
    être affiché tel quel : une reprise n'est JAMAIS présentée comme
    identique au run d'origine sans cette mesure (§4).
    """
    known = set(Config.__dataclass_fields__)
    kwargs = {key: value for key, value in parameters.items() if key in known}
    kwargs["T"] = int(t0)
    if overrides:
        kwargs.update(overrides)
    config = Config(**kwargs)
    simulation = Simulation(config)
    simulation.run()
    reference = read_series_csv(series_path)
    return simulation, divergence_report(simulation, reference, int(t0))


# --------------------------------------------------------------------------
# Session en direct
# --------------------------------------------------------------------------
class LiveSession:
    """Boucle de pas pilotable, avec journal d'interventions sur disque."""

    def __init__(
        self,
        simulation: Simulation,
        session_id: str,
        directory: str | Path,
        label: str = "",
        origin: dict | None = None,
    ) -> None:
        self.simulation = simulation
        self.session_id = session_id
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.label = label
        self.origin = origin or {}
        self.created_at = time.time()
        self.error: str | None = None
        # Reprise depuis un run stocké : la série de référence et le t₀
        # jusqu'auquel l'écart DOIT être mesuré et rapporté (§4).
        self.reference_path: str | Path | None = None
        self.reference_upto = 0
        self.divergence: dict | None = None

        self._thread: threading.Thread | None = None
        self._gate = threading.Event()  # armé = la boucle avance
        self._stop = threading.Event()
        self._single = 0
        self._single_lock = threading.Lock()
        self._speed = 0.0  # pas/s ; 0 = aussi vite que possible
        self._journal_written = 0
        self._recent: list[float] = []
        self._steps_per_second = 0.0

        self._write_config()
        self._flush_journal()

    # -- fichiers ----------------------------------------------------------
    @property
    def journal_path(self) -> Path:
        return self.directory / "interventions.jsonl"

    def _write_config(self) -> None:
        payload = {
            "session_id": self.session_id,
            "label": self.label,
            "origin": self.origin,
            "model_version": "m4_3live_v2-1",
            "parameters": self.simulation.config.to_dict(),
            "t_start": self.simulation.t,
            "fixed_rules": {
                "phase_order": (
                    "interventions_births_shock_production_interest_"
                    "depreciation_market_bankruptcy_measures"
                ),
                "principal_rule": "joint_production_optimum (delta = h(C) - K_b)",
                "rate_rule": self.simulation.config.rate_rule,
                "pool_size": 2,
                "bankruptcy": "cancel_and_destroy",
            },
        }
        (self.directory / "config.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _flush_journal(self) -> None:
        """Écrit les interventions APPLIQUÉES pas encore journalisées."""
        log = self.simulation.intervention_log
        if len(log) <= self._journal_written:
            return
        with open(self.journal_path, "a", encoding="utf-8") as handle:
            for entry in log[self._journal_written :]:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._journal_written = len(log)

    def write_series(self) -> Path:
        return write_series(self.simulation, self.directory)

    def snapshot(self, name: str | None = None) -> Path:
        name = name or f"snapshot_t{self.simulation.t}.pkl"
        return save_snapshot(self.simulation, self.directory / name)

    # -- contrôles de lecture ---------------------------------------------
    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name=f"live-{self.session_id}", daemon=True)
        self._thread.start()

    def play(self) -> None:
        self.start()
        self._gate.set()

    def pause(self) -> None:
        self._gate.clear()

    def step_once(self, count: int = 1) -> None:
        """Avance de `count` pas en restant en pause. Aucun tirage n'est
        consommé par la mise en pause elle-même."""
        self.start()
        with self._single_lock:
            self._single += int(count)

    def set_speed(self, steps_per_second: float) -> None:
        self._speed = max(0.0, float(steps_per_second))

    def extend(self, steps: int) -> None:
        """Repousse la cible T de `steps` pas à partir du t courant."""
        self.simulation.config = replace(
            self.simulation.config, T=self.simulation.t + max(1, int(steps))
        )

    def stop(self) -> None:
        self._stop.set()
        self._gate.set()
        thread = self._thread
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=10.0)
        self._gate.clear()

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def paused(self) -> bool:
        return not self._gate.is_set()

    def _claim_single(self) -> bool:
        with self._single_lock:
            if self._single > 0:
                self._single -= 1
                return True
        return False

    def _loop(self) -> None:
        simulation = self.simulation
        try:
            while not self._stop.is_set():
                if simulation.status != "ok":
                    self._gate.clear()
                    time.sleep(0.05)
                    continue
                target = simulation.config.T
                if target and simulation.t >= target:
                    self._gate.clear()
                    time.sleep(0.05)
                    continue
                if not self._gate.is_set() and not self._claim_single():
                    # PAUSE : on attend sans toucher au générateur.
                    time.sleep(0.02)
                    continue
                started = time.perf_counter()
                simulation.step()
                elapsed = time.perf_counter() - started
                self._recent.append(elapsed)
                if len(self._recent) > 50:
                    del self._recent[:-50]
                total = sum(self._recent)
                self._steps_per_second = len(self._recent) / total if total > 0 else 0.0
                self._flush_journal()
                if self._speed > 0.0:
                    remaining = 1.0 / self._speed - elapsed
                    if remaining > 0:
                        time.sleep(remaining)
        except Exception as exc:  # noqa: BLE001 - remonté à l'IHM
            self.error = f"{type(exc).__name__}: {exc}"
            self._gate.clear()

    # -- interventions -----------------------------------------------------
    def submit(
        self,
        param: str,
        value: float,
        scope: str,
        phi: float | None = None,
        ids: list[int] | None = None,
        note: str = "",
    ) -> dict:
        intervention = Intervention(
            param=param, value=float(value), scope=scope, phi=phi, ids=ids, note=note
        )
        self.simulation.submit(intervention)
        return {
            "queued": True,
            "param": param,
            "value": value,
            "scope": scope,
            "phi": phi,
            "t_submitted": self.simulation.t,
        }

    # -- état pour l'IHM ---------------------------------------------------
    def _maybe_verify(self) -> None:
        """Calcule l'écart à la série d'origine dès que t₀ est atteint.

        Appelé à chaque sondage d'état : le rapport est donc TOUJOURS dans
        la charge utile envoyée au navigateur, jamais calculé en silence.
        """
        if self.divergence is not None or not self.reference_path:
            return
        if self.simulation.t < self.reference_upto:
            return
        self.divergence = divergence_report(
            self.simulation, read_series_csv(self.reference_path), self.reference_upto
        )
        (self.directory / "divergence.json").write_text(
            json.dumps(self.divergence, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def cohorts(self) -> list[dict]:
        """Moyennes de A et γ par cohorte, de part et d'autre de chaque
        intervention appliquée (§5 de la spécification).

        La vue par technologie donne la dispersion complète ; celle-ci répond
        à une question différente et complémentaire : « les entités nées après
        cette intervention diffèrent-elles de celles nées avant ? ». Les deux
        coïncident pour la portée `new` (où technologie et cohorte de naissance
        sont la même chose) et divergent pour `fraction`, qui traite des
        entités réparties dans toutes les cohortes.
        """
        population = self.simulation.population
        living = population.living()
        if not living:
            return []
        rows = []
        for entry in self.simulation.intervention_log:
            boundary = int(entry["t"])
            before = [e for e in living if population.birth[e] < boundary]
            after = [e for e in living if population.birth[e] >= boundary]
            rows.append(
                {
                    "t": boundary,
                    "param": entry["param"],
                    "scope": entry["scope"],
                    "n_before": len(before),
                    "n_after": len(after),
                    "mean_A_before": (
                        sum(population.A[e] for e in before) / len(before) if before else None
                    ),
                    "mean_A_after": (
                        sum(population.A[e] for e in after) / len(after) if after else None
                    ),
                    "mean_gamma_before": (
                        sum(population.g[e] for e in before) / len(before) if before else None
                    ),
                    "mean_gamma_after": (
                        sum(population.g[e] for e in after) / len(after) if after else None
                    ),
                }
            )
        return rows

    def state(self, since: int = 0, limit: int = 4000) -> dict:
        self._maybe_verify()
        simulation = self.simulation
        series = simulation.series
        rows = [row for row in series[since:] if row["t"] > since]
        if len(rows) > limit:
            stride = len(rows) // limit + 1
            rows = rows[::stride] + rows[-1:]
        latest_t = simulation.t
        # La photo par technologie est prise sur le DERNIER pas effectivement
        # mesuré, pas sur `simulation.t` : le thread de boucle peut avoir déjà
        # incrémenté t sans avoir fini d'écrire les lignes de ce pas, et
        # comparer à t donnerait alors une liste vide.
        techs = {}
        tech_t = simulation.tech_series[-1]["t"] if simulation.tech_series else 0
        for entry in reversed(simulation.tech_series):
            if entry["t"] != tech_t:
                break
            techs[entry["tech"]] = entry
        return {
            "session_id": self.session_id,
            "label": self.label,
            "origin": self.origin,
            "t": latest_t,
            "T": simulation.config.T,
            "status": simulation.status,
            "error": self.error,
            "running": self.running,
            "paused": self.paused,
            "speed": self._speed,
            "steps_per_second": self._steps_per_second,
            "pending": simulation.pending_count(),
            "default_A": simulation.default_A,
            "default_gamma": simulation.default_gamma,
            "parameters": simulation.config.to_dict(),
            "series": [{column: row[column] for column in STREAM_COLUMNS} for row in rows],
            "tech": [techs[key] for key in sorted(techs)],
            "tech_t": tech_t,
            "cohorts": self.cohorts(),
            "journal": simulation.intervention_log,
            "kernel": simulation.kernel.describe()["path_counts"],
            "divergence": self.divergence,
            "directory": str(self.directory),
        }

    def describe(self) -> dict:
        return {
            "session_id": self.session_id,
            "label": self.label,
            "t": self.simulation.t,
            "T": self.simulation.config.T,
            "status": self.simulation.status,
            "running": self.running,
            "paused": self.paused,
            "created_at": self.created_at,
            "origin": self.origin,
            "divergence": self.divergence,
            "n_interventions": len(self.simulation.intervention_log),
        }


def read_journal(path: str | Path) -> list[dict]:
    entries = []
    path = Path(path)
    if not path.exists():
        return entries
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def config_with(config: Config, **changes) -> Config:
    return replace(config, **changes)
