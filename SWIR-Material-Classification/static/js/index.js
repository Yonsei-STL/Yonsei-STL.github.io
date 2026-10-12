/* Progressive enhancement: the full article and BibTeX remain readable without JS. */
(() => {
  'use strict';
  const button = document.querySelector('[data-copy-bibtex]');
  const source = document.getElementById('bibtex-code');
  const status = document.getElementById('copy-status');
  if (!button || !source || !status) return;
  button.hidden = false;
  button.addEventListener('click', async () => {
    const text = source.textContent;
    let copied = false;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        copied = true;
      }
    } catch (_) { /* Use a local-file-compatible fallback below. */ }
    if (!copied) {
      const field = document.createElement('textarea');
      field.value = text;
      field.setAttribute('readonly', '');
      field.style.cssText = 'position:fixed;left:-10000px;top:0;';
      document.body.appendChild(field);
      field.select();
      try { copied = document.execCommand('copy'); } catch (_) { copied = false; }
      field.remove();
      button.focus();
    }
    status.textContent = copied ? 'BibTeX copied.' : 'Copy was unavailable. Select the citation below or use Download .bib.';
  });
})();
