const list = document.querySelector("#event-list");
const image = document.querySelector("#annotation-image");
const canvas = document.querySelector("#annotation-canvas");
const overlay = document.querySelector("#annotation-box");
const message = document.querySelector("#gallery-message");
const annotationMessage = document.querySelector("#annotation-message");
const rows = document.querySelector("#annotation-list");
const showReviewed = document.querySelector("#show-reviewed");
const eventFrames = document.querySelector("#event-frames");

let events = [];
let selected = null;
let selectedFrame = null;
let box = null;
let items = [];

function visibleEvents() {
  return showReviewed.checked ? events : events.filter((event) => !event.reviewed);
}

function clearSelection() {
  selected = null;
  selectedFrame = null;
  items = [];
  box = null;
  image.removeAttribute("src");
  overlay.style.display = "none";
  rows.replaceChildren();
  eventFrames.replaceChildren();
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
      };
      row.append(remove);
      return row;
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
  image.src = "/event-image/" + frame;
  items = await (await fetch("/api/annotations/" + frame)).json();
  renderRows();
  renderFrames();
}

async function select(event) {
  selected = event;
  selectedFrame = null;
  await selectFrame(event.image, true);
  render();
}

function eventCard(event) {
  const card = document.createElement("button");
  card.type = "button";
  card.className = "event-card" + (selected === event ? " selected" : "");
  const preview = document.createElement("img");
  preview.src = "/event-image/" + event.image;
  preview.alt = "Event " + event.id;
  preview.loading = "lazy";
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
  message.textContent = showReviewed.checked
    ? String(events.length) + " recent events"
    : String(visible.length) + " unreviewed event" + (visible.length === 1 ? "" : "s");
  if (!visible.length) {
    const empty = document.createElement("p");
    empty.className = "text-body-secondary";
    empty.textContent = showReviewed.checked
      ? "No events available."
      : "All visible events have been reviewed.";
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

canvas.onpointerdown = (event) => {
  if (!selectedFrame || !image.naturalWidth) return;
  const bounds = image.getBoundingClientRect();
  const start = { x: event.clientX - bounds.left, y: event.clientY - bounds.top };
  canvas.setPointerCapture(event.pointerId);
  canvas.onpointermove = (move) => {
    const x = Math.max(0, Math.min(bounds.width, move.clientX - bounds.left));
    const y = Math.max(0, Math.min(bounds.height, move.clientY - bounds.top));
    box = {
      x: Math.round((Math.min(start.x, x) / bounds.width) * image.naturalWidth),
      y: Math.round((Math.min(start.y, y) / bounds.height) * image.naturalHeight),
      width: Math.max(1, Math.round((Math.abs(x - start.x) / bounds.width) * image.naturalWidth)),
      height: Math.max(1, Math.round((Math.abs(y - start.y) / bounds.height) * image.naturalHeight)),
    };
    showBox();
  };
  canvas.onpointerup = () => {
    canvas.onpointermove = null;
  };
};

document.querySelector("#add-box").onclick = () => {
  const label = document.querySelector("#annotation-label").value;
  if (!box && label !== "empty") {
    annotationMessage.textContent = "Draw a box first.";
    return;
  }
  items.push({ label, box: label === "empty" ? null : box });
  box = null;
  overlay.style.display = "none";
  annotationMessage.textContent = "";
  renderRows();
};

document.querySelector("#suggest-boxes").onclick = async () => {
  if (!selectedFrame) return;
  const boxes = await (await fetch("/api/events/" + selectedFrame + "/proposals")).json();
  items.push(...boxes.map((suggestion) => ({ label: "uncertain", box: suggestion })));
  renderRows();
  annotationMessage.textContent = boxes.length
    ? "Suggestions added as uncertain."
    : "No suggestions; update the background first.";
};

document.querySelector("#annotation-form").onsubmit = async (event) => {
  event.preventDefault();
  if (!selectedFrame) return;
  const label = document.querySelector("#annotation-label").value;
  if (box && label !== "empty") {
    items.push({ label, box });
    box = null;
    overlay.style.display = "none";
    renderRows();
  }
  if (!items.length && label === "empty") {
    items = [{ label: "empty", box: null }];
  }
  if (!items.length) {
    annotationMessage.textContent = "Draw a box, or choose Empty.";
    return;
  }
  const response = await fetch("/api/annotations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image: selectedFrame, annotations: items }),
  });
  annotationMessage.textContent = response.ok ? "Saved." : (await response.json()).error;
  if (response.ok) {
    await reloadSelectedEvent();
  }
};

document.querySelector("#delete-event").onclick = async () => {
  if (!selected || !confirm("Delete event?")) return;
  const response = await fetch("/api/events/" + selected.id, { method: "DELETE" });
  if (response.ok) await load();
};

showReviewed.onchange = render;
load();
