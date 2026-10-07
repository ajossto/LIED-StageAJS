"""Dry-run + manifeste de nettoyage des journaux bruts de M4.2B
(PROMPT_M4_3_FINAL.md §7 point 6). CE SCRIPT NE SUPPRIME RIEN — il calcule
et écrit le manifeste ; l'exécution réelle est un pas séparé, gardé pour
après le point de supervision quotidien suivant (§9).

Portée volontairement restreinte à `results/{campaign,confirmation}/` :
mesuré le 2026-08-06, ces deux collections pèsent à elles seules ~75 Go sur
les ~76 Go visés par l'autorisation (`du -sh`), et leur structure est
régulière (`<label>/seed<N>/`, un fichier agrégé unique par collection avec
colonnes `label,seed`). Les dossiers `pilot_*` (~2 Go combinés) ont un
nommage moins régulier (dirs plats `<param>_seed<N>`, un `control_geometric`
sans suffixe de graine) et ne sont PAS traités par cette passe — gain
marginal, pas de raison de risquer une correspondance fragile pour eux. Si
besoin plus tard, les traiter à la main ou étendre `COLLECTIONS` seulement
après vérification manuelle de leur structure.

Règles non négociables (§7.6, citées ici pour que le manifeste soit
auto-suffisant) :
  - jamais touché : `report/`, les fichiers agrégés à la racine de
    `results/` (*.csv, *.json), quoi que ce soit dans `m4_3_credit_soc/`.
  - toujours conservé par run : `config.json`, `analysis.json`/`summary.json`.
  - supprimable par run SEULEMENT si ce run apparaît déjà dans le fichier
    agrégé de sa collection : `loan_events.csv.gz`, `deaths.csv`,
    `final_loans.csv`, `entities.csv`, `avalanche_members.csv`,
    `snapshots/*.npz`.
"""

from __future__ import annotations

import csv
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

RESULTS = Path("/home/anatole/jupyter/m4_2b_credit_soc/results")
MANIFEST_PATH = RESULTS / "CLEANUP_MANIFEST.md"

DELETABLE_NAMES = (
    "loan_events.csv.gz", "deaths.csv", "final_loans.csv",
    "entities.csv", "avalanche_members.csv",
)
SNAPSHOT_GLOB = "snapshots/*.npz"
KEEP_ALWAYS = ("config.json",)  # analysis.json OU summary.json, vérifié séparément
KEEP_ANALYSIS_ONE_OF = ("analysis.json", "summary.json")

COLLECTIONS = {
    "campaign": RESULTS / "campaign" / "exploration_summary.csv",
    "confirmation": RESULTS / "confirmation" / "confirmation_runs.csv",
}


@dataclass
class RunEntry:
    collection: str
    label: str
    seed: int
    path: Path
    aggregated: bool
    guard_ok: bool
    guard_reason: str
    deletable_files: list[Path] = field(default_factory=list)
    deletable_bytes: int = 0


def _load_aggregated_keys(csv_path: Path) -> set[tuple[str, int]]:
    keys = set()
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            keys.add((row["label"], int(row["seed"])))
    return keys


def _run_dirs(collection_root: Path):
    for label_dir in sorted(p for p in collection_root.iterdir() if p.is_dir()):
        for seed_dir in sorted(label_dir.glob("seed*")):
            if not seed_dir.is_dir():
                continue
            suffix = seed_dir.name[len("seed"):]
            if not suffix.isdigit():
                continue
            yield label_dir.name, int(suffix), seed_dir


def _deletable_files(run_dir: Path) -> list[Path]:
    found = [run_dir / name for name in DELETABLE_NAMES if (run_dir / name).exists()]
    found.extend(run_dir.glob(SNAPSHOT_GLOB))
    return found


def scan() -> list[RunEntry]:
    entries: list[RunEntry] = []
    for collection, agg_path in COLLECTIONS.items():
        if not agg_path.exists():
            raise FileNotFoundError(
                f"fichier agrégé introuvable pour '{collection}' : {agg_path} — "
                f"impossible de vérifier l'agrégation, collection entière ignorée par "
                f"construction (aucune suppression sans preuve d'agrégation)"
            )
        aggregated_keys = _load_aggregated_keys(agg_path)
        for label, seed, run_dir in _run_dirs(agg_path.parent):
            aggregated = (label, seed) in aggregated_keys
            guard_ok = True
            guard_reason = ""
            if not aggregated:
                guard_ok = False
                guard_reason = f"absent de {agg_path.name}"
            elif not all((run_dir / f).exists() for f in KEEP_ALWAYS):
                guard_ok = False
                guard_reason = "config.json absent (anomalie)"
            elif not any((run_dir / f).exists() for f in KEEP_ANALYSIS_ONE_OF):
                guard_ok = False
                guard_reason = "ni analysis.json ni summary.json (anomalie)"

            entry = RunEntry(
                collection=collection, label=label, seed=seed, path=run_dir,
                aggregated=aggregated, guard_ok=guard_ok, guard_reason=guard_reason,
            )
            if guard_ok:
                entry.deletable_files = _deletable_files(run_dir)
                entry.deletable_bytes = sum(p.stat().st_size for p in entry.deletable_files)
            entries.append(entry)
    return entries


def write_manifest(entries: list[RunEntry], path: Path = MANIFEST_PATH) -> None:
    total_bytes = sum(e.deletable_bytes for e in entries if e.guard_ok)
    n_ok = sum(1 for e in entries if e.guard_ok)
    n_skip = sum(1 for e in entries if not e.guard_ok)

    lines = [
        "# Manifeste de nettoyage — journaux bruts M4.2B (dry-run)",
        "",
        f"Généré le {time.strftime('%Y-%m-%d %H:%M:%S')} par "
        f"`m4_3_credit_soc/scripts/cleanup_m4_2b_raw_logs.py` (dry-run, "
        f"AUCUNE suppression exécutée). Autorisation utilisateur : "
        f"PROMPT_M4_3_FINAL.md §7 point 6.",
        "",
        f"**Total à libérer si exécuté : {total_bytes / 1e9:.2f} Go** "
        f"({n_ok} runs éligibles, {n_skip} runs ignorés).",
        "",
        "> Ce total (GB décimaux, somme de `stat().st_size`) dépasse le "
        "\"≈76 Go\" cité dans l'autorisation (mesuré via `du -h`, qui compte "
        "en GiB et arrondit par bloc) alors même que ce script couvre MOINS "
        "de dossiers que l'autorisation (`pilot_*` exclu, voir §7.6 et "
        "JOURNAL.md). Pas une divergence : 76 GiB ≈ 81,6 GB décimaux ; la "
        "différence avec les 78,94 Go ci-dessus correspond aux fichiers "
        "par run volontairement gardés hors de la liste supprimable "
        "(`individual_series.csv.gz`, `avalanches.csv`, `series.csv`), qui "
        "restent sur disque après exécution de ce nettoyage.",
        "",
        "## Runs éligibles (agrégés + garde-fous OK)",
        "",
        "| collection | label | seed | fichiers | octets |",
        "|---|---|---|---|---|",
    ]
    for e in entries:
        if e.guard_ok:
            lines.append(
                f"| {e.collection} | {e.label} | {e.seed} | {len(e.deletable_files)} | "
                f"{e.deletable_bytes} |"
            )
    lines += ["", "## Runs ignorés (garde-fou déclenché — rien ne sera supprimé)", ""]
    skipped = [e for e in entries if not e.guard_ok]
    if not skipped:
        lines.append("(aucun)")
    else:
        lines += ["| collection | label | seed | raison |", "|---|---|---|---|"]
        for e in skipped:
            lines.append(f"| {e.collection} | {e.label} | {e.seed} | {e.guard_reason} |")

    lines += [
        "",
        "## Fichiers listés en détail (chemins complets)",
        "",
    ]
    for e in entries:
        if e.guard_ok and e.deletable_files:
            lines.append(f"### {e.path.relative_to(RESULTS)}")
            for f in e.deletable_files:
                lines.append(f"- `{f.relative_to(RESULTS)}` ({f.stat().st_size} octets)")
            lines.append("")

    path.write_text("\n".join(lines) + "\n")


def _assert_safe_to_delete(path: Path) -> None:
    """Défense en profondeur, indépendante de la logique de `scan()` : même si
    un bug introduisait une entrée hors périmètre, cette fonction refuse de
    supprimer quoi que ce soit qui ne soit pas nommément sur la liste blanche,
    sous `results/{campaign,confirmation}/`, et jamais sous `report/`."""
    resolved = path.resolve()
    if RESULTS.resolve() not in resolved.parents:
        raise RuntimeError(f"refus : {resolved} n'est pas sous {RESULTS}")
    if "report" in resolved.parts:
        raise RuntimeError(f"refus : {resolved} touche un dossier 'report' — jamais autorisé")
    is_named = resolved.name in DELETABLE_NAMES
    is_snapshot = resolved.parent.name == "snapshots" and resolved.suffix == ".npz"
    if not (is_named or is_snapshot):
        raise RuntimeError(f"refus : {resolved} n'est sur aucune liste blanche de suppression")


def execute_cleanup(entries: list[RunEntry]) -> tuple[int, int, list[str]]:
    """Supprime réellement les fichiers des entrées `guard_ok`. Recalculé à
    partir d'un scan FRAIS (pas du manifeste déjà écrit, pour éviter tout
    TOCTOU si l'état sur disque a changé entre le dry-run et l'exécution)."""
    n_deleted = 0
    freed_bytes = 0
    errors: list[str] = []
    for e in entries:
        if not e.guard_ok:
            continue
        for f in e.deletable_files:
            try:
                _assert_safe_to_delete(f)
                size = f.stat().st_size
                f.unlink()
                n_deleted += 1
                freed_bytes += size
            except OSError as exc:
                errors.append(f"{f}: {exc}")
    return n_deleted, freed_bytes, errors


def _append_execution_log(n_deleted: int, freed_bytes: int, errors: list[str], path: Path = MANIFEST_PATH) -> None:
    lines = [
        "",
        "## Exécution réelle",
        "",
        f"Exécuté le {time.strftime('%Y-%m-%d %H:%M:%S')}.",
        f"**{n_deleted} fichiers supprimés, {freed_bytes / 1e9:.2f} Go libérés.**",
    ]
    if errors:
        lines.append(f"{len(errors)} erreurs :")
        lines.extend(f"- {err}" for err in errors)
    else:
        lines.append("Aucune erreur.")
    with open(path, "a") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    execute = "--execute" in sys.argv
    entries = scan()
    write_manifest(entries)
    total_bytes = sum(e.deletable_bytes for e in entries if e.guard_ok)
    n_ok = sum(1 for e in entries if e.guard_ok)
    n_skip = sum(1 for e in entries if not e.guard_ok)
    print(f"scan terminé : {n_ok} runs éligibles, {n_skip} ignorés, "
          f"{total_bytes / 1e9:.2f} Go concernés.")
    print(f"manifeste écrit : {MANIFEST_PATH}")

    if not execute:
        print("AUCUNE suppression effectuée par ce script (dry-run, relancer avec --execute).")
        return

    n_deleted, freed_bytes, errors = execute_cleanup(entries)
    _append_execution_log(n_deleted, freed_bytes, errors)
    print(f"EXÉCUTÉ : {n_deleted} fichiers supprimés, {freed_bytes / 1e9:.2f} Go libérés.")
    if errors:
        print(f"{len(errors)} erreurs (voir {MANIFEST_PATH}).")


if __name__ == "__main__":
    main()
