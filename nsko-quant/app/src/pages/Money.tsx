import { useEffect, useMemo, useRef, useState } from 'react'
import { createChart, CandlestickSeries, type IChartApi, type ISeriesApi, type UTCTimestamp } from 'lightweight-charts'
import { useS } from '../store'
import { Canvas } from '../viz/canvas'
import { Head, fmt } from '../shell/Shell'
import { DecisionCards } from './Overview'
import { MARKETS } from '../demo/sim'

const RISK_WARN = 'Trading leveraged products like CFDs and spread bets carries a high risk of losing money rapidly. Most retail investor accounts lose money. Only trade with money you can afford to lose. NSKO QUANT is software, not financial advice. Past and simulated results do not guarantee future results.'
export const RiskWarning = () => <div className="lo" style={{ fontSize: 10, lineHeight: 1.5, padding: '10px 0' }}>{RISK_WARN}</div>

type C = { time: UTCTimestamp; open: number; high: number; low: number; close: number }
function history(mkt: string, n = 160, step = 60): C[] {
  const m = MARKETS[mkt]; let p = m.px * (1 - .004), a = mkt.length * 999; const now = Math.floor(Date.now() / 1000 / step) * step; const out: C[] = []
  for (let i = n; i > 0; i--) { a = (a * 1103515245 + 12345) & 0x7fffffff; const r = (a / 0x7fffffff - .5) * 2; const o = p, c = p * (1 + r * m.vol * 2.2 + .00003); out.push({ time: (now - i * step) as UTCTimestamp, open: o, high: Math.max(o, c) * (1 + m.vol * .7 * Math.abs(r)), low: Math.min(o, c) * (1 - m.vol * .7 * Math.abs(r)), close: c }); p = c }
  return out
}

export function LiveDesk() {
  const [mkt, setMkt] = useState('XAU/USD'); const box = useRef<HTMLDivElement>(null); const chart = useRef<IChartApi>(null); const ser = useRef<ISeriesApi<'Candlestick'>>(null)
  const data = useRef<C[]>([]); const price = useS(s => s.prices[mkt]); const bubbles = useS(s => s.bubbles); const killed = useS(s => s.killed)
  useEffect(() => {
    const ch = createChart(box.current!, { layout: { background: { color: '#08080F' }, textColor: '#5A5F6E', fontFamily: 'JetBrains Mono', fontSize: 10, attributionLogo: true }, grid: { vertLines: { color: '#10111A' }, horzLines: { color: '#10111A' } },
      rightPriceScale: { borderColor: '#1A1C26', scaleMargins: { top: .12, bottom: .12 } }, timeScale: { borderColor: '#1A1C26', timeVisible: true, rightOffset: 22 }, crosshair: { vertLine: { color: '#3A3E4E' }, horzLine: { color: '#3A3E4E' } }, autoSize: true })
    const s = ch.addSeries(CandlestickSeries, { upColor: '#78D880', downColor: '#E04858', borderVisible: false, wickUpColor: '#78D880', wickDownColor: '#E04858' })
    data.current = history(mkt); s.setData(data.current); chart.current = ch; ser.current = s
    if (mkt === 'XAU/USD') { const last = data.current[data.current.length - 1].close
      s.createPriceLine({ price: last * .9994, color: '#E8541A', lineStyle: 2, title: 'ENTRY' }); s.createPriceLine({ price: last * .9981, color: '#E04858', lineStyle: 0, title: 'STOP' }); s.createPriceLine({ price: last * 1.0016, color: '#78D880', lineStyle: 0, title: 'TARGET' }) }
    return () => ch.remove()
  }, [mkt])
  useEffect(() => { if (!price || !ser.current) return; const d = data.current; const now = Math.floor(Date.now() / 60000) * 60 as UTCTimestamp; const last = d[d.length - 1]
    if (last.time === now) { last.close = price; last.high = Math.max(last.high, price); last.low = Math.min(last.low, price); ser.current.update({ ...last }) } else { const c = { time: now, open: last.close, high: Math.max(last.close, price), low: Math.min(last.close, price), close: price }; d.push(c); ser.current.update(c) } }, [price])
  // overlay: key-level zones, order-flow bubbles, volume profile, Kronos forecast fan
  const fan = useMemo(() => Array.from({ length: 160 }, (_, k) => { let y = 0, a = k * 7919 + 13; return Array.from({ length: 30 }, () => { a = (a * 1103515245 + 12345) & 0x7fffffff; y += (a / 0x7fffffff - .5) * 2 + .05; return y }) }), [])
  const draw = (c: CanvasRenderingContext2D, w: number, h: number) => {
    c.clearRect(0, 0, w, h); const s = ser.current, ch = chart.current; if (!s || !ch || !data.current.length) return; const d = data.current; const last = d[d.length - 1]
    const Y = (p: number) => s.priceToCoordinate(p) ?? -99, lx = ch.timeScale().timeToCoordinate(last.time) ?? w * .7
    if (mkt === 'XAU/USD') {
      c.fillStyle = 'rgba(232,168,80,.10)'; const z1 = Y(last.close * .9984), z2 = Y(last.close * .9990); c.fillRect(0, Math.min(z1, z2), lx, Math.abs(z1 - z2))
      c.fillStyle = 'rgba(224,72,88,.12)'; const r1 = Y(last.close * 1.0021), r2 = Y(last.close * 1.0026); c.fillRect(0, Math.min(r1, r2), lx, Math.abs(r1 - r2))
      c.font = '9px JetBrains Mono'; c.fillStyle = '#E8A850'; c.fillText('KEY LEVEL · VALUE AREA LOW', 8, Math.min(z1, z2) - 4); c.fillStyle = '#E04858'; c.fillText('RESISTANCE', 8, Math.min(r1, r2) - 4)
      const t0 = d[0].time; bubbles.slice(-160).forEach(b => { const age = (Date.now() - b.t) / 1000, x = lx - age * 2.2; if (x < 0) return; const y = Y(b.price), r = Math.min(22, Math.sqrt(b.size) * 1.6)
        c.fillStyle = b.side === 'buy' ? 'rgba(120,216,128,.28)' : 'rgba(224,72,88,.28)'; c.strokeStyle = b.side === 'buy' ? 'rgba(120,216,128,.7)' : 'rgba(224,72,88,.7)'; c.beginPath(); c.arc(x, y, r, 0, 7); c.fill(); c.stroke() }); void t0
      // volume profile on the right edge (tick-volume profile on gold CFDs)
      const lo = Math.min(...d.slice(-120).map(x => x.low)), hi = Math.max(...d.slice(-120).map(x => x.high)); const bins = 36
      for (let i = 0; i < bins; i++) { const p = lo + (hi - lo) * (i + .5) / bins; const v = Math.exp(-(((i - 21) / 6) ** 2)) * .8 + Math.exp(-(((i - 9) / 4) ** 2)) * .4 + .08; const y = Y(p), bh = Math.max(1, Math.abs(Y(lo) - Y(hi)) / bins - 1)
        c.fillStyle = i === 21 ? '#E8541A' : i > 14 && i < 28 ? 'rgba(232,168,80,.55)' : 'rgba(90,95,110,.5)'; c.fillRect(w - 70 - v * 120, y - bh / 2, v * 120, bh) }
      c.fillStyle = '#5A5F6E'; c.fillText('TICK-VOLUME PROFILE', w - 190, 14)
    }
    // Kronos fan: 1,000 possible paths (160 drawn)
    const px = last.close, step = Math.max(4, (w - 90 - lx) / 30)
    c.lineWidth = .7; fan.forEach(p => { c.strokeStyle = 'rgba(232,84,26,.10)'; c.beginPath(); c.moveTo(lx, Y(px)); p.forEach((v, i) => c.lineTo(lx + (i + 1) * step, Y(px * (1 + v * MARKETS[mkt].vol * .8)))); c.stroke() }); c.lineWidth = 1
    c.fillStyle = 'rgba(232,84,26,.9)'; c.font = '10px JetBrains Mono'; c.fillText('KRONOS · 1,000 POSSIBLE PATHS', lx + 8, Y(px) - 60)
  }
  const pnl = price ? (price - MARKETS['XAU/USD'].px * .9994) * 10 : 0
  return <div className="page">
    <div className="row" style={{ marginBottom: 10 }}>{Object.keys(MARKETS).map(m => <button key={m} onClick={() => setMkt(m)} style={{ borderColor: mkt === m ? 'var(--orange)' : undefined }} className="mono">{m}</button>)}
      <span className="num" style={{ marginLeft: 'auto', fontSize: 22 }}>{price ? fmt(price, MARKETS[mkt].dp) : '—'}</span>{killed && <span className="chip r" style={{ borderColor: '#5A2028' }}>TRADING LOCKED</span>}</div>
    <div className="grid" style={{ gridTemplateColumns: '1fr 300px' }}>
      <div className="panel" style={{ height: 560, position: 'relative' }}><div ref={box} style={{ position: 'absolute', inset: 0 }} /><div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}><Canvas draw={draw} /></div></div>
      <div className="grid" style={{ alignContent: 'start' }}>
        <div className="panel"><Head t="ACCOUNT · PAPER" /><div className="pb">{[['EQUITY', '£10,000.00'], ["TODAY'S P&L", `${pnl >= 0 ? '+' : ''}£${pnl.toFixed(2)}`], ['RISK USED TODAY', '1.0% of 3%']].map(([l, v]) => <div key={l} style={{ marginBottom: 10 }}><div className="lbl">{l}</div><div className={`big ${l.includes('P&L') ? (pnl >= 0 ? 'g' : 'r') : ''}`} style={{ fontSize: 20 }}>{v}</div></div>)}<div className="bar"><i style={{ width: '33%', background: 'var(--amber)' }} /></div></div></div>
        <div className="panel"><Head t="OPEN POSITIONS" /><table><tbody><tr><td>XAU/USD</td><td className="g">BUY 0.10</td><td className={pnl >= 0 ? 'g' : 'r'}>{pnl >= 0 ? '+' : ''}£{pnl.toFixed(2)}</td></tr></tbody></table></div>
        <div className="panel"><Head t="ORDERS" /><table><tbody><tr><td>STOP</td><td className="r">{fmt(MARKETS['XAU/USD'].px * .9981, 2)}</td><td className="lo">at broker</td></tr><tr><td>TARGET</td><td className="g">{fmt(MARKETS['XAU/USD'].px * 1.0016, 2)}</td><td className="lo">at broker</td></tr></tbody></table></div>
      </div>
    </div>
    <div className="panel" style={{ marginTop: 12 }}><Head t="TRADE HISTORY" s="paper"><button style={{ padding: '3px 8px', fontSize: 10 }}>Export CSV</button></Head><table><thead><tr>{['Time', 'Market', 'Side', 'Strategy', 'Entry', 'Exit', 'Result'].map(h => <th key={h}>{h}</th>)}</tr></thead>
      <tbody>{[['09:14', 'XAU/USD', 'BUY', 'OF-1 Sweep', '2,641.20', '2,646.10', '+1.6R'], ['10:52', 'BTC/USD', 'SELL', 'VWAP-Rev', '97,880', '97,410', '+1.1R'], ['13:31', 'XAU/USD', 'BUY', 'OF-1 Sweep', '2,644.00', '2,641.70', '−1.0R']].map(r => <tr key={r[0]}>{r.map((x, i) => <td key={i} className={i === 6 ? (x.startsWith('+') ? 'g' : 'r') : ''}>{x}</td>)}</tr>)}</tbody></table></div>
    <RiskWarning />
  </div>
}

const STEPS = ['Scanner', 'News', 'Forecast', 'Entry', 'Time Machine', 'Size', 'Risk', 'Execute', 'Exit']
export function TradeCard() {
  const [step, setStep] = useState(0); const [t, setT] = useState(0); const auto = useS(s => s.auto); const set = useS(s => s.set); const [approved, setApproved] = useState(false)
  useEffect(() => { setT(0); const i = setInterval(() => setT(x => x + .05), 50); return () => clearInterval(i) }, [step])
  useEffect(() => { const dur = [3.2, 2.4, 2.6, 2.4, 4.4, 2, 2.6, 2.6, 3.4][step]; if (t > dur && (step !== 7 || auto || approved)) setStep(s => (s + 1) % STEPS.length) }, [t])
  const scanned = Math.min(5900, Math.floor(t / 3 * 5900))
  const tm = Math.min(10000, Math.floor(t / 2.6 * 10000)); const paths = useMemo(() => Array.from({ length: 140 }, (_, k) => { let y = 0, a = k * 31 + 7; const pts: number[] = []; let end = 0
    for (let i = 0; i < 60; i++) { a = (a * 1103515245 + 12345) & 0x7fffffff; y += (a / 0x7fffffff - .5) * 2.2; pts.push(y); if (!end && (y > 10 || y < -7)) end = y > 10 ? 1 : -1 } return { pts, end } }), [])
  const tmDraw = (c: CanvasRenderingContext2D, w: number, h: number) => { c.clearRect(0, 0, w, h); const Y = (v: number) => h / 2 - v * h / 26; c.strokeStyle = '#78D880'; c.setLineDash([5, 4]); c.beginPath(); c.moveTo(0, Y(10)); c.lineTo(w, Y(10)); c.stroke(); c.strokeStyle = '#E04858'; c.beginPath(); c.moveTo(0, Y(-7)); c.lineTo(w, Y(-7)); c.stroke(); c.setLineDash([])
    const n = Math.floor(paths.length * Math.min(1, tm / 10000)); paths.slice(0, n).forEach(p => { c.strokeStyle = p.end > 0 ? 'rgba(120,216,128,.35)' : p.end < 0 ? 'rgba(224,72,88,.35)' : 'rgba(90,140,255,.35)'; c.beginPath(); p.pts.forEach((v, i) => { const x = i / 59 * w, y = Y(Math.max(-7, Math.min(10, v))); i ? c.lineTo(x, y) : c.moveTo(x, y) }); c.stroke() })
    c.fillStyle = '#78D880'; c.font = '10px JetBrains Mono'; c.fillText('TARGET', 6, Y(10) - 4); c.fillStyle = '#E04858'; c.fillText('STOP', 6, Y(-7) + 12) }
  const fanDraw = (c: CanvasRenderingContext2D, w: number, h: number) => { c.clearRect(0, 0, w, h); const x0 = w * .4; c.strokeStyle = '#E8E8EC'; c.beginPath(); for (let i = 0; i <= 40; i++) { const x = i / 40 * x0, y = h * .6 - Math.sin(i * .3) * 10 - i * .8; i ? c.lineTo(x, y) : c.moveTo(x, y) } c.stroke()
    const y0 = h * .6 - Math.sin(12) * 10 - 32; const u = Math.min(1, t / 1.6); paths.forEach((p, k) => { c.strokeStyle = `rgba(232,${84 + k % 60},26,.18)`; c.beginPath(); c.moveTo(x0, y0); p.pts.slice(0, Math.floor(60 * u)).forEach((v, i) => c.lineTo(x0 + (i + 1) / 60 * (w - x0 - 10), y0 - v * 3 - i * .15)); c.stroke() })
    c.fillStyle = '#C890FF'; c.beginPath(); c.arc(x0, y0, 4, 0, 7); c.fill(); c.fillStyle = '#E8541A'; c.font = '10px JetBrains Mono'; c.fillText('1,000 POSSIBLE PATHS · 61% AGREE (DEMO)', x0 + 10, 16) }
  const Card = ({ i, title, children }: any) => <div className="panel" style={{ padding: 14, opacity: step >= i ? 1 : .35, borderColor: step === i ? 'var(--orange)' : undefined, transition: 'opacity .4s var(--ease), border-color .4s' }}><div className="lbl" style={{ marginBottom: 8 }}>{step > i ? <span className="g">✓ </span> : null}{title}</div>{children}</div>
  return <div className="page">
    <div className="row" style={{ alignItems: 'flex-start' }}><div><div className="ptitle">Trade Card · XAU/USD long</div><div className="psub">Every trade walks the same nine steps. DEMO / ILLUSTRATIVE: the numbers here come from the simulator.</div></div>
      <div className="row" style={{ marginLeft: 'auto' }}><span className="lbl">MODE</span>{['Auto', 'Manual'].map(m => <button key={m} onClick={() => set({ auto: m === 'Auto' })} style={{ borderColor: (m === 'Auto') === auto ? 'var(--orange)' : undefined }}>{m}</button>)}</div></div>
    <div className="row" style={{ gap: 0, marginBottom: 14, flexWrap: 'wrap' }}>{STEPS.map((s, i) => <div key={s} className="row" style={{ gap: 0 }}><span onClick={() => setStep(i)} className="pill" style={{ cursor: 'pointer', background: i === step ? 'var(--orange)' : 'transparent', borderColor: i <= step ? 'var(--orange)' : 'var(--line)', color: i === step ? '#fff' : i < step ? 'var(--hi)' : 'var(--lo)' }}>{i < step ? '✓ ' : ''}{s}</span>{i < STEPS.length - 1 && <i style={{ width: 14, height: 1, background: i < step ? 'var(--orange)' : 'var(--line)' }} />}</div>)}</div>
    <div className="grid" style={{ gridTemplateColumns: 'repeat(3,1fr)' }}>
      <Card i={0} title="SCANNER"><div className="num" style={{ fontSize: 26 }}>{fmt(step > 0 ? 5900 : scanned)}</div><div className="lo">markets scanned for setups</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(16,1fr)', gap: 2, margin: '8px 0' }}>{Array.from({ length: 64 }, (_, k) => <i key={k} style={{ height: 10, background: k === 37 && (step > 0 || t > 2) ? 'var(--orange)' : '#141520' }} />)}</div>
        {(step > 0 || t > 2) && <div className="row" style={{ gap: 6 }}><span className="chip o" style={{ borderColor: '#5A2A14' }}>XAU/USD · sweep-and-reclaim</span><span className="chip lo" style={{ borderColor: 'var(--line)' }}>BTC · VWAP</span></div>}</Card>
      <Card i={1} title="NEWS / EVENTS"><div className="panel" style={{ padding: 8, marginBottom: 6 }}><span className="chip r" style={{ borderColor: '#5A2028' }}>HIGH IMPACT</span> <span style={{ fontSize: 12 }}>US CPI in 2h 14m: outside the ±15 min blackout ✓</span></div>
        <div className="panel" style={{ padding: 8 }}><span className="chip c" style={{ borderColor: '#14505A' }}>GOD'S EYE</span> <span style={{ fontSize: 12 }}>No risk action on gold</span></div></Card>
      <Card i={2} title="FORECAST · KRONOS"><div style={{ height: 120 }}>{step >= 2 && <Canvas draw={fanDraw} />}</div></Card>
      <Card i={3} title="ENTRY TRIGGER"><div className="mono" style={{ fontSize: 14 }}>{step > 3 || (step === 3 && t > 1.4) ? <span className="g">✓ Triggered</span> : <span className="a">◉ Waiting</span>}</div>
        <div className="lo" style={{ fontSize: 11.5, marginTop: 6 }}>Swept 2,641.0 and closed back inside value on the 3m bar · aggressive buying at the level</div>
        <div style={{ position: 'relative', height: 70, marginTop: 8, background: '#06060B' }}><i style={{ position: 'absolute', left: 0, right: 0, top: 6, height: 22, background: 'rgba(120,216,128,.15)' }} /><i style={{ position: 'absolute', left: 0, right: 0, top: 46, height: 18, background: 'rgba(224,72,88,.15)' }} /><i style={{ position: 'absolute', left: 0, right: 0, top: 38, borderTop: '1px dashed var(--orange)' }} />
          <span className="mono g" style={{ position: 'absolute', right: 6, top: 8, fontSize: 9 }}>TAKE PROFIT</span><span className="mono o" style={{ position: 'absolute', right: 6, top: 28, fontSize: 9 }}>ENTRY</span><span className="mono r" style={{ position: 'absolute', right: 6, top: 50, fontSize: 9 }}>STOP · 1× RISK</span></div></Card>
      <Card i={4} title="TIME MACHINE"><div className="num" style={{ fontSize: 26, background: 'linear-gradient(90deg,#E8541A,#E8A850)', WebkitBackgroundClip: 'text', color: 'transparent' }}>{fmt(step > 4 ? 10000 : step === 4 ? tm : 0)}</div><div className="lo">replays of the rest of the session</div>
        <div style={{ height: 100, marginTop: 6 }}>{step >= 4 && <Canvas draw={tmDraw} />}</div>
        {(step > 4 || tm >= 10000) && <><div style={{ display: 'flex', height: 10, marginTop: 6 }}><i style={{ flex: 29.4, background: '#78D880' }} /><i style={{ flex: 25.5, background: '#E04858' }} /><i style={{ flex: 45.1, background: '#5A8CFF' }} /></div>
          <div className="row mono" style={{ fontSize: 10, justifyContent: 'space-between' }}><span className="g">29.4% target first</span><span className="r">25.5% stop first</span><span style={{ color: '#5A8CFF' }}>45.1% open</span></div></>}</Card>
      <Card i={5} title="SIZE">{[['Max loss per trade', '£100.00', 'rgba(248,160,192,.12)'], ['Risk per unit', '£5.00 / 0.1 oz', 'transparent'], ['Position size', '0.20 lots (rounded down)', 'rgba(200,144,255,.12)']].map(([l, v, bg]) => <div key={l} className="row" style={{ justifyContent: 'space-between', padding: '6px 8px', background: bg, marginBottom: 4 }}><span>{l}</span><span className="num">{v}</span></div>)}</Card>
      <Card i={6} title="RISK GATE">{['Max loss per trade', 'Daily loss limit', 'Trades per day', 'Exposure', 'News blackout'].map((r, k) => <div key={r} className="row" style={{ justifyContent: 'space-between', padding: '4px 0' }}><span>{r}</span><span className={step > 6 || (step === 6 && t > k * .4) ? 'g' : 'lo'}>{step > 6 || (step === 6 && t > k * .4) ? '✓' : '…'}</span></div>)}</Card>
      <Card i={7} title="ORDER TICKET"><div style={{ fontSize: 15 }}>BUY XAU/USD · bracket order</div><div className="row" style={{ gap: 6, margin: '8px 0' }}><span className="chip g" style={{ borderColor: '#2A5A30' }}>risk check passed</span><span className="chip g" style={{ borderColor: '#2A5A30' }}>stop + target attached</span></div>
        <div className="row"><span style={{ fontSize: 26 }}>{step > 7 || (step === 7 && (auto ? t > 1 : approved)) ? '🔓' : '🔒'}</span>
          {step > 7 || (step === 7 && (auto ? t > 1.4 : approved)) ? <span className="mono g" style={{ fontSize: 18, letterSpacing: '.1em' }}>SENT ✓</span> : !auto && step === 7 ? <button className="primary" onClick={() => setApproved(true)}>Approve</button> : <span className="lo">{auto ? 'auto mode: sends itself after the risk gate' : 'manual: waits for you (60 s, then skip)'}</span>}</div></Card>
      <Card i={8} title="EXIT"><div className={`big ${step === 8 ? 'g' : ''}`}>{step === 8 ? `+£${(t / 3.4 * 168).toFixed(2)}` : '—'}</div><div className="lo" style={{ fontSize: 11.5 }}>scale out 50% at 1R · stop to breakeven · then target · DEMO</div>
        {step === 8 && t > 2.6 && <div className="mono g" style={{ marginTop: 6 }}>CLOSED +1.7R ✓ · journal written · alert sent</div>}</Card>
    </div>
    <div className="panel" style={{ marginTop: 12 }}><Head t="DEBATE" s="analyst → bull vs bear → risk → trader (TradingAgents pattern)" /><div className="pb" style={{ fontSize: 12, lineHeight: 1.7 }}>
      <div><span className="c mono">ANALYST</span> Balanced day, price at value-area low, aggressive buyers absorbing. CPI later; outside blackout.</div><div><span className="g mono">BULL</span> Sweep-and-reclaim at a mapped level, POC 0.4% above: clean 1.6R.</div>
      <div><span className="r mono">BEAR</span> Dollar firm into CPI; a second sweep is possible.</div><div><span className="a mono">RISK</span> 1% risk, 1 of 5 trades today, exposure fine.</div><div><span className="o mono">TRADER</span> Take it at half size until 1R, then manage.</div></div></div>
  </div>
}

export function Decisions() { return <div className="page"><div className="ptitle">Decisions</div><div className="psub">Everything that needs you: strategies going to paper or live, skill proposals, and trades waiting in Manual mode.</div><div style={{ maxWidth: 640 }}><DecisionCards /></div></div> }

export function PaperLive() {
  const [phrase, setPhrase] = useState('')
  const checks: [string, boolean][] = [['Paper period met (21 days and 30 trades): day 9, 14 trades', false], ['Paper results inside the Lab\'s expected range', true], ['Broker connected with a trade-only key', true], ['Withdrawals OFF on the key', true], ['Risk limits confirmed', true], ['You typed: "I understand I can lose money"', phrase === 'I understand I can lose money']]
  return <div className="page"><div className="ptitle">Paper & Live</div><div className="psub">Paper first, always. Live unlocks only when every box below is ticked, and starts at 50% size for the first two weeks.</div>
    <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', marginBottom: 12 }}>{[['PAPER', '+6.4R', '14 trades · 57% win · DEMO', 'g'], ['LIVE', '—', 'locked', 'lo']].map(([t, v, s, c]) => <div key={t} className="panel"><Head t={t} /><div className="pb"><div className={`big ${c}`} style={{ fontSize: 32 }}>{v}</div><div className="lo">{s}</div></div></div>)}</div>
    <div className="panel" style={{ maxWidth: 700 }}><Head t="GO LIVE CHECKLIST" /><div className="pb">{checks.map(([l, ok]) => <div key={l} className="row" style={{ padding: '6px 0' }}><span className={ok ? 'g' : 'lo'}>{ok ? '✓' : '○'}</span>{l}</div>)}
      <input value={phrase} onChange={e => setPhrase(e.target.value)} placeholder='Type "I understand I can lose money"' style={{ width: '100%', margin: '10px 0' }} /><button className="primary" disabled={!checks.every(c => c[1])} style={{ opacity: checks.every(c => c[1]) ? 1 : .4 }}>Go live</button><RiskWarning /></div></div></div>
}
