"""Calibration pré-enregistrée de (s, c) — rapport 02 §4.

Critère : dans l'ablation B (sans crédit), régime démographique de M2 préservé
à l'horizon T --- population quasi stationnaire (croissance relative du dernier
quart < 15 %), mortalité endogène active (morts/naissances dans [0,5 ; 1,05]
sur le dernier quart). Plages : s dans [0.5, 0.9], c dans [0.02, 0.10].
La cellule provisoire (s=0.75, c=0.05) est retenue si elle satisfait le
critère ; sinon la cellule viable la plus proche. Décision consignée dans
NOTES.md et jamais retouchée ensuite.

Sert aussi d'étalon de coût (s/pas/entité) pour l'allocation du budget 48 h.
"""
import json

from exp_common import M3Config, RESULTS, run_one

S_GRID = (0.5, 0.65, 0.75, 0.9)
C_GRID = (0.02, 0.05, 0.10)
T_CAL = 1500


def check_regime(run_dir):
    """Applique le critère pré-enregistré sur la série d'un run."""
    from m3.metrics import load_series
    series = load_series(run_dir)
    if not series:
        return dict(ok=False, reason="série vide")
    last = [s for s in series if s["t"] > series[-1]["t"] * 3 // 4]
    pop_start, pop_end = last[0]["pop"], last[-1]["pop"]
    growth = (pop_end - pop_start) / max(pop_start, 1)
    births = sum(s["births"] for s in last)
    deaths = sum(s["deaths"] for s in last)
    ratio = deaths / births if births else float("nan")
    ok = abs(growth) < 0.15 and 0.5 <= ratio <= 1.05
    return dict(ok=ok, growth=round(growth, 4), deaths_over_births=round(ratio, 4),
                pop_final=pop_end)


if __name__ == "__main__":
    verdicts = {}
    for s in S_GRID:
        for c in C_GRID:
            run_id = f"calib_B_s{s}_c{c}"
            cfg = M3Config(seed=0, T=T_CAL, s=s, c=c, credit=False)
            run_one(cfg, run_id, log_every=0, snapshot_every=500)
            verdicts[run_id] = check_regime(RESULTS / run_id)
            v = verdicts[run_id]
            print(f"  s={s} c={c}: ok={v['ok']} growth={v.get('growth')} "
                  f"d/b={v.get('deaths_over_births')} pop={v.get('pop_final')}")
    with open(RESULTS / "calibration_verdicts.json", "w") as fh:
        json.dump(verdicts, fh, indent=2)
    print(json.dumps(verdicts, indent=2))
