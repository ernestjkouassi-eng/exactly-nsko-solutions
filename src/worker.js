// NSKO Solutions: serves the static site, handles POST /api/contact, and runs HQ (/hq and /api/hq/*).
// Settings (Cloudflare dashboard, Variables and Secrets): SUPABASE_SERVICE_KEY (admin project), NTFY_TOPIC (phone push), TURNSTILE_SITEKEY at build, CONTACT_TO (where briefs are emailed), RESEND_API_KEY, TURNSTILE_SECRET, HQ_PASSWORD.
// Storage: KV binding HQ (briefs, decisions, sign-ins, rate limits). The older binding name BRIEFS still works. Optional: FROM_EMAIL.
import {hqApi, briefStore} from './hq/api.js';
import {hqPage} from './hq/page.js';
import {intake} from './intake.js';

const json = (o, s = 200) => new Response(JSON.stringify(o), {status: s, headers: {'content-type': 'application/json', 'cache-control': 'no-store'}});
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const clip = (s, n) => String(s ?? '').slice(0, n);

async function contact(req, env) {
  if (req.method !== 'POST') return json({ok: false, error: 'method'}, 405);
  let d; try { d = await req.json(); } catch { return json({ok: false, error: 'bad json'}, 400); }
  if (!d || typeof d !== 'object') return json({ok: false, error: 'bad json'}, 400);
  if (d.website) return json({ok: true});                       // honeypot: pretend success
  const f = {name: clip(d.name, 120), company: clip(d.company, 160), email: clip(d.email, 200), phone: clip(d.phone, 40), sector: clip(d.sector, 80), project: clip(d.project, 160), budget: clip(d.budget, 40), timeline: clip(d.timeline, 120), message: clip(d.message, 5000), nda: !!d.nda};
  if (!f.name || !/^\S+@\S+\.\S+$/.test(f.email) || !f.message) return json({ok: false, error: 'missing fields'}, 400);
  const ip = req.headers.get('cf-connecting-ip') || 'x';
  const kv = briefStore(env);
  if (kv) { const k = 'rl:' + ip, n = +(await kv.get(k) || 0); if (n >= 5) return json({ok: false, error: 'slow down'}, 429); await kv.put(k, String(n + 1), {expirationTtl: 3600}); }
  if (env.TURNSTILE_SECRET) {
    const tok = d['cf-turnstile-response'] || d.turnstile || '';
    const r = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {method: 'POST', body: new URLSearchParams({secret: env.TURNSTILE_SECRET, response: tok, remoteip: ip})});
    if (!(await r.json()).success) return json({ok: false, error: 'captcha'}, 400);
  }
  // Save first, so a brief is never lost even if email is off or fails. HQ shows these in its Inbox.
  const at = new Date().toISOString(), key = 'brief:' + at + ':' + crypto.randomUUID();
  const rec = {...f, ip, at, state: 'new', emailed: false};
  let saved = false;
  if (kv) { try { await kv.put(key, JSON.stringify(rec)); saved = true; } catch {} }
  const subject = `New NSKO brief: ${f.company || f.name} · ${f.sector} · ${f.budget}`;
  const html = `<h2>${esc(subject)}</h2>` + Object.entries(f).map(([k, v]) => `<p><b>${esc(k)}:</b> ${esc(v)}</p>`).join('');
  let sent = false;
  if (env.RESEND_API_KEY && env.CONTACT_TO) {
    try {
      const r = await fetch('https://api.resend.com/emails', {method: 'POST', headers: {authorization: 'Bearer ' + env.RESEND_API_KEY, 'content-type': 'application/json'}, body: JSON.stringify({from: env.FROM_EMAIL || 'NSKO Solutions <hello@nskosolutions.co.uk>', to: [env.CONTACT_TO], reply_to: f.email, subject, html})});
      sent = r.ok;
    } catch {}
    if (sent && saved) { try { await kv.put(key, JSON.stringify({...rec, emailed: true})); } catch {} }
  }
  if (!sent && !saved) return json({ok: false, error: 'not configured'}, 503);
  return json({ok: true});
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const p = url.pathname;
    // quant.nskosolutions.co.uk serves the NSKO QUANT live demo, which lives in public/quant/
    if (url.hostname.startsWith('quant.')) {
      if (p.startsWith('/quant/')) return Response.redirect(url.origin + p.slice(6) + url.search, 301);
      const u = new URL(req.url); u.pathname = '/quant' + (p === '/' ? '/' : p);
      return env.ASSETS.fetch(new Request(u, req));
    }
    if (p === '/api/contact') return contact(req, env);
    if (p === '/api/brief') return intake(req, env, 'brief');
    if (p === '/api/portfolio') return intake(req, env, 'portfolio');
    if (p === '/api/quant-order') return intake(req, env, 'quant_order');   // NSKO QUANT checkout reservations (/nsko-quant)
    if (p.startsWith('/api/hq/')) return hqApi(req, env, url);
    if (p === '/hq') return hqPage(req, env);
    if (p.startsWith('/hq/')) return Response.redirect(url.origin + '/hq', 302);
    return env.ASSETS.fetch(req);
  },
};
