// NSKO Solutions: serves the static site and handles POST /api/contact.
// Settings (Cloudflare dashboard, Variables and Secrets): CONTACT_TO (where briefs are emailed), RESEND_API_KEY, TURNSTILE_SECRET.
// Optional: KV binding BRIEFS (backup copy and rate limit), FROM_EMAIL.
const json = (o, s = 200) => new Response(JSON.stringify(o), {status: s, headers: {'content-type': 'application/json', 'cache-control': 'no-store'}});
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const clip = (s, n) => String(s ?? '').slice(0, n);
export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (url.pathname !== '/api/contact') return env.ASSETS.fetch(req);
    if (req.method !== 'POST') return json({ok: false, error: 'method'}, 405);
    let d; try { d = await req.json(); } catch { return json({ok: false, error: 'bad json'}, 400); }
    if (d.website) return json({ok: true});                       // honeypot: pretend success
    const f = {name: clip(d.name, 120), company: clip(d.company, 160), email: clip(d.email, 200), phone: clip(d.phone, 40), sector: clip(d.sector, 80), project: clip(d.project, 160), budget: clip(d.budget, 40), timeline: clip(d.timeline, 120), message: clip(d.message, 5000), nda: !!d.nda};
    if (!f.name || !/^\S+@\S+\.\S+$/.test(f.email) || !f.message) return json({ok: false, error: 'missing fields'}, 400);
    const ip = req.headers.get('cf-connecting-ip') || 'x';
    if (env.BRIEFS) { const k = 'rl:' + ip, n = +(await env.BRIEFS.get(k) || 0); if (n >= 5) return json({ok: false, error: 'slow down'}, 429); await env.BRIEFS.put(k, String(n + 1), {expirationTtl: 3600}); }
    if (env.TURNSTILE_SECRET) {
      const tok = d['cf-turnstile-response'] || d.turnstile || '';
      const r = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {method: 'POST', body: new URLSearchParams({secret: env.TURNSTILE_SECRET, response: tok, remoteip: ip})});
      if (!(await r.json()).success) return json({ok: false, error: 'captcha'}, 400);
    }
    if (env.BRIEFS) await env.BRIEFS.put('brief:' + Date.now() + ':' + crypto.randomUUID(), JSON.stringify({...f, ip, at: new Date().toISOString()}));
    const subject = `New NSKO brief: ${f.company || f.name} · ${f.sector} · ${f.budget}`;
    const html = `<h2>${esc(subject)}</h2>` + Object.entries(f).map(([k, v]) => `<p><b>${esc(k)}:</b> ${esc(v)}</p>`).join('');
    let sent = false;
    if (env.RESEND_API_KEY && env.CONTACT_TO) {
      const r = await fetch('https://api.resend.com/emails', {method: 'POST', headers: {authorization: 'Bearer ' + env.RESEND_API_KEY, 'content-type': 'application/json'}, body: JSON.stringify({from: env.FROM_EMAIL || 'NSKO Solutions <hello@nskosolutions.co.uk>', to: [env.CONTACT_TO], reply_to: f.email, subject, html})});
      sent = r.ok;
    }
    if (!sent && !env.BRIEFS) return json({ok: false, error: 'not configured'}, 503);
    return json({ok: true});
  },
};
