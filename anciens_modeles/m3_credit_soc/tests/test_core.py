"""Tests des mécaniques individuelles M3 : naissance, production/partage,
chocs (i.i.d., macro, sectoriel), dépréciation/consommation, nominal, kill.
Assertions Python simples — pas de pytest."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import math

import numpy as np

from m3.bankruptcy import net_worth
from m3.config import M3Config
from m3.contracts import LoanBook
from m3.entities import Population
from m3.production import (apply_shock, apply_production,
                           apply_depreciation_consumption)


def test_birth():
    """Naissance : L0, K0, dette d0 implicite (NW = L0+K0-d0), pas de contrat."""
    cfg = M3Config()
    pop = Population()
    book = LoanBook()
    i = pop.born(cfg.L0, cfg.K0, t=3)
    assert pop.L[i] == cfg.L0
    assert pop.K[i] == cfg.K0
    assert pop.alive[i] is True
    assert pop.birth[i] == 3
    assert pop.n_alive == 1
    assert pop.prod[i] == 0.0 and pop.annuity[i] == 0.0
    assert not pop.defaulted[i]
    # dette d'amorçage implicite : NW = L0 + K0 - d0, aucun contrat au carnet
    assert net_worth(pop, book, cfg, i) == cfg.L0 + cfg.K0 - cfg.d0
    assert net_worth(pop, book, cfg, i) == cfg.eps0
    assert len(book) == 0
    assert book.claims.get(i, 0.0) == 0.0 and book.debts.get(i, 0.0) == 0.0


def test_production_sharing():
    """apply_production : K += s*alpha*sqrt(K_avant), L += (1-s)*alpha*sqrt(K_avant)."""
    cfg = M3Config()  # s = 0.75, alpha = 1.0
    pop = Population()
    pop.born(2.0, 16.0, 0)   # L=2, K=16 -> P = 4
    pop.born(1.0, 0.0, 0)    # K=0 -> P = 0
    total = apply_production(pop, cfg, [0, 1])
    p0 = cfg.alpha * math.sqrt(16.0)
    assert pop.prod[0] == p0
    assert pop.K[0] == 16.0 + cfg.s * p0
    assert pop.L[0] == 2.0 + (1.0 - cfg.s) * p0
    assert pop.prod[1] == 0.0 and pop.K[1] == 0.0 and pop.L[1] == 1.0
    assert total == p0


def test_shock_no_drift_iid():
    """Choc i.i.d. baseline : sur 20000 entités, E[exp(eta)] dans [0.98, 1.02]."""
    cfg = M3Config()  # rho_macro = rho_sector = 0
    rng = np.random.default_rng(42)
    pop = Population()
    n = 20000
    for _ in range(n):
        pop.born(0.0, 1.0, 0)  # K = 1 : K après choc = exp(eta)
    alive = list(range(n))
    apply_shock(pop, cfg, rng, alive)
    mean_factor = sum(pop.K) / n
    assert 0.98 <= mean_factor <= 1.02, mean_factor


def test_shock_no_drift_macro():
    """Variante macro (rho_macro=0.5) : moyenne de exp(eta) sur 200 pas d'une
    entité dans [0.98, 1.02] (seed fixe : test déterministe)."""
    cfg = M3Config(shock_rho_macro=0.5)
    rng = np.random.default_rng(18)
    pop = Population()
    pop.born(0.0, 1.0, 0)
    factors = []
    for _ in range(200):
        pop.K[0] = 1.0        # facteur du pas = K après choc
        apply_shock(pop, cfg, rng, [0])
        factors.append(pop.K[0])
    mean_factor = sum(factors) / len(factors)
    assert 0.98 <= mean_factor <= 1.02, mean_factor


def test_shock_sector_common_component():
    """Variante sectorielle : var idio ~0 (rho_macro=0, rho_sector=1.0) ->
    deux entités du même secteur reçoivent exactement le même facteur."""
    cfg = M3Config(shock_rho_macro=0.0, shock_rho_sector=1.0)
    rng = np.random.default_rng(3)
    pop = Population()
    pop.born(0.0, 1.0, 0, sector=0)
    pop.born(0.0, 2.0, 0, sector=0)
    pop.born(0.0, 3.0, 0, sector=1)
    apply_shock(pop, cfg, rng, [0, 1, 2])
    f0 = pop.K[0] / 1.0
    f1 = pop.K[1] / 2.0
    f2 = pop.K[2] / 3.0
    assert abs(f0 - f1) < 1e-12, (f0, f1)      # même composante sectorielle
    assert abs(f0 - f2) > 1e-6, (f0, f2)       # secteurs différents


def test_depreciation_consumption_exact():
    """K <- (1-delta)K exactement, L <- (1-c)L exactement ; clamp sous w_clamp."""
    cfg = M3Config()
    pop = Population()
    pop.born(50.0, 100.0, 0)
    pop.born(1e-13, 1e-13, 0)  # sous w_clamp après facteur -> clamp à 0
    depreciated, consumed = apply_depreciation_consumption(pop, cfg, [0, 1])
    assert pop.K[0] == 100.0 * (1.0 - cfg.delta)
    assert pop.L[0] == 50.0 * (1.0 - cfg.c)
    assert pop.K[1] == 0.0 and pop.L[1] == 0.0
    assert abs(depreciated - (100.0 * cfg.delta + 1e-13 * cfg.delta)) < 1e-15
    assert abs(consumed - (50.0 * cfg.c + 1e-13 * cfg.c)) < 1e-15


def test_nominal_not_depreciated():
    """claims/debts/due inchangés par apply_depreciation_consumption."""
    cfg = M3Config()
    pop = Population()
    pop.born(10.0, 20.0, 0)
    pop.born(10.0, 20.0, 0)
    book = LoanBook()
    book.add(0, 1, 10.0, 0.05)
    apply_depreciation_consumption(pop, cfg, [0, 1])
    assert book.claims[0] == 10.0
    assert book.debts[1] == 10.0
    assert book.due[1] == 10.0 * 0.05
    assert book.loans[0][2] == 10.0 and book.loans[0][3] == 0.05


def test_kill():
    """kill : annuity remise à 0, n_alive décrémenté, L=K=0."""
    pop = Population()
    i = pop.born(5.0, 25.0, 0)
    j = pop.born(5.0, 25.0, 0)
    pop.annuity[i] = 1.5
    assert pop.n_alive == 2
    pop.kill(i)
    assert pop.alive[i] is False
    assert pop.annuity[i] == 0.0
    assert pop.L[i] == 0.0 and pop.K[i] == 0.0
    assert pop.n_alive == 1
    assert pop.alive[j] and pop.alive_ids() == [j]


def _main():
    mod = sys.modules[__name__]
    names = sorted(n for n in dir(mod) if n.startswith("test_"))
    for name in names:
        getattr(mod, name)()
        print(f"OK {name}")
    return len(names)


if __name__ == "__main__":
    _main()
