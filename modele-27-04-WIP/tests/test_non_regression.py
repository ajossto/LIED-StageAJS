"""
test_non_regression.py — Compare la sortie de modele-27-04-WIP vs Modèle_sans_banque_wip
sur des seeds fixes, à dynamique strictement identique.

Compare pas-par-pas (stats légères) et résumés finaux.
Toute divergence > tolérance numérique → la modification N'EST PAS conservatrice.

Usage :
    /home/anatole/jupyter/.venv/bin/python3 modele-27-04-WIP/tests/test_non_regression.py [--quick]
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIP_SRC = ROOT / "modele-27-04-WIP" / "src"
ORIG_SRC = ROOT / "Modèle_sans_banque_wip" / "src"

# Tolerance pour les comparaisons flottantes : nous exigeons des résultats
# strictement identiques (même seed, même algorithme, même ordre des
# opérations → mêmes flottants au bit près). On tolère 0 par défaut.
ATOL = 0.0
RTOL = 0.0


def _load_simulation(src_dir: Path, tag: str):
    """Importe simulation/config depuis src_dir avec un tag pour isoler les modules."""
    sys.path.insert(0, str(src_dir))
    try:
        for purge in ("config", "models", "statistics", "simulation"):
            sys.modules.pop(purge, None)
        config = importlib.import_module("config")
        simulation = importlib.import_module("simulation")
    finally:
        sys.path.remove(str(src_dir))
    return config, simulation


def run(src_dir: Path, n_steps: int, seed: int):
    config_m, sim_m = _load_simulation(src_dir, tag=src_dir.name)
    cfg = config_m.SimulationConfig(duree_simulation=n_steps, seed=seed)
    sim = sim_m.Simulation(cfg)
    sim.run(verbose=False)
    return sim


def _close(a, b):
    if isinstance(a, float) and isinstance(b, float):
        if a == b:
            return True
        if RTOL == 0 and ATOL == 0:
            return False
        return abs(a - b) <= ATOL + RTOL * max(abs(a), abs(b))
    return a == b


def diff_stats(stats_a, stats_b):
    """Retourne la liste des divergences (step, key, val_a, val_b)."""
    diffs = []
    if len(stats_a) != len(stats_b):
        diffs.append(("LENGTH", "n_stats", len(stats_a), len(stats_b)))
        n = min(len(stats_a), len(stats_b))
    else:
        n = len(stats_a)
    for i in range(n):
        sa, sb = stats_a[i], stats_b[i]
        keys = set(sa.keys()) | set(sb.keys())
        for k in sorted(keys):
            va, vb = sa.get(k, "<missing>"), sb.get(k, "<missing>")
            if not _close(va, vb):
                diffs.append((sa.get("step", i), k, va, vb))
    return diffs


def compare_one(n_steps: int, seed: int, max_diffs_print: int = 10) -> bool:
    print(f"\n[seed={seed}, n_steps={n_steps}]")
    sim_orig = run(ORIG_SRC, n_steps=n_steps, seed=seed)
    sim_wip = run(WIP_SRC, n_steps=n_steps, seed=seed)

    # 1. Comparaison des résumés
    s_orig = sim_orig.summary()
    s_wip = sim_wip.summary()
    summary_ok = True
    for k in sorted(set(s_orig.keys()) | set(s_wip.keys())):
        va, vb = s_orig.get(k), s_wip.get(k)
        marker = "  " if _close(va, vb) else "✗ "
        if not _close(va, vb):
            summary_ok = False
        print(f"  {marker}{k:<28} orig={va!s:<20} wip={vb!s}")

    # 2. Comparaison stats légères pas par pas
    diffs = diff_stats(sim_orig.stats, sim_wip.stats)
    if diffs:
        print(f"  ✗ {len(diffs)} divergence(s) sur les stats légères")
        for d in diffs[:max_diffs_print]:
            print(f"      step={d[0]} {d[1]} orig={d[2]} wip={d[3]}")
        if len(diffs) > max_diffs_print:
            print(f"      ...(+{len(diffs) - max_diffs_print} autres)")
        return False

    # 3. Comparaison indicateurs systémiques
    ind_a = [i.to_dict() for i in sim_orig.collector.indicators]
    ind_b = [i.to_dict() for i in sim_wip.collector.indicators]
    diffs_ind = diff_stats(ind_a, ind_b)
    if diffs_ind:
        print(f"  ✗ {len(diffs_ind)} divergence(s) sur les indicateurs systémiques")
        for d in diffs_ind[:max_diffs_print]:
            print(f"      step={d[0]} {d[1]} orig={d[2]} wip={d[3]}")
        return False

    # 4. Comparaison cascades
    casc_a = [c.to_dict() for c in sim_orig.collector.cascades]
    casc_b = [c.to_dict() for c in sim_wip.collector.cascades]
    if len(casc_a) != len(casc_b):
        print(f"  ✗ nb cascades : orig={len(casc_a)} wip={len(casc_b)}")
        return False
    for ca, cb in zip(casc_a, casc_b):
        for k in set(ca.keys()) | set(cb.keys()):
            if not _close(ca.get(k), cb.get(k)):
                print(f"  ✗ cascade step={ca.get('step')} {k}: orig={ca.get(k)} wip={cb.get(k)}")
                return False

    if summary_ok:
        print("  ✓ summary identique")
    print("  ✓ stats légères, indicateurs systémiques, cascades : tous identiques")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--quick", action="store_true",
                   help="Une seule comparaison (200 pas × seed=42)")
    p.add_argument("--seeds", nargs="*", type=int, default=[42, 7, 123])
    p.add_argument("--n-steps", type=int, default=300)
    args = p.parse_args()

    if args.quick:
        seeds = [42]
        n_steps = 200
    else:
        seeds = args.seeds
        n_steps = args.n_steps

    all_ok = True
    for seed in seeds:
        ok = compare_one(n_steps=n_steps, seed=seed)
        all_ok = all_ok and ok

    print("\n" + ("=" * 60))
    if all_ok:
        print("RÉSULTAT : ✓ tous les seeds testés sont strictement identiques")
        sys.exit(0)
    else:
        print("RÉSULTAT : ✗ DIVERGENCE détectée — la version n'est plus conservatrice")
        sys.exit(1)


if __name__ == "__main__":
    main()
