# Stripe setup — AlphaBeast (19€)

3 actions chez Stripe + 3 env vars chez Netlify. ~10 min.

## 1. Créer le produit + prix Stripe (5 min)

1. Va sur https://dashboard.stripe.com/products
2. **Add product**
   - Name : `AlphaBeast`
   - Description : `Combine ton prompt avec 16 Mega Prompts brandés et envoie à Claude, GPT, Gemini, Mistral ou Grok. Windows desktop, paiement unique à vie.`
   - Image : upload `landing/public/img/icon.png`
3. **Pricing**
   - Type : `One-off`
   - Price : `19,00 €` EUR
   - Tax : `Auto` ou désactivé selon ta config TVA
4. Crée le produit → note le **Price ID** (`price_xxxxx`)

## 2. Récupérer les clés API (1 min)

https://dashboard.stripe.com/apikeys
- **Secret key** : `sk_live_xxxxx` (commence par `sk_live_` en prod, `sk_test_` en test)

## 3. Configurer les env vars sur Netlify (2 min)

Dashboard Netlify → site `ultimate-prompt-builder` → **Site configuration** → **Environment variables** → **Add a variable** :

```
STRIPE_SECRET_KEY = sk_live_xxxxx
STRIPE_PRICE_ID   = price_xxxxx
PUBLIC_URL        = https://prompt-builder.triskell-studio.fr
```

Puis clic **Deploys** → **Trigger deploy** → **Clear cache and deploy site** (pour que les vars soient prises en compte).

## 4. Test E2E

Sur https://prompt-builder.triskell-studio.fr → clic **Acheter AlphaBeast — 19€** → paiement test avec carte Stripe `4242 4242 4242 4242` (CVC: n'importe quoi, exp: future) → redirection vers `/success.html`.

## Optionnel — Webhook pour livraison auto

Pour automatiser l'envoi du lien de téléchargement par email après paiement, créer un webhook Stripe + une fonction `webhook.js` (mirror Studio PDF). À faire plus tard, le minimum (envoi manuel après confirmation Stripe Dashboard) suffit pour démarrer.
