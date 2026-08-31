const eventList = document.querySelector('#event-list');
const image = document.querySelector('#annotation-image');
const canvas = document.querySelector('#annotation-canvas');
const boxElement = document.querySelector('#annotation-box');
const message = document.querySelector('#gallery-message');
const annotationMessage = document.querySelector('#annotation-message');
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

async function loadEvents() {
  const events = await (await fetch('/api/events')).json();
  message.textContent = events.length ? `${events.length} recent events` : 'No saved events yet.';
  eventList.replaceChildren(...events.map((event) => {
    const button = document.createElement('button');
    button.className = 'event-card';
    const thumbnail = document.createElement('img');
    thumbnail.src = `/event-image/${event.image}`;
    thumbnail.alt = event.id;
    button.append(thumbnail, document.createTextNode(event.id.replace('/', ' · ')));
    button.addEventListener('click', () => {
      selected = event;
      box = null;
      boxElement.style.display = 'none';
      image.src = `/event-image/${event.image}`;
      annotationMessage.textContent = '';
    });
    return button;
  }));
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
  annotationMessage.textContent = response.ok ? 'Annotation saved.' : payload.error;
});

loadEvents().catch(() => { message.textContent = 'Gallery unavailable.'; });
