import { useEffect, useMemo, useRef, useState } from 'react'
import { useS, type Variant } from '../store'
import { labFan, labVariants, research } from '../api'
import { Canvas } from '../viz/canvas'
import { Head, fmt } from '../shell/Shell'
import { IDEA_TYPES } from '../demo/sim'

const IDEA_COL = ['#20E0F0', '#F8A0C0', '#E8A850', '#5A8CFF', '#78D880', '#C890FF', '#E8541A']
function path(v: Variant, n = 220) {   // equity path for a variant: IS drift from sharpeIS, OOS drift from sharpeOOS, converging to 0 at the split
  let a = v.seed, y = 0; const out: number[] = []
  for (let i = 0; i < n; i++) { a = (a * 1103515245 + 12345) & 0x7fffffff; const z = (a / 0x7fffffff - .5) * 2; const s = i < n / 2 ? v.sharpeIS : v.sharpeOOS; y += s * .035 + z * .18; out.push(y) }
  const mid = out[n / 2]; return out.map(q => q - mid)
}
const useEngine = () => { const source = useS(s => s.source), fallback = useS(s => s.fallback); return source === 'engine' && !fallback }
const fanLoaded = new Set<string>()
async function loadFan(recipe: string) {
  const r = await labFan(recipe); if (!r.ok || r.demo) return
  const lines = { ...useS.getState().labLines }; for (const l of r.data.lines) if (l.equity?.length) lines[l.id] = { id: l.id, label: l.label, outcome: l.outcome, equity: l.equity }
  useS.setState({ labLines: lines })
}
// Engine mode: the variants and their real equity curves come from the Lab (/lab/variants + /lab/fan), then live from
// `variant_tested` / `backtest_done`. Nothing is drawn from the demo bank.
export function useLabFromEngine() {
  const engine = useEngine(), last = useS(s => s.lastBacktest)
  useEffect(() => { if (!engine) return
    labVariants(300).then(r => { if (!r.ok || r.demo) return
      const rows: Variant[] = r.data.variants.map((v: any) => ({ id: v.id, recipe: v.label || v.recipe_id, market: String(v.market || '').split('/')[0], tf: v.tf, sharpeIS: +(+v.sharpe_is).toFixed(2), sharpeOOS: +(+v.sharpe_oos).toFixed(2),
        trades: v.trades, win: +(+v.win).toFixed(1), rr: +(+v.rr).toFixed(2), dd: +(+v.dd).toFixed(1), outcome: v.outcome, why: v.why, seed: v.seed ?? v.id, recipe_id: v.recipe_id, synthetic: !!v.synthetic } as any)).reverse()
      const st = useS.getState(); if (st.variants.length >= rows.length) return
      const fails: Record<string, number> = Object.fromEntries(Object.keys(st.fails).map(k => [k, 0])); rows.forEach(v => { if (v.why) fails[v.why] = (fails[v.why] || 0) + 1 })
      useS.setState({ variants: rows, tested: rows.length, sieve: rows.filter(v => v.outcome !== 'failed').length, clear: rows.filter(v => v.outcome === 'clear').length, fails })
      for (const id of new Set(rows.map((v: any) => v.recipe_id))) if (id && !fanLoaded.has(id)) { fanLoaded.add(id); loadFan(id) }
    }) }, [engine])
  useEffect(() => { if (engine && last?.recipe) loadFan(last.recipe) }, [engine, last])
}
function resample(a: number[], n: number) { if (!a.length) return []; return Array.from({ length: n }, (_, i) => a[Math.min(a.length - 1, Math.round(i / (n - 1) * (a.length - 1)))]) }

export function EquityFan() {
  const variants = useS(s => s.variants); const [mode, setMode] = useState<'outcome' | 'idea' | 'nocost'>('outcome'); const [hov, setHov] = useState<Variant | null>(null)
  const mouse = useRef<[number, number] | null>(null); const engine = useEngine(); const labLines = useS(s => s.labLines)
  const bank = useMemo(() => { const v: Variant[] = []; for (let i = 0; i < 520; i++) { const s = (i * 7919) % 99991; const is = .3 + ((s % 100) / 100) * 1.4; const oos = is - ((s % 37) / 37) * 1.6 + ((s % 11) - 5) / 20; v.push({ id: -i, recipe: `${['Range', 'Trend', 'Sweep', 'Spread', 'ORB'][i % 5]}-XAU ${i % 20 + 1}`, market: 'XAU', tf: '4h', sharpeIS: +is.toFixed(2), sharpeOOS: +oos.toFixed(2), trades: 200, win: 50, rr: 1.4, dd: -12, outcome: oos >= 1.4 ? 'clear' : oos > .7 && i % 2 ? 'sieve' : 'failed', why: oos < 1.4 ? 'Max drawdown too deep' : null, seed: s + 1 }) } return v }, [])
  // engine: only variants whose real equity curve the Lab stored, as % return over the whole test window
  const all = engine ? variants.filter(v => labLines[v.id]) : [...bank, ...variants]; const paths = useRef(new Map<number, number[]>()); const cache = useRef<{ key: string; img: HTMLCanvasElement | null }>({ key: '', img: null })
  const real = useMemo(() => { if (!engine) return null; const m = new Map<number, number[]>(); let mx = 14
    for (const v of all) { const e = labLines[v.id].equity, e0 = e[0] || 1, p = resample(e, 220).map(x => (x / e0 - 1) * 100); m.set(v.id, p); for (const x of p) mx = Math.max(mx, Math.abs(x)) }
    return { m, mx } }, [engine, labLines, variants])
  const draw = (c: CanvasRenderingContext2D, w: number, h: number, t: number) => {
    c.clearRect(0, 0, w, h); const n = 220, mid = engine ? h * .5 : h * .55, sx = (i: number) => 30 + (i / (n - 1)) * (w - 60), K = h * .4 / (real ? real.mx : 14), sy = (y: number) => mid - y * K   // ±14 units fills the panel
    c.font = '10px JetBrains Mono'; c.fillStyle = '#5A5F6E'
    if (engine) { c.fillText('REAL LAB EQUITY · % RETURN OVER THE WHOLE TEST WINDOW (IS → OOS), AFTER COSTS', 40, 18); c.strokeStyle = '#2A2D3A'; c.beginPath(); c.moveTo(30, mid); c.lineTo(w - 30, mid); c.stroke()
      if (!all.length) { c.fillStyle = '#9A9EAA'; c.font = '12px JetBrains Mono'; c.fillText('No Lab results yet. Run a recipe in the Lab (POST /lab/run) and every variant draws here.', 40, mid - 10); return } }
    else { c.fillStyle = 'rgba(255,255,255,.015)'; c.fillRect(30, 0, (w - 60) / 2, h); c.fillStyle = '#5A5F6E'; c.fillText('IN-SAMPLE (IS) 2009–2019', 40, 18); c.fillText('OUT-OF-SAMPLE (OOS) 2020–2026', w / 2 + 10, 18)
      c.strokeStyle = '#2A2D3A'; c.beginPath(); c.moveTo(w / 2, 26); c.lineTo(w / 2, h - 10); c.stroke() }
    let best: Variant | null = null, bd = 14
    const list = all.slice(-560), d = Math.min(2, devicePixelRatio || 1), key = `${w}x${h}|${mode}|${variants.length}|${all.length}`
    const line = (cc: CanvasRenderingContext2D, v: Variant, upto: number, running: boolean) => {
      let p = real ? real.m.get(v.id) : paths.current.get(v.id); if (!p) { p = path(v, n); paths.current.set(v.id, p) }
      cc.strokeStyle = running ? '#FFFFFF' : mode === 'idea' ? IDEA_COL[Math.abs(v.seed) % 7] : v.outcome === 'clear' ? '#78D880' : v.outcome === 'sieve' ? '#E8A850' : '#5A5F6E'
      cc.globalAlpha = running ? 1 : v.outcome === 'failed' && mode !== 'idea' ? .12 : .45; cc.lineWidth = running ? 1.6 : .7
      if (mode === 'nocost') cc.setLineDash([3, 3])
      cc.beginPath(); for (let i = 0; i < upto; i++) { const x = sx(i), y = sy(p[i] + (mode === 'nocost' && i > n / 2 ? (i - n / 2) * .02 : 0)); i ? cc.lineTo(x, y) : cc.moveTo(x, y) } cc.stroke(); cc.setLineDash([]); cc.globalAlpha = 1
      return p
    }
    if (cache.current.key !== key) {        // the settled lines are drawn once into an offscreen canvas; only the running test redraws each frame
      const oc = document.createElement('canvas'); oc.width = w * d; oc.height = h * d; const cc = oc.getContext('2d')!; cc.setTransform(d, 0, 0, d, 0, 0)
      list.slice(0, -1).forEach(v => line(cc, v, n, false)); cache.current = { key, img: oc }
    }
    c.drawImage(cache.current.img!, 0, 0, w, h)
    const run = list[list.length - 1], upto = Math.floor(((t * .5) % 1) * n); const rp = line(c, run, upto, true)
    if (upto > 0) { c.fillStyle = '#fff'; c.shadowColor = '#fff'; c.shadowBlur = 12; c.beginPath(); c.arc(sx(upto - 1), sy(rp[upto - 1]), 3, 0, 7); c.fill(); c.shadowBlur = 0 }
    if (mouse.current) { const i = Math.round((mouse.current[0] - 30) / (w - 60) * (n - 1)); if (i >= 0 && i < n) list.forEach(v => { const p = real ? real.m.get(v.id) : paths.current.get(v.id); if (!p) return; const dd = Math.abs(sy(p[i]) - mouse.current![1]); if (dd < bd) { bd = dd; best = v } }) }
    c.globalAlpha = 1
    if (best) { const p = (real ? real.m.get((best as Variant).id) : paths.current.get((best as Variant).id))!; c.strokeStyle = '#E8541A'; c.lineWidth = 2; c.beginPath(); p.forEach((y, i) => i ? c.lineTo(sx(i), sy(y)) : c.moveTo(sx(i), sy(y))); c.stroke() }
    if (best !== hov) setHov(best)
    if (engine) return
    // THE BAR
    c.strokeStyle = '#78D880'; c.setLineDash([6, 4]); c.beginPath(); c.moveTo(w / 2, mid); c.lineTo(w - 30, mid - 1.4 * .035 * 110 * K); c.stroke(); c.setLineDash([])
    c.fillStyle = '#78D880'; c.fillText('THE BAR · SHARPE 1.40', w - 190, mid - 1.4 * .035 * 110 * K - 8)
    // scan beam
    const bx = 30 + ((t * .12) % 1) * (w - 60); const g = c.createLinearGradient(bx - 40, 0, bx, 0); g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(1, 'rgba(255,255,255,.12)'); c.fillStyle = g; c.fillRect(bx - 40, 26, 40, h - 36)
  }
  return <div className="panel"><Head t="EQUITY CURVES" s="every variant: in-sample, then out-of-sample">
    {(['outcome', 'idea', 'nocost'] as const).map(m => <button key={m} onClick={() => setMode(m)} style={{ padding: '3px 8px', fontSize: 10, borderColor: mode === m ? 'var(--orange)' : undefined }}>{m === 'outcome' ? 'Colour by outcome' : m === 'idea' ? 'Colour by idea type' : 'Without costs'}</button>)}</Head>
    <div style={{ height: 380, position: 'relative' }} onMouseMove={e => { const r = e.currentTarget.getBoundingClientRect(); mouse.current = [e.clientX - r.left, e.clientY - r.top] }} onMouseLeave={() => { mouse.current = null; setHov(null) }}>
      <Canvas draw={draw} />
      {hov && <div className="panel mono" style={{ position: 'absolute', right: 20, top: 30, padding: 10, fontSize: 11, lineHeight: 1.6 }}>{hov.recipe} · v{Math.abs(hov.seed) % 12 + 1}<br />Sharpe IS {hov.sharpeIS} → OOS {hov.sharpeOOS} · decline {(hov.sharpeOOS - hov.sharpeIS).toFixed(2)}<br />
        <span className={hov.outcome === 'clear' ? 'g' : hov.outcome === 'sieve' ? 'a' : 'r'}>{hov.outcome === 'clear' ? 'CLEARS THE BAR' : hov.outcome === 'sieve' ? 'THROUGH THE SIEVE' : 'FAILED'}</span>{hov.why && <span className="lo"> · {hov.why}</span>}</div>}
    </div></div>
}

export function Lab() {
  useLabFromEngine(); const engine = useEngine(), labRunning = useS(s => s.labRunning), last = useS(s => s.lastBacktest)
  const tested = useS(s => s.tested), sieve = useS(s => s.sieve), clear = useS(s => s.clear), fails = useS(s => s.fails), lastFail = useS(s => s.lastFail), variants = useS(s => s.variants); const mx = Math.max(1, ...Object.values(fails))
  const avgDecl = variants.length ? variants.reduce((a, v) => a + v.sharpeIS - v.sharpeOOS, 0) / variants.length : 1.2
  return <div className="page">
    <div className="lbl g"><span className="dot pulse" /> LAB · LIVE</div>
    <div className="row" style={{ alignItems: 'flex-start' }}><div><div className="ptitle">The Lab</div><div className="psub">Every recipe is tested as variants. In-sample almost everything works; out-of-sample almost everything falls over. Only what clears the bar out-of-sample counts.</div></div><button style={{ marginLeft: 'auto' }}>Pause</button></div>
    <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', marginBottom: 12 }}>
      <div className="panel"><Head t="RECIPES IN THE LAB" /><div className="pb">
        {[['TESTED', tested, [[.73, '#2A2D3A'], [.2, '#E8A850'], [.07, '#78D880']]], ['THROUGH THE SIEVE', sieve, [[.6, '#2A2D3A'], [.3, '#E8A850'], [.1, '#78D880']]]].map(([l, v, segs]: any) =>
          <div key={l} style={{ marginBottom: 18 }}><div className="row" style={{ justifyContent: 'space-between' }}><span className="lbl">{l}</span><span className="num" style={{ fontSize: 18 }}>{fmt(v)}</span></div>
            <div style={{ display: 'flex', height: 8, marginTop: 6, gap: 2 }}>{segs.map(([f, col]: any, i: number) => <i key={i} style={{ flex: f, background: col, borderRadius: 1 }} />)}</div></div>)}
        <div className="lo mono" style={{ fontSize: 10 }}><span className="a">■</span> through the sieve &nbsp; <span className="g">■</span> clears the bar &nbsp; <span style={{ color: '#2A2D3A' }}>■</span> failed</div>
      </div></div>
      <div className="panel"><Head t="WHY DO THEY FAIL?" /><div className="pb">{Object.entries(fails).map(([k, v]) =>
        <div key={k} style={{ display: 'grid', gridTemplateColumns: '220px 1fr 70px', gap: 10, alignItems: 'center', marginBottom: 7 }}>
          <span style={{ fontSize: 12 }}>{k}</span>
          <div style={{ height: 6, background: '#12131B', borderRadius: 1, overflow: 'hidden' }}><i key={k === lastFail ? v : 0} style={{ display: 'block', height: '100%', width: `${v / mx * 100}%`, background: k === lastFail ? 'linear-gradient(90deg,#5A5F6E,#E8C060)' : '#5A5F6E', transition: 'width .6s var(--ease)' }} /></div>
          <span className="num" style={{ fontSize: 11, textAlign: 'right' }}>{v} <span className="lo">{tested ? Math.round(v / tested * 100) : 0}%</span></span></div>)}</div></div>
    </div>
    <EquityFan />
    <div className="panel" style={{ display: 'flex', margin: '12px 0' }}>{(engine ? [['VARIANTS', fmt(variants.length)], ['CLEAR THE BAR', String(clear)], ['SHARPE DECLINE IS→OOS', variants.length ? avgDecl.toFixed(2) : '—'], ['LAST RUN', last ? `${last.name} · ${last.synthetic ? 'SYNTHETIC data' : last.data_source}` : '—'], ['OVERFITTING CHANCE (PBO)', last?.pbo != null ? `${Math.round(last.pbo * 100)}%` : '—']]
      : [['VARIANTS', fmt(553 + variants.length)], ['CLEAR THE BAR', String(clear)], ['SHARPE DECLINE IS→OOS', avgDecl.toFixed(2)], ['CHANCE SCORE', '1.54'], ['OVERFITTING CHANCE', '64%']]).map(([l, v]) =>
      <div key={l} style={{ flex: 1, padding: 14, borderRight: '1px solid var(--line)' }}><div className="lbl">{l}</div><div className="big">{v}</div></div>)}</div>
    <div className="panel"><Head t="LATEST VARIANTS" /><table><thead><tr>{['Recipe', 'Market', 'Trades', 'Win rate', 'R:R', 'Expectancy', 'Sharpe IS→OOS', 'Max DD', 'Outcome'].map(h => <th key={h}>{h}</th>)}</tr></thead>
      <tbody>{!engine ? <tr><td className="o">Range-XAU 16</td><td>XAU · 4h</td><td colSpan={7} className="lo">TEST RUNNING…</td></tr> : labRunning ? <tr><td className="o">{labRunning}</td><td colSpan={8} className="lo">TEST RUNNING…</td></tr> : null}
        {engine && !variants.length && <tr><td colSpan={9} className="lo">No variants tested yet on this engine.</td></tr>}
        {variants.slice(-12).reverse().map(v => <tr key={v.id}><td>{v.recipe}</td><td className="lo">{v.market} · {v.tf}</td><td>{v.trades}</td><td>{v.win}%</td><td>1:{v.rr}</td><td className={v.win * v.rr / 100 > .5 ? 'g' : 'r'}>{(v.win / 100 * v.rr - (1 - v.win / 100)).toFixed(2)}R</td>
          <td>{v.sharpeIS} → {v.sharpeOOS}</td><td className="r">{v.dd}R</td><td className={v.outcome === 'clear' ? 'g' : v.outcome === 'sieve' ? 'a' : 'r'}>{v.outcome === 'clear' ? 'CLEARS' : v.outcome === 'sieve' ? 'SIEVE' : 'FAILED'}</td></tr>)}</tbody></table></div>
  </div>
}

const TRANSCRIPT = ['so the idea is simple: when price is above the 200-day average you only take longs,', 'and the first thing I look at in the morning is the overnight fair value gap,', 'if price runs the lows and closes back inside, that is a liquidity sweep,',
  'we anchor the VWAP to the session open and fade the two-sigma band,', 'the order block is the last down candle before the move,', 'mean reversion works in balance, trend following works when the market leaves value,', 'and that is why we size by volatility, not by conviction.']
const TERMS = ['fair value gap', 'liquidity sweep', 'VWAP', 'order block', 'mean reversion', 'trend following']
export function Research() {
  const sources = useS(s => s.sources); const [, force] = useState(0); const engine = useEngine(); const reading = useS(s => s.reading), terms = useS(s => s.terms)
  useEffect(() => { if (!engine) return   // first paint from the engine's tables, then live from source_added / summary_done / term_found
    research('sources', 40).then(r => { if (r.ok && !r.demo && !useS.getState().sources.length) useS.setState({ sources: (r.data.sources || []).reverse().map((x: any) => ({ kind: x.kind, title: x.title, idea: x.idea_type, ts: x.created_at })) }) })
    research('terms', 30).then(r => { if (r.ok && !r.demo && !useS.getState().terms.length) useS.setState({ terms: (r.data.terms || []).reverse().map((x: any) => ({ term: x.term, ts: x.created_at })) }) })
    research('summaries', 1).then(r => { const x = r.ok && !r.demo ? r.data.summaries?.[0] : null; if (x && !useS.getState().reading) useS.setState({ reading: { title: useS.getState().sources.find((s: any) => s.id === x.source_id)?.title || `source #${x.source_id}`, summary: x.summary, idea: x.idea_type, highlights: [], agent: x.agent, model: x.model, ts: x.created_at } }) })
  }, [engine])
  const stars = useMemo(() => IDEA_TYPES.map((n, i) => ({ n, x: .12 + (i % 4) * .25 + (i > 3 ? .12 : 0), y: i > 3 ? .7 : .32, dots: Array.from({ length: 60 + i * 9 }, (_, k) => ({ a: k * 2.4, r: 18 + (k * 37 % 50), s: .2 + (k % 7) / 20 })) })), [])
  const bg = useMemo(() => Array.from({ length: 400 }, (_, k) => [(k * 9301 % 1000) / 1000, (k * 4973 % 1000) / 1000, (k % 5) / 5]), [])
  const fly = useRef<{ i: number; t0: number }[]>([]); const seen = useRef(0)
  if (sources.length !== seen.current) { seen.current = sources.length; const s = sources[sources.length - 1]; if (s) fly.current.push({ i: IDEA_TYPES.indexOf(s.idea), t0: performance.now() / 1000 }) }
  const draw = (c: CanvasRenderingContext2D, w: number, h: number, t: number) => {
    const g = c.createRadialGradient(w * .5, h * .5, 10, w * .5, h * .5, w * .7); g.addColorStop(0, '#101A3A'); g.addColorStop(.6, '#0A0F24'); g.addColorStop(1, '#06070F'); c.fillStyle = g; c.fillRect(0, 0, w, h)
    bg.forEach(([x, y, b]) => { c.fillStyle = `rgba(200,210,255,${.15 + .35 * b * (.6 + .4 * Math.sin(t * 2 + x * 40))})`; c.fillRect(x * w + Math.sin(t * .05) * 6 * b, y * h, 1, 1) })
    stars.forEach((s, i) => {
      const X = s.x * w + Math.sin(t * .1 + i) * 4, Y = s.y * h
      s.dots.forEach(d => { const a = d.a + t * d.s * .3; c.fillStyle = 'rgba(120,216,128,.75)'; c.fillRect(X + Math.cos(a) * d.r, Y + Math.sin(a) * d.r * .7, 1.6, 1.6) })
      const gg = c.createRadialGradient(X, Y, 0, X, Y, 26); gg.addColorStop(0, 'rgba(255,255,255,1)'); gg.addColorStop(.15, 'rgba(160,240,255,.8)'); gg.addColorStop(1, 'rgba(32,224,240,0)'); c.fillStyle = gg; c.beginPath(); c.arc(X, Y, 26, 0, 7); c.fill()
      c.strokeStyle = 'rgba(200,240,255,.35)'; c.beginPath(); c.moveTo(X - 40, Y); c.lineTo(X + 40, Y); c.moveTo(X, Y - 30); c.lineTo(X, Y + 30); c.stroke()
      c.fillStyle = '#C8CCD8'; c.font = '10px JetBrains Mono'; c.textAlign = 'center'; c.fillText(s.n.toUpperCase(), X, Y + 70); c.textAlign = 'left'
    })
    const now = performance.now() / 1000
    fly.current = fly.current.filter(f => now - f.t0 < 1.6); fly.current.forEach(f => { const u = (now - f.t0) / 1.6, s = stars[Math.max(0, f.i)]; const x = w * (1.05 - u * (1.05 - s.x)), y = h * (.05 + u * (s.y - .05)); c.fillStyle = '#78D880'; c.shadowColor = '#78D880'; c.shadowBlur = 10; c.beginPath(); c.arc(x, y, 2.5, 0, 7); c.fill(); c.shadowBlur = 0 })
  }
  const line = Math.floor(performance.now() / 2600) % TRANSCRIPT.length
  useEffect(() => { if (engine) return; const i = setTimeout(() => force(x => x + 1), 1300); return () => clearTimeout(i) })
  const hl = (s: string, list = TERMS) => { const parts: any[] = []; let rest = s; list.forEach(tm => { if (rest.includes(tm)) { const [a, b] = rest.split(tm); parts.push(a, <span key={tm} className="chip" style={{ color: 'var(--green)', borderColor: '#2A5A30', background: 'rgba(120,216,128,.08)' }}>{tm}</span>); rest = b } }); parts.push(rest); return parts }
  return <div className="page">
    <div className="row" style={{ alignItems: 'flex-start' }}><div><div className="ptitle">Research</div><div className="psub">SCOUT reads YouTube, GitHub, articles and arXiv day and night. Every star is an idea type; every green dot is a source that fed it.</div></div><button style={{ marginLeft: 'auto' }}>Pause</button></div>
    <div className="grid" style={{ gridTemplateColumns: '2fr 1fr' }}>
      <div className="panel"><Head t="SOURCES PER IDEA TYPE" s="every dot is a source" /><div style={{ height: 520 }}><Canvas draw={draw} /></div></div>
      <div className="grid" style={{ alignContent: 'start' }}>
        {engine ? <div className="panel" data-testid="now-reading"><Head t="LAST SUMMARISED" s={reading ? `${reading.agent || 'SUMMARISER'} · ${reading.model || 'offline'}` : 'from the engine'} /><div className="pb">
          {reading ? <><span className="chip c" style={{ borderColor: '#14505A' }}>{String(reading.idea || '').toUpperCase()}</span>
            <div style={{ fontSize: 15, margin: '8px 0' }}>{reading.title}</div>
            <div style={{ lineHeight: 1.8, fontSize: 12.5, color: '#C8CCD8' }}>{hl(reading.summary || '', reading.highlights.length ? reading.highlights : terms.map(t => t.term))}</div></>
            : <div className="lo">Nothing read yet. The research team starts a round on its schedule, or with POST /research/round.</div>}
          <div className="lbl" style={{ marginTop: 12 }}>TERMS FOUND</div><div className="row" data-testid="terms" style={{ flexWrap: 'wrap', gap: 6, marginTop: 6 }}>{terms.length ? terms.slice(-12).reverse().map(t => <span key={t.term} className="chip g" style={{ borderColor: '#2A5A30' }}>{t.term}</span>) : <span className="lo">none yet</span>}</div>
        </div></div> : <div className="panel"><Head t="NOW READING" /><div className="pb">
          <span className="chip" style={{ color: 'var(--red)', borderColor: '#5A2028' }}>YOUTUBE</span>
          <div style={{ fontSize: 15, margin: '8px 0' }}>Time-series momentum on index futures</div>
          <div className="bar"><i style={{ width: `${(29 + line) / 39 * 100}%`, background: 'var(--blue, #5A8CFF)' }} /></div><div className="lo mono" style={{ fontSize: 10, marginTop: 4 }}>min {29 + line} of 39</div>
          <div style={{ marginTop: 12, lineHeight: 1.9, fontSize: 12.5 }}>{TRANSCRIPT.map((s, i) => <div key={i} style={{ color: i === line ? '#fff' : i < line ? '#5A5F6E' : '#3A3D48' }}>{i === line ? hl(s) : s}</div>)}</div>
          <div className="lbl" style={{ marginTop: 12 }}>TERMS FOUND</div><div className="row" style={{ flexWrap: 'wrap', gap: 6, marginTop: 6 }}>{TERMS.slice(0, 2 + line % 5).map(t => <span key={t} className="chip g" style={{ borderColor: '#2A5A30' }}>{t}</span>)}</div>
        </div></div>}
        <div className="panel"><Head t="THOUGHT STREAM · SCOUT" /><div className="pb mono" style={{ fontSize: 11, lineHeight: 1.8 }}>{engine && !sources.length && <div className="lo">No sources yet.</div>}{sources.slice(-7).reverse().map((s, i) => <div key={s.ts + i}><span className="lo">{new Date(s.ts).toLocaleTimeString('en-GB', { hour12: false })}</span> {s.kind}: "{s.title}" looks like <span className="c">{s.idea}</span>.</div>)}</div></div>
      </div>
    </div>
  </div>
}
