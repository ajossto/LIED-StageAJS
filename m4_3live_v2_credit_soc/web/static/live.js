"use strict";
/* M4.3Live — direct : IHM vanilla (aucune dépendance externe).
 * Contrat serveur : voir m4_3live_v2_credit_soc/web/router.py.
 * Point d'attention du contrat : GET /api/live2/sessions/<id>?since=<t> ne
 * renvoie que les lignes de `series` dont t > since. Le client accumule
 * donc les lignes localement par session (voir `getCursor`).
 */

// -- Couleurs (paire catégorielle Okabe-Ito, validée CVD/contraste) --------
const COLOR_A = "#0072B2"; // bleu : première série de chaque graphique
const COLOR_B = "#D55E00"; // vermillon : deuxième série
const COLOR_INTERVENTION = "rgba(28, 37, 43, 0.55)";

const STRING_FIELDS = {
  loan_direction: ["free", "richest_lends"],
  phase_order: ["v1", "deprec_first"],
  rate_rule: ["marginal", "surplus_share"],
  kernel_policy: ["exact_lut", "hybrid"],
};

const SCOPE_LABELS = { all: "toutes", new: "nouvelles", fraction: "fraction" };

const KERNEL_LABELS = {
  identity: "même technologie",
  same_gamma: "γ égaux (forme fermée)",
  lut: "table",
  warm: "tiède",
  newton: "Newton",
  build: "compilations",
};

const CHARTS = [
  {
    id: "chart-prod",
    legendId: "legend-prod",
    series: [{ key: "prod_tot", axis: "left", color: COLOR_A, label: "prod_tot" }],
  },
  {
    id: "chart-kpop",
    legendId: "legend-kpop",
    series: [
      { key: "K_tot", axis: "left", color: COLOR_A, label: "K_tot (capital)" },
      { key: "pop", axis: "right", color: COLOR_B, label: "pop (population)" },
    ],
  },
  {
    id: "chart-deaths",
    legendId: "legend-deaths",
    series: [
      { key: "deaths", axis: "left", color: COLOR_A, label: "deaths" },
      { key: "defaults", axis: "left", color: COLOR_B, label: "defaults" },
    ],
  },
  {
    id: "chart-market",
    legendId: "legend-market",
    series: [
      { key: "loan_volume", axis: "left", color: COLOR_A, label: "loan_volume" },
      { key: "mkt_volume_rev", axis: "left", color: COLOR_B, label: "mkt_volume_rev (sens inversé)" },
    ],
  },
  {
    id: "chart-creditors",
    legendId: "legend-creditors",
    series: [
      { key: "K_share_creditors", axis: "left", color: COLOR_A, label: "part du capital aux créancières nettes" },
      { key: "corr_marg_net", axis: "right", color: COLOR_B, label: "corr(rendement marginal, position nette)" },
    ],
  },
];

const state = {
  meta: null,
  sessions: [],
  selectedSessionId: "",
  cursors: {}, // session_id -> {since, series: [], lastT}
  lastState: null,
  pollInFlight: false,
  pollTimer: null,
  hover: {}, // chart id -> t survolé (ou null)
  redrawScheduled: false,
};

// ---------------------------------------------------------------------------
// Utilitaires
// ---------------------------------------------------------------------------
function $(id) {
  return document.getElementById(id);
}

function showError(message) {
  const node = $("message");
  if (node) {
    node.textContent = message;
  }
}

function clearMessage() {
  const node = $("message");
  if (node && node.textContent) {
    node.textContent = "";
  }
}

async function fetchJSON(url, options) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...(options || {}),
  });
  if (!response.ok) {
    let text = "";
    try {
      text = await response.text();
    } catch (err) {
      text = "";
    }
    throw new Error(text || `HTTP ${response.status}`);
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

function formatNumber(x) {
  if (x === null || x === undefined || (typeof x === "number" && Number.isNaN(x))) {
    return "—";
  }
  const num = Number(x);
  if (Number.isInteger(num)) {
    return num.toLocaleString("fr-FR");
  }
  const abs = Math.abs(num);
  if (abs !== 0 && (abs < 0.001 || abs >= 1e6)) {
    return num.toExponential(3);
  }
  return num.toLocaleString("fr-FR", { maximumFractionDigits: abs < 1 ? 4 : 2 });
}

function formatExponential(x) {
  if (x === null || x === undefined || Number.isNaN(x)) {
    return "—";
  }
  return Number(x).toExponential(3);
}

function formatPercent(x) {
  if (x === null || x === undefined || Number.isNaN(x)) {
    return "—";
  }
  return `${Number(x).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} %`;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text == null ? "" : String(text);
  return div.innerHTML;
}

// ---------------------------------------------------------------------------
// Chargement des métadonnées
// ---------------------------------------------------------------------------
async function loadMeta() {
  const meta = await fetchJSON("/api/live2/meta");
  state.meta = meta;
  buildFreshForm(meta);
  buildResumeRunOptions(meta);
  buildIntervenParamOptions(meta);
  clearMessage();
}

function buildFreshForm(meta) {
  const container = $("fresh-param-fields");
  container.innerHTML = "";
  meta.create_fields.forEach((field) => {
    const wrap = document.createElement("div");
    wrap.className = "field-item";
    const label = document.createElement("label");
    label.setAttribute("for", `field-${field}`);
    label.textContent = field;
    const info = meta.params[field];
    if (info && info.note) {
      label.title = info.note;
    }
    wrap.appendChild(label);

    let input;
    if (STRING_FIELDS[field]) {
      input = document.createElement("select");
      STRING_FIELDS[field].forEach((option) => {
        const opt = document.createElement("option");
        opt.value = option;
        opt.textContent = option;
        input.appendChild(opt);
      });
      input.value = meta.defaults[field];
    } else {
      input = document.createElement("input");
      input.type = "number";
      input.step = "any";
      input.value = meta.defaults[field];
    }
    input.id = `field-${field}`;
    input.dataset.field = field;
    wrap.appendChild(input);
    container.appendChild(wrap);
  });
}

function buildResumeRunOptions(meta) {
  const select = $("resume-run-select");
  select.innerHTML = "";
  if (!meta.runs.length) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "— aucun run M4.3 stocké —";
    select.appendChild(opt);
    return;
  }
  meta.runs.forEach((run) => {
    const opt = document.createElement("option");
    opt.value = run.run_id;
    opt.textContent = run.label ? `${run.run_id} — ${run.label}` : run.run_id;
    select.appendChild(opt);
  });
}

function buildIntervenParamOptions(meta) {
  const select = $("intervene-param");
  select.innerHTML = "";
  Object.keys(meta.params).forEach((param) => {
    const opt = document.createElement("option");
    opt.value = param;
    opt.textContent = param;
    select.appendChild(opt);
  });
  updateInterveneScopeOptions();
}

function updateInterveneScopeOptions() {
  const meta = state.meta;
  if (!meta) return;
  const param = $("intervene-param").value;
  const info = meta.params[param];
  const scopeSelect = $("intervene-scope");
  const previous = scopeSelect.value;
  scopeSelect.innerHTML = "";
  (info.scopes || []).forEach((scope) => {
    const opt = document.createElement("option");
    opt.value = scope;
    opt.textContent = SCOPE_LABELS[scope] || scope;
    scopeSelect.appendChild(opt);
  });
  if (info.scopes.includes(previous)) {
    scopeSelect.value = previous;
  }
  renderDegenerateAndNote(info);
  updatePhiVisibility();
}

function renderDegenerateAndNote(info) {
  const degenerateBlock = $("degenerate-block");
  const noteBlock = $("note-block");
  if (info.degenerate) {
    degenerateBlock.textContent = info.degenerate;
    degenerateBlock.classList.remove("hidden");
  } else {
    degenerateBlock.textContent = "";
    degenerateBlock.classList.add("hidden");
  }
  if (info.note) {
    noteBlock.textContent = info.note;
    noteBlock.classList.remove("hidden");
  } else {
    noteBlock.textContent = "";
    noteBlock.classList.add("hidden");
  }
}

function updatePhiVisibility() {
  const scope = $("intervene-scope").value;
  const wrap = $("phi-wrap");
  if (scope === "fraction") {
    wrap.classList.remove("hidden");
  } else {
    wrap.classList.add("hidden");
  }
}

// ---------------------------------------------------------------------------
// Sessions : liste et sélection
// ---------------------------------------------------------------------------
async function refreshSessions() {
  // Ne PAS effacer #message ici non plus : appelé par le minuteur de
  // rafraîchissement (5 s) en arrière-plan, en plus du bouton explicite.
  try {
    const list = await fetchJSON("/api/live2/sessions");
    state.sessions = list;
    populateSessionSelect(list);
  } catch (err) {
    showError(err.message);
  }
}

function populateSessionSelect(list) {
  const select = $("session-select");
  const previous = select.value;
  select.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "— aucune session sélectionnée —";
  select.appendChild(placeholder);
  list.forEach((session) => {
    const opt = document.createElement("option");
    opt.value = session.session_id;
    const label = session.label || session.session_id;
    opt.textContent = `${label} — t=${session.t}/${session.T} — ${session.status}`;
    select.appendChild(opt);
  });
  if (list.some((s) => s.session_id === previous)) {
    select.value = previous;
  } else if (list.some((s) => s.session_id === state.selectedSessionId)) {
    select.value = state.selectedSessionId;
  }
}

function selectSession(sessionId) {
  state.selectedSessionId = sessionId;
  const select = $("session-select");
  if (select.value !== sessionId) {
    select.value = sessionId;
  }
  if (sessionId) {
    clearMessage();
    pollOnce().then(scheduleNextPoll);
  } else {
    resetDisplays();
  }
}

function getCursor(sessionId) {
  if (!state.cursors[sessionId]) {
    state.cursors[sessionId] = { since: 0, series: [], lastT: 0 };
  }
  return state.cursors[sessionId];
}

// ---------------------------------------------------------------------------
// Sondage de l'état d'une session
// ---------------------------------------------------------------------------
async function fetchSessionState(sessionId) {
  const cursor = getCursor(sessionId);
  const data = await fetchJSON(
    `/api/live2/sessions/${encodeURIComponent(sessionId)}?since=${cursor.since}`
  );
  // Sécurité : si le t reçu est inférieur au dernier accumulé (changement de
  // session côté serveur), on repart de zéro (voir docstring de fichier).
  if (data.t < cursor.lastT) {
    cursor.series = [];
    cursor.since = 0;
  }
  if (Array.isArray(data.series) && data.series.length) {
    cursor.series = cursor.series.concat(data.series);
    cursor.since = data.series[data.series.length - 1].t;
  }
  cursor.lastT = data.t;
  if (sessionId === state.selectedSessionId) {
    renderAll(data, cursor.series);
  }
}

async function pollOnce() {
  if (!state.selectedSessionId || state.pollInFlight) {
    return;
  }
  state.pollInFlight = true;
  try {
    // Ne PAS effacer #message ici : ce sondage tourne en arrière-plan
    // toutes les 500 ms à 2 s, et écraserait silencieusement un message
    // d'erreur affiché par une action utilisateur juste avant (voir
    // clearMessage() dans postAction / createFreshSession / etc., qui
    // sont les seuls points qui doivent effacer une erreur affichée).
    await fetchSessionState(state.selectedSessionId);
  } catch (err) {
    showError(err.message);
  } finally {
    state.pollInFlight = false;
  }
}

function pollDelay() {
  const s = state.lastState;
  if (!s) return 2000;
  const advancing = s.running && !s.paused && s.status === "ok";
  return advancing ? 500 : 2000;
}

function scheduleNextPoll() {
  if (state.pollTimer) {
    clearTimeout(state.pollTimer);
  }
  state.pollTimer = setTimeout(async () => {
    await pollOnce();
    scheduleNextPoll();
  }, pollDelay());
}

// ---------------------------------------------------------------------------
// Rendu de l'état
// ---------------------------------------------------------------------------
function resetDisplays() {
  state.lastState = null;
  $("status-t").textContent = "—";
  $("status-status").textContent = "—";
  $("status-paused").textContent = "—";
  $("status-sps").textContent = "—";
  $("status-pending").textContent = "—";
  $("status-directory").textContent = "";
  $("banner-area").innerHTML = "";
  $("divergence-panel").classList.add("hidden");
  $("default-A-value").textContent = "—";
  $("default-gamma-value").textContent = "—";
  $("mean-A-value").textContent = "—";
  $("mean-gamma-value").textContent = "—";
  $("tech-table").querySelector("tbody").innerHTML = "";
  $("cohort-table").querySelector("tbody").innerHTML = "";
  $("journal-table").querySelector("tbody").innerHTML = "";
  $("kernel-counters").innerHTML = "";
  CHARTS.forEach((chart) => {
    chart._rows = [];
    chart._journal = [];
    renderLegend(chart);
    drawChart(chart);
  });
}

function renderAll(data, seriesAccum) {
  state.lastState = data;
  renderStatus(data);
  renderBanners(data);
  renderDivergence(data);
  renderInterveneDefaults(data);
  renderTechTable(data, seriesAccum);
  renderCohortTable(data);
  renderJournalTable(data);
  renderKernel(data);
  renderCharts(data, seriesAccum);
}

function renderStatus(data) {
  $("status-t").textContent = `${data.t} / ${data.T}`;
  $("status-status").textContent = data.status;
  $("status-paused").textContent = data.paused ? "en pause" : data.running ? "en lecture" : "arrêtée";
  $("status-sps").textContent = formatNumber(data.steps_per_second);
  $("status-pending").textContent = String(data.pending);
  $("status-directory").textContent = data.directory ? `Répertoire : ${data.directory}` : "";
}

function renderBanners(data) {
  const area = $("banner-area");
  area.innerHTML = "";
  if (data.status === "extinction" || data.status === "explosion") {
    const div = document.createElement("div");
    div.className = "banner stop";
    div.textContent =
      data.status === "extinction"
        ? "Simulation terminée : extinction"
        : "Simulation terminée : explosion";
    area.appendChild(div);
  }
  if (data.error) {
    const div = document.createElement("div");
    div.className = "banner error";
    div.textContent = `Erreur : ${data.error}`;
    area.appendChild(div);
  }
  if (data.origin && data.origin.mode === "resume" && data.origin.warning) {
    const div = document.createElement("div");
    div.className = "note";
    div.textContent = data.origin.warning;
    area.appendChild(div);
  }
}

function renderDivergence(data) {
  const panel = $("divergence-panel");
  const divergence = data.divergence;
  if (!divergence) {
    panel.classList.add("hidden");
    return;
  }
  panel.classList.remove("hidden");
  $("div-n-compared").textContent = String(divergence.n_compared);
  const identical = $("div-bit-identical");
  if (divergence.bit_identical) {
    identical.textContent = "identique bit à bit";
    identical.className = "status-ok";
  } else {
    identical.textContent = "DIVERGENT";
    identical.className = "status-bad";
  }
  $("div-max-relative").textContent = formatExponential(divergence.max_relative);

  const fdBlock = $("div-first-difference");
  if (divergence.first_difference) {
    fdBlock.classList.remove("hidden");
    const fd = divergence.first_difference;
    $("div-fd-t").textContent = String(fd.t);
    $("div-fd-column").textContent = fd.column;
    $("div-fd-obtained").textContent = formatNumber(fd.obtained);
    $("div-fd-expected").textContent = formatNumber(fd.expected);
  } else {
    fdBlock.classList.add("hidden");
  }
}

function renderInterveneDefaults(data) {
  $("default-A-value").textContent = formatNumber(data.default_A);
  $("default-gamma-value").textContent = formatNumber(data.default_gamma);
}

function renderTechTable(data, seriesAccum) {
  const tbody = $("tech-table").querySelector("tbody");
  tbody.innerHTML = "";
  const last = seriesAccum.length ? seriesAccum[seriesAccum.length - 1] : null;
  $("mean-A-value").textContent = last ? formatNumber(last.mean_A) : "—";
  $("mean-gamma-value").textContent = last ? formatNumber(last.mean_gamma) : "—";
  const popTotal = last ? Number(last.pop) : 0;
  const prodTotal = last ? Number(last.prod_tot) : 0;
  const techs = data.tech || [];
  techs.forEach((entry) => {
    const tr = document.createElement("tr");
    const partPop = popTotal > 0 ? (Number(entry.n_alive) / popTotal) * 100 : null;
    const partProd = prodTotal !== 0 ? (Number(entry.prod) / prodTotal) * 100 : null;
    const cells = [
      String(entry.tech),
      formatNumber(entry.A),
      formatNumber(entry.gamma),
      formatNumber(entry.n_alive),
      formatPercent(partPop),
      formatNumber(entry.K),
      formatNumber(entry.prod),
      formatPercent(partProd),
    ];
    cells.forEach((value, index) => {
      const td = document.createElement("td");
      td.textContent = value;
      if (index === 0) td.classList.add("text-cell");
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  if (!techs.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 8;
    td.className = "text-cell";
    td.textContent = "Pas encore de données de technologies.";
    tr.appendChild(td);
    tbody.appendChild(tr);
  }
}

function renderCohortTable(data) {
  const tbody = $("cohort-table").querySelector("tbody");
  tbody.innerHTML = "";
  const rows = data.cohorts || [];
  if (!rows.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 9;
    td.className = "text-cell";
    td.textContent = "Aucune intervention appliquée pour l'instant.";
    tr.appendChild(td);
    tbody.appendChild(tr);
    return;
  }
  rows.slice().reverse().forEach((entry) => {
    const tr = document.createElement("tr");
    const cells = [
      String(entry.t),
      entry.param,
      SCOPE_LABELS[entry.scope] || entry.scope,
      formatNumber(entry.n_before),
      formatNumber(entry.mean_A_before),
      formatNumber(entry.mean_gamma_before),
      formatNumber(entry.n_after),
      formatNumber(entry.mean_A_after),
      formatNumber(entry.mean_gamma_after),
    ];
    cells.forEach((value, index) => {
      const td = document.createElement("td");
      td.textContent = value;
      if (index <= 2) td.classList.add("text-cell");
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
}

function renderJournalTable(data) {
  const tbody = $("journal-table").querySelector("tbody");
  tbody.innerHTML = "";
  const journal = (data.journal || []).slice().reverse();
  journal.forEach((entry) => {
    const tr = document.createElement("tr");
    const basicCells = [
      String(entry.t),
      entry.param,
      SCOPE_LABELS[entry.scope] || entry.scope,
      entry.phi === null || entry.phi === undefined ? "—" : formatNumber(entry.phi),
      formatNumber(entry.old_value),
      formatNumber(entry.value),
      String(entry.n_selected),
    ];
    basicCells.forEach((value, index) => {
      const td = document.createElement("td");
      td.textContent = value;
      if (index === 1) td.classList.add("text-cell");
      tr.appendChild(td);
    });

    const noteTd = document.createElement("td");
    noteTd.classList.add("text-cell");
    noteTd.textContent = entry.note || "";
    tr.appendChild(noteTd);

    const idsTd = document.createElement("td");
    idsTd.classList.add("text-cell");
    if (entry.selected_ids && entry.selected_ids.length) {
      const details = document.createElement("details");
      const summary = document.createElement("summary");
      summary.textContent = "voir les identifiants";
      details.appendChild(summary);
      const list = document.createElement("div");
      list.className = "ids-list";
      list.textContent = entry.selected_ids.join(", ");
      details.appendChild(list);
      idsTd.appendChild(details);
    } else {
      idsTd.textContent = "—";
    }
    tr.appendChild(idsTd);

    tbody.appendChild(tr);
  });
  if (!journal.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 9;
    td.className = "text-cell";
    td.textContent = "Aucune intervention pour cette session.";
    tr.appendChild(td);
    tbody.appendChild(tr);
  }
}

function renderKernel(data) {
  const container = $("kernel-counters");
  container.innerHTML = "";
  const kernel = data.kernel || {};
  Object.keys(KERNEL_LABELS).forEach((key) => {
    const div = document.createElement("div");
    div.className = "live-metric";
    const span = document.createElement("span");
    span.textContent = KERNEL_LABELS[key];
    const strong = document.createElement("strong");
    strong.textContent = key in kernel ? formatNumber(kernel[key]) : "—";
    div.appendChild(span);
    div.appendChild(strong);
    container.appendChild(div);
  });
}

// ---------------------------------------------------------------------------
// Graphiques canvas
// ---------------------------------------------------------------------------
function renderCharts(data, seriesAccum) {
  const journal = data.journal || [];
  CHARTS.forEach((chart) => {
    chart._rows = seriesAccum;
    chart._journal = journal;
    renderLegend(chart);
    drawChart(chart);
  });
}

function renderLegend(chart) {
  const legend = $(chart.legendId);
  if (!legend) return;
  const singleAxis = chart.series.every((s) => s.axis === chart.series[0].axis);
  legend.innerHTML = "";
  chart.series.forEach((spec) => {
    const span = document.createElement("span");
    const swatch = document.createElement("span");
    swatch.className = "swatch";
    swatch.style.background = spec.color;
    span.appendChild(swatch);
    const axisText = singleAxis
      ? "axe unique"
      : spec.axis === "left"
      ? "axe gauche"
      : "axe droit";
    span.appendChild(document.createTextNode(`${spec.label} (${axisText})`));
    legend.appendChild(span);
  });
}

function computeExtent(values) {
  if (!values.length) return [0, 1];
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [0, 1];
  if (min === max) {
    min -= Math.abs(min) * 0.05 || 1;
    max += Math.abs(max) * 0.05 || 1;
  }
  const pad = (max - min) * 0.06;
  // Toutes les grandeurs tracées ici sont positives ou nulles (production,
  // capital, effectifs, volumes, comptages). On ne laisse donc pas la marge
  // basse afficher une borne négative : elle ferait lire un axe qui ne
  // correspond à aucune valeur possible.
  const low = min >= 0 ? Math.max(0, min - pad) : min - pad;
  return [low, max + pad];
}

function drawChart(chart) {
  const canvas = $(chart.id);
  if (!canvas) return;
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const w = Math.max(1, Math.round(rect.width));
  const h = Math.max(1, Math.round(rect.height || 210));
  canvas.width = Math.round(w * dpr);
  canvas.height = Math.round(h * dpr);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  const rows = chart._rows || [];
  const journal = chart._journal || [];

  if (!rows.length) {
    ctx.fillStyle = "#66757f";
    ctx.font = "13px sans-serif";
    ctx.fillText("Pas encore de données.", 12, h / 2);
    chart._layout = null;
    return;
  }

  const singleAxis = chart.series.every((s) => s.axis === chart.series[0].axis);
  const axes = {};
  if (singleAxis) {
    const all = [];
    chart.series.forEach((s) => rows.forEach((r) => all.push(Number(r[s.key]))));
    axes.left = computeExtent(all);
    axes.right = axes.left;
  } else {
    ["left", "right"].forEach((axis) => {
      const specs = chart.series.filter((s) => s.axis === axis);
      const all = [];
      specs.forEach((s) => rows.forEach((r) => all.push(Number(r[s.key]))));
      axes[axis] = computeExtent(all);
    });
  }

  const padLeft = 60;
  const padRight = singleAxis ? 14 : 60;
  const padTop = 12;
  const padBottom = 26;
  const plotW = Math.max(1, w - padLeft - padRight);
  const plotH = Math.max(1, h - padTop - padBottom);
  const tMin = rows[0].t;
  const tMax = rows[rows.length - 1].t;
  const xScale = (t) => padLeft + (tMax === tMin ? 0 : ((t - tMin) / (tMax - tMin)) * plotW);
  const yScale = (v, axis) => {
    const [mn, mx] = axes[axis];
    const denom = mx - mn || 1;
    return padTop + (1 - (v - mn) / denom) * plotH;
  };

  // Cadre
  ctx.strokeStyle = "#dccfb8";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padLeft, padTop);
  ctx.lineTo(padLeft, padTop + plotH);
  ctx.lineTo(padLeft + plotW, padTop + plotH);
  ctx.stroke();
  if (!singleAxis) {
    ctx.beginPath();
    ctx.moveTo(padLeft + plotW, padTop);
    ctx.lineTo(padLeft + plotW, padTop + plotH);
    ctx.stroke();
  }

  // Marqueurs d'intervention
  journal.forEach((entry) => {
    if (entry.t < tMin || entry.t > tMax) return;
    const x = xScale(entry.t);
    ctx.save();
    ctx.strokeStyle = COLOR_INTERVENTION;
    ctx.setLineDash([4, 3]);
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, padTop);
    ctx.lineTo(x, padTop + plotH);
    ctx.stroke();
    ctx.restore();
    ctx.save();
    ctx.fillStyle = "#1c252b";
    ctx.font = "9px sans-serif";
    ctx.translate(Math.min(x + 2, padLeft + plotW - 2), padTop + 9);
    ctx.textAlign = "left";
    ctx.fillText(entry.param, 0, 0);
    ctx.restore();
  });

  // Séries
  chart.series.forEach((spec) => {
    ctx.strokeStyle = spec.color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    rows.forEach((r, i) => {
      const x = xScale(r.t);
      const y = yScale(Number(r[spec.key]), spec.axis);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  });

  // Étiquettes min/max axe Y
  ctx.fillStyle = "#1c252b";
  ctx.font = "11px sans-serif";
  ctx.textAlign = "right";
  ctx.fillText(formatNumber(axes.left[1]), padLeft - 6, padTop + 9);
  ctx.fillText(formatNumber(axes.left[0]), padLeft - 6, padTop + plotH + 2);
  if (!singleAxis) {
    ctx.textAlign = "left";
    ctx.fillText(formatNumber(axes.right[1]), padLeft + plotW + 6, padTop + 9);
    ctx.fillText(formatNumber(axes.right[0]), padLeft + plotW + 6, padTop + plotH + 2);
  }

  // Bornes de t sur l'axe X
  ctx.textAlign = "left";
  ctx.fillText(`t=${tMin}`, padLeft, padTop + plotH + 18);
  ctx.textAlign = "right";
  ctx.fillText(`t=${tMax}`, padLeft + plotW, padTop + plotH + 18);

  chart._layout = { padLeft, padRight, padTop, padBottom, plotW, plotH, tMin, tMax, axes, singleAxis, w, h };

  const hoverT = state.hover[chart.id];
  if (hoverT != null) {
    drawHoverOverlay(ctx, chart, rows, hoverT);
  }
}

function nearestRow(rows, t) {
  let best = rows[0];
  let bestDist = Math.abs(rows[0].t - t);
  for (let i = 1; i < rows.length; i += 1) {
    const dist = Math.abs(rows[i].t - t);
    if (dist < bestDist) {
      best = rows[i];
      bestDist = dist;
    }
  }
  return best;
}

function drawHoverOverlay(ctx, chart, rows, hoverT) {
  const layout = chart._layout;
  if (!layout) return;
  const row = nearestRow(rows, hoverT);
  const x = layout.padLeft + (layout.tMax === layout.tMin ? 0 : ((row.t - layout.tMin) / (layout.tMax - layout.tMin)) * layout.plotW);

  ctx.save();
  ctx.strokeStyle = "#294c60";
  ctx.lineWidth = 1;
  ctx.setLineDash([2, 2]);
  ctx.beginPath();
  ctx.moveTo(x, layout.padTop);
  ctx.lineTo(x, layout.padTop + layout.plotH);
  ctx.stroke();
  ctx.restore();

  const lines = [`t = ${row.t}`];
  chart.series.forEach((spec) => {
    lines.push(`${spec.label} : ${formatNumber(Number(row[spec.key]))}`);
  });
  ctx.font = "11px sans-serif";
  const textWidth = Math.max(...lines.map((l) => ctx.measureText(l).width)) + 12;
  const boxH = lines.length * 14 + 8;
  let boxX = x + 8;
  if (boxX + textWidth > layout.w - 4) {
    boxX = x - textWidth - 8;
  }
  const boxY = layout.padTop + 4;
  ctx.fillStyle = "rgba(255, 253, 249, 0.95)";
  ctx.strokeStyle = "#dccfb8";
  ctx.lineWidth = 1;
  ctx.fillRect(boxX, boxY, textWidth, boxH);
  ctx.strokeRect(boxX, boxY, textWidth, boxH);
  ctx.fillStyle = "#1c252b";
  ctx.textAlign = "left";
  lines.forEach((line, i) => {
    ctx.fillText(line, boxX + 6, boxY + 14 + i * 14);
  });
}

function scheduleRedraw(chart) {
  if (chart._redrawScheduled) return;
  chart._redrawScheduled = true;
  requestAnimationFrame(() => {
    chart._redrawScheduled = false;
    drawChart(chart);
  });
}

function attachChartInteractions() {
  CHARTS.forEach((chart) => {
    const canvas = $(chart.id);
    if (!canvas) return;
    canvas.addEventListener("mousemove", (ev) => {
      const layout = chart._layout;
      if (!layout) return;
      const rect = canvas.getBoundingClientRect();
      const x = ev.clientX - rect.left;
      if (x < layout.padLeft || x > layout.padLeft + layout.plotW) {
        if (state.hover[chart.id] != null) {
          state.hover[chart.id] = null;
          scheduleRedraw(chart);
        }
        return;
      }
      const frac = (x - layout.padLeft) / layout.plotW;
      const t = Math.round(layout.tMin + frac * (layout.tMax - layout.tMin));
      state.hover[chart.id] = t;
      scheduleRedraw(chart);
    });
    canvas.addEventListener("mouseleave", () => {
      state.hover[chart.id] = null;
      scheduleRedraw(chart);
    });
  });
}

function redrawAllCharts() {
  CHARTS.forEach((chart) => drawChart(chart));
}

let resizeTimer = null;
window.addEventListener("resize", () => {
  if (resizeTimer) clearTimeout(resizeTimer);
  resizeTimer = setTimeout(redrawAllCharts, 120);
});

// ---------------------------------------------------------------------------
// Actions utilisateur
// ---------------------------------------------------------------------------
async function createFreshSession() {
  const meta = state.meta;
  const parameters = {};
  meta.create_fields.forEach((field) => {
    const input = $(`field-${field}`);
    if (!input) return;
    if (STRING_FIELDS[field]) {
      parameters[field] = input.value;
    } else {
      parameters[field] = Number(input.value);
    }
  });
  const body = {
    mode: "fresh",
    label: $("create-label").value || "",
    parameters,
  };
  try {
    const descriptor = await fetchJSON("/api/live2/sessions", {
      method: "POST",
      body: JSON.stringify(body),
    });
    clearMessage();
    await refreshSessions();
    selectSession(descriptor.session_id);
  } catch (err) {
    showError(err.message);
  }
}

async function createResumeSession() {
  const runId = $("resume-run-select").value;
  if (!runId) {
    showError("Aucun run M4.3 disponible pour une reprise.");
    return;
  }
  const body = {
    mode: "resume",
    label: $("create-label").value || "",
    run_id: runId,
    t0: Number($("resume-t0").value),
  };
  try {
    const descriptor = await fetchJSON("/api/live2/sessions", {
      method: "POST",
      body: JSON.stringify(body),
    });
    clearMessage();
    await refreshSessions();
    selectSession(descriptor.session_id);
  } catch (err) {
    showError(err.message);
  }
}

async function postAction(action, body) {
  if (!state.selectedSessionId) {
    showError("Sélectionnez d'abord une session.");
    return null;
  }
  try {
    const result = await fetchJSON(
      `/api/live2/sessions/${encodeURIComponent(state.selectedSessionId)}/${action}`,
      { method: "POST", body: JSON.stringify(body || {}) }
    );
    clearMessage();
    // Rafraîchit l'état tout de suite (au lieu d'attendre jusqu'à 2 s le
    // prochain sondage programmé), puis reprogramme le minuteur : après
    // Lecture/+1 pas/etc., `state.lastState` vient d'être mis à jour et la
    // cadence (500 ms si ça avance, sinon 2 s) est donc correcte tout de
    // suite plutôt qu'au sondage suivant.
    await pollOnce();
    scheduleNextPoll();
    return result;
  } catch (err) {
    showError(err.message);
    return null;
  }
}

async function sendIntervention() {
  const param = $("intervene-param").value;
  const scope = $("intervene-scope").value;
  const value = Number($("intervene-value").value);
  const body = {
    param,
    value,
    scope,
    phi: scope === "fraction" ? Number($("intervene-phi").value) : null,
    note: $("intervene-note").value || "",
  };
  const result = await postAction("intervene", body);
  if (result) {
    $("action-feedback").textContent = `Intervention mise en file à t=${result.t_submitted} (paramètre ${result.param}, portée ${SCOPE_LABELS[result.scope] || result.scope}).`;
  }
}

async function doSnapshot() {
  const result = await postAction("snapshot", {});
  if (result && result.snapshot) {
    $("action-feedback").textContent = `Snapshot écrit : ${result.snapshot}`;
  }
}

async function doSave() {
  const result = await postAction("save", {});
  if (result && result.series) {
    $("action-feedback").textContent = `Série écrite : ${result.series}`;
  }
}

// ---------------------------------------------------------------------------
// Initialisation
// ---------------------------------------------------------------------------
function wireEvents() {
  $("btn-refresh-sessions").addEventListener("click", () => {
    clearMessage();
    refreshSessions();
  });
  $("session-select").addEventListener("change", (ev) => selectSession(ev.target.value));

  document.querySelectorAll('input[name="create-mode"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      const mode = document.querySelector('input[name="create-mode"]:checked').value;
      $("create-fresh-block").classList.toggle("hidden", mode !== "fresh");
      $("create-resume-block").classList.toggle("hidden", mode !== "resume");
    });
  });

  $("btn-create-fresh").addEventListener("click", createFreshSession);
  $("btn-create-resume").addEventListener("click", createResumeSession);

  $("btn-play").addEventListener("click", () => postAction("play", {}));
  $("btn-pause").addEventListener("click", () => postAction("pause", {}));
  $("btn-step1").addEventListener("click", () => postAction("step", { count: 1 }));
  $("btn-step10").addEventListener("click", () => postAction("step", { count: 10 }));
  $("btn-step100").addEventListener("click", () => postAction("step", { count: 100 }));
  $("btn-speed").addEventListener("click", () =>
    postAction("speed", { speed: Number($("speed-input").value) })
  );
  $("btn-extend").addEventListener("click", () =>
    postAction("extend", { steps: Number($("extend-steps").value) })
  );
  $("btn-snapshot").addEventListener("click", doSnapshot);
  $("btn-save").addEventListener("click", doSave);

  $("intervene-param").addEventListener("change", updateInterveneScopeOptions);
  $("intervene-scope").addEventListener("change", updatePhiVisibility);
  $("btn-intervene").addEventListener("click", sendIntervention);

  attachChartInteractions();
}

async function init() {
  wireEvents();
  resetDisplays();
  try {
    await loadMeta();
  } catch (err) {
    showError(err.message);
  }
  await refreshSessions();
  // Une session est adressable par URL (`/live?session=<id>`) : pratique pour
  // garder un onglet sur une session longue, et pour ouvrir la page
  // directement sur la bonne session depuis un script.
  const requested = new URLSearchParams(window.location.search).get("session");
  if (requested) {
    const select = $("session-select");
    if ([...select.options].some((option) => option.value === requested)) {
      select.value = requested;
      await selectSession(requested);
    } else {
      showError(`Session inconnue dans l'URL : ${requested}`);
    }
  }
  setInterval(refreshSessions, 5000);
  scheduleNextPoll();
}

document.addEventListener("DOMContentLoaded", init);
