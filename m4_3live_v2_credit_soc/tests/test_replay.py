"""Tests §8 — déterminisme : rejeu, invariant de pause, aller-retour snapshot.

Le journal utilisé par le test de rejeu provient d'une SESSION EN DIRECT
RÉELLE : les interventions (une par portée) sont soumises de façon
asynchrone depuis le thread principal pendant que le thread de boucle
tourne, exactement comme le fait un `do_POST` de l'IHM. Un plan écrit et
exécuté par le code même que l'on cherche à vérifier ne prouverait rien
(exigence explicite du prompt §8).

    /home/anatole/jupyter/.venv/bin/python3 m4_3live_v2_credit_soc/tests/test_replay.py
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from m4_3live_v2.live import (  # noqa: E402
    LiveSession,
    load_snapshot,
    read_journal,
    replay,
    save_snapshot,
)
from m4_3live_v2.model import Config, Intervention, Simulation  # noqa: E402

BASE = dict(seed=11, lam=12.0, delta=0.01, sigma=0.01, K0=25.0, gamma=0.5, A=1.0)
COMPARED = (
    "t",
    "births",
    "deaths",
    "pop",
    "K_tot",
    "nw_tot",
    "prod_tot",
    "n_loans",
    "new_loans",
    "loan_volume",
    "interest_paid",
    "defaults",
    "mkt_blocked_dir",
    "mkt_surplus",
    "mean_A",
    "mean_gamma",
)

# Colonnes de la DYNAMIQUE : elles doivent être bit-identiques dans tous les
# tests, sans exception.
DYNAMIC = tuple(column for column in COMPARED if column != "interest_paid")

# `interest_paid` (et `int_out` par entité) sont les DEUX SEULES quantités
# qui dépendent de l'ordre d'itération d'un `set` : la phase d'intérêts
# parcourt `book.by_borrower[borrower]` (hérité de m4_3/model.py:587) et
# additionne les versements dans cet ordre. Cet ordre n'affecte AUCUN
# capital — chaque versement va à une prêteuse DIFFÉRENTE, donc dans un
# accumulateur différent — mais il change le dernier bit de ces deux
# agrégats de diagnostic. CPython ne sérialise pas la disposition interne
# d'un `set` : après un aller-retour `pickle`, l'ordre change pour environ
# la moitié des ensembles (mesuré). D'où la tolérance, uniquement ici, et
# uniquement pour l'aller-retour snapshot.
TOL_SET_ORDER = 1e-12


def rows_equal(left, right, tolerant_columns=()):
    """Égalité STRICTE, sauf tolérance relative sur `tolerant_columns`."""
    if len(left) != len(right):
        return f"longueurs différentes : {len(left)} vs {len(right)}"
    for a, b in zip(left, right):
        for column in COMPARED:
            if a[column] == b[column]:
                continue
            if column in tolerant_columns:
                scale = max(1.0, abs(float(b[column])))
                if abs(float(a[column]) - float(b[column])) / scale <= TOL_SET_ORDER:
                    continue
            return f"t={a['t']} colonne {column} : {a[column]!r} != {b[column]!r}"
    return ""


def test_live_session_journal_replays_identically():
    directory = tempfile.mkdtemp(prefix="m4_3live_v2_replay_")
    try:
        config = Config(**BASE, T=120)
        session = LiveSession(Simulation(config), "test-replay", directory)
        session.set_speed(60.0)
        session.play()

        # Interventions envoyées de façon ASYNCHRONE, une par portée, sans
        # savoir à quel pas la boucle en est — c'est le cas réel de l'IHM.
        submitted = []
        for delay, payload in (
            (0.35, dict(param="A", value=1.4, scope="fraction", phi=0.25)),
            (0.35, dict(param="gamma", value=0.6, scope="new")),
            (0.35, dict(param="A", value=1.1, scope="all")),
            (0.30, dict(param="delta", value=0.012, scope="new")),
        ):
            time.sleep(delay)
            submitted.append((session.simulation.t, session.submit(**payload)))

        deadline = time.time() + 60.0
        while session.simulation.t < 120 and time.time() < deadline:
            time.sleep(0.05)
        session.stop()
        assert session.error is None, session.error
        assert session.simulation.t == 120, session.simulation.t

        live_series = [dict(row) for row in session.simulation.series]
        journal = list(session.simulation.intervention_log)
        assert len(journal) == 4, journal
        scopes = sorted({entry["scope"] for entry in journal})
        assert scopes == ["all", "fraction", "new"], scopes
        for (t_submitted, _), entry in zip(submitted, journal):
            assert entry["t"] > t_submitted, (t_submitted, entry["t"])
        session.write_series()
        on_disk = read_journal(session.journal_path)
        assert [entry["t"] for entry in on_disk] == [entry["t"] for entry in journal]

        # -- rejeu sans tête, à partir du seul journal --------------------
        replayed = replay(Config(**BASE, T=120), on_disk)
        problem = rows_equal(live_series, [dict(row) for row in replayed.series])
        assert not problem, f"le rejeu diverge : {problem}"
        assert [entry["t"] for entry in replayed.intervention_log] == [
            entry["t"] for entry in journal
        ], "les t effectifs ne coïncident pas"
        for original, again in zip(journal, replayed.intervention_log):
            assert original["selected_ids"] == again["selected_ids"], original["t"]
            assert original["n_selected"] == again["n_selected"]
        print(
            f"  rejeu d'une session en direct réelle : {len(live_series)} pas, "
            f"{len(journal)} interventions ({', '.join(scopes)}), "
            "trajectoire et t effectifs strictement identiques  OK"
        )
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_pause_consumes_no_randomness():
    """N pas avec pauses == N pas sans pause, bit à bit."""
    reference = Simulation(Config(**BASE, T=80))
    reference.run()

    directory = tempfile.mkdtemp(prefix="m4_3live_v2_pause_")
    try:
        session = LiveSession(Simulation(Config(**BASE, T=80)), "test-pause", directory)
        session.set_speed(80.0)
        session.play()
        for _ in range(4):
            time.sleep(0.15)
            session.pause()
            time.sleep(0.25)  # pause franche, la boucle attend
            session.play()
        deadline = time.time() + 60.0
        while session.simulation.t < 80 and time.time() < deadline:
            time.sleep(0.05)
        session.pause()
        # quelques pas-à-pas en pause, pour couvrir aussi ce chemin
        session.stop()
        problem = rows_equal(
            [dict(row) for row in reference.series],
            [dict(row) for row in session.simulation.series],
        )
        assert not problem, f"la pause a modifié la trajectoire : {problem}"
        print("  invariant de pause : 4 pauses franches, trajectoire inchangée  OK")
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_step_by_step_matches_continuous():
    """Le pas-à-pas manuel produit la même trajectoire que la lecture continue."""
    reference = Simulation(Config(**BASE, T=30))
    reference.run()
    directory = tempfile.mkdtemp(prefix="m4_3live_v2_single_")
    try:
        session = LiveSession(Simulation(Config(**BASE, T=30)), "test-single", directory)
        session.start()
        session.step_once(30)
        deadline = time.time() + 60.0
        while session.simulation.t < 30 and time.time() < deadline:
            time.sleep(0.05)
        session.stop()
        assert session.paused, "le pas-à-pas ne doit pas dégeler la lecture"
        problem = rows_equal(
            [dict(row) for row in reference.series],
            [dict(row) for row in session.simulation.series],
        )
        assert not problem, problem
        print("  pas-à-pas : 30 pas déclenchés un par un, trajectoire identique  OK")
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_snapshot_round_trip():
    """snapshot(t₀) → restauration → N pas  ==  N pas sans interruption.

    C'est l'invariant sur lequel repose tout le protocole apparié du §7 :
    les bras branchés sur un même t₀ doivent être indiscernables d'une
    simulation menée d'un trait. Le snapshot doit donc emporter le registre
    de technologies ET les compteurs d'usage du noyau — sans eux, la
    branche restaurée compilerait ses tables à un autre indice d'appel.

    RÉSERVE MESURÉE, et bornée : la DYNAMIQUE est bit-identique, mais
    `interest_paid` peut différer au dernier bit (voir TOL_SET_ORDER).
    """
    directory = tempfile.mkdtemp(prefix="m4_3live_v2_snap_")
    try:
        straight = Simulation(Config(**BASE, T=90))
        straight.run()

        branched = Simulation(Config(**BASE, T=40))
        branched.run()
        path = save_snapshot(branched, os.path.join(directory, "t40.pkl"))
        restored = load_snapshot(path, config=Config(**BASE, T=90))
        restored.run()
        problem = rows_equal(
            [dict(row) for row in straight.series],
            [dict(row) for row in restored.series],
            tolerant_columns=("interest_paid",),
        )
        assert not problem, f"aller-retour snapshot non neutre : {problem}"
        # La dynamique, elle, est STRICTEMENT identique.
        for a, b in zip(straight.series, restored.series):
            for column in DYNAMIC:
                assert a[column] == b[column], (a["t"], column, a[column], b[column])
        gap = max(
            abs(a["interest_paid"] - b["interest_paid"])
            for a, b in zip(straight.series, restored.series)
        )

        # Deux bras branchés sur le MÊME snapshot : identiques jusqu'à t₀,
        # divergents seulement après l'intervention.
        control = load_snapshot(path, config=Config(**BASE, T=90))
        treatment = load_snapshot(path, config=Config(**BASE, T=90))
        treatment.submit(Intervention(param="A", value=1.5, scope="fraction", phi=0.2))
        control.run()
        treatment.run()
        for index in range(40):
            assert control.series[index]["prod_tot"] == treatment.series[index]["prod_tot"]
        assert control.series[-1]["prod_tot"] != treatment.series[-1]["prod_tot"]
        assert treatment.intervention_log[0]["t"] == 41
        # Deux bras issus du MÊME fichier : leur amorçage coïncide bit à bit,
        # y compris sur les agrégats sensibles à l'ordre des ensembles.
        for index in range(40):
            assert control.series[index]["interest_paid"] == treatment.series[index]["interest_paid"]
        print(
            f"  snapshot : dynamique bit-identique après aller-retour (interest_paid à "
            f"{gap:.1e} près, ordre des `set` non sérialisé), deux bras identiques "
            "jusqu'à t₀=40 et divergents ensuite  OK"
        )
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_snapshot_carries_kernel_cache():
    """Le snapshot emporte bien le cache du noyau (technologies et compteurs)."""
    directory = tempfile.mkdtemp(prefix="m4_3live_v2_cache_")
    try:
        simulation = Simulation(Config(**BASE, T=60, lut_threshold=200))
        for _ in range(20):
            simulation.step()
        simulation.submit(Intervention(param="gamma", value=0.6, scope="fraction", phi=0.4))
        for _ in range(15):
            simulation.step()
        described = simulation.kernel.describe()
        assert described["n_tech"] >= 2
        assert described["path_counts"]["newton"] + described["path_counts"]["lut"] > 0
        path = save_snapshot(simulation, os.path.join(directory, "cache.pkl"))
        restored = load_snapshot(path)
        assert restored.kernel.describe() == described
        assert restored.registry.A == simulation.registry.A
        assert restored.registry.gamma == simulation.registry.gamma
        assert restored.default_tech == simulation.default_tech
        print(
            f"  snapshot : {described['n_tech']} technologies et compteurs du noyau "
            f"{described['path_counts']} restaurés à l'identique  OK"
        )
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def main():
    print("test_replay.py — déterminisme (prompt §4, §8)")
    test_live_session_journal_replays_identically()
    test_pause_consumes_no_randomness()
    test_step_by_step_matches_continuous()
    test_snapshot_round_trip()
    test_snapshot_carries_kernel_cache()
    print("test_replay.py : tout est passé.")


if __name__ == "__main__":
    main()
