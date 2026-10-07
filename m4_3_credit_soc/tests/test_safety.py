"""Tests des modules de garde-fou (PROMPT_M4_3_FINAL.md §7) : préflight
disque, plafond mémoire, verrou mono-pool, checkpoint atomique. Assertions
Python simples, exécution directe (convention du dépôt, pas de pytest)."""

from __future__ import annotations

import os
import pickle
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from safety.disk_preflight import check_disk_preflight, require_disk_preflight  # noqa: E402
from safety.mem_cap import worker_memory_cap  # noqa: E402
from safety.pool_lock import PoolLock, PoolAlreadyRunningError  # noqa: E402
from safety.checkpoint import save_checkpoint, load_checkpoint  # noqa: E402


def test_disk_preflight_refuses_when_insufficient():
    # 10 runs restants x 1 Go x marge 3 = 30 Go requis ; on simule 5 Go libres.
    with tempfile.TemporaryDirectory() as d:
        # shutil.disk_usage lit le vrai filesystem ; on ne peut pas mocker la
        # taille du disque sans mocker shutil.disk_usage. On vérifie donc la
        # logique via des valeurs déraisonnablement grandes/petites pour que
        # le résultat soit déterministe quel que soit le disque réel.
        result_impossible = check_disk_preflight(
            remaining_runs=10, per_run_bytes=10**18, path=d
        )
        assert result_impossible.ok is False, "10^18 octets/run doit toujours refuser"

        result_trivial = check_disk_preflight(remaining_runs=1, per_run_bytes=1, path=d)
        assert result_trivial.ok is True, "1 octet requis doit toujours passer"
    print("test_disk_preflight_refuses_when_insufficient OK")


def test_disk_preflight_scales_with_remaining_runs():
    # Le required_bytes doit croître linéairement avec remaining_runs (le bug
    # visé par le prompt : un préflight qui ne regarde que le run courant).
    r1 = check_disk_preflight(remaining_runs=1, per_run_bytes=1_000_000, path="/home")
    r5 = check_disk_preflight(remaining_runs=5, per_run_bytes=1_000_000, path="/home")
    assert r5.required_bytes == 5 * r1.required_bytes
    print("test_disk_preflight_scales_with_remaining_runs OK")


def test_require_disk_preflight_raises():
    try:
        require_disk_preflight(remaining_runs=1, per_run_bytes=10**18, path="/home")
        raise AssertionError("aurait dû lever RuntimeError")
    except RuntimeError:
        pass
    print("test_require_disk_preflight_raises OK")


def test_mem_cap_uses_injected_available_not_total():
    # 16 Gio disponibles, réserve 4 Gio, 6 workers -> 12 Gio / 6 = 2 Gio/worker
    result = worker_memory_cap(
        n_workers=6, reserve_bytes=4 * 1024**3, mem_available_bytes=16 * 1024**3
    )
    expected = (16 * 1024**3 - 4 * 1024**3) // 6
    assert result.cap_per_worker_bytes == expected
    print("test_mem_cap_uses_injected_available_not_total OK")


def test_mem_cap_raises_below_floor():
    try:
        worker_memory_cap(n_workers=6, reserve_bytes=4 * 1024**3, mem_available_bytes=4 * 1024**3)
        raise AssertionError("aurait dû lever RuntimeError (plafond sous le plancher)")
    except RuntimeError:
        pass
    print("test_mem_cap_raises_below_floor OK")


def test_pool_lock_blocks_second_acquire():
    with tempfile.TemporaryDirectory() as d:
        lock_path = Path(d) / ".pool.lock"
        first = PoolLock(lock_path=lock_path)
        first.acquire()
        try:
            second = PoolLock(lock_path=lock_path)
            try:
                second.acquire()
                raise AssertionError("le second acquire() aurait dû échouer")
            except PoolAlreadyRunningError:
                pass
        finally:
            first.release()
        # Une fois libéré, un nouvel acquire doit réussir.
        third = PoolLock(lock_path=lock_path)
        third.acquire()
        third.release()
    print("test_pool_lock_blocks_second_acquire OK")


def test_checkpoint_atomic_replace_and_single_retention():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "checkpoint.pkl"
        save_checkpoint({"t": 1, "data": list(range(1000))}, path)
        loaded = load_checkpoint(path)
        assert loaded["t"] == 1

        # Deuxième sauvegarde : doit écraser, jamais accumuler de fichiers.
        save_checkpoint({"t": 2, "data": list(range(2000))}, path)
        loaded2 = load_checkpoint(path)
        assert loaded2["t"] == 2
        siblings = list(Path(d).iterdir())
        assert siblings == [path], f"aucun fichier temporaire ne doit survivre : {siblings}"
    print("test_checkpoint_atomic_replace_and_single_retention OK")


def test_checkpoint_no_tmp_leftover_on_failure():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "checkpoint.pkl"

        class Unpicklable:
            def __reduce__(self):
                raise pickle.PicklingError("volontairement non picklable")

        try:
            save_checkpoint(Unpicklable(), path)
            raise AssertionError("aurait dû lever une erreur de pickling")
        except pickle.PicklingError:
            pass
        assert not path.exists()
        assert list(Path(d).iterdir()) == [], "le fichier temporaire doit être nettoyé"
    print("test_checkpoint_no_tmp_leftover_on_failure OK")


if __name__ == "__main__":
    test_disk_preflight_refuses_when_insufficient()
    test_disk_preflight_scales_with_remaining_runs()
    test_require_disk_preflight_raises()
    test_mem_cap_uses_injected_available_not_total()
    test_mem_cap_raises_below_floor()
    test_pool_lock_blocks_second_acquire()
    test_checkpoint_atomic_replace_and_single_retention()
    test_checkpoint_no_tmp_leftover_on_failure()
    print("ALL TESTS PASSED")
