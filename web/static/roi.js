const stream = document.querySelector('#stream');
const streamContainer = document.querySelector('.stream-container');
const roiBox = document.querySelector('#roi');
const roiForm = document.querySelector('#roi-form');
const roiMessage = document.querySelector('#roi-message');
const inputs = Object.fromEntries(['x', 'y', 'width', 'height'].map((key) => [key, document.querySelector(`#roi-${key}`)]));
let frameSize = { width: 1280, height: 720 };

function currentRoi() { return Object.fromEntries(Object.entries(inputs).map(([key, input]) => [key, Number(input.value)])); }
function showRoi(roi) { Object.entries(roi).forEach(([key, value]) => { inputs[key].value = value; }); roiBox.style.left = `${(roi.x / frameSize.width) * 100}%`; roiBox.style.top = `${(roi.y / frameSize.height) * 100}%`; roiBox.style.width = `${(roi.width / frameSize.width) * 100}%`; roiBox.style.height = `${(roi.height / frameSize.height) * 100}%`; }
async function refreshStatus() { const response = await fetch('/status'); if (!response.ok) return; const state = await response.json(); frameSize = { width: state.frame_width, height: state.frame_height }; showRoi(state.roi); }
async function saveRoi() { const response = await fetch('/roi', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(currentRoi()) }); const payload = await response.json(); roiMessage.textContent = response.ok ? 'Saved locally.' : payload.error; if (response.ok) showRoi(payload.roi); }
roiForm.addEventListener('submit', async (event) => { event.preventDefault(); await saveRoi(); });
streamContainer.addEventListener('pointerdown', (event) => { const bounds = stream.getBoundingClientRect(); const start = { x: event.clientX - bounds.left, y: event.clientY - bounds.top }; const draw = (moveEvent) => { const endX = Math.max(0, Math.min(bounds.width, moveEvent.clientX - bounds.left)); const endY = Math.max(0, Math.min(bounds.height, moveEvent.clientY - bounds.top)); showRoi({ x: Math.round((Math.min(start.x, endX) / bounds.width) * frameSize.width), y: Math.round((Math.min(start.y, endY) / bounds.height) * frameSize.height), width: Math.max(1, Math.round((Math.abs(endX - start.x) / bounds.width) * frameSize.width)), height: Math.max(1, Math.round((Math.abs(endY - start.y) / bounds.height) * frameSize.height)) }); }; streamContainer.setPointerCapture(event.pointerId); streamContainer.addEventListener('pointermove', draw); streamContainer.addEventListener('pointerup', async () => { streamContainer.removeEventListener('pointermove', draw); await saveRoi(); }, { once: true }); });
refreshStatus();
