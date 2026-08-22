"""Tests §4/§8 — reprise depuis un run M4.3 stocké et MESURE de divergence.

M4.3Live est un fork d'institution différente (§3). Rejouer un run M4.3
avec ce moteur ne reproduit sa trajectoire que dans le régime homogène, et
rien ne le garantit hors de ce régime : chaque reprise doit donc mesurer et
RAPPORTER l'écart, jamais le supposer nul.

Ce fichier vérifie les deux faces de cette exigence :
  1. dans le régime homogène, l'écart mesuré est effectivement nul (parité
     bit à bit, obtenue par construction : le chemin (a) du noyau applique
     littéralement (K_ℓ-K_b)/2) ;
  2. le rapport n'est pas un « toujours OK » décoratif — confronté à une
     série qui ne correspond PAS, il signale la divergence, avec le premier
     pas fautif.

    /home/anatole/jupyter/.venv/bin/python3 m4_3live_v2_credit_soc/tests/test_resume_divergence.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, "/home/anatole/jupyter")

from m4_3live_v2.live import (  # noqa: E402
    divergence_report,
    read_series_csv,
    resume_from_series,
)
from m4_3live_v2.model import Config, Intervention, Simulation  # noqa: E402
from simulation_lab.runs.storage import RunStorage  # noqa: E402

REFERENCE_RUN = "m4_3__d1__baseline__seed0"
DIFFERENT_RUN = "m4_3__d1__rho_2__seed0"
T0 = 400


def stored(run_id: str):
    storage = RunStorage()
    metadata = storage.read_metadata(run_id)
    series = Path(storage.run_dir(run_id)) / "series.csv"
    assert series.exists(), f"série absente pour {run_id}"
    return metadata["parameters"], series


def test_homogeneous_resume_is_bit_identical():
    parameters, series = stored(REFERENCE_RUN)
    simulation, report = resume_from_series(parameters, series, T0)
    assert simulation.t == T0
    assert report["n_compared"] == T0
    assert report["bit_identical"], report["first_difference"]
    assert report["max_relative"] == 0.0
    assert not report["max_absolute"], report["max_absolute"]
    assert simulation.kernel.describe()["path_counts"]["identity"] > 0
    assert simulation.kernel.describe()["n_tech"] == 1
    print(
        f"  reprise homogène de {REFERENCE_RUN} à t₀={T0} : écart maximal mesuré "
        f"{report['max_relative']:.1e} sur {report['n_compared']} pas × "
        f"10 colonnes — bit à bit  OK"
    )
    return simulation


def test_report_actually_detects_a_difference():
    """Confronté à une série d'un AUTRE run, le rapport doit dénoncer l'écart."""
    parameters, _ = stored(REFERENCE_RUN)
    _, other_series = stored(DIFFERENT_RUN)
    simulation, report = resume_from_series(parameters, other_series, 60)
    assert not report["bit_identical"], "le rapport ne détecte rien : il est décoratif"
    assert report["first_difference"] is not None
    assert report["max_relative"] > 0.0
    print(
        f"  falsification : contre {DIFFERENT_RUN}, divergence signalée dès "
        f"t={report['first_difference']['t']} sur « "
        f"{report['first_difference']['column']} », écart relatif max "
        f"{report['max_relative']:.3e}  OK"
    )


def test_heterogeneous_resume_diverges_and_says_so():
    """Après une intervention, la trajectoire QUITTE le régime homogène : la
    comparaison à la série M4.3 d'origine doit cesser d'être exacte, et
    l'écart doit rester mesuré et affichable, pas silencieux."""
    parameters, series = stored(REFERENCE_RUN)
    known = set(Config.__dataclass_fields__)
    config = Config(**{**{k: v for k, v in parameters.items() if k in known}, "T": 120})
    simulation = Simulation(config)
    for _ in range(60):
        simulation.step()
    simulation.submit(Intervention(param="A", value=1.4, scope="fraction", phi=0.3))
    simulation.run()
    report = divergence_report(simulation, read_series_csv(series), 120)
    assert not report["bit_identical"]
    assert report["first_difference"]["t"] >= 61, report["first_difference"]
    assert report["max_relative"] > 1e-6
    print(
        f"  intervention à t=61 : divergence à partir de t="
        f"{report['first_difference']['t']}, écart relatif max "
        f"{report['max_relative']:.3e} — mesuré, pas supposé  OK"
    )


def test_divergence_report_is_surfaced_by_the_driver():
    """Le rapport remonte bien jusqu'à l'appelant (pilote/IHM) : c'est ce
    qui garantit qu'il est AFFICHÉ et pas seulement calculé (§8)."""
    from driver.headless import cmd_resume  # noqa: PLC0415
    import argparse
    import io
    import contextlib
    import json
    import tempfile

    directory = tempfile.mkdtemp(prefix="m4_3live_v2_resume_")
    args = argparse.Namespace(run_id=REFERENCE_RUN, t0=40, out=directory)
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = cmd_resume(args)
    assert code == 0
    payload = json.loads(buffer.getvalue())
    assert "divergence" in payload and payload["divergence"]["n_compared"] == 40
    summary = json.loads(Path(directory, "summary.json").read_text(encoding="utf-8"))
    assert summary["divergence"]["bit_identical"] is True
    assert summary["origin_run"] == REFERENCE_RUN
    assert list(Path(directory).glob("snapshot_t40.pkl"))
    print("  le pilote imprime le rapport ET l'écrit dans summary.json  OK")


def main():
    print("test_resume_divergence.py — reprise depuis un run M4.3 stocké (§4, §8)")
    test_homogeneous_resume_is_bit_identical()
    test_report_actually_detects_a_difference()
    test_heterogeneous_resume_diverges_and_says_so()
    test_divergence_report_is_surfaced_by_the_driver()
    print("test_resume_divergence.py : tout est passé.")


if __name__ == "__main__":
    main()
