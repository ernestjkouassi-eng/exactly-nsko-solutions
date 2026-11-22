// Serves the HQ page with its own strict Content Security Policy (a fresh nonce per request).
import shell from './shell.html';
import {getSession} from './auth.js';

export async function hqPage(req, env) {
  const mode = !env.HQ_PASSWORD ? 'setup' : (await getSession(req, env)) ? 'app' : 'login';
  const nonce = btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(16))));
  const html = shell.replaceAll('__NONCE__', nonce).replace('__MODE__', mode);
  return new Response(html, {headers: {
    'content-type': 'text/html; charset=utf-8',
    'cache-control': 'no-store',
    'content-security-policy': `default-src 'none'; script-src 'nonce-${nonce}'; style-src 'nonce-${nonce}'; font-src 'self'; img-src 'self' data:; connect-src 'self'; manifest-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'`,
    'x-frame-options': 'DENY',
    'x-content-type-options': 'nosniff',
    'referrer-policy': 'no-referrer',
    'x-robots-tag': 'noindex, nofollow',
    'permissions-policy': 'camera=(), microphone=(), geolocation=()',
    'strict-transport-security': 'max-age=31536000; includeSubDomains',
  }});
}
