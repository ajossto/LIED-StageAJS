"""Pont M4.4 -> reporting.py de M4.3, pour produire les ~20 figures vectorielles
de la campagne de référence (arms/free/control/seed0, gamma=0.5, T=4000) sans
toucher au moteur M4.4 ni au reporting.py de M4.3.

Contexte : reporting.py (modeles-systeme-physicoeconomique/m4_3_credit_soc/)
est générique -- il ne connaît que quatre points d'E/S propres à la mise en
disque de M4.3 :
  - config(folder)       -> folder/config.json (dict "parameters" + clefs plates)
  - snapshots(folder)    -> folder/snapshots/entities_t*.npz
  - folder/final_loans.csv  (colonnes lender,borrower,q,r)
  - folder/entities.csv     (colonnes id,birth_t,alive_final)
Le reste (Gini/Lorenz, ajustements de queue, export SVG, describe_run/save)
opère sur des tableaux nus et est directement réutilisable.

Ce script matérialise ces quatre points d'E/S DANS LE DOSSIER DU RUN M4.4
(results/campaign/arms/free/control/seed0/), en n'AJOUTANT que des fichiers
absents de ce dossier -- aucun fichier de sortie du moteur M4.4
(series.csv, avalanches.csv, deaths.csv, panels.npz, run.json, summary.json,
market_stats.csv, tension*.csv, loss_edges.npz, snapshot_t4000.pkl) n'est
modifié ni supprimé. Les fichiers ajoutés :
  - config.json                       (dérivé de run.json)
  - snapshots/entities_t{step:05d}.npz  (un par pas unique de panels.npz)
  - final_loans.csv                   (dérivé de snapshot_t4000.pkl : book.loans)
  - entities.csv                      (dérivé de snapshot_t4000.pkl : population)

Puis il importe reporting.py par chemin (comme figures.py de M4.3),
monkey-patche `series_figures` (qui contient, non factorisé, le calcul du
taux marginal interne r* -- pas de fonction séparée `internal_rate_evolution`
malgré son nom de fichier de sortie) pour utiliser les champs A/gamma PAR
ENTITÉ déjà présents dans panels.npz plutôt que les scalaires config()["A"]/
["gamma"] (valides pour M4.3 homogène, faux pour M4.4 hétérogène), puis
appelle generate_run().
"""

from __future__ import annotations

import csv
import importlib.util
import json
import pickle
import shutil
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

M4_4_ROOT = Path("/home/anatole/jupyter/m4_4_rebond_credit_soc")
FOLDER = M4_4_ROOT / "results/campaign/arms/free/control/seed0"
REPORTING_PATH = Path(
    "/home/anatole/jupyter/modeles-systeme-physicoeconomique/m4_3_credit_soc/reporting.py"
)


# --------------------------------------------------------------------------
# 1. config.json
# --------------------------------------------------------------------------
def build_config(folder: Path) -> None:
    run = json.loads((folder / "run.json").read_text(encoding="utf-8"))
    parameters = run["parameters"]
    payload = {
        "parameters": parameters,
        # describe_run() lit cette clef au niveau racine (pas dans
        # "parameters") -- absente de run.json, qui porte "model_id".
        "model_version": run.get("model_id", "m4_4_rebond_credit_soc"),
        "seed": run.get("seed", parameters.get("seed", 0)),
        # Marqueurs de provenance (demande explicite : rien de ce qui est
        # ajouté ne doit pouvoir être confondu avec une sortie du moteur
        # M4.4, qui n'écrit lui-même aucun config.json). config() de
        # reporting.py ne lit que payload["parameters"] : ces clefs
        # supplémentaires sont inertes pour lui.
        "_generated_by": "m4_4_rebond_credit_soc/scripts/reporting_bridge.py",
        "_generated_at": datetime.now().isoformat(timespec="seconds"),
        "_note": "Fichier dérivé de run.json, non produit par le moteur M4.4.",
    }
    (folder / "config.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[config.json] écrit ({folder / 'config.json'})")


# --------------------------------------------------------------------------
# 2. snapshots/entities_t*.npz, dérivés de panels.npz
# --------------------------------------------------------------------------
def build_snapshots(folder: Path) -> None:
    snap_dir = folder / "snapshots"
    snap_dir.mkdir(exist_ok=True)
    with np.load(folder / "panels.npz") as data:
        arrays = {key: np.asarray(data[key]) for key in data.files}
    t = arrays["t"]
    unique_steps = np.unique(t)
    passthrough_fields = [key for key in arrays if key != "t"]
    written = 0
    for step in unique_steps:
        mask = t == step
        snap = {field: arrays[field][mask] for field in passthrough_fields}
        k = snap["K"].astype(float)
        claims = snap["claims"].astype(float)
        debts = snap["debts"].astype(float)
        prod = snap["prod"].astype(float)
        int_in = snap["int_in"].astype(float)
        int_out = snap["int_out"].astype(float)
        # Champs dérivés, identiques aux identités comptables du moteur M4.3
        # (model.py:722-723,753-754,783-784) : NW = K + créances - dettes,
        # revenu brut = production + intérêts reçus, revenu net = revenu brut
        # - intérêts payés. M4.4 ne stocke pas ces trois champs dans
        # panels.npz (seul le brut K/claims/debts/prod/int_in/int_out y est),
        # donc reconstruits ici plutôt que dans le moteur (hors périmètre).
        snap["nw"] = k + claims - debts
        snap["income"] = prod + int_in
        snap["income_net"] = prod + int_in - int_out
        out_path = snap_dir / f"entities_t{int(step):05d}.npz"
        np.savez(out_path, **snap)
        written += 1
    print(f"[snapshots/] {written} fichiers écrits dans {snap_dir} "
          f"(pas {int(unique_steps.min())}..{int(unique_steps.max())})")
    (snap_dir / "README.txt").write_text(
        "Fichiers dérivés de ../panels.npz par "
        "m4_4_rebond_credit_soc/scripts/reporting_bridge.py -- pas produits "
        "par le moteur M4.4. nw/income/income_net sont reconstruits "
        "(identités comptables), tous les autres champs sont un simple "
        "passage direct des colonnes de panels.npz pour le pas concerné.\n"
        f"Couverture : pas {int(unique_steps.min())} à {int(unique_steps.max())} "
        "seulement (panel_every=10 dans les paramètres du run, ET la "
        "fenêtre enregistrée par ce run M4.4 ne commence elle-même qu'à "
        "ce pas -- cf. commentaire dans main() sur l'amorçage non "
        "instrumenté).\n",
        encoding="utf-8",
    )


# --------------------------------------------------------------------------
# 3 & 4. final_loans.csv et entities.csv, dérivés de snapshot_t4000.pkl
# --------------------------------------------------------------------------
def _load_final_snapshot(folder: Path):
    # Le pickle référence m4_4.model.Population / m4_4.model.LoanBook :
    # le paquet m4_4 doit être importable, donc son dossier PARENT
    # (m4_4_rebond_credit_soc/) doit être sur sys.path.
    parent = str(M4_4_ROOT)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    with open(folder / "snapshot_t4000.pkl", "rb") as stream:
        return pickle.load(stream)


def build_final_loans(folder: Path, payload) -> None:
    book = payload["book"]
    path = folder / "final_loans.csv"
    with open(path, "w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["lender", "borrower", "q", "r"])
        for lender, borrower, principal, rate in book.loans.values():
            writer.writerow([lender, borrower, principal, rate])
    print(f"[final_loans.csv] {len(book.loans)} prêts actifs écrits dans {path}")


def build_entities(folder: Path, payload) -> None:
    population = payload["population"]
    # Vérité terrain, pas une approximation : `population.birth` est indexé
    # par identifiant d'entité et couvre TOUTES les entités jamais nées
    # (mortes ou vivantes) -- pas seulement celles présentes dans panels.npz
    # (qui ne couvre que t>=2010 et à cadence panel_every=10). De même,
    # `population.alive` (liste de bool indexée par id) donne l'état exact à
    # t=4000, préférée au complément de deaths.csv comme le permettait la
    # consigne.
    births = population.birth
    alive = population.alive
    assert len(births) == len(alive), "population.birth et .alive désynchronisés"
    # VALIDÉ empiriquement (2026-09-25) : len(births)=120161 alors que
    # alive_final=1031 + lignes de deaths.csv=60151 ne totalisent que 61182.
    # Ce n'est PAS une incohérence dans ce pont : m4_4/live.py::resume_from_series
    # explique que ce run "control" reprend un état de population hérité d'un
    # AMORÇAGE non instrumenté (avant le début de la fenêtre enregistrée --
    # panels.npz ne couvre que t=2010..4000). Les ~58979 entités nées et
    # mortes PENDANT cet amorçage portent un birth_t < t0 et n'ont jamais eu
    # de ligne dans deaths.csv ("amorçages ne sont pas instrumentés", cf.
    # live.py). Elles sont écrites ici quand même (vérité brute de
    # population.birth/.alive) car aucune figure de reporting.py ne les
    # consulte par ailleurs : `lifespan()` ne considère comme "censurées" que
    # les entités présentes dans l'instantané final (donc les 1031 vivantes,
    # toutes correctement retrouvées ici), et `entity_lives()` retourne tôt
    # en l'absence d'individual_series.csv.gz. Vérifié : aucun chevauchement
    # entre `alive_final=1` et les id de deaths.csv, et tous les id de
    # deaths.csv ont bien alive_final=0.
    path = folder / "entities.csv"
    with open(path, "w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["id", "birth_t", "alive_final"])
        for entity_id, birth_t in enumerate(births):
            # 1/0 et non True/False : read_csv() de reporting.py convertit les
            # valeurs par float() quand c'est possible : "1"/"0" -> 1.0/0.0,
            # mais "True"/"False" resteraient des chaînes non vides (donc
            # toujours vraies au test `not data["alive_final"], y compris
            # pour une entité morte -- un bug d'interprétation qu'il faut
            # éviter en écrivant des 0/1 numériques.
            writer.writerow([entity_id, int(birth_t), 1 if alive[entity_id] else 0])
    n_alive = sum(1 for value in alive if value)
    print(f"[entities.csv] {len(births)} entités écrites dans {path} "
          f"({n_alive} vivantes à t=4000, {len(births) - n_alive} mortes)")


# --------------------------------------------------------------------------
# Chargement de reporting.py par chemin (idiome de figures.py, M4.3), sans
# modifier le fichier sur disque.
# --------------------------------------------------------------------------
def load_reporting_module():
    name = "m4_3_reporting_for_m4_4_bridge"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPORTING_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossible de charger {REPORTING_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def make_patched_series_figures(reporting):
    """Remplace `series_figures` par une version identique EXCEPTÉ pour le
    bloc r* = A.gamma.K^(gamma-1) (troisième sous-figure, écrite dans
    internal_rate_evolution.png) : celui-ci lisait deux scalaires
    config()["A"]/["gamma"] valables pour un M4.3 homogène, mais faux pour
    M4.4 où A et gamma sont des champs PAR ENTITÉ (déjà présents dans les
    instantanés bridés). Tout le reste -- extraction_power.png,
    destruction_moving_avg.png, noms de fichiers, notes, sources -- est
    inchangé caractère pour caractère."""
    plt = reporting.plt
    np_ = reporting.np
    COLORS = reporting.COLORS
    LABELS = reporting.LABELS
    save = reporting.save
    config = reporting.config
    snapshots = reporting.snapshots
    rolling = reporting.rolling
    read_csv = reporting.read_csv
    Path_ = reporting.Path

    def series_figures(members, out: Path_, title: str):
        fig, axis = plt.subplots(figsize=(12, 5))
        for index, (seed, folder) in enumerate(members):
            snaps = snapshots(folder); steps = sorted(snaps); color = COLORS[index % 10]
            if not steps:
                continue
            med = []; q10 = []; q90 = []
            for step in steps:
                values = np_.asarray(snaps[step]["prod"], dtype=float)
                values = values[np_.isfinite(values) & (values >= 0)]
                med.append(np_.median(values) if len(values) else 0)
                q10.append(np_.quantile(values, .1) if len(values) else 0)
                q90.append(np_.quantile(values, .9) if len(values) else 0)
            axis.fill_between(steps, q10, q90, color=color, alpha=.14)
            axis.plot(steps, med, color=color, label=f"médiane — {LABELS['seed']} {seed}")
        axis.set(xlabel=LABELS["step"], ylabel="Production Π (J/pas)")
        axis.grid(True, alpha=.22); axis.legend()
        fig.tight_layout()
        save(fig, out / "extraction_power.png", sources=["snapshots/entities_t*.npz"],
             note="Production individuelle aux instantanés : médiane et bande interdécile D1–D9.")

        fig, axis = plt.subplots(figsize=(12, 5))
        for index, (seed, folder) in enumerate(members):
            rows = read_csv(folder / "series.csv"); t = [row["t"] for row in rows]
            if not rows:
                continue
            window = max(5, min(100, len(rows) // 10)); color = COLORS[index % 10]
            axis.plot(t, rolling([row["prod_tot"] for row in rows], window), color=color, alpha=.55,
                      label=f"production — {LABELS['seed']} {seed}")
            axis.plot(t, rolling([row["destroyed"] + row["claim_losses"] for row in rows], window),
                      color=color, ls="--", label=f"destruction — {LABELS['seed']} {seed}")
        axis.set(xlabel=LABELS["step"], ylabel="J/pas"); axis.grid(True, alpha=.22); axis.legend()
        fig.tight_layout()
        save(fig, out / "destruction_moving_avg.png", sources=["series.csv"],
             note="Production totale et destruction (joules détruits + pertes de créances), en moyennes glissantes.")

        fig, axis = plt.subplots(figsize=(12, 5))
        for index, (seed, folder) in enumerate(members):
            cfg = config(folder)
            gamma = float(cfg.get("gamma", 0.5)); scale_A = float(cfg.get("A", 1.0))
            snaps = snapshots(folder); steps = []; values = []
            for step, snap in snaps.items():
                k = np_.asarray(snap["K"], dtype=float)
                mask = k > 0
                if not np_.any(mask):
                    continue
                if "A" in snap and "gamma" in snap:
                    # Chemin M4.4 : A et gamma hétérogènes, un par entité.
                    a_i = np_.asarray(snap["A"], dtype=float)[mask]
                    gamma_i = np_.asarray(snap["gamma"], dtype=float)[mask]
                    r_star = a_i * gamma_i * np_.power(k[mask], gamma_i - 1.0)
                else:
                    # Chemin M4.3 d'origine : A et gamma scalaires (config.json).
                    r_star = scale_A * gamma * np_.power(k[mask], gamma - 1.0)
                steps.append(step); values.append(float(np_.median(r_star)))
            if steps:
                axis.plot(steps, values, "o-", ms=3, color=COLORS[index % 10], label=f"{LABELS['seed']} {seed}")
        axis.set(xlabel=LABELS["step"], ylabel="r* = A·γ·K^(γ−1)"); axis.grid(True, alpha=.22); axis.legend()
        fig.tight_layout()
        save(fig, out / "internal_rate_evolution.png", sources=["snapshots/entities_t*.npz", "config.json"],
             note="Taux marginal interne médian r* = A·γ·K^(γ−1), aux instantanés.")

    return series_figures


def backup_existing_figures(folder: Path) -> Path | None:
    figures_dir = folder / "figures"
    if not figures_dir.exists() or not any(figures_dir.iterdir()):
        return None
    stamp = datetime.now().strftime("%Y-%m-%d")
    backup = folder / f"figures_avant_bridge_{stamp}"
    if backup.exists():
        shutil.rmtree(backup)
    shutil.copytree(figures_dir, backup)
    print(f"[backup] figures/ existant copié vers {backup} avant régénération")
    return backup


def main() -> None:
    build_config(FOLDER)
    build_snapshots(FOLDER)
    payload = _load_final_snapshot(FOLDER)
    build_final_loans(FOLDER, payload)
    build_entities(FOLDER, payload)

    backup_existing_figures(FOLDER)

    reporting = load_reporting_module()
    reporting.series_figures = make_patched_series_figures(reporting)

    errors = reporting.generate_run(FOLDER, "M4.4 — contrôle principal, graine 0")
    print(f"\n{len(errors)} erreur(s) pendant generate_run():")
    for error in errors:
        print("  -", error)

    figures_dir = FOLDER / "figures"
    produced = sorted(p.name for p in figures_dir.glob("*.png"))
    print(f"\n{len(produced)} PNG produits dans {figures_dir} :")
    for name in produced:
        print("  -", name)


if __name__ == "__main__":
    main()
