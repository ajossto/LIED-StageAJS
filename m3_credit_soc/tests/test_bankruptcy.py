"""Tests des faillites, cascades et avalanches causales (bankruptcy.py) et du
service des intérêts (phase 4 de Simulation.step).
Assertions Python simples — pas de pytest.

Configuration d'isolement des tests de service : lam=0 (pas de naissance),
sigma=0 (pas de choc), credit=False (pas de marché), s=1.0 (la production ne
touche pas L), c=0 (pas de consommation), d0=0 (pas d'insolvabilité par
plancher) ; les entités de service ont K=0 (production nulle)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from m3.bankruptcy import net_worth, resolve_bankruptcies
from m3.config import M3Config
from m3.contracts import LoanBook
from m3.entities import Population
from m3.simulation import Simulation


def _cfg(**kw):
    base = dict(lam=0.0, sigma=0.0, credit=False, s=1.0, c=0.0, d0=0.0)
    base.update(kw)
    return M3Config(**base)


def test_full_service():
    """Service complet via Simulation.step : emprunteuse avec L suffisant paie
    r*q, prêteuse reçoit dans L, int_in/int_out corrects, somme L conservée."""
    sim = Simulation(_cfg())
    lender = sim.pop.born(50.0, 0.0, 0)
    borrower = sim.pop.born(10.0, 0.0, 0)
    sim.book.add(lender, borrower, 5.0, 0.1)   # due = 0.5
    sum_before = sum(sim.pop.L)
    sim.step()
    assert sim.pop.L[borrower] == 10.0 - 0.5
    assert sim.pop.L[lender] == 50.0 + 0.5
    assert sim.pop.int_in[lender] == 0.5
    assert sim.pop.int_out[borrower] == 0.5
    assert sim.pop.defaulted[borrower] is False
    assert abs(sum(sim.pop.L) - sum_before) < 1e-12   # transfert conservatif
    s = sim.series[-1]
    assert s["interest_paid"] == 0.5
    assert s["deaths"] == 0 and s["defaults"] == 0


def test_partial_prorata():
    """Paiement partiel prorata : L insuffisant, deux contrats de taux
    différents -> chaque prêteuse reçoit ratio*r_j*q_j, defaulted=True."""
    sim = Simulation(_cfg())
    l1 = sim.pop.born(100.0, 0.0, 0)
    l2 = sim.pop.born(100.0, 0.0, 0)
    b = sim.pop.born(2.0, 0.0, 0)
    sim.book.add(l1, b, 10.0, 0.1)   # dû : 1.0
    sim.book.add(l2, b, 10.0, 0.3)   # dû : 3.0 -> total 4.0 > L_b = 2.0
    sim.step()
    ratio = 2.0 / 4.0
    assert sim.pop.int_in[l1] == ratio * 0.1 * 10.0   # 0.5
    assert sim.pop.int_in[l2] == ratio * 0.3 * 10.0   # 1.5
    assert sim.pop.int_out[b] == 2.0
    assert sim.pop.defaulted[b] is True
    s = sim.series[-1]
    assert s["defaults"] == 1
    # défaut de service -> faillite de b au même pas (NW = -20 : cause "both")
    assert s["deaths"] == 1 and not sim.pop.alive[b]
    assert s["roots_both"] == 1
    assert sim.pop.alive[l1] and sim.pop.alive[l2]
    assert sim.pop.L[l1] == 100.5 and sim.pop.L[l2] == 101.5


def test_liquidity_default_solvent():
    """Défaut de liquidité d'une entité SOLVABLE : NW > 0 mais L < due ->
    racine classée "liquidity"."""
    sim = Simulation(_cfg())
    lender = sim.pop.born(100.0, 0.0, 0)
    b = sim.pop.born(0.1, 100.0, 0)      # gros K : NW largement > 0
    sim.book.add(lender, b, 10.0, 0.05)  # due = 0.5 > L_b = 0.1
    sim.step()
    s = sim.series[-1]
    assert s["defaults"] == 1
    assert s["roots_liquidity"] == 1     # solvable mais illiquide
    assert s["roots_insolvency"] == 0 and s["roots_both"] == 0
    assert not sim.pop.alive[b] and s["deaths"] == 1
    # la prêteuse récupère le résidu en nature (seule créancière vivante)
    assert sim.pop.K[lender] > 0.0


def test_simple_failure_claim_loss():
    """Faillite simple : contrats de l'emprunteuse annulés, perte de créance
    chez la prêteuse, arête causale (i, lender, q), claim_losses correct."""
    cfg = _cfg()
    pop = Population()
    lender = pop.born(100.0, 0.0, 0)
    b = pop.born(0.0, 0.0, 0)
    book = LoanBook()
    book.add(lender, b, 10.0, 0.05)
    assert net_worth(pop, book, cfg, b) == -10.0
    dead, ledger = resolve_bankruptcies(pop, book, cfg)
    assert dead == [b]
    assert ledger["roots"] == {b: "insolvency"}
    assert ledger["loss_edges"] == [(b, lender, 10.0)]
    assert ledger["claim_losses"] == 10.0
    assert book.claims[lender] == 0.0        # créance perdue
    assert len(book) == 0                    # contrat annulé
    assert pop.alive[lender]
    assert len(ledger["avalanches"]) == 1
    assert ledger["avalanches"][0]["size"] == 1


def test_future_flow_removed():
    """Perte de flux futur : le service dû de l'emprunteuse morte disparaît
    du carnet ; celui des autres emprunteuses est intact."""
    cfg = _cfg()
    pop = Population()
    lender = pop.born(100.0, 0.0, 0)
    b_dead = pop.born(0.0, 0.0, 0)           # NW = -10 -> faillite
    b_ok = pop.born(50.0, 0.0, 0)
    book = LoanBook()
    book.add(lender, b_dead, 10.0, 0.05)
    book.add(lender, b_ok, 8.0, 0.1)
    resolve_bankruptcies(pop, book, cfg)
    assert not pop.alive[b_dead] and pop.alive[b_ok]
    assert book.due[b_dead] == 0.0
    assert book.due[b_ok] == 8.0 * 0.1
    assert abs(sum(book.due.values()) - 0.8) < 1e-12


def test_residual_prorata():
    """Résidu en nature : L_i réparti en L, K_i en K, au prorata des créances ;
    recovered correct."""
    cfg = _cfg()
    pop = Population()
    c1 = pop.born(100.0, 0.0, 0)
    c2 = pop.born(100.0, 0.0, 0)
    b = pop.born(6.0, 9.0, 0)                # NW = 15 - 40 = -25 -> faillite
    book = LoanBook()
    book.add(c1, b, 10.0, 0.05)
    book.add(c2, b, 30.0, 0.05)
    dead, ledger = resolve_bankruptcies(pop, book, cfg)
    assert dead == [b]
    assert pop.L[c1] == 100.0 + 6.0 * 0.25 and pop.K[c1] == 9.0 * 0.25
    assert pop.L[c2] == 100.0 + 6.0 * 0.75 and pop.K[c2] == 9.0 * 0.75
    assert ledger["recovered"] == 15.0
    assert ledger["destroyed"] == 0.0
    assert sorted(ledger["loss_edges"]) == [(b, c1, 10.0), (b, c2, 30.0)]


def test_residual_destroy():
    """fail_residual="destroy" : le résidu est détruit, pas redistribué."""
    cfg = _cfg(fail_residual="destroy")
    pop = Population()
    c1 = pop.born(100.0, 0.0, 0)
    b = pop.born(6.0, 9.0, 0)                # NW = 15 - 40 = -25
    book = LoanBook()
    book.add(c1, b, 40.0, 0.05)
    dead, ledger = resolve_bankruptcies(pop, book, cfg)
    assert dead == [b]
    assert pop.L[c1] == 100.0 and pop.K[c1] == 0.0
    assert ledger["destroyed"] == 15.0
    assert ledger["recovered"] == 0.0


def test_cascade_two_levels():
    """Cascade : A doit à B ; B, proche de NW=0, tient par sa créance sur A.
    Faillite de A entraîne B -> une seule avalanche size=2, depth=2, n_roots=1."""
    cfg = _cfg()
    pop = Population()
    a = pop.born(0.0, 0.0, 0)                # NW = -50 : racine insolvable
    b = pop.born(10.0, 0.0, 0)               # NW = 10 + 50 - 40 = 20 avant
    c = pop.born(100.0, 0.0, 0)              # survivante
    book = LoanBook()
    book.add(b, a, 50.0, 0.05)               # B prête 50 à A
    book.add(c, b, 40.0, 0.05)               # C prête 40 à B
    dead, ledger = resolve_bankruptcies(pop, book, cfg)
    assert set(dead) == {a, b}
    assert ledger["roots"] == {a: "insolvency"}
    assert ledger["death_iter"] == {a: 1, b: 2}
    assert pop.alive[c]
    avs = ledger["avalanches"]
    assert len(avs) == 1
    av = avs[0]
    assert av["size"] == 2
    assert av["depth"] == 2
    assert av["n_roots"] == 1
    assert av["members"] == sorted([a, b])
    assert av["causes"] == ["insolvency"]
    # C, seule créancière vivante de B, récupère le résidu L de B
    assert pop.L[c] == 100.0 + 10.0


def test_independent_roots_not_merged():
    """Racines indépendantes NON agrégées : deux faillites sans lien au même
    pas -> deux avalanches de taille 1."""
    cfg = _cfg(d0=28.0)                      # insolvabilité par plancher d0
    pop = Population()
    x = pop.born(0.0, 0.0, 0)                # NW = -28
    y = pop.born(0.0, 0.0, 0)                # NW = -28, aucun lien avec x
    pop.born(100.0, 100.0, 0)
    book = LoanBook()
    dead, ledger = resolve_bankruptcies(pop, book, cfg)
    assert set(dead) == {x, y}
    avs = ledger["avalanches"]
    assert len(avs) == 2
    for av in avs:
        assert av["size"] == 1 and av["depth"] == 1 and av["n_roots"] == 1
        assert av["causes"] == ["insolvency"]


def test_claim_loss_compensated():
    """Ablation D : prêteuse indemnisée de q en L, injected == q, PAS d'arête
    causale."""
    cfg = _cfg(claim_loss="compensated")
    pop = Population()
    lender = pop.born(100.0, 0.0, 0)
    b = pop.born(0.0, 0.0, 0)                # NW = -10
    book = LoanBook()
    book.add(lender, b, 10.0, 0.05)
    dead, ledger = resolve_bankruptcies(pop, book, cfg)
    assert dead == [b]
    assert pop.L[lender] == 110.0            # indemnisation du principal
    assert ledger["injected"] == 10.0
    assert ledger["claim_losses"] == 0.0
    assert ledger["loss_edges"] == []
    assert len(ledger["avalanches"]) == 1 and ledger["avalanches"][0]["size"] == 1


def test_flow_loss_annuity():
    """Ablation E : après faillite de l'emprunteuse, annuity[lender] == r*q ;
    au pas suivant L_lender += annuity (via step) ; éteinte à la mort."""
    cfg = _cfg(flow_loss="annuity")
    sim = Simulation(cfg)
    lender = sim.pop.born(100.0, 0.0, 0)
    b = sim.pop.born(0.0, 0.0, 0)            # NW = -10
    sim.book.add(lender, b, 10.0, 0.05)
    dead, ledger = resolve_bankruptcies(sim.pop, sim.book, cfg)
    assert dead == [b]
    assert sim.pop.annuity[lender] == 0.5    # rente fantôme r*q
    assert ledger["claim_losses"] == 10.0    # la perte de stock demeure
    assert ledger["loss_edges"] == [(b, lender, 10.0)]
    sim.step()                               # versement de la rente
    assert sim.pop.L[lender] == 100.5
    assert sim.pop.int_in[lender] == 0.5
    assert sim.series[-1]["injected"] == 0.5
    assert sim.pop.annuity[lender] == 0.5    # la rente persiste
    sim.pop.kill(lender)                     # mort de la prêteuse
    assert sim.pop.annuity[lender] == 0.0    # rente éteinte


def test_fail_lender_loans_transfer():
    """fail_lender_loans="transfer" : contrats prêtés par la faillie transférés
    aux créancières au prorata de leurs créances."""
    cfg = _cfg(fail_lender_loans="transfer")
    pop = Population()
    c1 = pop.born(100.0, 0.0, 0)
    c2 = pop.born(100.0, 0.0, 0)
    d = pop.born(100.0, 0.0, 0)              # emprunteuse de la faillie
    f = pop.born(0.0, 0.0, 0)                # NW = 20 - 40 = -20
    book = LoanBook()
    book.add(c1, f, 10.0, 0.1)
    book.add(c2, f, 30.0, 0.1)
    book.add(f, d, 20.0, 0.08)
    dead, ledger = resolve_bankruptcies(pop, book, cfg)
    assert dead == [f]
    assert pop.alive[d] and pop.alive[c1] and pop.alive[c2]
    # transfert au prorata 10:30 -> parts 5 et 15, taux d'origine conservé
    assert len(book) == 2
    recs = sorted(book.loans.values())
    assert recs[0] == [c1, d, 5.0, 0.08]
    assert recs[1] == [c2, d, 15.0, 0.08]
    assert book.debts[d] == 20.0             # dette de d inchangée au total
    assert abs(book.due[d] - 20.0 * 0.08) < 1e-12
    assert book.check_consistency(pop.alive) == []


def test_fail_lender_loans_cancel():
    """fail_lender_loans="cancel" : contrats prêtés par la faillie annulés."""
    cfg = _cfg(fail_lender_loans="cancel")
    pop = Population()
    c1 = pop.born(100.0, 0.0, 0)
    d = pop.born(100.0, 0.0, 0)
    f = pop.born(0.0, 0.0, 0)                # NW = 20 - 10 -> -10 + 20 = ...
    book = LoanBook()
    book.add(c1, f, 40.0, 0.1)               # NW_f = 20 - 40 = -20
    book.add(f, d, 20.0, 0.08)
    dead, ledger = resolve_bankruptcies(pop, book, cfg)
    assert dead == [f]
    assert len(book) == 0                    # tout annulé
    assert book.debts[d] == 0.0              # gain pour l'emprunteuse
    assert book.due[d] == 0.0
    assert book.check_consistency(pop.alive) == []


def test_no_orphan_contracts():
    """Pas de contrat orphelin après cascade : check_consistency vide après
    un run court avec faillites (baseline)."""
    cfg = M3Config(seed=2, T=150)
    sim = Simulation(cfg)
    sim.run()
    total_deaths = sum(s["deaths"] for s in sim.series)
    assert total_deaths > 0, "le run doit contenir des faillites"
    assert sim.book.check_consistency(sim.pop.alive) == []
    for lender, borrower, q, r in sim.book.loans.values():
        assert sim.pop.alive[lender] and sim.pop.alive[borrower]
        assert lender != borrower and q > 0.0


def _main():
    mod = sys.modules[__name__]
    names = sorted(n for n in dir(mod) if n.startswith("test_"))
    for name in names:
        getattr(mod, name)()
        print(f"OK {name}")
    return len(names)


if __name__ == "__main__":
    _main()
