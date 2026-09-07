const statusPanel = document.querySelector("#status");
const inferenceSummary = document.querySelector("#inference-summary");
const activeInference = document.querySelector("#active-inference");
const queuedJobs = document.querySelector("#queued-jobs");
const rescanStatus = document.querySelector("#rescan-status");
const trainingStatus = document.querySelector("#training-status");

function jobDescription(job) {
  const kind = job.kind === "rescan" ? "Historical re-evaluation" : "New live event";
  return `${kind}: ${job.image || "image unavailable"} (${job.frames || 0} frames)`;
}

function renderQueue(queue) {
  queuedJobs.replaceChildren();
  for (const job of queue.queued_jobs || []) {
    const row = document.createElement("tr");
    for (const value of [
      job.kind === "rescan" ? "Background" : "Live capture",
      job.image || "image unavailable",
      String(job.frames || 0),
    ]) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    queuedJobs.append(row);
  }
  if (!queuedJobs.children.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 3;
    cell.textContent = "No jobs waiting.";
    row.append(cell);
    queuedJobs.append(row);
  }
}

function renderJobs(state) {
  if (state.available === false) {
    inferenceSummary.textContent = "Job status is unavailable.";
    activeInference.textContent = "";
    rescanStatus.textContent = "Job status is unavailable.";
    trainingStatus.textContent = "Job status is unavailable.";
    return;
  }
  const queue = state.prediction_queue || {};
  inferenceSummary.textContent = `${queue.running ? "Model prediction running" : "No model prediction running"}. ${queue.queued_bursts || 0} of ${queue.queue_limit || 0} bursts waiting (${queue.live_queued_bursts || 0} live, ${queue.background_queued_bursts || 0} historical).`;
  activeInference.textContent = queue.active_job ? `Currently processing: ${jobDescription(queue.active_job)}` : "No active model job.";
  renderQueue(queue);

  const rescan = state.rescan || {};
  rescanStatus.textContent = rescan.running
    ? `Adding historical bursts to the low-priority queue: ${rescan.queued || 0} / ${rescan.total || 0}.`
    : `No re-evaluation is currently being added to the queue. Last batch: ${rescan.queued || 0} / ${rescan.total || 0} bursts.`;

  const training = state.training || {};
  const progress = training.progress;
  trainingStatus.textContent = `${training.state || "not configured"}: ${training.message || "No training job status available."}${progress ? ` (${progress.epochs_completed || 0} / ${progress.epochs_total || 0} epochs)` : ""}`;
}

async function loadSystem() {
  try {
    const [systemResponse, jobsResponse] = await Promise.all([
      fetch("/api/system-status", { cache: "no-store" }),
      fetch("/api/jobs", { cache: "no-store" }),
    ]);
    const system = await systemResponse.json();
    const device = system.device;
    const background = system.background;
    const night = device.night_mode || {};
    const storage = device.storage || {};
    statusPanel.innerHTML = `<p><strong>Night mode:</strong> ${night.active ? "active — motion paused" : night.preview_disabled ? "night mode pending — preview disabled" : "daylight monitoring"} (brightness: ${night.brightness ?? "?"}/255)</p><p><strong>Background:</strong> ${background.available ? "available" : "not captured"} ${background.updated_at || ""}</p><p class="${storage.warning ? "text-warning fw-bold" : ""}"><strong>Storage:</strong> ${storage.free_gb ?? device.disk_free_gb ?? "?"} GB free${storage.warning ? " — cleanup and backup recommended." : ""}</p><p><strong>CPU:</strong> ${device.cpu_load_1m ?? "unavailable"} · <strong>Memory:</strong> ${device.memory_used_percent ?? "unavailable"}%</p><p><strong>Code update:</strong> ${system.update.state}</p>`;
    renderJobs(await jobsResponse.json());
  } catch (_) {
    statusPanel.textContent = "System status unavailable.";
    renderJobs({ available: false });
  }
}

document.querySelector("#background").onclick = async () => {
  const response = await fetch("/api/background", { method: "POST" });
  alert(response.ok ? "Background updated." : (await response.json()).error);
  loadSystem();
};
document.querySelector("#backup").onclick = async () => {
  const response = await fetch("/api/backup", { method: "POST" });
  const value = await response.json();
  document.querySelector("#backup-result").textContent = value.path || value.error;
};
document.querySelector("#telegram").onsubmit = async (event) => {
  event.preventDefault();
  const response = await fetch("/api/telegram", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      enabled: enabled.checked,
      bot_token: token.value,
      chat_id: chat.value,
      confidence_threshold: +threshold.value,
      cooldown_seconds: +cooldown.value,
    }),
  });
  document.querySelector("#telegram-result").textContent =
    (await response.json()).message || "Could not save settings.";
  if (response.ok) setTimeout(() => (location.href = "/"), 8000);
};

loadSystem();
setInterval(loadSystem, 2000);
