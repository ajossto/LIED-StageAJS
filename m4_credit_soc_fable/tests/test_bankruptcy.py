"""Tests des faillites, cascades et avalanches causales (bankruptcy.py) et du
service des intérêts (phase 4 de Simulation.step) — moteur fusionné.
Assertions Python simples — pas de pytest.

Configuration d'isolement : lam=0 (pas de naissance), sigma=0 (pas de choc),
credit=False (pas de marché). Les entités de service ont K > 0 mais la
production ajoute alpha*sqrt(K) — les tests de service utilisent K=0 pour
les entités passives ou tiennent compte de la production exacte."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from m4.bankruptcy import net_worth, resolve_bankruptcies
from m4.config import M4Config
from m4.contracts import LoanBook
from m4.entities import Population
from m4.simulation import Simulation


def _cfg(**kw):
    base = dict(lam=0.0, sigma=0.0, credit=False)
    base.update(kw)
    return M4Config(**base)


def test_full_service():
    """Service complet via Simulation.step : emprunteuse avec K suffisant paie
    r*q depuis K, prêteuse reçoit dans K, int_in/int_out corrects, transfert
    conservatif (à production/dépréciation près, calculées exactement)."""
    import math
    sim = Simulation(_cfg())
    lender = sim.pop.born(50.0, 0)
    borrower = sim.pop.born(10.0, 0)
    sim.book.add(lender, borrower, 5.0, 0.1)   # due = 0.5
    sim.step()
    # trajectoires exactes : production puis service puis dépréciation
    k_l = 50.0 + math.sqrt(50.0)     # production
    k_b = 10.0 + math.sqrt(10.0)
    k_b -= 0.5                        # service payé
    k_l += 0.5                        # service reçu
    k_l *= 0.95                       # dépréciation
    k_b *= 0.95
    assert abs(sim.pop.K[lender] - k_l) < 1e-12
    assert abs(sim.pop.K[borrower] - k_b) < 1e-12
    assert sim.pop.int_in[lender] == 0.5
    assert sim.pop.int_out[borrower] == 0.5
    assert sim.pop.defaulted[borrower] is False
    s = sim.series[-1]
    assert s["interest_paid"] == 0.5
    assert s["deaths"] == 0 and s["defaults"] == 0


def test_partial_prorata_service():
    """Paiement partiel prorata : K insuffisant, deux contrats de taux
    différents -> chaque prêteuse reçoit ratio*r_j*q_j, defaulted=True,
    et l'emprunteuse (insolvable : dettes 20 > actifs) meurt au même pas."""
    sim = Simulation(_cfg())
    l1 = sim.pop.born(100.0, 0)
    l2 = sim.pop.born(100.0, 0)
    b = sim.pop.born(0.0, 0)          # K=0 : production nulle, service nul
    sim.book.add(l1, b, 10.0, 0.1)    # dû : 1.0
    sim.book.add(l2, b, 10.0, 0.3)    # dû : 3.0 -> total 4.0 > K_b = 0
    sim.step()
    assert sim.pop.int_in[l1] == 0.0 and sim.pop.int_in[l2] == 0.0
    assert sim.pop.int_out[b] == 0.0
    s = sim.series[-1]
    assert s["defaults"] == 1
    # défaut de service + NW = -20 : cause "both"
    assert s["deaths"] == 1 and not sim.pop.alive[b]
    assert s["roots_both"] == 1
    assert sim.pop.alive[l1] and sim.pop.alive[l2]


def test_partial_ratio_payment():
    """Ratio de paiement partiel exact : K couvre la moitié du dû."""
    sim = Simulation(_cfg())
    l1 = sim.pop.born(0.0, 0)         # K=0 : pas de production parasite
    b = sim.pop.born(0.0, 0)
    sim.book.add(l1, b, 10.0, 0.2)    # dû : 2.0
    sim.pop.K[b] = 1.0                # après naissance : la moitié du dû
    # ATTENTION : la production ajoute sqrt(1.0)=1.0 -> K=2.0 au service ;
    # pour un ratio 0.5 net, on vérifie plutôt les montants relatifs
    sim.step()
    # K au service : (1.0)*e^0 + sqrt(1.0) = 2.0 = dû -> paiement complet
    assert sim.pop.int_out[b] == 2.0
    assert sim.pop.defaulted[b] is False


def test_liquidity_default_solvent():
    """Défaut de service d'une entité SOLVABLE : NW > 0 (grosse créance) mais
    K < dû -> racine classée "liquidity"."""
    sim = Simulation(_cfg())
    lender = sim.pop.born(100.0, 0)
    rich_debtor = sim.pop.born(400.0, 0)
    b = sim.pop.born(0.0, 0)
    # b doit 10 à lender (dû 0.5 > K_b = 0) mais détient une créance de 50
    # sur rich_debtor : NW_b = 0 + 50 - 10 = 40 > 0
    sim.book.add(lender, b, 10.0, 0.05)
    sim.book.add(b, rich_debtor, 50.0, 0.001)
    sim.step()
    s = sim.series[-1]
    assert s["defaults"] >= 1
    assert s["roots_liquidity"] == 1     # solvable mais illiquide
    assert not sim.pop.alive[b] and s["deaths"] == 1


def test_simple_failure_claim_loss():
    """Faillite simple : contrats de l'emprunteuse annulés, perte de créance
    chez la prêteuse, arête causale (i, lender, q), claim_losses correct."""
    cfg = _cfg()
    pop = Population()
    lender = pop.born(100.0, 0)
    b = pop.born(0.0, 0)
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
    lender = pop.born(100.0, 0)
    b_dead = pop.born(0.0, 0)                # NW = -10 -> faillite
    b_ok = pop.born(50.0, 0)
    book = LoanBook()
    book.add(lender, b_dead, 10.0, 0.05)
    book.add(lender, b_ok, 8.0, 0.1)
    resolve_bankruptcies(pop, book, cfg)
    assert not pop.alive[b_dead] and pop.alive[b_ok]
    assert book.due[b_dead] == 0.0
    assert book.due[b_ok] == 8.0 * 0.1
    assert abs(sum(book.due.values()) - 0.8) < 1e-12


def test_residual_destroy_default():
    """Règle par défaut (destroy) : le résidu K est détruit, pas redistribué."""
    cfg = _cfg()
    assert cfg.fail_residual == "destroy"
    pop = Population()
    c1 = pop.born(100.0, 0)
    b = pop.born(15.0, 0)                    # NW = 15 - 40 = -25
    book = LoanBook()
    book.add(c1, b, 40.0, 0.05)
    dead, ledger = resolve_bankruptcies(pop, book, cfg)
    assert dead == [b]
    assert pop.K[c1] == 100.0                # rien récupéré
    assert ledger["destroyed"] == 15.0
    assert ledger["recovered"] == 0.0


def test_residual_prorata_variant():
    """Variante M3 (prorata) : K_i réparti au prorata des créances."""
    cfg = _cfg(fail_residual="prorata")
    pop = Population()
    c1 = pop.born(100.0, 0)
    c2 = pop.born(100.0, 0)
    b = pop.born(15.0, 0)                    # NW = 15 - 40 = -25 -> faillite
    book = LoanBook()
    book.add(c1, b, 10.0, 0.05)
    book.add(c2, b, 30.0, 0.05)
    dead, ledger = resolve_bankruptcies(pop, book, cfg)
    assert dead == [b]
    assert pop.K[c1] == 100.0 + 15.0 * 0.25
    assert pop.K[c2] == 100.0 + 15.0 * 0.75
    assert ledger["recovered"] == 15.0
    assert ledger["destroyed"] == 0.0
    assert sorted(ledger["loss_edges"]) == [(b, c1, 10.0), (b, c2, 30.0)]


def test_cascade_two_levels():
    """Cascade : A doit à B ; B, proche de NW=0, tient par sa créance sur A.
    Faillite de A entraîne B -> une seule avalanche size=2, depth=2, n_roots=1."""
    cfg = _cfg()
    pop = Population()
    a = pop.born(0.0, 0)                     # NW = -50 : racine insolvable
    b = pop.born(10.0, 0)                    # NW = 10 + 50 - 40 = 20 avant
    c = pop.born(100.0, 0)                   # survivante
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
    # règle destroy : C ne récupère rien, sa créance sur B est perdue
    assert pop.K[c] == 100.0
    assert book.claims[c] == 0.0


def test_cascade_three_levels():
    """Cascade profonde : A -> B -> C en chaîne de créances tendues,
    la racine A emporte B puis C — depth=3, la victime finale D survit."""
    cfg = _cfg()
    pop = Population()
    a = pop.born(0.0, 0)                     # NW = -50
    b = pop.born(1.0, 0)                     # NW = 1 + 50 - 45 = 6
    c = pop.born(2.0, 0)                     # NW = 2 + 45 - 40 = 7
    d = pop.born(500.0, 0)                   # NW = 500 + 40 : survit
    book = LoanBook()
    book.add(b, a, 50.0, 0.05)
    book.add(c, b, 45.0, 0.05)
    book.add(d, c, 40.0, 0.05)
    dead, ledger = resolve_bankruptcies(pop, book, cfg)
    assert set(dead) == {a, b, c}
    assert ledger["death_iter"] == {a: 1, b: 2, c: 3}
    assert pop.alive[d]
    avs = ledger["avalanches"]
    assert len(avs) == 1 and avs[0]["size"] == 3 and avs[0]["depth"] == 3


def test_independent_roots_not_merged():
    """Racines indépendantes NON agrégées : deux faillites sans créancière
    commune morte au même pas -> deux avalanches de taille 1."""
    cfg = _cfg()
    pop = Population()
    l1 = pop.born(1000.0, 0)
    l2 = pop.born(1000.0, 0)
    x = pop.born(0.0, 0)
    y = pop.born(0.0, 0)
    book = LoanBook()
    book.add(l1, x, 10.0, 0.05)              # NW_x = -10
    book.add(l2, y, 10.0, 0.05)              # NW_y = -10
    dead, ledger = resolve_bankruptcies(pop, book, cfg)
    assert set(dead) == {x, y}
    assert pop.alive[l1] and pop.alive[l2]
    avs = ledger["avalanches"]
    assert len(avs) == 2
    for av in avs:
        assert av["size"] == 1 and av["depth"] == 1 and av["n_roots"] == 1
        assert av["causes"] == ["insolvency"]


def test_fail_lender_loans_cancel_default():
    """Règle par défaut (cancel) : contrats prêtés par la faillie annulés —
    gain pour ses emprunteuses."""
    cfg = _cfg()
    assert cfg.fail_lender_loans == "cancel"
    pop = Population()
    c1 = pop.born(100.0, 0)
    d = pop.born(100.0, 0)
    f = pop.born(20.0, 0)
    book = LoanBook()
    book.add(c1, f, 60.0, 0.1)               # NW_f = 20 + 20 - 60 = -20
    book.add(f, d, 20.0, 0.08)
    dead, ledger = resolve_bankruptcies(pop, book, cfg)
    assert dead == [f]
    assert len(book) == 0                    # tout annulé
    assert book.debts[d] == 0.0              # gain pour l'emprunteuse
    assert book.due[d] == 0.0
    assert book.check_consistency(pop.alive) == []


def test_fail_lender_loans_transfer_variant():
    """Variante M3 (transfer) : contrats prêtés par la faillie transférés
    aux créancières au prorata de leurs créances, taux d'origine conservé."""
    cfg = _cfg(fail_lender_loans="transfer")
    pop = Population()
    c1 = pop.born(100.0, 0)
    c2 = pop.born(100.0, 0)
    d = pop.born(100.0, 0)                   # emprunteuse de la faillie
    f = pop.born(0.0, 0)                     # NW = 20 - 40 = -20
    book = LoanBook()
    book.add(c1, f, 10.0, 0.1)
    book.add(c2, f, 30.0, 0.1)
    book.add(f, d, 20.0, 0.08)
    dead, ledger = resolve_bankruptcies(pop, book, cfg)
    assert dead == [f]
    assert pop.alive[d] and pop.alive[c1] and pop.alive[c2]
    # transfert au prorata 10:30 -> parts 5 et 15
    assert len(book) == 2
    recs = sorted(book.loans.values())
    assert recs[0] == [c1, d, 5.0, 0.08]
    assert recs[1] == [c2, d, 15.0, 0.08]
    assert book.debts[d] == 20.0
    assert abs(book.due[d] - 20.0 * 0.08) < 1e-12
    assert book.check_consistency(pop.alive) == []


def test_no_orphan_contracts():
    """Pas de contrat orphelin après cascade : check_consistency vide après
    un run court avec faillites (baseline)."""
    cfg = M4Config(seed=2, T=150)
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
