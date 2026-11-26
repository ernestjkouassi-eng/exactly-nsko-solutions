import { useEffect, useMemo, useRef, useState } from 'react'
import { createChart, CandlestickSeries, type IChartApi, type ISeriesApi, type IPriceLine, type UTCTimestamp } from 'lightweight-charts'
import { useS } from '../store'
import { Canvas } from '../viz/canvas'
import { Head, fmt } from '../shell/Shell'
import { MARKETS } from '../demo/sim'
import { RiskWarning } from './Money'
import { accountSummary, candles as getCandles, journal as getJournal, profile as getProfile, type Profile } from '../api'

// Live Desk: loaded on demand (React.lazy) so lightweight-charts stays out of the first bundle.
// Demo mode draws the Stage 1 overlays from the simulator. Engine mode draws ONLY what the engine sends:
// candles (/data/candles + `candle` events), order-flow bubbles (`orderflow_bubble`), the profile (`profile_update`
// or /data/profile), the forecast fan (`forecast_done` of the latest plan) and the real positions / journal.
type C = { time: UTCTimestamp; open: number; high: number; low: number; close: number }
function history(mkt: string, n = 160, step = 60): C[] {
  const m = MARKETS[mkt]; let p = m.px * (1 - .004), a = mkt.length * 999; const now = Math.floor(Date.now() / 1000 / step) * step; const out: C[] = []
  for (let i = n; i > 0; i--) { a = (a * 1103515245 + 12345) & 0x7fffffff; const r = (a / 0x7fffffff - .5) * 2; const o = p, c = p * (1 + r * m.vol * 2.2 + .00003); out.push({ time: (now - i * step) as UTCTimestamp, open: o, high: Math.max(o, c) * (1 + m.vol * .7 * Math.abs(r)), low: Math.min(o, c) * (1 - m.vol * .7 * Math.abs(r)), close: c }); p = c }
  const k = m.px / out[out.length - 1].close            // history ends exactly where the live demo ticks start
  return out.map(c => ({ ...c, open: c.open * k, high: c.high * k, low: c.low * k, close: c.close * k }))
}

export default function LiveDesk() {
  const source = useS(s => s.source), fallback = useS(s => s.fallback); const engine = source === 'engine' && !fallback
  const [mkt, setMkt] = useState('XAU/USD'); const box = useRef<HTMLDivElement>(null); const chart = useRef<IChartApi>(null); const ser = useRef<ISeriesApi<'Candlestick'>>(null)
  const data = useRef<C[]>([]); const price = useS(s => s.prices[mkt]); const bubbles = useS(s => s.bubbles); const killed = useS(s => s.killed)
  const live = useS(s => s.candles[`${mkt}|1m`]); const streamProfile = useS(s => s.profiles[mkt]); const fc = useS(s => s.forecasts[mkt])
  const [attrs, setAttrs] = useState<any>({}); const [prof, setProf] = useState<Profile | null>(null); const [acct, setAcct] = useState<any>(null); const [trades, setTrades] = useState<any[]>([])
  const lines = useRef<IPriceLine[]>([])
  useEffect(() => {
    const ch = createChart(box.current!, { layout: { background: { color: '#08080F' }, textColor: '#5A5F6E', fontFamily: 'JetBrains Mono', fontSize: 10, attributionLogo: true }, grid: { vertLines: { color: '#10111A' }, horzLines: { color: '#10111A' } },
      rightPriceScale: { borderColor: '#1A1C26', scaleMargins: { top: .12, bottom: .12 } }, timeScale: { borderColor: '#1A1C26', timeVisible: true, rightOffset: 40 }, crosshair: { vertLine: { color: '#3A3E4E' }, horzLine: { color: '#3A3E4E' } }, autoSize: true })
    const s = ch.addSeries(CandlestickSeries, { upColor: '#78D880', downColor: '#E04858', borderVisible: false, wickUpColor: '#78D880', wickDownColor: '#E04858' })
    chart.current = ch; ser.current = s; lines.current = []
    if (!engine) {
      data.current = history(mkt); s.setData(data.current)
      if (mkt === 'XAU/USD') { const last = data.current[data.current.length - 1].close
        s.createPriceLine({ price: last * .9994, color: '#E8541A', lineStyle: 2, title: 'ENTRY' }); s.createPriceLine({ price: last * .9981, color: '#E04858', lineStyle: 0, title: 'STOP' }); s.createPriceLine({ price: last * 1.0016, color: '#78D880', lineStyle: 0, title: 'TARGET' }) }
    } else {
      data.current = []
      getCandles(mkt, '1m', 180).then(r => { if (!r.ok || ser.current !== s) return; data.current = r.data.candles.map(c => ({ ...c, time: c.time as UTCTimestamp })); s.setData(data.current); setAttrs(r.data.attrs || {}) })
    }
    return () => { ch.remove(); if (ser.current === s) { ser.current = null; chart.current = null } }
  }, [mkt, engine])
  // engine: new closed bars from the feed; profile, account and journal refreshed every 20 s
  useEffect(() => { if (!engine || !live?.length || !ser.current) return; const c = live[live.length - 1], d = data.current
    if (!d.length || c.time > d[d.length - 1].time) { const k = { time: c.time as UTCTimestamp, open: c.open, high: c.high, low: c.low, close: c.close }; d.push(k); ser.current.update(k) } }, [live, engine])
  useEffect(() => { if (!engine) return; let on = true
    const load = () => { getProfile(mkt, '1m', 120).then(r => on && r.ok && setProf(r.data)); accountSummary().then(r => on && r.ok && !r.demo && setAcct(r.data)); getJournal(12).then(r => on && r.ok && setTrades(r.data.trades || [])) }
    load(); const i = setInterval(load, 20000); return () => { on = false; clearInterval(i) } }, [mkt, engine])
  // engine: real position lines (entry / stop / target of open positions on this market)
  useEffect(() => { const s = ser.current; if (!engine || !s) return; lines.current.forEach(l => { try { s.removePriceLine(l) } catch { /* chart rebuilt */ } }); lines.current = []
    for (const p of (acct?.positions || []).filter((p: any) => p.market === mkt)) {
      lines.current.push(s.createPriceLine({ price: p.entry, color: '#E8541A', lineStyle: 2, title: `ENTRY ${String(p.side).toUpperCase()} ${p.qty}` }))
      if (p.stop) lines.current.push(s.createPriceLine({ price: p.stop, color: '#E04858', lineStyle: 0, title: 'STOP · at broker' }))
      if (p.target) lines.current.push(s.createPriceLine({ price: p.target, color: '#78D880', lineStyle: 0, title: 'TARGET · at broker' })) } }, [acct, mkt, engine])
  useEffect(() => { if (engine || !price || !ser.current) return; const d = data.current; const now = Math.floor(Date.now() / 60000) * 60 as UTCTimestamp; const last = d[d.length - 1]
    if (last.time === now) { last.close = price; last.high = Math.max(last.high, price); last.low = Math.min(last.low, price); ser.current.update({ ...last }) } else { const c = { time: now, open: last.close, high: Math.max(last.close, price), low: Math.min(last.close, price), close: price }; d.push(c); ser.current.update(c) } }, [price, engine])
  // overlay: key-level zones, order-flow bubbles, volume profile, Kronos forecast fan
  const fan = useMemo(() => Array.from({ length: 160 }, (_, k) => { let y = 0, a = k * 7919 + 13; return Array.from({ length: 30 }, () => { a = (a * 1103515245 + 12345) & 0x7fffffff; y += (a / 0x7fffffff - .5) * 2 + .05; return y }) }), [])
  const pr: any = streamProfile?.bins?.length ? streamProfile : prof
  const drawEngine = (c: CanvasRenderingContext2D, w: number) => {
    const s = ser.current, ch = chart.current, d = data.current; if (!s || !ch || !d.length) return; const last = d[d.length - 1]
    const Y = (p: number) => s.priceToCoordinate(p) ?? -99, lx = ch.timeScale().timeToCoordinate(last.time) ?? w * .7
    c.font = '9px JetBrains Mono'
    if (pr?.bins?.length) {   // profile on the right edge + POC / value area lines
      const mx = Math.max(...pr.bins.map((b: any) => b.vol)) || 1, bh = Math.max(1, Math.abs(Y(pr.bins[0].price) - Y(pr.bins[pr.bins.length - 1].price)) / pr.bins.length - 1)
      for (const b of pr.bins) { const inVa = pr.val != null && b.price >= pr.val && b.price <= pr.vah; c.fillStyle = Math.abs(b.price - pr.poc) < 1e-9 ? '#E8541A' : inVa ? 'rgba(232,168,80,.5)' : 'rgba(90,95,110,.45)'; c.fillRect(w - 70 - b.vol / mx * 120, Y(b.price) - bh / 2, b.vol / mx * 120, bh) }
      for (const [k, col] of [['poc', '#E8541A'], ['vah', '#E8A850'], ['val', '#E8A850']] as const) if (pr[k] != null) { c.strokeStyle = col; c.setLineDash([4, 4]); c.beginPath(); c.moveTo(0, Y(pr[k])); c.lineTo(w - 70, Y(pr[k])); c.stroke(); c.setLineDash([]); c.fillStyle = col; c.fillText(k.toUpperCase(), 6, Y(pr[k]) - 3) }
      c.fillStyle = '#5A5F6E'; c.fillText(String(pr.label || (pr.volume_kind === 'exchange' ? 'VOLUME PROFILE' : 'TICK-VOLUME PROFILE')).toUpperCase() + (pr.synthetic ? ' · SYNTHETIC' : ''), w - 260, 14)
    }
    for (const b of bubbles.filter(b => b.market === mkt).slice(-200)) {   // aggressive orders, placed at their own minute
      const x = ch.timeScale().timeToCoordinate(Math.floor(b.t / 60000) * 60 as UTCTimestamp) ?? lx; const r = Math.min(22, 3 + Math.sqrt(b.size) * 2)
      c.fillStyle = b.side === 'buy' ? 'rgba(120,216,128,.28)' : 'rgba(224,72,88,.28)'; c.strokeStyle = b.side === 'buy' ? 'rgba(120,216,128,.7)' : 'rgba(224,72,88,.7)'; c.beginPath(); c.arc(x, Y(b.price), r, 0, 7); c.fill(); c.stroke() }
    if (fc?.fan?.p50?.length) {   // the latest plan's forecast: P10–P90 band and the median, from the bar it was made on
      const f = fc.fan, step = Math.max(4, (w - 90 - lx) / f.p50.length)
      c.fillStyle = 'rgba(232,84,26,.14)'; c.beginPath(); c.moveTo(lx, Y(fc.entry)); f.p90.forEach((v: number, i: number) => c.lineTo(lx + (i + 1) * step, Y(v))); for (let i = f.p10.length - 1; i >= 0; i--) c.lineTo(lx + (i + 1) * step, Y(f.p10[i])); c.closePath(); c.fill()
      c.strokeStyle = 'rgba(232,84,26,.9)'; c.beginPath(); c.moveTo(lx, Y(fc.entry)); f.p50.forEach((v: number, i: number) => c.lineTo(lx + (i + 1) * step, Y(v))); c.stroke()
      c.fillStyle = 'rgba(232,84,26,.9)'; c.font = '10px JetBrains Mono'; c.fillText(`${String(fc.engine).toUpperCase()} · ${fmt(fc.paths)} PATHS · ${fc.agree_pct}% AGREE`, lx + 8, Y(fc.entry) - 40)
    }
  }
  const draw = (c: CanvasRenderingContext2D, w: number, h: number) => {
    c.clearRect(0, 0, w, h); if (engine) return drawEngine(c, w); const s = ser.current, ch = chart.current; if (!s || !ch || !data.current.length) return; const d = data.current; const last = d[d.length - 1]
    const Y = (p: number) => s.priceToCoordinate(p) ?? -99, lx = ch.timeScale().timeToCoordinate(last.time) ?? w * .7
    if (mkt === 'XAU/USD') {
      c.fillStyle = 'rgba(232,168,80,.10)'; const z1 = Y(last.close * .9984), z2 = Y(last.close * .9990); c.fillRect(0, Math.min(z1, z2), lx, Math.abs(z1 - z2))
      c.fillStyle = 'rgba(224,72,88,.12)'; const r1 = Y(last.close * 1.0021), r2 = Y(last.close * 1.0026); c.fillRect(0, Math.min(r1, r2), lx, Math.abs(r1 - r2))
      c.font = '9px JetBrains Mono'; c.fillStyle = '#E8A850'; c.fillText('KEY LEVEL · VALUE AREA LOW', 8, Math.min(z1, z2) - 4); c.fillStyle = '#E04858'; c.fillText('RESISTANCE', 8, Math.min(r1, r2) - 4)
      d.slice(-110, -1).forEach((k, i) => { const hsh = (i * 2654435761 + k.time) % 97; if (hsh % 3) return; const x = ch.timeScale().timeToCoordinate(k.time); if (x == null) return   // aggressive volume bubbles on past candles (demo)
        const buy = k.close >= k.open, r = 4 + (hsh % 17); c.fillStyle = buy ? 'rgba(120,216,128,.22)' : 'rgba(224,72,88,.22)'; c.strokeStyle = buy ? 'rgba(120,216,128,.6)' : 'rgba(224,72,88,.6)'; c.beginPath(); c.arc(x, Y(buy ? k.low : k.high), r, 0, 7); c.fill(); c.stroke() })
      bubbles.slice(-160).forEach(b => { const age = (Date.now() - b.t) / 1000, x = lx - age * 2.2; if (x < 0) return; const y = Y(b.price), r = Math.min(22, Math.sqrt(b.size) * 1.6)
        c.fillStyle = b.side === 'buy' ? 'rgba(120,216,128,.28)' : 'rgba(224,72,88,.28)'; c.strokeStyle = b.side === 'buy' ? 'rgba(120,216,128,.7)' : 'rgba(224,72,88,.7)'; c.beginPath(); c.arc(x, y, r, 0, 7); c.fill(); c.stroke() })
      // volume profile on the right edge (tick-volume profile on gold CFDs)
      const lo = Math.min(...d.slice(-120).map(x => x.low)), hi = Math.max(...d.slice(-120).map(x => x.high)); const bins = 36
      for (let i = 0; i < bins; i++) { const p = lo + (hi - lo) * (i + .5) / bins; const v = Math.exp(-(((i - 21) / 6) ** 2)) * .8 + Math.exp(-(((i - 9) / 4) ** 2)) * .4 + .08; const y = Y(p), bh = Math.max(1, Math.abs(Y(lo) - Y(hi)) / bins - 1)
        c.fillStyle = i === 21 ? '#E8541A' : i > 14 && i < 28 ? 'rgba(232,168,80,.55)' : 'rgba(90,95,110,.5)'; { const pw = Math.min(120, w * .16); c.fillRect(w - 70 - v * pw, y - bh / 2, v * pw, bh) } }
      c.fillStyle = '#5A5F6E'; c.fillText('TICK-VOLUME PROFILE', w - 190, 14)
    }
    // Kronos fan: 1,000 possible paths (160 drawn)
    const px = last.close, step = Math.max(4, (w - 90 - lx) / 30)
    c.lineWidth = .7; fan.forEach(p => { c.strokeStyle = 'rgba(232,84,26,.10)'; c.beginPath(); c.moveTo(lx, Y(px)); p.forEach((v, i) => c.lineTo(lx + (i + 1) * step, Y(px * (1 + v * MARKETS[mkt].vol * .8)))); c.stroke() }); c.lineWidth = 1
    c.fillStyle = 'rgba(232,84,26,.9)'; c.font = '10px JetBrains Mono'; c.fillText('KRONOS · 1,000 POSSIBLE PATHS', lx + 8, Y(px) - 60)
  }
  const pnl = price ? (price - MARKETS['XAU/USD'].px * .9994) * 10 : 0
  const lastPx = engine ? (live?.length ? live[live.length - 1].close : data.current[data.current.length - 1]?.close) : price
  const cur = acct?.account?.currency || 'GBP', money = (n: number) => `${n < 0 ? '−' : ''}${cur === 'GBP' ? '£' : ''}${fmt(Math.abs(n), 2)}${cur === 'GBP' ? '' : ' ' + cur}`
  return <div className="page">
    <div className="row" style={{ marginBottom: 10 }}>{Object.keys(MARKETS).map(m => <button key={m} onClick={() => setMkt(m)} style={{ borderColor: mkt === m ? 'var(--orange)' : undefined }} className="mono">{m}</button>)}
      {engine && <span className={`chip ${attrs.synthetic ? 'a' : 'g'}`} data-testid="desk-source" style={{ borderColor: 'var(--line)' }}>{attrs.synthetic ? 'SYNTHETIC CANDLES · no real source for this market yet' : `REAL · ${attrs.source || 'engine'}`}</span>}
      <span className="num" style={{ marginLeft: 'auto', fontSize: 22 }}>{lastPx ? fmt(lastPx, MARKETS[mkt].dp) : '—'}</span>{killed && <span className="chip r" style={{ borderColor: '#5A2028' }}>TRADING LOCKED</span>}</div>
    <div className="grid" style={{ gridTemplateColumns: '1fr 300px' }}>
      <div className="panel" style={{ height: 560, position: 'relative' }}><div ref={box} style={{ position: 'absolute', inset: 0 }} /><div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 5 }}><Canvas draw={draw} /></div></div>
      {engine ? <div className="grid" style={{ alignContent: 'start' }}>
        <div className="panel"><Head t={`ACCOUNT · ${acct?.paper ? 'PAPER' : 'BROKER'}`} /><div className="pb">{acct?.account ? [['EQUITY', money(acct.account.equity)], ['BALANCE', money(acct.account.balance ?? acct.account.equity)], ['MARGIN IN USE', money(acct.account.margin_used || 0)]].map(([l, v]) => <div key={l} style={{ marginBottom: 10 }}><div className="lbl">{l}</div><div className="big" style={{ fontSize: 20 }}>{v}</div></div>) : <div className="lo">Loading…</div>}</div></div>
        <div className="panel"><Head t="OPEN POSITIONS" /><table><tbody>{(acct?.positions || []).length ? acct.positions.map((p: any) => <tr key={p.id}><td>{p.market}</td><td className={p.side === 'buy' ? 'g' : 'r'}>{String(p.side).toUpperCase()} {p.qty}</td><td className={(p.unrealised || 0) >= 0 ? 'g' : 'r'}>{money(p.unrealised || 0)}</td></tr>) : <tr><td className="lo">None</td></tr>}</tbody></table></div>
        <div className="panel"><Head t="ORDERS" s="resting at the broker" /><table><tbody>{(acct?.orders || []).length ? acct.orders.map((o: any) => <tr key={o.id}><td>{String(o.role || o.kind).toUpperCase()}</td><td className={o.role === 'stop' ? 'r' : 'g'}>{fmt(o.price ?? 0, MARKETS[o.market]?.dp ?? 2)}</td><td className="lo">{o.market}</td></tr>) : <tr><td className="lo">None</td></tr>}</tbody></table></div>
      </div> : <div className="grid" style={{ alignContent: 'start' }}>
        <div className="panel"><Head t="ACCOUNT · PAPER" /><div className="pb">{[['EQUITY', '£10,000.00'], ["TODAY'S P&L", `${pnl >= 0 ? '+' : ''}£${pnl.toFixed(2)}`], ['RISK USED TODAY', '1.0% of 3%']].map(([l, v]) => <div key={l} style={{ marginBottom: 10 }}><div className="lbl">{l}</div><div className={`big ${l.includes('P&L') ? (pnl >= 0 ? 'g' : 'r') : ''}`} style={{ fontSize: 20 }}>{v}</div></div>)}<div className="bar"><i style={{ width: '33%', background: 'var(--amber)' }} /></div></div></div>
        <div className="panel"><Head t="OPEN POSITIONS" /><table><tbody><tr><td>XAU/USD</td><td className="g">BUY 0.10</td><td className={pnl >= 0 ? 'g' : 'r'}>{pnl >= 0 ? '+' : ''}£{pnl.toFixed(2)}</td></tr></tbody></table></div>
        <div className="panel"><Head t="ORDERS" /><table><tbody><tr><td>STOP</td><td className="r">{fmt(MARKETS['XAU/USD'].px * .9981, 2)}</td><td className="lo">at broker</td></tr><tr><td>TARGET</td><td className="g">{fmt(MARKETS['XAU/USD'].px * 1.0016, 2)}</td><td className="lo">at broker</td></tr></tbody></table></div>
      </div>}
    </div>
    <div className="panel" style={{ marginTop: 12 }}><Head t="TRADE HISTORY" s={engine ? 'journal · from the engine' : 'paper'}><button style={{ padding: '3px 8px', fontSize: 10 }}>Export CSV</button></Head><table><thead><tr>{['Time', 'Market', 'Side', engine ? 'Mode' : 'Strategy', 'Entry', 'Exit', 'Result'].map(h => <th key={h}>{h}</th>)}</tr></thead>
      <tbody>{engine ? (trades.length ? trades.map(t => { const d = (() => { try { return JSON.parse(t.detail || '{}') } catch { return {} } })(); return <tr key={t.id}><td>{new Date(t.ts * 1000).toLocaleTimeString('en-GB', { hour12: false })}</td><td>{t.market}</td><td>{String(t.side).toUpperCase()}</td><td className="lo">{t.mode}</td><td>{fmt(d.entry ?? 0, 2)}</td><td>{fmt(d.exit ?? 0, 2)}</td><td className={t.r_multiple >= 0 ? 'g' : 'r'}>{t.r_multiple >= 0 ? '+' : ''}{(+t.r_multiple).toFixed(2)}R · {money(t.pnl)}</td></tr> })
        : <tr><td colSpan={7} className="lo">No closed trades yet.</td></tr>)
        : [['09:14', 'XAU/USD', 'BUY', 'OF-1 Sweep', '2,641.20', '2,646.10', '+1.6R'], ['10:52', 'BTC/USD', 'SELL', 'VWAP-Rev', '97,880', '97,410', '+1.1R'], ['13:31', 'XAU/USD', 'BUY', 'OF-1 Sweep', '2,644.00', '2,641.70', '−1.0R']].map(r => <tr key={r[0]}>{r.map((x, i) => <td key={i} className={i === 6 ? (x.startsWith('+') ? 'g' : 'r') : ''}>{x}</td>)}</tr>)}</tbody></table></div>
    <RiskWarning />
  </div>
}
