import { create } from 'zustand'
import type { Ev } from './demo/sim'

export type Variant = { id: number; recipe: string; market: string; tf: string; sharpeIS: number; sharpeOOS: number; trades: number; win: number; rr: number; dd: number; outcome: 'clear' | 'sieve' | 'failed'; why: string | null; seed: number }
export type GeoPt = { layer: string; id: string; lat: number; lon: number; alt: number; label?: string; ts: number }
export type Impact = { id: string; title: string; asset: string; note: string; tone: string; lat?: number; lon?: number; ts: number }
export type Notice = { id: number; text: string; tone: 'info' | 'warn' | 'bad' | 'good'; action?: { label: string; run: () => void } }
export type Conn = 'off' | 'probing' | 'connecting' | 'online' | 'reconnecting' | 'offline'
export type Session = { token: string; name?: string; email?: string } | null

type S = {
  // data source
  source: 'demo' | 'engine'; conn: Conn; fallback: boolean; locked: boolean; session: Session; needAccount: boolean
  demo: boolean   // true whenever the numbers on screen come from the simulator (demo mode, or engine fallback)
  notices: Notice[]
  // desk state
  mode: 'PAPER' | 'LIVE'; auto: boolean; killed: boolean; paused: boolean
  round: number; health: any; budget: { used: number; of: number; days: number }
  log: { ts: number; verb: string; msg: string }[]
  variants: Variant[]; tested: number; sieve: number; clear: number; fails: Record<string, number>; lastFail: string | null
  prices: Record<string, number>; series: Record<string, { t: number; p: number }[]>
  bubbles: { t: number; price: number; size: number; side: string }[]
  sources: { kind: string; title: string; idea: string; ts: number }[]
  handoffs: { from: string; to: string; ts: number }[]
  decisions: { id: number; tag: string; title: string; desc: string; planId?: string }[]
  geo: Record<string, GeoPt>; geoV: number; impacts: Impact[]
  set: (p: Partial<S>) => void
}
const FAILS0 = { 'Win rate too low': 65, 'R:R too low': 18, 'Too few trades': 76, 'Expectancy negative after costs': 20, 'Max drawdown too deep': 219, "Doesn't work out-of-sample": 147 }
export const useS = create<S>((set) => ({
  source: 'demo', conn: 'off', fallback: false, locked: false, session: null, needAccount: false, demo: true, notices: [],
  mode: 'PAPER', auto: true, killed: false, paused: false, round: 12646, health: {}, budget: { used: 31, of: 50, days: 18 },
  log: [], variants: [], tested: 1251, sieve: 343, clear: 12, fails: { ...FAILS0 }, lastFail: null,
  prices: {}, series: {}, bubbles: [], sources: [], handoffs: [],
  decisions: [
    { id: 1, tag: 'TO PAPER', title: 'Trend-follower XAU · 4h', desc: 'Sharpe OOS 1.64 · 412 trades · max DD −11.2R. Cleared the bar after costs.' },
    { id: 2, tag: 'SKILL PROPOSAL', title: 'Check the news blackout earlier', desc: 'SCOUT suggests widening the CPI blackout from ±15 to ±20 min on gold.' },
  ],
  geo: {}, geoV: 0, impacts: [],
  set: (p) => set(p),
}))

// ---------- notices (toasts). Used for "engine offline, showing demo behaviour" and action results.
let nid = 0
export function notify(text: string, tone: Notice['tone'] = 'info', action?: Notice['action'], ms = 6000) {
  const st = useS.getState(); if (st.notices.some(n => n.text === text)) return
  const n = { id: ++nid, text, tone, action }; useS.setState({ notices: [...st.notices.slice(-3), n] })
  if (ms) setTimeout(() => dismiss(n.id), ms)
}
export const dismiss = (id: number) => useS.setState({ notices: useS.getState().notices.filter(n => n.id !== id) })

// Clear the simulator's numbers before real engine data arrives, so demo and real numbers never mix under the ENGINE chip.
export function resetForEngine() {
  pend = {}; geoPend = {}
  useS.setState({ log: [], variants: [], tested: 0, sieve: 0, clear: 0, fails: Object.fromEntries(Object.keys(FAILS0).map(k => [k, 0])), lastFail: null,
    prices: {}, series: {}, bubbles: [], sources: [], handoffs: [], decisions: [], geo: {}, geoV: 0, impacts: [], killed: false, demo: false })
}
export function resetForDemo() {
  useS.setState({ tested: 1251, sieve: 343, clear: 12, fails: { ...FAILS0 }, decisions: useS.getInitialState().decisions })
}

// ---------- the ONE event handler. Both the demo simulator and the engine WebSocket call handle(ev).
let pend: Record<string, { t: number; p: number }> = {}; let flushT: ReturnType<typeof setTimeout> | 0 = 0
let geoPend: Record<string, GeoPt> = {}; let geoT: ReturnType<typeof setTimeout> | 0 = 0
let decId = 100
export function handle(e: Ev) {
  const s = useS.getState(); if (s.killed && e.type === 'order_sent') return
  const p = e.payload || {}
  switch (e.type) {
    case 'engine_health': useS.setState({ round: p.round ?? s.round, health: p, ...(typeof p.paused === 'boolean' ? { paused: p.paused } : {}), ...(typeof p.killed === 'boolean' ? { killed: p.killed } : {}) }); break
    case 'budget_update': useS.setState({ budget: { ...s.budget, ...p } }); break
    case 'ticker_log': useS.setState({ log: [...s.log.slice(-79), { ts: e.ts, verb: p.verb, msg: p.msg }] }); break
    case 'tick': {   // coalesce: one store update per batch of ticks, not one per market
      pend[p.market] = { t: e.ts, p: p.price }
      if (!flushT) flushT = setTimeout(() => { flushT = 0; const st = useS.getState(); const prices = { ...st.prices }, series = { ...st.series }
        for (const [m, v] of Object.entries(pend)) { prices[m] = v.p; series[m] = [...(series[m] || []).slice(-1999), v] } pend = {}; useS.setState({ prices, series }) }, 250)
      break
    }
    case 'orderflow_bubble': useS.setState({ bubbles: [...s.bubbles.slice(-300), { t: e.ts, ...p }] }); break
    case 'source_added': useS.setState({ sources: [...s.sources.slice(-40), { ...p, ts: e.ts }] }); break
    case 'agent_handoff': useS.setState({ handoffs: [...s.handoffs.slice(-30), { from: p.from, to: p.to, ts: e.ts }] }); break
    case 'variant_tested': {
      const v = p as Variant; const fails = { ...s.fails }; if (v.why) fails[v.why] = (fails[v.why] || 0) + 1
      useS.setState({ variants: [...s.variants.slice(-599), v], tested: s.tested + 1, sieve: s.sieve + (v.outcome !== 'failed' ? 1 : 0), clear: s.clear + (v.outcome === 'clear' ? 1 : 0), fails, lastFail: v.why })
      break
    }
    case 'kill_switch': useS.setState({ killed: p.active ?? p.killed ?? true }); if (p.active ?? true) desktopAlert('Kill switch', 'Orders cancelled, positions closed, trading locked.'); break
    case 'decision_needed': useS.setState({ decisions: [...s.decisions, { id: p.id ?? ++decId, tag: (p.tag || 'DECISION').toUpperCase(), title: p.title || 'Decision needed', desc: p.desc || p.detail || '', planId: p.plan_id }] }); break
    case 'alert': notify(p.msg || p.title || 'Alert', p.level === 'high' ? 'bad' : 'info'); if (p.level === 'high' || p.desktop) desktopAlert(p.title || 'NSKO QUANT', p.msg || ''); break
    case 'order_filled': desktopAlert('Order filled', `${p.side?.toUpperCase?.() || ''} ${p.market || ''} ${p.qty ?? ''} @ ${p.price ?? ''}`.trim()); break
    case 'gods_eye_event': {
      const g: GeoPt = { layer: p.layer, id: String(p.id), lat: +p.lat, lon: +p.lon, alt: +(p.alt_m ?? 0), label: p.label, ts: p.ts ?? e.ts }
      geoPend[g.layer + ':' + g.id] = g
      if (!geoT) geoT = setTimeout(() => { geoT = 0; const st = useS.getState(); useS.setState({ geo: { ...st.geo, ...geoPend }, geoV: st.geoV + 1 }); geoPend = {} }, 400)
      break
    }
    case 'market_impact': useS.setState({ impacts: [{ ...p, id: p.id ?? String(e.ts), ts: e.ts }, ...s.impacts.filter(i => i.id !== p.id)].slice(0, 6) }); break
  }
}

// Desktop notification through the Tauri plugin (no-op in a plain browser).
export async function desktopAlert(title: string, body: string) {
  if (!('__TAURI_INTERNALS__' in window)) return
  try {
    const n = await import('@tauri-apps/plugin-notification')
    let ok = await n.isPermissionGranted(); if (!ok) ok = (await n.requestPermission()) === 'granted'
    if (ok) n.sendNotification({ title, body })
  } catch { /* notifications are best-effort */ }
}
