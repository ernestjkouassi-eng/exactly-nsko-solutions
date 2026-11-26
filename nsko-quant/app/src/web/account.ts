// Web demo accounts (nskosolutions.co.uk/quant only). Visitors sign up or log in with Supabase before the desk shows.
// The desktop app never uses this: it logs into the local engine. Only the publishable key is here; every rule
// lives in the database (quant_profiles: RLS on, a user can read, add and change only their own row).
import { create } from 'zustand'
import type { SupabaseClient, User } from '@supabase/supabase-js'
import { isTauri } from '../api'

/** True only in the browser build made with VITE_WEB_DEMO=1 (never inside the Tauri desktop shell). */
export const WEB_DEMO = import.meta.env.VITE_WEB_DEMO === '1' && !isTauri

const SB_URL = 'https://rluiyojdvkahfjuugqzt.supabase.co'
const SB_KEY = 'sb_publishable_NJWZ-zPaMkhomhYT5ZCWFA_j09PJ0bC'   // publishable key: safe in client code
export const PRODUCT_URL = '/nsko-quant'
const home = () => `${location.origin}/quant/`

export type Experience = 'new' | 'some' | 'experienced'
export type SignUpForm = { name: string; email: string; password: string; country: string; experience: Experience; marketing: boolean }
type Acct = { status: 'loading' | 'out' | 'in' | 'recovery'; user: User | null; name: string; urlNote: string }
export const useAcct = create<Acct>(() => ({ status: 'loading', user: null, name: '', urlNote: '' }))

let sb: SupabaseClient | null = null
async function client() {
  if (sb) return sb
  const { createClient } = await import('@supabase/supabase-js')
  sb = createClient(SB_URL, SB_KEY, { auth: { storageKey: 'nq-quant-auth', persistSession: true, autoRefreshToken: true, detectSessionInUrl: true } })
  return sb
}

const nameOf = (u: User | null) => String(u?.user_metadata?.full_name || '').trim() || (u?.email ? u.email.split('@')[0] : '')

/** Create the profile row from the details given at sign-up, the first time the user has a session (after email confirmation). */
async function ensureProfile(u: User) {
  const c = await client(), m = u.user_metadata || {}
  const { data } = await c.from('quant_profiles').select('full_name').eq('id', u.id).maybeSingle()
  if (data) { if (data.full_name) useAcct.setState({ name: data.full_name }); return }
  const exp = ['new', 'some', 'experienced'].includes(m.experience) ? m.experience : null
  await c.from('quant_profiles').insert({ id: u.id, full_name: String(m.full_name || '').slice(0, 120) || null, country: String(m.country || '').slice(0, 80) || null, experience: exp, marketing_ok: m.marketing_ok === true })
}

const signedIn = (u: User) => { useAcct.setState({ status: 'in', user: u, name: nameOf(u) }); // deferred: Supabase calls made inside an auth callback can deadlock
  setTimeout(() => ensureProfile(u).catch(() => { /* the desk still works without the profile row */ }), 0) }

let started = false
export async function initAccount() {
  if (started || !WEB_DEMO) return; started = true
  // Supabase puts link errors (expired or used confirmation link) in the address bar: show them on the gate in plain words.
  const h = new URLSearchParams(location.hash.slice(1)), q = new URLSearchParams(location.search)
  const linkErr = h.get('error_description') || q.get('error_description')
  if (linkErr) useAcct.setState({ urlNote: /expired|invalid/i.test(linkErr) ? 'That email link has expired or was already used. Log in, or ask for a new link.' : linkErr.replace(/\+/g, ' ') })
  try {
    const c = await client()
    c.auth.onAuthStateChange((ev, s) => {
      if (ev === 'PASSWORD_RECOVERY') { useAcct.setState({ status: 'recovery', user: s?.user ?? null }); return }
      if (ev === 'SIGNED_OUT') { useAcct.setState({ status: 'out', user: null, name: '' }); return }
      if (s?.user && useAcct.getState().status !== 'recovery' && (ev === 'SIGNED_IN' || ev === 'INITIAL_SESSION') && useAcct.getState().user?.id !== s.user.id) signedIn(s.user)
    })
    const { data } = await c.auth.getSession()
    if (useAcct.getState().status === 'loading') { if (data.session?.user) signedIn(data.session.user); else useAcct.setState({ status: 'out' }) }
    if (location.hash.includes('access_token') || linkErr) history.replaceState(null, '', location.pathname + location.search.replace(/[?&]error[^&]*/g, ''))
  } catch { useAcct.setState({ status: 'out', urlNote: 'Accounts are not reachable right now. Check your connection and try again.' }) }
}

/** Plain-English messages for the errors people actually hit. */
function say(e: { message?: string; code?: string; status?: number } | null | undefined): string {
  const m = (e?.message || '').toLowerCase(), c = e?.code || ''
  if (c === 'invalid_credentials' || m.includes('invalid login')) return 'That email and password do not match an account.'
  if (c === 'email_not_confirmed' || m.includes('not confirmed')) return 'Please confirm your email first: open the link we sent you, then log in.'
  if (c === 'user_already_exists' || m.includes('already registered')) return 'An account with this email already exists. Log in instead.'
  if (c === 'weak_password' || m.includes('password')) return 'Choose a stronger password: at least 10 characters, not a common one.'
  if (c === 'over_email_send_rate_limit' || c === 'over_request_rate_limit' || e?.status === 429) return 'Too many tries. Please wait a few minutes and try again.'
  if (c === 'signup_disabled' || m.includes('signups not allowed')) return 'New accounts are paused right now. Please try again later.'
  if (m.includes('fetch') || m.includes('network')) return 'Could not reach the account service. Check your connection and try again.'
  return e?.message || 'Something went wrong. Please try again.'
}
type R = { ok: true; confirm?: boolean } | { ok: false; error: string }

export async function signUp(f: SignUpForm): Promise<R> {
  try {
    const c = await client()
    const { data, error } = await c.auth.signUp({ email: f.email.trim(), password: f.password, options: { emailRedirectTo: home(),
      data: { full_name: f.name.trim(), country: f.country, experience: f.experience, marketing_ok: f.marketing, product: 'nsko-quant-demo' } } })
    if (error) return { ok: false, error: say(error) }
    // Email confirmation on: no session yet. (An existing address also comes back with no identities and no email sent.)
    if (!data.session) return data.user && data.user.identities?.length === 0 ? { ok: false, error: say({ code: 'user_already_exists' }) } : { ok: true, confirm: true }
    return { ok: true }
  } catch (e: any) { return { ok: false, error: say(e) } }
}

export async function logIn(email: string, password: string): Promise<R> {
  try { const c = await client(); const { error } = await c.auth.signInWithPassword({ email: email.trim(), password }); return error ? { ok: false, error: say(error) } : { ok: true } }
  catch (e: any) { return { ok: false, error: say(e) } }
}

export async function sendReset(email: string): Promise<R> {
  try { const c = await client(); const { error } = await c.auth.resetPasswordForEmail(email.trim(), { redirectTo: home() }); return error ? { ok: false, error: say(error) } : { ok: true } }
  catch (e: any) { return { ok: false, error: say(e) } }
}

export async function setNewPassword(password: string): Promise<R> {
  try {
    const c = await client(); const { data, error } = await c.auth.updateUser({ password })
    if (error) return { ok: false, error: say(error) }
    if (data.user) signedIn(data.user)
    return { ok: true }
  } catch (e: any) { return { ok: false, error: say(e) } }
}

export async function logOut() {
  try { const c = await client(); await c.auth.signOut() } catch { /* clear locally anyway */ }
  useAcct.setState({ status: 'out', user: null, name: '' })
}
