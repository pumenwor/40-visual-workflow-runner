"use strict";

const API = "/api/v1";
const NODE_WIDTH = 178;
const NODE_HEIGHT = 82;

const state = {
  workflows: [],
  workflow: null,
  selectedNodeId: null,
  dirty: false,
  runs: [],
  run: null,
  pollTimer: null,
};

const el = (id) => document.getElementById(id);

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function randomSuffix() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID().slice(0, 8);
  }
  return Math.random().toString(16).slice(2, 10).padEnd(8, "0");
}

function setMessage(text, type = "info") {
  const box = el("message");
  box.hidden = false;
  box.className = `message ${type}`;
  box.textContent = text;
}

function clearMessage() {
  el("message").hidden = true;
}

function apiErrorMessage(data, fallback) {
  if (data && data.error) {
    const base = data.error.message || fallback;
    const details = (data.error.details || [])
      .map((d) => d.message || JSON.stringify(d))
      .filter(Boolean);
    return details.length ? `${base} ${details.join(" ")}` : base;
  }
  if (data && data.detail) return String(data.detail);
  return fallback;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let data = null;
  if (text) {
    try { data = JSON.parse(text); } catch { data = { detail: text }; }
  }
  if (!response.ok) {
    throw new Error(apiErrorMessage(data, `Request failed (${response.status}).`));
  }
  return data;
}

function selectedNode() {
  if (!state.workflow) return null;
  return state.workflow.nodes.find((node) => node.id === state.selectedNodeId) || null;
}

function nodeById(id) {
  return state.workflow ? state.workflow.nodes.find((node) => node.id === id) : null;
}

function nodeName(id) {
  const node = nodeById(id);
  return node ? node.name : id;
}

function setDirty(value = true) {
  state.dirty = value;
  el("dirty-indicator").hidden = !value;
}

function defaultConfig(kind) {
  switch (kind) {
    case "emit_json": return { value: { value: 3 } };
    case "delay": return { seconds: 1 };
    case "demo_fail": return { fail_first_n_attempts: 1, value: { message: "Recovered" } };
    case "combine_inputs":
    default: return {};
  }
}

function formatTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

function statusPill(status) {
  const safe = escapeHtml(status || "unknown");
  return `<span class="status-pill ${safe}">${safe}</span>`;
}

function renderWorkflowList() {
  const container = el("workflow-list");
  container.innerHTML = "";
  if (!state.workflows.length) {
    container.innerHTML = '<p class="muted">No workflows yet. Create one or load the samples.</p>';
    return;
  }
  for (const workflow of state.workflows) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `workflow-item${state.workflow && workflow.id === state.workflow.id ? " selected" : ""}`;
    button.innerHTML = `<strong>${escapeHtml(workflow.name)}</strong><small>Version ${workflow.version} · Updated ${escapeHtml(formatTime(workflow.updated_at))}</small>`;
    button.addEventListener("click", () => selectWorkflow(workflow.id).catch(showError));
    container.append(button);
  }
}

async function loadWorkflows(selectId = null) {
  state.workflows = await api(`${API}/workflows`);
  renderWorkflowList();
  if (selectId) {
    await selectWorkflow(selectId, { push: false });
  } else if (!state.workflow && state.workflows.length) {
    await selectWorkflow(state.workflows[0].id, { push: false });
  } else if (!state.workflows.length) {
    state.workflow = null;
    renderEditor();
  }
}

async function selectWorkflow(id, options = {}) {
  stopPolling();
  state.workflow = await api(`${API}/workflows/${encodeURIComponent(id)}`);
  state.selectedNodeId = state.workflow.nodes[0]?.id || null;
  state.run = null;
  setDirty(false);
  renderWorkflowList();
  renderEditor();
  if (options.push !== false) {
    window.history.pushState(null, "", `/workflows/${encodeURIComponent(id)}`);
  }
  await loadRuns(options.runId || null);
}

function renderEditor() {
  const hasWorkflow = Boolean(state.workflow);
  el("empty-state").hidden = hasWorkflow;
  el("editor").hidden = !hasWorkflow;
  if (!hasWorkflow) return;

  el("workflow-title").textContent = state.workflow.name;
  el("workflow-meta").textContent =
    `Version ${state.workflow.version} · ${state.workflow.nodes.length} node(s) · ` +
    `${state.workflow.edges.length} connection(s) · Updated ${formatTime(state.workflow.updated_at)}`;

  renderCanvas();
  renderNodeEditor();
  renderEdgeControls();
}

function taskStatusByNodeId() {
  const statuses = {};
  if (state.run) {
    for (const task of state.run.tasks || []) statuses[task.node_id] = task.status;
  }
  return statuses;
}

function renderCanvas() {
  if (!state.workflow) return;
  el("workflow-meta").textContent =
    `Version ${state.workflow.version} · ${state.workflow.nodes.length} node(s) · ` +
    `${state.workflow.edges.length} connection(s) · Updated ${formatTime(state.workflow.updated_at)}`;

  const layer = el("node-layer");
  layer.innerHTML = "";
  el("canvas-empty").hidden = state.workflow.nodes.length > 0;
  const statuses = taskStatusByNodeId();

  for (const node of state.workflow.nodes) {
    const card = document.createElement("div");
    card.className = `node-card${node.id === state.selectedNodeId ? " selected" : ""}`;
    const status = statuses[node.id];
    if (status) card.classList.add(`status-${status}`);
    card.tabIndex = 0;
    card.dataset.nodeId = node.id;
    card.style.left = `${node.position.x}px`;
    card.style.top = `${node.position.y}px`;
    card.setAttribute("aria-label", `${node.name}, ${node.kind}${status ? `, status ${status}` : ""}`);
    card.innerHTML =
      `<strong>${escapeHtml(node.name)}</strong>` +
      `<small>${escapeHtml(node.kind)}</small>` +
      (status ? `<small>${statusPill(status)}</small>` : "");

    card.addEventListener("click", () => selectNode(node.id));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectNode(node.id);
      }
    });
    card.addEventListener("pointerdown", (event) => startDrag(event, node, card));
    layer.append(card);
  }
  drawEdges();
}

function drawEdges() {
  const svg = el("edge-layer");
  if (!state.workflow) return;
  const defs = `<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#2563eb"></path></marker></defs>`;
  const lines = [];
  for (const edge of state.workflow.edges) {
    const source = nodeById(edge.source_node_id);
    const target = nodeById(edge.target_node_id);
    if (!source || !target) continue;
    const x1 = source.position.x + NODE_WIDTH;
    const y1 = source.position.y + NODE_HEIGHT / 2;
    const x2 = target.position.x;
    const y2 = target.position.y + NODE_HEIGHT / 2;
    lines.push(`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#2563eb" stroke-width="2.5" marker-end="url(#arrow)"></line>`);
  }
  svg.innerHTML = defs + lines.join("");
}

function startDrag(event, node, card) {
  if (event.button !== undefined && event.button !== 0) return;
  selectNode(node.id, { rerender: false });
  card.classList.add("selected");
  const startX = event.clientX;
  const startY = event.clientY;
  const originalX = node.position.x;
  const originalY = node.position.y;
  card.setPointerCapture(event.pointerId);

  function onMove(moveEvent) {
    node.position.x = Math.max(0, Math.min(1000, Math.round(originalX + moveEvent.clientX - startX)));
    node.position.y = Math.max(0, Math.min(600, Math.round(originalY + moveEvent.clientY - startY)));
    card.style.left = `${node.position.x}px`;
    card.style.top = `${node.position.y}px`;
    el("node-x").value = node.position.x;
    el("node-y").value = node.position.y;
    setDirty(true);
    drawEdges();
  }

  function onUp() {
    card.removeEventListener("pointermove", onMove);
    card.removeEventListener("pointerup", onUp);
    card.removeEventListener("pointercancel", onUp);
  }

  card.addEventListener("pointermove", onMove);
  card.addEventListener("pointerup", onUp);
  card.addEventListener("pointercancel", onUp);
}

function selectNode(id, options = {}) {
  state.selectedNodeId = id;
  if (options.rerender !== false) {
    renderCanvas();
    renderNodeEditor();
  }
}

function renderNodeEditor() {
  const node = selectedNode();
  el("node-editor-empty").hidden = Boolean(node);
  el("node-editor").hidden = !node;
  el("delete-node").disabled = !node;
  if (!node) return;

  el("node-id").textContent = node.id;
  el("node-name").value = node.name;
  el("node-kind").value = node.kind;
  el("node-config").value = JSON.stringify(node.config || {}, null, 2);
  el("node-sort-order").value = node.sort_order ?? 0;
  el("node-retries").value = node.max_retries ?? 0;
  el("node-retry-delay").value = node.retry_delay_seconds ?? 1;
  el("node-timeout").value = node.timeout_seconds ?? 10;
  el("node-x").value = Math.round(node.position.x);
  el("node-y").value = Math.round(node.position.y);
}

function syncSelectedNodeFromEditor({ parseConfig = false } = {}) {
  const node = selectedNode();
  if (!node) return true;
  node.name = el("node-name").value.trim();
  node.kind = el("node-kind").value;
  node.sort_order = Number.parseInt(el("node-sort-order").value || "0", 10);
  node.max_retries = Number.parseInt(el("node-retries").value || "0", 10);
  node.retry_delay_seconds = Number.parseInt(el("node-retry-delay").value || "0", 10);
  node.timeout_seconds = Number.parseInt(el("node-timeout").value || "10", 10);
  node.position.x = Number.parseFloat(el("node-x").value || "0");
  node.position.y = Number.parseFloat(el("node-y").value || "0");
  if (parseConfig) {
    try {
      const parsed = JSON.parse(el("node-config").value || "{}");
      if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error("Node configuration must be a JSON object.");
      }
      node.config = parsed;
    } catch (error) {
      setMessage(`Configuration JSON is invalid: ${error.message}`, "error");
      return false;
    }
  }
  return true;
}

function renderEdgeControls() {
  if (!state.workflow) return;
  const source = el("edge-source");
  const target = el("edge-target");
  const previousSource = source.value;
  const previousTarget = target.value;
  source.innerHTML = "";
  target.innerHTML = "";

  for (const node of state.workflow.nodes) {
    source.add(new Option(node.name, node.id));
    target.add(new Option(node.name, node.id));
  }
  if (nodeById(previousSource)) source.value = previousSource;
  if (nodeById(previousTarget)) target.value = previousTarget;
  el("add-edge").disabled = state.workflow.nodes.length < 2;

  const list = el("edge-list");
  list.innerHTML = "";
  if (!state.workflow.edges.length) {
    list.innerHTML = '<p class="muted">No connections yet.</p>';
    return;
  }
  for (const edge of state.workflow.edges) {
    const row = document.createElement("div");
    row.className = "edge-row";
    const label = document.createElement("span");
    label.textContent = `${nodeName(edge.source_node_id)} → ${nodeName(edge.target_node_id)}`;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "danger small";
    remove.textContent = "Delete";
    remove.addEventListener("click", () => {
      state.workflow.edges = state.workflow.edges.filter(
        (candidate) => !(candidate.source_node_id === edge.source_node_id && candidate.target_node_id === edge.target_node_id),
      );
      setDirty(true);
      renderCanvas();
      renderEdgeControls();
    });
    row.append(label, remove);
    list.append(row);
  }
}

function uniqueNodeName(base) {
  const names = new Set(state.workflow.nodes.map((node) => node.name));
  if (!names.has(base)) return base;
  let i = 2;
  while (names.has(`${base} ${i}`)) i += 1;
  return `${base} ${i}`;
}

function addNode() {
  if (!state.workflow) return;
  const kind = el("new-node-kind").value;
  const labels = {
    emit_json: "New value",
    combine_inputs: "Combine inputs",
    delay: "Delay",
    demo_fail: "Demo failure",
  };
  const index = state.workflow.nodes.length;
  const node = {
    id: `node-${randomSuffix()}`,
    name: uniqueNodeName(labels[kind] || "New node"),
    kind,
    config: defaultConfig(kind),
    position: { x: 50 + (index % 4) * 220, y: 50 + Math.floor(index / 4) * 130 },
    sort_order: index,
    max_retries: kind === "demo_fail" ? 1 : 0,
    retry_delay_seconds: 0,
    timeout_seconds: 10,
  };
  state.workflow.nodes.push(node);
  state.selectedNodeId = node.id;
  setDirty(true);
  renderCanvas();
  renderNodeEditor();
  renderEdgeControls();
  setMessage("Node added locally. Save the graph to persist it.", "warning");
}

function deleteSelectedNode() {
  const node = selectedNode();
  if (!node) return;
  state.workflow.nodes = state.workflow.nodes.filter((candidate) => candidate.id !== node.id);
  state.workflow.edges = state.workflow.edges.filter(
    (edge) => edge.source_node_id !== node.id && edge.target_node_id !== node.id,
  );
  state.selectedNodeId = state.workflow.nodes[0]?.id || null;
  setDirty(true);
  renderCanvas();
  renderNodeEditor();
  renderEdgeControls();
}

function addEdge() {
  const sourceId = el("edge-source").value;
  const targetId = el("edge-target").value;
  if (!sourceId || !targetId) return;
  if (sourceId === targetId) {
    setMessage("A node cannot depend on itself.", "error");
    return;
  }
  if (state.workflow.edges.some((edge) => edge.source_node_id === sourceId && edge.target_node_id === targetId)) {
    setMessage("That connection already exists.", "error");
    return;
  }
  state.workflow.edges.push({ source_node_id: sourceId, target_node_id: targetId });
  setDirty(true);
  renderCanvas();
  renderEdgeControls();
}

async function saveGraph() {
  if (!state.workflow) return;
  if (!syncSelectedNodeFromEditor({ parseConfig: true })) return;
  const body = {
    expected_version: state.workflow.version,
    nodes: state.workflow.nodes,
    edges: state.workflow.edges,
  };
  state.workflow = await api(`${API}/workflows/${encodeURIComponent(state.workflow.id)}/graph`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
  setDirty(false);
  state.workflows = await api(`${API}/workflows`);
  renderWorkflowList();
  renderEditor();
  setMessage("Graph saved. You can now validate or run the saved version.", "success");
}

function ensureSaved(action) {
  if (!state.workflow) throw new Error("Select a workflow first.");
  if (!syncSelectedNodeFromEditor({ parseConfig: true })) throw new Error("Fix the node configuration first.");
  if (state.dirty) {
    throw new Error(`Save the graph before ${action}. The server always uses the last saved version.`);
  }
}

async function validateGraph() {
  ensureSaved("validation");
  const result = await api(`${API}/workflows/${encodeURIComponent(state.workflow.id)}/validate`, { method: "POST" });
  renderValidation(result);
  if (result.valid) {
    setMessage("Workflow is valid.", "success");
  } else {
    setMessage("Workflow is invalid. See the validation panel for specific fixes.", "error");
  }
  return result;
}

function renderValidation(result) {
  const container = el("validation-results");
  if (result.valid) {
    const order = result.execution_order.map(nodeName).join(" → ") || "—";
    container.innerHTML = `<div class="validation-success"><strong>Valid.</strong><br>Execution order: ${escapeHtml(order)}</div>`;
    return;
  }
  const items = (result.errors || []).map((issue) => {
    const nodes = issue.node_ids && issue.node_ids.length ? ` Nodes: ${issue.node_ids.map(nodeName).join(", ")}.` : "";
    return `<li><strong>${escapeHtml(issue.code)}:</strong> ${escapeHtml(issue.message)}${escapeHtml(nodes)}</li>`;
  });
  container.innerHTML = `<ul class="validation-errors">${items.join("") || "<li>Invalid graph.</li>"}</ul>`;
}

async function runWorkflow() {
  ensureSaved("running");
  const validation = await validateGraph();
  if (!validation.valid) return;
  const created = await api(`${API}/workflows/${encodeURIComponent(state.workflow.id)}/runs`, { method: "POST" });
  setMessage(`Run #${created.id} queued. Watching for updates…`, "success");
  await loadRuns(created.id);
  window.history.pushState(null, "", `/runs/${encodeURIComponent(created.id)}`);
}

async function loadRuns(runId = null) {
  if (!state.workflow) return;
  state.runs = await api(`${API}/workflows/${encodeURIComponent(state.workflow.id)}/runs?limit=20`);
  renderRuns();
  const targetRunId = runId || state.run?.id || state.runs[0]?.id;
  if (targetRunId) {
    await loadRun(targetRunId, { fromList: true });
  } else {
    state.run = null;
    renderRunDetail();
    renderCanvas();
  }
}

function renderRuns() {
  const container = el("runs-list");
  container.innerHTML = "";
  if (!state.runs.length) {
    container.innerHTML = '<p class="muted">No runs yet for this workflow.</p>';
    return;
  }
  for (const run of state.runs) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `run-item${state.run && run.id === state.run.id ? " selected" : ""}`;
    button.innerHTML =
      `<span>${statusPill(run.status)} <strong>Run ${escapeHtml(run.id.slice(0, 8))}</strong></span>` +
      `<small>Version ${run.workflow_version} · Created ${escapeHtml(formatTime(run.created_at))}</small>`;
    button.addEventListener("click", () => {
      window.history.pushState(null, "", `/runs/${encodeURIComponent(run.id)}`);
      loadRun(run.id).catch(showError);
    });
    container.append(button);
  }
}

function stopPolling() {
  if (state.pollTimer) window.clearTimeout(state.pollTimer);
  state.pollTimer = null;
}

async function loadRun(runId, options = {}) {
  stopPolling();
  state.run = await api(`${API}/runs/${encodeURIComponent(runId)}`);
  renderRuns();
  renderRunDetail();
  renderCanvas();

  if (state.run.status === "queued" || state.run.status === "running") {
    state.pollTimer = window.setTimeout(() => {
      loadRun(runId, options)
        .then(() => refreshRunListOnly())
        .catch(showError);
    }, 1000);
  } else {
    await refreshRunListOnly();
  }
}

async function refreshRunListOnly() {
  if (!state.workflow) return;
  state.runs = await api(`${API}/workflows/${encodeURIComponent(state.workflow.id)}/runs?limit=20`);
  renderRuns();
}

function renderRunDetail() {
  const container = el("run-detail");
  if (!state.run) {
    container.innerHTML = '<p class="muted">Select a run to inspect task outputs, errors, and every attempt.</p>';
    return;
  }
  const run = state.run;
  let html = `
    <div class="run-summary">
      <h3>Run ${escapeHtml(run.id)}</h3>
      ${statusPill(run.status)}
      <span>Workflow version ${run.workflow_version}</span>
    </div>
    <p class="muted">Created ${escapeHtml(formatTime(run.created_at))} · Started ${escapeHtml(formatTime(run.started_at))} · Finished ${escapeHtml(formatTime(run.finished_at))}</p>
  `;
  if (run.error_summary) {
    html += `<p class="error-text">${escapeHtml(run.error_summary)}</p>`;
  }

  html += `<div style="overflow:auto"><table class="task-table"><thead><tr><th>Task</th><th>Status</th><th>Attempts</th><th>Error</th></tr></thead><tbody>`;
  for (const task of run.tasks || []) {
    html += `<tr><td><strong>${escapeHtml(task.node_name)}</strong><br><small>${escapeHtml(task.node_kind)}</small></td><td>${statusPill(task.status)}</td><td>${task.attempt_count ?? (task.attempts || []).length}</td><td>${escapeHtml(task.error_message || "")}</td></tr>`;
  }
  html += `</tbody></table></div>`;

  for (const task of run.tasks || []) {
    html += `<details class="task-detail"><summary>${escapeHtml(task.node_name)} — ${escapeHtml(task.status)} (${(task.attempts || []).length} attempt(s))</summary>`;
    html += `<p class="muted">Started ${escapeHtml(formatTime(task.started_at))} · Finished ${escapeHtml(formatTime(task.finished_at))}</p>`;
    if (task.output !== null && task.output !== undefined) {
      html += `<h4>Output</h4><pre>${escapeHtml(JSON.stringify(task.output, null, 2))}</pre>`;
    }
    if (task.error_message) {
      const recovered = task.status === "succeeded";
      html += `<p class="error-text">${recovered ? "Recovered error: " : "Final error: "}${escapeHtml(task.error_message)}</p>`;
    }
    if ((task.attempts || []).length) {
      html += `<h4>Attempts</h4><ul class="attempt-list">`;
      for (const attempt of task.attempts) {
        const detail = attempt.error_message ? ` — ${attempt.error_type ? `${attempt.error_type}: ` : ""}${attempt.error_message}` : "";
        html += `<li>Attempt ${attempt.attempt_number}: <strong>${escapeHtml(attempt.status)}</strong>${escapeHtml(detail)}</li>`;
      }
      html += `</ul>`;
    } else {
      html += `<p class="muted">No attempts were made.</p>`;
    }
    html += `</details>`;
  }
  container.innerHTML = html;
}

async function createWorkflow() {
  const name = el("new-workflow-name").value.trim();
  if (!name) {
    setMessage("Give the workflow a name first.", "error");
    return;
  }
  const description = el("new-workflow-description").value.trim() || null;
  const workflow = await api(`${API}/workflows`, {
    method: "POST",
    body: JSON.stringify({ name, description }),
  });
  el("new-workflow-name").value = "";
  el("new-workflow-description").value = "";
  state.workflows = await api(`${API}/workflows`);
  await selectWorkflow(workflow.id);
  setMessage(`Created workflow “${workflow.name}”. Add nodes to begin.`, "success");
}

function sampleDefinitions() {
  return [
    {
      name: "Success demo",
      description: "Two source values combine successfully.",
      nodes: [
        ["a", "Source A", "emit_json", { value: { value: 3 } }, 50, 60, 0, 0],
        ["b", "Source B", "emit_json", { value: { value: 4 } }, 50, 220, 1, 0],
        ["c", "Combine", "combine_inputs", {}, 360, 140, 2, 0],
      ],
      edges: [["a", "c"], ["b", "c"]],
    },
    {
      name: "Retry demo",
      description: "A demo task fails once, then succeeds on retry.",
      nodes: [
        ["a", "Source", "emit_json", { value: { value: 10 } }, 50, 140, 0, 0],
        ["f", "Flaky task", "demo_fail", { fail_first_n_attempts: 1, value: { message: "Recovered" } }, 320, 140, 1, 1],
        ["c", "Combine", "combine_inputs", {}, 600, 140, 2, 0],
      ],
      edges: [["a", "f"], ["f", "c"]],
    },
    {
      name: "Failure demo",
      description: "A demo task exhausts retries; downstream work is skipped.",
      nodes: [
        ["a", "Source", "emit_json", { value: { value: 7 } }, 50, 140, 0, 0],
        ["f", "Broken task", "demo_fail", { fail_first_n_attempts: 99, value: { message: "Never reached" } }, 320, 140, 1, 1],
        ["c", "Combine", "combine_inputs", {}, 600, 140, 2, 0],
      ],
      edges: [["a", "f"], ["f", "c"]],
    },
  ];
}

async function loadSamples() {
  const existingNames = new Set(state.workflows.map((workflow) => workflow.name));
  let firstCreatedOrExisting = null;
  for (const definition of sampleDefinitions()) {
    const existing = state.workflows.find((workflow) => workflow.name === definition.name);
    if (existing) {
      firstCreatedOrExisting ||= existing.id;
      continue;
    }
    const workflow = await api(`${API}/workflows`, {
      method: "POST",
      body: JSON.stringify({ name: definition.name, description: definition.description }),
    });
    firstCreatedOrExisting ||= workflow.id;
    const suffix = randomSuffix();
    const idMap = {};
    const nodes = definition.nodes.map(([logicalId, name, kind, config, x, y, order, retries]) => {
      const id = `${logicalId}-${suffix}`;
      idMap[logicalId] = id;
      return {
        id, name, kind, config,
        position: { x, y },
        sort_order: order,
        max_retries: retries,
        retry_delay_seconds: 0,
        timeout_seconds: 10,
      };
    });
    const edges = definition.edges.map(([source, target]) => ({
      source_node_id: idMap[source],
      target_node_id: idMap[target],
    }));
    await api(`${API}/workflows/${encodeURIComponent(workflow.id)}/graph`, {
      method: "PUT",
      body: JSON.stringify({ expected_version: workflow.version, nodes, edges }),
    });
    existingNames.add(definition.name);
  }
  await loadWorkflows(firstCreatedOrExisting);
  setMessage("Sample workflows are ready. Retry/failure samples require ENABLE_DEMO_NODE=true.", "success");
}

function showError(error) {
  console.error(error);
  setMessage(error.message || String(error), "error");
}

function bindEvents() {
  el("create-workflow").addEventListener("click", () => createWorkflow().catch(showError));
  el("load-samples").addEventListener("click", () => loadSamples().catch(showError));
  el("refresh-workflows").addEventListener("click", () => loadWorkflows(state.workflow?.id).catch(showError));
  el("add-node").addEventListener("click", addNode);
  el("delete-node").addEventListener("click", deleteSelectedNode);
  el("add-edge").addEventListener("click", addEdge);
  el("save-graph").addEventListener("click", () => saveGraph().catch(showError));
  el("validate-graph").addEventListener("click", () => validateGraph().catch(showError));
  el("run-workflow").addEventListener("click", () => runWorkflow().catch(showError));
  el("refresh-runs").addEventListener("click", () => loadRuns(state.run?.id).catch(showError));

  const editorFields = [
    "node-name", "node-sort-order", "node-retries", "node-retry-delay",
    "node-timeout", "node-x", "node-y",
  ];
  for (const id of editorFields) {
    el(id).addEventListener("input", () => {
      if (syncSelectedNodeFromEditor()) {
        setDirty(true);
        renderCanvas();
        renderEdgeControls();
      }
    });
  }

  el("node-kind").addEventListener("change", () => {
    const node = selectedNode();
    if (!node) return;
    node.kind = el("node-kind").value;
    node.config = defaultConfig(node.kind);
    el("node-config").value = JSON.stringify(node.config, null, 2);
    setDirty(true);
    renderCanvas();
  });

  el("node-config").addEventListener("change", () => {
    if (syncSelectedNodeFromEditor({ parseConfig: true })) {
      setDirty(true);
      clearMessage();
    }
  });
}

async function init() {
  bindEvents();
  try {
    await api("/healthz");
  } catch {
    setMessage("The API health check failed. Confirm the database has been migrated and the server is running.", "error");
  }

  state.workflows = await api(`${API}/workflows`);
  renderWorkflowList();

  const runMatch = window.location.pathname.match(/^\/runs\/([^/]+)$/);
  const workflowMatch = window.location.pathname.match(/^\/workflows\/([^/]+)(?:\/history)?$/);
  if (runMatch) {
    const run = await api(`${API}/runs/${encodeURIComponent(runMatch[1])}`);
    await selectWorkflow(run.workflow_id, { push: false, runId: run.id });
  } else if (workflowMatch) {
    await selectWorkflow(workflowMatch[1], { push: false });
  } else if (state.workflows.length) {
    await selectWorkflow(state.workflows[0].id, { push: false });
  } else {
    renderEditor();
  }
}

init().catch(showError);
