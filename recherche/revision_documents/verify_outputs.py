"""Contrôles indépendants des exports et de l'autonomie des sources LaTeX."""
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import t

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / "generated"


def rows(path):
    with path.open(newline="") as h:
        return list(csv.DictReader(h))


def check_summary(individual, summary, keys, value, mean_key="mean"):
    groups = defaultdict(list)
    for r in rows(OUT / individual):
        groups[tuple(r[k] for k in keys)].append(float(r[value]))
    for r in rows(OUT / summary):
        vals = np.asarray(groups[tuple(r[k] for k in keys)])
        assert len(vals) == int(r["n"])
        assert np.isclose(vals.mean(), float(r[mean_key]), atol=1e-12)
        half = t.ppf(.975, len(vals)-1)*vals.std(ddof=1)/np.sqrt(len(vals))
        assert np.isclose(half, float(r["ci95"]), atol=1e-12)


def main():
    manifest = json.loads((OUT / "manifest.json").read_text())
    for source in manifest["sources"]:
        assert hashlib.sha256((ROOT/source["path"]).read_bytes()).hexdigest() == source["sha256"]
    check_summary("rev_quantiles_graines.csv", "rev_quantiles_points.csv", ("field", "quantile"), "ratio")
    check_summary("rev_reponse_graines.csv", "rev_reponse_estimateurs.csv", ("lineage", "arm"), "epsilon", "mean_log_ratio")
    for r in rows(OUT / "rev_reponse_graines.csv"):
        assert np.isclose(float(r["epsilon"]), np.log(float(r["treated"])/float(r["control"]))/np.log(1.5))
    for r in rows(OUT / "rev_quantiles_graines.csv"):
        assert np.isclose(float(r["ratio"]), float(r["treated"])/float(r["control"]))
    for gamma in (.3, .5, .7):
        for delta in (.01, .05, .2):
            A = 1.7
            k = (A*(1-delta)/delta)**(1/(1-gamma))
            assert np.isclose((k+A*k**gamma)*(1-delta), k)
            x = .4
            assert np.isclose(A*(k*x)**gamma/k, delta/(1-delta)*x**gamma)
    for dirname, stem in [("note_resultats", "note"), ("note_communication_encadrants", "note_encadrants")]:
        note = HERE.parent/dirname/"latex"
        text = (note/f"{stem}.tex").read_text()
        figures = re.findall(r"\\figurine\{([^}]+)\}", text)
        assert len(figures) == len(set(figures))
        for name in figures:
            assert any((note/"figures"/f"{name}.{ext}").exists() for ext in ("pdf", "png"))
        for filename in re.findall(r"\\input\{([^}]+)\}", text):
            assert (note/(filename if filename.endswith(".tex") else filename+".tex")).exists(), filename
            assert ".." not in filename
        assert "QUESTIONS_TEMP" not in text and "AUDIT_TEMP" not in text
        indexed = rows(note/"data_revision/figures_sources.csv")
        assert {r["figure"] for r in indexed} == set(figures)
        for r in indexed:
            paths = list((note/"figures").glob(r["figure"]+".*"))
            assert hashlib.sha256(paths[0].read_bytes()).hexdigest() == r["figure_sha256"]
        runs = rows(note/"data_revision/runs_m44.csv")
        assert len(runs) == len({r["run_id"] for r in runs}) == 372
        for path in OUT.iterdir():
            if path.suffix in (".csv", ".json"):
                assert path.read_bytes() == (note/"data_revision"/path.name).read_bytes()
        print(f"{dirname}: {len(figures)} figures, sources locales, 372 identifiants uniques et exports identiques")
    print(f"OK : {len(manifest['sources'])} empreintes sources ; rapports de quantiles et IC95 recalculés ; neuf contrôles de point fixe et d'adimensionnement")


if __name__ == "__main__":
    main()
