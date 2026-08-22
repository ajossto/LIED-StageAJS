const state = {
  models: [],
  selectedModelId: null,
  runs: [],
  jobs: [],
  selectedRunId: null,
  scope: "active",
  currentJobId: null,
  jobPollTimer: null,
  openRunGroups: new Set(),
  runGroupsTouched: false,
  studyCampaign: "",
  studyGroup: "",
  studyBounded: false,
  studyDrop5: false,
  studyConverged: false,
  searchQuery: "",
  filterImportant: false,
  filterKeep: false,
  multiSeedMode: false,
  selectedGroupKey: null,
};

const PARAMETER_HELP = {
  lam: "Intensité moyenne λ des naissances de Poisson par pas.",
  delta: "Fraction du capital productif dépréciée à chaque pas.",
  sigma: "Volatilité du choc multiplicatif individuel, de moyenne un.",
  K0: "Capital productif attribué à chaque nouvelle entité.",
  k: "Nombre d’entités du marché local parmi lesquelles sont choisies la prêteuse et l’emprunteuse.",
  T: "Nombre maximal de pas simulés.",
  pop_max: "Seuil de sécurité sur le nombre d’entités vivantes.",
  snapshot_every: "Fréquence des instantanés individuels et réseau ; 0 conserve seulement l’état final.",
  individual_every: "Fréquence des mesures longitudinales individuelles ; 0 les désactive.",
  alpha: "Coefficient de productivité de référence. Dans les WIP récents, les entités tirent surtout alpha dans [alpha_min, alpha_max].",
  alpha_min: "Borne basse du tirage initial de productivité individuelle alpha.",
  alpha_max: "Borne haute du tirage initial de productivité individuelle alpha.",
  alpha_sigma_brownien: "Volatilité du choc temporel sur alpha. 0 = productivité individuelle fixe après la naissance.",
  seuil_ratio_liquide_passif: "Seuil de liquidité L/P pour participer au marché du crédit et conserver une réserve avant prêt ou auto-investissement.",
  theta: "Fraction de la demande optimale d'emprunt effectivement demandée. Plus theta est haut, plus le levier financier monte vite.",
  mu: "Prime minimale exigée par l'emprunteur: l'emprunt doit améliorer le gain d'au moins mu par rapport à l'auto-investissement.",
  seuil_ratio_endettement: "Plafond charges d'intérêts / revenus. 1 signifie que les intérêts dus ne doivent pas dépasser extraction + intérêts reçus.",
  fraction_taux_emprunteur: "Paramètre f du taux de transaction: r = (1-f) r*_prêteur + f r*_emprunteur. Plus f est haut, plus le taux se rapproche du rendement marginal de l'emprunteur.",
  taux_amortissement: "Part du principal remboursée à chaque pas. 0 = dette perpétuelle.",
  n_entites_initiales: "Nombre d'entités créées à t=0.",
  lambda_creation: "Intensité moyenne des naissances par pas de temps, tirée par une loi de Poisson.",
  actif_liquide_initial: "Dotation liquide initiale L de chaque nouvelle entité.",
  passif_inne_initial: "Passif inné B de chaque nouvelle entité; base minimale du bilan.",
  taux_depreciation_liquide: "Dépréciation du liquide à chaque pas.",
  taux_depreciation_endo: "Dépréciation du capital endogène issu de l'auto-investissement.",
  taux_depreciation_exo: "Dépréciation du capital financé par crédit; sert aussi à réévaluer les créances.",
  coefficient_reliquefaction: "Décote de conversion du capital endogène en liquide lors d'une contrainte de paiement.",
  fraction_auto_investissement: "Part du surplus liquide convertie en capital endogène à la fin du pas.",
  duree_simulation: "Nombre de pas de temps simulés.",
  seed: "Graine aléatoire. Même seed et mêmes paramètres donnent une trajectoire reproductible.",
  max_credit_iterations: "Limite de sécurité sur les tentatives du marché du crédit à chaque pas.",
  n_candidats_pool: "Taille locale du pool de matching crédit. k=3 est le régime WIP critique; k bas stabilise, k haut densifie le réseau.",
  epsilon: "Seuil numérique sous lequel un montant est considéré nul.",
  log_events: "Active un journal détaillé des événements. Utile pour déboguer, coûteux sur longues simulations.",
  freq_snapshot: "Fréquence des snapshots statistiques détaillés.",
};

const PARAMETER_SYMBOLS = {
  theta: "θ",
  fraction_taux_emprunteur: "f",
  mu: "μ",
  lambda_creation: "λ",
  epsilon: "ε",
  alpha: "α",
  alpha_min: "α min",
  alpha_max: "α max",
  alpha_sigma_brownien: "σ(α)",
};

const KEY_PARAMETER_NAMES = [
  "T",
  "lam",
  "sigma",
  "delta",
  "K0",
  "k",
  "pop_max",
  "snapshot_every",
  "individual_every",
  "duree_simulation",
  "seed",
  "alpha_min",
  "alpha_max",
  "alpha_sigma_brownien",
  "n_candidats_pool",
  "theta",
  "mu",
  "fraction_taux_emprunteur",
  "seuil_ratio_endettement",
  "lambda_creation",
  "fraction_auto_investissement",
  "taux_depreciation_endo",
  "taux_depreciation_exo",
  "epsilon",
];

function page() {
  return document.body.dataset.page;
}

function setMessage(message) {
  const node = document.getElementById("messages");
  if (node) {
    node.textContent = message;
  }
}

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(await response.text() || `HTTP ${response.status}`);
  }
  return response.json();
}

function currentModel() {
  return state.models.find((model) => model.model_id === state.selectedModelId);
}

function modelDisplayName(modelId) {
  return state.models.find((model) => model.model_id === modelId)?.display_name || modelId || "Modèle inconnu";
}

function renderModelForm() {
  const model = currentModel();
  const form = document.getElementById("parameter-form");
  const description = document.getElementById("model-description");
  if (!form || !description) {
    return;
  }
  if (!model) {
    form.innerHTML = "";
    description.textContent = "";
    return;
  }
  description.textContent = model.description || "";
  const groups = groupParameters(model.parameters);
  form.innerHTML = Object.entries(groups).map(([groupName, parameters], index) => `
    <details class="param-group" ${index === 0 ? "open" : ""}>
      <summary>${groupName}</summary>
      ${parameters.map(renderParameterField).join("")}
    </details>
  `).join("");
}

function renderParameterField(parameter) {
  const inputType = parameter.param_type === "bool" ? "checkbox" : parameter.param_type === "str" ? "text" : "number";
  const symbol = PARAMETER_SYMBOLS[parameter.name];
  const label = `${parameter.label || parameter.name}${symbol ? ` <span class="param-symbol">${symbol}</span>` : ""}`;
  const help = PARAMETER_HELP[parameter.name] || parameter.description || "";
  if (parameter.param_type === "bool") {
    return `<label>${label}</label>
      <div class="help">${help}</div>
      <input data-param="${parameter.name}" type="checkbox" ${parameter.default ? "checked" : ""}>`;
  }
  const min = parameter.minimum !== null ? `min="${parameter.minimum}"` : "";
  const max = parameter.maximum !== null ? `max="${parameter.maximum}"` : "";
  const step = parameter.param_type === "int" ? "1" : "any";
  return `<label>${label}</label>
    <div class="help">${help}</div>
    <input data-param="${parameter.name}" type="${inputType}" value="${parameter.default ?? ""}" ${min} ${max} step="${step}">`;
}

function groupParameters(parameters) {
  const groups = {};
  parameters.forEach((parameter) => {
    const name = parameter.name;
    let group = "Autres";
    if (["lam", "K0", "pop_max"].includes(name)) group = "Population";
    else if (["k"].includes(name)) group = "Crédit et marché";
    else if (["delta", "sigma"].includes(name)) group = "Dynamique";
    else if (["T", "snapshot_every", "individual_every"].includes(name)) group = "Exécution et mesures";
    else if (/(alpha|productiv)/.test(name)) group = "Productivité";
    else if (/(theta|mu|credit|taux|emprunt|pool|lender|ratio_endettement|liquide_passif)/.test(name)) group = "Crédit et marché";
    else if (/(creation|entites|inne_initial|liquide_initial)/.test(name)) group = "Population initiale";
    else if (/(depreciation|reliquefaction)/.test(name)) group = "Dépréciation et liquidité";
    else if (/(auto_investissement)/.test(name)) group = "Auto-investissement";
    else if (/(duree|seed|snapshot|iterations|epsilon|log_events)/.test(name)) group = "Exécution et technique";
    if (!groups[group]) groups[group] = [];
    groups[group].push(parameter);
  });
  return groups;
}

function readParameters() {
  const model = currentModel();
  const values = {};
  model.parameters.forEach((parameter) => {
    const element = document.querySelector(`[data-param="${parameter.name}"]`);
    values[parameter.name] = parameter.param_type === "bool" ? element.checked : element.value;
  });
  return values;
}

async function loadModels() {
  const modelScope = page() === "launch" ? "active" : "all";
  state.models = await fetchJSON(`/api/models?scope=${modelScope}`);
  const select = document.getElementById("model-select");
  if (!select) {
    return;
  }
  select.innerHTML = state.models.map((model) => `<option value="${model.model_id}">${model.display_name}</option>`).join("");
  if (state.models.length > 0) {
    state.selectedModelId = state.models[0].model_id;
  }
  select.addEventListener("change", () => {
    state.selectedModelId = select.value;
    renderModelForm();
  });
  renderModelForm();
}

async function loadSystemInfo() {
  const info = await fetchJSON("/api/system");
  const workerInput = document.getElementById("batch-workers");
  const cpuHint = document.getElementById("cpu-hint");
  if (workerInput && Number(workerInput.value) === 0) {
    workerInput.value = info.recommended_workers;
  }
  if (cpuHint) {
    cpuHint.textContent = `Machine détectée: ${info.cpu_count} cœurs logiques. Recommandation par défaut: ${info.recommended_workers} workers, ${info.reserved_cores} cœurs laissés libres.`;
  }
}

async function createSingleRun() {
  const payload = {
    model_id: state.selectedModelId,
    parameters: readParameters(),
    seed: parseInt(document.getElementById("single-seed").value, 10),
    label: document.getElementById("run-label").value,
  };
  const job = await fetchJSON("/api/jobs/run", { method: "POST", body: JSON.stringify(payload) });
  state.currentJobId = job.job_id;
  setMessage("Job créé. Simulation en attente de démarrage.");
  await refreshJobs();
}

async function createBatch() {
  const payload = {
    model_id: state.selectedModelId,
    parameters: readParameters(),
    run_count: parseInt(document.getElementById("batch-count").value, 10),
    max_workers: parseInt(document.getElementById("batch-workers").value, 10),
    base_seed: parseInt(document.getElementById("batch-seed").value, 10),
    label: document.getElementById("run-label").value,
  };
  const job = await fetchJSON("/api/jobs/batch", { method: "POST", body: JSON.stringify(payload) });
  state.currentJobId = job.job_id;
  setMessage("Batch créé.");
  await refreshJobs();
}

async function refreshJobs() {
  const container = document.getElementById("jobs-list");
  if (!container) {
    return;
  }
  state.jobs = await fetchJSON("/api/jobs");
  renderJobs();
  const hasActive = state.jobs.some((job) => job.status === "running" || job.status === "queued");
  if (state.jobPollTimer) {
    window.clearTimeout(state.jobPollTimer);
    state.jobPollTimer = null;
  }
  if (hasActive) {
    state.jobPollTimer = window.setTimeout(refreshJobs, 1000);
  }
}

function renderJobs() {
  const list = document.getElementById("jobs-list");
  const legacyCard = document.getElementById("job-status-card");
  const legacyBar = document.getElementById("progress-bar");
  if (!list) {
    return;
  }
  const jobs = state.jobs.slice(0, 12);
  if (!jobs.length) {
    list.innerHTML = `<div class="muted">Aucune simulation lancée depuis ce démarrage du serveur.</div>`;
    if (legacyCard) legacyCard.innerHTML = `<div class="muted">Aucun lancement en cours.</div>`;
    if (legacyBar) legacyBar.style.width = "0%";
    return;
  }
  list.innerHTML = jobs.map(renderJobCard).join("");
  list.querySelectorAll("[data-cancel-job]").forEach((button) => {
    button.addEventListener("click", async () => {
      await fetchJSON(`/api/jobs/${encodeURIComponent(button.dataset.cancelJob)}/cancel`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      await refreshJobs();
    });
  });
  list.querySelectorAll("[data-open-run]").forEach((button) => {
    button.addEventListener("click", () => {
      window.location.href = `/results?run=${encodeURIComponent(button.dataset.openRun)}`;
    });
  });

  const current = state.currentJobId
    ? state.jobs.find((job) => job.job_id === state.currentJobId)
    : state.jobs[0];
  if (current && legacyCard && legacyBar) {
    renderJob(current);
  }
}

function renderJobCard(job) {
  const active = job.status === "running" || job.status === "queued";
  const resultButtons = [
    job.run_id ? `<button class="secondary compact-button" data-open-run="${job.run_id}">Voir le résultat</button>` : "",
    ...(job.run_ids || []).slice(0, 3).map((runId) => `<button class="secondary compact-button" data-open-run="${runId}">Run ${runId.slice(-8)}</button>`),
  ].join("");
  return `
    <article class="job-card ${active ? "active" : ""}">
      <div class="job-head">
        <strong>${modelDisplayName(job.model_id)}</strong>
        <span class="pill ${job.status === "failed" ? "trash" : active ? "important" : "readonly"}">${job.status}</span>
      </div>
      <div class="run-meta">${escapeHtml(job.label || job.job_type)} | ${escapeHtml(job.created_at)}</div>
      <div>${escapeHtml(job.message || "-")}</div>
      <div class="mini-progress"><span style="width:${job.progress || 0}%"></span></div>
      <div class="run-meta">${Math.round(job.progress || 0)}%${job.error ? ` | ${escapeHtml(job.error)}` : ""}</div>
      ${renderTelemetrySummary(job)}
      ${renderJobAlerts(job.alerts)}
      ${job.telemetry && Object.keys(job.telemetry).length ? `
        <details class="live-details">
          <summary>Déroulé et bilan en direct</summary>
          ${renderTelemetryDetails(job)}
        </details>` : ""}
      ${job.logs?.length ? `<details class="job-log"><summary>Derniers logs</summary><pre>${escapeHtml(job.logs.slice(-8).join("\n"))}</pre></details>` : ""}
      <div class="inline-actions job-actions">
        ${active ? `<button class="secondary compact-button" data-cancel-job="${job.job_id}" ${job.cancel_requested ? "disabled" : ""}>${job.cancel_requested ? "Annulation demandée" : "Avorter"}</button>` : ""}
        ${resultButtons}
      </div>
    </article>
  `;
}

function renderJob(job) {
  const card = document.getElementById("job-status-card");
  const bar = document.getElementById("progress-bar");
  const cancelButton = document.getElementById("cancel-job");
  if (!card || !bar) {
    return;
  }
  bar.style.width = `${job.progress || 0}%`;
  if (cancelButton) {
    const cancellable = job.status === "running" || job.status === "queued";
    cancelButton.classList.toggle("hidden", !cancellable);
    cancelButton.disabled = !!job.cancel_requested;
    cancelButton.textContent = job.cancel_requested ? "Annulation demandée" : "Avorter la simulation";
    cancelButton.onclick = async () => {
      await fetchJSON(`/api/jobs/${encodeURIComponent(job.job_id)}/cancel`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      await refreshJobs();
    };
  }
  card.innerHTML = `
    <div><strong>${escapeHtml(modelDisplayName(job.model_id))}</strong></div>
    <div>${escapeHtml(job.message || "-")}</div>
    <div class="run-meta">Statut: ${job.status} | Progression: ${Math.round(job.progress || 0)}%</div>
    ${renderJobAlerts(job.alerts)}
    ${renderTelemetryDetails(job)}
    ${job.logs?.length ? `<div class="run-meta">${escapeHtml(job.logs.slice(-5).join("\n")).replaceAll("\n", "<br>")}</div>` : ""}
  `;
}

function renderTelemetrySummary(job) {
  const metric = job.telemetry || {};
  if (!Object.keys(metric).length) return "";
  if (metric.phase === "batch") {
    return `<div class="live-summary-grid">
      ${liveMetric("Terminées", `${metric.completed_runs ?? 0} / ${metric.total_runs ?? "-"}`)}
      ${liveMetric("Encore actives", metric.running_runs ?? "-")}
    </div>`;
  }
  return `<div class="live-summary-grid">
    ${liveMetric("Pas", `${metric.t ?? 0} / ${metric.t_total ?? "-"}`)}
    ${liveMetric("Population", metric.population !== undefined ? formatLiveNumber(metric.population) : "—")}
    ${liveMetric("Valeur nette", metric.net_worth_j !== undefined ? `${formatLiveNumber(metric.net_worth_j)} J` : "—")}
    ${liveMetric("Temps restant", formatDuration(metric.eta_seconds))}
  </div>`;
}

function renderTelemetryDetails(job) {
  const metric = job.telemetry || {};
  if (!Object.keys(metric).length) {
    return `<p class="muted">Les premières mesures arrivent après le premier pas.</p>`;
  }
  if (metric.phase === "batch") return renderTelemetrySummary(job);
  const metrics = [
    ["Phase", telemetryPhaseLabel(metric.phase)],
    ["Pas simulé", `${metric.t ?? 0} / ${metric.t_total ?? "-"}`],
    ["Temps écoulé", formatDuration(metric.elapsed_seconds, false)],
    ["Temps restant estimé", formatDuration(metric.eta_seconds)],
    ["Vitesse", metric.steps_per_second !== undefined ? `${formatLiveNumber(metric.steps_per_second)} pas/s` : "—"],
    ["Population", metric.population !== undefined ? `${formatLiveNumber(metric.population)} / ${formatLiveNumber(metric.population_limit)}` : "—"],
    ["Charge de la limite", metric.population_load_pct !== undefined ? `${metric.population_load_pct.toFixed(1)} %` : "—"],
    ["Variation population (20 pas)", signedValue(metric.population_change_20)],
    ["Prêts actifs", formatLiveNumber(metric.loans)],
    ["Capital", joules(metric.capital_j)],
    ["Valeur nette", joules(metric.net_worth_j)],
    ["Variation valeur nette (20 pas)", signedValue(metric.net_worth_change_20_j, " J")],
    ["Dette", joules(metric.debt_j)],
    ["Dette / actifs", metric.debt_assets_ratio !== undefined ? `${(100 * metric.debt_assets_ratio).toFixed(1)} %` : "—"],
    ["Naissances cumulées", formatLiveNumber(metric.births_total)],
    ["Décès cumulés / dernier pas", `${formatLiveNumber(metric.deaths_total)} / ${formatLiveNumber(metric.deaths_step)}`],
    ["Avalanches cumulées / dernier pas", `${formatLiveNumber(metric.avalanches_total)} / ${formatLiveNumber(metric.avalanches_step)}`],
    ["Avalanche max. dernier pas / run", `${formatLiveNumber(metric.max_avalanche_step)} / ${formatLiveNumber(metric.max_avalanche_seen)}`],
    ["État du modèle", metric.model_status || "—"],
  ].filter(([, value]) => value !== "— / —");
  return `
    <div class="live-metrics-grid">
      ${metrics.map(([label, value]) => liveMetric(label, value)).join("")}
    </div>
    ${renderTelemetryHistory(job.telemetry_history || [])}
  `;
}

function renderTelemetryHistory(history) {
  const rows = history.filter((item) => item.phase === "simulation").slice(-12);
  if (rows.length < 2) return "";
  return `<div class="telemetry-history-wrap">
    <div class="run-meta">12 derniers points de contrôle</div>
    <table class="telemetry-history">
      <thead><tr><th>Pas</th><th>Pop.</th><th>Prêts</th><th>Valeur nette</th><th>Décès</th><th>Avalanches</th></tr></thead>
      <tbody>${rows.map((item) => `<tr>
        <td>${formatLiveNumber(item.t)}</td>
        <td>${formatLiveNumber(item.population)}</td>
        <td>${formatLiveNumber(item.loans)}</td>
        <td>${joules(item.net_worth_j)}</td>
        <td>${formatLiveNumber(item.deaths_total)}</td>
        <td>${formatLiveNumber(item.avalanches_total)}</td>
      </tr>`).join("")}</tbody>
    </table>
  </div>`;
}

function renderJobAlerts(alerts = []) {
  if (!alerts.length) return "";
  return `<div class="job-alerts">${alerts.map((alert) => `<div>${escapeHtml(alert)}</div>`).join("")}</div>`;
}

function liveMetric(label, value) {
  return `<div class="live-metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value ?? "—")}</strong></div>`;
}

function telemetryPhaseLabel(phase) {
  return ({ initialisation: "Initialisation", simulation: "Simulation", figures: "Génération des figures", batch: "Batch" })[phase] || phase || "—";
}

function formatDuration(seconds, estimate = true) {
  if (seconds === null || seconds === undefined || !Number.isFinite(Number(seconds))) {
    return estimate ? "calcul…" : "—";
  }
  const total = Math.max(0, Math.round(Number(seconds)));
  if (total < 60) return `${total} s`;
  const minutes = Math.floor(total / 60);
  const remainder = total % 60;
  if (minutes < 60) return `${minutes} min ${remainder} s`;
  const hours = Math.floor(minutes / 60);
  return `${hours} h ${minutes % 60} min`;
}

function formatLiveNumber(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
  const number = Number(value);
  const absolute = Math.abs(number);
  if ((absolute >= 1e7) || (absolute > 0 && absolute < 0.001)) return number.toExponential(2);
  return number.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
}

function joules(value) {
  const formatted = formatLiveNumber(value);
  return formatted === "—" ? formatted : `${formatted} J`;
}

function signedValue(value, suffix = "") {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
  const number = Number(value);
  return `${number > 0 ? "+" : ""}${formatLiveNumber(number)}${suffix}`;
}

async function refreshRuns() {
  state.runs = await fetchJSON(`/api/runs?scope=${state.scope}`);
  renderRuns();
}

function renderRuns() {
  const list = document.getElementById("runs-list");
  if (!list) {
    return;
  }
  const trashActions = document.getElementById("trash-actions");
  if (trashActions) {
    trashActions.classList.toggle("hidden", state.scope !== "trash");
  }
  const hasStudy = state.runs.some((r) => r.model_id === "etude_sensibilite_27_04_wip");
  document.getElementById("study-filter")?.classList.toggle("hidden", !hasStudy);

  const afterStudyFilter = filterStudyRuns(state.runs);
  const visibleRuns = filterAllRuns(afterStudyFilter);

  if (state.multiSeedMode) {
    const groups = buildMultiSeedGroups(visibleRuns);
    list.innerHTML = renderMultiSeedGroups(groups);
    bindMultiSeedInteractions(list);
  } else {
    list.innerHTML = renderRunsGrouped(visibleRuns, { compact: list.dataset.compact === "true" });
    bindRunListInteractions(list);
  }
}

function studyGroupOf(run) {
  const sg = run.study_group;
  if (sg) return sg;
  const id = run.run_id || "";
  if (id.includes("_coupling_")) return "couplages";
  if (id.includes("_multirun_")) return "multirun";
  if (id.includes("_predictab")) return "predictabilite";
  if (id.includes("_long_run_") || id.includes("_long_probe_")) return "long_runs";
  if (id.includes("_oat_") || id.includes("_robustness_") || id.includes("_lambda_fine_")) return "oat";
  if (id.includes("sensitivity_")) return "exploratoire";
  return "direct";
}

const STUDY_GROUP_ORDER = ["exploratoire", "oat", "couplages", "multirun", "predictabilite", "long_runs", "direct"];
const STUDY_GROUP_LABELS = {
  exploratoire: "Exploration initiale",
  oat: "OAT (One-at-a-time)",
  couplages: "Couplages 2D",
  multirun: "Multi-seeds probabiliste",
  predictabilite: "Prédictabilité",
  long_runs: "Long runs",
  direct: "Simulations directes",
};

function filterStudyRuns(runs) {
  const { studyCampaign, studyGroup, studyBounded, studyDrop5, studyConverged } = state;
  if (!studyCampaign && !studyGroup && !studyBounded && !studyDrop5 && !studyConverged) return runs;
  return runs.filter((run) => {
    if (run.model_id !== "etude_sensibilite_27_04_wip") return true;
    if (studyGroup) {
      if (studyGroupOf(run) !== studyGroup) return false;
    }
    if (studyCampaign) {
      const prefix = `sensitivity_${studyCampaign}_`;
      const exact = `sensitivity_${studyCampaign}`;
      if (!run.run_id.startsWith(prefix) && run.run_id !== exact) return false;
    }
    const s = run.summary || {};
    if (studyBounded && !s.bounded_tail) return false;
    if (studyDrop5 && !s.drop_5_detected) return false;
    if (studyConverged && !s.converged) return false;
    return true;
  });
}

function filterAllRuns(runs) {
  const { searchQuery, filterImportant, filterKeep } = state;
  return runs.filter((run) => {
    if (filterImportant && !run.important) return false;
    if (filterKeep && !run.keep) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const inId = run.run_id.toLowerCase().includes(q);
      const inLabel = (run.label || "").toLowerCase().includes(q);
      if (!inId && !inLabel) return false;
    }
    return true;
  });
}

// Fingerprint d'un run pour le regroupement multi-seeds.
// Exclut : seed (top-level), _campaign, exported_at_local, executed_at_local,
// duree_simulation, log_events, freq_snapshot (non-déterministes ou hors modèle).
const PARAM_FINGERPRINT_EXCLUDE = new Set([
  "_campaign", "exported_at_local", "executed_at_local",
  "duree_simulation", "log_events", "freq_snapshot",
]);

function computeParamFingerprint(run) {
  const params = run.parameters || {};
  const filtered = Object.fromEntries(
    Object.entries(params)
      .filter(([k]) => !PARAM_FINGERPRINT_EXCLUDE.has(k) && k !== "seed")
      .map(([k, v]) => [k, typeof v === "number" ? Math.round(v * 1e9) / 1e9 : v])
  );
  const keys = Object.keys(filtered).sort();
  const parts = keys.map((k) => `${k}=${JSON.stringify(filtered[k])}`);
  return `${run.model_id}||${parts.join("|")}`;
}

function buildMultiSeedGroups(runs) {
  const groups = new Map(); // fingerprint -> {fp, model_id, params_repr, runs[]}
  for (const run of runs) {
    const fp = computeParamFingerprint(run);
    if (!groups.has(fp)) {
      groups.set(fp, { fp, model_id: run.model_id, runs: [] });
    }
    groups.get(fp).runs.push(run);
  }
  // Keep only groups with ≥2 runs (otherwise not multi-seed)
  const result = [];
  for (const g of groups.values()) {
    if (g.runs.length >= 2) result.push(g);
  }
  result.sort((a, b) => b.runs.length - a.runs.length);
  return result;
}

function isStudyRecord(run) {
  return (
    run.model_id === "etude_sensibilite_27_04_wip" &&
    !run.run_id.endsWith("_aggregate") &&
    run.run_id !== "sensitivity_manifest" &&
    run.run_id !== "sensitivity_important_cases_figures"
  );
}

function renderStudyActions(run) {
  if (run.archived || !isStudyRecord(run)) return "";
  const artifacts = run.artifacts || [];
  const hasMacro = artifacts.some((a) => a.label === "macro_overview.png" && a.relative_path.includes("legacy_output"));
  const hasCompact = artifacts.some((a) => a.label === "compact_timeseries.json");
  const csvCount = artifacts.filter((a) => a.kind === "csv").length;
  const regenBtn = `<button id="regen-graphs">Régénérer graphiques complets</button>`;
  let cleanPart = "";
  if (hasMacro && hasCompact && csvCount > 0) {
    cleanPart = `<button id="clean-csv" class="secondary">Nettoyer CSV (${csvCount} fichier${csvCount > 1 ? "s" : ""})</button>`;
  } else if (hasMacro && hasCompact) {
    cleanPart = `<span class="muted">CSV déjà supprimés.</span>`;
  }
  return `
    <details class="action-menu">
      <summary>Actions étude OAT</summary>
      <div class="action-list">
        ${regenBtn}
        ${cleanPart}
      </div>
    </details>`;
}

function makeSpark(values, W, H, color) {
  if (values.length < 2) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const pad = 3;
  const pts = values
    .map((v, i) => {
      const x = pad + (i / (values.length - 1)) * (W - 2 * pad);
      const y = H - pad - ((v - min) / range) * (H - 2 * pad);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return `<polyline points="${pts}" fill="none" stroke="${escapeAttr(color)}" stroke-width="1.5" stroke-linejoin="round"/>`;
}

async function renderCompactTimeseries(run) {
  const artifact = (run.artifacts || []).find((a) => a.label === "compact_timeseries.json");
  const container = document.getElementById("compact-timeseries-plot");
  if (!artifact || !container) return;
  const url = `/api/runs/${encodeURIComponent(run.run_id)}/artifact?path=${encodeURIComponent(artifact.relative_path)}`;
  try {
    const data = await fetchJSON(url);
    const rows = data.rows || [];
    if (!rows.length) return;
    const SERIES = [
      { key: "alive", label: "n_alive", color: "#4e9af1" },
      { key: "actif", label: "actif", color: "#57a64b" },
      { key: "densite_fin", label: "densité fin.", color: "#e07b39" },
      { key: "gini", label: "Gini", color: "#b07aa1" },
    ];
    const W = 160, H = 50;
    const cells = SERIES.map(({ key, label, color }) => {
      const vals = rows.map((r) => r[key] ?? 0);
      return `<div class="sparkline-cell"><svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${makeSpark(vals, W, H, color)}</svg><div class="sparkline-label">${escapeHtml(label)}</div></div>`;
    });
    container.innerHTML = `<div class="sparklines-header">Trajectoire compacte (${rows.length} pas)</div><div class="sparklines-row">${cells.join("")}</div>`;
  } catch (_) {
    // silently ignore if fetch fails
  }
}

function renderMultiSeedGroups(groups) {
  if (!groups.length) {
    return `<div class="muted">Aucun groupe multi-seeds trouvé avec les filtres actuels.</div>`;
  }
  return groups.map((g, i) => {
    const isOpen = g.fp === state.selectedGroupKey || i === 0;
    const seeds = g.runs.map((r) => r.seed ?? "?").join(", ");
    const convergentCount = g.runs.filter((r) => (r.summary || {}).stationary).length;
    const convergentPct = Math.round((convergentCount / g.runs.length) * 100);
    const sampleParams = g.runs[0]?.parameters || {};
    const keyParamStr = ["n_candidats_pool", "lambda_creation", "mu", "alpha_sigma_brownien", "theta", "taux_depreciation_endo"]
      .filter((k) => k in sampleParams)
      .map((k) => `${PARAMETER_SYMBOLS[k] || k}=${formatValue(sampleParams[k])}`)
      .join(" | ");
    const modelName = modelDisplayName(g.model_id);
    return `
      <details class="multiseed-group" data-fp="${escapeAttr(g.fp)}" ${isOpen ? "open" : ""}>
        <summary class="multiseed-summary">
          <div class="multiseed-summary-main">
            <strong>${modelName}</strong>
            <span class="run-count">${g.runs.length} seeds</span>
            <span class="convergence-badge ${convergentPct >= 50 ? "conv-good" : "conv-low"}">${convergentPct}% stat.</span>
          </div>
          <div class="multiseed-params muted">${escapeHtml(keyParamStr)}</div>
          <div class="muted" style="font-size:0.78rem">seeds : ${escapeHtml(seeds)}</div>
        </summary>
        <div class="multiseed-body">
          <div class="multiseed-seed-list">
            ${g.runs.map((r) => `
              <div class="multiseed-seed-item ${r.run_id === state.selectedRunId ? "active" : ""}" data-run-id="${escapeAttr(r.run_id)}" data-fp="${escapeAttr(g.fp)}" role="button" tabindex="0">
                <span>seed ${r.seed ?? "?"}</span>
                ${(r.summary || {}).stationary ? `<span class="pill readonly">stat.</span>` : ""}
                ${r.important ? `<span class="pill important">!!</span>` : ""}
              </div>
            `).join("")}
          </div>
          <div class="multiseed-overlay-plot" id="overlay-${escapeAttr(g.fp.slice(0, 32).replace(/[^a-z0-9]/gi, "_"))}">
            <div class="muted" style="font-size:0.8rem">Cliquez sur un groupe pour charger les trajectoires superposées.</div>
          </div>
        </div>
      </details>
    `;
  }).join("");
}

function bindMultiSeedInteractions(list) {
  list.querySelectorAll(".multiseed-group").forEach((el) => {
    el.addEventListener("toggle", async () => {
      if (el.open) {
        state.selectedGroupKey = el.dataset.fp;
        const groups = buildMultiSeedGroups(filterAllRuns(filterStudyRuns(state.runs)));
        const g = groups.find((g) => g.fp === el.dataset.fp);
        if (g) await loadMultiSeedOverlay(g);
      }
    });
  });
  list.querySelectorAll(".multiseed-seed-item").forEach((item) => {
    const select = async () => {
      state.selectedRunId = item.dataset.runId;
      window.history.replaceState(null, "", `/results?run=${encodeURIComponent(state.selectedRunId)}`);
      renderRuns();
      await loadRunDetail();
    };
    item.addEventListener("click", select);
    item.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(); } });
  });
}

const SEED_COLORS = ["#4e9af1", "#e07b39", "#57a64b", "#b07aa1", "#e05c5c", "#5cb8b0", "#c4a240", "#888888"];

async function loadMultiSeedOverlay(group) {
  const plotId = "overlay-" + group.fp.slice(0, 32).replace(/[^a-z0-9]/gi, "_");
  const container = document.getElementById(plotId);
  if (!container) return;
  container.innerHTML = `<div class="muted">Chargement des trajectoires…</div>`;

  const SERIES = [
    { key: "alive",      label: "n vivantes",   W: 200, H: 60 },
    { key: "actif",      label: "actif total",   W: 200, H: 60 },
    { key: "loans",      label: "n prêts",       W: 200, H: 60 },
    { key: "densite_fin", label: "densité fin.", W: 200, H: 60 },
  ];

  const runSeries = await Promise.all(group.runs.map(async (run) => {
    const artifact = (run.artifacts || []).find((a) => a.label === "compact_timeseries.json");
    if (!artifact) return { run, rows: [] };
    try {
      const url = `/api/runs/${encodeURIComponent(run.run_id)}/artifact?path=${encodeURIComponent(artifact.relative_path)}`;
      const data = await fetchJSON(url);
      return { run, rows: data.rows || [] };
    } catch (_) {
      return { run, rows: [] };
    }
  }));

  const hasData = runSeries.some((rs) => rs.rows.length > 0);
  if (!hasData) {
    container.innerHTML = `<div class="muted">Pas de compact_timeseries.json disponible pour ce groupe.</div>`;
    return;
  }

  const cells = SERIES.map(({ key, label, W, H }) => {
    const sparklines = runSeries
      .filter((rs) => rs.rows.length > 0)
      .map((rs, i) => {
        const vals = rs.rows.map((r) => r[key] ?? 0);
        const color = SEED_COLORS[i % SEED_COLORS.length];
        const spark = makeSpark(vals, W, H, color);
        return spark ? `<g opacity="0.75">${spark}</g>` : "";
      }).join("");
    return `<div class="sparkline-cell">
      <svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${sparklines}</svg>
      <div class="sparkline-label">${escapeHtml(label)}</div>
    </div>`;
  }).join("");

  const convergentCount = group.runs.filter((r) => (r.summary || {}).stationary).length;
  const legend = runSeries
    .filter((rs) => rs.rows.length > 0)
    .map((rs, i) => `<span style="color:${SEED_COLORS[i % SEED_COLORS.length]}">■ seed ${rs.run.seed ?? "?"} ${(rs.run.summary || {}).stationary ? "(stat.)" : ""}</span>`)
    .join(" ");

  container.innerHTML = `
    <div class="multiseed-convergence-header">
      ${convergentCount}/${group.runs.length} seeds stationnaires
      <span class="muted" style="font-size:0.75rem;margin-left:8px">(bounded_tail + flux équilibré)</span>
    </div>
    <div class="sparklines-row">${cells}</div>
    <div class="multiseed-legend">${legend}</div>
  `;
}

function renderRunsGrouped(runs, { compact = false } = {}) {
  if (!runs.length) {
    return `<div class="muted">Aucune simulation dans ce périmètre.</div>`;
  }
  const modelGroups = new Map();
  for (const run of runs) {
    const key = run.model_id || "external";
    if (!modelGroups.has(key)) modelGroups.set(key, []);
    modelGroups.get(key).push(run);
  }
  return Array.from(modelGroups.entries()).map(([modelId, items], index) => {
    if (modelId === "etude_sensibilite_27_04_wip") {
      return renderStudyModelGroup(modelId, items, index, compact);
    }
    return `
      <details class="model-run-group" data-model-id="${escapeAttr(modelId)}" ${isRunGroupOpen(modelId, items, index) ? "open" : ""}>
        <summary>
          <span>${modelDisplayName(modelId)}</span>
          <span class="run-count">${items.length}</span>
        </summary>
        <div class="model-run-items">
          ${items.map((run) => renderRunCard(run, compact)).join("")}
        </div>
      </details>
    `;
  }).join("");
}

function renderStudyModelGroup(modelId, items, index, compact) {
  const sgGroups = new Map();
  for (const run of items) {
    const sg = studyGroupOf(run);
    if (!sgGroups.has(sg)) sgGroups.set(sg, []);
    sgGroups.get(sg).push(run);
  }
  const subGroupHtml = STUDY_GROUP_ORDER
    .filter((sg) => sgGroups.has(sg))
    .map((sg) => {
      const sgRuns = sgGroups.get(sg);
      const sgKey = `${modelId}__${sg}`;
      const isOpen = sgRuns.some((r) => r.run_id === state.selectedRunId) || state.openRunGroups.has(sgKey);
      return `
        <details class="model-run-group study-subgroup" data-model-id="${escapeAttr(sgKey)}" ${isOpen ? "open" : ""}>
          <summary>
            <span>${escapeHtml(STUDY_GROUP_LABELS[sg] || sg)}</span>
            <span class="run-count">${sgRuns.length}</span>
          </summary>
          <div class="model-run-items">
            ${sgRuns.map((run) => renderRunCard(run, compact)).join("")}
          </div>
        </details>
      `;
    }).join("");
  const open = isRunGroupOpen(modelId, items, index);
  return `
    <details class="model-run-group" data-model-id="${escapeAttr(modelId)}" ${open ? "open" : ""}>
      <summary>
        <span>${modelDisplayName(modelId)}</span>
        <span class="run-count">${items.length}</span>
      </summary>
      <div class="model-run-items study-subgroups">
        ${subGroupHtml}
      </div>
    </details>
  `;
}

function isRunGroupOpen(modelId, runs, index) {
  if (runs.some((run) => run.run_id === state.selectedRunId)) {
    return true;
  }
  if (state.openRunGroups.has(modelId)) {
    return true;
  }
  return !state.runGroupsTouched && index < 2;
}

function renderRunCard(run, compact = false) {
  return `
    <div class="run-card ${run.run_id === state.selectedRunId ? "active" : ""}" data-run-id="${escapeAttr(run.run_id)}" role="button" tabindex="0">
      <div class="run-card-actions">
        <button class="icon-action ${run.trashed ? "is-active" : ""}" data-action="trash" data-run-id="${escapeAttr(run.run_id)}" title="Corbeille" ${!run.deletable || run.trashed ? "disabled" : ""}>x</button>
        <button class="icon-action ${run.important ? "is-active" : ""}" data-action="important" data-run-id="${escapeAttr(run.run_id)}" title="Important">!!</button>
        <button class="icon-action ${run.keep ? "is-active" : ""}" data-action="keep" data-run-id="${escapeAttr(run.run_id)}" title="À garder"><3</button>
      </div>
      ${run.preview_artifact && !compact ? `<img class="run-thumb" src="/api/runs/${encodeURIComponent(run.run_id)}/artifact?path=${encodeURIComponent(run.preview_artifact)}" alt="preview">` : ""}
      <div class="pill-row">
        ${run.important ? `<span class="pill important">Importante</span>` : ""}
        ${run.archived ? `<span class="pill readonly">Archivée</span>` : ""}
        ${run.trashed ? `<span class="pill trash">Corbeille</span>` : ""}
        ${run.origin === "external" ? `<span class="pill readonly">Historique</span>` : ""}
      </div>
      <strong>${run.label || run.run_id}</strong>
      <div>${run.model_id}</div>
      <div class="run-meta">Seed ${run.seed ?? "-"} | ${run.status}</div>
      <div class="run-meta">${run.created_at}</div>
    </div>
  `;
}

function bindRunListInteractions(list) {
  list.querySelectorAll(".model-run-group").forEach((group) => {
    group.addEventListener("toggle", () => {
      const modelId = group.dataset.modelId;
      if (!modelId) {
        return;
      }
      state.runGroupsTouched = true;
      if (group.open) {
        state.openRunGroups.add(modelId);
      } else {
        state.openRunGroups.delete(modelId);
      }
    });
  });
  list.querySelectorAll(".run-card").forEach((card) => {
    const selectRun = async (event) => {
      event.stopPropagation();
      if (card.dataset.ignoreClick === "true") {
        card.dataset.ignoreClick = "";
        return;
      }
      state.selectedRunId = card.dataset.runId;
      if (page() === "results") {
        window.history.replaceState(null, "", `/results?run=${encodeURIComponent(state.selectedRunId)}`);
        renderRuns();
        await loadRunDetail();
      } else {
        window.location.href = `/results?run=${encodeURIComponent(state.selectedRunId)}`;
      }
    };
    card.addEventListener("click", selectRun);
    card.addEventListener("keydown", async (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        await selectRun(event);
      }
    });
  });
  list.querySelectorAll(".icon-action").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.stopPropagation();
      const parent = button.closest(".run-card");
      if (parent) {
        parent.dataset.ignoreClick = "true";
      }
      await handleQuickAction(button.dataset.runId, button.dataset.action);
    });
  });
}

async function handleQuickAction(runId, action) {
  const run = state.runs.find((item) => item.run_id === runId);
  if (!run) {
    return;
  }
  if (action === "important") {
    await fetchJSON(`/api/runs/${encodeURIComponent(runId)}/important`, {
      method: "POST",
      body: JSON.stringify({ important: !run.important }),
    });
  } else if (action === "keep") {
    await fetchJSON(`/api/runs/${encodeURIComponent(runId)}/keep`, {
      method: "POST",
      body: JSON.stringify({ keep: !run.keep }),
    });
  } else if (action === "trash" && run.deletable && !run.trashed) {
    await fetchJSON(`/api/runs/${encodeURIComponent(runId)}/trash`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    if (state.selectedRunId === runId) {
      state.selectedRunId = null;
      renderRunDetail(null);
    }
  }
  await refreshRuns();
  if (state.selectedRunId) {
    await loadRunDetail();
  }
}

async function loadRunDetail() {
  if (!state.selectedRunId) {
    renderRunDetail(null);
    return;
  }
  const run = await fetchJSON(`/api/runs/${encodeURIComponent(state.selectedRunId)}`);
  if (run.archived && state.scope === "active") {
    state.scope = "archived";
    await refreshRuns();
  }
  renderRunDetail(run);
}

function renderRunDetail(run) {
  const detail = document.getElementById("run-detail");
  const tabNav = document.getElementById("artifacts-tab-nav");
  const tabContent = document.getElementById("artifacts-tab-content");
  if (!detail) {
    return;
  }
  const main = document.querySelector("main.results-grid");
  if (main) main.classList.toggle("list-expanded", !run);
  const list = document.getElementById("runs-list");
  if (list) list.classList.toggle("compact-runs", !run);
  if (!run) {
    detail.innerHTML = "Sélectionnez une simulation.";
    detail.classList.add("muted");
    if (tabNav) tabNav.innerHTML = "";
    if (tabContent) tabContent.innerHTML = "";
    return;
  }
  detail.classList.remove("muted");
  detail.innerHTML = `
    <div class="detail-split">
      <section>
        <h3>Note rapide</h3>
        ${renderRunQuickNote(run)}
        <dl>
          <dt>Run ID</dt><dd>${run.run_id}</dd>
          <dt>Modèle</dt><dd>${run.model_id}</dd>
          <dt>Origine</dt><dd>${run.origin}</dd>
          <dt>Seed</dt><dd>${run.seed ?? "-"}</dd>
          <dt>Statut</dt><dd>${run.status}</dd>
          <dt>Archivée</dt><dd>${run.archived ? "oui" : "non"}</dd>
          <dt>Importante</dt><dd>${run.important ? "oui" : "non"}</dd>
          <dt>Corbeille</dt><dd>${run.trashed ? "oui" : "non"}</dd>
          <dt>Commentaire</dt><dd><pre>${escapeHtml(run.comment || "")}</pre></dd>
          <dt>Résumé</dt><dd><pre>${JSON.stringify(run.summary || {}, null, 2)}</pre></dd>
        </dl>
      </section>
      <aside class="parameter-note">
        <h3>Paramètres clés</h3>
        ${renderParameterSummary(run.parameters || {}, true)}
        <details>
          <summary>Tous les paramètres</summary>
          ${renderParameterSummary(run.parameters || {}, false)}
        </details>
      </aside>
    </div>
    <div class="annotation-box">
      <label>Label</label>
      <input id="annotation-label" type="text" value="${escapeAttr(run.label || "")}">
      <label>Commentaire</label>
      <textarea id="annotation-comment" rows="5">${escapeHtml(run.comment || "")}</textarea>
      <div class="inline-actions">
        <button id="save-annotations">Enregistrer les annotations</button>
        <button id="refresh-artifacts" class="secondary">Rafraîchir les artéfacts</button>
      </div>
    </div>
    ${renderRunActions(run)}
    <div id="compact-timeseries-plot"></div>
  `;
  bindRunActions(run);
  bindAnnotationSave(run);
  renderArtifacts(run);
  renderCompactTimeseries(run);
}

function renderRunQuickNote(run) {
  const params = run.parameters || {};
  const items = [
    ["Durée", params.T ?? params.duree_simulation ?? params.steps],
    ["Seed", run.seed ?? params.seed],
    ["α", formatAlphaRange(params)],
    ["k", params.k ?? params.n_candidats_pool],
    ["θ", params.theta],
    ["f", params.fraction_taux_emprunteur],
    ["λ", params.lam ?? params.lambda_creation],
    ["K₀", params.K0],
  ].filter(([, value]) => value !== undefined && value !== null && value !== "");
  return `<div class="quick-note">${items.map(([label, value]) => `
    <div><span>${label}</span><strong>${escapeHtml(formatValue(value))}</strong></div>
  `).join("")}</div>`;
}

function renderParameterSummary(parameters, keyOnly) {
  const names = keyOnly
    ? KEY_PARAMETER_NAMES.filter((name) => Object.prototype.hasOwnProperty.call(parameters, name))
    : Object.keys(parameters).sort();
  if (!names.length) {
    return `<p class="muted">Aucun paramètre enregistré.</p>`;
  }
  return `<div class="parameter-summary">${names.map((name) => `
    <div class="parameter-row" title="${escapeAttr(PARAMETER_HELP[name] || "")}">
      <span>${escapeHtml(PARAMETER_SYMBOLS[name] || name)}</span>
      <strong>${escapeHtml(formatValue(parameters[name]))}</strong>
    </div>
  `).join("")}</div>`;
}

function formatAlphaRange(parameters) {
  if (parameters.alpha_min !== undefined && parameters.alpha_max !== undefined) {
    const sigma = parameters.alpha_sigma_brownien !== undefined ? `; σ=${formatValue(parameters.alpha_sigma_brownien)}` : "";
    return `[${formatValue(parameters.alpha_min)}, ${formatValue(parameters.alpha_max)}]${sigma}`;
  }
  return parameters.alpha;
}

function formatValue(value) {
  if (typeof value === "number") {
    if (Number.isInteger(value)) return String(value);
    if (Math.abs(value) >= 1000 || Math.abs(value) < 0.001) return value.toExponential(2);
    return String(Number(value.toFixed(5)));
  }
  if (typeof value === "boolean") return value ? "oui" : "non";
  return String(value);
}

function renderRunActions(run) {
  const baseMenu = `
    <details class="action-menu">
      <summary>Actions</summary>
      <div class="action-list">
        <button id="locate-run" class="secondary">Localiser dans le finder</button>
        <button id="toggle-important">${run.important ? "Retirer !! importante" : "Marquer !! importante"}</button>
        <button id="toggle-keep">${run.keep ? "Retirer étoile" : "Marquer étoile"}</button>
        ${run.deletable && !run.trashed ? `<button id="trash-run" class="secondary">Corbeille</button>` : ""}
      </div>
    </details>
  `;
  if (run.trashed) {
    return `
      <div class="inline-actions">
        <button id="locate-run" class="secondary">Localiser dans le finder</button>
        <button id="restore-run">Restaurer</button>
        <button id="purge-run" class="secondary">Supprimer définitivement</button>
      </div>
    `;
  }
  const archiveNotice = run.archived
    ? `<p class="muted">Simulation archivée : consultation et annotations autorisées, suppression désactivée.</p>`
    : "";
  return baseMenu + archiveNotice + renderStudyActions(run);
}

function bindRunActions(run) {
  const locateButton = document.getElementById("locate-run");
  if (locateButton) {
    locateButton.addEventListener("click", async () => {
      await fetchJSON(`/api/runs/${encodeURIComponent(run.run_id)}/locate`, {
        method: "POST",
        body: JSON.stringify({}),
      });
    });
  }
  if (run.trashed) {
    document.getElementById("restore-run").addEventListener("click", async () => {
      await fetchJSON(`/api/trash/${encodeURIComponent(run.run_id)}/restore`, { method: "POST", body: JSON.stringify({}) });
      state.scope = "active";
      await refreshRuns();
      state.selectedRunId = run.run_id;
      await loadRunDetail();
    });
    document.getElementById("purge-run").addEventListener("click", async () => {
      await fetchJSON(`/api/trash/${encodeURIComponent(run.run_id)}`, { method: "DELETE" });
      state.selectedRunId = null;
      await refreshRuns();
      renderRunDetail(null);
    });
    return;
  }
  document.getElementById("toggle-important").addEventListener("click", async () => {
    await fetchJSON(`/api/runs/${encodeURIComponent(run.run_id)}/important`, {
      method: "POST",
      body: JSON.stringify({ important: !run.important }),
    });
    await refreshRuns();
    await loadRunDetail();
  });
  document.getElementById("toggle-keep").addEventListener("click", async () => {
    await fetchJSON(`/api/runs/${encodeURIComponent(run.run_id)}/keep`, {
      method: "POST",
      body: JSON.stringify({ keep: !run.keep }),
    });
    await refreshRuns();
    await loadRunDetail();
  });
  const trashButton = document.getElementById("trash-run");
  if (trashButton) {
    trashButton.addEventListener("click", async () => {
      await fetchJSON(`/api/runs/${encodeURIComponent(run.run_id)}/trash`, {
        method: "POST",
        body: JSON.stringify({}),
      });
      state.selectedRunId = null;
      await refreshRuns();
      renderRunDetail(null);
    });
  }
  const regenButton = document.getElementById("regen-graphs");
  if (regenButton) {
    regenButton.addEventListener("click", async () => {
      regenButton.disabled = true;
      regenButton.textContent = "Lancement…";
      try {
        const result = await fetchJSON(`/api/runs/${encodeURIComponent(run.run_id)}/regen-graphs`, {
          method: "POST",
          body: JSON.stringify({}),
        });
        regenButton.textContent = result.message || "Lancé — rafraîchir les artefacts dans quelques minutes.";
      } catch (exc) {
        regenButton.textContent = `Erreur : ${exc.message}`;
        regenButton.disabled = false;
      }
    });
  }
  const cleanCsvButton = document.getElementById("clean-csv");
  if (cleanCsvButton) {
    cleanCsvButton.addEventListener("click", async () => {
      cleanCsvButton.disabled = true;
      try {
        const result = await fetchJSON(`/api/runs/${encodeURIComponent(run.run_id)}/clean-csv`, {
          method: "POST",
          body: JSON.stringify({}),
        });
        cleanCsvButton.textContent = `${result.deleted_csv} CSV supprimé${result.deleted_csv > 1 ? "s" : ""}.`;
        await refreshRuns();
        await loadRunDetail();
      } catch (exc) {
        cleanCsvButton.textContent = `Erreur : ${exc.message}`;
        cleanCsvButton.disabled = false;
      }
    });
  }
}

function bindAnnotationSave(run) {
  document.getElementById("save-annotations").addEventListener("click", async () => {
    await fetchJSON(`/api/runs/${encodeURIComponent(run.run_id)}/annotations`, {
      method: "POST",
      body: JSON.stringify({
        label: document.getElementById("annotation-label").value,
        comment: document.getElementById("annotation-comment").value,
      }),
    });
    await refreshRuns();
    await loadRunDetail();
  });
  document.getElementById("refresh-artifacts").addEventListener("click", async () => {
    await fetchJSON(`/api/runs/${encodeURIComponent(run.run_id)}/refresh-artifacts`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    await refreshRuns();
    await loadRunDetail();
  });
}

const ARTIFACT_GROUP_NAMES = {
  figures: "Graphiques",
  analyse_par_classe: "Analyse par classe",
  detail_vie_entites: "Vies individuelles",
  csv: "Données CSV",
};
const ARTIFACT_GROUP_ORDER = [
  "Graphiques",
  "Analyse par classe",
  "Vies individuelles",
  "Données CSV",
  "Résumé",
  "Logs",
];

function _artifactGroupKey(relativePath) {
  const parts = relativePath.split("/");
  const parent = parts.length >= 2 ? parts[parts.length - 2] : "racine";
  if (ARTIFACT_GROUP_NAMES[parent]) return ARTIFACT_GROUP_NAMES[parent];
  if (parent === "racine") return "Logs";
  if (parent.startsWith("simu_") || parent === "legacy_output") return "Résumé";
  return parent;
}

function _artifactCard(artifact, runId) {
  const url = `/api/runs/${encodeURIComponent(runId)}/artifact?path=${encodeURIComponent(artifact.relative_path)}`;
  if (artifact.kind === "image") {
    return `<div class="artifact-card"><strong>${artifact.label}</strong><img src="${url}" alt="${artifact.label}"><div><a href="${url}" target="_blank">ouvrir</a></div></div>`;
  }
  return `<div class="artifact-card"><strong>${artifact.label}</strong><div class="artifact-kind">${artifact.kind}</div><div><a href="${url}" target="_blank">ouvrir</a></div></div>`;
}

function renderArtifacts(run) {
  const nav = document.getElementById("artifacts-tab-nav");
  const content = document.getElementById("artifacts-tab-content");
  if (!nav || !content) return;

  const artifacts = run.artifacts || [];
  if (artifacts.length === 0) {
    nav.innerHTML = "";
    content.innerHTML = "<p class='muted'>Aucun artefact.</p>";
    return;
  }

  // Group by subfolder
  const groups = {};
  for (const artifact of artifacts) {
    const key = _artifactGroupKey(artifact.relative_path);
    if (!groups[key]) groups[key] = [];
    groups[key].push(artifact);
  }

  const sortedKeys = Object.keys(groups).sort((a, b) => {
    const ia = ARTIFACT_GROUP_ORDER.indexOf(a);
    const ib = ARTIFACT_GROUP_ORDER.indexOf(b);
    if (ia >= 0 && ib >= 0) return ia - ib;
    if (ia >= 0) return -1;
    if (ib >= 0) return 1;
    return a.localeCompare(b);
  });

  // Build nav buttons
  nav.innerHTML = sortedKeys.map((groupName, i) =>
    `<button class="artifact-tab-btn${i === 0 ? " active" : ""}" data-group="${groupName}">
      ${groupName} <span class="artifact-count">${groups[groupName].length}</span>
    </button>`
  ).join("");

  // Build content panes
  content.innerHTML = sortedKeys.map((groupName, i) => {
    const cards = groups[groupName].map((a) => _artifactCard(a, run.run_id)).join("");
    return `<div class="artifact-tab-pane${i === 0 ? " active" : ""}" data-group="${groupName}">
      <div class="artifact-section-grid">${cards}</div>
    </div>`;
  }).join("");

  // Wire up tab clicks
  nav.querySelectorAll(".artifact-tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      nav.querySelectorAll(".artifact-tab-btn").forEach((b) => b.classList.remove("active"));
      content.querySelectorAll(".artifact-tab-pane").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      content.querySelector(`.artifact-tab-pane[data-group="${btn.dataset.group}"]`).classList.add("active");
    });
  });
}

async function initLaunchPage() {
  await loadModels();
  await loadSystemInfo();
  await refreshJobs();
  await refreshRuns();
  document.getElementById("run-single").addEventListener("click", createSingleRun);
  document.getElementById("run-batch").addEventListener("click", createBatch);
  document.getElementById("refresh-launch-runs").addEventListener("click", refreshRuns);
}

async function initResultsPage() {
  await loadModels();
  const params = new URLSearchParams(window.location.search);
  state.selectedRunId = params.get("run");
  await refreshJobs();
  await refreshRuns();
  if (state.selectedRunId) {
    await loadRunDetail();
  } else {
    renderRunDetail(null);
  }
  document.getElementById("refresh-runs").addEventListener("click", async () => {
    await refreshJobs();
    await refreshRuns();
    await loadRunDetail();
  });
  document.querySelectorAll("[data-scope]").forEach((button) => {
    button.addEventListener("click", async () => {
      state.scope = button.dataset.scope;
      state.selectedRunId = null;
      await refreshRuns();
      renderRunDetail(null);
    });
  });
  document.getElementById("empty-trash").addEventListener("click", async () => {
    await fetchJSON("/api/trash", { method: "DELETE" });
    state.selectedRunId = null;
    await refreshRuns();
    renderRunDetail(null);
  });
  const groupSelect = document.getElementById("study-group");
  if (groupSelect) {
    groupSelect.addEventListener("change", () => {
      state.studyGroup = groupSelect.value;
      renderRuns();
    });
  }
  const campaignSelect = document.getElementById("study-campaign");
  if (campaignSelect) {
    campaignSelect.addEventListener("change", () => {
      state.studyCampaign = campaignSelect.value;
      renderRuns();
    });
  }
  ["study-filter-bounded", "study-filter-drop5", "study-filter-converged"].forEach((id) => {
    const cb = document.getElementById(id);
    if (cb) {
      cb.addEventListener("change", () => {
        state.studyBounded = document.getElementById("study-filter-bounded")?.checked || false;
        state.studyDrop5 = document.getElementById("study-filter-drop5")?.checked || false;
        state.studyConverged = document.getElementById("study-filter-converged")?.checked || false;
        renderRuns();
      });
    }
  });

  const searchInput = document.getElementById("search-runs");
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      state.searchQuery = searchInput.value.trim();
      renderRuns();
    });
    // Initialiser depuis l'URL si hash passé
    const params = new URLSearchParams(window.location.search);
    const hashParam = params.get("search");
    if (hashParam) {
      searchInput.value = hashParam;
      state.searchQuery = hashParam;
    }
  }

  const filterImportantCb = document.getElementById("filter-important");
  if (filterImportantCb) {
    filterImportantCb.addEventListener("change", () => {
      state.filterImportant = filterImportantCb.checked;
      renderRuns();
    });
  }
  const filterKeepCb = document.getElementById("filter-keep");
  if (filterKeepCb) {
    filterKeepCb.addEventListener("change", () => {
      state.filterKeep = filterKeepCb.checked;
      renderRuns();
    });
  }

  const toggleMultiseed = document.getElementById("toggle-multiseed");
  if (toggleMultiseed) {
    toggleMultiseed.addEventListener("click", () => {
      state.multiSeedMode = !state.multiSeedMode;
      toggleMultiseed.classList.toggle("secondary", !state.multiSeedMode);
      toggleMultiseed.classList.toggle("active-mode", state.multiSeedMode);
      renderRuns();
    });
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll('"', "&quot;");
}


async function init() {
  if (page() === "launch") {
    await initLaunchPage();
  } else if (page() === "results") {
    await initResultsPage();
  }
}

init().catch((error) => setMessage(error.message));
