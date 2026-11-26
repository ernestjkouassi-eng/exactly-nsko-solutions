import { useEffect, useMemo, useState } from 'react'
import { useS, notify } from '../store'
import { approveTrade, checklist, goLive, withdrawHelper, withdrawAction, openExternal, type Checklist, type Withdraw as W } from '../api'
import { Canvas } from '../viz/canvas'
import { Head, fmt } from '../shell/Shell'
import { DecisionCards } from './Overview'

const RISK_WARN = 'Trading leveraged products like CFDs and spread bets carries a high risk of losing money rapidly. Most retail investor accounts lose money. Only trade with money you can afford to lose. NSKO QUANT is software, not financial advice. Past and simulated results do not guarantee future results.'
export const RiskWarning = () => <div className="lo" style={{ fontSize: 10, lineHeight: 1.5, padding: '10px 0' }}>{RISK_WARN}</div>

const STEPS = ['Scanner', 'News', 'Forecast', 'Entry', 'Time Machine', 'Size', 'Risk', 'Execute', 'Exit']
export function TradeCard() {
  const [step, setStep] = useState(0); const [t, setT] = useState(0); const auto = useS(s => s.auto); const set = useS(s => s.set); const [approved, setApproved] = useState(false); const [busy, setBusy] = useState(false)
  const planId = useS(s => s.decisions.find(d => d.planId)?.planId) || 'demo-xau-long'
  const approve = async () => { setBusy(true); const r = await approveTrade(planId); setBusy(false)
    if (r.ok) { setApproved(true); if (!r.demo) notify(`Approved · order ${r.data.order_id || 'sent'}`, 'good') } else notify(`Not approved: ${r.error}`, 'bad') }
  useEffect(() => { if (step === 0) setApproved(false) }, [step])
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
          {step > 7 || (step === 7 && (auto ? t > 1.4 : approved)) ? <span className="mono g" style={{ fontSize: 18, letterSpacing: '.1em' }}>SENT ✓</span> : !auto && step === 7 ? <button className="primary" disabled={busy} onClick={approve}>{busy ? 'Sending…' : 'Approve'}</button> : <span className="lo">{auto ? 'auto mode: sends itself after the risk gate' : 'manual: waits for you (60 s, then skip)'}</span>}</div></Card>
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
  const [phrase, setPhrase] = useState(''); const [c, setC] = useState<Checklist | null>(null); const [demo, setDemo] = useState(true); const [msg, setMsg] = useState('')
  useEffect(() => { checklist().then(r => { if (r.ok) { setC(r.data); setDemo(r.demo) } }) }, [])
  if (!c) return <div className="page"><div className="ptitle">Paper & Live</div><div className="lo">Loading the checklist…</div></div>
  const checks: [string, boolean][] = [...c.items.map(i => [i.label, i.ok] as [string, boolean]), [`You typed: "${c.phrase}"`, phrase === c.phrase]]
  const ready = checks.every(x => x[1])
  const go = async () => { const r = await goLive(phrase); setMsg(r.ok && r.data.ok ? 'Live is on, at 50% size for the first two weeks.' : (r.error || r.data.message || 'Live stays locked.')) }
  return <div className="page"><div className="ptitle">Paper & Live</div><div className="psub">Paper first, always. Live unlocks only when every box below is ticked, and starts at 50% size for the first two weeks.</div>
    <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', marginBottom: 12 }}>{[['PAPER', `${c.paper.r >= 0 ? '+' : ''}${c.paper.r.toFixed(1)}R`, `${c.paper.trades} trades · ${c.paper.win}% win · day ${c.paper.days}${demo ? ' · DEMO' : ''}`, 'g'], ['LIVE', c.live_unlocked ? 'ON' : '—', c.live_unlocked ? 'unlocked' : 'locked', 'lo']].map(([t, v, s, cl]) => <div key={t} className="panel"><Head t={t} /><div className="pb"><div className={`big ${cl}`} style={{ fontSize: 32 }}>{v}</div><div className="lo">{s}</div></div></div>)}</div>
    <div className="panel" style={{ maxWidth: 700 }}><Head t="GO LIVE CHECKLIST" s={demo ? 'demo checklist' : 'from the engine'} /><div className="pb">{checks.map(([l, ok]) => <div key={l} className="row" style={{ padding: '6px 0' }}><span className={ok ? 'g' : 'lo'}>{ok ? '✓' : '○'}</span>{l}</div>)}
      <input value={phrase} onChange={e => setPhrase(e.target.value)} placeholder={`Type "${c.phrase}"`} style={{ width: '100%', margin: '10px 0' }} /><button className="primary" disabled={!ready} onClick={go} style={{ opacity: ready ? 1 : .4 }}>Go live</button>
      {msg && <div className="mono a" style={{ fontSize: 11, marginTop: 8 }}>{msg}</div>}<RiskWarning /></div></div></div>
}

// ---------------- Money → Withdraw (section 9.7): take money out without the engine fighting you.
const money = (n: number, cur = 'GBP') => n.toLocaleString('en-GB', { style: 'currency', currency: cur })
export function Withdraw() {
  const [w, setW] = useState<W | null>(null); const [demo, setDemo] = useState(true); const [busy, setBusy] = useState(''); const [closeAll, setCloseAll] = useState(false)
  const [done, setDone] = useState<Record<string, boolean>>({}); const [rescaled, setRescaled] = useState('')
  const load = () => withdrawHelper().then(r => { if (r.ok) { setW(r.data); setDemo(r.demo); setDone(d => ({ ...d, pause: d.pause || r.data.trading_paused })) } else notify(r.error || 'Could not load the withdraw helper', 'bad') })
  useEffect(() => { load() }, [])
  const act = async (a: 'pause' | 'close_positions' | 'rescale' | 'resume') => {
    setBusy(a); const r = await withdrawAction(a); setBusy('')
    if (!r.ok) { notify(r.error || 'The engine refused that step', 'bad'); return }
    setW(x => x ? { ...x, ...r.data } as W : x); setDone(d => ({ ...d, [a]: true }))
    if (a === 'pause') useS.getState().set({ paused: true })
    if (a === 'resume') useS.getState().set({ paused: false })
    if (a === 'rescale') setRescaled(r.data.message || (r.data.new_equity ? `Sizes now based on ${money(r.data.new_equity, w?.currency)}` : 'Sizes rescaled'))
    if (!r.demo && a !== 'rescale') load()
  }
  if (!w) return <div className="page"><div className="ptitle">Withdraw</div><div className="lo">Loading…</div></div>
  const paused = !!done.pause || w.trading_paused, closed = !!done.close_positions || w.open_positions.length === 0
  const Step = ({ n, t, ok, children }: { n: number; t: string; ok: boolean; children: any }) => <div className="panel" style={{ padding: 16, borderLeft: `2px solid ${ok ? 'var(--green)' : 'var(--line)'}` }}>
    <div className="row"><span className="num lo" style={{ fontSize: 11 }}>0{n}</span><span className="lbl" style={{ color: 'var(--hi)' }}>{t}</span>{ok && <span className="chip g" style={{ borderColor: '#2A5A30', marginLeft: 'auto' }}>DONE ✓</span>}</div><div style={{ marginTop: 10 }}>{children}</div></div>
  return <div className="page">
    <div className="row" style={{ alignItems: 'flex-start' }}><div><div className="ptitle">Withdraw</div><div className="psub">Your money is in your own broker account, and only you can withdraw it: NSKO QUANT's key has no withdrawal permission. This helper makes it safe: it pauses new trades, frees the cash, opens your broker's page, then rescales position sizes to the new balance.</div></div>
      {demo && <span className="chip a" style={{ borderColor: '#5A4020', marginLeft: 'auto' }}>DEMO · nothing is sent to a broker</span>}</div>
    <div className="panel" style={{ display: 'flex', marginBottom: 12 }}>{[['BROKER', w.broker, ''], ['EQUITY', money(w.equity, w.currency), ''], ['MARGIN IN USE', money(w.margin_used, w.currency), w.margin_used ? 'a' : ''], ['OPEN POSITIONS', String(w.open_positions.length), ''], ['FREE TO WITHDRAW', money(w.free, w.currency), 'g']].map(([l, v, c]) =>
      <div key={l} style={{ flex: 1, padding: 14, borderRight: '1px solid var(--line)' }}><div className="lbl">{l}</div><div className={`big ${c}`} style={{ fontSize: l === 'BROKER' ? 15 : 22, marginTop: 4 }}>{v}</div></div>)}</div>
    <div className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
      <Step n={1} t="Pause new trades" ok={paused}><div className="lo" style={{ fontSize: 12, marginBottom: 10 }}>Open trades keep their stops and targets at the broker. Nothing new opens until you resume.</div>
        <button className="primary" disabled={paused || !!busy} onClick={() => act('pause')}>{busy === 'pause' ? 'Pausing…' : paused ? 'Paused' : 'Pause new trades'}</button></Step>
      <Step n={2} t="Close positions (optional)" ok={closed}><div className="lo" style={{ fontSize: 12, marginBottom: 8 }}>Only if you want to withdraw the margin too. Positions close at market.</div>
        {w.open_positions.length > 0 && <table style={{ marginBottom: 10 }}><tbody>{w.open_positions.map(p => <tr key={p.market}><td>{p.market}</td><td className={p.side === 'BUY' ? 'g' : 'r'}>{p.side} {p.qty}</td><td className={p.pnl >= 0 ? 'g' : 'r'}>{p.pnl >= 0 ? '+' : ''}{money(p.pnl, w.currency)}</td></tr>)}</tbody></table>}
        <label className="row" style={{ fontSize: 12, marginBottom: 8 }}><input type="checkbox" checked={closeAll} onChange={e => setCloseAll(e.target.checked)} disabled={closed} />Yes, close all {w.open_positions.length} open position{w.open_positions.length === 1 ? '' : 's'}</label>
        <button disabled={!closeAll || closed || !paused || !!busy} onClick={() => act('close_positions')}>{busy === 'close_positions' ? 'Closing…' : closed ? 'No open positions' : 'Close positions'}</button></Step>
      <Step n={3} t="Withdraw at your broker" ok={!!done.opened}><div style={{ fontSize: 12, marginBottom: 6 }}>Free to withdraw now: <span className="num g" style={{ fontSize: 16 }}>{money(w.free, w.currency)}</span></div>
        <div className="lo" style={{ fontSize: 12, marginBottom: 10 }}>Log in at {w.broker} in your browser and withdraw to your own bank. NSKO QUANT never sees your bank details.</div>
        <button className="primary" disabled={!paused} onClick={() => { openExternal(w.withdraw_url); setDone(d => ({ ...d, opened: true })) }}>Open {w.broker.replace(/ \(demo\)$/, '')} withdrawal page ↗</button></Step>
      <Step n={4} t="Rescale and resume" ok={!!done.rescale}><div className="lo" style={{ fontSize: 12, marginBottom: 10 }}>After the money has left, the engine re-reads your balance and sizes every new trade from it (1% of the new equity), then resumes.</div>
        <div className="row"><button className="primary" disabled={!done.opened || !!busy} onClick={async () => { await act('rescale'); await act('resume') }}>{busy === 'rescale' || busy === 'resume' ? 'Rescaling…' : 'I have withdrawn · rescale and resume'}</button></div>
        {rescaled && <div className="mono g" style={{ fontSize: 11, marginTop: 8 }}>✓ {rescaled}</div>}</Step>
    </div>
    <RiskWarning />
  </div>
}
