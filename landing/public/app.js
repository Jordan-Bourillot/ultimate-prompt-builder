// Tracking minimal du clic download (no-op si pas d'analytics)
'use strict';
(function () {
  const btn = document.getElementById('download-btn');
  if (!btn) return;
  btn.addEventListener('click', () => {
    try { window.dataLayer = window.dataLayer || []; window.dataLayer.push({ event: 'download_click', app: 'ultimate-prompt-builder' }); }
    catch (_) {}
  });
})();
