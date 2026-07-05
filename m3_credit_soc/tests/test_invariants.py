"""Tests des invariants I1, I4, I7, I8, I9 et de la réduction R1 vers M2,
sur runs courts à seed fixe. Assertions Python simples — pas de pytest."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from m3.config import M3Config
from m3.simulation import Simulation

M2_SRC = "/home/anatole/jupyter/m2_fable/src"


def test_I1_nonnegative():
    """I1 : aucun L < 0 ni K < 0 à la fin d'un run baseline."""
    sim = Simulation(M3Config(seed=3, T=250))
    sim.run()
    for i in range(len(sim.pop)):
        assert sim.pop.L[i] >= 0.0, (i, sim.pop.L[i])
        assert sim.pop.K[i] >= 0.0, (i, sim.pop.K[i])


def test_I4_global_balance():
    """I4 : bilan global par pas — pour chaque ligne de series,
    Delta(L_tot+K_tot) == births*w0 + shock_gain + prod_tot - depreciated
    - consumed - destroyed + injected (tolérance relative 1e-6)."""
    cfg = M3Config(seed=7, T=200)
    sim = Simulation(cfg)
    sim.run()
    assert len(sim.series) == 200
    prev = 0.0  # N(0) = 0 : richesse réelle initiale nulle
    for s in sim.series:
        total = s["L_tot"] + s["K_tot"]
        lhs = total - prev
        rhs = (s["births"] * cfg.w0 + s["shock_gain"] + s["prod_tot"]
               - s["depreciated"] - s["consumed"] - s["destroyed"]
               + s["injected"])
        tol = 1e-6 * max(1.0, abs(total))
        assert abs(lhs - rhs) <= tol, (s["t"], lhs, rhs, lhs - rhs)
        prev = total


def test_I7_seed_reproducibility():
    """I7 : deux Simulation même seed -> séries identiques champ à champ."""
    sim1 = Simulation(M3Config(seed=5, T=150))
    sim2 = Simulation(M3Config(seed=5, T=150))
    sim1.run()
    sim2.run()
    assert len(sim1.series) == len(sim2.series)
    for s1, s2 in zip(sim1.series, sim2.series):
        assert s1.keys() == s2.keys()
        for key in s1:
            assert s1[key] == s2[key], (s1["t"], key, s1[key], s2[key])


def test_I8_snapshots_no_effect():
    """I8 STRICT : run avec snapshots vs run sans -> séries identiques bit à
    bit. (Bug historique corrigé : snapshot() insérait des clés vides dans
    les defaultdict du carnet via [], changeant l'ordre d'itération du
    service des intérêts ; accès en .get() désormais.)"""
    sim1 = Simulation(M3Config(seed=9, T=150))
    sim2 = Simulation(M3Config(seed=9, T=150))
    sim1.run()
    grabbed = []
    sim2.run(snapshot_times=(50, 100, 140),
             on_snapshot=lambda t, snap, net: grabbed.append(t))
    assert grabbed == [50, 100, 140]
    assert len(sim1.series) == len(sim2.series)
    for s1, s2 in zip(sim1.series, sim2.series):
        for key in s1:
            assert s1[key] == s2[key], (s1["t"], key, s1[key], s2[key])


def test_R1_reduction_to_M2():
    """R1 : M3(L0=0, K0=30, s=1, c=0, credit=False) == m2_fable
    M2(credit=False) à seed égale — K == w exactement, mêmes vivantes,
    mêmes morts par pas."""
    if M2_SRC not in sys.path:
        sys.path.insert(0, M2_SRC)
    from m2.config import M2Config
    from m2.simulation import Simulation as M2Simulation

    cfg3 = M3Config(L0=0.0, K0=30.0, s=1.0, c=0.0, credit=False,
                    seed=11, T=200)
    cfg2 = M2Config(credit=False, seed=11, T=200)
    sim3 = Simulation(cfg3)
    sim2 = M2Simulation(cfg2)
    sim3.run()
    sim2.run()
    assert len(sim3.pop) == len(sim2.pop), "mêmes naissances"
    max_diff = max((abs(sim3.pop.K[i] - sim2.pop.w[i])
                    for i in range(len(sim3.pop))), default=0.0)
    assert max_diff == 0.0, max_diff       # identité bit à bit K == w
    assert sim3.pop.alive == sim2.pop.alive
    deaths3 = [s["deaths"] for s in sim3.series]
    deaths2 = [s["deaths"] for s in sim2.series]
    assert deaths3 == deaths2
    births3 = [s["births"] for s in sim3.series]
    births2 = [s["births"] for s in sim2.series]
    assert births3 == births2
    # la liquidité doit rester identiquement nulle dans la réduction
    assert all(x == 0.0 for x in sim3.pop.L)


def test_I9_runs_clean():
    """I9 : le run ne lève pas RuntimeError (cascade avec point fixe)."""
    sim = Simulation(M3Config(seed=13, T=300))
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
