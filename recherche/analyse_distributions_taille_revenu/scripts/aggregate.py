import glob
import json
import os
from collections import Counter, defaultdict

RESULTS_GLOB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "*.json"
)


def load_records():
    recs = []
    for f in glob.glob(RESULTS_GLOB):
        try:
            recs.append(json.load(open(f)))
        except Exception:
            continue
    return recs


def group_key(rec):
    p = rec["params"]
    k = p.get("n_candidats_pool")
    homog = p.get("alpha_min") == p.get("alpha_max")
    sigma = p.get("alpha_sigma_brownien")
    return (k, homog, sigma)


def summarize(var_name, criterion="aic"):
    recs = load_records()
    by_group = defaultdict(lambda: Counter())
    by_group_k = defaultdict(lambda: Counter())  # winning family family-size (param count) per group
    n_by_group = Counter()
    for rec in recs:
        e = rec["variables"].get(var_name)
        if not e or "fits" not in e:
            continue
        g = group_key(rec)
        n_by_group[g] += 1
        best_name = e.get(f"overall_best_{criterion}")
        by_group[g][best_name] += 1
        best_k = e["fits"][best_name]["k"]
        by_group_k[g][best_k] += 1
    return by_group, by_group_k, n_by_group


if __name__ == "__main__":
    for var in ("actif_total", "passif_total", "revenu_total"):
        print(f"\n===== {var} (winner by AIC) =====")
        by_group, by_group_k, n_by_group = summarize(var, "aic")
        for g in sorted(n_by_group, key=lambda x: -n_by_group[x]):
            n = n_by_group[g]
            if n < 3:
                continue
            print(f"k={g[0]} homog={g[1]} sigma={g[2]}  (n={n})")
            for name, cnt in by_group[g].most_common():
                print(f"    {name:26s} {cnt}/{n}")
