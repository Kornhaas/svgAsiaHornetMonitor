const indicator = document.querySelector('#indicator');
const message = document.querySelector('#message');
const details = document.querySelector('#details');
const roiBox = document.querySelector('#roi');
const stream = document.querySelector('#stream');
const activityList = document.querySelector('#activity-list');
const updateMessage = document.querySelector('#update-message');
let frameSize = { width: 1280, height: 720 };
let reconnectTimer;

function showRoi(roi) { roiBox.style.left = `${(roi.x / frameSize.width) * 100}%`; roiBox.style.top = `${(roi.y / frameSize.height) * 100}%`; roiBox.style.width = `${(roi.width / frameSize.width) * 100}%`; roiBox.style.height = `${(roi.height / frameSize.height) * 100}%`; }
function reconnectStream() { clearTimeout(reconnectTimer); reconnectTimer = setTimeout(() => { stream.src = `/stream.mjpg?reconnect=${Date.now()}`; }, 1500); }
async function refreshStatus() { try { const state = await (await fetch('/status', { cache: 'no-store' })).json(); frameSize = { width: state.frame_width, height: state.frame_height }; indicator.classList.toggle('motion', state.motion); message.textContent = state.camera_error || (state.motion ? 'Motion detected in ROI' : 'Watching ROI'); details.textContent = `Largest moving area: ${state.largest_area}px²${state.last_event ? ` · Latest event: ${state.last_event}` : ''}`; showRoi(state.roi); } catch (_) { message.textContent = 'Status unavailable'; } }
async function refreshActivities() { try { const activities = await (await fetch('/activities')).json(); activityList.replaceChildren(...activities.map((activity) => { const item = document.createElement('li'); const time = document.createElement('span'); time.className = 'activity-time'; time.textContent = `${new Date(activity.timestamp).toLocaleString()} — `; item.append(time, activity.message); return item; })); if (!activities.length) activityList.textContent = 'No activity recorded yet.'; } catch (_) { activityList.textContent = 'Activity log unavailable.'; } }
async function updateRequest(path) { const response = await fetch(path, { method: 'POST' }); const result = await response.json(); updateMessage.textContent = result.message || (result.state === 'current' ? `Up to date (${result.current}).` : `${result.pending} update(s) available.`); if (path === '/updates/install' && result.state === 'running') { updateMessage.textContent = 'Update installed; reconnecting the monitor…'; stream.removeAttribute('src'); setTimeout(() => window.location.reload(), 8000); } }
stream.addEventListener('error', reconnectStream);
document.querySelector('#check-update').addEventListener('click', () => updateRequest('/updates/check'));
document.querySelector('#install-update').addEventListener('click', () => updateRequest('/updates/install'));
refreshStatus(); refreshActivities(); setInterval(refreshStatus, 1000); setInterval(refreshActivities, 5000);
