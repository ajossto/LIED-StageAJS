"""Temps de relaxation sur runs pilotes M4.3, ÉTENDU à la variable
d'intérêt central (PROMPT_M4_3_FINAL.md §3) : M4.2B (`renewal_relaxation_
all_runs.py`, copié tel quel dans ce dossier, §5/§8 — réutilisation, pas de
récriture) n'a jamais mesuré le temps de relaxation propre du REVENU
D'INTÉRÊT PUR (`int_in`, `pop.int_in` dans `m4_3/model.py`) — seulement
`nw` (net worth), `K` (capital) et `income` (production + intérêt, PAS
l'intérêt seul). C'est exactement l'écart que le prompt demande de vérifier
(§3, dernier point avant "Checkpointing obligatoire" ; §8 du rapport final
M4.2B, cité comme limite).

Réutilise `persistence_curve`/`fit_fopdt` (régression FOPDT déjà validée en
M4.2B) SANS LES RÉÉCRIRE — importés directement de
`renewal_relaxation_all_runs.py`."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import interest_income  # noqa: E402
from renewal_relaxation_all_runs import persistence_curve, fit_fopdt  # noqa: E402

FIELDS = (
    ("nw", "net_worth"),
    ("K", "capital"),
    ("income", "income (production+interet)"),
    ("int_in", "interet_pur (variable centrale du programme)"),
)


def analyze_run(run_dir: Path) -> list[dict]:
    snaps = interest_income.load_all_entity_snapshots(run_dir)
    if len(snaps) < 5:
        raise ValueError(f"pas assez de snapshots dans {run_dir} ({len(snaps)} < 5)")
    t0 = snaps[0][0]
    rows = []
    for field, field_name in FIELDS:
        t, y = persistence_curve(snaps, field)
        fit = fit_fopdt(t, y, t0)
        row = {"field": field, "field_name": field_name, "n_snapshots": len(snaps),
               "t0": t0, "t_last": snaps[-1][0]}
        if fit["ok"]:
            row.update(fit)
            row["t_converge"] = t0 + fit["t_delay"] + 3 * fit["tau"]
        else:
            row.update({"ok": False})
        rows.append(row)
    return rows


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: relaxation_pilot.py <run_dir> [<run_dir> ...]")
        sys.exit(1)

    for run_dir_str in sys.argv[1:]:
        run_dir = Path(run_dir_str)
        print(f"\n=== {run_dir} ===")
        rows = analyze_run(run_dir)
        print(f"{'field':>10} {'tau':>10} {'t_delay':>10} {'floor':>8} {'r2':>8} {'t_converge':>12}")
        taus = {}
        for r in rows:
            if r.get("ok"):
                print(f"{r['field']:>10} {r['tau']:>10.1f} {r['t_delay']:>10.1f} "
                      f"{r['floor']:>8.3f} {r['r2']:>8.3f} {r['t_converge']:>12.1f}")
                taus[r["field"]] = r["tau"]
            else:
                print(f"{r['field']:>10}   FIT ÉCHOUÉ")

        if "int_in" in taus:
            others = [taus[f] for f in ("nw", "K", "income") if f in taus]
            if others:
                other_mean = sum(others) / len(others)
                ratio = taus["int_in"] / other_mean if other_mean else float("nan")
                print(f"\ntau(int_in)={taus['int_in']:.1f} vs tau moyen(nw,K,income)={other_mean:.1f} "
                      f"-> ratio={ratio:.2f}")
                if ratio > 1.5 or ratio < 1 / 1.5:
                    print("ÉCART NOTABLE (>50%) : le proxy M4.2B (nw/K/income) ne représente PAS "
                          "correctement le temps de relaxation de l'intérêt pur — la fenêtre "
                          "d'analyse doit être positionnée sur tau(int_in), pas sur le proxy.")
                else:
                    print("Pas d'écart notable (<50%) : le proxy M4.2B reste une approximation "
                          "raisonnable pour cette cellule.")


if __name__ == "__main__":
    main()
