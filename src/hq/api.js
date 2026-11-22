// HQ API: /api/hq/*. Everything except /login needs a valid session.
import status from '../../hq/status.json';
import {passwordMatches, createSession, getSession, endSession, clearCookie, triesUsed, recordFail, clearFails, MAX_TRIES, LOCK_SECONDS} from './auth.js';

const json = (o, s = 200, extra = {}) => new Response(JSON.stringify(o), {status: s, headers: {'content-type': 'application/json', 'cache-control': 'no-store', 'x-content-type-options': 'nosniff', 'x-robots-tag': 'noindex', ...extra}});
const BRIEF_STATES = ['new', 'replied', 'archived'];
const ID_RE = /^[A-Za-z0-9:._-]{1,120}$/;

export const briefStore = env => env.HQ || env.BRIEFS || null;

async function body(req) { try { return await req.json(); } catch { return null; } }

// Every write must come from this site, as JSON (blocks cross-site form posts).
function sameOrigin(req, url) {
  const o = req.headers.get('origin');
  if (o && o !== url.origin) return false;
  return (req.headers.get('content-type') || '').toLowerCase().startsWith('application/json');
}

async function listBriefs(kv) {
  const keys = []; let cursor;
  do {
    const page = await kv.list({prefix: 'brief:', cursor});
    keys.push(...page.keys.map(k => k.name));
    cursor = page.list_complete ? null : page.cursor;
  } while (cursor && keys.length < 1000);
  keys.sort().reverse();
  const top = keys.slice(0, 200);
  const vals = await Promise.all(top.map(k => kv.get(k, 'json')));
  return top.map((k, i) => vals[i] && {id: k.slice(6), ...vals[i], state: BRIEF_STATES.includes(vals[i].state) ? vals[i].state : 'new'})
    .filter(Boolean)
    .map(({ip, ...b}) => b)                                     // never send visitor IPs to the browser
    .sort((a, b) => String(b.at).localeCompare(String(a.at)));
}

async function approvals(env) {
  const kv = env.HQ;
  const items = status.approvals || [];
  const decisions = kv ? await Promise.all(items.map(a => kv.get('decision:' + a.id, 'json'))) : items.map(() => null);
  return items.map((a, i) => ({...a, decision: decisions[i] || null}));
}

async function timed(fn) {
  const t = Date.now();
  try { const r = await fn(); return {status: r.status, ok: r.ok, ms: Date.now() - t}; }
  catch (e) { return {status: 0, ok: false, ms: Date.now() - t, error: e && e.name === 'TimeoutError' ? 'No answer within 8 seconds' : 'Could not connect'}; }
}

async function health(req, env, url) {
  const live = 'https://nskosolutions.co.uk';
  const liveChecks = [['Home page', '/'], ['Main stylesheet', '/css/site.css'], ['Main script', '/js/main.js'], ['Inter font', '/fonts/Inter.woff2'], ['robots.txt', '/robots.txt']];
  const localChecks = [['Home page', '/'], ['Main stylesheet', '/css/site.css'], ['Inter font', '/fonts/Inter.woff2']];
  const [liveRes, localRes] = await Promise.all([
    Promise.all(liveChecks.map(([name, path]) => timed(() => fetch(live + path, {signal: AbortSignal.timeout(8000), headers: {'user-agent': 'NSKO-HQ-health-check'}})).then(r => ({name, url: live + path, ...r})))),
    Promise.all(localChecks.map(([name, path]) => timed(() => env.ASSETS.fetch(new Request(url.origin + path))).then(r => ({name, url: path, ...r})))),
  ]);
  const has = k => typeof env[k] === 'string' && env[k].length > 0;
  return {
    checkedAt: new Date().toISOString(),
    live: liveRes,
    deployment: localRes,
    config: [
      {key: 'HQ_PASSWORD', set: has('HQ_PASSWORD'), what: 'Password for this HQ page.'},
      {key: 'HQ storage (KV)', set: !!env.HQ, what: 'Where briefs, decisions and sign-ins are stored. Cloudflare creates it on deploy.'},
      {key: 'CONTACT_TO', set: has('CONTACT_TO'), what: 'The email address new briefs are sent to.'},
      {key: 'RESEND_API_KEY', set: has('RESEND_API_KEY'), what: 'Lets the site send email through Resend.'},
      {key: 'TURNSTILE_SECRET', set: has('TURNSTILE_SECRET'), what: 'Cloudflare’s spam check on the contact form.'},
    ],
  };
}

export async function hqApi(req, env, url) {
  const route = url.pathname.slice('/api/hq/'.length);
  const post = req.method === 'POST';
  if (post && !sameOrigin(req, url)) return json({ok: false, error: 'forbidden'}, 403);

  if (route === 'login') {
    if (!post) return json({ok: false, error: 'method'}, 405);
    if (!env.HQ_PASSWORD) return json({ok: false, error: 'setup'}, 503);
    const ip = req.headers.get('cf-connecting-ip') || 'local';
    const used = await triesUsed(env, ip);
    if (used >= MAX_TRIES) return json({ok: false, error: 'locked', minutes: LOCK_SECONDS / 60}, 429);
    const d = await body(req);
    const pw = d && typeof d.password === 'string' ? d.password.slice(0, 512) : '';
    if (!pw || !(await passwordMatches(env, pw))) {
      await recordFail(env, ip, used);
      const left = MAX_TRIES - used - 1;
      // A wrong password is an expected answer, not a server error: 200 with ok:false keeps the browser console clean.
      return json(left > 0 ? {ok: false, error: 'wrong', left} : {ok: false, error: 'locked', minutes: LOCK_SECONDS / 60}, left > 0 ? 200 : 429);
    }
    await clearFails(env, ip);
    const {cookie} = await createSession(env);
    return json({ok: true}, 200, {'set-cookie': cookie});
  }

  const s = await getSession(req, env);
  if (!s) return json({ok: false, error: 'signed out'}, 401);

  if (route === 'logout' && post) { await endSession(env, s); return json({ok: true}, 200, {'set-cookie': clearCookie}); }
  if (route === 'me') return json({ok: true, until: s.exp});

  if (route === 'briefs' && !post) {
    const kv = briefStore(env);
    if (!kv) return json({ok: true, storage: false, briefs: []});
    return json({ok: true, storage: true, briefs: await listBriefs(kv)});
  }
  if (route === 'briefs/state' && post) {
    const kv = briefStore(env), d = await body(req);
    if (!kv) return json({ok: false, error: 'no storage'}, 503);
    if (!d || !ID_RE.test(d.id || '') || !BRIEF_STATES.includes(d.state)) return json({ok: false, error: 'bad request'}, 400);
    const rec = await kv.get('brief:' + d.id, 'json');
    if (!rec) return json({ok: false, error: 'not found'}, 404);
    rec.state = d.state; rec.stateAt = new Date().toISOString();
    await kv.put('brief:' + d.id, JSON.stringify(rec));
    return json({ok: true, state: rec.state, stateAt: rec.stateAt});
  }

  if (route === 'approvals' && !post) return json({ok: true, storage: !!env.HQ, approvals: await approvals(env)});
  if (route === 'approvals/decide' && post) {
    const d = await body(req);
    if (!env.HQ) return json({ok: false, error: 'no storage'}, 503);
    const item = d && (status.approvals || []).find(a => a.id === d.id);
    if (!item || !['approved', 'declined', 'undo'].includes(d.decision)) return json({ok: false, error: 'bad request'}, 400);
    if (d.decision === 'undo') { await env.HQ.delete('decision:' + item.id); return json({ok: true, decision: null}); }
    const rec = {decision: d.decision, at: new Date().toISOString()};
    await env.HQ.put('decision:' + item.id, JSON.stringify(rec));
    return json({ok: true, decision: rec});
  }

  if (route === 'team') return json({ok: true, updated: status.updated, team: status.team || []});
  if (route === 'log') return json({ok: true, updated: status.updated, log: status.log || []});
  if (route === 'health') return json({ok: true, ...(await health(req, env, url))});

  return json({ok: false, error: 'not found'}, 404);
}
