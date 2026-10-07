"""Garde-fou mémoire indépendant, avec AUTORITÉ de blocage et de terminaison
(PROMPT_M4_3_FINAL.md §7 point 1).

M4.2B (`scripts/mem_watch.py`, JOURNAL.md §10) ne faisait que journaliser :
les deuxième et troisième arrêts machine n'ont laissé aucune trace
d'OOM-kill avec une uptime continue — cohérent avec un thrashing swap
plutôt qu'un OOM-kill propre, un phénomène qu'un plafond `RLIMIT_AS` par
worker ne voit pas (chaque worker peut rester sous son propre plafond tout
en faisant swapper le système entier jusqu'au gel). Ce script tourne dans un
process séparé du pool (sa propre session tmux, comme en M4.2B) et a
l'autorité de :

  1. poser la sentinelle HALT (`safety/halt.py`) si `MemAvailable` descend
     sous un seuil fixe, ou si le débit de swap-in/out reste soutenu sur
     plusieurs lectures consécutives — le lanceur de pool DOIT vérifier
     cette sentinelle avant chaque nouveau run, pas seulement au démarrage
     de la cellule ;
  2. terminer (SIGTERM puis SIGKILL après délai de grâce) les processus
     enregistrés dans `safety/worker_registry.py` si la situation ne se
     résorbe pas.

Stdlib seul (lecture directe de /proc), même patron que mem_watch.py.
"""

from __future__ import annotations

import csv
import os
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from safety.halt import raise_halt, is_halted  # noqa: E402
from safety.worker_registry import read_workers  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "results" / "mem_guard.csv"
INTERVAL_S = 15

MEM_AVAILABLE_FLOOR_BYTES = 2 * 1024**3  # 2 GiB : sous ce seuil, danger immédiat
SWAP_RATE_FLOOR_PAGES_S = 200  # pages/s soutenues = thrashing, pas un pic ponctuel
CONSECUTIVE_BREACHES_TO_ACT = 3  # ~45 s de dégradation soutenue avant d'agir
GRACE_PERIOD_S = 10  # délai entre SIGTERM et SIGKILL des workers

FIELDS = [
    "ts", "mem_available_gb", "swap_in_rate_pps", "swap_out_rate_pps",
    "n_breaches_consecutive", "halt_active", "action",
]


def _meminfo() -> dict[str, int]:
    out = {}
    with open("/proc/meminfo") as f:
        for line in f:
            key, _, rest = line.partition(":")
            parts = rest.split()
            if parts:
                out[key] = int(parts[0]) * 1024
    return out


def _vmstat() -> dict[str, int]:
    out = {}
    with open("/proc/vmstat") as f:
        for line in f:
            key, _, val = line.partition(" ")
            if val.strip().isdigit():
                out[key] = int(val)
    return out


def _terminate_registered_workers() -> list[int]:
    registry = read_workers()
    pids = list(registry.get("worker_pids") or [])
    if registry.get("pool_pid"):
        pids.append(registry["pool_pid"])
    killed = []
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            killed.append(pid)
        except ProcessLookupError:
            continue
    if killed:
        time.sleep(GRACE_PERIOD_S)
        for pid in killed:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                continue
    return killed


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_file = not OUT_PATH.exists()
    prev_vmstat = _vmstat()
    prev_ts = time.monotonic()
    consecutive_breaches = 0
    workers_killed_this_episode = False

    with open(OUT_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()

        while True:
            time.sleep(INTERVAL_S)
            now = time.monotonic()
            dt = max(now - prev_ts, 1e-6)

            mi = _meminfo()
            vm = _vmstat()
            mem_available = mi.get("MemAvailable", 0)
            swap_in_rate = max(vm.get("pswpin", 0) - prev_vmstat.get("pswpin", 0), 0) / dt
            swap_out_rate = max(vm.get("pswpout", 0) - prev_vmstat.get("pswpout", 0), 0) / dt
            prev_vmstat = vm
            prev_ts = now

            breach = (
                mem_available < MEM_AVAILABLE_FLOOR_BYTES
                or swap_in_rate > SWAP_RATE_FLOOR_PAGES_S
                or swap_out_rate > SWAP_RATE_FLOOR_PAGES_S
            )
            consecutive_breaches = consecutive_breaches + 1 if breach else 0

            action = ""
            if consecutive_breaches >= CONSECUTIVE_BREACHES_TO_ACT:
                if not is_halted():
                    raise_halt(
                        f"MemAvailable={mem_available / 1e9:.2f}Go "
                        f"swap_in={swap_in_rate:.0f}pps swap_out={swap_out_rate:.0f}pps "
                        f"({consecutive_breaches} lectures consécutives en dépassement)"
                    )
                    action = "HALT"
                # Ne tuer qu'une fois par épisode : sans ce verrou, chaque tour de
                # boucle re-déclenche SIGTERM sur des PID déjà morts (le registre
                # n'est pas nettoyé par ce script) et le `sleep(GRACE_PERIOD_S)`
                # de _terminate_registered_workers gèle l'échantillonnage à
                # chaque itération pendant tout l'épisode.
                if not workers_killed_this_episode:
                    killed = _terminate_registered_workers()
                    workers_killed_this_episode = True
                    if killed:
                        action = f"{action or 'HALT'}+KILL({killed})"
            elif not breach and is_halted() and consecutive_breaches == 0:
                # Résorption confirmée (une lecture saine) : ne PAS lever le halt
                # automatiquement — décision de reprise laissée au superviseur
                # humain (§9 : ce qui engage un budget de calcul attend la
                # supervision), on se contente de le signaler.
                action = "RESOLVED_PENDING_HUMAN_CLEAR"
            if not is_halted():
                # Le halt a été levé (par un humain, entre deux lectures) :
                # réarmer pour le prochain épisode.
                workers_killed_this_episode = False

            row = {
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "mem_available_gb": round(mem_available / 1e9, 3),
                "swap_in_rate_pps": round(swap_in_rate, 1),
                "swap_out_rate_pps": round(swap_out_rate, 1),
                "n_breaches_consecutive": consecutive_breaches,
                "halt_active": is_halted(),
                "action": action,
            }
            writer.writerow(row)
            f.flush()
            print(
                f"{row['ts']} avail={row['mem_available_gb']}GB "
                f"swap_in={row['swap_in_rate_pps']}pps swap_out={row['swap_out_rate_pps']}pps "
                f"breaches={consecutive_breaches} halt={row['halt_active']} "
                f"{('action=' + action) if action else ''}",
                flush=True,
            )


if __name__ == "__main__":
    main()
