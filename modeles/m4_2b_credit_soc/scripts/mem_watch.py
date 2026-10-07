"""Observateur mémoire pour la campagne M4.2B (incident du 04/08, JOURNAL.md
§9) : logge à intervalle régulier la mémoire système et par worker
`campaign.py`, pour disposer d'un historique en cas de nouvel arrêt.

Tourne indépendamment de la campagne (sa propre session tmux) pour survivre
si le pool de workers meurt. Stdlib seul (lecture directe de /proc).
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "results" / "campaign" / "mem_watch.csv"
INTERVAL_S = 15
FIELDS = [
    "ts", "mem_total_gb", "mem_available_gb", "mem_used_gb", "swap_used_gb",
    "n_campaign_procs", "campaign_rss_total_gb", "campaign_rss_max_gb",
]


def _meminfo() -> dict[str, int]:
    out = {}
    with open("/proc/meminfo") as f:
        for line in f:
            key, _, rest = line.partition(":")
            parts = rest.split()
            if parts:
                out[key] = int(parts[0]) * 1024  # kB -> bytes
    return out


def _campaign_rss_bytes() -> list[int]:
    rss = []
    for proc_dir in Path("/proc").glob("[0-9]*"):
        try:
            cmdline = (proc_dir / "cmdline").read_bytes()
        except OSError:
            continue
        if b"campaign.py" not in cmdline:
            continue
        try:
            status = (proc_dir / "status").read_text()
        except OSError:
            continue
        for line in status.splitlines():
            if line.startswith("VmRSS:"):
                rss.append(int(line.split()[1]) * 1024)
                break
    return rss


def sample() -> dict:
    mi = _meminfo()
    rss = _campaign_rss_bytes()
    total = mi.get("MemTotal", 0)
    avail = mi.get("MemAvailable", 0)
    swap_total = mi.get("SwapTotal", 0)
    swap_free = mi.get("SwapFree", 0)
    return {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mem_total_gb": round(total / 1e9, 3),
        "mem_available_gb": round(avail / 1e9, 3),
        "mem_used_gb": round((total - avail) / 1e9, 3),
        "swap_used_gb": round((swap_total - swap_free) / 1e9, 3),
        "n_campaign_procs": len(rss),
        "campaign_rss_total_gb": round(sum(rss) / 1e9, 3),
        "campaign_rss_max_gb": round(max(rss) / 1e9, 3) if rss else 0.0,
    }


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_file = not OUT_PATH.exists()
    with open(OUT_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        while True:
            row = sample()
            writer.writerow(row)
            f.flush()
            print(
                f"{row['ts']} mem_used={row['mem_used_gb']}GB "
                f"avail={row['mem_available_gb']}GB swap={row['swap_used_gb']}GB "
                f"campaign_rss={row['campaign_rss_total_gb']}GB "
                f"(n={row['n_campaign_procs']}, max={row['campaign_rss_max_gb']}GB)",
                flush=True,
            )
            time.sleep(INTERVAL_S)


if __name__ == "__main__":
    main()
