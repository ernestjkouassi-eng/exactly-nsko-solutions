import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Viewer, Ion, EllipsoidTerrainProvider, ImageryLayer, TileMapServiceImageryProvider, UrlTemplateImageryProvider, OpenStreetMapImageryProvider, buildModuleUrl,
  PointPrimitiveCollection, LabelCollection, Cartesian3, Cartesian2, Color, PostProcessStageLibrary, PostProcessStage, NearFarScalar, ScreenSpaceEventHandler, ScreenSpaceEventType,
  type PointPrimitive, LabelStyle, VerticalOrigin, Math as CMath,
} from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import { Canvas } from '../viz/canvas'
import { Head } from '../shell/Shell'
import { useS, type GeoPt } from '../store'
import { reducedMotion } from '../tokens'

// God's Eye (Stage 3): CesiumJS globe with free imagery and NO Cesium ion (no ion token, no ion assets, no Google 3D Tiles).
// Layers render from gods_eye_event / market_impact events: from the engine, or from the demo simulator in demo mode.
;(Ion as { defaultAccessToken?: string }).defaultAccessToken = undefined

const LAYERS: [string, string, string][] = [
  ['Flights', '#E8E8A0', 'adsb.lol (ODbL 1.0)'], ['Military', '#E8A850', 'adsb.lol military feed (ODbL 1.0)'], ['Ships', '#20E0F0', 'AISStream.io'],
  ['Satellites', '#C8CCD8', 'CelesTrak GP data'], ['Quakes', '#E04858', 'USGS Earthquake Hazards Program'], ['Fires', '#E8541A', 'NASA FIRMS (LANCE)'],
  ['Weather', '#5A8CFF', 'Open-Meteo (CC BY 4.0)'], ['Launches', '#F8A0C0', 'Launch Library 2 · The Space Devs'], ['Crops', '#78D880', 'Copernicus Sentinel-2 (modified Copernicus data)'],
]
const TRACKS = new Set(['Flights', 'Ships', 'Satellites'])   // moving objects: always shown at their latest position
const BASEMAPS = {
  satellite: { name: 'Satellite', credit: 'Imagery: Esri World Imagery · Esri, Maxar, Earthstar Geographics, and the GIS User Community' },
  map: { name: 'Map', credit: 'Map: © OpenStreetMap contributors (ODbL) · tile.openstreetmap.org' },
  offline: { name: 'Offline', credit: 'Imagery: Natural Earth II (public domain, bundled with CesiumJS)' },
} as const
type Basemap = keyof typeof BASEMAPS
const TONE: Record<string, string> = { cyan: 'var(--cyan)', blue: '#5A8CFF', red: 'var(--red)', amber: 'var(--amber)', green: 'var(--green)', orange: 'var(--orange)' }

const THERMAL = `uniform sampler2D colorTexture; in vec2 v_textureCoordinates;
void main() {
  vec3 c = texture(colorTexture, v_textureCoordinates).rgb; float l = clamp(dot(c, vec3(0.299, 0.587, 0.114)) * 1.25, 0.0, 1.0);
  vec3 t = l < 0.25 ? mix(vec3(0.02, 0.0, 0.08), vec3(0.35, 0.0, 0.55), l / 0.25)
         : l < 0.5 ? mix(vec3(0.35, 0.0, 0.55), vec3(0.9, 0.15, 0.1), (l - 0.25) / 0.25)
         : l < 0.75 ? mix(vec3(0.9, 0.15, 0.1), vec3(1.0, 0.75, 0.0), (l - 0.5) / 0.25)
         : mix(vec3(1.0, 0.75, 0.0), vec3(1.0, 1.0, 0.92), (l - 0.75) / 0.25);
  out_FragColor = vec4(t, 1.0);
}`

function Globe({ on, sensor, basemap, cutoff }: { on: Record<string, boolean>; sensor: string; basemap: Basemap; cutoff: number }) {
  const box = useRef<HTMLDivElement>(null); const credits = useRef<HTMLDivElement>(null); const viewer = useRef<Viewer | null>(null)
  const cols = useRef<Record<string, PointPrimitiveCollection>>({}); const prims = useRef<Record<string, Map<string, PointPrimitive>>>({})
  const labels = useRef<LabelCollection | null>(null); const impactPts = useRef<PointPrimitiveCollection | null>(null)
  const [err, setErr] = useState('')
  const geo = useS(s => s.geo), geoV = useS(s => s.geoV), impacts = useS(s => s.impacts)

  useEffect(() => {   // create the viewer once
    let v: Viewer
    try {
      v = new Viewer(box.current!, {
        baseLayer: false, baseLayerPicker: false, geocoder: false, homeButton: false, sceneModePicker: false, navigationHelpButton: false, animation: false, timeline: false,
        fullscreenButton: false, infoBox: false, selectionIndicator: false, vrButton: false, projectionPicker: false,
        terrainProvider: new EllipsoidTerrainProvider(), creditContainer: credits.current!, msaaSamples: 1,
      })
    } catch (e) { setErr(`3D globe unavailable: ${String(e).slice(0, 140)}`); return }
    viewer.current = v
    const sc = v.scene
    sc.backgroundColor = Color.fromCssColorString('#04050A'); if (sc.skyBox) sc.skyBox.show = false; if (sc.sun) sc.sun.show = false; if (sc.moon) sc.moon.show = false
    sc.globe.baseColor = Color.fromCssColorString('#0A1222'); sc.globe.showGroundAtmosphere = true
    if (sc.skyAtmosphere) { sc.skyAtmosphere.hueShift = -0.05; sc.skyAtmosphere.brightnessShift = -0.35 }
    sc.screenSpaceCameraController.minimumZoomDistance = 250000
    v.camera.setView({ destination: Cartesian3.fromDegrees(18, 22, 21000000) })
    for (const [k] of LAYERS) { cols.current[k] = sc.primitives.add(new PointPrimitiveCollection()); prims.current[k] = new Map() }
    impactPts.current = sc.primitives.add(new PointPrimitiveCollection()); labels.current = sc.primitives.add(new LabelCollection())
    // gentle idle spin, stopped by the first drag (and never under reduced motion)
    let spin = !reducedMotion(); const h = new ScreenSpaceEventHandler(sc.canvas); h.setInputAction(() => { spin = false }, ScreenSpaceEventType.LEFT_DOWN); h.setInputAction(() => { spin = false }, ScreenSpaceEventType.WHEEL)
    const rm = sc.preUpdate.addEventListener(() => { if (spin) v.camera.rotate(Cartesian3.UNIT_Z, -CMath.toRadians(0.02)) })
    return () => { rm(); h.destroy(); v.destroy(); viewer.current = null; cols.current = {}; prims.current = {} }
  }, [])

  useEffect(() => {   // basemap: Natural Earth II (bundled, works offline) always underneath, free online imagery on top
    const v = viewer.current; if (!v) return
    const L = v.imageryLayers; L.removeAll()
    L.add(ImageryLayer.fromProviderAsync(TileMapServiceImageryProvider.fromUrl(buildModuleUrl('Assets/Textures/NaturalEarthII')), { brightness: .7 }))
    if (basemap === 'satellite') L.add(new ImageryLayer(new UrlTemplateImageryProvider({ url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', maximumLevel: 18, credit: 'Esri, Maxar, Earthstar Geographics, and the GIS User Community' }), { brightness: .82, saturation: .85 }))
    if (basemap === 'map') L.add(new ImageryLayer(new OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/', maximumLevel: 19 }), { brightness: .42, contrast: 1.25, saturation: .25, gamma: 1.1 }))
  }, [basemap])

  useEffect(() => {   // sensor modes as post-process stages
    const v = viewer.current; if (!v) return
    const st = v.scene.postProcessStages; st.removeAll()
    if (sensor === 'Night-vision') st.add(PostProcessStageLibrary.createNightVisionStage())
    if (sensor === 'Thermal') st.add(new PostProcessStage({ fragmentShader: THERMAL }))
  }, [sensor])

  useEffect(() => {   // points: update in place, add new, remove gone
    if (!viewer.current) return
    const want: Record<string, Map<string, GeoPt>> = {}
    for (const g of Object.values(geo)) { if (!on[g.layer]) continue; if (!TRACKS.has(g.layer) && (g.ts > cutoff || g.ts < cutoff - 24 * 3600e3)) continue; (want[g.layer] ||= new Map()).set(g.id, g) }
    for (const [k, col] of LAYERS) {
      const c = cols.current[k], m = prims.current[k]; if (!c || !m) continue
      const w = want[k] || new Map<string, GeoPt>(); const color = Color.fromCssColorString(col)
      for (const [id, p] of m) if (!w.has(id)) { c.remove(p); m.delete(id) }
      for (const [id, g] of w) {
        const pos = Cartesian3.fromDegrees(g.lon, g.lat, g.alt || 0); const p = m.get(id)
        if (p) p.position = pos
        else m.set(id, c.add({ position: pos, color, pixelSize: TRACKS.has(k) ? (k === 'Satellites' ? 3 : 3.5) : 8, outlineColor: Color.fromCssColorString('#08080F'), outlineWidth: TRACKS.has(k) ? 0 : 1.5, scaleByDistance: new NearFarScalar(1.5e6, 1.6, 2.5e7, .8) }))
      }
    }
  }, [geoV, on, cutoff])

  useEffect(() => {   // market-impact markers with a short label
    const pc = impactPts.current, lc = labels.current; if (!pc || !lc) return
    pc.removeAll(); lc.removeAll()
    impacts.filter(i => i.lat != null && i.lon != null).forEach(i => {
      const pos = Cartesian3.fromDegrees(i.lon!, i.lat!, 0)
      pc.add({ position: pos, pixelSize: 14, color: Color.TRANSPARENT, outlineColor: Color.fromCssColorString('#E8541A'), outlineWidth: 2 })
      lc.add({ position: pos, text: i.title.split('·')[0].trim(), font: '10px "JetBrains Mono", monospace', fillColor: Color.fromCssColorString('#E8E8EC'), outlineColor: Color.fromCssColorString('#04050A'), outlineWidth: 3, style: LabelStyle.FILL_AND_OUTLINE, verticalOrigin: VerticalOrigin.BOTTOM, pixelOffset: new Cartesian2(0, -12), scaleByDistance: new NearFarScalar(1.5e6, 1.2, 2.5e7, .85) })
    })
  }, [impacts])

  return <>
    <div ref={box} className="nq-cesium" style={{ position: 'absolute', inset: 0 }} />
    {err && <div className="empty" style={{ position: 'absolute', left: '50%', top: '45%', transform: 'translateX(-50%)', zIndex: 3, background: '#0A0B12' }}>{err}</div>}
    <div ref={credits} className="nq-credits" />
  </>
}

export default function GodsEye() {
  const [tab, setTab] = useState<'globe' | 'alt'>('globe'); const [sensor, setSensor] = useState('Normal'); const [time, setTime] = useState(24); const [basemap, setBasemap] = useState<Basemap>('satellite')
  const [on, setOn] = useState<Record<string, boolean>>(Object.fromEntries(LAYERS.map(([k]) => [k, !['Weather', 'Launches'].includes(k)])))
  const impacts = useS(s => s.impacts), demo = useS(s => s.demo), geo = useS(s => s.geo), geoV = useS(s => s.geoV)
  const [now, setNow] = useState(Date.now()); useEffect(() => { const i = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(i) }, [])
  const cutoff = useMemo(() => Math.floor(now / 60000) * 60000 - (24 - time) * 3600e3 + 59999, [Math.floor(now / 60000), time])
  const counts = useMemo(() => { const c: Record<string, number> = {}; for (const g of Object.values(geo)) c[g.layer] = (c[g.layer] || 0) + 1; return c }, [geoV])
  const attribution = [BASEMAPS[basemap].credit, ...LAYERS.filter(([k]) => on[k]).map(([k, , src]) => `${k}: ${src}`)]
  return <div className="page" style={{ padding: 0, position: 'relative', background: '#04050A' }}>
    <style>{`.nq-cesium .cesium-viewer-bottom{display:none}.nq-cesium .cesium-widget canvas{outline:none}
      .nq-credits{position:absolute;right:16px;bottom:4px;z-index:4;font:9px var(--mono);color:#5A5F6E;max-width:40%;text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      .nq-credits img{height:11px;vertical-align:middle;opacity:.6;filter:grayscale(1)} .nq-credits a{color:#5A5F6E}
      .nq-credits .cesium-credit-lightbox-overlay{display:none} .nq-credits .cesium-credit-expand-link{display:none}`}</style>
    <div className="row" style={{ position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)', zIndex: 5, gap: 4 }}>
      {(['globe', 'alt'] as const).map(t => <button key={t} onClick={() => setTab(t)} style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.12em', borderColor: tab === t ? 'var(--orange)' : undefined, background: '#0A0B12' }}>{t === 'globe' ? 'GLOBE' : 'ALT-DATA LAB'}</button>)}</div>
    {tab === 'globe' ? <>
      <Globe on={on} sensor={sensor} basemap={basemap} cutoff={cutoff} />
      <div className="mono lo" style={{ position: 'absolute', top: 14, left: 16, fontSize: 10, lineHeight: 1.7, zIndex: 4, pointerEvents: 'none' }}><div style={{ color: 'var(--hi)', letterSpacing: '.16em' }}>GOD'S EYE · NSKO QUANT</div>51.5072° N · 0.1276° W<br />{new Date(now).toISOString().slice(11, 19)} UTC · <span className="o">{sensor.toUpperCase()}</span> · {demo ? 'DEMO LAYERS' : 'LIVE LAYERS'}</div>
      <div className="panel" style={{ position: 'absolute', left: 16, top: 90, width: 186, padding: 10, zIndex: 4, background: 'rgba(12,13,20,.88)' }}>
        <div className="lbl" style={{ marginBottom: 6 }}>LAYERS</div>{LAYERS.map(([k, col]) => <label key={k} className="row" style={{ gap: 8, padding: '3px 0', fontSize: 12, cursor: 'pointer' }}><input type="checkbox" checked={!!on[k]} onChange={() => setOn({ ...on, [k]: !on[k] })} /><span className="dot" style={{ background: col }} />{k}<span className="lo num" style={{ marginLeft: 'auto', fontSize: 10 }}>{counts[k] || 0}</span></label>)}
        <div className="lbl" style={{ margin: '10px 0 6px' }}>SENSOR</div>{['Normal', 'Night-vision', 'Thermal'].map(s => <button key={s} onClick={() => setSensor(s)} style={{ display: 'block', width: '100%', marginBottom: 4, fontSize: 11, borderColor: sensor === s ? 'var(--orange)' : undefined }}>{s}</button>)}
        <div className="lbl" style={{ margin: '10px 0 6px' }}>BASEMAP</div><div className="row" style={{ gap: 4 }}>{(Object.keys(BASEMAPS) as Basemap[]).map(b => <button key={b} onClick={() => setBasemap(b)} style={{ flex: 1, padding: '4px 0', fontSize: 10, borderColor: basemap === b ? 'var(--orange)' : undefined }}>{BASEMAPS[b].name}</button>)}</div>
        <div className="lo" style={{ fontSize: 9, marginTop: 8, lineHeight: 1.5 }}>No Cesium ion. Free imagery only; terrain is the plain ellipsoid.</div></div>
      <div style={{ position: 'absolute', right: 16, top: 60, width: 320, zIndex: 4 }}><div className="lbl" style={{ marginBottom: 6 }}>MARKET IMPACT</div>
        {impacts.length === 0 && <div className="empty" style={{ background: 'rgba(12,13,20,.9)' }}>No market-impact events yet.</div>}
        {impacts.map(i => <div key={i.id} className="panel" style={{ padding: 10, marginBottom: 8, borderLeft: `2px solid ${TONE[i.tone] || 'var(--cyan)'}`, background: 'rgba(12,13,20,.9)' }}>
          <div className="mono" style={{ fontSize: 10.5, letterSpacing: '.06em' }}>{i.title}</div><div className="a" style={{ fontSize: 11.5, margin: '4px 0' }}>{i.asset}</div><div className="lo" style={{ fontSize: 11, lineHeight: 1.5 }}>{i.note}</div>
          <div className="row" style={{ marginTop: 8, gap: 6 }}><button style={{ fontSize: 10.5, padding: '3px 8px' }}>Send to Research</button><span className="lo" style={{ fontSize: 9.5 }}>never opens a trade by itself</span></div></div>)}</div>
      <div className="panel" style={{ position: 'absolute', left: 218, right: 350, bottom: 40, padding: '8px 14px', zIndex: 4, background: 'rgba(12,13,20,.88)' }}>
        <div className="row"><span className="lbl">24H TIMELINE</span><input type="range" min={0} max={24} value={time} onChange={e => setTime(+e.target.value)} style={{ flex: 1, accentColor: '#E8541A' }} /><span className="num" style={{ width: 40, textAlign: 'right' }}>{time === 24 ? 'NOW' : `−${24 - time}h`}</span></div>
        <div className="lo mono" style={{ fontSize: 9, marginTop: 4 }}>events up to {new Date(cutoff).toISOString().slice(11, 16)} UTC · flights, ships and satellites show their latest position</div></div>
      <div className="mono" style={{ position: 'absolute', left: 16, right: '42%', bottom: 4, zIndex: 4, fontSize: 9, color: '#5A5F6E', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={attribution.join(' · ')}>
        {demo && <span className="a">DEMO POSITIONS · </span>}{attribution.join(' · ')}</div>
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
