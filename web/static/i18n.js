(() => {
  const translations = window.hornetTranslations || {};
  window.t = (value) => translations[value] || value;
  const translateText = (text) => {
    const value = text.nodeValue;
    const key = value.trim();
    if (translations[key]) text.nodeValue = value.replace(key, translations[key]);
  };
  const translate = (root) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = []; let node;
    while ((node = walker.nextNode())) nodes.push(node);
    nodes.forEach((text) => { if (!['SCRIPT', 'STYLE'].includes(text.parentElement.tagName)) translateText(text); });
  };
  translate(document.body);
  new MutationObserver((changes) => changes.forEach((change) => change.addedNodes.forEach((node) => { if (node.nodeType === Node.TEXT_NODE) translateText(node); else if (node.nodeType === Node.ELEMENT_NODE) translate(node); }))).observe(document.body, { childList: true, subtree: true });
  const picker = document.createElement('select');
  picker.className = 'form-select form-select-sm language-picker';
  picker.innerHTML = '<option value="de">Deutsch</option><option value="en">English</option>';
  picker.value = document.documentElement.lang || 'de';
  picker.onchange = async () => { await fetch(`/language/${picker.value}`, { method: 'POST' }); location.reload(); };
  document.body.append(picker);
})();
