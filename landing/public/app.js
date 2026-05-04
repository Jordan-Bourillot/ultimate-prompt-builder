// Boutons "Acheter" -> POST /api/create-checkout -> redirige vers Stripe Checkout.
'use strict';

(function () {
  const BTN_IDS = ['buy-btn', 'buy-btn-final'];

  async function startCheckout(btn) {
    const original = btn.textContent;
    btn.disabled = true;
    btn.textContent = '⏳ Chargement...';

    try {
      const res = await fetch('/api/create-checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await res.json();
      if (!res.ok || !data.url) {
        throw new Error(data.error || data.message || 'Réponse invalide');
      }
      window.location.href = data.url;
    } catch (err) {
      console.error(err);
      btn.disabled = false;
      btn.textContent = original;
      alert(
        'Impossible de lancer le paiement : ' + err.message +
        '\n\nRéessaie ou contacte contact@triskell-studio.fr'
      );
    }
  }

  for (const id of BTN_IDS) {
    const btn = document.getElementById(id);
    if (btn) btn.addEventListener('click', () => startCheckout(btn));
  }
})();
