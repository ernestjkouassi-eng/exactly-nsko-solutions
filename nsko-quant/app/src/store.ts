import { create } from 'zustand'
import { on, startDemo, type Ev } from './demo/sim'

export type Variant = { id: number; recipe: string; market: string; tf: string; sharpeIS: number; sharpeOOS: number; trades: number; win: number; rr: number; dd: number; outcome: 'clear' | 'sieve' | 'failed'; why: string | null; seed: number }
type S = {
  demo: boolean; mode: 'PAPER' | 'LIVE'; auto: boolean; killed: boolean
  round: number; health: any; budget: { used: number; of: number; days: number }
  log: { ts: number; verb: string; msg: string }[]
  variants: Variant[]; tested: number; sieve: number; clear: number; fails: Record<string, number>; lastFail: string | null
  prices: Record<string, number>; series: Record<string, { t: number; p: number }[]>
  bubbles: { t: number; price: number; size: number; side: string }[]
  sources: { kind: string; title: string; idea: string; ts: number }[]
  handoffs: { from: string; to: string; ts: number }[]
  decisions: { id: number; tag: string; title: string; desc: string }[]
  set: (p: Partial<S>) => void
}
export const useS = create<S>((set) => ({
  demo: true, mode: 'PAPER', auto: true, killed: false, round: 12646, health: {}, budget: { used: 31, of: 50, days: 18 },
  log: [], variants: [], tested: 1251, sieve: 343, clear: 12,
  fails: { 'Win rate too low': 65, 'R:R too low': 18, 'Too few trades': 76, 'Expectancy negative after costs': 20, 'Max drawdown too deep': 219, "Doesn't work out-of-sample": 147 }, lastFail: null,
  prices: {}, series: {}, bubbles: [], sources: [], handoffs: [],
  decisions: [
    { id: 1, tag: 'TO PAPER', title: 'Trend-follower XAU · 4h', desc: 'Sharpe OOS 1.64 · 412 trades · max DD −11.2R. Cleared the bar after costs.' },
    { id: 2, tag: 'SKILL PROPOSAL', title: 'Check the news blackout earlier', desc: 'SCOUT suggests widening the CPI blackout from ±15 to ±20 min on gold.' },
  ],
  set: (p) => set(p),
}))

let wired = false
let pend: Record<string, { t: number; p: number }> = {}; let flushT: any = 0
export function wire() {
  if (wired) return; wired = true; startDemo()
  on((e: Ev) => {
    const s = useS.getState(); if (s.killed && ['order_sent'].includes(e.type)) return
    switch (e.type) {
      case 'engine_health': useS.setState({ round: e.payload.round, health: e.payload }); break
      case 'budget_update': useS.setState({ budget: e.payload }); break
      case 'ticker_log': useS.setState({ log: [...s.log.slice(-79), { ts: e.ts, ...e.payload }] }); break
      case 'tick': {   // coalesce: one store update per batch of ticks, not one per market
        pend[e.payload.market] = { t: e.ts, p: e.payload.price }
        if (!flushT) flushT = setTimeout(() => { flushT = 0; const st = useS.getState(); const prices = { ...st.prices }, series = { ...st.series }
          for (const [m, v] of Object.entries(pend)) { prices[m] = v.p; series[m] = [...(series[m] || []).slice(-1999), v] } pend = {}; useS.setState({ prices, series }) }, 250)
        break
      }
      case 'orderflow_bubble': useS.setState({ bubbles: [...s.bubbles.slice(-300), { t: e.ts, ...e.payload }] }); break
      case 'source_added': useS.setState({ sources: [...s.sources.slice(-40), { ...e.payload, ts: e.ts }] }); break
      case 'agent_handoff': useS.setState({ handoffs: [...s.handoffs.slice(-30), { from: e.payload.from, to: e.payload.to, ts: e.ts }] }); break
      case 'variant_tested': {
        const v = e.payload as Variant; const fails = { ...s.fails }; if (v.why) fails[v.why]++
        useS.setState({ variants: [...s.variants.slice(-599), v], tested: s.tested + 1, sieve: s.sieve + (v.outcome !== 'failed' ? 1 : 0), clear: s.clear + (v.outcome === 'clear' ? 1 : 0), fails, lastFail: v.why })
        break
      }
    }
  })
}
