const list = document.querySelector("#event-list");
const image = document.querySelector("#annotation-image");
const canvas = document.querySelector("#annotation-canvas");
const overlay = document.querySelector("#annotation-box");
const annotationBoxes = document.querySelector("#annotation-boxes");
const message = document.querySelector("#gallery-message");
const annotationMessage = document.querySelector("#annotation-message");
const rows = document.querySelector("#annotation-list");
const eventFilter = document.querySelector("#event-filter");
const eventFrames = document.querySelector("#event-frames");
const suggestionPanel = document.querySelector("#model-suggestion");
const suggestionDetails = document.querySelector("#model-suggestion-details");
const acceptSuggestion = document.querySelector("#accept-suggestion");

let events = [];
let selected = null;
let selectedFrame = null;
let box = null;
let items = [];
let currentSuggestion = null;
let annotationSource = "manual";

function visibleEvents() {
  if (eventFilter.value === "animals") {
    return events.filter((event) => event.animal_frames.length);
  }
  if (eventFilter.value === "suggestions") {
    return events.filter((event) => Object.keys(event.suggestions || {}).length);
  }
  if (eventFilter.value === "reviewed") {
    return events.filter((event) => event.reviewed);
  }
  if (eventFilter.value === "all") return events;
  return events.filter((event) => !event.reviewed);
}

function clearSelection() {
  selected = null;
  selectedFrame = null;
  items = [];
  box = null;
  image.removeAttribute("src");
  overlay.style.display = "none";
  annotationBoxes.replaceChildren();
  rows.replaceChildren();
  eventFrames.replaceChildren();
  currentSuggestion = null;
  suggestionPanel.classList.add("d-none");
}

function showBox() {
  if (!box || !image.naturalWidth || !image.naturalHeight) return;
  overlay.style.display = "block";
  overlay.style.left = String((box.x / image.naturalWidth) * 100) + "%";
  overlay.style.top = String((box.y / image.naturalHeight) * 100) + "%";
  overlay.style.width = String((box.width / image.naturalWidth) * 100) + "%";
  overlay.style.height = String((box.height / image.naturalHeight) * 100) + "%";
}

function renderRows() {
  rows.replaceChildren(
    ...items.map((item, index) => {
      const row = document.createElement("li");
      row.className = "list-group-item d-flex justify-content-between align-items-center";
      row.append("#" + (index + 1) + " · ");
      row.append(
        item.label + ": " + (item.box ? item.box.width + " × " + item.box.height : "empty"),
      );
      const remove = document.createElement("button");
      remove.className = "btn btn-sm btn-outline-danger";
      remove.type = "button";
      remove.textContent = "Remove";
      remove.onclick = () => {
        items.splice(index, 1);
        renderRows();
        renderSavedBoxes();
      };
      row.append(remove);
      return row;
    }),
  );
}

function renderSavedBoxes() {
  if (!image.naturalWidth || !image.naturalHeight) return;
  const modelBoxes = currentSuggestion && !items.length ? [{
    label: currentSuggestion.label,
    box: currentSuggestion.box,
    model: true,
  }] : [];
  annotationBoxes.replaceChildren(
    ...[...items, ...modelBoxes].flatMap((item, index) => {
      if (!item.box) return [];
      const itemBox = document.createElement("div");
      itemBox.className = "annotation-box";
      itemBox.style.display = "block";
      itemBox.style.left = String((item.box.x / image.naturalWidth) * 100) + "%";
      itemBox.style.top = String((item.box.y / image.naturalHeight) * 100) + "%";
      itemBox.style.width = String((item.box.width / image.naturalWidth) * 100) + "%";
      itemBox.style.height = String((item.box.height / image.naturalHeight) * 100) + "%";
      if (item.label === "uncertain" || item.model) {
        itemBox.style.borderColor = "#0dcaf0";
        itemBox.style.borderStyle = "dashed";
      }
      const number = document.createElement("span");
      number.className = "annotation-box-number";
      number.textContent = item.model ? "AI" : String(index + 1);
      number.style.cssText = "display:grid;place-items:center;width:1.5rem;height:1.5rem;"
        + "margin:-3px 0 0 -3px;border-radius:0 0 .3rem 0;background:"
        + (item.label === "uncertain" || item.model ? "#0dcaf0" : "#ffc107")
        + ";color:#101713;font-size:.9rem;font-weight:700;line-height:1;";
      itemBox.append(number);
      return itemBox;
    }),
  );
}

function renderFrames() {
  if (!selected) {
    eventFrames.replaceChildren();
    return;
  }
  eventFrames.replaceChildren(
    ...selected.frames.map((frame, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "frame-card" + (frame === selectedFrame ? " selected" : "");
      button.setAttribute("aria-pressed", String(frame === selectedFrame));
      button.title = "Frame " + index;
      if (selected.reviewed_frames.includes(frame)) {
        button.classList.add("reviewed");
      }
      const preview = document.createElement("img");
      preview.src = "/event-image/" + frame;
      preview.alt = "Frame " + index;
      preview.loading = "lazy";
      const caption = document.createElement("span");
      caption.textContent = "Frame " + index;
      if (selected.reviewed_frames.includes(frame)) {
        const reviewed = document.createElement("span");
        reviewed.className = "ms-1 text-success";
        reviewed.textContent = "Reviewed";
        caption.append(reviewed);
      }
      button.append(preview, caption);
      button.onclick = () => selectFrame(frame);
      return button;
    }),
  );
}

async function selectFrame(frame, force = false) {
  if (!selected || (!force && frame === selectedFrame)) return;
  selectedFrame = frame;
  box = null;
  overlay.style.display = "none";
  annotationBoxes.replaceChildren();
  image.src = "/event-image/" + frame;
  items = await (await fetch("/api/annotations/" + frame)).json();
  annotationSource = "manual";
  currentSuggestion = (selected.suggestions || {})[frame] || null;
  if (currentSuggestion) {
    suggestionDetails.textContent = currentSuggestion.label + " · "
      + Math.round(currentSuggestion.confidence * 100) + "%"
      + (currentSuggestion.model_version ? " · " + currentSuggestion.model_version : "");
    acceptSuggestion.disabled = items.length > 0;
    suggestionPanel.classList.remove("d-none");
  } else {
    suggestionPanel.classList.add("d-none");
  }
  renderRows();
  renderSavedBoxes();
  renderFrames();
}

async function select(event) {
  selected = event;
  selectedFrame = null;
  const suggestedFrame = event.best_suggestion_image || Object.keys(event.suggestions || {})[0];
  await selectFrame(event.animal_frames[0] || suggestedFrame || event.image, true);
  render();
}

function eventCard(event) {
  const card = document.createElement("button");
  card.type = "button";
  card.className = "event-card" + (selected === event ? " selected" : "");
  const preview = event.night_preview ? document.createElement("span") : document.createElement("img");
  if (event.night_preview) {
    preview.className = "event-night-preview";
    preview.textContent = "Night mode · preview disabled";
  } else {
    preview.src = "/event-image/" + event.image;
    preview.alt = "Event " + event.id;
    preview.loading = "lazy";
  }
  const title = document.createElement("span");
  title.className = "event-card-title";
  title.textContent = event.id;
  const state = document.createElement("span");
  state.className = "badge " + (event.reviewed ? "text-bg-success" : "text-bg-warning");
  state.textContent = event.reviewed ? "Reviewed" : "Unreviewed";
  card.append(preview, title, state);
  card.onclick = () => select(event);
  return card;
}

function render() {
  const visible = visibleEvents();
  if (selected && !events.some((event) => event.id === selected.id)) clearSelection();
  list.replaceChildren(...visible.map(eventCard));
  message.textContent = String(visible.length) + " events";
  if (!visible.length) {
    const empty = document.createElement("p");
    empty.className = "text-body-secondary";
    empty.textContent = "No events available.";
    list.replaceChildren(empty);
  } else if (!selected) {
    select(visible[0]);
  }
}

async function load() {
  events = await (await fetch("/api/events")).json();
  render();
}

async function reloadSelectedEvent() {
  const selectedId = selected && selected.id;
  const previousFrame = selectedFrame;
  events = await (await fetch("/api/events")).json();
  const refreshed = events.find((event) => event.id === selectedId);
  if (!refreshed) {
    clearSelection();
    render();
    return;
  }
  selected = refreshed;
  const nextFrame = refreshed.frames.find(
    (frame) => !refreshed.reviewed_frames.includes(frame),
  ) || previousFrame || refreshed.image;
  await selectFrame(nextFrame, true);
  render();
}

let drawing = null;

function imageCoordinates(event, bounds) {
  return {
    x: Math.max(0, Math.min(bounds.width, event.clientX - bounds.left)),
    y: Math.max(0, Math.min(bounds.height, event.clientY - bounds.top)),
  };
}

function finishDrawing(event) {
  if (!drawing || event.pointerId !== drawing.pointerId) return;
  const wasDragged = drawing.dragged;
  drawing = null;
  if (canvas.hasPointerCapture(event.pointerId)) {
    canvas.releasePointerCapture(event.pointerId);
  }
  if (!wasDragged) {
    box = null;
    overlay.style.display = "none";
    annotationMessage.textContent = "Drag to draw a rectangle.";
  }
}

canvas.addEventListener("pointerdown", (event) => {
  if (!selectedFrame || !image.naturalWidth) return;
  event.preventDefault();
  annotationSource = "manual";
  const bounds = image.getBoundingClientRect();
  const start = imageCoordinates(event, bounds);
  drawing = { pointerId: event.pointerId, bounds, start, dragged: false };
  canvas.setPointerCapture(event.pointerId);
});

canvas.addEventListener("pointermove", (event) => {
  if (!drawing || event.pointerId !== drawing.pointerId) return;
  event.preventDefault();
  const point = imageCoordinates(event, drawing.bounds);
  const moved = Math.abs(point.x - drawing.start.x) > 3 || Math.abs(point.y - drawing.start.y) > 3;
  if (!moved && !drawing.dragged) return;
  drawing.dragged = true;
  const { bounds, start } = drawing;
    box = {
    x: Math.round((Math.min(start.x, point.x) / bounds.width) * image.naturalWidth),
    y: Math.round((Math.min(start.y, point.y) / bounds.height) * image.naturalHeight),
    width: Math.max(1, Math.round((Math.abs(point.x - start.x) / bounds.width) * image.naturalWidth)),
    height: Math.max(1, Math.round((Math.abs(point.y - start.y) / bounds.height) * image.naturalHeight)),
    };
    showBox();
});

canvas.addEventListener("pointerup", finishDrawing);
canvas.addEventListener("pointercancel", finishDrawing);
canvas.addEventListener("lostpointercapture", finishDrawing);

document.querySelector("#add-box").onclick = () => {
  const label = document.querySelector("#annotation-label").value;
  if (!box && label !== "empty") {
    annotationMessage.textContent = "Draw a box first.";
    return;
  }
  items.push({ label, box: label === "empty" ? null : box });
  annotationSource = "manual";
  box = null;
  overlay.style.display = "none";
  annotationMessage.textContent = "";
  renderRows();
  renderSavedBoxes();
};

document.querySelector("#suggest-boxes").onclick = async () => {
  if (!selectedFrame) return;
  annotationSource = "manual";
  const boxes = await (await fetch("/api/events/" + selectedFrame + "/proposals")).json();
  items.push(...boxes.map((suggestion) => ({ label: "uncertain", box: suggestion })));
  renderRows();
  renderSavedBoxes();
  annotationMessage.textContent = boxes.length
    ? "Suggestions added as uncertain."
    : "No suggestions; update the background first.";
};

async function saveAnnotations() {
  if (!selectedFrame) return false;
  const label = document.querySelector("#annotation-label").value;
  let savedEmpty = false;
  if (box && label !== "empty") {
    items.push({ label, box });
    box = null;
    overlay.style.display = "none";
    renderRows();
    renderSavedBoxes();
  }
  if (!items.length && label === "empty") {
    items = [{ label: "empty", box: null }];
  }
  if (!items.length) {
    annotationMessage.textContent = "Draw a box, or choose Empty.";
    return false;
  }
  const response = await fetch("/api/annotations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      image: selectedFrame,
      annotations: items,
      source: annotationSource,
      model_version: annotationSource === "model_confirmed" ? currentSuggestion.model_version : null,
      prediction_id: annotationSource === "model_confirmed" ? currentSuggestion.id : null,
    }),
  });
  annotationMessage.textContent = response.ok ? "Saved." : (await response.json()).error;
  if (!response.ok) return false;
  savedEmpty = items.length === 1 && items[0].label === "empty" && items[0].box === null;
  if (savedEmpty) {
    const emptyFrames = await fetch("/api/events/" + selected.id + "/mark-empty", {
      method: "POST",
    });
    if (emptyFrames.ok) {
      annotationMessage.textContent = "Saved and marked unannotated frames as empty.";
    }
  }
  await reloadSelectedEvent();
  return true;
}

acceptSuggestion.onclick = async () => {
  if (!currentSuggestion || items.length) return;
  items = [{ label: currentSuggestion.label, box: currentSuggestion.box }];
  annotationSource = "model_confirmed";
  document.querySelector("#annotation-label").value = currentSuggestion.label;
  box = null;
  overlay.style.display = "none";
  renderRows();
  renderSavedBoxes();
  acceptSuggestion.disabled = true;
  annotationMessage.textContent = "Saving accepted model suggestion…";
  if (await saveAnnotations()) {
    annotationMessage.textContent = "Model suggestion accepted and saved.";
  } else {
    acceptSuggestion.disabled = false;
  }
};

document.querySelector("#annotation-form").onsubmit = async (event) => {
  event.preventDefault();
  await saveAnnotations();
};

document.querySelector("#delete-event").onclick = async () => {
  if (!selected || !confirm("Delete event?")) return;
  const response = await fetch("/api/events/" + selected.id, { method: "DELETE" });
  if (response.ok) await load();
};

document.querySelector("#annotation-label").onchange = () => { annotationSource = "manual"; };
document.querySelector("#refresh-events").onclick = load;

eventFilter.onchange = () => {
  clearSelection();
  render();
};
image.addEventListener("load", renderSavedBoxes);
load();
