import { useEffect, useRef, useState } from 'react'
import { useS } from '../store'
import { VERB_COL, reducedMotion } from '../tokens'

export const Wordmark = ({ size = 13 }: { size?: number }) => (
  <span className="mono" style={{ fontSize: size, letterSpacing: '.14em', fontWeight: 600 }}><span className="o">NSKO</span> <span className="lo">//</span> QUANT</span>
)
export const Demo = () => useS(s => s.demo) ? <span className="chip" style={{ color: 'var(--amber)', borderColor: '#5A4020' }}>DEMO DATA</span> : null
export const fmt = (n: number, d = 0) => n.toLocaleString('en-GB', { minimumFractionDigits: d, maximumFractionDigits: d })

function Clock() {
  const [t, setT] = useState(new Date())
  useEffect(() => { const i = setInterval(() => setT(new Date()), 1000); return () => clearInterval(i) }, [])
  return <span className="num" style={{ fontSize: 22, letterSpacing: '.04em' }}>{t.toLocaleTimeString('en-GB', { timeZone: 'Europe/London', hour12: false })} <span className="lo" style={{ fontSize: 11 }}>GMT</span></span>
}

function KillSwitch() {
  const [p, setP] = useState(0); const raf = useRef(0); const killed = useS(s => s.killed)
  const start = () => { const t0 = performance.now(); const f = () => { const v = Math.min(1, (performance.now() - t0) / 1500); setP(v); if (v >= 1) { useS.getState().set({ killed: true }); setP(0); return } raf.current = requestAnimationFrame(f) }; raf.current = requestAnimationFrame(f) }
  const stop = () => { cancelAnimationFrame(raf.current); setP(0) }
  if (killed) return <button onClick={() => useS.getState().set({ killed: false })} style={{ borderColor: 'var(--red)', color: 'var(--red)' }} className="mono">TRADING LOCKED · re-enable</button>
  return <button onMouseDown={start} onMouseUp={stop} onMouseLeave={stop} title="Hold for 1.5 s: cancels all orders, closes all positions, locks trading"
    style={{ borderColor: 'var(--red)', color: 'var(--red)', position: 'relative', overflow: 'hidden', fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.12em' }}>
    <i style={{ position: 'absolute', inset: 0, width: `${p * 100}%`, background: 'rgba(224,72,88,.25)' }} /><span style={{ position: 'relative' }}>KILL SWITCH · HOLD</span></button>
}

function Ticker() {
  const log = useS(s => s.log); const ref = useRef<HTMLDivElement>(null); const x = useRef(0)
  useEffect(() => {
    if (reducedMotion()) return
    let raf = 0, last = performance.now()
    const f = (now: number) => { x.current -= (now - last) * .04; last = now; const el = ref.current; if (el) { if (-x.current > el.scrollWidth / 2) x.current = 0; el.style.transform = `translateX(${x.current}px)` } raf = requestAnimationFrame(f) }
    raf = requestAnimationFrame(f); return () => cancelAnimationFrame(raf)
  }, [])
  const items = log.slice(-24)
  const row = items.map((l, i) => <span key={i} style={{ marginRight: 28 }} className="mono">
    <span className="lo">{new Date(l.ts).toLocaleTimeString('en-GB', { hour12: false })}</span>{' '}
    <span style={{ color: VERB_COL[l.verb] || '#fff' }}>{l.verb}</span> <span style={{ color: '#9A9EAA' }}>{l.msg}</span></span>)
  return <div className="tick-wrap" style={{ fontSize: 11 }}><div ref={ref} style={{ display: 'inline-block', willChange: 'transform' }}>{row}{row}</div></div>
}

export function TopBar({ openJarvis }: { openJarvis: () => void }) {
  const round = useS(s => s.round), budget = useS(s => s.budget), decisions = useS(s => s.decisions), mode = useS(s => s.mode), set = useS(s => s.set)
  return <div style={{ borderBottom: '1px solid var(--line)', background: '#07070D' }}>
    <div className="row" style={{ padding: '8px 14px', gap: 14 }}>
      <button onClick={openJarvis} style={{ padding: '2px 8px' }} title="JARVIS (Ctrl+J)">+</button>
      <Wordmark size={14} />
      <span className="pill"><span className="dot pulse" /> JARVIS running</span>
      <span className="pill"><span className="dot pulse" /> SCOUT reading</span>
      <span className="pill">THINK BUDGET £{budget.used.toFixed(0)} of £{budget.of} · {budget.days} days
        <span className="bar" style={{ width: 60, display: 'inline-block' }}><i style={{ width: `${budget.used / budget.of * 100}%` }} /></span></span>
      <Demo />
      <div style={{ marginLeft: 'auto' }} className="row">
        <div style={{ textAlign: 'right', lineHeight: 1.3 }}><div className="lbl">ROUND <span className="num" style={{ color: 'var(--hi)' }}>{fmt(round)}</span></div>
          <div className="lbl">DECISIONS <span className="num" style={{ color: decisions.length ? 'var(--amber)' : 'var(--hi)' }}>{decisions.length}</span></div></div>
        <span className="pill" style={{ cursor: 'pointer' }} onClick={() => set({ mode: mode === 'PAPER' ? 'PAPER' : 'PAPER' })} title="Live unlocks after the paper checklist">MODE: <b className="o">{mode}</b> <span className="lo">| LIVE 🔒</span></span>
        <KillSwitch />
        <Clock />
      </div>
    </div>
    <div className="row" style={{ padding: '5px 14px', borderTop: '1px solid #11121A', gap: 10 }}>
      <span className="mono g" style={{ fontSize: 10 }}><span className="dot pulse" /> LIVE</span><Ticker />
    </div>
  </div>
}

export const NAV: [string, [string, string, boolean?][]][] = [
  ['OVERVIEW', [['overview', 'Overview']]],
  ['BRAIN', [['lab', 'Lab', true], ['research', 'Research', true], ['strategies', 'Strategies'], ['knowledge', 'Knowledge Base'], ['agents', 'Agent Room'], ['godseye', "God's Eye"]]],
  ['MONEY', [['desk', 'Live Desk'], ['tradecard', 'Trade Card'], ['decisions', 'Decisions'], ['paperlive', 'Paper & Live']]],
  ['SYSTEM', [['brokers', 'Brokers'], ['engine', 'Engine'], ['costs', 'Costs'], ['settings', 'Settings'], ['help', 'Help']]],
]
export function Sidebar({ page, go }: { page: string; go: (p: string) => void }) {
  const decisions = useS(s => s.decisions), round = useS(s => s.round)
  return <div style={{ width: 168, borderRight: '1px solid var(--line)', padding: '12px 0', display: 'flex', flexDirection: 'column', background: '#07070D' }}>
    {NAV.map(([g, items]) => <div key={g} style={{ marginBottom: 14 }}>
      <div className="lbl" style={{ padding: '0 16px 6px' }}>{g}</div>
      {items.map(([id, name, live]) => <div key={id} onClick={() => go(id)} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 16px', cursor: 'pointer', fontSize: 12.5,
        background: page === id ? '#11121B' : 'transparent', borderLeft: `2px solid ${page === id ? 'var(--orange)' : 'transparent'}`, color: page === id ? 'var(--hi)' : '#9A9EAA' }}>
        {name}{live && <span className="dot pulse" style={{ marginLeft: 4 }} />}
        {id === 'decisions' && decisions.length > 0 && <span className="badge">{decisions.length}</span>}
        {id === 'knowledge' && <span className="badge">4</span>}
      </div>)}
    </div>)}
    <div className="lbl" style={{ marginTop: 'auto', padding: '0 16px', lineHeight: 1.6, fontSize: 8.5 }}>NSKO QUANT · by NSKO Solutions<br /><span className="g">●</span> engine online · round {fmt(round)}</div>
  </div>
}

const SCRIPT: [RegExp, string][] = [
  [/gold|xau/i, 'Gold is in a balanced range on the 15m profile: value area high 2,652, low 2,641, POC 2,646 (demo). I would only act at those levels, on a sweep-and-reclaim with aggressive buying. Want me to draft a plan?'],
  [/news|cpi|fed/i, 'Next high-impact release in the demo calendar: US CPI in 2h 14m. The news blackout (±15 min) will block new entries around it.'],
  [/plan|trade/i, 'Draft plan (demo): long XAU/USD at a sweep of 2,641 that closes back inside value. Stop 2,637.8, target POC 2,646 then VAH 2,652. Risk 1% → size from your equity. I will run the Time Machine before anything is sent.'],
  [/risk/i, 'Your limits: 1% per trade, 3% daily stop, 6% weekly, max 5 trades a day, 2 open positions. The risk gate cannot be switched off in live.'],
]
export function Jarvis({ open, close }: { open: boolean; close: () => void }) {
  const [msgs, setMsgs] = useState<{ me: boolean; t: string }[]>([{ me: false, t: 'Good evening. I am JARVIS. Ask me about an idea, the live market, the news, or plan a trade together. (Demo mode: scripted answers.)' }])
  const [v, setV] = useState('')
  const send = () => { if (!v.trim()) return; const a = SCRIPT.find(([r]) => r.test(v))?.[1] || 'Noted. In demo mode I answer from a script; with the engine connected I will research it with SCOUT and come back with sources.'; setMsgs(m => [...m, { me: true, t: v }, { me: false, t: a }]); setV('') }
  return <div style={{ position: 'fixed', top: 0, right: 0, bottom: 0, width: 380, background: '#0A0B12', borderLeft: '1px solid var(--line)', zIndex: 50, transform: `translateX(${open ? 0 : 400}px)`, transition: 'transform .35s var(--ease)', display: 'flex', flexDirection: 'column' }}>
    <div className="ph"><span className="dot pulse" style={{ background: 'var(--orange)' }} /><span className="t">JARVIS</span><span className="s">director · Ctrl+J</span><span className="rt"><button onClick={close}>×</button></span></div>
    <div style={{ flex: 1, overflow: 'auto', padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
      {msgs.map((m, i) => <div key={i} style={{ alignSelf: m.me ? 'flex-end' : 'flex-start', maxWidth: '88%', background: m.me ? '#1A1410' : 'var(--panel)', border: `1px solid ${m.me ? '#3A2414' : 'var(--line)'}`, padding: '8px 11px', borderRadius: 3, lineHeight: 1.5 }}>{m.t}</div>)}
    </div>
    <div className="row" style={{ padding: 12, borderTop: '1px solid var(--line)' }}><input style={{ flex: 1 }} value={v} onChange={e => setV(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()} placeholder="Ask JARVIS…" /><button className="primary" onClick={send}>Send</button></div>
  </div>
}

export const Head = ({ t, s, children }: { t: string; s?: string; children?: any }) =>
  <div className="ph"><span className="t">• {t}</span>{s && <span className="s">— {s}</span>}<span className="rt">{children}</span></div>
export const Corners = () => <>{(['Top', 'Bottom'] as const).flatMap(v => (['Left', 'Right'] as const).map(h =>
  <span key={v + h} className="corner" style={{ [v.toLowerCase()]: 8, [h.toLowerCase()]: 8, borderWidth: 0, [`border${v}Width`]: 1, [`border${h}Width`]: 1 } as any} />))}</>
