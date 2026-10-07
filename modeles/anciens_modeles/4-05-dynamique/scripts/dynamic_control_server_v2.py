"""
Mini logiciel local de pilotage dynamique.

Usage:
    python scripts/dynamic_control_server_v2.py --port 8767

Le serveur utilise uniquement la bibliotheque standard. Les modifications de
parametres passent par Simulation.apply_parameter_updates() et sont donc
appliquees entre deux pas complets.
"""

from __future__ import annotations

import argparse
from collections import deque
import json
import logging
import sys
import threading
import time
import webbrowser
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src_v2"
sys.path.insert(0, str(SRC))
LOG_DIR = ROOT / "logs"
LOG_FILE: Path | None = None
LOGGER = logging.getLogger(Path(__file__).stem)

from config import SimulationConfig
from simulation import Simulation, run_scenario
from output import create_output_folder, save_meta

try:
    from analysis import analyze_folder
except Exception:
    analyze_folder = None


def configure_logging(port: int) -> Path:
    """Configure un log persistant par serveur/port."""
    global LOG_FILE
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE = LOG_DIR / f"{Path(__file__).stem}_{port}.log"
    LOGGER.setLevel(logging.INFO)
    LOGGER.handlers.clear()
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    LOGGER.addHandler(handler)
    LOGGER.propagate = False
    return LOG_FILE


def log_tail(n_lines: int = 200) -> list[str]:
    if LOG_FILE is None or not LOG_FILE.exists():
        return []
    with LOG_FILE.open("r", encoding="utf-8", errors="replace") as handle:
        return list(deque(handle, maxlen=max(1, min(n_lines, 2000))))


INDEX_HTML = """<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dynamic Simulation Control V2</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #1e252e;
      --muted: #66717f;
      --line: #d8dee6;
      --accent: #0f766e;
      --danger: #b42318;
      --ok: #087443;
      --warn: #b45309;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }
    header {
      padding: 16px 20px;
      border-bottom: 1px solid var(--line);
      background: #fff;
      display: flex;
      gap: 16px;
      align-items: baseline;
      justify-content: space-between;
    }
    h1 { margin: 0; font-size: 20px; font-weight: 650; letter-spacing: 0; }
    main {
      max-width: 1220px;
      margin: 0 auto;
      padding: 18px;
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 16px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }
    h2 { margin: 0 0 12px; font-size: 15px; font-weight: 650; letter-spacing: 0; }
    .toolbar, .form-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    button {
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      border-radius: 6px;
      padding: 8px 10px;
      font: inherit;
      cursor: pointer;
      min-height: 36px;
    }
    button.primary { background: var(--accent); color: white; border-color: var(--accent); }
    button.danger { color: var(--danger); }
    button:disabled { opacity: 0.5; cursor: default; }
    input, textarea {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px;
      font: inherit;
      background: #fff;
      color: var(--ink);
      min-height: 36px;
    }
    .button-group {
      display: inline-flex;
      gap: 4px;
      flex-wrap: wrap;
    }
    .button-group button.active {
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
    }
    .param-grid {
      display: grid;
      gap: 8px;
    }
    .param-row {
      display: grid;
      grid-template-columns: minmax(170px, 1fr) minmax(86px, 120px) minmax(120px, auto) minmax(120px, 1fr);
      gap: 8px;
      align-items: center;
    }
    .param-row label {
      color: var(--ink);
      font-size: 13px;
      overflow-wrap: anywhere;
    }
    .param-row input { width: 100%; }
    .param-row.dirty { background: #fff8eb; }
    .param-row.error { background: #fff1f0; }
    .param-row.saved { background: #eefbf4; }
    .param-meta {
      color: var(--muted);
      font-size: 11px;
      margin-left: 6px;
    }
    .param-status {
      color: var(--muted);
      font-size: 12px;
      overflow-wrap: anywhere;
    }
    .param-status.ok { color: var(--ok); }
    .param-status.warn { color: var(--warn); }
    .param-status.error { color: var(--danger); }
    .param-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      justify-content: flex-end;
    }
    .status-line {
      color: var(--muted);
      font-size: 13px;
      min-height: 18px;
      overflow-wrap: anywhere;
    }
    .status-line.ok { color: var(--ok); }
    .status-line.warn { color: var(--warn); }
    .status-line.error { color: var(--danger); }
    textarea {
      width: 100%;
      min-height: 170px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      min-height: 76px;
      background: #fbfcfd;
    }
    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .metric strong { font-size: 18px; font-weight: 650; overflow-wrap: anywhere; }
    canvas {
      width: 100%;
      height: 100%;
      background: #fff;
      display: block;
    }
    .chart-panel {
      resize: both;
      overflow: auto;
      min-width: 430px;
      min-height: 290px;
    }
    .chart-wrap {
      width: 100%;
      height: clamp(300px, 42vh, 620px);
      min-height: 260px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      overflow: hidden;
    }
    .histogram-wrap {
      width: 100%;
      height: 260px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      overflow: hidden;
      margin-top: 12px;
    }
    pre {
      margin: 0;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfd;
      min-height: 160px;
      max-height: 280px;
      overflow: auto;
      font-size: 12px;
    }
    .muted { color: var(--muted); font-size: 13px; }
    .stack { display: grid; gap: 12px; }
    @media (max-width: 900px) {
      main { grid-template-columns: 1fr; }
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .param-row { grid-template-columns: 1fr; }
      .param-actions { justify-content: flex-start; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Dynamic Simulation Control V2</h1>
    <div class="muted" id="state">loading</div>
  </header>
  <main>
    <div class="stack">
      <section>
        <h2>Controle</h2>
        <div class="toolbar">
          <button class="primary" onclick="play()">Play</button>
          <button onclick="pause()">Pause</button>
          <button onclick="stepOnce()">Step</button>
          <button onclick="runBlock(10)">+10</button>
          <button onclick="runBlock(50)">+50</button>
          <button class="danger" onclick="stopRun()">Stop</button>
          <button class="danger" onclick="wipeZero()">Wipe 0</button>
          <label class="muted">delay ms <input id="delay" type="number" value="50" min="0" max="2000" style="width:90px"></label>
        </div>
      </section>
      <section>
        <h2>Metriques</h2>
        <div class="metrics">
          <div class="metric"><span>step</span><strong id="m_step">0</strong></div>
          <div class="metric"><span>entites vivantes</span><strong id="m_alive">0</strong></div>
          <div class="metric"><span>prets actifs</span><strong id="m_loans">0</strong></div>
          <div class="metric"><span>volume prets</span><strong id="m_volume">0</strong></div>
          <div class="metric"><span>actif total</span><strong id="m_assets">0</strong></div>
          <div class="metric"><span>passif total</span><strong id="m_liabilities">0</strong></div>
          <div class="metric"><span>extraction pas</span><strong id="m_extract">0</strong></div>
          <div class="metric"><span>faillites pas</span><strong id="m_failures">0</strong></div>
        </div>
      </section>
      <section class="chart-panel">
        <div class="toolbar" style="justify-content:space-between; margin-bottom:10px">
          <h2 style="margin:0">Courbes en continu</h2>
          <div class="button-group" id="chartWindowButtons">
            <button onclick="setChartWindow('100')">100</button>
            <button onclick="setChartWindow('200')">200</button>
            <button class="active" onclick="setChartWindow('500')">500</button>
            <button onclick="setChartWindow('all')">tous</button>
          </div>
        </div>
        <div class="chart-wrap" id="chartWrap">
          <canvas id="chart"></canvas>
        </div>
        <div class="histogram-wrap" id="histogramWrap">
          <canvas id="histogram"></canvas>
        </div>
      </section>
    </div>
    <div class="stack">
      <section>
        <h2>Parametres</h2>
        <div class="toolbar" style="justify-content:space-between; margin-bottom:10px">
          <label class="muted" title="Autorise les changements de categorie B : utiles en exploration, mais ils changent l'interpretation de la trajectoire.">
            <input id="risky" type="checkbox"> autoriser parametres structurels
          </label>
          <div class="toolbar">
            <button onclick="applyDirtyParameters()">Appliquer modifies</button>
            <button onclick="syncParameterInputs(true)">Recharger valeurs</button>
          </div>
        </div>
        <div class="status-line" id="paramStatus">Pret.</div>
        <div class="param-grid" id="configParamGrid" style="margin-top:10px"></div>
        <p class="muted">Les changements interactifs sont journalises et appliques entre deux pas.</p>
      </section>
      <section>
        <h2>Alpha</h2>
        <div class="toolbar" style="justify-content:space-between; margin-bottom:10px">
          <label class="muted" title="Autorise les modifications directes de productivite alpha.">
            <input id="entityRisky" type="checkbox" checked> autoriser alpha
          </label>
          <button onclick="applyDirtyEntityParameters()">Appliquer alpha modifies</button>
        </div>
        <div class="param-grid" id="alphaParamGrid"></div>
        <p class="muted">Vivantes modifie les entites presentes. Futures modifie la plage alpha_min/alpha_max des prochaines naissances.</p>
      </section>
      <section>
        <h2>Scenario JSON</h2>
        <textarea id="scenario">{
  "name": "ui_theta_lambda",
  "seed": 42,
  "initial_config": {"duree_simulation": 40, "theta": 0.2, "lambda_creation": 1.0},
  "interventions": [
    {"step": 20, "parameter": "theta", "old_value_expected": 0.2, "new_value": 0.4, "scope": "global_config"},
    {"step": 30, "entity_updates": {"alpha_multiplier": 1.05}, "scope": "existing_entities", "comment": "boost productivite des entites vivantes"}
  ]
}</textarea>
        <div class="toolbar" style="margin-top:8px">
          <button onclick="runScenario()">Run scenario</button>
          <button onclick="exportJournal()">Export journal</button>
          <button onclick="saveSimulation()">Sauvegarder simulation</button>
        </div>
      </section>
      <section>
        <h2>Journal</h2>
        <pre id="log"></pre>
      </section>
    </div>
  </main>
  <script>
    let series = [];
    let histogram = null;
    let interventions = [];
    let lastRenderedStep = null;
    let lastHistogramSignature = "";
    let refreshTimer = null;
    let latestState = {};
    let uiHoldUntil = 0;
    let activeChartWindow = "500";
    let parameterControlsReady = false;
    let alphaControlsReady = false;
    let lastConfig = {};
    let lastParameterSchema = {};
    const CONFIG_PARAM_ORDER = [
      "theta", "mu", "seuil_ratio_endettement", "fraction_taux_emprunteur",
      "lambda_creation", "max_credit_iterations", "n_candidats_pool",
      "fraction_auto_investissement", "coefficient_reliquefaction",
      "taux_depreciation_liquide", "taux_depreciation_endo",
      "alpha_min", "alpha_max", "alpha_sigma_brownien",
      "seuil_ratio_liquide_passif", "taux_amortissement",
      "actif_liquide_initial", "passif_inne_initial",
      "epsilon", "freq_snapshot", "duree_simulation", "log_events"
    ];
    const INTEGER_CONFIG_PARAMS = new Set(["max_credit_iterations", "n_candidats_pool", "freq_snapshot", "duree_simulation"]);
    const ENTITY_ALPHA_ORDER = [
      ["alpha_multiplier", 1.05],
      ["alpha_set", 1],
      ["alpha_add", 0.05],
      ["alpha_min", 0.8],
      ["alpha_max", 1.2]
    ];

    function holdUi(ms = 2500) {
      uiHoldUntil = Math.max(uiHoldUntil, Date.now() + ms);
      if (refreshTimer) clearTimeout(refreshTimer);
      refreshTimer = setTimeout(refresh, ms + 80);
    }
    function releaseUi() {
      uiHoldUntil = 0;
    }
    function isControlElement(el) {
      return el && ["INPUT", "TEXTAREA"].includes(el.tagName);
    }
    function statusElement(inputId) {
      return document.getElementById(`s_${inputId}`);
    }
    function setStatus(text, kind = "") {
      const el = document.getElementById("paramStatus");
      if (!el) return;
      el.textContent = text;
      el.className = `status-line ${kind}`.trim();
    }
    function setRowStatus(inputId, text, kind = "") {
      const input = document.getElementById(inputId);
      const row = input ? input.closest(".param-row") : null;
      const status = statusElement(inputId);
      if (status) {
        status.textContent = text || "";
        status.className = `param-status ${kind}`.trim();
      }
      if (row) {
        row.classList.remove("dirty", "error", "saved");
        if (kind === "warn") row.classList.add("dirty");
        if (kind === "error") row.classList.add("error");
        if (kind === "ok") row.classList.add("saved");
      }
    }
    function markDirty(inputId) {
      setRowStatus(inputId, "modifie", "warn");
    }
    async function reportClientError(kind, message, details = {}) {
      try {
        await fetch("/api/client_log", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({kind, message, details, location: window.location.href, ts: new Date().toISOString()})
        });
      } catch (_) {}
    }
    window.addEventListener("error", event => {
      reportClientError("window.error", event.message, {filename: event.filename, line: event.lineno, column: event.colno});
    });
    window.addEventListener("unhandledrejection", event => {
      reportClientError("unhandledrejection", String(event.reason), {});
    });
    document.addEventListener("pointerdown", event => {
      if (isControlElement(event.target)) holdUi(3200);
    }, true);
    document.addEventListener("focusin", event => {
      if (isControlElement(event.target)) holdUi(3200);
    }, true);

    function fmt(x) {
      if (x === null || x === undefined) return "NA";
      if (Math.abs(x) >= 1000000) return Number(x).toExponential(2);
      if (Math.abs(x) >= 1000) return Number(x).toFixed(0);
      if (typeof x === "number") return Number(x).toFixed(2);
      return String(x);
    }
    async function api(path, body) {
      const options = body === undefined ? {} : {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body)
      };
      try {
        const response = await fetch(path, options);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || response.statusText);
        return data;
      } catch (error) {
        await reportClientError("api.error", error.message || String(error), {path, body});
        throw error;
      }
    }
    function sortedConfigParams(config, schema) {
      const known = CONFIG_PARAM_ORDER.filter(name => Object.prototype.hasOwnProperty.call(config, name));
      const extra = Object.keys(config).filter(name => !known.includes(name)).sort();
      return known.concat(extra).filter(name => {
        const item = schema[name] || {};
        return item.risk_category !== "C";
      });
    }
    function inputIdForParam(name) { return `p_${name}`; }
    function inputIdForEntity(name) { return `e_${name}`; }
    function makeValueInput(id, value, isBool = false, integerOnly = false) {
      const input = document.createElement("input");
      input.id = id;
      input.dataset.lastApplied = String(value);
      if (isBool) {
        input.type = "checkbox";
        input.checked = Boolean(value);
      } else {
        input.type = "number";
        input.step = integerOnly ? "1" : "any";
        input.value = value;
      }
      input.addEventListener("input", () => markDirty(id));
      input.addEventListener("keydown", event => {
        if (event.key === "Enter") {
          event.preventDefault();
          const defaultScope = input.dataset.defaultScope || "global_config";
          if (input.dataset.entity === "1") updateEntities(input.dataset.name, id, defaultScope);
          else updateParam(input.dataset.name, id, defaultScope);
        }
      });
      return input;
    }
    function ensureParameterControls(config, schema) {
      lastParameterSchema = schema || {};
      if (parameterControlsReady) return;
      const grid = document.getElementById("configParamGrid");
      grid.textContent = "";
      sortedConfigParams(config, schema || {}).forEach(name => {
        const item = (schema || {})[name] || {};
        const id = inputIdForParam(name);
        const row = document.createElement("div");
        row.className = "param-row";
        const label = document.createElement("label");
        label.htmlFor = id;
        label.textContent = name;
        const meta = document.createElement("span");
        meta.className = "param-meta";
        meta.textContent = item.risk_category ? `cat. ${item.risk_category}` : "";
        label.appendChild(meta);
        const input = makeValueInput(id, config[name], typeof config[name] === "boolean", INTEGER_CONFIG_PARAMS.has(name));
        input.dataset.name = name;
        input.dataset.defaultScope = item.global_config ? "global_config" : "future_entities";
        const actions = document.createElement("div");
        actions.className = "param-actions";
        if (item.global_config) {
          const button = document.createElement("button");
          button.textContent = "global";
          button.addEventListener("click", () => updateParam(name, id, "global_config"));
          actions.appendChild(button);
        }
        if (item.future_entities) {
          const button = document.createElement("button");
          button.textContent = "futures";
          button.addEventListener("click", () => updateParam(name, id, "future_entities"));
          actions.appendChild(button);
        }
        const status = document.createElement("span");
        status.id = `s_${id}`;
        status.className = "param-status";
        row.append(label, input, actions, status);
        grid.appendChild(row);
      });
      parameterControlsReady = true;
    }
    function ensureAlphaControls() {
      if (alphaControlsReady) return;
      const grid = document.getElementById("alphaParamGrid");
      grid.textContent = "";
      ENTITY_ALPHA_ORDER.forEach(([name, initial]) => {
        const id = inputIdForEntity(name);
        const row = document.createElement("div");
        row.className = "param-row";
        const label = document.createElement("label");
        label.htmlFor = id;
        label.textContent = name;
        const meta = document.createElement("span");
        meta.className = "param-meta";
        meta.textContent = "alpha";
        label.appendChild(meta);
        const input = makeValueInput(id, initial, false);
        input.dataset.name = name;
        input.dataset.entity = "1";
        input.dataset.defaultScope = "existing_entities";
        const actions = document.createElement("div");
        actions.className = "param-actions";
        [["existing_entities", "vivantes"], ["future_entities", "futures"]].forEach(([scope, labelText]) => {
          const button = document.createElement("button");
          button.textContent = labelText;
          button.addEventListener("click", () => updateEntities(name, id, scope));
          actions.appendChild(button);
        });
        const status = document.createElement("span");
        status.id = `s_${id}`;
        status.className = "param-status";
        row.append(label, input, actions, status);
        grid.appendChild(row);
      });
      alphaControlsReady = true;
    }
    function syncParameterInputs(force = false) {
      if (!lastConfig) return;
      Object.entries(lastConfig).forEach(([name, value]) => {
        const input = document.getElementById(inputIdForParam(name));
        if (!input || (!force && document.activeElement === input)) return;
        if (input.type === "checkbox") input.checked = Boolean(value);
        else input.value = value;
        input.dataset.lastApplied = String(value);
        if (force) setRowStatus(input.id, "recharge", "ok");
      });
      if (force) setStatus("Valeurs rechargees depuis la simulation.", "ok");
    }
    function parseInputValue(inputId) {
      const input = document.getElementById(inputId);
      if (!input) throw new Error(`champ introuvable: ${inputId}`);
      if (input.type === "checkbox") return input.checked;
      const raw = String(input.value).trim();
      if (raw === "") throw new Error("valeur vide");
      const value = Number(raw);
      if (!Number.isFinite(value)) throw new Error(`valeur numerique invalide: ${raw}`);
      return value;
    }
    function summarizeRefusals(refused) {
      return (refused || []).map(item => item.reason || JSON.stringify(item)).join("; ");
    }
    async function applyDirtyParameters() {
      const dirty = [...document.querySelectorAll("#configParamGrid .param-row.dirty input")];
      if (!dirty.length) {
        setStatus("Aucun parametre modifie.", "warn");
        return;
      }
      for (const input of dirty) {
        await updateParam(input.dataset.name, input.id, input.dataset.defaultScope || "global_config");
      }
    }
    async function applyDirtyEntityParameters() {
      const dirty = [...document.querySelectorAll("#alphaParamGrid .param-row.dirty input")];
      if (!dirty.length) {
        setStatus("Aucun alpha modifie.", "warn");
        return;
      }
      for (const input of dirty) {
        await updateEntities(input.dataset.name, input.id, input.dataset.defaultScope || "existing_entities");
      }
    }
    async function refresh() {
      if (isEditingControl() || Date.now() < uiHoldUntil) {
        scheduleRefresh(latestState.running);
        return;
      }
      let data;
      try {
        data = await api("/api/observation");
      } catch (error) {
        document.getElementById("state").textContent = "serveur indisponible";
        setStatus(`Observation impossible: ${error.message}`, "error");
        scheduleRefresh(false);
        return;
      }
      const obs = data.observation;
      latestState = data.state;
      lastConfig = data.state.config || {};
      ensureParameterControls(lastConfig, data.parameter_schema || {});
      ensureAlphaControls();
      syncParameterInputs(false);
      const stateText = data.state.finished ? "finished" : (data.state.running ? "running" : (data.state.paused ? "paused" : "ready"));
      document.getElementById("state").textContent = `${stateText} · step ${obs.current_step}/${data.state.config.duree_simulation}`;
      document.getElementById("m_step").textContent = obs.current_step;
      document.getElementById("m_alive").textContent = obs.n_entities_alive;
      document.getElementById("m_loans").textContent = obs.n_active_loans;
      document.getElementById("m_volume").textContent = fmt(obs.active_loans_total_volume);
      document.getElementById("m_assets").textContent = fmt(obs.system_total_assets);
      document.getElementById("m_liabilities").textContent = fmt(obs.system_total_liabilities);
      document.getElementById("m_extract").textContent = fmt(obs.last_step_extraction_total);
      document.getElementById("m_failures").textContent = obs.last_step_failures;
      series = (data.history || []).map(row => ({
        step: row.step,
        alive: row.n_entities_alive,
        loans: row.n_prets_actifs,
        assets: row.actif_total_systeme,
        failures: row.n_failures,
        extraction: row.extraction_total
      }));
      histogram = data.entity_size_histogram || null;
      interventions = data.journal.applied_updates || [];
      const newestStep = series.length ? series[series.length - 1].step : obs.current_step;
      if (newestStep !== lastRenderedStep || canvasSizeChanged()) {
        drawChart(data.state);
        lastRenderedStep = newestStep;
      }
      const histogramSignature = JSON.stringify(histogram);
      if (histogramSignature !== lastHistogramSignature || canvasSizeChanged("histogram")) {
        drawHistogram();
        lastHistogramSignature = histogramSignature;
      }
      document.getElementById("log").textContent = JSON.stringify(data.journal.applied_updates, null, 2);
      scheduleRefresh(data.state.running && !data.state.finished);
    }
    function isEditingControl() {
      const active = document.activeElement;
      return active && ["INPUT", "TEXTAREA"].includes(active.tagName);
    }
    function canvasSizeChanged(id = "chart") {
      const canvas = document.getElementById(id);
      const rect = canvas.getBoundingClientRect();
      const ratio = window.devicePixelRatio || 1;
      const w = Math.max(420, Math.floor(rect.width * ratio));
      const h = Math.max(260, Math.floor(rect.height * ratio));
      return canvas.width !== w || canvas.height !== h;
    }
    function fitCanvas(id = "chart") {
      const canvas = document.getElementById(id);
      const rect = canvas.getBoundingClientRect();
      const ratio = window.devicePixelRatio || 1;
      const w = Math.max(420, Math.floor(rect.width * ratio));
      const h = Math.max(260, Math.floor(rect.height * ratio));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }
      const ctx = canvas.getContext("2d");
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      return {canvas, ctx, width: rect.width, height: rect.height};
    }
    function drawChart(state = {}) {
      const {ctx, width, height} = fitCanvas();
      ctx.clearRect(0, 0, width, height);
      const pad = {left: 58, right: 132, top: 38, bottom: 64};
      const plotW = Math.max(10, width - pad.left - pad.right);
      const plotH = Math.max(10, height - pad.top - pad.bottom);
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, width, height);
      ctx.strokeStyle = "#d8dee6";
      ctx.fillStyle = "#66717f";
      ctx.font = "12px system-ui";
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      for (let i = 0; i <= 4; i++) {
        const y = pad.top + (plotH * i / 4);
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(width - pad.right, y); ctx.stroke();
        ctx.fillText(`${100 - i * 25}%`, pad.left - 8, y);
      }
      ctx.textAlign = "center";
      for (let i = 0; i <= 4; i++) {
        const x = pad.left + (plotW * i / 4);
        ctx.beginPath(); ctx.moveTo(x, pad.top); ctx.lineTo(x, height - pad.bottom); ctx.stroke();
      }
      ctx.strokeStyle = "#1e252e";
      ctx.beginPath();
      ctx.moveTo(pad.left, pad.top);
      ctx.lineTo(pad.left, height - pad.bottom);
      ctx.lineTo(width - pad.right, height - pad.bottom);
      ctx.stroke();
      ctx.fillStyle = "#1e252e";
      ctx.font = "600 13px system-ui";
      ctx.textAlign = "left";
      ctx.fillText("Evolution pas a pas", pad.left, 18);
      ctx.font = "12px system-ui";
      ctx.fillStyle = "#66717f";
      ctx.fillText(state.running ? "fenetre glissante" : "trace arrete", pad.left + 142, 18);
      if (series.length < 2) {
        ctx.fillStyle = "#66717f";
        ctx.textAlign = "center";
        ctx.fillText("Lancez la simulation pour alimenter les courbes.", width / 2, height / 2);
        drawLegend(ctx, width, pad);
        return;
      }
      const view = chartView();
      const visible = series.filter(p => p.step >= view.xMin && p.step <= view.xMax);
      drawInterventionMarkers(ctx, width, height, pad, plotW, plotH, view.xMin, view.xMax);
      plotLine(ctx, visible, "alive", "#0f766e", pad, plotW, plotH, view.xMin, view.xMax);
      plotLine(ctx, visible, "loans", "#7c3aed", pad, plotW, plotH, view.xMin, view.xMax);
      plotLine(ctx, visible, "assets", "#b45309", pad, plotW, plotH, view.xMin, view.xMax);
      annotateLast(ctx, visible, "alive", "entites", "#0f766e", pad, plotW, plotH, view.xMin, view.xMax);
      annotateLast(ctx, visible, "loans", "prets", "#7c3aed", pad, plotW, plotH, view.xMin, view.xMax);
      annotateLast(ctx, visible, "assets", "actifs", "#b45309", pad, plotW, plotH, view.xMin, view.xMax);
      drawAxesLabels(ctx, width, height, pad, view.xMin, view.xMax);
      drawLegend(ctx, width, pad);
    }
    function chartView() {
      const latest = series.length ? series[series.length - 1].step : 0;
      const raw = activeChartWindow;
      if (raw === "all") {
        return {xMin: series[0].step, xMax: Math.max(series[0].step + 1, latest)};
      }
      const span = Number(raw);
      const xMax = Math.max(span, latest);
      const xMin = Math.max(0, xMax - span);
      return {xMin, xMax};
    }
    function setChartWindow(value) {
      activeChartWindow = value;
      document.querySelectorAll("#chartWindowButtons button").forEach(button => {
        button.classList.toggle("active", button.textContent.trim() === value || (value === "all" && button.textContent.trim() === "tous"));
      });
      drawChart(latestState);
    }
    function scaleFor(points, key) {
      const values = points.map(p => Number(p[key] || 0));
      const min = Math.min(...values);
      const max = Math.max(...values);
      return {min, span: Math.max(1, max - min)};
    }
    function xy(points, point, key, pad, plotW, plotH, xMin, xMax) {
      const scale = scaleFor(points, key);
      const x = pad.left + ((point.step - xMin) / Math.max(1, xMax - xMin)) * plotW;
      const y = pad.top + plotH - ((Number(point[key] || 0) - scale.min) / scale.span) * plotH;
      return {x, y};
    }
    function plotLine(ctx, points, key, color, pad, plotW, plotH, xMin, xMax) {
      if (points.length < 2) return;
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      points.forEach((p, i) => {
        const {x, y} = xy(points, p, key, pad, plotW, plotH, xMin, xMax);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.stroke();
    }
    function annotateLast(ctx, points, key, label, color, pad, plotW, plotH, xMin, xMax) {
      if (!points.length) return;
      const last = points[points.length - 1];
      const {x, y} = xy(points, last, key, pad, plotW, plotH, xMin, xMax);
      ctx.fillStyle = color;
      ctx.beginPath(); ctx.arc(x, y, 3.5, 0, Math.PI * 2); ctx.fill();
      ctx.font = "12px system-ui";
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(`${label}: ${fmt(last[key])}`, Math.min(x + 8, pad.left + plotW + 8), y);
    }
    function interventionLabel(entry) {
      if (entry.parameter === "entity_alpha") {
        const [[name, value]] = Object.entries(entry.operation || {});
        return `${name} = ${fmt(value)}`;
      }
      if (entry.parameter === "future_entity_alpha") {
        if (entry.operation && entry.operation.alpha_set !== undefined) return `alpha futur = ${fmt(entry.operation.alpha_set)}`;
        return `alpha futur = ${fmt(entry.new_value?.alpha_min)}..${fmt(entry.new_value?.alpha_max)}`;
      }
      return `${entry.parameter} = ${fmt(entry.new_value)}`;
    }
    function drawInterventionMarkers(ctx, width, height, pad, plotW, plotH, xMin, xMax) {
      const visible = interventions.filter(entry => Number(entry.step) >= xMin && Number(entry.step) <= xMax);
      if (!visible.length) return;
      ctx.save();
      ctx.strokeStyle = "#475569";
      ctx.fillStyle = "#475569";
      ctx.font = "11px system-ui";
      ctx.textAlign = "left";
      visible.slice(-10).forEach((entry, i) => {
        const x = pad.left + ((Number(entry.step) - xMin) / Math.max(1, xMax - xMin)) * plotW;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(x, pad.top);
        ctx.lineTo(x, pad.top + plotH);
        ctx.stroke();
        ctx.setLineDash([]);
        const label = interventionLabel(entry);
        const y = height - 45 + (i % 2) * 15;
        ctx.fillText(label, Math.min(x + 4, width - pad.right - 120), y);
      });
      ctx.restore();
    }
    function drawAxesLabels(ctx, width, height, pad, xMin, xMax) {
      ctx.fillStyle = "#66717f";
      ctx.font = "12px system-ui";
      ctx.textAlign = "center";
      ctx.fillText(`pas ${xMin}`, pad.left, height - 18);
      ctx.fillText(`pas ${xMax}`, width - pad.right, height - 18);
      ctx.fillText("chaque serie est normalisee sur sa propre plage", pad.left + (width - pad.left - pad.right) / 2, height - 18);
      ctx.save();
      ctx.translate(18, pad.top + (height - pad.top - pad.bottom) / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.fillText("niveau relatif", 0, 0);
      ctx.restore();
    }
    function drawLegend(ctx, width, pad) {
      const items = [
        ["#0f766e", "entites vivantes"],
        ["#7c3aed", "prets actifs"],
        ["#b45309", "actif total"]
      ];
      let y = pad.top;
      ctx.font = "12px system-ui";
      ctx.textAlign = "left";
      items.forEach(([color, label]) => {
        ctx.fillStyle = color;
        ctx.fillRect(width - pad.right + 18, y - 6, 18, 3);
        ctx.fillText(label, width - pad.right + 42, y);
        y += 20;
      });
    }
    function scheduleRefresh(running) {
      if (refreshTimer) clearTimeout(refreshTimer);
      refreshTimer = setTimeout(refresh, running ? 180 : 1000);
    }
    function drawHistogram() {
      const {ctx, width, height} = fitCanvas("histogram");
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, width, height);
      const pad = {left: 58, right: 24, top: 36, bottom: 44};
      const plotW = Math.max(10, width - pad.left - pad.right);
      const plotH = Math.max(10, height - pad.top - pad.bottom);
      ctx.fillStyle = "#1e252e";
      ctx.font = "600 13px system-ui";
      ctx.textAlign = "left";
      ctx.fillText("Distribution des tailles des entites", pad.left, 18);
      ctx.font = "12px system-ui";
      ctx.fillStyle = "#66717f";
      ctx.fillText("abscisse logarithmique · taille = actif total", pad.left + 220, 18);
      ctx.strokeStyle = "#d8dee6";
      for (let i = 0; i <= 4; i++) {
        const y = pad.top + plotH * i / 4;
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(width - pad.right, y); ctx.stroke();
      }
      ctx.strokeStyle = "#1e252e";
      ctx.beginPath();
      ctx.moveTo(pad.left, pad.top);
      ctx.lineTo(pad.left, pad.top + plotH);
      ctx.lineTo(pad.left + plotW, pad.top + plotH);
      ctx.stroke();
      if (!histogram || !histogram.bins || histogram.bins.length === 0) {
        ctx.fillStyle = "#66717f";
        ctx.textAlign = "center";
        ctx.fillText("Aucune taille strictement positive a afficher.", width / 2, height / 2);
        return;
      }
      const maxCount = Math.max(1, ...histogram.bins.map(b => b.count));
      const barGap = 2;
      const barW = Math.max(2, plotW / histogram.bins.length - barGap);
      histogram.bins.forEach((bin, i) => {
        const x = pad.left + i * (plotW / histogram.bins.length);
        const barH = (bin.count / maxCount) * plotH;
        const y = pad.top + plotH - barH;
        ctx.fillStyle = "#2f6f73";
        ctx.fillRect(x, y, barW, barH);
      });
      ctx.fillStyle = "#66717f";
      ctx.font = "12px system-ui";
      ctx.textAlign = "left";
      ctx.fillText(fmt(histogram.min), pad.left, height - 18);
      ctx.textAlign = "right";
      ctx.fillText(fmt(histogram.max), pad.left + plotW, height - 18);
      ctx.textAlign = "center";
      ctx.fillText(`${histogram.count} entites vivantes`, pad.left + plotW / 2, height - 18);
      ctx.save();
      ctx.translate(18, pad.top + plotH / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.fillText("effectif", 0, 0);
      ctx.restore();
    }
    async function play() {
      try {
        const delay = Number(document.getElementById("delay").value || 50) / 1000;
        await api("/api/play", {delay_seconds: delay});
        setStatus("Simulation lancee.", "ok");
        await refresh();
      } catch (error) {
        setStatus(`Erreur play: ${error.message}`, "error");
      }
    }
    async function pause() {
      try { await api("/api/pause", {}); setStatus("Pause.", "ok"); await refresh(); }
      catch (error) { setStatus(`Erreur pause: ${error.message}`, "error"); }
    }
    async function stopRun() {
      try { await api("/api/stop", {}); setStatus("Stop.", "ok"); await refresh(); }
      catch (error) { setStatus(`Erreur stop: ${error.message}`, "error"); }
    }
    async function wipeZero() {
      try { await api("/api/wipe_zero", {}); setStatus("Simulation wipee a 0.", "ok"); await refresh(); }
      catch (error) { setStatus(`Erreur wipe: ${error.message}`, "error"); }
    }
    async function stepOnce() {
      try { await api("/api/step", {n_steps: 1}); setStatus("Un pas execute.", "ok"); await refresh(); }
      catch (error) { setStatus(`Erreur step: ${error.message}`, "error"); }
    }
    async function runBlock(n) {
      try { await api("/api/step", {n_steps: n}); setStatus(`${n} pas executes.`, "ok"); await refresh(); }
      catch (error) { setStatus(`Erreur run: ${error.message}`, "error"); }
    }
    async function updateParam(name, inputId, scope) {
      try {
        const value = parseInputValue(inputId);
        const allow = document.getElementById("risky").checked;
        setRowStatus(inputId, "application...", "warn");
        const data = await api("/api/update", {updates: {[name]: value}, scope: scope, allow_risky: allow});
        const refused = data.result?.refused || [];
        if (refused.length) throw new Error(summarizeRefusals(refused));
        setRowStatus(inputId, `${scope}: ok`, "ok");
        setStatus(`${name} = ${fmt(value)} applique (${scope}).`, "ok");
        releaseUi();
        await refresh();
      } catch (error) {
        setRowStatus(inputId, error.message, "error");
        setStatus(`Erreur ${name}: ${error.message}`, "error");
      }
    }
    async function updateEntities(name, inputId, scope) {
      try {
        const value = parseInputValue(inputId);
        const allow = document.getElementById("entityRisky").checked;
        setRowStatus(inputId, "application...", "warn");
        const data = await api("/api/entity_update", {updates: {[name]: value}, scope: scope, allow_risky: allow});
        const refused = data.result?.refused || [];
        if (refused.length) throw new Error(summarizeRefusals(refused));
        setRowStatus(inputId, `${scope}: ok`, "ok");
        setStatus(`${name} = ${fmt(value)} applique (${scope}).`, "ok");
        releaseUi();
        await refresh();
      } catch (error) {
        setRowStatus(inputId, error.message, "error");
        setStatus(`Erreur ${name}: ${error.message}`, "error");
      }
    }
    async function runScenario() {
      try {
        const scenario = JSON.parse(document.getElementById("scenario").value);
        const data = await api("/api/run_scenario", {scenario, allow_risky: true});
        document.getElementById("log").textContent = JSON.stringify(data.journal, null, 2);
        setStatus("Scenario execute.", "ok");
        await refresh();
      } catch (error) {
        setStatus(`Erreur scenario: ${error.message}`, "error");
      }
    }
    async function exportJournal() {
      try {
        const data = await api("/api/export_journal");
        document.getElementById("log").textContent = JSON.stringify(data, null, 2);
      } catch (error) {
        setStatus(`Erreur export journal: ${error.message}`, "error");
      }
    }
    async function saveSimulation() {
      try {
        const data = await api("/api/export_simulation", {label: "interactive_ui", make_figures: true});
        document.getElementById("log").textContent = JSON.stringify(data, null, 2);
        setStatus("Simulation sauvegardee.", "ok");
      } catch (error) {
        setStatus(`Erreur sauvegarde: ${error.message}`, "error");
      }
    }
    new ResizeObserver(() => drawChart(latestState)).observe(document.getElementById("chartWrap"));
    new ResizeObserver(() => drawHistogram()).observe(document.getElementById("histogramWrap"));
    refresh();
  </script>
</body>
</html>
"""


class DynamicRuntimeController:
    """Controle thread-safe d'une Simulation pour une interface locale."""

    def __init__(self, config: SimulationConfig | None = None) -> None:
        self.lock = threading.RLock()
        initial_config = config or SimulationConfig()
        self.sim = Simulation(initial_config)
        self._resume_after_wipe_config = asdict(initial_config)
        self._wiped_zero = False
        self.running = False
        self.paused = False
        self._stop_event = threading.Event()
        self._runner: threading.Thread | None = None
        self.last_error: str | None = None

    def state(self) -> dict[str, Any]:
        finished = self.sim.current_step >= self.sim.config.duree_simulation
        return {
            "running": self.running,
            "paused": self.paused,
            "finished": finished,
            "last_error": self.last_error,
            "config": asdict(self.sim.config),
        }

    def entity_size_histogram(self, n_bins: int = 24) -> dict[str, Any]:
        values = [
            float(entity.actif_total)
            for entity in self.sim.active_entities()
            if entity.actif_total > 0
        ]
        if not values:
            return {"count": 0, "min": None, "max": None, "bins": []}
        import math

        vmin, vmax = min(values), max(values)
        if vmax <= vmin:
            return {
                "count": len(values),
                "min": vmin,
                "max": vmax,
                "bins": [{"low": vmin, "high": vmax, "count": len(values)}],
            }
        log_min = math.log10(vmin)
        log_max = math.log10(vmax)
        width = (log_max - log_min) / n_bins
        counts = [0] * n_bins
        for value in values:
            idx = int((math.log10(value) - log_min) / width)
            idx = min(max(idx, 0), n_bins - 1)
            counts[idx] += 1
        bins = []
        for i, count in enumerate(counts):
            low = 10 ** (log_min + i * width)
            high = 10 ** (log_min + (i + 1) * width)
            bins.append({"low": low, "high": high, "count": count})
        return {"count": len(values), "min": vmin, "max": vmax, "bins": bins}

    def observation_payload(self) -> dict[str, Any]:
        with self.lock:
            return {
                "state": self.state(),
                "observation": self.sim.current_observation(),
                "history": [dict(row) for row in self.sim.stats],
                "entity_size_histogram": self.entity_size_histogram(),
                "journal": self.sim.intervention_journal(),
                "parameter_schema": self.sim.parameter_scope_matrix(),
                "log_file": str(LOG_FILE) if LOG_FILE is not None else None,
            }

    def reset(self, config_updates: dict[str, Any] | None = None) -> dict[str, Any]:
        self.stop()
        cfg = SimulationConfig(**dict(config_updates or {}))
        with self.lock:
            self.sim = Simulation(cfg)
            self._resume_after_wipe_config = asdict(cfg)
            self._wiped_zero = False
            self.paused = False
            self.last_error = None
            return self.observation_payload()

    def wipe_zero(self) -> dict[str, Any]:
        self.stop()
        current = asdict(self.sim.config)
        self._resume_after_wipe_config = dict(current)
        zero_config = {name: 0 for name in current}
        zero_config["seed"] = current.get("seed", 42)
        zero_config["duree_simulation"] = current.get("duree_simulation", 1000)
        zero_config["epsilon"] = current.get("epsilon", 1e-6) or 1e-6
        zero_config["freq_snapshot"] = current.get("freq_snapshot", 50) or 50
        zero_config["max_credit_iterations"] = current.get("max_credit_iterations", 100_000)
        zero_config["log_events"] = False
        with self.lock:
            self.sim = Simulation(SimulationConfig(**zero_config))
            self._wiped_zero = True
            self.paused = False
            self.last_error = None
            return self.observation_payload()

    def _restart_after_wipe_if_needed(self) -> None:
        if not self._wiped_zero:
            return
        self.sim = Simulation(SimulationConfig(**self._resume_after_wipe_config))
        self._wiped_zero = False
        self.paused = False

    def step(self, n_steps: int = 1) -> dict[str, Any]:
        if n_steps < 1:
            raise ValueError("n_steps doit etre >= 1")
        if self.running:
            raise RuntimeError("pause requise avant un step manuel")
        with self.lock:
            self._restart_after_wipe_if_needed()
            for _ in range(n_steps):
                if self.sim.current_step >= self.sim.config.duree_simulation:
                    break
                self.sim.run_step()
            return self.observation_payload()

    def _play_loop(self, delay_seconds: float, max_steps: int | None) -> None:
        steps_done = 0
        try:
            while not self._stop_event.is_set():
                with self.lock:
                    if self.sim.current_step >= self.sim.config.duree_simulation:
                        break
                    if max_steps is not None and steps_done >= max_steps:
                        break
                    self.sim.run_step()
                    steps_done += 1
                if delay_seconds > 0:
                    time.sleep(delay_seconds)
                else:
                    time.sleep(0)
        except Exception as exc:
            self.last_error = str(exc)
            LOGGER.exception("play loop crashed at step %s", getattr(self.sim, "current_step", None))
        finally:
            self.running = False

    def play(self, delay_seconds: float = 0.05, max_steps: int | None = None) -> dict[str, Any]:
        if self.running:
            return self.observation_payload()
        with self.lock:
            self._restart_after_wipe_if_needed()
        if self.sim.current_step >= self.sim.config.duree_simulation:
            self.paused = False
            return self.observation_payload()
        self._stop_event.clear()
        self.paused = False
        self.running = True
        self.last_error = None
        self._runner = threading.Thread(
            target=self._play_loop,
            args=(max(0.0, delay_seconds), max_steps),
            daemon=True,
        )
        self._runner.start()
        return self.observation_payload()

    def pause(self) -> dict[str, Any]:
        self._stop_event.set()
        if self._runner and self._runner.is_alive():
            self._runner.join(timeout=3.0)
        self.running = False
        self.paused = True
        return self.observation_payload()

    def stop(self) -> dict[str, Any]:
        self._stop_event.set()
        if self._runner and self._runner.is_alive():
            self._runner.join(timeout=3.0)
        self.running = False
        self.paused = False
        with self.lock:
            self.sim.request_stop()
            return self.observation_payload()

    def update_parameters(
        self,
        updates: dict[str, Any],
        allow_risky: bool = False,
        scope: str = "global_config",
    ) -> dict[str, Any]:
        with self.lock:
            LOGGER.info("parameter update requested scope=%s allow_risky=%s updates=%s", scope, allow_risky, updates)
            result = self.sim.apply_parameter_updates(
                updates,
                allow_risky=allow_risky,
                scope=scope,
                source="interactive_ui",
            )
            if result.get("refused"):
                LOGGER.warning("parameter update refused: %s", result["refused"])
            else:
                LOGGER.info("parameter update applied: %s", result.get("applied"))
            return {
                "result": result,
                "state": self.state(),
                "observation": self.sim.current_observation(),
                "journal": self.sim.intervention_journal(),
            }

    def update_entities(
        self,
        updates: dict[str, Any],
        allow_risky: bool = False,
        scope: str = "existing_entities",
    ) -> dict[str, Any]:
        with self.lock:
            LOGGER.info("entity update requested scope=%s allow_risky=%s updates=%s", scope, allow_risky, updates)
            result = self.sim.apply_entity_updates(
                updates,
                allow_risky=allow_risky,
                scope=scope,
                source="interactive_ui",
            )
            if result.get("refused"):
                LOGGER.warning("entity update refused: %s", result["refused"])
            else:
                LOGGER.info("entity update applied: %s", result.get("applied"))
            return {
                "result": result,
                "state": self.state(),
                "observation": self.sim.current_observation(),
                "journal": self.sim.intervention_journal(),
            }

    def run_reproducible_scenario(self, scenario: dict[str, Any], allow_risky: bool = False) -> dict[str, Any]:
        self.stop()
        sim = run_scenario(scenario, allow_risky=allow_risky)
        with self.lock:
            self.sim = sim
            self.paused = False
            self.last_error = None
            return {
                "state": self.state(),
                "observation": self.sim.current_observation(),
                "summary": self.sim.summary(),
                "journal": self.sim.intervention_journal(),
            }

    def export_journal_as_scenario(self) -> dict[str, Any]:
        with self.lock:
            journal = self.sim.intervention_journal()
            interventions = []
            for entry in journal["applied_updates"]:
                if entry.get("parameter") in {"entity_alpha", "future_entity_alpha"}:
                    interventions.append({
                        "step": entry["step"],
                        "entity_updates": entry["operation"],
                        "scope": entry["scope"],
                        "selector": entry.get("selector", "alive"),
                        "comment": entry.get("comment") or f"exported from {entry.get('source')}",
                    })
                else:
                    interventions.append({
                        "step": entry["step"],
                        "parameter": entry["parameter"],
                        "old_value_expected": entry["old_value"],
                        "new_value": entry["new_value"],
                        "scope": entry["scope"],
                        "comment": entry.get("comment") or f"exported from {entry.get('source')}",
                    })
            return {
                "name": journal.get("scenario_name") or "exported_interactive_session",
                "seed": journal["seed"],
                "initial_config": journal["initial_config"],
                "interventions": interventions,
                "journal": journal,
            }

    def export_simulation(
        self,
        label: str = "interactive_ui",
        notes: str = "",
        root: str = "simulations",
        make_figures: bool = True,
    ) -> dict[str, Any]:
        self.pause() if self.running else None
        with self.lock:
            folder = create_output_folder(self.sim.config, label=label, root=str(ROOT / root))
            csv_dir = Path(folder) / "csv"
            summary = self.sim.summary()
            save_meta(folder, self.sim.config, summary, label=label, notes=notes)
            self.sim.export_stats_csv(str(csv_dir / "stats_legeres.csv"))
            self.sim.collector.export_all(str(csv_dir), entities=self.sim.entities, loans=self.sim.loans)
            self.sim.export_intervention_journal(str(Path(folder) / "intervention_journal.json"))
            if self.sim.event_log:
                self.sim.export_event_log(str(Path(folder) / "event_log.txt"))

        figures_error = None
        if make_figures and analyze_folder is not None:
            try:
                analyze_folder(folder, label=label)
            except Exception as exc:
                figures_error = str(exc)
        elif make_figures:
            figures_error = "analysis.py non disponible"

        figures_dir = Path(folder) / "figures"
        figures = sorted(p.name for p in figures_dir.iterdir()) if figures_dir.exists() else []
        if make_figures and not figures:
            figures = write_fallback_figures(folder, [dict(row) for row in self.sim.stats])
            if figures and figures_error is None:
                figures_error = "matplotlib indisponible; graphe SVG de synthese genere"
        return {
            "folder": folder,
            "summary": summary,
            "csv_dir": str(csv_dir),
            "figures_dir": str(figures_dir),
            "figures": figures,
            "figures_error": figures_error,
        }


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def _svg_polyline(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def _scaled_points(
    rows: list[dict[str, Any]],
    key: str,
    left: float,
    top: float,
    width: float,
    height: float,
) -> list[tuple[float, float]]:
    values = [float(row.get(key) or 0.0) for row in rows]
    steps = [float(row.get("step") or 0.0) for row in rows]
    if not rows:
        return []
    xmin, xmax = min(steps), max(steps)
    ymin, ymax = min(values), max(values)
    xspan = max(1.0, xmax - xmin)
    yspan = max(1.0, ymax - ymin)
    return [
        (
            left + ((step - xmin) / xspan) * width,
            top + height - ((value - ymin) / yspan) * height,
        )
        for step, value in zip(steps, values)
    ]


def write_fallback_figures(folder: str, rows: list[dict[str, Any]]) -> list[str]:
    if len(rows) < 2:
        return []
    fig_dir = Path(folder) / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    w, h = 980, 520
    left, top, plot_w, plot_h = 70, 58, 700, 380
    colors = {
        "n_entities_alive": "#0f766e",
        "n_prets_actifs": "#7c3aed",
        "actif_total_systeme": "#b45309",
    }
    labels = {
        "n_entities_alive": "entites vivantes",
        "n_prets_actifs": "prets actifs",
        "actif_total_systeme": "actif total",
    }
    lines = []
    for key, color in colors.items():
        pts = _scaled_points(rows, key, left, top, plot_w, plot_h)
        lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.5" points="{_svg_polyline(pts)}"/>')
        lx, ly = pts[-1]
        last_value = rows[-1].get(key)
        lines.append(
            f'<circle cx="{lx:.2f}" cy="{ly:.2f}" r="4" fill="{color}"/>'
            f'<text x="{min(lx + 8, left + plot_w + 8):.2f}" y="{ly + 4:.2f}" fill="{color}" font-size="13">{labels[key]}: {last_value}</text>'
        )
    legend = []
    for i, (key, color) in enumerate(colors.items()):
        y = top + i * 24
        legend.append(f'<line x1="805" y1="{y}" x2="834" y2="{y}" stroke="{color}" stroke-width="3"/>')
        legend.append(f'<text x="842" y="{y + 4}" fill="#1e252e" font-size="13">{labels[key]}</text>')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="{left}" y="28" fill="#1e252e" font-family="system-ui, sans-serif" font-size="18" font-weight="700">Evolution pas a pas</text>
  <text x="{left + 170}" y="28" fill="#66717f" font-family="system-ui, sans-serif" font-size="13">series normalisees sur leur propre plage</text>
  <g stroke="#d8dee6" stroke-width="1">
    {''.join(f'<line x1="{left}" y1="{top + plot_h * i / 4:.2f}" x2="{left + plot_w}" y2="{top + plot_h * i / 4:.2f}"/>' for i in range(5))}
    {''.join(f'<line x1="{left + plot_w * i / 4:.2f}" y1="{top}" x2="{left + plot_w * i / 4:.2f}" y2="{top + plot_h}"/>' for i in range(5))}
  </g>
  <path d="M {left} {top} L {left} {top + plot_h} L {left + plot_w} {top + plot_h}" fill="none" stroke="#1e252e" stroke-width="1.4"/>
  <text x="{left}" y="{h - 32}" fill="#66717f" font-family="system-ui, sans-serif" font-size="13">pas {rows[0].get('step')}</text>
  <text x="{left + plot_w - 64}" y="{h - 32}" fill="#66717f" font-family="system-ui, sans-serif" font-size="13">pas {rows[-1].get('step')}</text>
  <g font-family="system-ui, sans-serif">{''.join(lines)}{''.join(legend)}</g>
</svg>
'''
    path = fig_dir / "interactive_overview.svg"
    path.write_text(svg, encoding="utf-8")
    return [path.name]


def make_handler(controller: DynamicRuntimeController):
    class Handler(BaseHTTPRequestHandler):
        server_version = "DynamicControl/0.1"

        def log_message(self, fmt: str, *args: Any) -> None:
            if getattr(self.server, "quiet", False):
                return
            LOGGER.info("access %s - %s", self.address_string(), fmt % args)

        def _send_json(self, payload: Any, status: int = 200) -> None:
            data = _json_bytes(payload)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length <= 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            return json.loads(raw)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            try:
                if path == "/":
                    data = INDEX_HTML.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                elif path == "/api/observation":
                    self._send_json(controller.observation_payload())
                elif path == "/api/export_journal":
                    self._send_json(controller.export_journal_as_scenario())
                elif path == "/api/logs":
                    query = dict(item.split("=", 1) for item in parsed.query.split("&") if "=" in item)
                    lines = int(query.get("lines", "200") or 200)
                    self._send_json({"log_file": str(LOG_FILE) if LOG_FILE else None, "lines": log_tail(lines)})
                else:
                    self._send_json({"error": "not found"}, status=404)
            except Exception as exc:
                controller.last_error = str(exc)
                LOGGER.exception("GET %s failed", path)
                self._send_json({"error": str(exc)}, status=500)

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            try:
                payload = self._read_json()
                if path == "/api/step":
                    self._send_json(controller.step(int(payload.get("n_steps", 1))))
                elif path == "/api/play":
                    self._send_json(controller.play(
                        delay_seconds=float(payload.get("delay_seconds", 0.05)),
                        max_steps=payload.get("max_steps"),
                    ))
                elif path == "/api/pause":
                    self._send_json(controller.pause())
                elif path == "/api/stop":
                    self._send_json(controller.stop())
                elif path == "/api/wipe_zero":
                    self._send_json(controller.wipe_zero())
                elif path == "/api/reset":
                    self._send_json(controller.reset(payload.get("config", {})))
                elif path == "/api/update":
                    self._send_json(controller.update_parameters(
                        payload.get("updates", {}),
                        allow_risky=bool(payload.get("allow_risky", False)),
                        scope=payload.get("scope", "global_config"),
                    ))
                elif path == "/api/entity_update":
                    self._send_json(controller.update_entities(
                        payload.get("updates", {}),
                        allow_risky=bool(payload.get("allow_risky", False)),
                        scope=payload.get("scope", "existing_entities"),
                    ))
                elif path == "/api/run_scenario":
                    self._send_json(controller.run_reproducible_scenario(
                        payload["scenario"],
                        allow_risky=bool(payload.get("allow_risky", False)),
                    ))
                elif path == "/api/export_simulation":
                    self._send_json(controller.export_simulation(
                        label=str(payload.get("label", "interactive_ui")),
                        notes=str(payload.get("notes", "")),
                        root=str(payload.get("root", "simulations")),
                        make_figures=bool(payload.get("make_figures", True)),
                    ))
                elif path == "/api/client_log":
                    LOGGER.warning("client log: %s", json.dumps(payload, ensure_ascii=False, default=str))
                    self._send_json({"ok": True})
                else:
                    self._send_json({"error": "not found"}, status=404)
            except Exception as exc:
                controller.last_error = str(exc)
                LOGGER.exception("POST %s failed", path)
                self._send_json({"error": str(exc)}, status=400)

    return Handler


def build_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    controller: DynamicRuntimeController | None = None,
    quiet: bool = False,
) -> ThreadingHTTPServer:
    controller = controller or DynamicRuntimeController()
    server = ThreadingHTTPServer((host, port), make_handler(controller))
    server.controller = controller
    server.quiet = quiet
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--open", action="store_true", help="ouvre automatiquement l'interface dans le navigateur")
    args = parser.parse_args(argv)

    log_file = configure_logging(args.port)
    config = SimulationConfig(seed=args.seed, duree_simulation=args.steps)
    controller = DynamicRuntimeController(config)
    server = build_server(args.host, args.port, controller)
    host, port = server.server_address
    url = f"http://{host}:{port}/"
    print(f"Dynamic control server: {url}")
    print(f"Logs: {log_file}")
    LOGGER.info("server starting url=%s log_file=%s", url, log_file)
    if args.open:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        controller.stop()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
