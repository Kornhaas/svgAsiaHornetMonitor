(() => {
  const translations = window.hornetTranslations || {};
  window.t = (value) => translations[value.trim()] || value;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const nodes = []; let node;
  while ((node = walker.nextNode())) nodes.push(node);
  nodes.forEach((text) => { if (text.parentElement.tagName !== 'SCRIPT') text.nodeValue = text.nodeValue.replace(/\S[\s\S]*?\S/g, (value) => window.t(value)); });
  const picker = document.createElement('select');
  picker.className = 'form-select form-select-sm language-picker';
  picker.innerHTML = '<option value="de">Deutsch</option><option value="en">English</option>';
  picker.value = document.documentElement.lang || 'de';
  picker.onchange = async () => { await fetch(`/language/${picker.value}`, { method: 'POST' }); location.reload(); };
  document.body.append(picker);
})();
