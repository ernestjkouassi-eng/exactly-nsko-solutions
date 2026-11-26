import { useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, Spark, walk } from '../viz/canvas'
import { Head } from '../shell/Shell'

const STRATS = [
  ['Trend-follower XAU', '4h', 'waiting on you', 1.64, 'Approved'], ['OF-1 Sweep XAU', '15m→3m', 'on paper · day 9', 1.52, 'On paper'], ['VWAP-Rev BTC', '5m', 'approved', 2.10, 'Approved'],
  ['ORB NVDA', '5m', 'in review', 1.12, 'In review'], ['Carry XAU', '1d', 'approved', 1.47, 'Approved'], ['Breakout ETH', '1h', 'failed · coin flip', .21, 'Failed'],
  ['Range-XAU 16', '4h', 'thought up', 0, 'Thought up'], ['Momentum BTC', '4h', 'on paper · day 4', 1.58, 'On paper'],
] as const

function eq(seed: number, n = 400, drift = .12) { let a = seed, y = 0, peak = 0; const e: number[] = [], dd: number[] = []; for (let i = 0; i < n; i++) { a = (a * 1103515245 + 12345) & 0x7fffffff; y += (a / 0x7fffffff - .5) * 2.4 + drift; peak = Math.max(peak, y); e.push(y); dd.push(y - peak) } return { e, dd } }

function EquityChart({ seed }: { seed: number }) {
  const { e, dd } = useMemo(() => eq(seed), [seed]); const t0 = useRef(performance.now())
  useEffect(() => { t0.current = performance.now() }, [seed])
  const draw = (c: CanvasRenderingContext2D, w: number, h: number) => {
    c.clearRect(0, 0, w, h); const u = Math.min(1, (performance.now() - t0.current) / 800), n = Math.floor(e.length * u), top = h * .68
    const mx = Math.max(...e), mn = Math.min(0, ...e), md = Math.min(...dd), X = (i: number) => 10 + i / (e.length - 1) * (w - 90), Y = (v: number) => 10 + (1 - (v - mn) / (mx - mn)) * (top - 20)
    const g = c.createLinearGradient(0, 0, 0, top); g.addColorStop(0, 'rgba(120,216,128,.35)'); g.addColorStop(1, 'rgba(120,216,128,0)')
    c.beginPath(); c.moveTo(X(0), top); for (let i = 0; i < n; i++) c.lineTo(X(i), Y(e[i])); c.lineTo(X(n - 1), top); c.fillStyle = g; c.fill()
    c.beginPath(); for (let i = 0; i < n; i++) i ? c.lineTo(X(i), Y(e[i])) : c.moveTo(X(i), Y(e[i])); c.strokeStyle = '#78D880'; c.lineWidth = 1.5; c.stroke()
    const DY = (v: number) => top + 14 + (v / md) * (h - top - 24)
    c.beginPath(); c.moveTo(X(0), top + 14); for (let i = 0; i < n; i++) c.lineTo(X(i), DY(dd[i])); c.lineTo(X(n - 1), top + 14); c.fillStyle = 'rgba(224,72,88,.45)'; c.fill()
    if (n > 1) { c.fillStyle = '#78D880'; c.fillRect(X(n - 1) + 6, Y(e[n - 1]) - 9, 66, 18); c.fillStyle = '#08080F'; c.font = '11px JetBrains Mono'; c.fillText(`+${e[n - 1].toFixed(1)}R`, X(n - 1) + 10, Y(e[n - 1]) + 4) }
    c.fillStyle = '#5A5F6E'; c.font = '9px JetBrains Mono'; c.fillText(`DRAWDOWN · MAX ${md.toFixed(1)}R`, 12, top + 10)
  }
  return <div style={{ height: 300 }}><Canvas draw={draw} /></div>
}

export function Strategies() {
  const [tab, setTab] = useState('Approved'); const [sel, setSel] = useState(0); const [q, setQ] = useState('')
  const list = STRATS.map((s, i) => ({ s, i })).filter(({ s }) => (tab === 'all' || s[4] === tab || (tab === 'Thought up')) && s[0].toLowerCase().includes(q.toLowerCase()))
  const s = STRATS[sel]
  return <div className="page">
    <div className="ptitle">Strategy Book</div><div className="psub">Every test is here, even the failures.</div>
    <div className="row" style={{ marginBottom: 12 }}>{[['Thought up', '1,308'], ['Approved', '12'], ['On paper', '3'], ['In review', '32'], ['Failed', '1,217']].map(([t, n]) =>
      <button key={t} onClick={() => setTab(t)} style={{ borderColor: tab === t ? 'var(--orange)' : undefined }}>{t} <span className="lo num">{n}</span></button>)}
      <input placeholder="Search strategies" value={q} onChange={e => setQ(e.target.value)} style={{ marginLeft: 'auto', width: 220 }} /></div>
    <div className="grid" style={{ gridTemplateColumns: '280px 1fr' }}>
      <div className="panel">{list.map(({ s, i }) => <div key={i} onClick={() => setSel(i)} style={{ padding: '10px 12px', borderBottom: '1px solid var(--line)', cursor: 'pointer', background: sel === i ? '#11121B' : undefined, borderLeft: `2px solid ${sel === i ? 'var(--orange)' : 'transparent'}` }}>
        <div className="row" style={{ justifyContent: 'space-between' }}><span>{s[0]}</span><span className="num" style={{ color: s[3] >= 1.4 ? 'var(--green)' : 'var(--lo)' }}>{s[3] ? s[3].toFixed(2) : '—'}</span></div>
        <div className="row" style={{ justifyContent: 'space-between' }}><span className="lo mono" style={{ fontSize: 10 }}>{s[1]} · {s[2]}</span><Spark data={walk(i + 3, 24, s[3] / 30)} w={60} h={16} color={s[3] >= 1.4 ? '#78D880' : '#5A5F6E'} /></div>
        <div style={{ display: 'flex', gap: 2, marginTop: 5 }}>{[0, 1, 2, 3, 4].map(k => <i key={k} style={{ flex: 1, height: 3, background: k < Math.round(s[3] * 2.4) ? (k === 3 && i % 3 === 0 ? '#E04858' : '#78D880') : '#1A1C26' }} />)}</div></div>)}</div>
      <div className="panel"><div className="pb">
        <span className="chip" style={{ color: s[4] === 'Failed' ? 'var(--red)' : 'var(--green)', borderColor: '#2A5A30' }}>{s[4].toUpperCase()}</span>
        <div className="row" style={{ marginTop: 8 }}><div><div style={{ fontSize: 22 }}>{s[0]} · {s[1]} v1</div><div className="lo" style={{ fontSize: 11.5 }}>From SCOUT's reading: 3 sources (YouTube, GitHub, arXiv) · recipe by RECIPE-MAKER · {s[2]}</div></div>
          <div className="row" style={{ marginLeft: 'auto', gap: 6 }}><button className="primary">To paper</button><button>Back, with a note</button><button>Edit rules</button><button>Version history</button></div></div>
        <div className="row" style={{ gap: 18, margin: '12px 0', borderBottom: '1px solid var(--line)' }}>{['OVERVIEW', 'TRADES 621 · 442 TO REVIEW', 'RULES'].map((t, i) => <span key={t} className="lbl" style={{ padding: '8px 0', color: i ? undefined : 'var(--hi)', borderBottom: i ? undefined : '1px solid var(--orange)' }}>{t}</span>)}</div>
        <div className="lbl" style={{ marginBottom: 8 }}>KEY FIGURES · DEMO</div>
        <div style={{ display: 'flex', border: '1px solid var(--line)' }}>{[['WIN RATE', '51.9%', 'g'], ['AVG R:R', '1 : 1.82', ''], ['EXPECTANCY', '+0.45R · £45', 'g'], ['TRADES', '621', ''], ['MAX DRAWDOWN', '−13.2R', 'r']].map(([l, v, c]) =>
          <div key={l} style={{ flex: 1, padding: 12, borderRight: '1px solid var(--line)' }}><div className="lbl">{l}</div><div className={`big ${c}`} style={{ fontSize: 20 }}>{v}</div></div>)}</div>
        <div className="lbl" style={{ margin: '14px 0 4px' }}>EQUITY CURVE · DEMO</div>
        <EquityChart seed={sel * 77 + 5} />
        <div className="grid" style={{ gridTemplateColumns: '1.4fr 1fr', marginTop: 12 }}>
          <div><div className="lbl" style={{ marginBottom: 6 }}>MONTHLY ROBUSTNESS</div>
            {[2020, 2021, 2022, 2023, 2024, 2025, 2026].map((y, yi) => <div key={y} className="row" style={{ gap: 3, marginBottom: 3 }}><span className="lo mono" style={{ fontSize: 10, width: 34 }}>{y}</span>
              {Array.from({ length: 12 }, (_, m) => { const v = Math.sin((yi * 12 + m) * 1.7 + sel) + .35; return <i key={m} style={{ width: 16, height: 12, background: v > 0 ? `rgba(120,216,128,${.25 + Math.min(.7, v / 2)})` : `rgba(224,72,88,${.25 + Math.min(.7, -v / 2)})` }} /> })}</div>)}</div>
          <div><div className="lbl" style={{ marginBottom: 6 }}>WHEN DOES IT WORK</div>
            {[['Asia', .12], ['London', .58], ['London–NY overlap', .82], ['New York PM', .31]].map(([n, v]) => <div key={n as string} style={{ marginBottom: 8 }}><div className="row" style={{ justifyContent: 'space-between', fontSize: 11.5 }}><span>{n}</span><span className="num g">+{((v as number) * .9).toFixed(2)}R</span></div><div className="bar"><i style={{ width: `${(v as number) * 100}%` }} /></div></div>)}</div>
        </div>
      </div></div>
    </div>
  </div>
}

// ---------------- Knowledge Base
type Candle = [number, number, number, number]
function candles(seed: number, n: number, drift = 0): Candle[] { let a = seed, p = 100; const out: Candle[] = []; for (let i = 0; i < n; i++) { a = (a * 1103515245 + 12345) & 0x7fffffff; const r = (a / 0x7fffffff - .5) * 2 + drift; const o = p, c = p + r * 1.4, hi = Math.max(o, c) + Math.abs(r) * .6 + .2, lo = Math.min(o, c) - Math.abs(r) * .5 - .2; out.push([o, hi, lo, c]); p = c } return out }
function CandleChart({ data, upto, zone, labels }: { data: Candle[]; upto?: number; zone?: [number, number, number, string, string]; labels?: [number, string][] }) {
  const draw = (c: CanvasRenderingContext2D, w: number, h: number) => {
    c.clearRect(0, 0, w, h); const d = data.slice(0, upto ?? data.length); const all = data.flatMap(x => [x[1], x[2]]); const mx = Math.max(...all), mn = Math.min(...all)
    const cw = (w - 20) / data.length, Y = (v: number) => 10 + (1 - (v - mn) / (mx - mn)) * (h - 30)
    if (zone) { c.fillStyle = zone[4]; c.fillRect(10 + zone[0] * cw, Y(zone[2]), (data.length - zone[0]) * cw, Y(zone[1]) - Y(zone[2])); c.fillStyle = '#C8CCD8'; c.font = '9px JetBrains Mono'; c.fillText(zone[3], 14 + zone[0] * cw, Y(zone[2]) - 4) }
    d.forEach(([o, hi, lo, cl], i) => { const x = 10 + i * cw + cw / 2, up = cl >= o; c.strokeStyle = up ? '#C8CCD8' : '#5A5F6E'; c.beginPath(); c.moveTo(x, Y(hi)); c.lineTo(x, Y(lo)); c.stroke(); c.fillStyle = up ? '#C8CCD8' : '#2A2D3A'; c.fillRect(x - cw * .32, Y(Math.max(o, cl)), cw * .64, Math.max(1, Math.abs(Y(o) - Y(cl)))) })
    labels?.forEach(([i, t]) => { if (i < d.length) { c.fillStyle = '#E8A850'; c.font = '9px JetBrains Mono'; c.fillText(t, 10 + i * cw - 10, h - 6) } })
  }
  return <Canvas draw={draw} />
}
const CARDS = [
  { n: 'Fair value gap', tags: ['PRICE ACTION', 'ICT'], txt: 'A three-candle gap: the wick of candle 1 and the wick of candle 3 do not overlap, leaving an inefficient zone price often returns to fill.', code: 'def fvg_bull(c1, c3):\n    return c3.low > c1.high', stat: '38,412 times found in XAU 5m · 71% filled within 20 candles · 4.2 pts avg size (demo)', zone: [14, 103.5, 105, 'fair value gap', 'rgba(32,224,240,.14)'] },
  { n: 'Break of structure', tags: ['STRUCTURE'], txt: 'Price closes beyond the last swing high (bullish) or swing low (bearish), confirming the trend continues.', code: 'def bos_bull(close, swing_high):\n    return close > swing_high', stat: '12,904 found · 58% follow through 1R (demo)', zone: [18, 104, 104.4, 'last swing high', 'rgba(232,168,80,.3)'] },
  { n: 'Optimal trade entry', tags: ['ICT'], txt: 'A retracement into the 62–79% zone of the last impulse leg, used as a refined entry area.', code: 'def ote(low, high, px):\n    r = (high - px) / (high - low)\n    return .62 <= r <= .79', stat: '6,310 found · 49% reach 2R (demo)', zone: [20, 101, 102.6, '62–79% zone', 'rgba(120,216,128,.12)'] },
  { n: 'Liquidity sweep', tags: ['ICT', 'ORDER FLOW'], txt: 'Price runs the stops beyond an obvious level, then closes back inside. NSKO-OF-1 only enters on the reclaim.', code: 'def sweep_reclaim(c, level):\n    return c.low < level and c.close > level', stat: '9,880 found · 63% revisit POC (demo)', zone: [16, 99, 99.3, 'swept level', 'rgba(224,72,88,.25)'] },
]
export function Knowledge() {
  const [k, setK] = useState(0); const [verdict, setV] = useState<Record<number, string>>({}); const card = CARDS[k]
  const [rep, setRep] = useState(28); const [play, setPlay] = useState(false); const data = useMemo(() => candles(k * 31 + 7, 28, .05), [k]); const rdata = useMemo(() => candles(901, 28, -.08), [])
  const [life, setLife] = useState(5)
  useEffect(() => { if (!play) return; const i = setInterval(() => setRep(r => { if (r >= 28) { setPlay(false); return 28 } return r + 1 }), 220); return () => clearInterval(i) }, [play])
  useEffect(() => { setLife(5); const t = setTimeout(() => setLife(6), 2200); return () => clearTimeout(t) }, [k])
  return <div className="page">
    <div className="ptitle">Knowledge Base</div><div className="psub">Every trading term JARVIS learns, written as a rule you can check against your own data.</div>
    <div className="panel" style={{ display: 'flex', marginBottom: 12 }}>{[['25', 'in your database', ''], ['16', 'you say correct', 'g'], ['6', 'code + picture ready', 'a'], ['14', 'terms the brain is still checking', 'c']].map(([v, l, c]) =>
      <div key={l} style={{ flex: 1, padding: 14, borderRight: '1px solid var(--line)' }}><div className={`big ${c}`}>{v}</div><div className="lo">{l}</div></div>)}</div>
    <div className="panel" style={{ marginBottom: 12 }}><Head t="YOUR CHECK" s="is this rule right?" />
      <div className="grid" style={{ gridTemplateColumns: '1.1fr 1fr', padding: 14 }}>
        <div><div style={{ height: 260, background: '#06060B', border: '1px solid var(--line)' }}><CandleChart data={data} zone={card.zone as any} labels={[[13, 'candle 1'], [15, 'candle 3']]} /></div><div className="lo mono" style={{ fontSize: 10.5, marginTop: 6 }}>{card.stat}</div></div>
        <div>
          <div className="row" style={{ gap: 6 }}>{[...card.tags, 'FROM YOUR DATABASE'].map(t => <span key={t} className="chip lo" style={{ borderColor: 'var(--line)' }}>{t}</span>)}</div>
          <div style={{ fontSize: 22, margin: '8px 0' }}>{card.n}</div><div style={{ lineHeight: 1.6, color: '#B8BCC8' }}>{card.txt}</div>
          <div className="g mono" style={{ fontSize: 11, margin: '8px 0' }}>12 of 12 of your examples found</div>
          <pre className="mono" style={{ background: '#06060B', borderLeft: '2px solid var(--orange)', padding: 10, fontSize: 11.5, color: '#C8CCD8' }}>{card.code}</pre>
          <textarea placeholder="Your note" style={{ width: '100%', marginTop: 8, height: 50 }} />
          <div className="row" style={{ marginTop: 8 }}><button className="primary" onClick={() => setV({ ...verdict, [k]: 'correct' })}>Correct</button><button onClick={() => setV({ ...verdict, [k]: 'not' })}>Not correct</button>
            {verdict[k] && <span className={verdict[k] === 'correct' ? 'g mono' : 'r mono'} style={{ fontSize: 11 }}>✓ saved: {verdict[k] === 'correct' ? 'correct' : 'not correct'}</span>}<span className="lo" style={{ marginLeft: 'auto', fontSize: 11 }}>all about {card.n} →</span></div>
        </div>
      </div>
      <div className="row" style={{ justifyContent: 'center', padding: 10, borderTop: '1px solid var(--line)' }}><button onClick={() => setK((k + CARDS.length - 1) % CARDS.length)}>‹ previous</button>
        {CARDS.map((_, i) => <i key={i} style={{ width: i === k ? 22 : 10, height: 2, background: i === k ? 'var(--orange)' : 'var(--line)', transition: 'width .3s var(--ease)' }} />)}<button onClick={() => setK((k + 1) % CARDS.length)}>next ›</button></div>
    </div>
    <div className="grid" style={{ gridTemplateColumns: '260px 1fr' }}>
      <div className="panel"><div className="pb"><input placeholder="Search terms" style={{ width: '100%', marginBottom: 10 }} />
        {[['PRICE ACTION · ICT', ['Fair value gap', 'Order block', 'Liquidity sweep', 'Break of structure', 'Change of character', 'Displacement']], ['STRUCTURE', ['Swing high / low', 'Higher low', 'Range']], ['SESSIONS & TIME', ['London open', 'NY open', 'Kill zones']]].map(([g, items]: any) =>
          <div key={g} style={{ marginBottom: 10 }}><div className="lbl" style={{ marginBottom: 4 }}>{g}</div>{items.map((it: string, i: number) => <div key={it} className="row" style={{ padding: '4px 0', fontSize: 12 }}><svg width="12" height="12"><circle cx="6" cy="6" r="4.5" fill="none" stroke="#2A2D3A" strokeWidth="2" /><circle cx="6" cy="6" r="4.5" fill="none" stroke="#78D880" strokeWidth="2" strokeDasharray={`${(i % 4 + 3) / 6 * 28} 28`} transform="rotate(-90 6 6)" /></svg>{it}<span className="lo num" style={{ marginLeft: 'auto' }}>{(i * 37 + 12) % 90}</span></div>)}</div>)}</div></div>
      <div className="panel"><Head t="CONCEPT" s="Change of character" /><div className="grid pb" style={{ gridTemplateColumns: '1fr 220px' }}>
        <div><div className="lbl">IN PLAIN ENGLISH</div><div style={{ margin: '6px 0 10px', lineHeight: 1.6, color: '#B8BCC8' }}>The first break against the trend: in a downtrend, price makes a higher high for the first time. It warns the trend may be changing.</div>
          <div className="mono g" style={{ fontSize: 11.5 }}>▲ BULLISH high[t] &gt; last lower high</div><div className="mono r" style={{ fontSize: 11.5, marginBottom: 10 }}>▼ BEARISH low[t] &lt; last higher low</div>
          <div className="lbl">REPLAY</div><div style={{ height: 180, background: '#06060B', border: '1px solid var(--line)', margin: '6px 0' }}><CandleChart data={rdata} upto={rep} labels={[[9, 'lower high'], [17, 'lower low'], [24, 'change of character']]} /></div>
          <div className="row" style={{ gap: 6 }}><button className="primary" onClick={() => { setRep(1); setPlay(true) }}>Play</button><button onClick={() => setRep(1)}>«</button><button onClick={() => setRep(r => Math.max(1, r - 1))}>‹</button><button onClick={() => setRep(r => Math.min(28, r + 1))}>›</button><button onClick={() => setRep(28)}>»</button><span className="lo mono" style={{ fontSize: 11 }}>candle {rep} of 28</span></div>
        </div>
        <div><div className="lbl">LIFECYCLE</div><svg width="200" height="160" viewBox="0 0 200 160">{[0, 1, 2, 3, 4, 5].map(i => <path key={i} d={arc(100, 80, 58, i * 60 + 2, i * 60 + 58)} stroke={i < life ? (i === 5 && life < 6 ? '#E8A850' : '#78D880') : '#E8A850'} strokeOpacity={i < life ? 1 : .5} strokeWidth="8" fill="none" style={{ transition: 'stroke .6s' }} />)}
          <text x="100" y="84" textAnchor="middle" fill="#E8E8EC" fontFamily="JetBrains Mono" fontSize="20">{life}/6</text><text x="100" y="102" textAnchor="middle" fill={life === 6 ? '#78D880' : '#5A5F6E'} fontFamily="JetBrains Mono" fontSize="8">{life === 6 ? 'FULLY READY' : 'CHECKING'}</text></svg>
          {['Found in sources', 'Rule written', 'Code written', 'Found in your data', 'Picture drawn', 'You checked it'].map((s, i) => <div key={s} className="mono" style={{ fontSize: 10.5, color: i < life ? 'var(--green)' : 'var(--lo)', padding: '2px 0' }}>{i + 1}. {s}</div>)}</div>
      </div>
      <div className="pb" style={{ borderTop: '1px solid var(--line)' }}><div className="lbl" style={{ marginBottom: 8 }}>THREE SOURCES SIDE BY SIDE</div><div className="grid" style={{ gridTemplateColumns: 'repeat(3,1fr)' }}>
        {[['YOUTUBE', '"…the first higher high after a run of lower highs…"'], ['GITHUB', 'smc-indicators/choch.py · swing-based detection'], ['ARXIV', 'Market structure shifts and short-horizon reversals (2023)']].map(([k, t]) => <div key={k} className="panel" style={{ padding: 10 }}><div className="lbl c">{k}</div><div style={{ fontSize: 11.5, marginTop: 4, color: '#B8BCC8' }}>{t}</div></div>)}</div></div>
      </div>
    </div>
  </div>
}
function arc(cx: number, cy: number, r: number, a0: number, a1: number) { const p = (a: number) => [cx + r * Math.cos((a - 90) * Math.PI / 180), cy + r * Math.sin((a - 90) * Math.PI / 180)]; const [x0, y0] = p(a0), [x1, y1] = p(a1); return `M${x0},${y0} A${r},${r} 0 0 1 ${x1},${y1}` }
