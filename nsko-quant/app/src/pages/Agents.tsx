import { useMemo, useRef, useState } from 'react'
import { Canvas as R3F, useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { useS } from '../store'
import { Head } from '../shell/Shell'

// Agent Room: an isometric 3D office. Every figure is an agent; packets fly desk to desk on real handoff events.
const A: { n: string; col: string; p: [number, number]; role: string; state: 'work' | 'idle' | 'stuck' | 'queue' }[] = [
  { n: 'JARVIS', col: '#E8541A', p: [0, 0], role: 'director · plans the night, hands out work', state: 'work' },
  { n: 'SCOUT', col: '#78D880', p: [-5, -3], role: 'searches YouTube, GitHub, arXiv and the web', state: 'work' },
  { n: 'READER', col: '#E8E8EC', p: [-2, -4], role: 'reads articles and papers', state: 'work' },
  { n: 'WATCHER', col: '#F01848', p: [2, -4], role: 'watches videos, with subtitles', state: 'work' },
  { n: 'SUMMARISER 1', col: '#5A8CFF', p: [5, -3], role: 'turns a source into a summary + idea type', state: 'work' },
  { n: 'SUMMARISER 2', col: '#5A8CFF', p: [6, 0], role: 'turns a source into a summary + idea type', state: 'idle' },
  { n: 'SUMMARISER 3', col: '#5A8CFF', p: [5, 3], role: 'turns a source into a summary + idea type', state: 'queue' },
  { n: 'TERM-CHECKER', col: '#F8A0C0', p: [2, 4], role: 'checks new trading terms against your data', state: 'work' },
  { n: 'RECIPE-MAKER', col: '#E8A850', p: [-2, 4], role: 'turns ideas into strategy recipes', state: 'work' },
  { n: 'LAB', col: '#20E0F0', p: [-5, 3], role: 'tests every recipe as variants', state: 'stuck' },
  { n: 'RISK', col: '#E04858', p: [-6, 0], role: 'checks every plan against your limits', state: 'idle' },
]
const idx = (n: string) => Math.max(0, A.findIndex(a => a.n === n))

function Figure({ a, i, onPick }: { a: typeof A[0]; i: number; onPick: (i: number) => void }) {
  const head = useRef<THREE.Mesh>(null); const screen = useRef<THREE.MeshBasicMaterial>(null)
  useFrame(({ clock }) => { const t = clock.elapsedTime; if (head.current) head.current.position.y = 1.35 + (a.state === 'work' ? Math.sin(t * 8 + i) * .02 : 0); if (screen.current) screen.current.opacity = a.state === 'work' ? .35 + .25 * Math.sin(t * 3 + i * 2) : .15 })
  const col = new THREE.Color(a.col); const isJ = a.n === 'JARVIS'
  return <group position={[a.p[0], 0, a.p[1]]} onClick={e => { e.stopPropagation(); onPick(i) }}>
    {isJ ? <mesh rotation-x={-Math.PI / 2} position-y={.02}><ringGeometry args={[.9, 1.1, 48]} /><meshBasicMaterial color={col} transparent opacity={.8} /></mesh>
      : <mesh position={[0, .4, -.55]}><boxGeometry args={[1.4, .08, .7]} /><meshStandardMaterial color="#14151E" emissive={col} emissiveIntensity={a.state === 'work' ? .25 : .03} /></mesh>}
    {!isJ && <mesh position={[0, 1.05, -.85]}><planeGeometry args={[1.1, .6]} /><meshBasicMaterial ref={screen} color={col} transparent opacity={.3} side={THREE.DoubleSide} /></mesh>}
    <mesh position={[0, .7, 0]}><capsuleGeometry args={[.22, .45, 6, 12]} /><meshStandardMaterial color="#E8E8EC" roughness={.5} /></mesh>
    <mesh ref={head} position={[0, 1.35, 0]}><sphereGeometry args={[.2, 20, 16]} /><meshStandardMaterial color="#F2F2F5" roughness={.35} /></mesh>
    {isJ && <mesh position={[0, 1.8, 0]} rotation-x={Math.PI / 2}><torusGeometry args={[.3, .015, 8, 40]} /><meshBasicMaterial color={col} /></mesh>}
    {a.state === 'stuck' && <mesh position={[.55, .62, -.5]}><sphereGeometry args={[.08, 12, 8]} /><meshBasicMaterial color="#E04858" /></mesh>}
    {a.state === 'idle' && <mesh position={[.45, .52, -.4]}><cylinderGeometry args={[.06, .05, .14, 12]} /><meshStandardMaterial color="#C8A070" /></mesh>}
    {a.state === 'queue' && [0, 1, 2].map(k => <mesh key={k} position={[-.5, .47 + k * .03, -.45]}><boxGeometry args={[.3, .02, .22]} /><meshStandardMaterial color="#D8D8DC" /></mesh>)}
  </group>
}

function Packets() {
  const handoffs = useS(s => s.handoffs); const group = useRef<THREE.Group>(null)
  const live = useRef<{ from: number; to: number; t0: number; m: THREE.Mesh }[]>([]); const seen = useRef(0)
  useFrame(({ clock }) => {
    const g = group.current!; const now = clock.elapsedTime
    while (seen.current < handoffs.length) { const h = handoffs[seen.current++]; const m = new THREE.Mesh(new THREE.SphereGeometry(.07, 10, 8), new THREE.MeshBasicMaterial({ color: A[idx(h.from)].col })); g.add(m); live.current.push({ from: idx(h.from), to: idx(h.to), t0: now, m }) }
    live.current = live.current.filter(p => { const u = (now - p.t0) / 1.6; if (u > 1) { g.remove(p.m); return false } const a = A[p.from].p, b = A[p.to].p; p.m.position.set(a[0] + (b[0] - a[0]) * u, 1.2 + Math.sin(u * Math.PI) * 1.4, a[1] + (b[1] - a[1]) * u); return true })
  })
  return <group ref={group} />
}

function Cam({ mode, focus }: { mode: string; focus: number | null }) {
  const { camera } = useThree(); const tgt = useRef(new THREE.Vector3()); const handoffs = useS(s => s.handoffs)
  useFrame(({ clock }, dt) => {
    let pos: THREE.Vector3, look: THREE.Vector3
    if (focus !== null) { const p = A[focus].p; pos = new THREE.Vector3(p[0] + 2.2, 2.4, p[1] + 2.6); look = new THREE.Vector3(p[0], 1, p[1]) }
    else if (mode === 'top') { pos = new THREE.Vector3(0, 16, .01); look = new THREE.Vector3() }
    else if (mode === 'floor') { pos = new THREE.Vector3(Math.sin(clock.elapsedTime * .05) * 9, 1.6, 9); look = new THREE.Vector3(0, 1, 0) }
    else if (mode === 'follow' && handoffs.length) { const p = A[idx(handoffs[handoffs.length - 1].to)].p; pos = new THREE.Vector3(p[0] + 4, 5, p[1] + 5); look = new THREE.Vector3(p[0], 1, p[1]) }
    else { pos = new THREE.Vector3(11, 10, 11); look = new THREE.Vector3() }
    const k = 1 - Math.exp(-dt * 2.6); camera.position.lerp(pos, k); tgt.current.lerp(look, k); camera.lookAt(tgt.current)
  })
  return null
}

const STATE: Record<string, (typeof A)[0]['state']> = { working: 'work', busy: 'work', idle: 'idle', paused: 'stuck', error: 'stuck', stuck: 'stuck', queued: 'queue', waiting: 'queue' }
export default function Agents() {
  const [mode, setMode] = useState('overview'); const [focus, setFocus] = useState<number | null>(null); const [table, setTable] = useState(false)
  const handoffs = useS(s => s.handoffs); const sources = useS(s => s.sources); const agents = useS(s => s.agents); const budget = useS(s => s.budget)
  const source = useS(s => s.source), fallback = useS(s => s.fallback); const engine = source === 'engine' && !fallback
  // engine: each figure's state is the last agent_status the engine sent for it (idle until it has sent one)
  const AA = useMemo(() => engine ? A.map(x => ({ ...x, state: STATE[agents[x.n]?.status] || 'idle' as const })) : A, [engine, agents])
  const grid = useMemo(() => new THREE.GridHelper(18, 18, '#1A1C26', '#12131B'), [])
  const a = focus !== null ? AA[focus] : null
  return <div className="page">
    <div className="ptitle">Agent Room</div><div className="psub">The JARVIS team at work. Every movement is a real task: packets fly between desks when work is handed over.{engine ? ' Live from the engine: counts start when this window connected.' : ''}</div>
    <div className="panel" style={{ display: 'flex', marginBottom: 12 }}>{(engine ? [['BUSY NOW', Object.values(agents).filter(x => STATE[x.status] === 'work').length], ['HANDOFFS', handoffs.length], ['SOURCES READ', sources.length], ['STATUS UPDATES', Object.keys(agents).length], ['THINK BUDGET', `${budget.used.toFixed(1)} of ${budget.of} units`]]
      : [['TASKS', 273 + handoffs.length], ['HANDOFFS', 135 + handoffs.length], ['SOURCES READ', 100 + sources.length], ['SUMMARISED', 94 + Math.floor(sources.length * .9)], ['COST', '£0.20 · local model']]).map(([l, v]) =>
      <div key={l as string} style={{ flex: 1, padding: 14, borderRight: '1px solid var(--line)' }}><div className="lbl">{l}</div><div className="big" style={{ fontSize: 20 }}>{v}</div></div>)}</div>
    <div className="panel"><Head t="THE WORKFLOOR" s="every movement is a real task">
      {[['overview', 'Overview'], ['top', 'Top down'], ['floor', 'Floor'], ['follow', '◎ Follow the work']].map(([k, n]) => <button key={k} onClick={() => { setMode(k); setFocus(null) }} style={{ padding: '3px 8px', fontSize: 10, borderColor: mode === k && focus === null ? 'var(--orange)' : undefined }}>{n}</button>)}
      <button onClick={() => setTable(!table)} style={{ padding: '3px 8px', fontSize: 10 }}>{table ? 'SHOW AS ROOM' : 'SHOW AS TABLE'}</button></Head>
      {table ? <table><thead><tr><th>Agent</th><th>Role</th><th>State</th>{engine && <th>Last item</th>}</tr></thead><tbody>{AA.map(x => <tr key={x.n}><td style={{ color: x.col }}>{x.n}</td><td>{x.role}</td><td>{x.state}</td>{engine && <td className="lo">{agents[x.n]?.item || '—'}</td>}</tr>)}</tbody></table> :
        <div style={{ height: 560, position: 'relative' }}>
          <R3F camera={{ position: [11, 10, 11], fov: 35 }} dpr={[1, 2]} onPointerMissed={() => setFocus(null)}>
            <color attach="background" args={['#06070C']} /><fog attach="fog" args={['#06070C', 18, 36]} />
            <ambientLight intensity={.35} /><directionalLight position={[5, 10, 4]} intensity={1.1} /><pointLight position={[0, 3, 0]} color="#E8541A" intensity={6} distance={6} />
            <primitive object={grid} />
            <lineSegments><edgesGeometry args={[new THREE.BoxGeometry(17, .01, 11)]} /><lineBasicMaterial color="#5A5F6E" /></lineSegments>
            {AA.map((x, i) => <Figure key={x.n + x.state} a={x} i={i} onPick={setFocus} />)}
            <Packets /><Cam mode={mode} focus={focus} />
          </R3F>
          <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>{/* labels are drawn in the legend + panel to keep the 3D clean */}</div>
          {a && <div className="panel" style={{ position: 'absolute', right: 12, top: 12, bottom: 12, width: 320, padding: 14, background: 'rgba(12,13,20,.94)' }}>
            <div className="row"><span className="dot" style={{ background: a.col }} /><span className="mono" style={{ letterSpacing: '.1em' }}>{a.n}</span><span className="chip" style={{ marginLeft: 'auto', color: a.state === 'stuck' ? 'var(--red)' : 'var(--green)', borderColor: 'var(--line)' }}>{a.state === 'stuck' ? 'STUCK' : a.state === 'work' ? 'BUSY' : a.state.toUpperCase()}</span></div>
            <div className="lo" style={{ margin: '4px 0 12px' }}>{a.role}</div>
            {(engine ? [['NOW', agents[a.n] ? `${agents[a.n].status}${agents[a.n].item ? ` · "${agents[a.n].item}"` : ''}` : 'No status from the engine yet'], ['LAST UPDATE', agents[a.n] ? new Date(agents[a.n].ts).toLocaleTimeString('en-GB', { hour12: false }) : '—'],
              ['HANDED TO', handoffs.filter(h => h.from === a.n).slice(-1)[0]?.to || '—'], ['RECEIVED FROM', handoffs.filter(h => h.to === a.n).slice(-1)[0]?.from || '—']] : [['NOW', a.n === 'WATCHER' ? 'Watching "Time-series momentum on index futures", minute 4 of 39' : a.state === 'stuck' ? 'Waiting for 2009 gold history: data request timed out, retrying' : 'Working on "' + (sources[sources.length - 1]?.title || 'Order blocks explained') + '"'],
              ['BEFORE', 'Finished "Seasonality in precious metals" (12 min)'], ['HEARD', '"the order block is the last down candle before the move"'], ['NEXT STEP', 'Hand the summary to RECIPE-MAKER']]).map(([k, v]) =>
              <div key={k} style={{ marginBottom: 10 }}><div className="lbl">{k}</div><div style={{ fontSize: 12.5, marginTop: 3, lineHeight: 1.5, ...(k === 'HEARD' ? { border: '1px solid #5A4020', background: 'rgba(232,168,80,.06)', padding: 6 } : {}) }}>{v}</div></div>)}
            <button onClick={() => setFocus(null)} style={{ marginTop: 6, pointerEvents: 'auto' }}>‹ Back to the room ›</button></div>}
        </div>}
      <div className="row mono lo" style={{ padding: '8px 14px', borderTop: '1px solid var(--line)', fontSize: 10, flexWrap: 'wrap', gap: 14 }}>{A.map(x => <span key={x.n}><span className="dot" style={{ background: x.col }} /> {x.n}</span>)}
        <span style={{ marginLeft: 'auto' }}>desk light: working · coffee: resting · red lamp: stuck · packet: work between desks · stack: work waiting · click an agent</span></div>
    </div>
    {engine && <div className="panel" style={{ marginTop: 12 }} data-testid="handoffs"><Head t="HANDOFFS" s="agent_handoff events from the engine" /><table><tbody>{handoffs.length ? handoffs.slice(-10).reverse().map((h, i) => <tr key={h.ts + i}><td className="lo mono">{new Date(h.ts).toLocaleTimeString('en-GB', { hour12: false })}</td><td>{h.from}</td><td className="lo">→</td><td>{h.to}</td></tr>)
      : <tr><td className="lo">No handoffs yet. They arrive when a research round, a Lab run or a trade debate runs.</td></tr>}</tbody></table></div>}
  </div>
}
