// DEMO DATA simulator. Emits exactly the WebSocket event contract the real engine will emit (master prompt section 10),
// so Stage 2 only swaps the source. Seeded: the same demo plays out the same way every time.
export type Ev = { type: string; ts: number; payload: any }
type Fn = (e: Ev) => void

function mulberry32(a: number) {
  return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296 }
}
export const rnd = mulberry32(20261126)
export const pick = <T,>(a: T[]) => a[Math.floor(rnd() * a.length)]
export const gauss = () => { let u = 0, v = 0; while (!u) u = rnd(); while (!v) v = rnd(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v) }

const subs = new Set<Fn>()
export const on = (f: Fn) => { subs.add(f); return () => { subs.delete(f) } }
const emit = (type: string, payload: any) => { const e = { type, ts: Date.now(), payload }; subs.forEach(f => f(e)) }

export const MARKETS: Record<string, { px: number; vol: number; dp: number }> = {
  'XAU/USD': { px: 2648.4, vol: .00045, dp: 2 }, 'BTC/USD': { px: 97240, vol: .0011, dp: 0 },
  'ETH/USD': { px: 3612, vol: .0013, dp: 1 }, 'NVDA': { px: 141.2, vol: .0009, dp: 2 }, 'AAPL': { px: 232.6, vol: .0006, dp: 2 },
}
export const IDEA_TYPES = ['Trend following', 'Mean reversion', 'Breakout', 'Volatility', 'Orderflow', 'Seasonality', 'Carry']
export const AGENTS = ['JARVIS', 'SCOUT', 'READER', 'WATCHER', 'SUMMARISER 1', 'SUMMARISER 2', 'SUMMARISER 3', 'TERM-CHECKER', 'RECIPE-MAKER', 'LAB', 'RISK', 'EXECUTOR']
const SEARCHES = ['GitHub "orderflow futures backtest"', 'arXiv "time-series momentum gold"', 'YouTube "London session XAU scalping"', 'Web "VWAP reversion intraday"',
  'GitHub "volume profile python"', 'arXiv "regime switching commodities"', 'YouTube "liquidity sweep reclaim"', 'Web "COT positioning gold"']
const TITLES = ['Time-series momentum on index futures', 'Order blocks and fair value gaps, explained', 'Volatility breakout on gold, 4h', 'Seasonality in precious metals',
  'Carry and roll yield in commodity futures', 'Reading the volume profile like a market maker', 'Opening-range breakout: does it still work?']
const RECIPES = ['Range-XAU', 'Trend-XAU', 'Sweep-XAU', 'VWAP-Rev-BTC', 'ORB-NVDA', 'Breakout-ETH', 'Carry-XAU', 'OF-1-XAU', 'Momentum-BTC']
const FAILS = ['Win rate too low', 'R:R too low', 'Too few trades', 'Expectancy negative after costs', 'Max drawdown too deep', "Doesn't work out-of-sample"]

let started = false
export function startDemo() {
  if (started) return; started = true
  let round = 12646, tested = 1251
  const px: Record<string, number> = Object.fromEntries(Object.entries(MARKETS).map(([k, v]) => [k, v.px]))
  setInterval(() => { round++; emit('engine_health', { round, uptime: round, cpu: 18 + rnd() * 9, ram: 2.1 + rnd() * .3, keepAwake: true, heartbeat: Date.now() }) }, 1000)
  setInterval(() => {
    for (const k of Object.keys(px)) {
      const m = MARKETS[k]; px[k] *= 1 + gauss() * m.vol * .35
      emit('tick', { market: k, price: px[k], bid: px[k] * (1 - .00004), ask: px[k] * (1 + .00004) })
      if (k === 'XAU/USD' && rnd() < .35) emit('orderflow_bubble', { market: k, price: px[k], size: Math.exp(gauss() * .8) * 40, side: rnd() < .5 ? 'buy' : 'sell' })
    }
  }, 250)
  const logVerb = () => {
    const r = rnd(), t = pick(TITLES)
    if (r < .2) emit('ticker_log', { verb: 'SEARCH', msg: `${pick(SEARCHES)} · ${3 + Math.floor(rnd() * 9)} results, ${Math.floor(rnd() * 3)} new` })
    else if (r < .36) emit('ticker_log', { verb: 'READ', msg: `Browser opens "${t}" · ${1200 + Math.floor(rnd() * 2400)} words` })
    else if (r < .48) emit('ticker_log', { verb: 'SUMMARISE', msg: `"${t}" → idea type ${pick(IDEA_TYPES)}` })
    else if (r < .58) emit('ticker_log', { verb: 'TERM', msg: `new term "${pick(['fair value gap', 'order block', 'liquidity sweep', 'VWAP band', 'point of control'])}" queued for checking` })
    else if (r < .68) emit('ticker_log', { verb: 'SAVE', msg: `source saved · ${pick(IDEA_TYPES)} cluster` })
    else if (r < .76) emit('ticker_log', { verb: 'REJECT', msg: `"this strategy always wins" · promises fixed profit` })
    else if (r < .82) emit('ticker_log', { verb: 'BUDGET', msg: `think budget · ${(31 + rnd()).toFixed(2)} of 50 used` })
    else emit('ticker_log', { verb: 'TEST', msg: `${pick(RECIPES)} ${8 + Math.floor(rnd() * 12)} · 4h · walk-forward started` })
  }
  setInterval(logVerb, 1400)
  setInterval(() => {
    const kind = pick(['YouTube', 'GitHub', 'arXiv', 'Web'])
    emit('source_added', { kind, title: pick(TITLES), idea: pick(IDEA_TYPES) })
    const a = pick(AGENTS.slice(1, 10)), b = pick(AGENTS.slice(1, 10))
    if (a !== b) emit('agent_handoff', { from: a, to: b, item: pick(TITLES) })
  }, 2600)
  setInterval(() => {
    tested++
    const isS = gauss() * .5 + .4, oos = isS - Math.abs(gauss()) * .9 + gauss() * .15
    const pass = oos >= 1.4 ? 'clear' : oos > .7 && rnd() < .5 ? 'sieve' : 'failed'
    emit('variant_tested', { id: tested, recipe: `${pick(RECIPES)} ${1 + Math.floor(rnd() * 20)}`, market: pick(['XAU', 'BTC', 'ETH', 'NVDA']), tf: pick(['5m', '15m', '1h', '4h']),
      sharpeIS: +isS.toFixed(2), sharpeOOS: +oos.toFixed(2), trades: 40 + Math.floor(rnd() * 600), win: +(38 + rnd() * 24).toFixed(1), rr: +(1 + rnd() * 1.4).toFixed(2),
      dd: +(-4 - rnd() * 22).toFixed(1), outcome: pass, why: pass === 'failed' ? pick(FAILS) : null, seed: Math.floor(rnd() * 1e9) })
  }, 2200)
  setInterval(() => emit('budget_update', { used: 31 + rnd() * .5, of: 50, days: 18 }), 5000)
}
