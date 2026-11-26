// v4.2 intake: Start-a-project briefs (with optional private file), portfolio-pack requests and NSKO QUANT order reservations.
// quant_order rows go into the same `briefs` table (sector 'NSKO QUANT') so they show in the admin Inbox; no payment is taken.
// Saves to the NSKO admin Supabase project with the service key (Worker secret SUPABASE_SERVICE_KEY, never sent to browsers).
// Fallback: KV, so nothing is lost before the key is added. Notifies Ernest by email (Resend) and phone push (ntfy) if set.
import {briefStore} from './hq/api.js';
const SB = 'https://rluiyojdvkahfjuugqzt.supabase.co';
const json = (o, s = 200) => new Response(JSON.stringify(o), {status: s, headers: {'content-type': 'application/json', 'cache-control': 'no-store'}});
const clip = (v, n) => String(v ?? '').trim().slice(0, n);
const MIME = ['application/pdf', 'image/png', 'image/jpeg', 'image/webp', 'text/plain', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];

async function limited(env, ip, kind) {
  const kv = briefStore(env); if (!kv) return false;
  const k = `rl:${kind}:${ip}`, n = +(await kv.get(k) || 0);
  if (n >= 5) return true; await kv.put(k, String(n + 1), {expirationTtl: 3600}); return false;
}
async function human(env, fd, ip) {
  if (!env.TURNSTILE_SECRET) return true;
  const r = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {method: 'POST', body: new URLSearchParams({secret: env.TURNSTILE_SECRET, response: String(fd.get('cf-turnstile-response') || ''), remoteip: ip})});
  return !!(await r.json()).success;
}
const sb = (env, path, init = {}) => fetch(SB + path, {...init, headers: {apikey: env.SUPABASE_SERVICE_KEY, authorization: 'Bearer ' + env.SUPABASE_SERVICE_KEY, ...(init.headers || {})}});
async function notify(env, subject, lines) {
  const jobs = [];
  if (env.RESEND_API_KEY && env.CONTACT_TO) jobs.push(fetch('https://api.resend.com/emails', {method: 'POST', headers: {authorization: 'Bearer ' + env.RESEND_API_KEY, 'content-type': 'application/json'},
    body: JSON.stringify({from: env.FROM_EMAIL || 'NSKO Solutions <hello@nskosolutions.co.uk>', to: [env.CONTACT_TO], subject, text: lines.join('\n') + '\n\nOpen the admin: https://nskosolutions.co.uk/admin'})}));
  if (env.NTFY_TOPIC) jobs.push(fetch('https://ntfy.sh/' + encodeURIComponent(env.NTFY_TOPIC), {method: 'POST', headers: {Title: subject, Click: 'https://nskosolutions.co.uk/admin'}, body: lines.slice(0, 3).join(' · ')}));
  await Promise.allSettled(jobs);
}
export async function intake(req, env, kind) {
  if (req.method !== 'POST') return json({ok: false, error: 'method'}, 405);
  let fd; try { fd = await req.formData(); } catch { return json({ok: false, error: 'bad form'}, 400); }
  if (fd.get('website')) return json({ok: true});                       // honeypot
  const ip = req.headers.get('cf-connecting-ip') || 'x';
  if (await limited(env, ip, kind)) return json({ok: false, error: 'slow down'}, 429);
  if (!(await human(env, fd, ip))) return json({ok: false, error: 'captcha'}, 400);
  const email = clip(fd.get('email'), 200), name = clip(fd.get('name'), 120);
  if (!name || !/^\S+@\S+\.\S+$/.test(email) || !fd.get('consent')) return json({ok: false, error: 'missing fields'}, 400);
  let row, table, subject;
  if (kind === 'brief') {
    const message = clip(fd.get('message'), 5000); if (!message) return json({ok: false, error: 'missing fields'}, 400);
    row = {sector: clip(fd.get('sector'), 80), need: clip(fd.get('type'), 200), message, budget: clip(fd.get('budget'), 40), timeline: clip(fd.get('timeline'), 60), nda: !!fd.get('nda'),
      name, company: clip(fd.get('company'), 160), email, phone: clip(fd.get('phone'), 40), source: clip(fd.get('source'), 120)};
    table = 'briefs'; subject = `New brief: ${row.company || name} · ${row.sector || 'no sector'} · ${row.budget || 'budget open'}`;
    const f = fd.get('file');
    if (f && typeof f === 'object' && f.size) {
      if (f.size > 10 * 1024 * 1024) return json({ok: false, error: 'file too large'}, 413);
      if (!MIME.includes(f.type)) return json({ok: false, error: 'file type'}, 415);
      const head = new Uint8Array(await f.slice(0, 8).arrayBuffer()), hex = [...head].map(b => b.toString(16).padStart(2, '0')).join('');
      const SIG = {'application/pdf': ['25504446'], 'image/png': ['89504e47'], 'image/jpeg': ['ffd8ff'], 'image/webp': ['52494646'], 'application/msword': ['d0cf11e0'], 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['504b0304']};
      if (SIG[f.type] && !SIG[f.type].some(x => hex.startsWith(x))) return json({ok: false, error: 'file type'}, 415);
      if (env.SUPABASE_SERVICE_KEY) {
        const path = `${new Date().toISOString().slice(0, 10)}/${crypto.randomUUID()}-${clip(f.name, 80).replace(/[^\w.-]/g, '_')}`;
        const up = await sb(env, '/storage/v1/object/briefs/' + path, {method: 'POST', headers: {'content-type': f.type}, body: f.stream()});
        if (up.ok) row.file_path = path;
      }
    }
  } else if (kind === 'quant_order') {
    const plan = clip(fd.get('plan'), 20), billing = clip(fd.get('billing'), 10), country = clip(fd.get('country'), 80), platform = clip(fd.get('platform'), 20);
    if (!['standard', 'pro', 'founders'].includes(plan) || !['monthly', 'yearly', 'once'].includes(billing) || (plan === 'founders') !== (billing === 'once')
      || !country || !['Windows', 'macOS', 'Linux'].includes(platform)) return json({ok: false, error: 'missing fields'}, 400);
    const price = clip(fd.get('price'), 40);
    row = {sector: 'NSKO QUANT', need: `quant_order · ${plan} · ${billing}`, budget: price, timeline: 'Reserve now', nda: false, name, company: '', email, phone: '', source: clip(fd.get('source'), 120) || '/nsko-quant',
      message: `NSKO QUANT order reservation\nPlan: ${plan} (${billing})\nPrice shown: ${price}\nCountry: ${country}\nPlatform: ${platform}\nRisk warning and terms accepted: yes\nNext step: email a secure payment link and the licence within one working day.`};
    table = 'briefs'; subject = `NSKO QUANT order: ${plan} ${billing} · ${price} · ${name}`;
  } else {
    row = {name, company: clip(fd.get('company'), 160), email, interest: clip(fd.get('interest'), 60)};
    table = 'portfolio_requests'; subject = `Portfolio pack request: ${row.company || name}`;
  }
  let saved = false;
  if (env.SUPABASE_SERVICE_KEY) { const r = await sb(env, '/rest/v1/' + table, {method: 'POST', headers: {'content-type': 'application/json', prefer: 'return=minimal'}, body: JSON.stringify(row)}); saved = r.ok; }
  if (!saved) { const kv = briefStore(env); if (kv) { try { await kv.put(`${kind === 'quant_order' ? 'brief' : kind}:${new Date().toISOString()}:${crypto.randomUUID()}`, JSON.stringify({...row, at: new Date().toISOString(), state: 'new'})); saved = true; } catch {} } }
  if (!saved) return json({ok: false, error: 'not configured'}, 503);
  await notify(env, subject, [`${name} (${row.company || 'no organisation'})`, email, kind !== 'portfolio' ? row.message.slice(0, 400) : 'Interested in: ' + row.interest]);
  return json({ok: true});
}
