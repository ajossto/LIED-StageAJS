"""Tests des invariants I1, I4, I7, I8, I9 et de la réduction R1' (sans
crédit : personne ne meurt, trajectoire K identique au calcul manuel),
sur runs courts à seed fixe. Assertions Python simples — pas de pytest.

R1' remplace la R1 du fork L/K : la réduction bit à bit vers m2_fable
reposait sur le plancher d0 de M2, retiré du code à la refonte. Sans crédit,
le moteur fusionné n'a AUCUN mécanisme de mort (NW = K > 0) — c'est le
comportement attendu et testé, avec l'identité de trajectoire par entité."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np

from m4.config import M4Config
from m4.simulation import Simulation


def test_I1_nonnegative():
    """I1 : aucun K < 0 à la fin d'un run baseline."""
    sim = Simulation(M4Config(seed=3, T=250))
    sim.run()
    for i in range(len(sim.pop)):
        assert sim.pop.K[i] >= 0.0, (i, sim.pop.K[i])


def test_I4_global_balance():
    """I4 : bilan global par pas — pour chaque ligne de series,
    Delta(K_tot) == injected + shock_gain + prod_tot - depreciated
    - destroyed (tolérance relative 1e-6). Les transferts (prêts, intérêts,
    naissances financées, résidu prorata) sont conservatifs et n'apparaissent
    pas dans le bilan."""
    for kw in (dict(), dict(birth_loan=True),
               dict(fail_residual="prorata", fail_lender_loans="transfer")):
        cfg = M4Config(seed=7, T=200, **kw)
        sim = Simulation(cfg)
        sim.run()
        assert len(sim.series) == 200
        prev = 0.0  # N(0) = 0 : richesse réelle initiale nulle
        for s in sim.series:
            total = s["K_tot"]
            lhs = total - prev
            rhs = (s["injected"] + s["shock_gain"] + s["prod_tot"]
                   - s["depreciated"] - s["destroyed"])
            tol = 1e-6 * max(1.0, abs(total))
            assert abs(lhs - rhs) <= tol, (kw, s["t"], lhs, rhs, lhs - rhs)
            prev = total


def test_I7_seed_reproducibility():
    """I7 : deux Simulation même seed -> séries identiques champ à champ."""
    sim1 = Simulation(M4Config(seed=5, T=150))
    sim2 = Simulation(M4Config(seed=5, T=150))
    sim1.run()
    sim2.run()
    assert len(sim1.series) == len(sim2.series)
    for s1, s2 in zip(sim1.series, sim2.series):
        assert s1.keys() == s2.keys()
        for key in s1:
            assert s1[key] == s2[key], (s1["t"], key, s1[key], s2[key])


def test_I8_snapshots_no_effect():
    """I8 STRICT : run avec snapshots vs run sans -> séries identiques bit à
    bit. (Bug historique M3 : snapshot() insérait des clés vides dans les
    defaultdict du carnet via [] ; accès en .get() désormais.)"""
    sim1 = Simulation(M4Config(seed=9, T=150))
    sim2 = Simulation(M4Config(seed=9, T=150))
    sim1.run()
    grabbed = []
    sim2.run(snapshot_times=(50, 100, 140),
             on_snapshot=lambda t, snap, net: grabbed.append(t))
    assert grabbed == [50, 100, 140]
    assert len(sim1.series) == len(sim2.series)
    for s1, s2 in zip(sim1.series, sim2.series):
        for key in s1:
            assert s1[key] == s2[key], (s1["t"], key, s1[key], s2[key])


def test_R1_no_credit_no_death():
    """R1' : credit=False -> personne n'a jamais de dette, NW = K > 0,
    AUCUNE mort ; la population croît comme le cumul des naissances ;
    trajectoire K de la première entité == calcul manuel pas à pas."""
    cfg = M4Config(credit=False, seed=11, T=120)
    sim = Simulation(cfg)
    # rejouer la séquence RNG en parallèle pour la trajectoire manuelle
    rng = np.random.default_rng(cfg.seed)
    first = None       # (id, K courant)
    var = cfg.sigma ** 2
    n_alive = 0
    for t in range(1, cfg.T + 1):
        births = int(rng.poisson(cfg.lam))
        n_alive += births
        if first is None and births > 0:
            first = [0, cfg.K0]
        if n_alive > 0:
            eta = rng.normal(-0.5 * var, cfg.sigma, size=n_alive)
            if first is not None:
                k = first[1] * math.exp(eta[first[0]])
                k += cfg.alpha * math.sqrt(k)
                k *= 1.0 - cfg.delta
                first[1] = k if k > cfg.w_clamp else 0.0
        sim.step()
        s = sim.series[-1]
        assert s["births"] == births, (t, s["births"], births)
        assert s["deaths"] == 0
        assert s["pop"] == n_alive
    assert sum(s["deaths"] for s in sim.series) == 0
    assert len(sim.book) == 0
    assert first is not None
    assert abs(sim.pop.K[0] - first[1]) < 1e-9 * max(1.0, first[1]), \
        (sim.pop.K[0], first[1])


def test_birth_loan_accounting():
    """birth_loan : la part financée sort de la prêteuse (transfert réel),
    le contrat existe, NW du nouveau-né = apport en fonds propres."""
    from m4.bankruptcy import net_worth
    cfg = M4Config(birth_loan=True, birth_equity=0.2, lam=0.0, sigma=0.0,
                   credit=False)
    sim = Simulation(cfg)
    # amorce : une prêteuse riche, puis forcer une naissance via _born
    rich = sim.pop.born(1000.0, 0)
    sim.t = 1
    injected = sim._born(1)
    newborn = 1
    q_loan = cfg.K0 * (1.0 - cfg.birth_equity)
    assert sim.pop.K[newborn] == cfg.K0
    assert sim.pop.K[rich] == 1000.0 - q_loan
    assert len(sim.book) == 1
    assert sim.book.debts[newborn] == q_loan
    assert abs(net_worth(sim.pop, sim.book, cfg, newborn)
               - cfg.birth_equity * cfg.K0) < 1e-12
    assert injected == cfg.K0 - q_loan       # seul l'apport est injecté
    assert sim.equity_births == 0


def test_birth_loan_fallback_equity():
    """birth_loan sans prêteuse faisable : repli fonds propres, injection
    complète, compteur equity_births incrémenté."""
    cfg = M4Config(birth_loan=True, birth_equity=0.2, lam=0.0, sigma=0.0,
                   credit=False)
    sim = Simulation(cfg)
    sim.t = 1
    injected = sim._born(1)                  # population vide : pas de pool
    assert sim.equity_births == 1
    assert injected == cfg.K0
    assert len(sim.book) == 0


def test_I9_runs_clean():
    """I9 : le run ne lève pas RuntimeError (cascade avec point fixe)."""
    sim = Simulation(M4Config(seed=13, T=300))
    try:
        status = sim.run()
    except RuntimeError as exc:
        raise AssertionError(f"I9 violé : {exc}")
    assert status in ("ok", "extinction", "explosion")
    assert sim.t == 300 or status != "ok"


def _main():
    mod = sys.modules[__name__]
    names = sorted(n for n in dir(mod) if n.startswith("test_"))
    for name in names:
        getattr(mod, name)()
        print(f"OK {name}")
    return len(names)


if __name__ == "__main__":
    _main()
