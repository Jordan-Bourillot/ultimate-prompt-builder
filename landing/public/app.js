// Boutons "Acheter" -> POST /api/create-checkout -> redirige vers Stripe Checkout.
// Auto-déclenchement si l'URL contient ?buy=1 (skip de la page intermédiaire
// quand on arrive depuis la grande landing triskell-studio.fr/alphabeast).
'use strict';

(function () {
  const BTN_IDS = ['buy-btn', 'buy-btn-final'];
  const buttons = BTN_IDS.map(id => document.getElementById(id)).filter(Boolean);
  if (!buttons.length) return;

  async function startCheckout(btn) {
    const original = btn.textContent;
    buttons.forEach(b => { b.disabled = true; });
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
      buttons.forEach(b => { b.disabled = false; });
      btn.textContent = original;
      document.body.classList.remove('auto-buy');
      alert(
        'Impossible de lancer le paiement : ' + err.message +
        '\n\nRéessaie ou contacte contact@triskell-studio.fr'
      );
    }
  }

  buttons.forEach(btn => {
    btn.addEventListener('click', () => startCheckout(btn));
  });

  const params = new URLSearchParams(window.location.search);
  if (params.get('buy') === '1') {
    document.body.classList.add('auto-buy');
    startCheckout(buttons[0]);
  }
})();
