const message = document.getElementById("message");
const stream = document.getElementById("stream");
const canvas = document.getElementById("roi-canvas");
const outerBox = document.getElementById("outer-box");
const triggerBox = document.getElementById("trigger-box");
const outerForm = document.getElementById("outer");
const triggerForm = document.getElementById("trigger");
const outerButton = document.getElementById("draw-outer");
const triggerButton = document.getElementById("draw-trigger");

let frame = { width: 1, height: 1 };
let mode = "outer";
let drawing = null;

function values(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function fill(form, roi) {
  for (const [key, value] of Object.entries(roi)) {
    form.elements[key].value = value;
  }
}

function show(box, roi) {
  box.style.left = `${(roi.x / frame.width) * 100}%`;
  box.style.top = `${(roi.y / frame.height) * 100}%`;
  box.style.width = `${(roi.width / frame.width) * 100}%`;
  box.style.height = `${(roi.height / frame.height) * 100}%`;
}

function select(nextMode) {
  mode = nextMode;
  outerButton.classList.toggle("active", mode === "outer");
  outerButton.classList.toggle("btn-warning", mode === "outer");
  outerButton.classList.toggle("btn-outline-warning", mode !== "outer");
  triggerButton.classList.toggle("active", mode === "trigger");
  triggerButton.classList.toggle("btn-info", mode === "trigger");
  triggerButton.classList.toggle("btn-outline-info", mode !== "trigger");
}

async function save(form, payload) {
  const response = await fetch("/roi", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  message.textContent = response.ok ? "Saved locally." : (result.error || "Could not save settings.");
  if (response.ok) {
    show(form === outerForm ? outerBox : triggerBox, result.roi);
  }
  return response.ok;
}

function roiFromPointer(event) {
  const bounds = stream.getBoundingClientRect();
  const x = Math.max(0, Math.min(bounds.width, event.clientX - bounds.left));
  const y = Math.max(0, Math.min(bounds.height, event.clientY - bounds.top));
  const left = Math.min(drawing.x, x);
  const top = Math.min(drawing.y, y);
  return {
    x: Math.round((left / bounds.width) * frame.width),
    y: Math.round((top / bounds.height) * frame.height),
    width: Math.max(1, Math.round((Math.abs(x - drawing.x) / bounds.width) * frame.width)),
    height: Math.max(1, Math.round((Math.abs(y - drawing.y) / bounds.height) * frame.height)),
  };
}

canvas.addEventListener("pointerdown", (event) => {
  if (!frame.width || !stream.getBoundingClientRect().width) return;
  const bounds = stream.getBoundingClientRect();
  drawing = { x: event.clientX - bounds.left, y: event.clientY - bounds.top };
  canvas.setPointerCapture(event.pointerId);
  event.preventDefault();
});

canvas.addEventListener("pointermove", (event) => {
  if (!drawing) return;
  const form = mode === "outer" ? outerForm : triggerForm;
  const box = mode === "outer" ? outerBox : triggerBox;
  const roi = roiFromPointer(event);
  fill(form, roi);
  show(box, roi);
});

canvas.addEventListener("pointerup", async (event) => {
  if (!drawing) return;
  const form = mode === "outer" ? outerForm : triggerForm;
  const box = mode === "outer" ? outerBox : triggerBox;
  const roi = roiFromPointer(event);
  const bounds = stream.getBoundingClientRect();
  const distance = Math.hypot(
    event.clientX - bounds.left - drawing.x,
    event.clientY - bounds.top - drawing.y,
  );
  drawing = null;
  canvas.releasePointerCapture(event.pointerId);
  if (distance < 8) {
    show(box, values(form));
    message.textContent = "Drag to draw a rectangle.";
    return;
  }
  await save(form, mode === "outer" ? roi : { trigger: roi });
});

outerButton.addEventListener("click", () => select("outer"));
triggerButton.addEventListener("click", () => select("trigger"));
outerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await save(outerForm, values(outerForm));
});
triggerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await save(triggerForm, { trigger: values(triggerForm) });
});

async function init() {
  const response = await fetch("/status");
  const status = await response.json();
  frame = status.frame || { width: status.frame_width, height: status.frame_height };
  if (!Number.isFinite(frame.width) || !Number.isFinite(frame.height) || frame.width < 1 || frame.height < 1) {
    message.textContent = "Camera dimensions are unavailable.";
    return;
  }
  fill(outerForm, status.roi);
  fill(triggerForm, status.trigger_roi || status.roi);
  show(outerBox, status.roi);
  show(triggerBox, status.trigger_roi || status.roi);
}

init();
