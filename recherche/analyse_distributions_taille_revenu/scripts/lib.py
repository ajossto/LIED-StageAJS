import csv
import glob
import json
import os

# scripts/ -> analyse_distributions_taille_revenu/ -> recherche/ -> jupyter/ (repo root)
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
RUNS_GLOB = os.path.join(BASE, "simulation_lab_data/runs/*/run.json")


def find_csv_dir(run_dir):
    for root, dirs, files in os.walk(run_dir):
        if os.path.basename(root) == "csv":
            return root
    return None


def load_stationary_runs(model_ids=("etude_sensibilite_27_04_wip", "modele_27_04_wip")):
    rows = []
    for f in glob.glob(RUNS_GLOB):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if d.get("model_id") not in model_ids:
            continue
        if d.get("status") != "completed":
            continue
        s = d.get("summary", {}) or {}
        if s.get("stationary") is not True:
            continue
        p = d.get("parameters", {}) or {}
        run_dir = os.path.dirname(f)
        csv_dir = find_csv_dir(run_dir)
        if csv_dir is None:
            continue
        rows.append({
            "run_id": d["run_id"],
            "params": p,
            "summary": s,
            "csv_dir": csv_dir,
        })
    return rows


def read_raw_distribution(csv_dir, name):
    """Returns dict step -> list of values, from distrib_brute_<name>.csv"""
    path = os.path.join(csv_dir, f"distrib_brute_{name}.csv")
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        for row in reader:
            if len(row) < 2:
                continue
            try:
                step = int(float(row[0]))
                val = float(row[1])
            except ValueError:
                continue
            out.setdefault(step, []).append(val)
    return out


def last_step_values(csv_dir, name, min_step=None):
    data = read_raw_distribution(csv_dir, name)
    if not data:
        return None, []
    steps = sorted(data.keys())
    if min_step is not None:
        candidates = [s for s in steps if s >= min_step]
        step = candidates[0] if candidates else steps[-1]
    else:
        step = steps[-1]
    return step, data[step]


def measurement_step_floor(run):
    s = run["summary"]
    for key in ("t_measure", "tail_start", "t_regime"):
        v = s.get(key)
        if isinstance(v, (int, float)):
            return int(v)
    return None
