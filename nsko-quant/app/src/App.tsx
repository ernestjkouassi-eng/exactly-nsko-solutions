import { lazy, Suspense, useEffect, useState, type ReactNode } from 'react'
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

// Heavy pages load on demand: three.js (Agent Room), CesiumJS (God's Eye), lightweight-charts (Live Desk).
const Agents = lazy(() => import('./pages/Agents'))
const GodsEye = lazy(() => import('./pages/GodsEye'))
const LiveDesk = lazy(() => import('./pages/LiveDesk'))

initSource()
const PAGES: Record<string, () => ReactNode> = {
  overview: () => <Overview />, lab: () => <Lab />, research: () => <Research />, strategies: () => <Strategies />, knowledge: () => <Knowledge />, agents: () => <Agents />, godseye: () => <GodsEye />,
  desk: () => <LiveDesk />, tradecard: () => <TradeCard />, decisions: () => <Decisions />, paperlive: () => <PaperLive />, withdraw: () => <Withdraw />,
  brokers: () => <Brokers />, engine: () => <Engine />, costs: () => <Costs />, settings: () => <Settings />, help: () => <Help />,
}
const Loading = () => <div className="page"><div className="lbl"><span className="dot pulse" /> LOADING</div></div>

export default function App() {
  const q = new URLSearchParams(location.search)
  const [page, setPage] = useState(q.get('page') || 'overview'); const [jarvis, setJarvis] = useState(false)
  const [onboard, setOnboard] = useState(() => { try { return q.get('onboard') === '1' || (!q.get('page') && localStorage.getItem('nq_onboarded') !== '1') } catch { return false } })
  const locked = useS(s => s.locked), needAccount = useS(s => s.needAccount)
  useEffect(() => { const k = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'j') { e.preventDefault(); setJarvis(j => !j) } }; addEventListener('keydown', k); return () => removeEventListener('keydown', k) }, [])
  useEffect(() => {   // desktop shell: the tray kill switch reports back here
    if (!('__TAURI_INTERNALS__' in window)) return
    let un: (() => void) | undefined
    import('@tauri-apps/api/event').then(({ listen }) => listen<boolean>('tray-kill', e => { if (e.payload) useS.getState().set({ killed: true }) }).then(u => { un = u }))
    return () => un?.()
  }, [])
  const showOnboard = onboard || needAccount
  return <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
    <TopBar openJarvis={() => setJarvis(true)} />
    <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
      <Sidebar page={page} go={setPage} />
      <div style={{ flex: 1, minWidth: 0, position: 'relative' }}>
        <AnimatePresence mode="wait">
          <motion.div key={page} style={{ position: 'absolute', inset: 0 }} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0, transition: { duration: .25, ease: [.2, .8, .2, 1] } }} exit={{ opacity: 0, transition: { duration: .15 } }}>
            <Suspense fallback={<Loading />}>{PAGES[page]?.()}</Suspense>
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
