const message = document.querySelector('#message');
function values(form) { return Object.fromEntries(new FormData(form).entries().map(([key, value]) => [key, Number(value)])); }
function fill(form, roi) { Object.entries(roi).forEach(([key, value]) => { form.elements[key].value = value; }); }
async function save(form, payload) { const response = await fetch('/roi', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); const result = await response.json(); message.textContent = response.ok ? 'Saved locally.' : result.error; }
async function init() { const status = await (await fetch('/status')).json(); fill(outer, status.roi); fill(trigger, status.trigger_roi); }
outer.onsubmit = (event) => { event.preventDefault(); save(outer, values(outer)); };
trigger.onsubmit = (event) => { event.preventDefault(); save(trigger, { trigger: values(trigger) }); };
init();
