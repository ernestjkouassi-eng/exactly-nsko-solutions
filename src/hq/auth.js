// HQ sign-in: password check, signed session cookie, login rate limit.
// The only secret is the Worker secret HQ_PASSWORD. It is never sent to the browser.
const enc = new TextEncoder();
export const COOKIE = '__Host-nsko_hq';
const SESSION_SECONDS = 12 * 60 * 60;
const MAX_TRIES = 5, LOCK_SECONDS = 15 * 60;

const b64u = buf => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const unb64u = s => Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0));

// Signing key is derived from HQ_PASSWORD, so changing the password signs everyone out.
async function key(env, purpose) {
  const raw = await crypto.subtle.digest('SHA-256', enc.encode('nsko-hq:' + purpose + ':' + env.HQ_PASSWORD));
  return crypto.subtle.importKey('raw', raw, {name: 'HMAC', hash: 'SHA-256'}, false, ['sign', 'verify']);
}

// Constant-time password check: compare fixed-length MACs, never the raw strings.
export async function passwordMatches(env, given) {
  const k = await key(env, 'pw');
  const [a, b] = await Promise.all([crypto.subtle.sign('HMAC', k, enc.encode(String(given))), crypto.subtle.sign('HMAC', k, enc.encode(env.HQ_PASSWORD))]);
  if (crypto.subtle.timingSafeEqual) return crypto.subtle.timingSafeEqual(a, b);
  const x = new Uint8Array(a), y = new Uint8Array(b); let d = 0;
  for (let i = 0; i < x.length; i++) d |= x[i] ^ y[i];
  return d === 0;
}

export function readCookie(req, name = COOKIE) {
  const c = req.headers.get('cookie') || '';
  for (const part of c.split(/;\s*/)) { const i = part.indexOf('='); if (i > 0 && part.slice(0, i) === name) return part.slice(i + 1); }
  return '';
}

export async function createSession(env) {
  const sid = crypto.randomUUID();
  const payload = b64u(enc.encode(JSON.stringify({sid, exp: Date.now() + SESSION_SECONDS * 1000})));
  const sig = b64u(await crypto.subtle.sign('HMAC', await key(env, 'session'), enc.encode(payload)));
  if (env.HQ) await env.HQ.put('sess:' + sid, '1', {expirationTtl: SESSION_SECONDS});
  return {cookie: `${COOKIE}=${payload}.${sig}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=${SESSION_SECONDS}`, sid};
}

export const clearCookie = `${COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0`;

// Returns the session ({sid, exp}) or null. HMAC verify is constant-time.
export async function getSession(req, env) {
  if (!env.HQ_PASSWORD) return null;
  const v = readCookie(req);
  const dot = v.indexOf('.');
  if (dot < 1) return null;
  const payload = v.slice(0, dot), sig = v.slice(dot + 1);
  let ok = false, s;
  try {
    ok = await crypto.subtle.verify('HMAC', await key(env, 'session'), unb64u(sig), enc.encode(payload));
    s = JSON.parse(new TextDecoder().decode(unb64u(payload)));
  } catch { return null; }
  if (!ok || !s || typeof s.sid !== 'string' || !(s.exp > Date.now())) return null;
  if (env.HQ && !(await env.HQ.get('sess:' + s.sid))) return null;   // signed out on the server
  return s;
}

export async function endSession(env, s) { if (env.HQ && s) await env.HQ.delete('sess:' + s.sid); }

// Login rate limit: 5 wrong tries per IP, then a 15 minute pause.
export async function triesUsed(env, ip) { return env.HQ ? +(await env.HQ.get('hqrl:' + ip) || 0) : 0; }
export async function recordFail(env, ip, used) { if (env.HQ) await env.HQ.put('hqrl:' + ip, String(used + 1), {expirationTtl: LOCK_SECONDS}); }
export async function clearFails(env, ip) { if (env.HQ) await env.HQ.delete('hqrl:' + ip); }
export {MAX_TRIES, LOCK_SECONDS};
