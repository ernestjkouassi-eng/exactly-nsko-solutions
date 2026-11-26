import { useState } from 'react'
import { useS } from '../store'
import { Head, Wordmark, fmt } from '../shell/Shell'
import { RiskWarning } from './Money'

const BROKERS = [['Capital.com', 'Gold, indices, FX, crypto CFDs · UK spread betting', 'Demo'], ['IG', 'Gold, indices, FX · UK spread betting', 'Not connected'], ['OANDA', 'FX, gold, indices', 'Not connected'], ['Interactive Brokers', 'Stocks, futures (COMEX gold), FX', 'Not connected'],
  ['Kraken', 'Crypto · real trade volume', 'Not connected'], ['Coinbase Advanced', 'Crypto', 'Not connected'], ['Alpaca', 'US stocks, crypto · free paper account', 'Not connected'], ['MetaTrader 5 bridge', 'Many FX/gold brokers · Windows engine only', 'Not connected']]
export function Brokers() {
  return <div className="page"><div className="ptitle">Brokers</div><div className="psub">Your money stays in your own broker account. NSKO QUANT only holds a key that can trade: switch withdrawals OFF on the key wherever the broker allows it. Each adapter is checked against the broker's current API terms in Stage 4.</div>
    <div className="grid" style={{ gridTemplateColumns: 'repeat(4,1fr)' }}>{BROKERS.map(([n, m, s]) => <div key={n} className="panel" style={{ padding: 14 }}>
      <div className="row" style={{ justifyContent: 'space-between' }}><span style={{ fontSize: 15, fontWeight: 600 }}>{n}</span><span className={`chip ${s === 'Demo' ? 'a' : 'lo'}`} style={{ borderColor: 'var(--line)' }}>{s.toUpperCase()}</span></div>
      <div className="lo" style={{ fontSize: 11.5, margin: '6px 0 10px', minHeight: 30 }}>{m}</div>
      {s === 'Demo' ? <div className="mono" style={{ fontSize: 10.5, lineHeight: 1.7 }}><span className="g">Trading ✓</span> · <span className="g">Withdrawals OFF ✓</span><br /><span className="lo">latency 84 ms · last sync 2s ago</span></div> : <button>Connect</button>}</div>)}</div>
    <div className="panel" style={{ marginTop: 12, padding: 14 }}><span className="r mono">CMC Markets is not supported</span><span className="lo"> · it offers no API access for automated trading.</span></div></div>
}
export function Engine() {
  const h = useS(s => s.health); const round = useS(s => s.round)
  return <div className="page"><div className="ptitle">Engine</div><div className="psub">The background service that trades 24/7 on this computer, even with the window closed, as long as the computer is on and online.</div>
    <div className="panel" style={{ display: 'flex', marginBottom: 12 }}>{[['STATUS', 'RUNNING', 'g'], ['UPTIME', `${Math.floor(round / 3600)}h ${Math.floor(round / 60) % 60}m`, ''], ['KEEP-AWAKE', 'ON', 'g'], ['CPU', `${(h.cpu || 20).toFixed(0)}%`, ''], ['RAM', `${(h.ram || 2.2).toFixed(1)} GB`, ''], ['LAST HEARTBEAT', h.heartbeat ? new Date(h.heartbeat).toLocaleTimeString('en-GB', { hour12: false }) : '—', '']].map(([l, v, c]) =>
      <div key={l} style={{ flex: 1, padding: 14, borderRight: '1px solid var(--line)' }}><div className="lbl">{l}</div><div className={`big ${c}`} style={{ fontSize: 18 }}>{v}</div></div>)}</div>
    <div className="row" style={{ marginBottom: 12 }}><button>Restart engine</button><button>Update engine</button><span className="chip a" style={{ borderColor: '#5A4020' }}>DEMO · the real service arrives in Stage 2</span></div>
    <div className="panel"><Head t="LOGS" s="keys are always redacted" /><div className="pb mono" style={{ fontSize: 11, lineHeight: 1.8 }}>{useS.getState().log.slice(-12).map((l, i) => <div key={i}><span className="lo">{new Date(l.ts).toISOString()}</span> INFO {l.verb.toLowerCase()} {l.msg}</div>)}<div><span className="lo">{new Date().toISOString()}</span> INFO broker capital.com key=****REDACTED**** heartbeat ok</div></div></div></div>
}
export function Costs() {
  const b = useS(s => s.budget)
  return <div className="page"><div className="ptitle">Costs</div><div className="psub">NSKO QUANT runs on free, local tools. The think budget is compute and time on your own computer (the local AI model), not money, unless you bring your own Claude or OpenAI key.</div>
    <div className="grid" style={{ gridTemplateColumns: 'repeat(3,1fr)' }}>{[['THINK BUDGET', `${b.used.toFixed(1)} of ${b.of} units`, `${b.days} days left`], ['LOCAL AI', 'Ollama · small model', '0 £ · runs on this computer'], ['DATA', 'Broker + public feeds', 'free tiers · licences logged']].map(([l, v, s]) => <div key={l} className="panel" style={{ padding: 14 }}><div className="lbl">{l}</div><div style={{ fontSize: 18, margin: '6px 0' }}>{v}</div><div className="lo">{s}</div></div>)}</div></div>
}
export function Settings() {
  const auto = useS(s => s.auto), set = useS(s => s.set); const [upd, setUpd] = useState('Ask me')
  const R = [['Risk per trade', '1%'], ['Daily loss limit', '3% · then stop for the day'], ['Weekly loss limit', '6%'], ['Max trades per day', '5'], ['Max open positions', '2'], ['News blackout', '±15 min'], ['Paper period before live', '21 days and 30 trades'], ['Live start size', '50% for 2 weeks'], ['The bar (Lab)', 'OOS Sharpe ≥ 1.40 after costs']]
  return <div className="page"><div className="ptitle">Settings</div>
    <div className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
      <div className="panel"><Head t="RISK LIMITS" s="hard limits: the gate cannot be switched off in live" /><div className="pb">{R.map(([l, v]) => <div key={l} className="row" style={{ justifyContent: 'space-between', padding: '7px 0', borderBottom: '1px solid #12131B' }}><span>{l}</span><input defaultValue={v} style={{ width: 230, textAlign: 'right' }} /></div>)}</div></div>
      <div className="grid" style={{ alignContent: 'start' }}>
        <div className="panel"><Head t="TRADING" /><div className="pb row">{['Auto', 'Manual'].map(m => <button key={m} onClick={() => set({ auto: m === 'Auto' })} style={{ borderColor: (m === 'Auto') === auto ? 'var(--orange)' : undefined }}>{m}</button>)}<span className="lo" style={{ fontSize: 11 }}>Manual waits for Approve at the order ticket</span></div></div>
        <div className="panel"><Head t="STRATEGY UPDATES" /><div className="pb">{['Manual', 'Automatic → paper, then ask me', 'Ask me'].map(m => <label key={m} className="row" style={{ padding: '4px 0', cursor: 'pointer' }}><input type="radio" checked={upd === m} onChange={() => setUpd(m)} />{m}</label>)}<div className="lo" style={{ fontSize: 11, marginTop: 6 }}>NSKO strategy packs always go to the Lab first, never straight to live. Every change can be rolled back in one click.</div></div></div>
        <div className="panel"><Head t="ALERTS" /><div className="pb">{['Phone: ntfy (high priority alarm)', 'Telegram bot · /kill from your paired account', 'Desktop notifications'].map(a => <label key={a} className="row" style={{ padding: '4px 0' }}><input type="checkbox" defaultChecked />{a}</label>)}</div></div>
        <div className="panel"><Head t="DESK" /><div className="pb row"><button>Export my desk</button><button>Restore</button><span className="lo" style={{ fontSize: 11 }}>encrypted · never includes broker keys</span></div></div>
      </div></div></div>
}
export function Help() {
  return <div className="page"><div className="ptitle">Help</div><div className="psub">The full User Guide (PDF) opens here once it is written in Stage 5.</div>
    <div className="panel" style={{ maxWidth: 780 }}>{[['Does NSKO hold my money?', 'No. Your money stays in your own broker account. NSKO QUANT holds a trade-only key and has no withdrawal code at all.'], ['Does it trade when the window is closed?', 'Yes. The engine is a background service with a tray icon. It trades as long as the computer is on and online.'], ['Can I stop everything at once?', 'Yes. Hold the KILL SWITCH for 1.5 s, or send /kill from your paired Telegram account. It cancels orders, closes positions and locks trading.'], ['Is the data on screen real?', 'Not yet. Stage 1 runs on the DEMO DATA simulator, labelled on every screen.']].map(([q, a]) =>
      <div key={q} style={{ padding: 14, borderBottom: '1px solid var(--line)' }}><div style={{ fontWeight: 600, marginBottom: 4 }}>{q}</div><div className="lo" style={{ lineHeight: 1.6 }}>{a}</div></div>)}<div style={{ padding: '0 14px' }}><RiskWarning /></div></div></div>
}

// ---------------- first-run onboarding (7 steps)
export function Onboarding({ done }: { done: () => void }) {
  const [s, setS] = useState(0); const [acct, setAcct] = useState({ name: '', email: '', pw: '', lic: '' })
  const steps = ['Welcome', 'Your account', '24/7 setup', 'Connect broker', 'Risk limits', 'Markets & mode', 'Start on paper']
  const body = [
    <div key={0} style={{ textAlign: 'center', padding: '50px 0' }}><div style={{ animation: 'sting 2.4s var(--ease) both' }}><Wordmark size={34} /></div><div className="lo" style={{ marginTop: 14 }}>by NSKO Solutions</div><div style={{ marginTop: 26, fontSize: 18 }}>Trade the markets. Automatically.</div><RiskWarning /></div>,
    <div key={1} className="grid">{[['name', 'Name'], ['email', 'Email'], ['pw', 'Password'], ['lic', 'Licence key']].map(([k, l]) => <input key={k} type={k === 'pw' ? 'password' : 'text'} placeholder={l} value={(acct as any)[k]} onChange={e => setAcct({ ...acct, [k]: e.target.value })} />)}
      <label className="row"><input type="checkbox" />Add a 6-digit PIN</label><label className="row"><input type="checkbox" />Authenticator app (2FA)</label><div className="lo" style={{ fontSize: 11 }}>Your account lives on this computer only, encrypted. There is no NSKO login server.</div></div>,
    <div key={2}>{['Start NSKO QUANT when the computer turns on', 'Keep the computer awake while the engine is active', 'Plugged in · laptop lid closed = do nothing', 'Phone alerts paired and tested (ntfy / Telegram)'].map(c => <div key={c} className="row" style={{ padding: '7px 0' }}><span className="g">✓</span>{c}</div>)}<div className="lo" style={{ fontSize: 11, marginTop: 8 }}>It trades 24/7 as long as this computer is on and online.</div></div>,
    <div key={3} className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>{BROKERS.slice(0, 4).map(([n]) => <button key={n} style={{ padding: 14, textAlign: 'left' }}>{n}<div className="lo" style={{ fontSize: 11 }}>{n === 'Capital.com' ? 'recommended for gold · demo first' : 'demo account available'}</div></button>)}<div className="lo" style={{ fontSize: 11, gridColumn: '1/-1' }}>Key permissions: trading ON, withdrawals OFF. Optional extras: God's Eye data keys, JARVIS local AI model download.</div></div>,
    <div key={4}>{[['Risk per trade', '1%'], ['Daily loss limit', '3%'], ['Weekly loss limit', '6%'], ['Max trades per day', '5'], ['Max open positions', '2']].map(([l, v]) => <div key={l} className="row" style={{ justifyContent: 'space-between', padding: '6px 0' }}><span>{l}</span><input defaultValue={v} style={{ width: 90, textAlign: 'right' }} /></div>)}</div>,
    <div key={5}><div className="row" style={{ flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>{['XAU/USD', 'BTC/USD', 'ETH/USD', 'US stocks'].map((m, i) => <label key={m} className="pill"><input type="checkbox" defaultChecked={i < 2} />{m}</label>)}</div><div className="row"><button style={{ borderColor: 'var(--orange)' }}>Auto</button><button>Manual</button></div></div>,
    <div key={6} style={{ textAlign: 'center', padding: '30px 0' }}><div className="big o" style={{ fontSize: 30 }}>PAPER</div><div className="lo" style={{ margin: '8px 0 20px' }}>Live stays locked until the paper checklist is met (21 days and 30 trades).</div><button className="primary" onClick={done}>Open my desk</button></div>,
  ]
  return <div style={{ position: 'fixed', inset: 0, background: 'radial-gradient(circle at 50% 30%, #14141E, #08080F 60%)', zIndex: 100, display: 'grid', placeItems: 'center' }}>
    <style>{`@keyframes sting{0%{opacity:0;letter-spacing:.5em;filter:blur(8px)}60%{opacity:1;filter:blur(0)}100%{letter-spacing:.14em}}`}</style>
    <div className="panel" style={{ width: 620, padding: 26 }}>
      <div className="row" style={{ gap: 4, marginBottom: 18 }}>{steps.map((x, i) => <i key={x} style={{ flex: 1, height: 2, background: i <= s ? 'var(--orange)' : 'var(--line)' }} />)}</div>
      <div className="lbl">STEP {s + 1} OF 7 · {steps[s].toUpperCase()}</div><div style={{ minHeight: 280, marginTop: 14 }}>{body[s]}</div>
      <div className="row" style={{ justifyContent: 'space-between' }}><button onClick={() => s ? setS(s - 1) : done()}>{s ? 'Back' : 'Skip (demo)'}</button>{s < 6 && <button className="primary" onClick={() => setS(s + 1)}>Continue</button>}</div>
    </div></div>
}
export { fmt }
