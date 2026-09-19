"use strict";

const STATUS_LABELS = {
  todo: "To do",
  doing: "Doing",
  done: "Done",
};

const PRIORITY_LABELS = {
  P0: "NEXT",
  P1: "SOON",
  P2: "LATER",
};

const state = {
  board: null,
  draggedTaskId: null,
  editingTaskId: null,
  pendingDeleteId: null,
  saveChain: Promise.resolve(),
};

const elements = {
  addButton: document.querySelector("#add-task-button"),
  cancelButton: document.querySelector("#cancel-task-button"),
  closeButton: document.querySelector("#close-dialog-button"),
  confirmDialog: document.querySelector("#confirm-dialog"),
  confirmDeleteButton: document.querySelector("#confirm-delete-button"),
  criteria: document.querySelector("#task-criteria"),
  deleteButton: document.querySelector("#delete-task-button"),
  description: document.querySelector("#task-description"),
  dialog: document.querySelector("#task-dialog"),
  dialogKicker: document.querySelector("#dialog-kicker"),
  dialogTitle: document.querySelector("#dialog-title"),
  errorBanner: document.querySelector("#error-banner"),
  form: document.querySelector("#task-form"),
  id: document.querySelector("#task-id"),
  labels: document.querySelector("#task-labels"),
  notes: document.querySelector("#task-notes"),
  phase: document.querySelector("#task-phase"),
  phaseFilter: document.querySelector("#phase-filter"),
  priority: document.querySelector("#task-priority"),
  priorityFilter: document.querySelector("#priority-filter"),
  progressFill: document.querySelector("#progress-fill"),
  progressPercent: document.querySelector("#progress-percent"),
  progressTrack: document.querySelector("#progress-track"),
  saveLabel: document.querySelector("#save-label"),
  saveState: document.querySelector("#save-state"),
  search: document.querySelector("#search-input"),
  status: document.querySelector("#task-status"),
  title: document.querySelector("#task-title"),
};

function setSaveState(mode, label) {
  elements.saveState.dataset.state = mode;
  elements.saveLabel.textContent = label;
}

function showError(message) {
  elements.errorBanner.textContent = message;
  elements.errorBanner.hidden = false;
}

function clearError() {
  elements.errorBanner.hidden = true;
  elements.errorBanner.textContent = "";
}

function normalizeBoard(payload) {
  if (!payload || !Array.isArray(payload.tasks)) {
    throw new Error("The server returned an invalid task board.");
  }

  const seen = new Set();
  payload.tasks.forEach((task, index) => {
    if (!task.id || seen.has(task.id)) {
      throw new Error(`Task ${index + 1} has a missing or duplicate ID.`);
    }
    seen.add(task.id);
    if (!Object.hasOwn(STATUS_LABELS, task.status)) task.status = "todo";
    if (!["P0", "P1", "P2"].includes(task.priority)) task.priority = "P2";
    task.title = String(task.title || "Untitled task");
    task.phase = String(task.phase || "Unassigned");
    task.description = String(task.description || "");
    task.acceptance_criteria = Array.isArray(task.acceptance_criteria)
      ? task.acceptance_criteria.map(String)
      : [];
    task.labels = Array.isArray(task.labels) ? task.labels.map(String) : [];
    task.notes = String(task.notes || "");
    task.order = Number.isFinite(task.order) ? task.order : index;
  });

  return payload;
}

async function loadBoard() {
  try {
    const response = await fetch("/api/tasks", { cache: "no-store" });
    if (!response.ok) throw new Error(`Server returned ${response.status}.`);
    state.board = normalizeBoard(await response.json());
    clearError();
    setSaveState("saved", "Saved to tasks.json");
    populatePhaseFilter();
    render();
  } catch (error) {
    setSaveState("error", "Board unavailable");
    showError(
      `Could not load tasks.json. Start the board with “python scripts/run_board.py”. ${error.message}`,
    );
  }
}

function queueSave() {
  if (!state.board) return;

  state.board.updated_at = new Date().toISOString();
  const snapshot = JSON.stringify(state.board, null, 2);
  setSaveState("saving", "Saving…");

  state.saveChain = state.saveChain
    .catch(() => undefined)
    .then(async () => {
      const response = await fetch("/api/tasks", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: snapshot,
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `Server returned ${response.status}.`);
      }
      clearError();
      setSaveState("saved", "Saved to tasks.json");
    })
    .catch((error) => {
      setSaveState("error", "Save failed");
      showError(`Your latest change is still visible but was not saved. ${error.message}`);
      throw error;
    });
}

function populatePhaseFilter() {
  const current = elements.phaseFilter.value;
  const phases = [...new Set(state.board.tasks.map((task) => task.phase))].sort();
  elements.phaseFilter.replaceChildren(new Option("All phases", "all"));
  phases.forEach((phase) => elements.phaseFilter.add(new Option(phase, phase)));
  elements.phaseFilter.value = phases.includes(current) ? current : "all";
}

function filteredTasks() {
  const query = elements.search.value.trim().toLocaleLowerCase();
  const phase = elements.phaseFilter.value;
  const priority = elements.priorityFilter.value;

  return state.board.tasks.filter((task) => {
    if (phase !== "all" && task.phase !== phase) return false;
    if (priority !== "all" && task.priority !== priority) return false;
    if (!query) return true;

    const haystack = [
      task.id,
      task.title,
      task.phase,
      task.priority,
      task.description,
      task.notes,
      ...task.labels,
      ...task.acceptance_criteria,
    ]
      .join(" ")
      .toLocaleLowerCase();
    return haystack.includes(query);
  });
}

function render() {
  if (!state.board) return;

  const filtered = filteredTasks();
  Object.keys(STATUS_LABELS).forEach((status) => {
    const list = document.querySelector(`#list-${status}`);
    const tasks = filtered
      .filter((task) => task.status === status)
      .sort((a, b) => a.order - b.order || a.id.localeCompare(b.id));

    list.replaceChildren();
    tasks.forEach((task) => list.append(createTaskCard(task)));
    if (!tasks.length) {
      list.append(document.querySelector("#empty-state-template").content.cloneNode(true));
    }
    document.querySelector(`#count-${status}`).textContent = String(tasks.length);
  });

  const total = state.board.tasks.length;
  const done = state.board.tasks.filter((task) => task.status === "done").length;
  const doing = state.board.tasks.filter((task) => task.status === "doing").length;
  const percentage = total ? Math.round((done / total) * 100) : 0;

  document.querySelector("#stat-total").textContent = String(total);
  document.querySelector("#stat-doing").textContent = String(doing);
  document.querySelector("#stat-done").textContent = String(done);
  elements.progressPercent.textContent = `${percentage}%`;
  elements.progressFill.style.width = `${percentage}%`;
  elements.progressTrack.setAttribute("aria-valuenow", String(percentage));
}

function createTaskCard(task) {
  const card = document.createElement("article");
  card.className = "task-card";
  card.draggable = true;
  card.tabIndex = 0;
  card.dataset.taskId = task.id;
  card.setAttribute("aria-label", `${task.id}: ${task.title}. ${STATUS_LABELS[task.status]}.`);

  const meta = document.createElement("div");
  meta.className = "card-meta";

  const id = document.createElement("span");
  id.className = "task-id";
  id.textContent = task.id;

  const priority = document.createElement("span");
  priority.className = `priority priority-${task.priority.toLowerCase()}`;
  priority.textContent = PRIORITY_LABELS[task.priority];
  priority.title = `${PRIORITY_LABELS[task.priority]} priority`;

  meta.append(id, priority);

  const title = document.createElement("h4");
  title.textContent = task.title;

  const description = document.createElement("p");
  description.className = "card-description";
  description.textContent = task.description;

  const footer = document.createElement("div");
  footer.className = "card-footer";

  const phase = document.createElement("span");
  phase.className = "phase-label";
  phase.textContent = task.phase;

  const criteria = document.createElement("span");
  criteria.className = "criteria-count";
  criteria.textContent = `${task.acceptance_criteria.length} checks${task.notes ? " · " : ""}`;
  if (task.notes) {
    const note = document.createElement("span");
    note.className = "notes-indicator";
    note.textContent = "note";
    criteria.append(note);
  }

  footer.append(phase, criteria);
  card.append(meta, title, description, footer);

  card.addEventListener("click", () => openTaskDialog(task.id));
  card.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openTaskDialog(task.id);
    }
  });
  card.addEventListener("dragstart", (event) => {
    state.draggedTaskId = task.id;
    card.classList.add("dragging");
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", task.id);
  });
  card.addEventListener("dragend", () => {
    state.draggedTaskId = null;
    card.classList.remove("dragging");
    document.querySelectorAll(".drag-target").forEach((node) => node.classList.remove("drag-target"));
  });

  return card;
}

function nextTaskId() {
  const highest = state.board.tasks.reduce((max, task) => {
    const match = /^OTR-(\d+)$/i.exec(task.id);
    return match ? Math.max(max, Number(match[1])) : max;
  }, 0);
  return `OTR-${String(highest + 1).padStart(3, "0")}`;
}

function openTaskDialog(taskId = null) {
  state.editingTaskId = taskId;
  const task = taskId ? state.board.tasks.find((item) => item.id === taskId) : null;

  elements.dialogKicker.textContent = task ? task.id : "NEW TASK";
  elements.dialogTitle.textContent = task ? "Edit task" : "Create task";
  elements.id.value = task?.id || nextTaskId();
  elements.title.value = task?.title || "";
  elements.status.value = task?.status || "todo";
  elements.priority.value = task?.priority || "P1";
  elements.phase.value = task?.phase || "Phase 0 — Repository bootstrap";
  elements.labels.value = task?.labels.join(", ") || "";
  elements.description.value = task?.description || "";
  elements.criteria.value = task?.acceptance_criteria.join("\n") || "";
  elements.notes.value = task?.notes || "";
  elements.deleteButton.hidden = !task;

  elements.dialog.showModal();
  elements.title.focus();
}

function closeTaskDialog() {
  elements.dialog.close();
  state.editingTaskId = null;
}

function saveFormTask() {
  const existing = state.editingTaskId
    ? state.board.tasks.find((task) => task.id === state.editingTaskId)
    : null;
  const status = elements.status.value;
  const maxOrder = state.board.tasks
    .filter((task) => task.status === status)
    .reduce((max, task) => Math.max(max, task.order), -1);

  const task = {
    id: elements.id.value,
    title: elements.title.value.trim(),
    status,
    priority: elements.priority.value,
    phase: elements.phase.value.trim(),
    description: elements.description.value.trim(),
    acceptance_criteria: elements.criteria.value
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean),
    labels: elements.labels.value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
    notes: elements.notes.value.trim(),
    order: existing?.status === status ? existing.order : maxOrder + 1,
  };

  if (existing) Object.assign(existing, task);
  else state.board.tasks.push(task);

  populatePhaseFilter();
  render();
  queueSave();
  closeTaskDialog();
}

function moveTask(taskId, status) {
  const task = state.board.tasks.find((item) => item.id === taskId);
  if (!task || task.status === status) return;
  const maxOrder = state.board.tasks
    .filter((item) => item.status === status)
    .reduce((max, item) => Math.max(max, item.order), -1);
  task.status = status;
  task.order = maxOrder + 1;
  render();
  queueSave();
}

document.querySelectorAll(".task-list").forEach((list) => {
  list.addEventListener("dragover", (event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    list.classList.add("drag-target");
  });
  list.addEventListener("dragleave", (event) => {
    if (!list.contains(event.relatedTarget)) list.classList.remove("drag-target");
  });
  list.addEventListener("drop", (event) => {
    event.preventDefault();
    list.classList.remove("drag-target");
    const taskId = event.dataTransfer.getData("text/plain") || state.draggedTaskId;
    moveTask(taskId, list.dataset.status);
  });
});

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!elements.form.reportValidity()) return;
  saveFormTask();
});

elements.addButton.addEventListener("click", () => openTaskDialog());
elements.cancelButton.addEventListener("click", closeTaskDialog);
elements.closeButton.addEventListener("click", closeTaskDialog);
elements.deleteButton.addEventListener("click", () => {
  state.pendingDeleteId = state.editingTaskId;
  elements.confirmDialog.showModal();
});
elements.confirmDialog.addEventListener("close", () => {
  if (elements.confirmDialog.returnValue !== "confirm" || !state.pendingDeleteId) {
    state.pendingDeleteId = null;
    return;
  }
  state.board.tasks = state.board.tasks.filter((task) => task.id !== state.pendingDeleteId);
  state.pendingDeleteId = null;
  closeTaskDialog();
  populatePhaseFilter();
  render();
  queueSave();
});

[elements.search, elements.phaseFilter, elements.priorityFilter].forEach((control) => {
  control.addEventListener("input", render);
  control.addEventListener("change", render);
});

window.addEventListener("beforeunload", (event) => {
  if (elements.saveState.dataset.state === "saving") {
    event.preventDefault();
  }
});

loadBoard();
