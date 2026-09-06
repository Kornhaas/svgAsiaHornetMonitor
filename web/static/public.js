const stream = document.querySelector("#public-stream");
const detections = document.querySelector("#public-detections");
const message = document.querySelector("#public-message");
const predictionMessage = document.querySelector("#public-prediction");
let reconnectTimer;

function reconnectStream() {
  clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(() => {
    stream.src = `/public/stream.mjpg?reconnect=${Date.now()}`;
  }, 1500);
}

function drawDetections(state) {
  detections.replaceChildren();
  const prediction = state.prediction;
  if (!prediction || !state.frame_width || !state.frame_height) {
    predictionMessage.textContent = "No completed model detection yet.";
    return;
  }
  const offset = state.event_crop && state.roi ? state.roi : { x: 0, y: 0 };
  for (const detection of prediction.detections) {
    const box = detection.box;
    const marker = document.createElement("div");
    marker.className = "public-detection";
    marker.style.left = `${((box.x + offset.x) / state.frame_width) * 100}%`;
    marker.style.top = `${((box.y + offset.y) / state.frame_height) * 100}%`;
    marker.style.width = `${(box.width / state.frame_width) * 100}%`;
    marker.style.height = `${(box.height / state.frame_height) * 100}%`;
    const label = document.createElement("span");
    label.textContent = `${detection.label} ${Math.round(detection.confidence * 100)}%`;
    marker.append(label);
    detections.append(marker);
  }
  const time = prediction.timestamp ? new Date(prediction.timestamp).toLocaleString() : "unknown time";
  predictionMessage.textContent = `Last model detection: ${time}.`;
}

async function refresh() {
  try {
    const state = await (await fetch("/public/status", { cache: "no-store" })).json();
    message.textContent = state.camera_error || "Live camera";
    drawDetections(state);
  } catch (_) {
    message.textContent = "Camera status unavailable.";
  }
}

stream.addEventListener("error", reconnectStream);
refresh();
setInterval(refresh, 2000);
