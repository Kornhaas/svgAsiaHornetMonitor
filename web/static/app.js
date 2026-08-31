const indicator = document.querySelector('#indicator');
const message = document.querySelector('#message');
const details = document.querySelector('#details');
async function refreshStatus() {
  try {
    const state = await (await fetch('/status')).json();
    indicator.classList.toggle('motion', state.motion);
    message.textContent = state.camera_error || (state.motion ? 'Motion detected in ROI' : 'Watching ROI');
    details.textContent = `Largest moving area: ${state.largest_area}px²${state.last_event ? ` · Latest event: ${state.last_event}` : ''}`;
  } catch (_) { message.textContent = 'Status unavailable'; }
}
refreshStatus(); setInterval(refreshStatus, 1000);
