const indicator = document.querySelector('#indicator');
const message = document.querySelector('#message');
const details = document.querySelector('#details');
const roiBox = document.querySelector('#roi');
const stream = document.querySelector('#stream');
const nightPreview = document.querySelector('#night-preview');
const activityList = document.querySelector('#activity-list');
const updateMessage = document.querySelector('#update-message');
const manualTrigger = document.querySelector('#manual-trigger');
const manualTriggerResult = document.querySelector('#manual-trigger-result');
let frameSize = { width: 1280, height: 720 };
let reconnectTimer;
let previewDisabled = false;

function showRoi(roi) {
  roiBox.style.left = `${(roi.x / frameSize.width) * 100}%`;
  roiBox.style.top = `${(roi.y / frameSize.height) * 100}%`;
  roiBox.style.width = `${(roi.width / frameSize.width) * 100}%`;
  roiBox.style.height = `${(roi.height / frameSize.height) * 100}%`;
}

function reconnectStream() {
  if (previewDisabled) return;
  clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(() => {
    stream.src = `/stream.mjpg?reconnect=${Date.now()}`;
  }, 1500);
}

function setPreviewDisabled(disabled) {
  if (disabled === previewDisabled) return;
  previewDisabled = disabled;
  stream.classList.toggle('d-none', disabled);
  roiBox.classList.toggle('d-none', disabled);
  nightPreview.classList.toggle('d-none', !disabled);
  if (disabled) stream.removeAttribute('src');
  else stream.src = `/stream.mjpg?reconnect=${Date.now()}`;
}

async function refreshStatus() {
  try {
    const state = await (await fetch('/status', { cache: 'no-store' })).json();
    frameSize = { width: state.frame_width, height: state.frame_height };
    const night = state.night_mode || {};
    setPreviewDisabled(Boolean(night.preview_disabled));
    indicator.classList.toggle('motion', state.motion);
    message.textContent = state.camera_error || (
      night.preview_disabled ? (night.active ? 'Night mode active' : 'Night mode pending') :
        (state.motion ? 'Motion detected in ROI' : 'Watching ROI')
    );
    details.textContent = `Largest moving area: ${state.largest_area}px²${
      state.last_event ? ` · Latest event: ${state.last_event}` : ''}`;
    showRoi(state.roi);
  } catch (_) {
    message.textContent = 'Status unavailable';
  }
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
  } catch (_) {
    activityList.textContent = 'Activity log unavailable.';
  }
}

async function updateRequest(path) {
  const response = await fetch(path, { method: 'POST' });
  const result = await response.json();
  if (!response.ok || result.error) {
    updateMessage.textContent = result.error || 'Update request failed.';
    return;
  }
  updateMessage.textContent = result.message || (
    result.state === 'current' ? `Up to date (${result.current}).` : `${result.pending} update(s) available.`
  );
  if (path === '/updates/install' && result.state === 'running') {
    updateMessage.textContent = 'Update installed; reconnecting the monitor…';
    stream.removeAttribute('src');
    setTimeout(() => window.location.reload(), 8000);
  }
}

async function requestManualTrigger() {
  manualTrigger.disabled = true;
  manualTriggerResult.textContent = 'Capturing event…';
  try {
    const response = await fetch('/api/events/trigger', { method: 'POST' });
    const result = await response.json();
    manualTriggerResult.textContent = response.ok
      ? result.message
      : (result.error || 'Manual event capture failed.');
    if (response.ok) {
      refreshStatus();
      refreshActivities();
    }
  } catch (_) {
    manualTriggerResult.textContent = 'Manual event capture failed.';
  } finally {
    setTimeout(() => { manualTrigger.disabled = false; }, 1000);
  }
}

stream.addEventListener('error', reconnectStream);
document.querySelector('#check-update').addEventListener('click', () => updateRequest('/updates/check'));
document.querySelector('#install-update').addEventListener('click', () => updateRequest('/updates/install'));
manualTrigger.addEventListener('click', requestManualTrigger);
refreshStatus();
refreshActivities();
setInterval(refreshStatus, 1000);
setInterval(refreshActivities, 5000);
