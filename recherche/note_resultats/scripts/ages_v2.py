"""Complément V2 : âges des survivantes, sans simulation ni figure.

Moyennes temporelles des moyennes et médianes instantanées, puis moyenne
entre graines. Aucun regroupement des individus de tous les instantanés.
"""
from pathlib import Path
import csv
import hashlib
import json
import numpy as np
from scipy.stats import sem, t as student

NOTE = Path(__file__).resolve().parents[1]
ROOT = NOTE.parents[1]
OUT = NOTE / 'revision_2026-09-17'


def main():
    rows, sources = [], {}
    for arm in ('control', 'all_A150'):
        for seed in range(12):
            path = ROOT / 'm4_4_rebond_credit_soc/results/campaign/arms/free' / arm / f'seed{seed}/panels.npz'
            sources[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
            with np.load(path, allow_pickle=False) as data:
                ts, ages = data['t'], data['age']
                means, medians = [], []
                for time in range(3010, 4001, 10):
                    age = ages[ts == time]
                    assert age.size and np.all(age >= 0)
                    means.append(float(age.mean()))
                    medians.append(float(np.median(age)))
                rows.append(dict(arm=arm, seed=seed, n_snapshots=len(means),
                                 mean_age=float(np.mean(means)),
                                 mean_snapshot_median_age=float(np.mean(medians))))
    with (OUT / 'ages_v2_graines.csv').open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    results = {}
    for arm in ('control', 'all_A150'):
        results[arm] = {}
        for field in ('mean_age', 'mean_snapshot_median_age'):
            values = [r[field] for r in rows if r['arm'] == arm]
            results[arm][field] = dict(mean=float(np.mean(values)),
                                      ci95=float(student.ppf(.975, 11) * sem(values)))
    record = dict(convention='100 instantanés 3010..4000 par pas de 10 ; moyenne temporelle par graine puis moyenne sur 12 graines ; âge des survivantes, pas durée de vie',
                  sources=sources, results=results)
    (OUT / 'ages_v2.json').write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
