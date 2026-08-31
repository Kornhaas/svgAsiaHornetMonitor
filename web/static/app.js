const indicator = document.querySelector('#indicator');
const message = document.querySelector('#message');
const details = document.querySelector('#details');
const stream = document.querySelector('#stream');
const streamContainer = document.querySelector('.stream-container');
const roiBox = document.querySelector('#roi');
const roiForm = document.querySelector('#roi-form');
const roiMessage = document.querySelector('#roi-message');
const activityList = document.querySelector('#activity-list');
const updateMessage = document.querySelector('#update-message');
const inputs = Object.fromEntries(['x', 'y', 'width', 'height'].map((key) => [key, document.querySelector(`#roi-${key}`)]));
let frameSize = { width: 1280, height: 720 };
let editingRoi = false;

function currentRoi() { return Object.fromEntries(Object.entries(inputs).map(([key, input]) => [key, Number(input.value)])); }
function showRoi(roi) {
  Object.entries(roi).forEach(([key, value]) => { inputs[key].value = value; });
  roiBox.style.left = `${(roi.x / frameSize.width) * 100}%`;
  roiBox.style.top = `${(roi.y / frameSize.height) * 100}%`;
  roiBox.style.width = `${(roi.width / frameSize.width) * 100}%`;
  roiBox.style.height = `${(roi.height / frameSize.height) * 100}%`;
}

async function refreshStatus() {
  try {
    const state = await (await fetch('/status')).json();
    frameSize = { width: state.frame_width, height: state.frame_height };
    indicator.classList.toggle('motion', state.motion);
    message.textContent = state.camera_error || (state.motion ? 'Motion detected in ROI' : 'Watching ROI');
    details.textContent = `Largest moving area: ${state.largest_area}px²${state.last_event ? ` · Latest event: ${state.last_event}` : ''}`;
    if (!editingRoi && !roiForm.contains(document.activeElement)) showRoi(state.roi);
  } catch (_) { message.textContent = 'Status unavailable'; }
}

async function refreshActivities() {
  try {
    const activities = await (await fetch('/activities')).json();
    activityList.replaceChildren(...activities.map((activity) => {
      const item = document.createElement('li');
      const time = document.createElement('span');
      time.className = 'activity-time';
      time.textContent = `${new Date(activity.timestamp).toLocaleString()} — `;
      item.append(time, activity.message);
      return item;
    }));
    if (!activities.length) activityList.textContent = 'No activity recorded yet.';
  } catch (_) { activityList.textContent = 'Activity log unavailable.'; }
}

async function updateRequest(path) {
  const response = await fetch(path, { method: 'POST' });
  const result = await response.json();
  updateMessage.textContent = result.message || (result.state === 'current' ? `Up to date (${result.current}).` : `${result.pending} update(s) available.`);
}

document.querySelector('#check-update').addEventListener('click', () => updateRequest('/updates/check'));
document.querySelector('#install-update').addEventListener('click', () => updateRequest('/updates/install'));

async function saveRoi() {
  const response = await fetch('/roi', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(currentRoi()) });
  const payload = await response.json();
  roiMessage.textContent = response.ok ? 'Saved locally.' : payload.error;
  if (response.ok) showRoi(payload.roi);
}

roiForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  await saveRoi();
});

streamContainer.addEventListener('pointerdown', (event) => {
  editingRoi = true;
  const bounds = stream.getBoundingClientRect();
  const start = { x: event.clientX - bounds.left, y: event.clientY - bounds.top };
  const draw = (moveEvent) => {
    const endX = Math.max(0, Math.min(bounds.width, moveEvent.clientX - bounds.left));
    const endY = Math.max(0, Math.min(bounds.height, moveEvent.clientY - bounds.top));
    showRoi({ x: Math.round((Math.min(start.x, endX) / bounds.width) * frameSize.width), y: Math.round((Math.min(start.y, endY) / bounds.height) * frameSize.height), width: Math.max(1, Math.round((Math.abs(endX - start.x) / bounds.width) * frameSize.width)), height: Math.max(1, Math.round((Math.abs(endY - start.y) / bounds.height) * frameSize.height)) });
  };
  streamContainer.setPointerCapture(event.pointerId);
  streamContainer.addEventListener('pointermove', draw);
  streamContainer.addEventListener('pointerup', async () => {
    streamContainer.removeEventListener('pointermove', draw);
    editingRoi = false;
    await saveRoi();
  }, { once: true });
});

refreshStatus(); refreshActivities(); setInterval(refreshStatus, 1000); setInterval(refreshActivities, 5000);
