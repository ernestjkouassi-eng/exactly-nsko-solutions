import { useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, Spark, walk } from '../viz/canvas'
import { Head, ask } from '../shell/Shell'
import { notify } from '../store'
import { strategies, promote, rollback, DEMO_STRATEGIES, type Strategy, type Version } from '../api'

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

const TABS: [Strategy['status'] | 'all', string][] = [['Thought up', '1,308'], ['Approved', '12'], ['On paper', '3'], ['In review', '32'], ['Failed', '1,217'], ['all', '']]
export function Strategies() {
  const [list, setList] = useState<Strategy[]>(DEMO_STRATEGIES); const [demo, setDemo] = useState(true)
  const [tab, setTab] = useState<string>('all'); const [selId, setSelId] = useState(DEMO_STRATEGIES[0].id); const [q, setQ] = useState('')
  const [hist, setHist] = useState(() => new URLSearchParams(location.search).get('history') === '1'); const [busy, setBusy] = useState('')
  const load = () => strategies().then(r => { if (r.ok && Array.isArray(r.data) && r.data.length) { setList(r.data); setDemo(r.demo); if (!r.data.some(x => x.id === selId)) setSelId(r.data[0].id) } })
  useEffect(() => { load() }, [])
  const shown = list.map((s, i) => ({ s, i })).filter(({ s }) => (tab === 'all' || s.status === tab) && s.name.toLowerCase().includes(q.toLowerCase()))
  const si = Math.max(0, list.findIndex(x => x.id === selId)); const s = list[si]
  const counts = (t: string) => demo ? TABS.find(x => x[0] === t)?.[1] : String(list.filter(x => x.status === t).length)
  const doPromote = async (to: 'paper' | 'live') => {
    if (!await ask(to === 'paper' ? 'Send to paper?' : 'Send to live?', to === 'paper' ? `${s.name} v${s.version} starts paper trading: no real money, every trade journaled.` : `${s.name} v${s.version} starts live at 50% size for two weeks. The risk gate stays on.`, to === 'paper' ? 'To paper' : 'To live', to === 'live')) return
    setBusy('promote'); const r = await promote(s.id, to); setBusy('')
    if (!r.ok) return notify(`Not promoted: ${r.error}`, 'bad')
    notify(r.data.message || `${s.name} → ${to}`, 'good'); if (r.demo) setList(l => l.map(x => x.id === s.id ? { ...x, status: to === 'paper' ? 'On paper' : 'Live', stage: to === 'paper' ? 'on paper · day 0' : 'live · 50% size' } : x)); else load()
  }
  const doRollback = async (v: Version) => {
    if (!await ask(`Roll back to v${v.version}?`, `v${v.version} (${v.note}) becomes the active version of ${s.name}. v${s.version} is kept in the history and can be restored the same way.`, `Roll back to v${v.version}`)) return
    setBusy('v' + v.version); const r = await rollback(s.id, v.version); setBusy('')
    if (!r.ok) return notify(`Rollback failed: ${r.error}`, 'bad')
    notify(r.data.message || `v${v.version} is active`, 'good')
    if (r.demo) setList(l => l.map(x => x.id === s.id ? { ...x, version: v.version, sharpe_oos: v.sharpe_oos, versions: x.versions.map(y => ({ ...y, active: y.version === v.version })) } : x)); else load()
  }
  if (!s) return <div className="page"><div className="ptitle">Strategy Book</div><div className="empty">No strategies yet.</div></div>
  return <div className="page">
    <div className="row" style={{ alignItems: 'flex-start' }}><div><div className="ptitle">Strategy Book</div><div className="psub">Every test is here, even the failures. Every change is a new version you can roll back in one click.</div></div>{demo && <span className="chip a" style={{ borderColor: '#5A4020', marginLeft: 'auto' }}>DEMO BOOK</span>}</div>
    <div className="row" style={{ marginBottom: 12 }}>{TABS.map(([t]) =>
      <button key={t} onClick={() => setTab(t)} style={{ borderColor: tab === t ? 'var(--orange)' : undefined }}>{t === 'all' ? 'All' : t} {t !== 'all' && <span className="lo num">{counts(t)}</span>}</button>)}
      <input placeholder="Search strategies" value={q} onChange={e => setQ(e.target.value)} style={{ marginLeft: 'auto', width: 220 }} /></div>
    <div className="grid" style={{ gridTemplateColumns: '280px 1fr' }}>
      <div className="panel" style={{ alignSelf: 'start' }}>{shown.length === 0 && <div className="pb lo">Nothing here.</div>}{shown.map(({ s: x, i }) => <div key={x.id} onClick={() => setSelId(x.id)} style={{ padding: '10px 12px', borderBottom: '1px solid var(--line)', cursor: 'pointer', background: selId === x.id ? '#11121B' : undefined, borderLeft: `2px solid ${selId === x.id ? 'var(--orange)' : 'transparent'}` }}>
        <div className="row" style={{ justifyContent: 'space-between' }}><span>{x.name} <span className="lo mono" style={{ fontSize: 10 }}>v{x.version}</span></span><span className="num" style={{ color: x.sharpe_oos >= 1.4 ? 'var(--green)' : 'var(--lo)' }}>{x.sharpe_oos ? x.sharpe_oos.toFixed(2) : '—'}</span></div>
        <div className="row" style={{ justifyContent: 'space-between' }}><span className="lo mono" style={{ fontSize: 10 }}>{x.tf} · {x.stage}</span><Spark data={walk(i + 3, 24, x.sharpe_oos / 30)} w={60} h={16} color={x.sharpe_oos >= 1.4 ? '#78D880' : '#5A5F6E'} /></div>
        <div style={{ display: 'flex', gap: 2, marginTop: 5 }}>{[0, 1, 2, 3, 4].map(k => <i key={k} style={{ flex: 1, height: 3, background: k < Math.round(x.sharpe_oos * 2.4) ? (k === 3 && i % 3 === 0 ? '#E04858' : '#78D880') : '#1A1C26' }} />)}</div></div>)}</div>
      <div className="panel"><div className="pb">
        <span className="chip" style={{ color: s.status === 'Failed' ? 'var(--red)' : 'var(--green)', borderColor: s.status === 'Failed' ? '#5A2028' : '#2A5A30' }}>{s.status.toUpperCase()}</span>
        <div className="row" style={{ marginTop: 8 }}><div><div style={{ fontSize: 22 }}>{s.name} · {s.tf} v{s.version}</div><div className="lo" style={{ fontSize: 11.5 }}>From SCOUT's reading: 3 sources (YouTube, GitHub, arXiv) · recipe by RECIPE-MAKER · {s.stage}</div></div>
          <div className="row" style={{ marginLeft: 'auto', gap: 6 }}>
            {s.status === 'On paper' ? <button className="primary" disabled={!!busy} onClick={() => doPromote('live')}>To live</button> : <button className="primary" disabled={!!busy || s.status === 'Failed' || s.status === 'Live'} style={{ opacity: s.status === 'Failed' ? .4 : 1 }} onClick={() => doPromote('paper')}>To paper</button>}
            <button>Back, with a note</button><button>Edit rules</button>
            <button onClick={() => setHist(h => !h)} style={{ borderColor: hist ? 'var(--orange)' : undefined }}>Version history · {s.versions.length}</button></div></div>
        {hist && <div className="panel" data-testid="versions" style={{ margin: '12px 0 4px', background: '#0A0B12' }}><Head t="VERSION HISTORY" s={`${s.versions.length} version${s.versions.length === 1 ? '' : 's'} · newest first`} />
          <table><thead><tr>{['Version', 'Created', 'By', 'Change', 'Sharpe OOS', 'Stage', ''].map(h => <th key={h}>{h}</th>)}</tr></thead>
            <tbody>{s.versions.map(v => <tr key={v.version} style={{ background: v.active ? 'rgba(232,84,26,.05)' : undefined }}>
              <td><span className={v.active ? 'o' : ''}>v{v.version}</span>{v.active && <span className="chip o" style={{ borderColor: '#5A2A14', marginLeft: 6 }}>ACTIVE</span>}</td>
              <td className="lo">{new Date(v.created).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}</td><td className="lo">{v.by}</td><td style={{ fontFamily: 'var(--sans)', fontSize: 12 }}>{v.note}</td>
              <td className={v.sharpe_oos >= 1.4 ? 'g' : ''}>{v.sharpe_oos.toFixed(2)}</td><td className="lo">{v.active ? s.stage : v.stage}</td>
              <td style={{ textAlign: 'right' }}>{!v.active && <button style={{ padding: '2px 8px', fontSize: 10.5 }} disabled={!!busy} onClick={() => doRollback(v)}>{busy === 'v' + v.version ? 'Rolling back…' : `Roll back to v${v.version}`}</button>}</td></tr>)}</tbody></table></div>}
        <div className="row" style={{ gap: 18, margin: '12px 0', borderBottom: '1px solid var(--line)' }}>{['OVERVIEW', 'TRADES 621 · 442 TO REVIEW', 'RULES'].map((t, i) => <span key={t} className="lbl" style={{ padding: '8px 0', color: i ? undefined : 'var(--hi)', borderBottom: i ? undefined : '1px solid var(--orange)' }}>{t}</span>)}</div>
        <div className="lbl" style={{ marginBottom: 8 }}>KEY FIGURES · DEMO</div>
        <div style={{ display: 'flex', border: '1px solid var(--line)' }}>{[['WIN RATE', '51.9%', 'g'], ['AVG R:R', '1 : 1.82', ''], ['EXPECTANCY', '+0.45R · £45', 'g'], ['TRADES', '621', ''], ['MAX DRAWDOWN', '−13.2R', 'r']].map(([l, v, c]) =>
          <div key={l} style={{ flex: 1, padding: 12, borderRight: '1px solid var(--line)' }}><div className="lbl">{l}</div><div className={`big ${c}`} style={{ fontSize: 20 }}>{v}</div></div>)}</div>
        <div className="lbl" style={{ margin: '14px 0 4px' }}>EQUITY CURVE · DEMO</div>
        <EquityChart seed={si * 77 + 5 + s.version} />
        <div className="grid" style={{ gridTemplateColumns: '1.4fr 1fr', marginTop: 12 }}>
          <div><div className="lbl" style={{ marginBottom: 6 }}>MONTHLY ROBUSTNESS</div>
            {[2020, 2021, 2022, 2023, 2024, 2025, 2026].map((y, yi) => <div key={y} className="row" style={{ gap: 3, marginBottom: 3 }}><span className="lo mono" style={{ fontSize: 10, width: 34 }}>{y}</span>
              {Array.from({ length: 12 }, (_, m) => { const v = Math.sin((yi * 12 + m) * 1.7 + si) + .35; return <i key={m} style={{ width: 16, height: 12, background: v > 0 ? `rgba(120,216,128,${.25 + Math.min(.7, v / 2)})` : `rgba(224,72,88,${.25 + Math.min(.7, -v / 2)})` }} /> })}</div>)}</div>
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
