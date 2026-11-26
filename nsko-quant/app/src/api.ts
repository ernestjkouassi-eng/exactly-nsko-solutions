// REST helpers for the local engine (127.0.0.1:8787).
// Every call degrades gracefully: in demo mode it returns demo data straight away; in engine mode, if the
// engine does not answer, it returns the same demo data with demo=true and shows a notice. Engine errors
// (4xx/5xx) are returned as ok=false with the engine's message, never silently replaced by demo data.
import { useS, notify } from './store'

// The engine always listens on 127.0.0.1:8787. `?engine=http://127.0.0.1:PORT` overrides it for development and tests only.
const override = typeof location !== 'undefined' ? new URLSearchParams(location.search).get('engine') : null
export const ENGINE = override && /^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(override) ? override : 'http://127.0.0.1:8787'
export const WS_URL = ENGINE.replace(/^http/, 'ws') + '/ws'
export const isTauri = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window

export type Res<T> = { ok: boolean; data: T; demo: boolean; error?: string; code?: string }
type Opt = { timeout?: number; quiet?: boolean; what?: string }

async function call<T>(method: 'GET' | 'POST', path: string, body: unknown, demo: () => T, o: Opt = {}): Promise<Res<T>> {
  const st = useS.getState()
  if (st.source === 'demo') return { ok: true, data: demo(), demo: true }
  const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), o.timeout ?? 6000)
  try {
    const r = await fetch(ENGINE + path, {
      method, signal: ctl.signal,
      headers: { 'Content-Type': 'application/json', 'X-NSQ-Client': 'desktop-ui', ...(st.session?.token ? { Authorization: `Bearer ${st.session.token}` } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    const j = await r.json().catch(() => ({}))
    if (r.status === 401 && st.session && !path.startsWith('/account/')) { useS.setState({ session: null, locked: true }); notify('Session ended. Log in again.', 'warn') }
    if (!r.ok) {   // accepts FastAPI {detail: str | {code, msg}} and plain {error|message, code}
      const d = typeof j.detail === 'object' && j.detail ? j.detail : j
      const msg = typeof j.detail === 'string' ? j.detail : d.msg || d.message || d.error || `Engine answered ${r.status}`
      return { ok: false, data: j as T, demo: false, error: String(msg), code: d.code || j.code }
    }
    return { ok: true, data: j as T, demo: false }
  } catch {
    if (!o.quiet) notify(`Engine offline · ${o.what || 'this action'} uses demo behaviour`, 'warn')
    return { ok: true, data: demo(), demo: true }
  } finally { clearTimeout(t) }
}

/** Quick reachability check, no notice. */
export async function probe(ms = 1500): Promise<any | null> {
  const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), ms)
  try { const r = await fetch(ENGINE + '/health', { signal: ctl.signal }); return r.ok ? await r.json().catch(() => ({})) : null } catch { return null } finally { clearTimeout(t) }
}

// ---------------- account, licence, lock
export type CreateAccount = { name: string; email: string; password: string; licence_key: string; pin?: string; totp: boolean }
export type Created = { token?: string; recovery_code: string; totp_secret?: string; totp_uri?: string; totp_pending?: boolean }
const B32 = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
const demoRecovery = () => Array.from({ length: 6 }, (_, i) => Array.from({ length: 4 }, (_, k) => B32[(Math.imul(i * 4 + k + 11, 2654435761) >>> 27)]).join('')).join('-')
export const createAccount = (b: CreateAccount) => call<Created>('POST', '/account/create', b,
  () => ({ token: 'demo', recovery_code: demoRecovery(), ...(b.totp ? { totp_secret: 'JBSWY3DPEHPK3PXP', totp_uri: 'otpauth://totp/NSKO%20QUANT:demo?secret=JBSWY3DPEHPK3PXP&issuer=NSKO%20QUANT' } : {}) }), { what: 'account creation' })

export type Login = { token?: string; need?: 'pin' | 'totp'; name?: string; email?: string; pin?: boolean; totp?: boolean }
export const login = (b: { email?: string; password: string; pin?: string; totp?: string }) => call<Login>('POST', '/account/login', b,
  () => ({ token: 'demo', name: 'Demo user' }), { what: 'login' })

export type Licence = { valid: boolean; plan?: string; expires?: string; message?: string }
export const licenceCheck = (key: string) => call<Licence>('GET', `/licence/check?key=${encodeURIComponent(key)}`, undefined,
  () => /^NSQ(-[A-Z0-9]{4}){3}$/i.test(key.trim()) || key.trim().toUpperCase() === 'DEMO'
    ? { valid: true, plan: 'Founder · demo', expires: '2027-11-26', message: 'Demo licence (not checked against the engine)' }
    : { valid: false, message: 'Format is NSQ-XXXX-XXXX-XXXX' }, { what: 'licence check' })

export const totpBegin = () => call<{ secret: string; uri?: string }>('POST', '/account/totp/begin', {}, () => ({ secret: 'JBSWY3DPEHPK3PXP' }), { what: '2FA set-up' })
export const totpConfirm = (code: string) => call<{ ok: boolean }>('POST', '/account/totp/confirm', { code }, () => ({ ok: true }), { what: '2FA set-up' })

// ---------------- trading controls
export const kill = () => call<{ ok: boolean }>('POST', '/kill', { confirm: true, source: 'desk' }, () => ({ ok: true }), { what: 'kill switch' })
export const releaseKill = () => call<{ ok: boolean }>('POST', '/kill', { action: 'release' }, () => ({ ok: true }), { what: 're-enable trading' })
export const approveTrade = (plan_id: string) => call<{ ok: boolean; order_id?: string }>('POST', '/trade/approve', { plan_id }, () => ({ ok: true, order_id: 'DEMO-' + plan_id }), { what: 'trade approval' })
export const health = () => call<any>('GET', '/health', undefined, () => useS.getState().health, { quiet: true })

// ---------------- settings, desk backup
export type Settings = Record<string, any>
export const DEMO_SETTINGS: Settings = {
  risk_per_trade_pct: 1, daily_loss_limit_pct: 3, weekly_loss_limit_pct: 6, max_trades_per_day: 5, max_open_positions: 2,
  news_blackout_min: 15, paper_days: 21, paper_trades: 30, live_start_size_pct: 50, bar_sharpe_oos: 1.4,
  trading_mode: 'auto', strategy_updates: 'ask', alerts_ntfy: true, alerts_telegram: true, alerts_desktop: true, trading_paused: false,
}
export const getSettings = () => call<Settings>('GET', '/settings', undefined, () => ({ ...DEMO_SETTINGS }), { what: 'settings', quiet: true })
export const saveSettings = (s: Settings) => call<Settings>('POST', '/settings', s, () => s, { what: 'saving settings' })
export const exportDesk = (passphrase: string) => call<{ filename: string; data_b64: string }>('POST', '/desk/export', { passphrase },
  () => ({ filename: 'nsko-quant-desk-DEMO.nsqdesk', data_b64: btoa('NSKO QUANT demo desk export · no real data') }), { what: 'desk export' })
export const restoreDesk = (data_b64: string, passphrase: string) => call<{ ok: boolean; restored?: string[] }>('POST', '/desk/restore', { data_b64, passphrase },
  () => ({ ok: true, restored: ['settings', 'strategies', 'journal'] }), { what: 'desk restore' })

// ---------------- brokers
export type Broker = { id: string; name: string; markets: string; status: 'connected' | 'demo' | 'not_connected' | 'error'; latency_ms?: number; withdrawals_off?: boolean; key_stored?: boolean; withdraw_url?: string }
export const DEMO_BROKERS: Broker[] = [
  { id: 'capital', name: 'Capital.com', markets: 'Gold, indices, FX, crypto CFDs · UK spread betting', status: 'demo', latency_ms: 84, withdrawals_off: true },
  { id: 'ig', name: 'IG', markets: 'Gold, indices, FX · UK spread betting', status: 'not_connected' },
  { id: 'oanda', name: 'OANDA', markets: 'FX, gold, indices', status: 'not_connected' },
  { id: 'ibkr', name: 'Interactive Brokers', markets: 'Stocks, futures (COMEX gold), FX', status: 'not_connected' },
  { id: 'kraken', name: 'Kraken', markets: 'Crypto · real trade volume', status: 'not_connected' },
  { id: 'coinbase', name: 'Coinbase Advanced', markets: 'Crypto', status: 'not_connected' },
  { id: 'alpaca', name: 'Alpaca', markets: 'US stocks, crypto · free paper account', status: 'not_connected' },
  { id: 'mt5', name: 'MetaTrader 5 bridge', markets: 'Many FX/gold brokers · Windows engine only', status: 'not_connected' },
]
export const brokers = () => call<Broker[]>('GET', '/brokers', undefined, () => DEMO_BROKERS, { what: 'broker list', quiet: true })
export type ConnectBody = { environment: 'demo' | 'live'; keychain_service?: string; keychain_account?: string; api_key?: string; api_secret?: string; account_id?: string }
export const connectBroker = (id: string, b: ConnectBody) => call<{ ok: boolean; status?: string; trading?: boolean; withdrawals_off?: boolean; message?: string }>('POST', `/brokers/${encodeURIComponent(id)}/connect`, b,
  () => ({ ok: true, status: 'demo', trading: true, withdrawals_off: true, message: 'Demo: nothing was sent to a broker.' }), { what: 'broker connection' })

// ---------------- money: withdraw helper (section 9.7)
export type Withdraw = { broker: string; currency: string; equity: number; margin_used: number; open_positions: { market: string; side: string; qty: number; pnl: number }[]; free: number; withdraw_url: string; trading_paused: boolean }
export const DEMO_WITHDRAW: Withdraw = { broker: 'Capital.com (demo)', currency: 'GBP', equity: 10164.2, margin_used: 1324.6, free: 8839.6, trading_paused: false,
  open_positions: [{ market: 'XAU/USD', side: 'BUY', qty: .1, pnl: 64.2 }], withdraw_url: 'https://capital.com/' }
export const withdrawHelper = () => call<Withdraw>('GET', '/withdraw/helper', undefined, () => ({ ...DEMO_WITHDRAW }), { what: 'withdraw helper' })
export const withdrawAction = (action: 'pause' | 'close_positions' | 'rescale' | 'resume') => call<Partial<Withdraw> & { ok?: boolean; new_equity?: number; message?: string }>('POST', '/withdraw/helper', { action },
  () => action === 'close_positions' ? { ok: true, open_positions: [], margin_used: 0, free: DEMO_WITHDRAW.equity } : action === 'pause' ? { ok: true, trading_paused: true } : action === 'resume' ? { ok: true, trading_paused: false } : { ok: true, message: 'Sizes rescaled to the new balance (demo).' },
  { what: 'withdraw step' })

// ---------------- paper & live
export type Checklist = { items: { id: string; label: string; ok: boolean; detail?: string }[]; paper: { r: number; trades: number; win: number; days: number }; live_unlocked: boolean; phrase: string }
export const checklist = () => call<Checklist>('GET', '/paperlive/checklist', undefined, () => ({
  phrase: 'I understand I can lose money', live_unlocked: false, paper: { r: 6.4, trades: 14, win: 57, days: 9 },
  items: [
    { id: 'paper_period', label: 'Paper period met (21 days and 30 trades): day 9, 14 trades', ok: false },
    { id: 'in_range', label: "Paper results inside the Lab's expected range", ok: true },
    { id: 'broker', label: 'Broker connected with a trade-only key', ok: true },
    { id: 'withdrawals_off', label: 'Withdrawals OFF on the key', ok: true },
    { id: 'risk', label: 'Risk limits confirmed', ok: true },
  ] }), { what: 'live checklist', quiet: true })
export const goLive = (phrase: string) => call<{ ok: boolean; message?: string }>('POST', '/settings', { mode: 'live', confirm_phrase: phrase }, () => ({ ok: false, message: 'Demo: live trading is never enabled in demo mode.' }), { what: 'go live' })

// ---------------- strategy book
export type Version = { version: number; created: string; note: string; sharpe_oos: number; by: string; active: boolean; stage: string }
export type Strategy = { id: string; name: string; tf: string; status: 'Thought up' | 'Approved' | 'On paper' | 'In review' | 'Failed' | 'Live'; stage: string; sharpe_oos: number; version: number; versions: Version[] }
const DS: [string, string, Strategy['status'], string, number][] = [
  ['Trend-follower XAU', '4h', 'Approved', 'waiting on you', 1.64], ['OF-1 Sweep XAU', '15m→3m', 'On paper', 'on paper · day 9', 1.52], ['VWAP-Rev BTC', '5m', 'Approved', 'approved', 2.10],
  ['ORB NVDA', '5m', 'In review', 'in review', 1.12], ['Carry XAU', '1d', 'Approved', 'approved', 1.47], ['Breakout ETH', '1h', 'Failed', 'failed · coin flip', .21],
  ['Range-XAU 16', '4h', 'Thought up', 'thought up', 0], ['Momentum BTC', '4h', 'On paper', 'on paper · day 4', 1.58],
]
const NOTES = ['First recipe from SCOUT\'s sources', 'Wider stop: 1.0 → 1.2 ATR', 'London + NY sessions only', 'News blackout ±15 → ±20 min', 'Target 1.6R → 1.8R']
export const DEMO_STRATEGIES: Strategy[] = DS.map(([name, tf, status, stage, sh], i) => {
  const n = 1 + (i * 3) % 4
  const versions = Array.from({ length: n }, (_, k) => ({ version: k + 1, created: new Date(Date.UTC(2026, 9, 2 + i * 3 + k * 6, 9 + k, 14)).toISOString(), note: k === 0 ? NOTES[0] : NOTES[1 + (k + i) % (NOTES.length - 1)],
    sharpe_oos: +(sh - (n - 1 - k) * .07 + (k % 2 ? .03 : 0)).toFixed(2), by: k === 0 ? 'RECIPE-MAKER' : k % 2 ? 'LAB' : 'You', active: k === n - 1, stage: k === n - 1 ? stage : 'retired' })).reverse()
  return { id: name.toLowerCase().replace(/[^a-z0-9]+/g, '-'), name, tf, status, stage, sharpe_oos: sh, version: n, versions }
})
export const strategies = () => call<Strategy[]>('GET', '/strategies', undefined, () => DEMO_STRATEGIES, { what: 'strategy book', quiet: true })
export const promote = (id: string, to: 'paper' | 'live') => call<{ ok: boolean; status?: string; message?: string }>('POST', `/strategies/${encodeURIComponent(id)}/promote`, { to },
  () => ({ ok: true, status: to === 'paper' ? 'On paper' : 'Live', message: `Demo: moved to ${to}.` }), { what: 'promote' })
export const rollback = (id: string, version: number) => call<{ ok: boolean; version?: number; message?: string }>('POST', `/strategies/${encodeURIComponent(id)}/rollback`, { version },
  () => ({ ok: true, version, message: `Demo: v${version} is active again.` }), { what: 'rollback' })

// ---------------- desktop shell helpers (Tauri only; safe no-ops in a browser)
export async function keychainSet(account: string, secret: string) {
  if (!isTauri) return false
  const { invoke } = await import('@tauri-apps/api/core'); await invoke('keychain_set', { account, secret }); return true
}
export async function openExternal(url: string) {
  if (isTauri) { const { openUrl } = await import('@tauri-apps/plugin-opener'); return openUrl(url) }
  window.open(url, '_blank', 'noopener')
}
