const eventList = document.querySelector('#event-list');
const image = document.querySelector('#annotation-image');
const canvas = document.querySelector('#annotation-canvas');
const boxElement = document.querySelector('#annotation-box');
const message = document.querySelector('#gallery-message');
const annotationMessage = document.querySelector('#annotation-message');
const showReviewed = document.querySelector('#show-reviewed');
let events = [];
let selected = null;
let box = null;

function displayBox() {
  if (!box || !image.naturalWidth) return;
  boxElement.style.display = 'block';
  boxElement.style.left = `${(box.x / image.naturalWidth) * 100}%`;
  boxElement.style.top = `${(box.y / image.naturalHeight) * 100}%`;
  boxElement.style.width = `${(box.width / image.naturalWidth) * 100}%`;
  boxElement.style.height = `${(box.height / image.naturalHeight) * 100}%`;
}

function selectEvent(event) {
  selected = event;
  box = null;
  boxElement.style.display = 'none';
  image.src = `/event-image/${event.image}`;
  annotationMessage.textContent = '';
  renderEvents();
}

function visibleEvents() { return events.filter((event) => showReviewed.checked || !event.reviewed); }

function renderEvents() {
  const visible = visibleEvents();
  message.textContent = `${visible.length} ${showReviewed.checked ? 'events' : 'unreviewed events'}`;
  eventList.replaceChildren(...visible.map((event) => {
    const button = document.createElement('button');
    button.className = `event-card ${selected === event ? 'selected' : ''}`;
    const thumbnail = document.createElement('img');
    thumbnail.src = `/event-image/${event.image}`;
    thumbnail.alt = event.id;
    const caption = document.createElement('span');
    caption.textContent = event.id.replace('/', ' · ');
    button.append(thumbnail, caption);
    if (event.reviewed) {
      const badge = document.createElement('span');
      badge.className = 'badge text-bg-success';
      badge.textContent = 'Reviewed';
      button.append(badge);
    }
    button.addEventListener('click', () => selectEvent(event));
    return button;
  }));
  if (!selected && visible[0]) selectEvent(visible[0]);
}

async function loadEvents() {
  events = await (await fetch('/api/events')).json();
  renderEvents();
}

canvas.addEventListener('pointerdown', (event) => {
  if (!selected || !image.naturalWidth) return;
  const bounds = image.getBoundingClientRect();
  const start = { x: event.clientX - bounds.left, y: event.clientY - bounds.top };
  const draw = (moveEvent) => {
    const endX = Math.max(0, Math.min(bounds.width, moveEvent.clientX - bounds.left));
    const endY = Math.max(0, Math.min(bounds.height, moveEvent.clientY - bounds.top));
    box = { x: Math.round((Math.min(start.x, endX) / bounds.width) * image.naturalWidth), y: Math.round((Math.min(start.y, endY) / bounds.height) * image.naturalHeight), width: Math.max(1, Math.round((Math.abs(endX - start.x) / bounds.width) * image.naturalWidth)), height: Math.max(1, Math.round((Math.abs(endY - start.y) / bounds.height) * image.naturalHeight)) };
    displayBox();
  };
  canvas.setPointerCapture(event.pointerId);
  canvas.addEventListener('pointermove', draw);
  canvas.addEventListener('pointerup', () => canvas.removeEventListener('pointermove', draw), { once: true });
});

document.querySelector('#annotation-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const label = document.querySelector('#annotation-label').value;
  if (!selected || (!box && label !== 'empty')) { annotationMessage.textContent = 'Select an image and draw a box first.'; return; }
  const response = await fetch('/api/annotations', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image: selected.image, label, box: label === 'empty' ? null : box }) });
  const payload = await response.json();
  annotationMessage.textContent = response.ok ? 'Saved — opening next event…' : payload.error;
  if (response.ok) {
    selected.reviewed = true;
    const next = events.find((candidate) => !candidate.reviewed);
    selected = null;
    renderEvents();
    if (next) selectEvent(next);
  }
});

document.querySelector('#delete-event').addEventListener('click', async () => {
  if (!selected || !confirm(`Delete event ${selected.id} and all of its burst images?`)) return;
  const response = await fetch(`/api/events/${selected.id}`, { method: 'DELETE' });
  if (!response.ok) { annotationMessage.textContent = 'Could not delete this event.'; return; }
  events = events.filter((event) => event !== selected);
  selected = null;
  box = null;
  image.removeAttribute('src');
  boxElement.style.display = 'none';
  renderEvents();
});

showReviewed.addEventListener('change', renderEvents);
loadEvents().catch(() => { message.textContent = 'Gallery unavailable.'; });
