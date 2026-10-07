"""Tests de la journalisation enrichie (richlog.py) : neutralité dynamique,
estimateurs (_gini, _quantile), politique du Watcher, registre des morts,
aller-retour disque. Assertions Python simples — pas de pytest."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from m4.config import M4Config
from m4.contracts import LoanBook
from m4.entities import Population
from m4.bankruptcy import resolve_bankruptcies
from m4.metrics import (enable_rich_logging, write_run, load_dist_series,
                        load_watch, load_death_registry, load_births,
                        load_series)
from m4.richlog import DistLog, Watcher, _gini, _quantile
from m4.simulation import Simulation

CFG = M4Config(lam=5.0, T=120, seed=7)


def test_gini():
    """_gini : 0 pour l'égalité, valeurs de référence exactes, négatifs
    ramenés à 0."""
    assert _gini([3.0, 3.0, 3.0, 3.0]) == 0.0
    # deux entités {0, 1} : G = 1/2
    assert abs(_gini([0.0, 1.0]) - 0.5) < 1e-12
    # {1, 3} : G = 2*(1*1+2*3)/(2*4) - 3/2 = 0.25
    assert abs(_gini([3.0, 1.0]) - 0.25) < 1e-12
    # les négatifs comptent comme 0 : {-5, 1} == {0, 1}
    assert abs(_gini([-5.0, 1.0]) - 0.5) < 1e-12
    assert _gini([]) == 0.0 and _gini([2.0]) == 0.0


def test_quantile():
    """_quantile : interpolation linéaire sur liste triée."""
    v = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert _quantile(v, 0.0) == 1.0
    assert _quantile(v, 1.0) == 5.0
    assert _quantile(v, 0.5) == 3.0
    assert abs(_quantile(v, 0.25) - 2.0) < 1e-12
    assert abs(_quantile([1.0, 2.0], 0.5) - 1.5) < 1e-12
    assert _quantile([7.0], 0.9) == 7.0


def test_richlog_dynamics_unchanged():
    """CRITIQUE : la journalisation enrichie ne change pas la trajectoire —
    séries et avalanches bit-identiques avec et sans."""
    sim_a = Simulation(CFG)
    sim_a.run()
    sim_b = Simulation(CFG)
    enable_rich_logging(sim_b)
    sim_b.run()
    assert sim_a.series == sim_b.series
    assert sim_a.avalanche_log == sim_b.avalanche_log
    assert sim_b.dist_log.rows and sim_b.death_registry


def test_dist_log_coherence():
    """dist_series : une ligne par pas, n = pop de la série, quantiles
    ordonnés, Gini dans [0, 1]."""
    sim = Simulation(CFG)
    sim.dist_log = DistLog()
    sim.run()
    rows = sim.dist_log.rows
    assert len(rows) == len([s for s in sim.series if s["pop"] > 0])
    by_t = {s["t"]: s for s in sim.series}
    for r in rows:
        assert r["n"] == by_t[r["t"]]["pop"]
        assert r["prod_q10"] <= r["prod_med"] <= r["prod_q90"] <= r["prod_max"]
        assert r["r_min"] <= r["r_q10"] <= r["r_med"] <= r["r_q90"] <= r["r_max"]
        for k in ("gini_K", "gini_nw", "gini_income"):
            assert 0.0 <= r[k] <= 1.0


def test_watcher_policy():
    """Watcher : cap_first entités toutes suivies, p_watch=0 n'en ajoute pas,
    cap_total respecté, enregistrements uniquement pour des vivantes."""
    sim = Simulation(CFG)
    sim.watcher = Watcher(CFG.seed, cap_first=4, p_watch=0.0, cap_total=10)
    sim.run()
    assert sim.watcher.watched == {0, 1, 2, 3}
    ids_alive_rows = {(r["t"], r["id"]) for r in sim.watcher.rows}
    dead_t = {i: t for t, i in
              [(r["t"], r["id"]) for r in _registry_of(CFG)]}
    for t, i in ids_alive_rows:
        assert i in sim.watcher.watched
        if i in dead_t:
            assert t < dead_t[i]
    # p_watch=1 : toutes suivies jusqu'à cap_total
    sim2 = Simulation(CFG)
    sim2.watcher = Watcher(CFG.seed, cap_first=2, p_watch=1.0, cap_total=6)
    sim2.run()
    assert len(sim2.watcher.watched) == 6
    # enrôlement déterministe étalé : une naissance sur stride
    sim3 = Simulation(CFG)
    sim3.watcher = Watcher(CFG.seed, cap_first=2, cap_total=8,
                           expected_births=CFG.lam * CFG.T)
    sim3.run()
    w = sim3.watcher
    total_born = len(sim3.pop)
    assert w.stride == max(1, int(CFG.lam * CFG.T / 6))
    expected = {0, 1} | {i for i in range(2, total_born)
                         if (i - 2) % w.stride == 0}
    assert w.watched == set(sorted(expected)[:8])
    # les suivies couvrent bien la seconde moitié des naissances
    assert max(w.watched) > total_born // 2


def _registry_of(cfg):
    sim = Simulation(cfg)
    sim.log_death_registry = True
    sim.run()
    return sim.death_registry


def test_death_registry_cascade():
    """dead_info : bilan au moment de la mort dans une cascade construite
    a -> b (b créancière de a, insolvable après la perte)."""
    cfg = M4Config()
    pop = Population()
    book = LoanBook()
    a = pop.born(0.0, 0)   # K=0, dette 40 -> NW = -40 : racine insolvable
    b = pop.born(5.0, 0)   # K=5, créance 40 sur a, dette 20 envers c
    c = pop.born(1.0, 0)   # K=1, créance 20 sur b : survit à la perte
    book.add(b, a, 40.0, 0.05)
    book.add(c, b, 20.0, 0.05)
    dead, ledger = resolve_bankruptcies(pop, book, cfg)
    assert dead == [a, b] and pop.alive[c]
    ia = ledger["dead_info"][a]
    assert ia["K"] == 0.0 and ia["debts"] == 40.0 and ia["nw"] == -40.0
    ib = ledger["dead_info"][b]
    # bilan de b AU MOMENT de sa mort : la créance sur a est déjà perdue
    assert ib["claims"] == 0.0 and ib["debts"] == 20.0
    assert ib["K"] == 5.0 and ib["nw"] == -15.0


def test_death_registry_run():
    """Registre des morts sur un run : volume = morts des séries, âges
    cohérents, causes valides. NB : nw est le bilan AU MOMENT de la mort,
    pas au diagnostic — une racine insolvency peut remonter à nw >= 0 si une
    morte antérieure de la même itération annule d'abord sa dette (cancel)."""
    sim = Simulation(CFG)
    sim.log_death_registry = True
    sim.run()
    reg = sim.death_registry
    assert reg
    assert len(reg) == sum(s["deaths"] for s in sim.series)
    causes = {"liquidity", "insolvency", "both", "cascade"}
    for r in reg:
        assert r["cause"] in causes
        assert 0 <= r["age"] <= r["t"]
        assert r["death_iter"] >= 1
        if r["cause"] == "cascade":
            assert r["death_iter"] >= 2


def test_write_load_roundtrip():
    """write_run avec journalisation enrichie : les 4 artefacts existent et
    les loaders les relisent avec les bons volumes."""
    sim = Simulation(CFG)
    enable_rich_logging(sim)
    with tempfile.TemporaryDirectory() as tmp:
        write_run(tmp, "r0", sim)
        run_dir = Path(tmp) / "r0"
        dist = load_dist_series(run_dir)
        watch = load_watch(run_dir)
        reg = load_death_registry(run_dir)
        births = load_births(run_dir)
        assert len(dist) == len(sim.dist_log.rows)
        assert len(watch) == len(sim.watcher.rows)
        assert len(reg) == len(sim.death_registry)
        assert len(births) == len(sim.pop)
        assert len(load_series(run_dir)) == len(sim.series)
        # cohérence morts/naissances : chaque morte du registre est née avant
        birth_by_id = {b["id"]: b for b in births}
        for r in reg:
            b = birth_by_id[r["id"]]
            assert b["alive_final"] == 0
            assert r["t"] - r["age"] == b["birth"]


if __name__ == "__main__":
    for name in sorted(n for n in dir() if n.startswith("test_")):
        globals()[name]()
        print(f"OK {name}")
