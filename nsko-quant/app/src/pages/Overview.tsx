import { useMemo, useRef } from 'react'
import { useS } from '../store'
import { Canvas, Spark, walk } from '../viz/canvas'
import { Head, Corners, fmt } from '../shell/Shell'
import { VERB_COL } from '../tokens'

function Kpi({ l, v, cap, dashed, children, dot }: any) {
  return <div style={{ padding: '12px 14px', borderRight: '1px solid var(--line)', flex: 1, minWidth: 0 }}>
    <div className="lbl">{dot && <span className="dot" style={{ background: dot, marginRight: 5 }} />}{l}</div>
    {dashed ? <div className="empty" style={{ marginTop: 6 }}>— {cap}</div> : <><div className="big" style={{ marginTop: 4 }}>{v}</div><div className="lo" style={{ fontSize: 11 }}>{cap}</div></>}
    {children}
  </div>
}

// BRAIN CORE: a 3,000-point sphere on a lat/long wireframe, sources flowing in on the left, output flowing out on the right.
// Each tested variant sprays a particle burst from the sphere along the line into "Variants tested".
function BrainCore() {
  const tested = useS(s => s.tested); const last = useRef(tested); const bursts = useRef<{ t0: number }[]>([])
  if (tested !== last.current) { last.current = tested; bursts.current.push({ t0: performance.now() / 1000 }) }
  const pts = useMemo(() => Array.from({ length: 3000 }, (_, i) => { const y = 1 - (i / 2999) * 2, r = Math.sqrt(1 - y * y), th = i * 2.39996; return [Math.cos(th) * r, y, Math.sin(th) * r] }), [])
  const parts = useRef<{ x: number; y: number; vx: number; vy: number; life: number }[]>([])
  const draw = (c: CanvasRenderingContext2D, w: number, h: number, t: number, dt: number) => {
    c.clearRect(0, 0, w, h); const cx = w / 2, cy = h / 2, R = Math.min(w * .17, h * .38), rot = t * Math.PI * 2 / 60
    const L = [cx - R * 1.05, cy], Rt = [cx + R * 1.05, cy]
    // input and output curves
    const ins = [h * .2, h * .38, h * .56, h * .74], outs = [h * .28, h * .5, h * .72]
    c.lineWidth = 1
    const curve = (x0: number, y0: number, x1: number, y1: number) => { c.beginPath(); c.moveTo(x0, y0); c.bezierCurveTo((x0 + x1) / 2, y0, (x0 + x1) / 2, y1, x1, y1); c.stroke() }
    const bez = (x0: number, y0: number, x1: number, y1: number, u: number) => { const mx = (x0 + x1) / 2, a = 1 - u; return [a * a * a * x0 + 3 * a * a * u * mx + 3 * a * u * u * mx + u * u * u * x1, a * a * a * y0 + 3 * a * a * u * y0 + 3 * a * u * u * y1 + u * u * u * y1] }
    c.strokeStyle = '#22252F'; ins.forEach(y => curve(200, y, L[0], L[1])); outs.forEach(y => curve(Rt[0], Rt[1], w - 200, y))
    // travelling light dots on the input lines
    ins.forEach((y, i) => { for (let k = 0; k < 2; k++) { const u = ((t * .25 + i * .21 + k * .5) % 1); const [x, yy] = bez(200, y, L[0], L[1], u); c.fillStyle = 'rgba(32,224,240,.9)'; c.fillRect(x - 1, yy - 1, 2, 2) } })
    // wireframe lat/long
    c.strokeStyle = 'rgba(90,95,110,.22)'
    for (let la = -60; la <= 60; la += 30) { const r = R * Math.cos(la * Math.PI / 180), y = cy - R * Math.sin(la * Math.PI / 180); c.beginPath(); c.ellipse(cx, y, r, r * .18, 0, 0, Math.PI * 2); c.stroke() }
    for (let lo = 0; lo < 180; lo += 30) { const a = lo * Math.PI / 180 + rot; c.beginPath(); c.ellipse(cx, cy, Math.abs(R * Math.cos(a)), R, 0, 0, Math.PI * 2); c.stroke() }
    // points
    const cr = Math.cos(rot), sr = Math.sin(rot)
    for (const [x, y, z] of pts) { const X = x * cr - z * sr, Z = x * sr + z * cr; const a = .25 + .75 * (Z + 1) / 2; c.fillStyle = `rgba(232,232,236,${a})`; c.fillRect(cx + X * R, cy - y * R, Z > 0 ? 1.4 : 1, Z > 0 ? 1.4 : 1) }
    // bursts → variants-tested card (middle output line)
    for (let nb = bursts.current.splice(0).length; nb > 0; nb--) for (let k = 0; k < 40; k++) parts.current.push({ x: Rt[0], y: Rt[1] + (Math.random() - .5) * 20, vx: 60 + Math.random() * 260, vy: (Math.random() - .5) * 90, life: 1 })
    for (const p of parts.current) { p.x += p.vx * dt; p.y += (outs[1] - p.y) * dt * 1.6 + p.vy * dt; p.vy *= .96; p.life -= dt * .9; c.fillStyle = `rgba(255,255,255,${Math.max(0, p.life)})`; c.fillRect(p.x, p.y, 1.6, 1.6) }
    parts.current = parts.current.filter(p => p.life > 0 && p.x < w - 200)
  }
  const flash = useRef(0); flash.current = tested
  return <div className="panel" style={{ height: 460 }}>
    <Head t="BRAIN CORE" s="every source in, every test out"><span className="mono g" style={{ fontSize: 10 }}><span className="dot pulse" /> BRAIN RUNNING</span></Head>
    <div style={{ position: 'absolute', inset: '40px 0 0 0' }}>
      <Corners />
      <Canvas draw={draw} />
      <div className="mono" style={{ position: 'absolute', top: 10, left: 0, right: 0, textAlign: 'center', fontSize: 11 }}><span className="lo">NOW</span> the lab is testing <span className="o">Range-XAU 16 · 4h</span></div>
      <div style={{ position: 'absolute', left: 14, top: 26, width: 180 }}>
        <div className="lbl" style={{ marginBottom: 6 }}>SOURCES IN TODAY ↓100</div>
        {[['YOUTUBE', 45, 1], ['GITHUB', 23, 2], ['ARXIV', 12, 3], ['WEB', 20, 4]].map(([k, v, s]) =>
          <div key={k as string} className="panel" style={{ padding: '7px 10px', marginBottom: 22, borderLeft: '2px solid var(--cyan)' }}>
            <div className="row" style={{ justifyContent: 'space-between' }}><span className="lbl">{k}</span><span className="num">{v}</span></div><Spark data={walk(s as number, 30)} color="#20E0F0" w={155} h={16} /></div>)}
      </div>
      <div style={{ position: 'absolute', right: 14, top: 40, width: 180 }}>
        <div className="lbl" style={{ marginBottom: 6 }}>OUTPUT TODAY</div>
        {[['THOUGHT UP', 103], ['VARIANTS TESTED', useS.getState().demo ? 532 + (tested - 1251) : tested], ['APPROVED', 2]].map(([k, v], i) =>
          <div key={k as string} className="panel" style={{ padding: '9px 10px', marginBottom: 52, borderLeft: `2px solid ${i === 2 ? 'var(--green)' : 'var(--hi)'}`, ...(i === 1 ? { animation: 'none' } : {}) }}>
            <div className="lbl">{k}</div><div key={i === 1 ? String(v) : k as string} className="big" style={{ fontSize: 20, ...(i === 1 ? { animation: 'flash .6s var(--ease)' } : {}) }}>{fmt(v as number)}</div></div>)}
      </div>
      <div className="mono" style={{ position: 'absolute', bottom: 12, left: 0, right: 0, textAlign: 'center', fontSize: 11 }}><span className="lo">READING</span> Time-series momentum on index futures · <span className="lo">min 21 of 39</span></div>
      <style>{`@keyframes flash{0%{color:#fff;text-shadow:0 0 12px #fff}100%{text-shadow:none}}`}</style>
    </div>
  </div>
}

function Pipeline() {
  const tested = useS(s => s.tested), sieve = useS(s => s.sieve), clear = useS(s => s.clear), log = useS(s => s.log)
  const nodes = [['READ', 407], ['SUMMARISED', 401], ['THOUGHT UP', 1308], ['TESTED', tested], ['THROUGH THE SIEVE', sieve], ['APPROVED', clear], ['ON PAPER', 3], ['LIVE', 0]]
  const draw = (c: CanvasRenderingContext2D, w: number, h: number, t: number) => {
    c.clearRect(0, 0, w, h); const x0 = 110, step = (w - x0 - 40) / (nodes.length - 1), y = 60
    const srcs = [['YouTube', 185], ['GitHub', 90], ['arXiv', 55], ['Web', 77]]
    c.font = '10px JetBrains Mono'; c.strokeStyle = '#2A2D3A'
    srcs.forEach(([n, v], i) => { const sy = 18 + i * 28; c.beginPath(); c.moveTo(30, sy); c.bezierCurveTo(70, sy, 70, y, x0, y); c.stroke(); c.beginPath(); c.arc(24, sy, 4, 0, 7); c.stroke(); c.fillStyle = '#5A5F6E'; c.fillText(`${n} ${v}`, 0, sy + 16 > h ? sy : sy - 8) })
    c.beginPath(); c.moveTo(x0, y); c.lineTo(x0 + step * (nodes.length - 1), y); c.stroke()
    nodes.forEach(([n, v], i) => {
      const x = x0 + i * step, col = i === 3 ? '#E8E8EC' : i === 4 ? '#E8A850' : i >= 5 && (v as number) > 0 ? '#78D880' : '#5A5F6E'
      if (i === 3) { c.fillStyle = 'rgba(232,232,236,.12)'; c.beginPath(); c.arc(x, y, 14, 0, 7); c.fill() }
      c.strokeStyle = col; c.fillStyle = '#0C0D14'; c.beginPath(); c.arc(x, y, 6, 0, 7); c.fill(); c.stroke()
      c.fillStyle = '#5A5F6E'; c.textAlign = 'center'; c.fillText(n as string, x, y + 24); c.fillStyle = col; c.font = '12px JetBrains Mono'; c.fillText(fmt(v as number), x, y + 40); c.font = '10px JetBrains Mono'
      if (i >= 2 && i <= 4) { c.strokeStyle = '#2A2D3A'; c.beginPath(); c.moveTo(x, y + 46); c.lineTo(x + step / 2, y + 70); c.stroke(); c.fillStyle = '#E04858'; c.fillText(['REJECTED 287', 'FAILED 908', 'FAILED 299'][i - 2], x + step / 2, y + 84) }
      c.textAlign = 'left'
    })
    // comet pulse
    const u = (t * .22) % 1, cx = x0 + u * step * (nodes.length - 1)
    const g = c.createLinearGradient(cx - 60, 0, cx, 0); g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(1, 'rgba(255,255,255,.9)')
    c.strokeStyle = g; c.lineWidth = 2; c.beginPath(); c.moveTo(Math.max(x0, cx - 60), y); c.lineTo(cx, y); c.stroke(); c.lineWidth = 1
    c.fillStyle = '#fff'; c.shadowColor = '#fff'; c.shadowBlur = 10; c.beginPath(); c.arc(cx, y, 2.5, 0, 7); c.fill(); c.shadowBlur = 0
  }
  return <div className="panel">
    <Head t="PIPELINE" s="from source to live" />
    <div style={{ height: 160 }}><Canvas draw={draw} /></div>
    <div style={{ borderTop: '1px solid var(--line)' }}><Head t="LOGBOOK · ACTIVITY" /></div>
    <div style={{ padding: '4px 14px 10px' }}>{log.slice(-8).reverse().map((l, i) => <div key={l.ts + i} className="mono" style={{ fontSize: 11, padding: '3px 0', display: 'flex', gap: 10 }}>
      <span className="lo">{new Date(l.ts).toLocaleTimeString('en-GB', { hour12: false })}</span><span style={{ color: VERB_COL[l.verb], width: 70 }}>{l.verb}</span><span style={{ color: '#9A9EAA', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>{l.msg}</span></div>)}</div>
  </div>
}

export function DecisionCards() {
  const decisions = useS(s => s.decisions), set = useS(s => s.set)
  const out = (id: number) => { const el = document.getElementById('dec' + id); if (el) { el.style.transform = 'translateX(120%)'; el.style.opacity = '0' } setTimeout(() => set({ decisions: useS.getState().decisions.filter(d => d.id !== id) }), 350) }
  return <>{decisions.length === 0 && <div className="empty">Nothing waiting on you.</div>}
    {decisions.map(d => <div key={d.id} id={'dec' + d.id} className="panel" style={{ borderLeft: '2px solid var(--amber)', padding: 12, marginBottom: 10, transition: 'transform .35s var(--ease), opacity .35s var(--ease)' }}>
      <div className="lbl a">{d.tag}</div><div style={{ fontSize: 15, margin: '4px 0' }}>{d.title}</div><div className="lo" style={{ fontSize: 11.5, lineHeight: 1.5 }}>{d.desc}</div>
      <div className="row" style={{ marginTop: 10, gap: 8 }}><button className="primary" onClick={() => out(d.id)}>Approve</button><button onClick={() => out(d.id)}>Back</button></div></div>)}</>
}

export default function Overview() {
  const tested = useS(s => s.tested), sieve = useS(s => s.sieve), clear = useS(s => s.clear), budget = useS(s => s.budget), variants = useS(s => s.variants)
  return <div className="page">
    <div className="panel" style={{ display: 'flex', marginBottom: 12 }}>
      <Kpi l="THOUGHT UP" v="1,308" cap="ideas from sources" />
      <Kpi l="TESTED" v={fmt(tested)} cap={`${Math.round(tested / 1308 * 100)}% of thought up`} />
      <Kpi l="THROUGH THE SIEVE" v={fmt(sieve)} cap={`${tested ? Math.round(sieve / tested * 100) : 0}%`} dot="var(--amber)" />
      <Kpi l="APPROVED" v={fmt(clear)} cap={`${tested ? (clear / tested * 100).toFixed(1) : '0.0'}%`} dot="var(--green)" />
      <Kpi l="ON PAPER" v="3" cap="day 9 of 21"><div className="bar" style={{ marginTop: 6 }}><i style={{ width: '43%' }} /></div></Kpi>
      <Kpi l="LIVE" dashed cap="waiting for you" />
      <Kpi l="PROFIT LIVE" dashed cap="not started" />
      <Kpi l="THINK BUDGET" v={`£${budget.used.toFixed(0)}/£${budget.of}`} cap={`${budget.days} days left`}><div className="bar" style={{ marginTop: 6 }}><i style={{ width: `${budget.used / budget.of * 100}%` }} /></div></Kpi>
    </div>
    <BrainCore />
    <div className="panel" style={{ margin: '12px 0' }}><Head t="DAILY BRIEFING" s="SCOUT's read of the night"><span className="chip lo" style={{ borderColor: 'var(--line)' }}>not measured yet</span></Head>
      <div className="pb lo" style={{ textAlign: 'center', padding: 22 }}>The first briefing arrives after SCOUT's first full night of reading.</div></div>
    <div className="grid" style={{ gridTemplateColumns: '2fr 1fr' }}>
      <Pipeline />
      <div className="panel"><Head t="YOUR DECISIONS" s={`${useS.getState().decisions.length} waiting on you`} /><div className="pb"><DecisionCards /></div></div>
    </div>
    <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', marginTop: 12 }}>
      <div className="panel"><Head t="EQUITY CURVES" s="live · last 100 variants" /><div className="pb" style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 8 }}>
        {variants.slice(-10).map(v => <Spark key={v.id} data={walk(v.seed % 9999, 30, v.sharpeOOS / 40)} color={v.outcome === 'clear' ? '#78D880' : v.outcome === 'sieve' ? '#E8A850' : '#5A5F6E'} w={90} h={30} />)}</div></div>
      <div className="panel"><Head t="LATEST VARIANTS" /><table><thead><tr><th>Recipe</th><th>Mkt</th><th>Sharpe IS→OOS</th><th>Outcome</th></tr></thead>
        <tbody>{variants.slice(-6).reverse().map(v => <tr key={v.id}><td>{v.recipe}</td><td className="lo">{v.market} · {v.tf}</td><td>{v.sharpeIS} → <span className={v.sharpeOOS >= 1.4 ? 'g' : ''}>{v.sharpeOOS}</span></td>
          <td className={v.outcome === 'clear' ? 'g' : v.outcome === 'sieve' ? 'a' : 'r'}>{v.outcome === 'clear' ? 'CLEARS THE BAR' : v.outcome === 'sieve' ? 'SIEVE' : 'FAILED'}</td></tr>)}</tbody></table></div>
    </div>
  </div>
}
