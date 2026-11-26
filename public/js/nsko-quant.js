// NSKO QUANT product page (/nsko-quant): prices, monthly/yearly toggle, checkout modal, reveal on scroll.

/* =====================================================================
   PRICES: the ONE place to change what the page shows.
   amount is in whole pounds. The page formats it (e.g. 1490 -> £1,490).
   ===================================================================== */
const PRICES = {
  standard: {name: 'Standard', monthly: 149, yearly: 1490},
  pro:      {name: 'Pro',      monthly: 349, yearly: 3490},
  founders: {name: 'Founders Licence', once: 4950, note: 'First 100 clients only'},
};

/* =====================================================================
   STRIPE_PAYMENT_LINKS
   Paste a Stripe Payment Link (https://buy.stripe.com/...) into a slot and
   that plan's "Buy now" goes straight to Stripe instead of opening the
   reservation form. Leave a slot as '' to keep the form for that plan.
   Keys: <plan>_<billing>, and 'founders' for the one-off licence.
   Stripe is a full-page redirect, so no security-policy change is needed.
   ===================================================================== */
const STRIPE_PAYMENT_LINKS = {
  standard_monthly: '',
  standard_yearly: '',
  pro_monthly: '',
  pro_yearly: '',
  founders: '',
};

const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const gbp = n => '£' + Number(n).toLocaleString('en-GB');
document.documentElement.classList.add('js');

let bill = 'monthly';
try { if (localStorage.getItem('nq-bill') === 'yearly') bill = 'yearly'; } catch {}

function priceOf(plan, b = bill) {
  const p = PRICES[plan];
  if (p.once != null) return {key: 'founders', billing: 'once', amount: p.once, label: gbp(p.once) + ' one-off', per: ' one-off', alt: p.note || ''};
  if (b === 'yearly') return {key: plan + '_yearly', billing: 'yearly', amount: p.yearly, label: gbp(p.yearly) + '/year', per: '/year', alt: 'or ' + gbp(p.monthly) + '/month'};
  return {key: plan + '_monthly', billing: 'monthly', amount: p.monthly, label: gbp(p.monthly) + '/month', per: '/month', alt: 'or ' + gbp(p.yearly) + '/year'};
}
function render() {
  $$('[data-bill]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.bill === bill)));
  $$('.q-plan').forEach(card => {
    const x = priceOf(card.dataset.plan);
    $('[data-price]', card).textContent = gbp(x.amount);
    $('[data-per]', card).textContent = x.per;
    $('[data-alt]', card).textContent = x.alt;
  });
}
$$('[data-bill]').forEach(b => b.addEventListener('click', () => { bill = b.dataset.bill; try { localStorage.setItem('nq-bill', bill); } catch {} render(); }));
render();

/* ---------- checkout ---------- */
const dlg = $('#order'), form = $('#oform'), msg = $('.msg', form), sub = $('[type=submit]', form);
let tsKey = $('meta[name=nsko-ts]')?.content, tsLoaded = false;
function turnstile() {
  if (!tsKey) return;
  const draw = () => $$('[data-ts]', form).forEach(el => { if (!el.childElementCount) window.turnstile.render(el, {sitekey: tsKey, theme: 'dark', size: 'flexible'}); });
  if (tsLoaded) return window.turnstile && draw();
  tsLoaded = true; const s = document.createElement('script');
  s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'; s.async = true; s.onload = draw; document.head.appendChild(s);
}
function openCheckout(plan) {
  const x = priceOf(plan), link = STRIPE_PAYMENT_LINKS[x.key];
  if (link) { location.href = link; return; }
  form.elements.plan.value = plan; form.elements.billing.value = x.billing; form.elements.price.value = x.label;
  $('[data-o-plan]', dlg).textContent = PRICES[plan].name + (x.billing === 'once' ? '' : x.billing === 'yearly' ? ' · Yearly' : ' · Monthly');
  $('[data-o-price]', dlg).textContent = x.label;
  msg.textContent = ''; sub.disabled = false;
  if (dlg.showModal) dlg.showModal(); else dlg.setAttribute('open', '');
  turnstile();
  setTimeout(() => $('#o-name').focus(), 50);
}
$$('[data-buy]').forEach(b => b.addEventListener('click', () => openCheckout(b.dataset.buy)));
$$('[data-close]', dlg).forEach(b => b.addEventListener('click', () => dlg.close()));
dlg.addEventListener('click', e => { if (e.target === dlg) dlg.close(); });

const errText = e => ({'slow down': 'Too many tries. Please wait an hour and try again.', captcha: 'Please complete the check and try again.', 'missing fields': 'Please fill in every field and tick the box.'}[e.message] || 'That did not send. Please email hello@nskosolutions.co.uk and we will reserve your licence by hand.');
form.addEventListener('submit', async e => {
  e.preventDefault();
  for (const el of $$('[required]', form)) {
    const bad = el.type === 'checkbox' ? !el.checked : !el.value.trim() || (el.type === 'email' && !/^\S+@\S+\.\S+$/.test(el.value));
    if (bad) { el.focus(); msg.textContent = el.type === 'checkbox' ? 'Please tick the box to confirm you have read the risk warning.' : 'Please fill in ' + ($(`label[for="${el.id}"]`)?.textContent || 'this field').toLowerCase() + '.'; return; }
  }
  sub.disabled = true; msg.textContent = 'Sending.';
  try {
    const fd = new FormData(form); fd.set('source', location.pathname);
    const ts = $('[name="cf-turnstile-response"]', form); if (ts) fd.set('cf-turnstile-response', ts.value);
    const r = await fetch('/api/quant-order', {method: 'POST', body: fd}); let j = {}; try { j = await r.json(); } catch {}
    if (!r.ok || !j.ok) throw new Error(j.error || 'failed');
    $('[data-fields]', form).hidden = true; $('[data-actions]', form).hidden = true; msg.textContent = ''; msg.hidden = true;
    const done = document.createElement('div'); done.className = 'q-done';
    const h = document.createElement('h3'); h.textContent = 'Reserved.';
    const p = document.createElement('p'); p.textContent = "We'll email your secure payment link and licence within one working day.";
    done.append(h, p); form.appendChild(done);
  } catch (er) { msg.textContent = errText(er); sub.disabled = false; }
});
// After a reservation, closing the modal resets it so another plan can be reserved.
dlg.addEventListener('close', () => { const d = $('.q-done', form); if (d) { d.remove(); form.reset(); $('[data-fields]', form).hidden = false; $('[data-actions]', form).hidden = false; msg.hidden = false; } });
