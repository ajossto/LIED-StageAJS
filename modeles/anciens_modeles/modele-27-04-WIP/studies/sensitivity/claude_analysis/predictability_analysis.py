"""
Analyse de la prédictibilité de l'évolution des populations.

Pour une sélection de cas couvrant différents régimes, calcule :
  - Exposant de Hurst (R/S) : H ≈ 0.5 = bruit brownien, H > 0.7 = tendance persistante
  - Autocorrélation aux décalages 1, 5, 20, 50
  - Erreur AR(5) one-step-ahead vs. baseline naïf (répétition lag-1)
  - Ratio drift/bruit : |ΔN|_mean / std(ΔN) — mesure la régularité locale
  - Entropie de permutation (ordre 3) : mesure la complexité

Chaque run est classé :
  - "bruit"      : H < 0.55, rapport AR_ratio > 0.85
  - "tendance"   : H > 0.70, autocorr_lag20 > 0.50
  - "régime"     : grande autocorrélation + faible entropie
  - "hybride"    : intermédiaire
"""
from __future__ import annotations
import json, sys, math
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from run_simulation import run_and_collect

OUT = HERE / "results" / "claude_predictability.json"
AGG = HERE / "results" / "claude_predictability_aggregate.json"

N_STEPS   = 1500
N_WORKERS = 4
SEEDS     = [42, 7, 123]

# Cases couvrant différents régimes de comportement de population
CASES = [
    ("k2_baseline",   {"n_candidats_pool": 2, "epsilon": 1e-3}),
    ("k3_baseline",   {"n_candidats_pool": 3, "epsilon": 1e-3}),
    ("k3_sigma005",   {"n_candidats_pool": 3, "alpha_sigma_brownien": 0.005, "epsilon": 1e-3}),
    ("k3_sigma020",   {"n_candidats_pool": 3, "alpha_sigma_brownien": 0.020, "epsilon": 1e-3}),
    ("k3_mu0",        {"n_candidats_pool": 3, "mu": 0.0, "epsilon": 1e-3}),
    ("k4_baseline",   {"n_candidats_pool": 4, "epsilon": 1e-3}),
    ("k4_lam15",      {"n_candidats_pool": 4, "lambda_creation": 1.5, "epsilon": 1e-3}),
    ("k4_sigma020",   {"n_candidats_pool": 4, "alpha_sigma_brownien": 0.020, "epsilon": 1e-3}),
    ("k5_baseline",   {"n_candidats_pool": 5, "epsilon": 1e-3}),
    ("k4_lam30",      {"n_candidats_pool": 4, "lambda_creation": 3.0, "epsilon": 1e-3}),
]


# ─── Métriques de prédictibilité ───────────────────────────────────────────

def hurst_rs(ts: list[float], min_len: int = 8) -> float:
    """Exposant de Hurst par analyse R/S. Retourne nan si insuffisant."""
    n = len(ts)
    if n < 32:
        return float("nan")
    # utilise seulement les 512 derniers points pour la stabilité
    ts = ts[-512:] if n > 512 else ts
    n = len(ts)
    rs_list = []
    scale_list = []
    for scale in _log2_scales(n, min_len):
        rs_vals = []
        for start in range(0, n - scale + 1, scale):
            chunk = ts[start:start + scale]
            m = sum(chunk) / scale
            deviations = [chunk[i] - m for i in range(scale)]
            cumdev = []
            c = 0
            for d in deviations:
                c += d
                cumdev.append(c)
            R = max(cumdev) - min(cumdev)
            diffs = [chunk[i] - chunk[i-1] for i in range(1, scale)]
            if not diffs:
                continue
            S = math.sqrt(sum(d*d for d in diffs) / len(diffs))
            if S > 0:
                rs_vals.append(R / S)
        if rs_vals:
            rs_list.append(math.log(sum(rs_vals) / len(rs_vals)))
            scale_list.append(math.log(scale))
    if len(scale_list) < 3:
        return float("nan")
    return _linreg_slope(scale_list, rs_list)


def _log2_scales(n: int, min_len: int) -> list[int]:
    scales = []
    s = min_len
    while s <= n // 2:
        scales.append(s)
        s *= 2
    return scales


def _linreg_slope(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    return num / den if den > 0 else float("nan")


def autocorr(ts: list[float], lag: int) -> float:
    """Autocorrélation sur les différences premières."""
    diff = [ts[i] - ts[i-1] for i in range(1, len(ts))]
    if len(diff) <= lag:
        return float("nan")
    m = sum(diff) / len(diff)
    var = sum((x - m) ** 2 for x in diff) / len(diff)
    if var < 1e-12:
        return 1.0
    cov = sum((diff[i] - m) * (diff[i - lag] - m)
              for i in range(lag, len(diff))) / (len(diff) - lag)
    return cov / var


def ar_prediction_error_ratio(ts: list[float], p: int = 5, test_frac: float = 0.3) -> float:
    """
    Erreur one-step-ahead d'un AR(p) vs. baseline naïf (x_{t+1} = x_t).
    Retourne ratio = MAE_AR / MAE_naive. < 1 = AR meilleur.
    Entraîné sur les 70% premiers, testé sur les 30% derniers.
    """
    n = len(ts)
    if n < p + 20:
        return float("nan")
    train_end = int(n * (1 - test_frac))
    train = ts[:train_end]
    test  = ts[train_end:]
    if len(test) < 5:
        return float("nan")

    # Moindres carrés sur les différences pour stabilité numérique
    # Modèle : diff[t] = sum(a[i] * diff[t-i-1]) pour i in range(p)
    diff_train = [train[i] - train[i-1] for i in range(1, len(train))]
    if len(diff_train) < p + 5:
        return float("nan")

    # Matrice de design
    X = []
    y_vec = []
    for t in range(p, len(diff_train)):
        X.append([diff_train[t - j - 1] for j in range(p)])
        y_vec.append(diff_train[t])

    coeffs = _ols(X, y_vec)
    if coeffs is None:
        return float("nan")

    # Reconstruction sur la fenêtre test
    # On a besoin des p dernières différences du train pour lancer l'AR
    recent_diffs = [train[i] - train[i-1] for i in range(max(1, len(train) - p), len(train))]
    all_diffs = list(recent_diffs)
    preds = []
    actuals = []
    prev_val = train[-1]
    for i in range(len(test)):
        # Prédire la prochaine différence
        feats = [all_diffs[-(j+1)] for j in range(p)] if len(all_diffs) >= p else None
        if feats is None:
            break
        pred_diff = sum(c * f for c, f in zip(coeffs, feats))
        pred_val = prev_val + pred_diff
        actual_val = test[i]
        preds.append(pred_val)
        actuals.append(actual_val)
        # Mise à jour avec la vraie valeur
        all_diffs.append(actual_val - prev_val)
        prev_val = actual_val

    if not preds:
        return float("nan")
    mae_ar = sum(abs(p - a) for p, a in zip(preds, actuals)) / len(preds)
    # Baseline naïf : x_{t+1} = x_t (ie diff=0)
    mae_naive = sum(abs(test[i] - test[i-1] if i > 0 else test[i] - train[-1])
                    for i in range(len(test))) / len(test)
    if mae_naive < 1e-9:
        return float("nan")
    return mae_ar / mae_naive


def _ols(X: list[list[float]], y: list[float]) -> list[float] | None:
    """OLS minimal sans numpy. Retourne None si singulier."""
    p = len(X[0])
    n = len(X)
    # XtX et Xty
    XtX = [[0.0] * p for _ in range(p)]
    Xty = [0.0] * p
    for row, yi in zip(X, y):
        for i in range(p):
            Xty[i] += row[i] * yi
            for j in range(p):
                XtX[i][j] += row[i] * row[j]
    # Régularisation légère
    for i in range(p):
        XtX[i][i] += 1e-6
    # Résolution par élimination de Gauss
    return _gauss_solve(XtX, Xty)


def _gauss_solve(A: list[list[float]], b: list[float]) -> list[float] | None:
    n = len(b)
    M = [A[i][:] + [b[i]] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[pivot] = M[pivot], M[col]
        if abs(M[col][col]) < 1e-12:
            return None
        f = M[col][col]
        M[col] = [x / f for x in M[col]]
        for row in range(n):
            if row != col:
                factor = M[row][col]
                M[row] = [M[row][j] - factor * M[col][j] for j in range(n + 1)]
    return [M[i][n] for i in range(n)]


def permutation_entropy(ts: list[float], order: int = 3, lag: int = 1) -> float:
    """Entropie de permutation normalisée (0=régulier, 1=aléatoire)."""
    n = len(ts)
    if n < order * lag + 5:
        return float("nan")
    from math import factorial, log2
    counts: dict[tuple, int] = {}
    total = 0
    for i in range(n - (order - 1) * lag):
        motif = tuple(ts[i + j * lag] for j in range(order))
        pattern = tuple(sorted(range(order), key=lambda x: motif[x]))
        counts[pattern] = counts.get(pattern, 0) + 1
        total += 1
    if total == 0:
        return float("nan")
    entropy = -sum((c / total) * log2(c / total) for c in counts.values())
    max_entropy = log2(factorial(order))
    return entropy / max_entropy if max_entropy > 0 else float("nan")


def drift_noise_ratio(ts: list[float]) -> float:
    """Ratio |ΔN|_mean / std(ΔN). Grand = tendance dominante, petit = bruit."""
    diff = [abs(ts[i] - ts[i-1]) for i in range(1, len(ts))]
    if not diff:
        return float("nan")
    mean_abs = sum(diff) / len(diff)
    std = math.sqrt(sum((d - mean_abs) ** 2 for d in diff) / len(diff))
    return mean_abs / std if std > 1e-9 else float("nan")


def classify(h: float, ac20: float, ar_ratio: float, perm_ent: float) -> str:
    if math.isnan(h):
        return "indéterminé"
    if h < 0.52 and ar_ratio > 0.85:
        return "bruit_brownien"
    if h > 0.70 and ac20 > 0.40:
        return "variation_lente"
    if h > 0.60 and perm_ent < 0.75:
        return "régime_structuré"
    if h > 0.60:
        return "tendance_modérée"
    return "hybride"


def compute_predictability(ts: list[float]) -> dict:
    # Normaliser par la moyenne pour comparer des régimes avec populations très différentes
    m = sum(ts) / len(ts) if ts else 1.0
    ts_norm = [x / m if m > 0 else x for x in ts]

    h     = hurst_rs(ts_norm)
    ac1   = autocorr(ts_norm, 1)
    ac5   = autocorr(ts_norm, 5)
    ac20  = autocorr(ts_norm, 20)
    ac50  = autocorr(ts_norm, 50)
    ar_r  = ar_prediction_error_ratio(ts_norm)
    pent  = permutation_entropy(ts, order=3)
    dnr   = drift_noise_ratio(ts_norm)
    cls   = classify(h, ac20, ar_r if not math.isnan(ar_r) else 1.0, pent if not math.isnan(pent) else 1.0)

    return {
        "hurst": round(h, 4) if not math.isnan(h) else None,
        "autocorr_lag1":  round(ac1,  4) if not math.isnan(ac1)  else None,
        "autocorr_lag5":  round(ac5,  4) if not math.isnan(ac5)  else None,
        "autocorr_lag20": round(ac20, 4) if not math.isnan(ac20) else None,
        "autocorr_lag50": round(ac50, 4) if not math.isnan(ac50) else None,
        "ar5_error_ratio": round(ar_r, 4) if not math.isnan(ar_r) else None,
        "perm_entropy":   round(pent, 4) if not math.isnan(pent) else None,
        "drift_noise_ratio": round(dnr, 4) if not math.isnan(dnr) else None,
        "class": cls,
    }


# ─── Job parallèle ─────────────────────────────────────────────────────────

def _job(name: str, override: dict, seed: int) -> dict:
    r = run_and_collect(override, n_steps=N_STEPS, seed=seed)
    ts = r.get("ts_n_alive", [])
    metrics = compute_predictability(ts)
    bounded = r.get("regime_diagnostics", {}).get("bounded_tail", False)
    return {
        "case": name,
        "seed": seed,
        "bounded_tail": bounded,
        "n_steps": len(ts),
        "mean_alive": sum(ts) / len(ts) if ts else 0,
        **metrics,
    }


def mean(xs): return sum(xs) / len(xs) if xs else float("nan")
def std(xs):
    if len(xs) < 2: return 0.
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def _aggregate(results):
    groups = defaultdict(list)
    for r in results:
        groups[r["case"]].append(r)

    agg = []
    print("\n=== Résumé prédictibilité ===")
    header = f"{'case':22s} {'H':>6} {'ac20':>6} {'ar_r':>6} {'pent':>6} {'class':20s} {'p_bnd':>5}"
    print(header)
    print("-" * len(header))
    for case, runs in sorted(groups.items()):
        hursts = [r["hurst"] for r in runs if r.get("hurst") is not None]
        ac20s  = [r["autocorr_lag20"] for r in runs if r.get("autocorr_lag20") is not None]
        ar_rs  = [r["ar5_error_ratio"] for r in runs if r.get("ar5_error_ratio") is not None]
        pents  = [r["perm_entropy"] for r in runs if r.get("perm_entropy") is not None]
        bnds   = [r["bounded_tail"] for r in runs]
        classes = [r.get("class", "?") for r in runs]
        dominant = max(set(classes), key=classes.count)
        h_m   = mean(hursts) if hursts else float("nan")
        ac20_m = mean(ac20s) if ac20s else float("nan")
        ar_m  = mean(ar_rs)  if ar_rs  else float("nan")
        p_m   = mean(pents)  if pents  else float("nan")
        p_bnd = sum(bnds) / len(bnds) if bnds else float("nan")
        row = {
            "case": case,
            "n_seeds": len(runs),
            "hurst_mean": round(h_m, 3) if not math.isnan(h_m) else None,
            "ac20_mean": round(ac20_m, 3) if not math.isnan(ac20_m) else None,
            "ar5_ratio_mean": round(ar_m, 3) if not math.isnan(ar_m) else None,
            "perm_entropy_mean": round(p_m, 3) if not math.isnan(p_m) else None,
            "p_bounded": round(p_bnd, 2) if not math.isnan(p_bnd) else None,
            "dominant_class": dominant,
        }
        agg.append(row)
        fmt = lambda x: f"{x:.3f}" if isinstance(x, float) and not math.isnan(x) else "  — "
        print(f"{case:22s} {fmt(h_m):>6} {fmt(ac20_m):>6} {fmt(ar_m):>6} {fmt(p_m):>6} {dominant:20s} {p_bnd:.2f}")
    AGG.write_text(json.dumps(agg, indent=2))
    print(f"\nAgrégat: {AGG}")


def main():
    # Aussi inclure les long runs existants si disponibles
    existing_results = []
    long_probe_f = HERE / "results" / "codex_long_probe_steps3000_seeds42.json"
    if long_probe_f.exists():
        try:
            for r in json.loads(long_probe_f.read_text()):
                ts = r.get("ts_n_alive", [])
                if not ts:
                    continue
                metrics = compute_predictability(ts)
                bounded = r.get("bounded_tail", r.get("regime_diagnostics", {}).get("bounded_tail", False))
                case_key = r.get("case_key", r.get("case", "long_probe"))
                existing_results.append({
                    "case": f"long_{case_key}",
                    "seed": r.get("seed", 42),
                    "bounded_tail": bounded,
                    "n_steps": len(ts),
                    "mean_alive": sum(ts) / len(ts),
                    "source": "long_probe",
                    **metrics,
                })
            print(f"Chargé {len(existing_results)} long runs depuis {long_probe_f.name}")
        except Exception as e:
            print(f"Impossible de charger long probe: {e}")

    # Runs manquants
    existing = json.loads(OUT.read_text()) if OUT.exists() else []
    done = {(e["case"], e["seed"]) for e in existing}
    jobs = [(name, ov, s) for name, ov in CASES
            for s in SEEDS if (name, s) not in done]
    print(f"{len(jobs)} sims à lancer, {len(existing)} déjà présentes.")

    results = list(existing)
    if jobs:
        with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
            futures = {ex.submit(_job, n, ov, s): (n, s) for n, ov, s in jobs}
            for i, fut in enumerate(as_completed(futures), 1):
                n, s = futures[fut]
                try:
                    r = fut.result()
                    results.append(r)
                    print(f"[{i}/{len(jobs)}] {n} seed={s}: H={r.get('hurst')} "
                          f"ar={r.get('ar5_error_ratio')} class={r.get('class')}")
                except Exception as e:
                    print(f"ERREUR {n} seed={s}: {e}")
                OUT.write_text(json.dumps(results, indent=2))

    _aggregate(results + existing_results)


if __name__ == "__main__":
    main()
