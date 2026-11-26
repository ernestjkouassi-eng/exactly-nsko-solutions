import { Component, lazy, Suspense, useEffect, useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useS } from './store'
import { initSource } from './source'
import { TopBar, Sidebar, Jarvis, Notices, ConfirmHost } from './shell/Shell'
import Overview from './pages/Overview'
import { Lab, Research } from './pages/LabResearch'
import { Strategies, Knowledge } from './pages/BookKnowledge'
import { TradeCard, Decisions, PaperLive, Withdraw } from './pages/Money'
import { Brokers, Engine, Costs, Settings, Help, Onboarding } from './pages/System'
import Lock from './pages/Lock'
import Gate from './web/Gate'
import { WEB_DEMO, initAccount, useAcct } from './web/account'

// Heavy pages load on demand: three.js (Agent Room), CesiumJS (God's Eye), lightweight-charts (Live Desk).
const Agents = lazy(() => import('./pages/Agents'))
const GodsEye = lazy(() => import('./pages/GodsEye'))
const GodsEyeLite = lazy(() => import('./pages/GodsEyeLite'))
// Phones get the light globe (fast, no map engine); a desktop browser that cannot run the full globe falls back to it too.
const smallScreen = () => typeof window !== 'undefined' && window.matchMedia('(max-width: 820px)').matches
const LiveDesk = lazy(() => import('./pages/LiveDesk'))

// One broken page (for example a browser without WebGL for the globe) must never black out the whole desk.
class PageBoundary extends Component<{ children: ReactNode; page: string }, { err: string | null }> {
  state = { err: null as string | null }
  static getDerivedStateFromError(e: Error) { return { err: e?.message || 'error' } }
  componentDidUpdate(prev: { page: string }) { if (prev.page !== this.props.page && this.state.err) this.setState({ err: null }) }
  render() { if (this.state.err && this.props.page === 'godseye') return <Suspense fallback={<Loading />}><GodsEyeLite /></Suspense>
    return this.state.err ? <div className="page"><div className="ptitle">This screen could not start</div><div className="psub">Your browser blocked part of it ({this.state.err}). The rest of the desk still works: pick another page from the menu.</div></div> : this.props.children }
}

initSource()
initAccount()   // web demo build only (no-op on desktop)
const PAGES: Record<string, () => ReactNode> = {
  overview: () => <Overview />, lab: () => <Lab />, research: () => <Research />, strategies: () => <Strategies />, knowledge: () => <Knowledge />, agents: () => <Agents />, godseye: () => smallScreen() ? <GodsEyeLite /> : <GodsEye />,
  desk: () => <LiveDesk />, tradecard: () => <TradeCard />, decisions: () => <Decisions />, paperlive: () => <PaperLive />, withdraw: () => <Withdraw />,
  brokers: () => <Brokers />, engine: () => <Engine />, costs: () => <Costs />, settings: () => <Settings />, help: () => <Help />,
}
const Loading = () => <div className="page"><div className="lbl"><span className="dot pulse" /> LOADING</div></div>

export default function App() {
  const q = new URLSearchParams(location.search)
  const [page, setPage] = useState(q.get('page') || 'overview'); const [jarvis, setJarvis] = useState(false)
  const [onboard, setOnboard] = useState(() => { try { return q.get('onboard') === '1' || (!WEB_DEMO && !q.get('page') && localStorage.getItem('nq_onboarded') !== '1') } catch { return false } })
  const locked = useS(s => s.locked), needAccount = useS(s => s.needAccount)
  useEffect(() => { const k = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'j') { e.preventDefault(); setJarvis(j => !j) } }; addEventListener('keydown', k); return () => removeEventListener('keydown', k) }, [])
  useEffect(() => {   // desktop shell: the tray kill switch reports back here
    if (!('__TAURI_INTERNALS__' in window)) return
    let un: (() => void) | undefined
    import('@tauri-apps/api/event').then(({ listen }) => listen<boolean>('tray-kill', e => { if (e.payload) useS.getState().set({ killed: true }) }).then(u => { un = u }))
    return () => un?.()
  }, [])
  const acct = useAcct(s => s.status)
  const showOnboard = onboard || needAccount
  if (WEB_DEMO && acct !== 'in') return <Gate />   // web demo: an account first, then the desk on demo data
  return <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
    <TopBar openJarvis={() => setJarvis(true)} />
    <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
      <Sidebar page={page} go={setPage} />
      <div style={{ flex: 1, minWidth: 0, position: 'relative' }}>
        <AnimatePresence mode="wait">
          <motion.div key={page} style={{ position: 'absolute', inset: 0 }} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0, transition: { duration: .25, ease: [.2, .8, .2, 1] } }} exit={{ opacity: 0, transition: { duration: .15 } }}>
            <PageBoundary page={page}><Suspense fallback={<Loading />}>{PAGES[page]?.()}</Suspense></PageBoundary>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
    <Jarvis open={jarvis} close={() => setJarvis(false)} />
    {showOnboard && <Onboarding done={() => { try { localStorage.setItem('nq_onboarded', '1') } catch { /* ignore */ } setOnboard(false); useS.setState({ needAccount: false }) }} />}
    {!showOnboard && locked && <Lock />}
    <Notices />
    <ConfirmHost />
  </div>
}
