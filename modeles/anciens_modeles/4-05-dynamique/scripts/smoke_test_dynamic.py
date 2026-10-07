"""
Smoke tests du runtime dynamique.

Usage:
    python scripts/smoke_test_dynamic.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from config import SimulationConfig
from simulation import Simulation, run_scenario
from dynamic_control_server import DynamicRuntimeController, build_server


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_short_run() -> None:
    sim = Simulation(SimulationConfig(duree_simulation=8, seed=42))
    stats = sim.run(verbose=False)
    assert_true(len(stats) == 8, "run() doit produire 8 lignes de stats")
    assert_true(sim.current_step == 8, "current_step doit avancer")


def test_observation_json() -> None:
    sim = Simulation(SimulationConfig(duree_simulation=3, seed=42))
    sim.run_step()
    obs = sim.current_observation()
    json.dumps(obs)
    assert_true(isinstance(obs, dict), "current_observation() doit retourner un dict")
    assert_true(obs["current_step"] == 1, "observation au bon step")


def test_parameter_updates() -> None:
    sim = Simulation(SimulationConfig(duree_simulation=3, seed=42, theta=0.35))
    result = sim.apply_parameter_updates({"theta": 0.42})
    assert_true(not result["refused"], "theta categorie A doit etre accepte")
    assert_true(sim.config.theta == 0.42, "theta doit etre modifie")
    refused = sim.apply_parameter_updates({"seed": 7})
    assert_true(refused["refused"], "seed categorie C doit etre refuse")
    assert_true(sim.config.seed == 42, "seed ne doit pas changer")


def test_entity_updates() -> None:
    sim = Simulation(SimulationConfig(duree_simulation=3, seed=42))
    before = [e.alpha for e in sim.active_entities()]
    refused = sim.apply_entity_updates({"alpha_multiplier": 1.1}, allow_risky=False)
    assert_true(refused["refused"], "entity update doit exiger allow_risky=True")
    result = sim.apply_entity_updates({"alpha_multiplier": 1.1}, allow_risky=True)
    assert_true(not result["refused"], "entity update alpha_multiplier accepte avec allow_risky")
    after = [e.alpha for e in sim.active_entities()]
    assert_true(after[0] == before[0] * 1.1, "alpha existant doit etre multiplie")
    assert_true(result["applied"][0]["affected_entities"] == len(before), "nombre entites affectees")


def test_run_dynamic() -> None:
    sim = Simulation(SimulationConfig(duree_simulation=10, seed=42, lambda_creation=1.0))

    def update_provider() -> dict | None:
        if sim.current_step == 4:
            return {"lambda_creation": 2.0}
        return None

    sim.run_dynamic(n_steps=10, observe_every=5, update_provider=update_provider)
    assert_true(sim.current_step == 10, "run_dynamic doit avancer la simulation")
    assert_true(sim.config.lambda_creation == 2.0, "update_provider doit etre applique")
    assert_true(len(sim.parameter_update_log) == 1, "update log attendu")


def test_scenario() -> None:
    scenario = {
        "name": "smoke_scenario",
        "seed": 42,
        "initial_config": {"duree_simulation": 12, "theta": 0.2, "lambda_creation": 1.0},
        "interventions": [
            {
                "step": 5,
                "parameter": "theta",
                "old_value_expected": 0.2,
                "new_value": 0.3,
                "scope": "global_config",
            }
        ],
    }
    sim = run_scenario(scenario)
    assert_true(sim.current_step == 12, "run_scenario doit executer duree_simulation")
    assert_true(sim.config.theta == 0.3, "intervention scenario appliquee")
    json.dumps(sim.intervention_journal())


def test_scenario_entity_updates() -> None:
    scenario = {
        "name": "entity_update_scenario",
        "seed": 42,
        "initial_config": {"duree_simulation": 8},
        "interventions": [
            {
                "step": 3,
                "entity_updates": {"alpha_multiplier": 1.05},
                "scope": "existing_entities",
                "comment": "test alpha existing entities",
            }
        ],
    }
    sim = run_scenario(scenario, allow_risky=True)
    assert_true(sim.current_step == 8, "scenario entity doit avancer")
    assert_true(any(e.get("parameter") == "entity_alpha" for e in sim.parameter_update_log), "journal entity attendu")


def test_demo_script() -> None:
    cmd = [sys.executable, str(ROOT / "examples" / "dynamic_demo.py"), "--steps", "12", "--observe-every", "6"]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert_true(proc.returncode == 0, proc.stderr or proc.stdout)
    assert_true("Parameter update log" in proc.stdout, "demo doit afficher le journal")


def _http_json(url: str, payload: dict | None = None) -> dict:
    if payload is None:
        with urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def test_dynamic_control_server_api() -> None:
    controller = DynamicRuntimeController(SimulationConfig(duree_simulation=20, seed=42, theta=0.35))
    server = build_server("127.0.0.1", 0, controller=controller, quiet=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://{server.server_address[0]}:{server.server_address[1]}"
    try:
        obs = _http_json(base + "/api/observation")
        assert_true(obs["observation"]["current_step"] == 0, "observation HTTP initiale")

        stepped = _http_json(base + "/api/step", {"n_steps": 2})
        assert_true(stepped["observation"]["current_step"] == 2, "step HTTP doit avancer")

        updated = _http_json(base + "/api/update", {"updates": {"theta": 0.41}})
        assert_true(not updated["result"]["refused"], "update HTTP categorie A accepte")
        assert_true(updated["observation"]["current_config"]["theta"] == 0.41, "theta HTTP modifie")

        refused = _http_json(base + "/api/update", {"updates": {"seed": 99}})
        assert_true(refused["result"]["refused"], "seed HTTP refuse")

        entity_updated = _http_json(
            base + "/api/entity_update",
            {"updates": {"alpha_multiplier": 1.01}, "scope": "existing_entities", "allow_risky": True},
        )
        assert_true(not entity_updated["result"]["refused"], "entity update HTTP accepte")

        _http_json(base + "/api/play", {"max_steps": 3, "delay_seconds": 0.001})
        deadline = time.time() + 5
        while time.time() < deadline:
            obs = _http_json(base + "/api/observation")
            if obs["observation"]["current_step"] >= 5 and not obs["state"]["running"]:
                break
            time.sleep(0.02)
        assert_true(obs["observation"]["current_step"] >= 5, "play HTTP doit avancer")

        exported = _http_json(base + "/api/export_journal")
        assert_true(exported["interventions"], "export journal doit produire un scenario")
        assert_true(any("entity_updates" in i for i in exported["interventions"]), "export scenario doit inclure entity_updates")
    finally:
        controller.stop()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def main() -> int:
    tests = [
        test_short_run,
        test_observation_json,
        test_parameter_updates,
        test_entity_updates,
        test_run_dynamic,
        test_scenario,
        test_scenario_entity_updates,
        test_demo_script,
        test_dynamic_control_server_api,
    ]
    for test in tests:
        test()
        print(f"OK {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
