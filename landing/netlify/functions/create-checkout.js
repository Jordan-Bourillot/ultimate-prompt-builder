// POST /api/create-checkout — cree une session Stripe pour AlphaBeast.
'use strict';

const Stripe = require('stripe');

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY, {
  apiVersion: '2024-12-18.acacia',
});

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: JSON.stringify({ error: 'method-not-allowed' }) };
  }

  if (!process.env.STRIPE_SECRET_KEY ||
      !process.env.STRIPE_PRICE_ID ||
      !process.env.PUBLIC_URL) {
    return {
      statusCode: 500,
      body: JSON.stringify({
        error: 'config-missing',
        message: 'Variables Stripe non configurees sur Netlify (STRIPE_SECRET_KEY, STRIPE_PRICE_ID, PUBLIC_URL).',
      }),
    };
  }

  try {
    const session = await stripe.checkout.sessions.create({
      mode: 'payment',
      payment_method_types: ['card'],
      line_items: [{ price: process.env.STRIPE_PRICE_ID, quantity: 1 }],
      locale: 'fr',
      customer_creation: 'always',
      automatic_tax: { enabled: false },
      billing_address_collection: 'auto',
      allow_promotion_codes: true,
      metadata: {
        product: 'alphabeast-v1',
        consent_immediate_execution: 'true',
        source: event.headers.referer || event.headers.referrer || 'direct',
      },
      success_url: `${process.env.PUBLIC_URL}/success.html?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${process.env.PUBLIC_URL}/cancel.html`,
      expires_at: Math.floor(Date.now() / 1000) + 30 * 60,
      custom_text: {
        submit: {
          message: 'En validant, vous acceptez la livraison immédiate du contenu numérique et reconnaissez avoir lu nos CGV.',
        },
      },
    });

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: session.url, id: session.id }),
    };
  } catch (err) {
    console.error('Stripe session create failed:', err);
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: 'stripe-error', message: err.message }),
    };
  }
};
