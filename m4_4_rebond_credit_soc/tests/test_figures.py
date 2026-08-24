"""Les figures ne mentent pas, et ne manquent pas.

Trois garde-fous, tous du même genre que ceux que ce programme s'impose
ailleurs : ce qui est publié doit être engendré, et ce qui est engendré doit
coïncider avec ce qui est écrit.

1. **Aucune figure manquante.** Chaque `\\figurine{...}` des deux rapports
   doit avoir un PDF dans `report/figures/`. Vingt-six inclusions entrent
   d'un coup ; une seule absente ferait échouer la compilation, et l'erreur
   de LaTeX est illisible.

2. **Aucune figure orpheline.** Une figure engendrée que personne n'inclut
   est du travail perdu — ou pire, une figure qu'on croit publiée.

3. **Aucune dérive entre figure et texte.** Les valeurs ANNOTÉES sur les
   figures sont déposées par `save()` dans `report/figures/manifest.json`.
   Chacune est confrontée à la macro correspondante de `report/numbers.tex`.
   C'est le pendant, pour les figures, de la règle « aucun nombre recopié à
   la main » : une figure qui affiche 93 quand le texte dit 98 est un défaut
   silencieux, et c'est exactement celui-ci qui a été trouvé sur la part
   d'effet annulée par la compensation de dotation.

Aucun run n'est lancé : le test lit des fichiers déjà écrits.

    python3 tests/test_figures.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

REPORTS = (ROOT / "report" / "rapport_final.tex",
           ROOT / "report" / "conception_m4_4.tex")
FIGURES = ROOT / "report" / "figures"
NUMBERS = ROOT / "report" / "numbers.tex"

#: Figure annotée -> macro de `numbers.tex` qui doit dire la même chose.
#: La tolérance est celle de l'ARRONDI de la macro : `make_numbers` écrit un
#: nombre déjà mis en forme, donc comparer au-delà de ses décimales n'aurait
#: pas de sens. Une entrée par valeur que le lecteur peut lire deux fois.
COHERENCE = {
    ("f06_mortalite_rotation", "a_all_A150"): ("ExposantAallAUnCinqZero", 3),
    ("f06_mortalite_rotation", "a_new_g060"): ("ExposantAnewgZeroSixZero", 3),
    ("f06_mortalite_rotation", "a_new_A150"): ("ExposantAnewAUnCinqZero", 3),
    ("f06_mortalite_rotation", "a_new_A075"): ("ExposantAnewAZeroSeptCinq", 3),
    ("f01_ancrages", "epsilon_prod_tot"): ("Epsilon", 4),
    ("f01_ancrages", "dln_pop_dlnA"): ("ElasticitePop", 4),
    ("f07_chaine", "epsilon_prod_tot"): ("Epsilon", 4),
    ("f07_chaine", "dln_rotation_dlnA"): ("ElasticiteRotation", 4),
    ("f07_chaine", "dln_mortality_dlnA"): ("ElasticiteMortalite", 4),
    ("f10_k0", "effet"): ("EffetABranchement", 4),
    ("f10_k0", "residuel"): ("EffetResiduelBranchement", 4),
    ("f10_k0", "part_annulee"): ("PartAnnuleeKzero", 1),
    ("f13_vuong", "degenerees_int_in"): ("DegenereesInteret", 0),
    ("f13_vuong", "degenerees_nw"): ("DegenereesNW", 0),
    ("f13_vuong", "ajustements_int_in"): ("AjustementsInteret", 0),
    ("f14_bargain_population", "p_moyen"): ("TauxmarginalPartageImplique", 4),
    ("f19_ablation", "part_expliquee"): ("AblationMquatreBPart", 1),
    ("f19_ablation", "b1_m4b_like"): ("AblationMquatreBBUn", 4),
    ("f19_ablation", "b1_controle"): ("BUnControle", 4),
    ("f22_ponderation", "p_moyen"): ("PartageParContrat", 4),
    ("f22_ponderation", "p_pondere"): ("PartagePondere", 4),
    ("f22_ponderation", "covariance"): ("CovariancePartage", 4),
    ("f23_suffisance", "plancher"): ("PlancherSuffisance", 1, 100),
    ("f23_suffisance", "toutes_suffisantes"): ("ToutesCausesSuffisantes", 1, 100),
    ("f23_suffisance", "incidence_effacement"): ("IncidenceEffacement", 2, 100),
    ("f11_couverture", "n_tail_int_in"): ("CouvertureInteretNTail", 0),
}


def read_macros() -> dict[str, str]:
    text = NUMBERS.read_text(encoding="utf-8")
    return dict(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}\{(.*?)\}\n", text))


def to_float(raw: str) -> float:
    """Les macros sont mises en forme à la française : virgule décimale et
    espace fine insécable aux milliers. Il faut défaire les deux."""
    cleaned = raw.replace("\u202f", "").replace("\u00a0", "").replace(" ", "")
    return float(cleaned.replace(",", "."))


def included() -> dict[str, list[str]]:
    """Nom de figure -> rapports qui l'incluent."""
    out: dict[str, list[str]] = {}
    for report in REPORTS:
        if not report.exists():
            continue
        for name in re.findall(r"\\figurine\{([^}]+)\}", report.read_text(encoding="utf-8")):
            out.setdefault(name, []).append(report.name)
    return out


def test_aucune_figure_manquante() -> None:
    missing = [name for name in included() if not (FIGURES / f"{name}.pdf").exists()]
    assert not missing, f"figures incluses mais absentes de report/figures/ : {missing}"
    print(f"  {len(included())} inclusions, toutes résolues")


def test_aucune_figure_orpheline() -> None:
    produced = {path.stem for path in FIGURES.glob("*.pdf")}
    orphans = sorted(produced - set(included()))
    assert not orphans, f"figures engendrées que personne n'inclut : {orphans}"
    print(f"  {len(produced)} figures engendrées, aucune orpheline")


def test_figures_coherentes_avec_les_macros() -> None:
    manifest_path = FIGURES / "manifest.json"
    assert manifest_path.exists(), "manifest absent : lancer scripts/make_figures.py"
    manifest = {entry["nom"]: entry["valeurs"]
                for entry in json.loads(manifest_path.read_text(encoding="utf-8"))}
    macros = read_macros()

    checked, absent = 0, []
    for (figure, key), spec in COHERENCE.items():
        macro, digits = spec[0], spec[1]
        scale = spec[2] if len(spec) > 2 else 1.0
        if figure not in manifest:
            absent.append(f"{figure} (figure absente du manifeste)")
            continue
        if key not in manifest[figure]:
            absent.append(f"{figure}.{key} (valeur non annotée)")
            continue
        if macro not in macros:
            absent.append(f"\\{macro} (macro absente)")
            continue
        drawn = float(manifest[figure][key]) * scale
        written = to_float(macros[macro])
        # Tolérance = un demi-quantum du dernier chiffre publié, plus une
        # marge de virgule flottante. Au-delà, la figure et le texte ne
        # racontent pas la même chose.
        tolerance = 0.5 * 10 ** (-digits) + 1e-9
        assert abs(drawn - written) <= tolerance, (
            f"{figure}.{key} = {drawn} mais \\{macro} = {written} "
            f"(écart {abs(drawn - written):.6g} > {tolerance:.6g})")
        checked += 1

    assert not absent, "correspondances déclarées mais introuvables : " + ", ".join(absent)
    print(f"  {checked} valeurs annotées confrontées aux macros, toutes d'accord")


def test_provenance_des_figures_non_versionnees() -> None:
    """Une figure tirée d'une source ignorée par git doit déposer sa série.

    Sinon elle n'est pas reproductible depuis le dépôt seul, et le rapport
    cesse d'être autonome.
    """
    data = FIGURES / "data"
    manifest = json.loads((FIGURES / "manifest.json").read_text(encoding="utf-8"))
    declared = {entry["nom"] for entry in manifest
                if "non versionné" in entry.get("legende", "")
                or "panels.npz" in entry.get("legende", "")}
    for name in declared:
        assert (data / f"{name}.csv").exists(), (
            f"{name} lit une source non versionnée sans déposer sa série "
            f"dans report/figures/data/")
    print(f"  {len(declared)} figures à source non versionnée, séries déposées")


def main() -> int:
    tests = [value for key, value in sorted(globals().items()) if key.startswith("test_")]
    for test in tests:
        print(f"{test.__name__} :")
        test()
    print(f"\ntest_figures : {len(tests)}/{len(tests)} verts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
