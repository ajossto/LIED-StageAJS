const state = {
  models: [],
  selectedModelId: null,
  runs: [],
  selectedRunId: null,
  scope: "active",
  currentJobId: null,
};

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
  if (parameter.param_type === "bool") {
    return `<label>${parameter.label || parameter.name}</label>
      <div class="help">${parameter.description || ""}</div>
      <input data-param="${parameter.name}" type="checkbox" ${parameter.default ? "checked" : ""}>`;
  }
  const min = parameter.minimum !== null ? `min="${parameter.minimum}"` : "";
  const max = parameter.maximum !== null ? `max="${parameter.maximum}"` : "";
  const step = parameter.param_type === "int" ? "1" : "any";
  return `<label>${parameter.label || parameter.name}</label>
    <div class="help">${parameter.description || ""}</div>
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
  await pollJob();
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
  await pollJob();
}

async function pollJob() {
  if (!state.currentJobId) {
    return;
  }
  const job = await fetchJSON(`/api/jobs/${encodeURIComponent(state.currentJobId)}`);
  renderJob(job);
  if (job.status === "running" || job.status === "queued") {
    window.setTimeout(pollJob, 1000);
    return;
  }
  if (job.status === "completed") {
    setMessage(`${job.message}\n${job.logs.join("\n")}`);
  } else if (job.status === "failed") {
    setMessage(`${job.message}\n${job.error}\n${job.logs.join("\n")}`);
  }
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
      await pollJob();
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
  list.innerHTML = state.runs.map((run) => `
    <div class="run-card ${run.run_id === state.selectedRunId ? "active" : ""}" data-run-id="${run.run_id}">
      <div class="run-card-actions">
        <button class="icon-action ${run.trashed ? "is-active" : ""}" data-action="trash" data-run-id="${run.run_id}" title="Corbeille" ${run.origin === "external" || run.trashed ? "disabled" : ""}>x</button>
        <button class="icon-action ${run.important ? "is-active" : ""}" data-action="important" data-run-id="${run.run_id}" title="Important">!!</button>
        <button class="icon-action ${run.keep ? "is-active" : ""}" data-action="keep" data-run-id="${run.run_id}" title="À garder"><3</button>
      </div>
      ${run.preview_artifact ? `<img class="run-thumb" src="/api/runs/${encodeURIComponent(run.run_id)}/artifact?path=${encodeURIComponent(run.preview_artifact)}" alt="preview">` : ""}
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
  `).join("");
  list.querySelectorAll(".run-card").forEach((card) => {
    card.addEventListener("click", async () => {
      if (card.dataset.ignoreClick === "true") {
        card.dataset.ignoreClick = "";
        return;
      }
      state.selectedRunId = card.dataset.runId;
      renderRuns();
      await loadRunDetail();
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
    <div class="annotation-box">
      <label>Label</label>
      <input id="annotation-label" type="text" value="${escapeAttr(run.label || "")}">
      <label>Commentaire</label>
      <textarea id="annotation-comment" rows="5">${escapeHtml(run.comment || "")}</textarea>
      <div class="inline-actions">
        <button id="save-annotations">Enregistrer les annotations</button>
      </div>
    </div>
    ${renderRunActions(run)}
  `;
  bindRunActions(run);
  bindAnnotationSave(run);
  renderArtifacts(run);
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
  document.getElementById("run-single").addEventListener("click", createSingleRun);
  document.getElementById("run-batch").addEventListener("click", createBatch);
}

async function initResultsPage() {
  await refreshRuns();
  document.getElementById("refresh-runs").addEventListener("click", async () => {
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
