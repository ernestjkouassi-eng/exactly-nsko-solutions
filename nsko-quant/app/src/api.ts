// REST helpers for the local engine (127.0.0.1:8787).
// Every call degrades gracefully: in demo mode it returns demo data straight away; in engine mode, if the
// engine does not answer, it returns the same demo data with demo=true and shows a notice. Engine errors
// (4xx/5xx) are returned as ok=false with the engine's message, never silently replaced by demo data.
// The engine's own shapes (engine/nsq/app.py) are mapped to the desk's shapes HERE, in one place, so the pages
// stay the same for demo and engine.
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
      headers: { 'Content-Type': 'application/json', 'X-NSQ-Client': 'desktop-ui', ...(st.session?.token && st.session.token !== 'demo' ? { Authorization: `Bearer ${st.session.token}` } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    const j = await r.json().catch(() => ({}))
    if (r.status === 401 && st.session && !path.startsWith('/account/')) { useS.setState({ session: null, locked: true }); notify('Session ended. Log in again.', 'warn') }
    if (!r.ok) {   // accepts FastAPI {detail: str | {code, message} | [{msg}]} and plain {error|message, code}
      const d = typeof j.detail === 'object' && j.detail && !Array.isArray(j.detail) ? j.detail : j
      const msg = typeof j.detail === 'string' ? j.detail : Array.isArray(j.detail) ? j.detail.map((x: any) => x.msg).join('; ') : d.msg || d.message || d.error || `Engine answered ${r.status}`
      return { ok: false, data: j as T, demo: false, error: String(msg), code: d.code || j.code }
    }
    return { ok: true, data: j as T, demo: false }
  } catch {
    if (!o.quiet) notify(`Engine offline · ${o.what || 'this action'} uses demo behaviour`, 'warn')
    return { ok: true, data: demo(), demo: true }
  } finally { clearTimeout(t) }
}
/** Same as call(), then maps a real engine answer into the desk's shape (demo answers are already in it). */
async function mapped<T>(method: 'GET' | 'POST', path: string, body: unknown, demo: () => T, map: (j: any) => T, o: Opt = {}): Promise<Res<T>> {
  const r = await call<any>(method, path, body, demo, o)
  if (r.ok && !r.demo) { try { return { ...r, data: map(r.data) } } catch (e) { return { ok: false, data: r.data, demo: false, error: `Unexpected engine answer (${String(e)})` } } }
  return r as Res<T>
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

export type Licence = { valid: boolean; plan?: string; expires?: string; message?: string; status?: string }
const demoLicence = (key: string): Licence => /^NSQ(-[A-Z0-9]{4}){3}$/i.test(key.trim()) || key.trim().toUpperCase() === 'DEMO'
  ? { valid: true, plan: 'Founder · demo', expires: '2027-11-26', message: 'Demo licence (not checked against the engine)' }
  : { valid: false, message: 'Demo format is NSQ-XXXX-XXXX-XXXX (a real key starts NSQ1.)' }
// engine: {status: valid|invalid|expired, reason, licence: {tier, expiry, name}, days_left}
export const licenceCheck = (key: string) => mapped<Licence>('GET', `/licence/check?key=${encodeURIComponent(key.trim())}`, undefined, () => demoLicence(key),
  j => ({ valid: j.status === 'valid', status: j.status, plan: j.licence?.tier, expires: j.licence?.expiry, message: j.reason }), { what: 'licence check' })

export const totpBegin = () => mapped<{ secret: string; uri?: string }>('POST', '/account/totp/begin', {}, () => ({ secret: 'JBSWY3DPEHPK3PXP' }),
  j => ({ secret: j.secret, uri: j.otpauth_uri || j.uri }), { what: '2FA set-up' })
export const totpConfirm = (code: string) => call<{ ok: boolean }>('POST', '/account/totp/confirm', { code }, () => ({ ok: true }), { what: '2FA set-up' })

// ---------------- trading controls
export const kill = () => call<{ ok?: boolean; locked?: boolean; cancelled?: number; closed?: number; errors?: string[] }>('POST', '/kill', { reason: 'kill switch (desk)', source: 'desk' }, () => ({ ok: true }), { what: 'kill switch' })
export const releaseKill = () => call<{ locked: boolean }>('POST', '/trading/enable', {}, () => ({ locked: false }), { what: 're-enable trading' })
export const pauseTrading = (paused: boolean) => call<{ trading_paused: boolean }>('POST', '/trading/pause', { paused }, () => ({ trading_paused: paused }), { what: paused ? 'pause' : 'resume' })
export const approveTrade = (plan_id: string, decision: 'approve' | 'skip' = 'approve') => call<{ ok: boolean; order_id?: string }>('POST', '/trade/approve', { plan_id, decision }, () => ({ ok: true, order_id: 'DEMO-' + plan_id }), { what: 'trade approval' })
export const health = () => call<any>('GET', '/health', undefined, () => useS.getState().health, { quiet: true })

// ---------------- settings, desk backup
export type Settings = Record<string, any>
export const DEMO_SETTINGS: Settings = {
  risk_per_trade_pct: 1, daily_loss_limit_pct: 3, weekly_loss_limit_pct: 6, max_trades_per_day: 5, max_open_positions: 2,
  news_blackout_min: 15, paper_days: 21, paper_trades: 30, live_start_size_pct: 50, bar_sharpe_oos: 1.4,
  trading_mode: 'auto', strategy_updates: 'ask', alerts_ntfy: true, alerts_telegram: true, alerts_desktop: true, trading_paused: false,
  ntfy_url: 'https://ntfy.sh', ntfy_topic: '', telegram_chat_id: '', godseye_risk_actions: 'suggest',
}
// desk key -> engine setting key (engine/nsq/settings.py DEFAULTS; the bar lives in the Lab's lab.bar.* settings)
export const SETTING_KEYS: Record<string, string> = {
  risk_per_trade_pct: 'risk.per_trade_pct', daily_loss_limit_pct: 'risk.daily_loss_pct', weekly_loss_limit_pct: 'risk.weekly_loss_pct',
  max_trades_per_day: 'risk.max_trades_per_day', max_open_positions: 'risk.max_open_positions', news_blackout_min: 'news.blackout_min',
  paper_days: 'live.paper_days_required', paper_trades: 'live.paper_trades_required', live_start_size_pct: 'live.start_size_pct',
  bar_sharpe_oos: 'lab.bar.oos_sharpe', trading_mode: 'trade_mode', strategy_updates: 'updates.mode',
  alerts_ntfy: 'notify.ntfy_enabled', alerts_telegram: 'notify.telegram_enabled', alerts_desktop: 'ui.alerts_desktop', trading_paused: 'trading.paused',
  ntfy_url: 'notify.ntfy_url', ntfy_topic: 'notify.ntfy_topic', telegram_chat_id: 'notify.telegram_chat_id', godseye_risk_actions: 'godseye.risk_actions',
}
const fromEngineSettings = (j: Record<string, any>): Settings => Object.fromEntries(Object.entries(SETTING_KEYS).map(([k, e]) => [k, j[e] ?? DEMO_SETTINGS[k]]))
export const getSettings = () => mapped<Settings>('GET', '/settings', undefined, () => ({ ...DEMO_SETTINGS }), fromEngineSettings, { what: 'settings', quiet: true })
export const saveSettings = (s: Settings) => {
  const values = Object.fromEntries(Object.entries(s).filter(([k, v]) => SETTING_KEYS[k] && k !== 'trading_paused' && k !== 'telegram_chat_id' && v !== undefined && (v !== '' || k === 'ntfy_topic')).map(([k, v]) => [SETTING_KEYS[k], v]))
  return mapped<Settings>('POST', '/settings', { values }, () => s, () => s, { what: 'saving settings' })
}
export const exportDesk = (passphrase: string) => call<{ filename: string; data_b64: string }>('POST', '/backup/export', { passphrase, format: 'json' },
  () => ({ filename: 'nsko-quant-desk-DEMO.nsko', data_b64: btoa('NSKO QUANT demo desk export · no real data') }), { what: 'desk export', timeout: 30000 })
export const restoreDesk = (data_b64: string, passphrase: string) => mapped<{ ok: boolean; restored?: string[] }>('POST', '/backup/restore', { data_b64, passphrase },
  () => ({ ok: true, restored: ['settings', 'strategies', 'journal'] }), j => ({ ok: !!j.ok, restored: Array.isArray(j.restored) ? j.restored : Object.keys(j.restored || {}) }), { what: 'desk restore', timeout: 30000 })

// ---------------- brokers
export type Broker = { id: string; name: string; markets: string; status: 'connected' | 'demo' | 'not_connected' | 'error' | 'coming_soon' | 'unsupported'; latency_ms?: number; withdrawals_off?: boolean; key_stored?: boolean; withdraw_url?: string; reason?: string }
const SOON = "its official API docs could not be checked from the build machine, so it is not shipped until the endpoints are verified."
// Same list and statuses as the engine's catalogue (engine/nsq/brokers/__init__.py): paper is the connected default.
export const DEMO_BROKERS: Broker[] = [
  { id: 'paper', name: 'Paper', markets: 'Simulator · every market · GBP account', status: 'connected', withdrawals_off: true, latency_ms: 1 },
  { id: 'alpaca', name: 'Alpaca', markets: 'US stocks, crypto · free paper account', status: 'not_connected' },
  { id: 'kraken', name: 'Kraken', markets: 'Crypto · real trade volume · gold as PAXG', status: 'not_connected' },
  { id: 'coinbase', name: 'Coinbase Advanced', markets: 'Crypto', status: 'not_connected' },
  { id: 'ibkr', name: 'Interactive Brokers', markets: 'Stocks, futures (COMEX gold), FX · needs IB Gateway', status: 'not_connected' },
  { id: 'capital', name: 'Capital.com', markets: 'Gold, indices, FX, crypto CFDs · UK spread betting', status: 'coming_soon', reason: `open-api.capital.com: ${SOON}` },
  { id: 'ig', name: 'IG', markets: 'Gold, indices, FX · UK spread betting', status: 'coming_soon', reason: `labs.ig.com: ${SOON}` },
  { id: 'oanda', name: 'OANDA', markets: 'FX, gold, indices', status: 'coming_soon', reason: `developer.oanda.com: ${SOON}` },
  { id: 'mt5', name: 'MetaTrader 5', markets: 'Many FX/gold brokers · Windows only', status: 'coming_soon', reason: 'The MetaTrader5 Python package is Windows-only (no Linux wheel), so it could not be installed or checked. It also needs the MT5 terminal running on Windows.' },
]
const MARKET_TEXT: Record<string, string> = { paper: 'Simulator · every market · GBP account', alpaca: 'US stocks, crypto · free paper account', kraken: 'Crypto · real trade volume · gold as PAXG',
  coinbase: 'Crypto', ibkr: 'Stocks, futures (COMEX gold), FX · needs IB Gateway', capital: 'Gold, indices, FX, crypto CFDs · UK spread betting', ig: 'Gold, indices, FX · UK spread betting',
  oanda: 'FX, gold, indices', mt5: 'Many FX/gold brokers · Windows only', cmc: 'No bot API for retail' }
// engine: {active, brokers: [{name, title, status: ready|coming_soon|unsupported, reason, markets: [], withdraw_page, key_stored}]}
export const brokers = () => mapped<Broker[]>('GET', '/brokers', undefined, () => DEMO_BROKERS, j => (j.brokers || []).map((b: any): Broker => ({
  id: b.name, name: b.title || b.name, markets: MARKET_TEXT[b.name] || (b.markets || []).join(', '), reason: b.reason, key_stored: !!b.key_stored, withdraw_url: b.withdraw_page || undefined,
  status: b.name === j.active ? 'connected' : b.status === 'ready' ? 'not_connected' : b.status === 'coming_soon' ? 'coming_soon' : b.status === 'unsupported' ? 'unsupported' : 'error',
  withdrawals_off: b.name === j.active ? true : undefined })), { what: 'broker list', quiet: true })
export type ConnectBody = { environment: 'demo' | 'live'; keychain_service?: string; keychain_account?: string; api_key?: string; api_secret?: string; account_id?: string }
type Connected = { ok: boolean; status?: string; trading?: boolean; withdrawals_off?: boolean; message?: string }
export const connectBroker = (id: string, b: ConnectBody) => mapped<Connected>('POST', `/brokers/${encodeURIComponent(id)}/connect`, b,
  () => ({ ok: true, status: 'demo', trading: true, withdrawals_off: true, message: 'Demo: nothing was sent to a broker.' }),
  j => ({ ok: !!j.ok, status: 'connected', trading: j.permissions?.trading === true, withdrawals_off: j.permissions?.withdrawals === false,
    message: `Connected to ${j.broker} · trading ${j.permissions?.trading ? 'ON' : 'not confirmed'} · withdrawals ${j.permissions?.withdrawals === false ? 'OFF ✓' : j.permissions?.withdrawals == null ? 'cannot be checked: make sure the key has no withdraw permission' : 'ON (refused)'}` }),
  { what: 'broker connection', timeout: 20000 })

// ---------------- alerts set-up: ntfy, Telegram (the bot token goes into the engine's vault / OS keychain, never into settings)
export const vaultNames = () => call<{ backend: string; names: string[] }>('GET', '/vault', undefined, () => ({ backend: 'demo', names: [] }), { quiet: true })
export const saveSecret = (name: string, value: string) => call<{ ok: boolean; stored_in?: string }>('POST', `/vault/${encodeURIComponent(name)}`, { value }, () => ({ ok: true, stored_in: 'nowhere (demo)' }), { what: 'saving the token' })
export const telegramPairBegin = () => call<{ code: string; how: string; expires_in_s: number }>('POST', '/telegram/pair/begin', {}, () => ({ code: '482913', how: 'Demo: send /pair 482913 to your bot in Telegram.', expires_in_s: 600 }), { what: 'Telegram pairing' })
export const notifyTest = () => call<{ delivered: string | null; ntfy_topic_set: boolean; telegram_paired: boolean; telegram_token_set: boolean }>('POST', '/notify/test', {},
  () => ({ delivered: "{'ntfy': 'demo', 'telegram': 'demo'}", ntfy_topic_set: false, telegram_paired: false, telegram_token_set: false }), { what: 'test alert', timeout: 20000 })

// ---------------- money: withdraw helper (section 9.7)
export type Withdraw = { broker: string; currency: string; equity: number; margin_used: number; open_positions: { market: string; side: string; qty: number; pnl: number }[]; free: number; withdraw_url: string; trading_paused: boolean; note?: string; paper?: boolean }
export const DEMO_WITHDRAW: Withdraw = { broker: 'Capital.com (demo)', currency: 'GBP', equity: 10164.2, margin_used: 1324.6, free: 8839.6, trading_paused: false,
  open_positions: [{ market: 'XAU/USD', side: 'BUY', qty: .1, pnl: 64.2 }], withdraw_url: 'https://capital.com/' }
const BROKER_TITLE: Record<string, string> = { paper: 'Paper simulator', alpaca: 'Alpaca', kraken: 'Kraken', coinbase: 'Coinbase Advanced', ibkr: 'Interactive Brokers' }
// engine: {broker, currency, equity, margin_used, free_to_withdraw, open_positions (count), positions: [...], trading_paused, withdraw_url, paper, note}
const fromEngineWithdraw = (j: any): Withdraw => ({ broker: BROKER_TITLE[j.broker] || j.broker, currency: j.currency || 'GBP', equity: +j.equity || 0, margin_used: +j.margin_used || 0,
  free: +(j.free_to_withdraw ?? j.free ?? 0), withdraw_url: j.withdraw_url || '', trading_paused: !!j.trading_paused, note: j.note, paper: !!j.paper,
  open_positions: (j.positions || []).map((p: any) => ({ market: p.market, side: String(p.side).toUpperCase(), qty: p.qty, pnl: +p.pnl || 0 })) })
export const withdrawHelper = () => mapped<Withdraw>('GET', '/withdraw/helper', undefined, () => ({ ...DEMO_WITHDRAW }), fromEngineWithdraw, { what: 'withdraw helper' })
type WStep = Partial<Withdraw> & { ok?: boolean; new_equity?: number; message?: string }
export const withdrawAction = (action: 'pause' | 'close_positions' | 'rescale' | 'resume') => mapped<WStep>('POST', '/withdraw/helper', { action },
  () => action === 'close_positions' ? { ok: true, open_positions: [], margin_used: 0, free: DEMO_WITHDRAW.equity } : action === 'pause' ? { ok: true, trading_paused: true } : action === 'resume' ? { ok: true, trading_paused: false } : { ok: true, message: 'Sizes rescaled to the new balance (demo).' },
  j => ({ ok: !!j.ok, new_equity: j.new_equity, message: j.message, ...(j.positions ? fromEngineWithdraw(j) : {}), ...(typeof j.trading_paused === 'boolean' ? { trading_paused: j.trading_paused } : {}) }),
  { what: 'withdraw step', timeout: 20000 })

// ---------------- paper & live
export type Checklist = { items: { id: string; label: string; ok: boolean; detail?: string }[]; paper: { r: number; trades: number; win: number; days: number }; live_unlocked: boolean; phrase: string; start_size_pct?: number }
// engine: {ok, items: [{id, ok, label, value}], phrase, paper: {trades, days, r, win}, unlocked, start_size_pct}
const fromEngineChecklist = (j: any): Checklist => ({ phrase: j.phrase || 'I understand I can lose money', live_unlocked: !!j.unlocked, start_size_pct: j.start_size_pct,
  paper: { r: +j.paper?.r || 0, trades: +j.paper?.trades || 0, win: +j.paper?.win || 0, days: +j.paper?.days || 0 },
  items: (j.items || []).filter((i: any) => i.id !== 'phrase').map((i: any) => ({ id: i.id, ok: !!i.ok, label: i.id === 'paper_days' || i.id === 'paper_trades' ? `${i.label}: ${i.value ?? 0} so far` : i.label, detail: i.value == null ? undefined : String(i.value) })) })
export const checklist = () => mapped<Checklist>('GET', '/live/checklist', undefined, () => ({
  phrase: 'I understand I can lose money', live_unlocked: false, paper: { r: 6.4, trades: 14, win: 57, days: 9 },
  items: [
    { id: 'paper_period', label: 'Paper period met (21 days and 30 trades): day 9, 14 trades', ok: false },
    { id: 'in_range', label: "Paper results inside the Lab's expected range", ok: true },
    { id: 'broker', label: 'Broker connected with a trade-only key', ok: true },
    { id: 'withdrawals_off', label: 'Withdrawals OFF on the key', ok: true },
    { id: 'risk', label: 'Risk limits confirmed', ok: true },
  ] }), fromEngineChecklist, { what: 'live checklist', quiet: true })
export const goLive = (phrase: string) => mapped<{ ok: boolean; message?: string }>('POST', '/live/unlock', { phrase },
  () => ({ ok: false, message: 'Demo: live trading is never enabled in demo mode.' }),
  j => j.unlocked ? { ok: true } : { ok: false, message: 'Live stays locked. Still missing: ' + (j.items || []).filter((i: any) => !i.ok).map((i: any) => i.label).join(' · ') }, { what: 'go live' })

// ---------------- strategy book
export type Version = { version: number; created: string; note: string; sharpe_oos: number; by: string; active: boolean; stage: string }
export type Strategy = { id: string; name: string; tf: string; status: 'Thought up' | 'Approved' | 'On paper' | 'In review' | 'Failed' | 'Live' | 'Retired'; stage: string; sharpe_oos: number; version: number; versions: Version[]; market?: string }
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
const ST_STATUS: Record<string, Strategy['status']> = { lab: 'In review', paper: 'On paper', live: 'Live', retired: 'Retired' }
const BY: Record<string, string> = { lab: 'LAB', manual: 'You', auto: 'LAB · auto', dev: 'DEV', seed: 'SEED PACK', research: 'RECIPE-MAKER' }
const sharpeOf = (m: any) => +(m?.sharpeOOS ?? m?.oos?.sharpe ?? m?.sharpe_oos ?? 0) || 0
// engine (?include=versions): [{id, name, market, timeframe, status: lab|paper|live|retired, paper_version, live_version, active_version, versions: [{version, note, source, metrics, created_at}]}]
const fromEngineStrategy = (s: any): Strategy => {
  const status = ST_STATUS[s.status] || 'In review', av = s.active_version
  const stage = s.status === 'paper' ? `on paper · v${av}` : s.status === 'live' ? `live · v${av}` : s.status === 'lab' ? 'in the Lab · not approved' : s.status
  const versions: Version[] = [...(s.versions || [])].reverse().map((v: any) => ({ version: v.version, created: new Date((v.created_at || 0) * 1000).toISOString(), note: v.note || '—',
    sharpe_oos: sharpeOf(v.metrics), by: BY[String(v.source).split(':')[0]] || String(v.source || '').toUpperCase(), active: v.version === av, stage: v.version === av ? stage : 'kept' }))
  return { id: s.id, name: s.name, tf: s.timeframe, market: s.market, status, stage, version: av || 0, sharpe_oos: versions.find(v => v.active)?.sharpe_oos || 0, versions }
}
export const strategies = () => mapped<Strategy[]>('GET', '/strategies?include=versions', undefined, () => DEMO_STRATEGIES, j => (j.strategies || []).map(fromEngineStrategy), { what: 'strategy book', quiet: true })
export const promote = (id: string, to: 'paper' | 'live') => mapped<{ ok: boolean; status?: string; message?: string }>('POST', `/strategies/${encodeURIComponent(id)}/promote`, { to },
  () => ({ ok: true, status: to === 'paper' ? 'On paper' : 'Live', message: `Demo: moved to ${to}.` }),
  j => ({ ok: true, status: j.status, message: j.queued ? `v${j.version} queued: it goes ${to} when the open trade closes (live never changes mid-trade).` : `v${j.version} is now on ${to}.` }), { what: 'promote' })
export const rollback = (id: string, version: number) => mapped<{ ok: boolean; version?: number; message?: string }>('POST', `/strategies/${encodeURIComponent(id)}/rollback`, { version },
  () => ({ ok: true, version, message: `Demo: v${version} is active again.` }),
  j => ({ ok: true, version: j.to, message: j.queued ? `Rollback to v${j.to} queued until the open trade closes.` : `v${j.to} is active again (was v${j.from}).` }), { what: 'rollback' })

// ---------------- data, Lab and research (engine only; demo pages draw their own)
export type Candle = { time: number; open: number; high: number; low: number; close: number }
export const candles = (market: string, tf = '1m', bars = 160) => call<{ attrs: any; candles: Candle[] }>('GET', `/data/candles?market=${encodeURIComponent(market)}&tf=${tf}&bars=${bars}`, undefined, () => ({ attrs: { demo: true }, candles: [] }), { quiet: true, timeout: 15000 })
export type Profile = { poc: number | null; vah: number | null; val: number | null; bins: { price: number; vol: number }[]; volume_kind?: string; label?: string; synthetic?: boolean }
export const profile = (market: string, tf = '1m', bars = 120) => call<Profile>('GET', `/data/profile?market=${encodeURIComponent(market)}&tf=${tf}&bars=${bars}`, undefined, () => ({ poc: null, vah: null, val: null, bins: [] }), { quiet: true, timeout: 15000 })
export const labFan = (recipe_id: string) => call<{ lines: { id: number; label: string; outcome: string; equity: number[] }[] }>('GET', `/lab/fan?recipe_id=${encodeURIComponent(recipe_id)}`, undefined, () => ({ lines: [] }), { quiet: true })
export const labVariants = (limit = 200) => call<{ variants: any[] }>('GET', `/lab/variants?limit=${limit}`, undefined, () => ({ variants: [] }), { quiet: true })
export const research = (table: 'sources' | 'summaries' | 'terms', limit = 40) => call<Record<string, any[]>>('GET', `/research/${table}?limit=${limit}`, undefined, () => ({ [table]: [] }), { quiet: true })
export const accountSummary = () => call<{ account: any; positions: any[]; orders: any[]; paper: boolean }>('GET', '/account/summary', undefined, () => ({ account: null, positions: [], orders: [], paper: true }), { quiet: true })
export const journal = (n = 20) => call<{ trades: any[] }>('GET', `/journal?n=${n}`, undefined, () => ({ trades: [] }), { quiet: true })

// ---------------- JARVIS (engine: local model through Ollama when installed, an honest notice otherwise)
export const jarvisChat = (message: string, history: { me: boolean; t: string }[], demo: () => string) => mapped<{ reply: string; local_model: boolean }>('POST', '/jarvis/chat', { message, history },
  () => ({ reply: demo(), local_model: false }), j => ({ reply: String(j.reply || ''), local_model: !!j.local_model }), { what: 'JARVIS', timeout: 100000 })

// ---------------- desktop shell helpers (Tauri only; safe no-ops in a browser)
export async function keychainSet(account: string, secret: string) {
  if (!isTauri) return false
  const { invoke } = await import('@tauri-apps/api/core'); await invoke('keychain_set', { account, secret }); return true
}
export async function openExternal(url: string) {
  if (isTauri) { const { openUrl } = await import('@tauri-apps/plugin-opener'); return openUrl(url) }
  window.open(url, '_blank', 'noopener')
}
