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

let timers: ReturnType<typeof setInterval>[] = []
let round = 12646, tested = 1251
export const demoRunning = () => timers.length > 0
export function stopDemo() { timers.forEach(clearInterval); timers = [] }
export function startDemo() {
  if (timers.length) return
  const setInterval = (f: () => void, ms: number) => { const id = globalThis.setInterval(f, ms); timers.push(id); return id }
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
  demoGodsEye(setInterval)
}

// ---------- God's Eye demo layers: the same gods_eye_event / market_impact events the engine sends.
// gods_eye_event payload: { layer, id, lat, lon, alt_m?, label?, ts? } (ts = when it was observed, ms)
const LANES = [[26.5, 56.3, 12, 45], [12, 45, 30, 32.5], [1.3, 103.8, 22, 114], [36, -6, 50, 0], [30, 32.5, 36, -6], [51, 2, 40, -70], [-34, 18, 1.3, 103.8]]
const GE_STATIC: Record<string, [number, number, string][]> = {
  Military: [[26, 56, 'patrol orbit'], [35, 33, 'tanker track'], [49, 32, 'ISR orbit'], [36, 129, 'patrol'], [24, 121, 'patrol'], [52, 20, 'tanker track']],
  Quakes: [[-23.6, -70.4, 'M6.4 · Antofagasta, Chile'], [38.3, 142.4, 'M5.1 · off Honshu'], [36.2, 28.0, 'M4.6 · Aegean']],
  Fires: [[-25, 135, 'bushfire cluster'], [-28, 145, 'bushfire'], [-12, -55, 'Mato Grosso clearing fires'], [38, -120, 'Sierra Nevada fire'], [-8, 25, 'savanna burning']],
  Weather: [[-19.9, -44, 'frost risk −1 °C'], [6.8, -5.3, 'dry Harmattan'], [40, -95, 'heat dome']],
  Launches: [[28.5, -80.6, 'Falcon 9 · Starlink'], [45.9, 63.3, 'Soyuz'], [19.6, 110.9, 'Long March 7']],
  Crops: [[-19.9, -44.5, 'coffee NDVI −7%'], [6.8, -5.3, 'cocoa NDVI −4%'], [7.9, -1.0, 'cocoa'], [41, -93, 'corn belt'], [48, 35, 'wheat']],
}
function demoGodsEye(every: (f: () => void, ms: number) => unknown) {
  const now = Date.now(), H = 3600e3
  const flights = Array.from({ length: 320 }, (_, i) => ({ id: 'F' + i, lat: ((i * 37) % 120) - 50 + (i % 3) * 5, lon: ((i * 91) % 300) - 150, h: (i * 53) % 360 })).filter(f => !(f.lon < -30 && f.lon > -60 && f.lat < 0))
  const ships = Array.from({ length: 160 }, (_, i) => ({ id: 'S' + i, lane: LANES[i % LANES.length], u: (i * .137) % 1 }))
  const sats = Array.from({ length: 140 }, (_, i) => ({ id: 'SAT' + i, a: i * .7, inc: 20 + (i % 6) * 14, raan: (i * 47) % 360 }))
  const emitAll = (age = 0) => {
    flights.forEach(f => emit('gods_eye_event', { layer: 'Flights', id: f.id, lat: f.lat, lon: f.lon, alt_m: 10500, ts: now - age }))
    ships.forEach(s => { const l = s.lane; emit('gods_eye_event', { layer: 'Ships', id: s.id, lat: l[0] + (l[2] - l[0]) * s.u, lon: l[1] + (l[3] - l[1]) * s.u, ts: now - age }) })
    sats.forEach(s => { const lat = Math.asin(Math.sin(s.inc * Math.PI / 180) * Math.sin(s.a)) * 180 / Math.PI; const lon = ((s.raan + s.a * 180 / Math.PI) % 360) - 180; emit('gods_eye_event', { layer: 'Satellites', id: s.id, lat, lon, alt_m: 550e3, ts: now - age }) })
  }
  emitAll()
  Object.entries(GE_STATIC).forEach(([layer, pts]) => pts.forEach(([lat, lon, label], i) => emit('gods_eye_event', { layer, id: layer + i, lat, lon, label, ts: now - ((i * 5 + layer.length) % 23) * H })))
  emit('market_impact', { id: 'hormuz', title: 'TANKER SLOWDOWN · STRAIT OF HORMUZ', asset: 'Oil ↑ watch · Gold safe-haven watch', note: 'JARVIS: 14 tankers below 4 kn for 6h (demo). Watching Brent; no trade opened.', tone: 'cyan', lat: 26.5, lon: 56.3 })
  emit('market_impact', { id: 'frost', title: 'FROST RISK · MINAS GERAIS', asset: 'Arabica coffee watch', note: 'JARVIS: GFS shows −1 °C at dawn over the coffee belt (demo). Sent to Research.', tone: 'blue', lat: -19.9, lon: -44 })
  emit('market_impact', { id: 'quake', title: 'M6.4 QUAKE · NEAR COPPER MINES, CHILE', asset: 'Copper / metals watch', note: 'JARVIS: risk action → cut size 50% on metals for 24h (demo).', tone: 'red', lat: -23.6, lon: -70.4 })
  every(() => {   // movement: flights ~ 0.6°/tick along their heading, ships along their lane, satellites along the orbit
    flights.forEach(f => { f.lat = Math.max(-70, Math.min(75, f.lat + Math.cos(f.h * Math.PI / 180) * .6)); f.lon = ((f.lon + Math.sin(f.h * Math.PI / 180) * .6 + 540) % 360) - 180 })
    ships.forEach(s => { s.u = (s.u + .002) % 1 }); sats.forEach(s => { s.a += .05 })
    const t = Date.now(); flights.forEach(f => emit('gods_eye_event', { layer: 'Flights', id: f.id, lat: f.lat, lon: f.lon, alt_m: 10500, ts: t }))
    ships.forEach(s => { const l = s.lane; emit('gods_eye_event', { layer: 'Ships', id: s.id, lat: l[0] + (l[2] - l[0]) * s.u, lon: l[1] + (l[3] - l[1]) * s.u, ts: t }) })
    sats.forEach(s => { const lat = Math.asin(Math.sin(s.inc * Math.PI / 180) * Math.sin(s.a)) * 180 / Math.PI; const lon = ((s.raan + s.a * 180 / Math.PI) % 360) - 180; emit('gods_eye_event', { layer: 'Satellites', id: s.id, lat, lon, alt_m: 550e3, ts: t }) })
  }, 3000)
}
