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
};

const PARAMETER_HELP = {
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
    if (/(alpha|productiv)/.test(name)) group = "Productivité";
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
  state.models = await fetchJSON("/api/models");
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
      <div class="run-meta">${job.label || job.job_type} | ${job.created_at}</div>
      <div>${job.message || "-"}</div>
      <div class="mini-progress"><span style="width:${job.progress || 0}%"></span></div>
      <div class="run-meta">${Math.round(job.progress || 0)}%${job.error ? ` | ${escapeHtml(job.error)}` : ""}</div>
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
    <div><strong>${job.model_id}</strong></div>
    <div>${job.message || "-"}</div>
    <div class="run-meta">Statut: ${job.status} | Progression: ${Math.round(job.progress || 0)}%</div>
    <div class="run-meta">${job.logs.slice(-5).join("<br>")}</div>
  `;
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
  list.innerHTML = renderRunsGrouped(state.runs, { compact: list.dataset.compact === "true" });
  bindRunListInteractions(list);
}

function renderRunsGrouped(runs, { compact = false } = {}) {
  if (!runs.length) {
    return `<div class="muted">Aucune simulation dans ce périmètre.</div>`;
  }
  const groups = new Map();
  for (const run of runs) {
    const key = run.model_id || "external";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(run);
  }
  return Array.from(groups.entries()).map(([modelId, items], index) => `
    <details class="model-run-group" data-model-id="${escapeAttr(modelId)}" ${isRunGroupOpen(modelId, items, index) ? "open" : ""}>
      <summary>
        <span>${modelDisplayName(modelId)}</span>
        <span class="run-count">${items.length}</span>
      </summary>
      <div class="model-run-items">
        ${items.map((run) => renderRunCard(run, compact)).join("")}
      </div>
    </details>
  `).join("");
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
        <button class="icon-action ${run.trashed ? "is-active" : ""}" data-action="trash" data-run-id="${escapeAttr(run.run_id)}" title="Corbeille" ${run.origin === "external" || run.trashed ? "disabled" : ""}>x</button>
        <button class="icon-action ${run.important ? "is-active" : ""}" data-action="important" data-run-id="${escapeAttr(run.run_id)}" title="Important">!!</button>
        <button class="icon-action ${run.keep ? "is-active" : ""}" data-action="keep" data-run-id="${escapeAttr(run.run_id)}" title="À garder"><3</button>
      </div>
      ${run.preview_artifact && !compact ? `<img class="run-thumb" src="/api/runs/${encodeURIComponent(run.run_id)}/artifact?path=${encodeURIComponent(run.preview_artifact)}" alt="preview">` : ""}
      <div class="pill-row">
        ${run.important ? `<span class="pill important">Importante</span>` : ""}
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
  } else if (action === "trash" && run.origin !== "external" && !run.trashed) {
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
  renderRunDetail(run);
}

function renderRunDetail(run) {
  const detail = document.getElementById("run-detail");
  const grid = document.getElementById("artifacts-grid");
  if (!detail || !grid) {
    return;
  }
  if (!run) {
    detail.innerHTML = "Sélectionnez une simulation.";
    detail.classList.add("muted");
    grid.innerHTML = "";
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
  `;
  bindRunActions(run);
  bindAnnotationSave(run);
  renderArtifacts(run);
}

function renderRunQuickNote(run) {
  const params = run.parameters || {};
  const items = [
    ["Durée", params.duree_simulation ?? params.steps],
    ["Seed", run.seed ?? params.seed],
    ["α", formatAlphaRange(params)],
    ["k", params.n_candidats_pool],
    ["θ", params.theta],
    ["f", params.fraction_taux_emprunteur],
    ["λ", params.lambda_creation],
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
        ${run.origin !== "external" && !run.trashed ? `<button id="trash-run" class="secondary">Corbeille</button>` : ""}
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
  return baseMenu + (run.origin === "external" ? `<p class="muted">Simulation historique : annotations persistantes autorisées, suppression désactivée.</p>` : "");
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

function renderArtifacts(run) {
  const grid = document.getElementById("artifacts-grid");
  if (!grid) {
    return;
  }
  grid.innerHTML = (run.artifacts || []).map((artifact) => {
    const url = `/api/runs/${encodeURIComponent(run.run_id)}/artifact?path=${encodeURIComponent(artifact.relative_path)}`;
    if (artifact.kind === "image") {
      return `<div class="artifact-card"><strong>${artifact.label}</strong><img src="${url}" alt="${artifact.label}"><div><a href="${url}" target="_blank">ouvrir</a></div></div>`;
    }
    return `<div class="artifact-card"><strong>${artifact.label}</strong><div>${artifact.kind}</div><div><a href="${url}" target="_blank">ouvrir</a></div></div>`;
  }).join("");
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
