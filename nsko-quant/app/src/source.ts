// Data source switch: the seeded demo simulator, or the live engine WebSocket (ws://127.0.0.1:8787/ws).
// Both feed the same store handler, handle(ev). If the engine is unreachable the desk falls back to demo
// data with a visible notice, and keeps retrying in the background with backoff.
import { on, startDemo, stopDemo } from './demo/sim'
import { handle, notify, resetForDemo, resetForEngine, useS, type Session } from './store'
import { isTauri, probe, WS_URL } from './api'

let ws: WebSocket | null = null
let wantEngine = false
let wsTries = 0, probeTries = 0
let wsT: ReturnType<typeof setTimeout> | undefined, probeT: ReturnType<typeof setTimeout> | undefined
const backoff = (n: number) => Math.min(30000, 1000 * 2 ** Math.min(n, 5)) * (0.85 + Math.random() * 0.3)

let inited = false
export function initSource() {
  if (inited) return; inited = true
  on(handle)
  const q = new URLSearchParams(location.search).get('source')
  let saved: string | null = null; try { saved = localStorage.getItem('nq_source') } catch { /* private mode */ }
  const pick = q || saved || (isTauri ? 'engine' : 'demo')
  if (pick === 'engine') selectEngine(false); else selectDemo(false)
}

const persist = (v: string) => { try { localStorage.setItem('nq_source', v) } catch { /* ignore */ } }

export function selectDemo(save = true) {
  wantEngine = false; closeWs(); clearTimeout(probeT); clearTimeout(wsT)
  const wasEngine = useS.getState().source === 'engine' && !useS.getState().fallback
  if (wasEngine) resetForDemo()
  useS.setState({ source: 'demo', conn: 'off', fallback: false, locked: false, demo: true, needAccount: false })
  startDemo(); if (save) persist('demo')
}

export async function selectEngine(save = true) {
  wantEngine = true; probeTries = 0; clearTimeout(probeT); if (save) persist('engine')
  useS.setState({ source: 'engine', conn: 'probing' })
  const h = await probe()
  if (!wantEngine) return
  if (h) engineUp(h)
  else { enterFallback('Engine not answering on 127.0.0.1:8787'); scheduleProbe() }
}

function engineUp(h: any) {
  stopDemo(); clearTimeout(probeT)
  const s = useS.getState()
  const needAccount = h && h.account_exists === false
  useS.setState({ fallback: false, demo: false, conn: s.session ? 'connecting' : 'online', needAccount, locked: !s.session && !needAccount })
  if (s.session) connectWs()
}

function enterFallback(why: string) {
  const s = useS.getState()
  if (!s.fallback) notify(`${why} · showing DEMO DATA, retrying in the background`, 'warn', { label: 'Retry now', run: () => selectEngine(false) }, 12000)
  useS.setState({ fallback: true, demo: true, conn: 'offline', locked: false })
  startDemo()
}

function scheduleProbe() {
  clearTimeout(probeT)
  probeT = setTimeout(async () => {
    if (!wantEngine) return
    const h = await probe()
    if (!wantEngine) return
    if (h) { notify('Engine is answering again. Log in to use live data.', 'good'); resetForEngine(); engineUp(h) }
    else { probeTries++; scheduleProbe() }
  }, backoff(probeTries))
}

/** Called by the lock screen / onboarding after a successful login. */
export function afterLogin(session: NonNullable<Session>) {
  useS.setState({ session, locked: false, needAccount: false })
  if (useS.getState().source !== 'engine') return
  if (session.token === 'demo') return   // the login itself fell back to demo behaviour
  resetForEngine(); connectWs()
}

export function logout() { closeWs(); useS.setState({ session: null, locked: useS.getState().source === 'engine' && !useS.getState().fallback }) }

function closeWs() { if (ws) { ws.onclose = null; ws.close(); ws = null } }

function connectWs() {
  closeWs(); clearTimeout(wsT)
  const tok = useS.getState().session?.token
  useS.setState({ conn: wsTries ? 'reconnecting' : 'connecting' })
  let sock: WebSocket
  try { sock = new WebSocket(WS_URL + (tok && tok !== 'demo' ? `?token=${encodeURIComponent(tok)}` : '')) } catch { return onDrop() }
  ws = sock
  sock.onopen = () => {
    wsTries = 0
    if (useS.getState().fallback) { stopDemo(); resetForEngine(); notify('Engine connected · live data', 'good') }
    useS.setState({ conn: 'online', fallback: false, demo: false })
  }
  sock.onmessage = (m) => {
    try {
      const d = JSON.parse(typeof m.data === 'string' ? m.data : '')
      const evs = Array.isArray(d) ? d : [d]
      for (const e of evs) if (e && e.type) handle({ type: e.type, ts: e.ts ?? Date.now(), payload: e.payload ?? {} })
    } catch { /* ignore malformed frames */ }
  }
  sock.onclose = () => onDrop()
}

function onDrop() {
  ws = null
  if (!wantEngine) return
  wsTries++
  useS.setState({ conn: 'reconnecting' })
  if (wsTries >= 3 && !useS.getState().fallback) enterFallback('Engine connection lost')
  wsT = setTimeout(connectWs, backoff(wsTries))
}
