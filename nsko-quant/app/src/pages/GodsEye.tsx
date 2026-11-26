import { useMemo, useRef, useState } from 'react'
import { Canvas as R3F, useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { Canvas } from '../viz/canvas'
import { Head } from '../shell/Shell'

// God's Eye, Stage 1 shell: a dark 3D globe with demo layers. Stage 3 swaps in CesiumJS and the free live feeds.
const LAYERS: [string, string][] = [['Flights', '#E8E8A0'], ['Military', '#E8A850'], ['Ships', '#20E0F0'], ['Satellites', '#C8CCD8'], ['Quakes', '#E04858'], ['Fires', '#E8541A'], ['Weather', '#5A8CFF'], ['Launches', '#F8A0C0'], ['Crops', '#78D880']]
const ll = (lat: number, lon: number, r = 1.002) => { const p = (90 - lat) * Math.PI / 180, t = (lon + 180) * Math.PI / 180; return new THREE.Vector3(-r * Math.sin(p) * Math.cos(t), r * Math.cos(p), r * Math.sin(p) * Math.sin(t)) }
const SEEDS: Record<string, [number, number][]> = {
  Flights: Array.from({ length: 260 }, (_, i) => [((i * 37) % 120) - 50 + (i % 3) * 5, ((i * 91) % 300) - 150] as [number, number]).filter(([la, lo]) => !(lo < -30 && lo > -60 && la < 0)),
  Military: [[26, 56], [35, 33], [49, 32], [36, 129], [24, 121], [52, 20]],
  Ships: Array.from({ length: 120 }, (_, i) => { const lanes = [[26.5, 56.3, 12, 45], [12, 45, 30, 32.5], [1.3, 103.8, 22, 114], [36, -6, 50, 0], [30, 32.5, 36, -6]]; const l = lanes[i % 5], u = (i * .137) % 1; return [l[0] + (l[2] - l[0]) * u, l[1] + (l[3] - l[1]) * u] as [number, number] }),
  Quakes: [[-33.4, -70.6], [38.3, 142.4], [36.2, 28.0]], Fires: [[-25, 135], [-28, 145], [-12, -55], [38, -120], [-8, 25]],
  Weather: [[-19.9, -44], [6.8, -5.3], [40, -95]], Launches: [[28.5, -80.6], [45.9, 63.3], [19.6, 110.9]], Crops: [[-19.9, -44.5], [6.8, -5.3], [7.9, -1.0], [41, -93], [48, 35]],
}
function Globe({ on, sensor }: { on: Record<string, boolean>; sensor: string }) {
  const g = useRef<THREE.Group>(null)
  const land = useMemo(() => { // procedural continents from a few blobs: a stand-in until the Stage 3 imagery
    const blobs = [[50, 10, 25], [5, 20, 28], [45, 90, 38], [40, -100, 25], [-15, -60, 22], [-25, 135, 15], [65, -40, 10], [20, 78, 12], [60, 100, 30]]
    const pts: number[] = []; for (let i = 0; i < 14000; i++) { const y = 1 - (i / 13999) * 2, r = Math.sqrt(1 - y * y), th = i * 2.39996; const lat = Math.asin(y) * 180 / Math.PI, lon = ((th * 180 / Math.PI) % 360) - 180
      if (blobs.some(([a, b, s]) => (lat - a) ** 2 + ((lon - b) * Math.cos(lat * Math.PI / 180)) ** 2 < s * s)) pts.push(Math.cos(th) * r * 1.001, y * 1.001, Math.sin(th) * r * 1.001) }
    const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3)); return geo }, [])
  const layerGeo = useMemo(() => Object.fromEntries(Object.entries(SEEDS).map(([k, v]) => { const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(v.flatMap(([a, b]) => ll(a, b, k === 'Satellites' ? 1.25 : 1.006).toArray()), 3)); return [k, geo] })), [])
  const sats = useMemo(() => { const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(Array.from({ length: 160 }, (_, i) => { const a = i * .7, inc = (i % 6) * .5; return [Math.cos(a) * 1.3, Math.sin(a) * Math.sin(inc) * 1.3, Math.sin(a) * Math.cos(inc) * 1.3] }).flat(), 3)); return geo }, [])
  useFrame((_, dt) => { if (g.current) g.current.rotation.y += dt * .05 })
  const tint = sensor === 'Night-vision' ? '#2A8A3A' : sensor === 'Thermal' ? '#8A2A6A' : '#1A2A4A'
  return <group ref={g} rotation={[.35, 0, 0]}>
    <mesh><sphereGeometry args={[1, 64, 48]} /><meshStandardMaterial color={tint} roughness={.9} emissive={tint} emissiveIntensity={.25} /></mesh>
    <points geometry={land}><pointsMaterial size={.008} color={sensor === 'Night-vision' ? '#7AFF8A' : sensor === 'Thermal' ? '#FFB060' : '#5A7AA0'} /></points>
    <mesh scale={1.06}><sphereGeometry args={[1, 32, 24]} /><meshBasicMaterial color="#20E0F0" transparent opacity={.05} side={THREE.BackSide} /></mesh>
    {LAYERS.map(([k, col]) => on[k] && k !== 'Satellites' && SEEDS[k] && <points key={k} geometry={layerGeo[k]}><pointsMaterial size={k === 'Flights' ? .016 : .04} color={col} /></points>)}
    {on.Satellites && <points geometry={sats}><pointsMaterial size={.02} color="#E8E8EC" /></points>}
    {on.Satellites && [0, 1, 2].map(i => <mesh key={i} rotation={[Math.PI / 2 + i * .5, i * .8, 0]}><torusGeometry args={[1.3, .0015, 4, 120]} /><meshBasicMaterial color="#5A5F6E" /></mesh>)}
  </group>
}
const IMPACT = [
  ['TANKER SLOWDOWN · STRAIT OF HORMUZ', 'Oil ↑ watch · Gold safe-haven watch', 'JARVIS: 14 tankers below 4 kn for 6h (demo). Watching Brent; no trade opened.', 'var(--cyan)'],
  ['FROST RISK · MINAS GERAIS', 'Arabica coffee watch', 'JARVIS: GFS shows −1 °C at dawn over the coffee belt (demo). Sent to Research.', 'var(--blue, #5A8CFF)'],
  ['M6.4 QUAKE · NEAR COPPER MINES, CHILE', 'Copper / metals watch', 'JARVIS: risk action → cut size 50% on metals for 24h (demo).', 'var(--red)'],
]
export default function GodsEye() {
  const [tab, setTab] = useState<'globe' | 'alt'>('globe'); const [sensor, setSensor] = useState('Normal'); const [time, setTime] = useState(24)
  const [on, setOn] = useState<Record<string, boolean>>(Object.fromEntries(LAYERS.map(([k]) => [k, !['Weather', 'Launches'].includes(k)])))
  return <div className="page" style={{ padding: 0, position: 'relative', background: '#04050A' }}>
    <div className="row" style={{ position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)', zIndex: 5, gap: 4 }}>
      {(['globe', 'alt'] as const).map(t => <button key={t} onClick={() => setTab(t)} style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.12em', borderColor: tab === t ? 'var(--orange)' : undefined, background: '#0A0B12' }}>{t === 'globe' ? 'GLOBE' : 'ALT-DATA LAB'}</button>)}</div>
    {tab === 'globe' ? <>
      <div style={{ position: 'absolute', inset: 0 }}>
        <R3F camera={{ position: [0, 0, 3.1], fov: 40 }} dpr={[1, 2]}><color attach="background" args={['#04050A']} /><ambientLight intensity={.6} /><directionalLight position={[3, 2, 4]} intensity={1.2} /><Globe on={on} sensor={sensor} /></R3F>
      </div>
      <div className="mono lo" style={{ position: 'absolute', top: 14, left: 16, fontSize: 10, lineHeight: 1.7, zIndex: 4 }}><div style={{ color: 'var(--hi)', letterSpacing: '.16em' }}>GOD'S EYE · NSKO QUANT</div>51.5072° N · 0.1276° W<br />{new Date().toISOString().slice(11, 19)} UTC · <span className="o">{sensor.toUpperCase()}</span> · DEMO LAYERS</div>
      <div className="panel" style={{ position: 'absolute', left: 16, top: 90, width: 170, padding: 10, zIndex: 4, background: 'rgba(12,13,20,.85)' }}>
        <div className="lbl" style={{ marginBottom: 6 }}>LAYERS</div>{LAYERS.map(([k, col]) => <label key={k} className="row" style={{ gap: 8, padding: '3px 0', fontSize: 12, cursor: 'pointer' }}><input type="checkbox" checked={!!on[k]} onChange={() => setOn({ ...on, [k]: !on[k] })} /><span className="dot" style={{ background: col }} />{k}</label>)}
        <div className="lbl" style={{ margin: '10px 0 6px' }}>SENSOR</div>{['Normal', 'Night-vision', 'Thermal'].map(s => <button key={s} onClick={() => setSensor(s)} style={{ display: 'block', width: '100%', marginBottom: 4, fontSize: 11, borderColor: sensor === s ? 'var(--orange)' : undefined }}>{s}</button>)}
        <div className="lo" style={{ fontSize: 9, marginTop: 8, lineHeight: 1.5 }}>Stage 3 sources: adsb.lol · AISStream · CelesTrak · USGS · NASA FIRMS · Open-Meteo · Launch Library 2 · Sentinel-2</div></div>
      <div style={{ position: 'absolute', right: 16, top: 60, width: 320, zIndex: 4 }}><div className="lbl" style={{ marginBottom: 6 }}>MARKET IMPACT</div>
        {IMPACT.map(([t, asset, note, col]) => <div key={t} className="panel" style={{ padding: 10, marginBottom: 8, borderLeft: `2px solid ${col}`, background: 'rgba(12,13,20,.9)' }}>
          <div className="mono" style={{ fontSize: 10.5, letterSpacing: '.06em' }}>{t}</div><div className="a" style={{ fontSize: 11.5, margin: '4px 0' }}>{asset}</div><div className="lo" style={{ fontSize: 11, lineHeight: 1.5 }}>{note}</div>
          <div className="row" style={{ marginTop: 8, gap: 6 }}><button style={{ fontSize: 10.5, padding: '3px 8px' }}>Send to Research</button><span className="lo" style={{ fontSize: 9.5 }}>never opens a trade by itself</span></div></div>)}</div>
      <div className="panel" style={{ position: 'absolute', left: 200, right: 350, bottom: 16, padding: '8px 14px', zIndex: 4, background: 'rgba(12,13,20,.85)' }}>
        <div className="row"><span className="lbl">24H TIMELINE</span><input type="range" min={0} max={24} value={time} onChange={e => setTime(+e.target.value)} style={{ flex: 1, accentColor: '#E8541A' }} /><span className="num">{time === 24 ? 'NOW' : `−${24 - time}h`}</span></div></div>
    </> : <AltData />}
  </div>
}

function Tile({ title, sub, count, unit, locked, draw, bars, note }: any) {
  return <div className="panel" style={{ overflow: 'hidden' }}><Head t={title} s={sub}>{locked && <span className="chip a" style={{ borderColor: '#5A4020' }}>PREMIUM 🔒</span>}</Head>
    <div style={{ height: 230, position: 'relative', filter: locked ? 'blur(2px) brightness(.6)' : undefined }}><Canvas draw={draw} />
      <div style={{ position: 'absolute', left: 14, bottom: 12 }}><div className="num" style={{ fontSize: 34, textShadow: '0 2px 12px #000' }}>{count}</div><div className="lbl" style={{ color: '#C8CCD8' }}>{unit}</div></div></div>
    <div className="pb"><div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 60 }}>{bars.map((b: number, i: number) => <i key={i} style={{ flex: 1, height: `${b * 100}%`, background: i > bars.length - 4 ? 'var(--cyan)' : '#1F4A55' }} />)}</div>
      <div className="lo" style={{ fontSize: 11, marginTop: 8 }}>{note}</div></div></div>
}
function AltData() {
  const field = (c: CanvasRenderingContext2D, w: number, h: number, t: number) => { // Crop Watch: NDVI-style field mosaic with a frost overlay
    for (let y = 0; y < h; y += 14) for (let x = 0; x < w; x += 18) { const v = (Math.sin(x * .07 + y * .05) + Math.sin(x * .013 - y * .09)) * .25 + .5; c.fillStyle = `rgb(${40 + v * 60},${70 + v * 90},${30 + v * 30})`; c.fillRect(x, y, 17, 13) }
    const fr = .5 + .5 * Math.sin(t * .8); c.fillStyle = `rgba(120,170,255,${.15 + fr * .2})`; c.beginPath(); c.ellipse(w * .6, h * .45, w * .3, h * .3, .3, 0, 7); c.fill()
    c.strokeStyle = '#20E0F0'; c.setLineDash([4, 3]); c.strokeRect(w * .35, h * .2, w * .5, h * .5); c.setLineDash([]); c.fillStyle = '#20E0F0'; c.font = '10px JetBrains Mono'; c.fillText('FROST RISK · NDVI ↓', w * .36, h * .18) }
  const tanks = (c: CanvasRenderingContext2D, w: number, h: number, t: number) => {
    c.fillStyle = '#3A4A38'; c.fillRect(0, 0, w, h)
    for (let i = 0; i < 12; i++) { const x = 40 + (i % 4) * (w - 80) / 3, y = 50 + Math.floor(i / 4) * 70, r = 24, fill = .3 + ((i * 37) % 60) / 100; c.fillStyle = '#C8CCC4'; c.beginPath(); c.arc(x, y, r, 0, 7); c.fill(); c.fillStyle = `rgba(0,0,0,${.55 * (1 - fill)})`; c.beginPath(); c.arc(x - r * (1 - fill) * .4, y, r * .92, 0, 7); c.fill()
      c.strokeStyle = `rgba(32,224,240,${.6 + .4 * Math.sin(t * 2 + i)})`; c.lineWidth = 2; c.beginPath(); c.arc(x, y, r + 5, 0, 7); c.stroke(); c.lineWidth = 1 } }
  const cars = (c: CanvasRenderingContext2D, w: number, h: number) => { c.fillStyle = '#5A5E64'; c.fillRect(0, 0, w, h); for (let i = 0; i < 160; i++) { const x = 20 + (i % 20) * (w - 40) / 20, y = 20 + Math.floor(i / 20) * 26; if ((i * 7) % 5) { c.fillStyle = ['#D8D8DC', '#202024', '#8A2020', '#3050A0'][i % 4]; c.fillRect(x, y, 10, 16); c.strokeStyle = '#20E0F0'; c.strokeRect(x - 2, y - 2, 14, 20) } } }
  return <div className="page" style={{ paddingTop: 54 }}>
    <div className="ptitle">Alt-Data Lab</div><div className="psub">How the big desks use satellites, in a form you can use. Context and risk only: alternative data never opens a trade by itself. All tiles show DEMO data in Stage 1.</div>
    <div className="grid" style={{ gridTemplateColumns: 'repeat(3,1fr)' }}>
      <Tile title="CROP WATCH" sub="Sentinel-2 NDVI · coffee, cocoa, wheat" count="−7.4%" unit="NDVI vs 5-yr norm · Minas Gerais" draw={field} bars={[.4, .45, .5, .48, .52, .5, .47, .44, .36, .3]} note="Arabica coffee futures watch · frost forecast −1 °C at dawn (demo)" />
      <Tile title="OIL STORAGE" sub="V1: EIA weekly stocks · imagery later" count="12" unit="tanks measured · Cushing-style farm" draw={tanks} bars={[.6, .62, .58, .55, .57, .52, .5, .46, .44, .41]} note="Floating roofs sinking = stocks falling (demo). Imagery version is premium." />
      <Tile title="CAR COUNTS" sub="retail car parks" count="414" unit="cars counted · RETAILER" draw={cars} locked bars={[.5, .52, .49, .55, .53, .5, .58, .62, .7, .78]} note="Premium placeholder. No real store names or logos." />
    </div>
  </div>
}
