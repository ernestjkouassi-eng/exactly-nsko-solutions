import { create } from 'zustand'
import type { Ev } from './demo/sim'

export type Variant = { id: number; recipe: string; market: string; tf: string; sharpeIS: number; sharpeOOS: number; trades: number; win: number; rr: number; dd: number; outcome: 'clear' | 'sieve' | 'failed'; why: string | null; seed: number }
export type GeoPt = { layer: string; id: string; lat: number; lon: number; alt: number; label?: string; ts: number }
export type Impact = { id: string; title: string; asset: string; note: string; tone: string; lat?: number; lon?: number; ts: number }
export type Notice = { id: number; text: string; tone: 'info' | 'warn' | 'bad' | 'good'; action?: { label: string; run: () => void } }
export type Conn = 'off' | 'probing' | 'connecting' | 'online' | 'reconnecting' | 'offline'
export type Session = { token: string; name?: string; email?: string } | null
// One trade walking the nine steps, built from the engine's trade-flow events (engine mode Trade Card).
export type Trade = { planId: string; step: number; ts: number; market?: string; side?: string; strategy?: string; synthetic?: boolean
  scan?: any; news?: any; forecast?: any; entry?: any; tm?: any; tmProgress?: { done: number; of: number }; size?: any; risk?: any
  approval?: { timeout_s?: number; since: number }; order?: any; fill?: any; updates: any[]; exit?: any; skipped?: { step: string; why: string } }
export type LabLine = { id: number; label?: string; outcome: string; equity: number[] }

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
  bubbles: { t: number; price: number; size: number; side: string; market?: string }[]
  sources: { kind: string; title: string; idea: string; ts: number }[]
  handoffs: { from: string; to: string; ts: number }[]
  decisions: { id: number | string; tag: string; title: string; desc: string; planId?: string }[]
  geo: Record<string, GeoPt>; geoV: number; impacts: Impact[]
  // engine-fed views (empty in demo mode: the pages draw their own demo overlays there)
  trade: Trade | null; trades: Trade[]
  candles: Record<string, { time: number; open: number; high: number; low: number; close: number; synthetic?: boolean }[]>
  profiles: Record<string, any>; forecasts: Record<string, any>
  terms: { term: string; ts: number }[]; reading: { title: string; summary: string; idea: string; highlights: string[]; agent?: string; model?: string; ts: number } | null
  agents: Record<string, { status: string; item?: string; ts: number }>
  labLines: Record<number, LabLine>; labRunning: string | null; lastBacktest: any
  engineDemo: boolean   // the engine itself is running its scripted demo source (payloads flagged demo: true)
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
  trade: null, trades: [], candles: {}, profiles: {}, forecasts: {}, terms: [], reading: null, agents: {}, labLines: {}, labRunning: null, lastBacktest: null, engineDemo: false,
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
    prices: {}, series: {}, bubbles: [], sources: [], handoffs: [], decisions: [], geo: {}, geoV: 0, impacts: [], killed: false, demo: false,
    trade: null, trades: [], candles: {}, profiles: {}, forecasts: {}, terms: [], reading: null, agents: {}, labLines: {}, labRunning: null, lastBacktest: null, engineDemo: false,
    budget: { used: 0, of: 50, days: 0 } })
}
export function resetForDemo() {
  useS.setState({ tested: 1251, sieve: 343, clear: 12, fails: { ...FAILS0 }, decisions: useS.getInitialState().decisions })
}

// ---------- the ONE event handler. Both the demo simulator and the engine WebSocket call handle(ev).
let pend: Record<string, { t: number; p: number }> = {}; let flushT: ReturnType<typeof setTimeout> | 0 = 0
let geoPend: Record<string, GeoPt> = {}; let geoT: ReturnType<typeof setTimeout> | 0 = 0
let decId = 100
// Trade-flow events -> the Trade Card's nine steps (Scanner, News, Forecast, Entry, Time Machine, Size, Risk, Execute, Exit).
const FLOW_STEP: Record<string, number> = { scan_hit: 0, news_hit: 1, forecast_done: 2, entry_state: 3, timemachine_progress: 4, timemachine_done: 4, size_calc: 5, risk_check: 6, order_sent: 7, order_filled: 7, position_update: 8, exit_done: 8 }
function flowEvent(e: Ev) {
  const s = useS.getState(), p = e.payload || {}
  if (!p.plan_id) return
  let t: Trade | null = s.trade && s.trade.planId === p.plan_id ? { ...s.trade } : null
  if (!t) { if (e.type !== 'scan_hit') return; t = { planId: p.plan_id, step: 0, ts: e.ts, updates: [] } }
  t.ts = e.ts; t.step = Math.max(t.step, FLOW_STEP[e.type] ?? t.step)
  switch (e.type) {
    case 'scan_hit': Object.assign(t, { scan: p, market: p.market, side: p.side, strategy: p.strategy, synthetic: !!p.synthetic }); break
    case 'news_hit': t.news = p; break
    case 'forecast_done': t.forecast = p; break
    case 'entry_state': t.entry = { ...t.entry, ...p }; break
    case 'timemachine_progress': t.tmProgress = { done: p.done, of: p.of }; break
    case 'timemachine_done': t.tm = p; t.tmProgress = { done: p.replays, of: p.replays }; break
    case 'size_calc': t.size = p; break
    case 'risk_check': t.risk = p; break
    case 'order_sent': t.order = p; t.approval = undefined; break
    case 'order_filled': t.fill = p; break
    case 'position_update': if (p.event !== 'mark') t.updates = [...t.updates, p].slice(-10); break
    case 'exit_done': t.exit = p; break
  }
  const done = s.trade && s.trade.planId !== t.planId ? [s.trade, ...s.trades].slice(0, 10) : s.trades
  useS.setState({ trade: t, trades: done, ...(e.type === 'forecast_done' && p.fan && t.market ? { forecasts: { ...s.forecasts, [t.market]: { ...p, ts: e.ts } } } : {}) })
}

export function handle(e: Ev) {
  const s = useS.getState(); if (s.killed && e.type === 'order_sent') return
  const p = e.payload || {}
  if (s.source === 'engine' && p.demo === true && !s.engineDemo) useS.setState({ engineDemo: true, demo: true })   // honest: the engine is showing its demo feed
  if (s.source === 'engine' && e.type in FLOW_STEP) flowEvent(e)
  switch (e.type) {
    case 'engine_health': useS.setState({ round: p.round ?? s.round, health: p, ...(typeof p.paused === 'boolean' ? { paused: p.paused } : {}), ...(typeof p.killed === 'boolean' ? { killed: p.killed } : {}) }); break
    case 'budget_update': useS.setState({ budget: { ...s.budget, ...p } }); break
    case 'ticker_log': useS.setState({ log: [...s.log.slice(-79), { ts: e.ts, verb: p.verb, msg: p.msg }] })
      if (p.plan_id && s.trade && s.trade.planId === p.plan_id && p.step) useS.setState({ trade: { ...s.trade, skipped: { step: p.step, why: p.why || p.msg }, approval: undefined, ts: e.ts } })
      break
    case 'tick': {   // coalesce: one store update per batch of ticks, not one per market
      pend[p.market] = { t: e.ts, p: p.price }
      if (!flushT) flushT = setTimeout(() => { flushT = 0; const st = useS.getState(); const prices = { ...st.prices }, series = { ...st.series }
        for (const [m, v] of Object.entries(pend)) { prices[m] = v.p; series[m] = [...(series[m] || []).slice(-1999), v] } pend = {}; useS.setState({ prices, series }) }, 250)
      break
    }
    case 'orderflow_bubble': useS.setState({ bubbles: [...s.bubbles.slice(-300), { t: p.ts ?? e.ts, market: p.market, price: p.price, size: p.size, side: p.side }] }); break
    case 'candle': {   // a newly closed bar from the engine's data feed
      const k = `${p.market}|${p.tf}`, t = Math.floor(Date.parse(p.time) / 1000), arr = s.candles[k] || []
      if (arr.length && arr[arr.length - 1].time >= t) break
      useS.setState({ candles: { ...s.candles, [k]: [...arr.slice(-499), { time: t, open: p.open, high: p.high, low: p.low, close: p.close, synthetic: !!p.synthetic }] } }); break
    }
    case 'profile_update': useS.setState({ profiles: { ...s.profiles, [p.market]: { ...p, ts: e.ts } } }); break
    case 'source_added': useS.setState({ sources: [...s.sources.slice(-40), { ...p, ts: e.ts }] }); break
    case 'summary_done': useS.setState({ reading: { title: p.title, summary: p.summary, idea: p.idea, highlights: p.highlights || [], agent: p.agent, model: p.model, ts: e.ts } }); break
    case 'term_found': useS.setState({ terms: [...s.terms.filter(t => t.term !== p.term).slice(-40), { term: p.term, ts: e.ts }] }); break
    case 'agent_status': if (p.agent) useS.setState({ agents: { ...s.agents, [p.agent]: { status: p.status || p.state || 'working', item: p.item || p.plan_id, ts: e.ts } },
      ...(p.agent === 'LAB' ? { labRunning: (p.status || p.state) === 'working' ? (p.item || 'a recipe') : null } : {}) }); break
    case 'backtest_done': useS.setState({ lastBacktest: { ...p, ts: e.ts }, labRunning: null }); break
    case 'agent_handoff': useS.setState({ handoffs: [...s.handoffs.slice(-30), { from: p.from, to: p.to, ts: e.ts }] }); break
    case 'variant_tested': {
      const v = p as Variant; const fails = { ...s.fails }; if (v.why) fails[v.why] = (fails[v.why] || 0) + 1
      useS.setState({ variants: [...s.variants.slice(-599), v], tested: s.tested + 1, sieve: s.sieve + (v.outcome !== 'failed' ? 1 : 0), clear: s.clear + (v.outcome === 'clear' ? 1 : 0), fails, lastFail: v.why })
      break
    }
    case 'kill_switch': { const on = p.on ?? p.active ?? p.killed ?? true; useS.setState({ killed: on }); if (on) desktopAlert('Kill switch', 'Orders cancelled, positions closed, trading locked.'); break }
    case 'decision_needed': {
      const planId = p.plan_id ?? (String(p.tag).toUpperCase() === 'APPROVE TRADE' ? p.id : undefined)
      if (s.decisions.some(d => String(d.id) === String(p.id ?? ''))) break
      useS.setState({ decisions: [...s.decisions, { id: p.id ?? ++decId, tag: (p.tag || 'DECISION').toUpperCase(), title: p.title || 'Decision needed', desc: p.desc || p.detail || '', planId }] })
      if (planId && s.trade?.planId === planId) useS.setState({ trade: { ...useS.getState().trade!, approval: { timeout_s: p.timeout_s, since: e.ts }, step: 7 } })
      break
    }
    case 'alert': { const body = p.body ?? p.msg ?? '', hi = ['high', 'critical', 'error'].includes(p.level)
      notify(p.title && body ? `${p.title} · ${body}` : p.title || body || 'Alert', hi ? 'bad' : 'info'); if (hi || p.desktop || p.kind === 'trade') desktopAlert(p.title || 'NSKO QUANT', body); break }
    case 'order_filled': desktopAlert('Order filled', `${p.side?.toUpperCase?.() || ''} ${p.market || ''} ${p.qty ?? ''} @ ${p.price ?? ''}`.trim()); break
    case 'gods_eye_event': {
      // engine layers arrive as one event per layer refresh: {layer, features: [{id, lat, lon, alt_m?, label?}], attribution}
      const feats: any[] = Array.isArray(p.features) ? p.features : [p]
      for (const f of feats) { if (f.lat == null || f.lon == null) continue
        const g: GeoPt = { layer: p.layer, id: String(f.id ?? `${f.lat},${f.lon}`), lat: +f.lat, lon: +f.lon, alt: +(f.alt_m ?? f.alt ?? 0), label: f.label ?? f.name, ts: f.ts ?? p.ts ?? e.ts }
        geoPend[g.layer + ':' + g.id] = g }
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
