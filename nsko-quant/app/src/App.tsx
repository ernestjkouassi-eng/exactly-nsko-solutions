import { useEffect, useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { wire } from './store'
import { TopBar, Sidebar, Jarvis } from './shell/Shell'
import Overview from './pages/Overview'
import { Lab, Research } from './pages/LabResearch'
import { Strategies, Knowledge } from './pages/BookKnowledge'
import Agents from './pages/Agents'
import GodsEye from './pages/GodsEye'
import { LiveDesk, TradeCard, Decisions, PaperLive } from './pages/Money'
import { Brokers, Engine, Costs, Settings, Help, Onboarding } from './pages/System'

wire()
const PAGES: Record<string, () => ReactNode> = {
  overview: () => <Overview />, lab: () => <Lab />, research: () => <Research />, strategies: () => <Strategies />, knowledge: () => <Knowledge />, agents: () => <Agents />, godseye: () => <GodsEye />,
  desk: () => <LiveDesk />, tradecard: () => <TradeCard />, decisions: () => <Decisions />, paperlive: () => <PaperLive />,
  brokers: () => <Brokers />, engine: () => <Engine />, costs: () => <Costs />, settings: () => <Settings />, help: () => <Help />,
}
export default function App() {
  const q = new URLSearchParams(location.search)
  const [page, setPage] = useState(q.get('page') || 'overview'); const [jarvis, setJarvis] = useState(false)
  const [onboard, setOnboard] = useState(() => q.get('onboard') === '1' || (!q.get('page') && localStorage.getItem('nq_onboarded') !== '1'))
  useEffect(() => { const k = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'j') { e.preventDefault(); setJarvis(j => !j) } }; addEventListener('keydown', k); return () => removeEventListener('keydown', k) }, [])
  return <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
    <TopBar openJarvis={() => setJarvis(true)} />
    <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
      <Sidebar page={page} go={setPage} />
      <div style={{ flex: 1, minWidth: 0, position: 'relative' }}>
        <AnimatePresence mode="wait">
          <motion.div key={page} style={{ position: 'absolute', inset: 0 }} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0, transition: { duration: .25, ease: [.2, .8, .2, 1] } }} exit={{ opacity: 0, transition: { duration: .15 } }}>
            {PAGES[page]?.()}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
    <Jarvis open={jarvis} close={() => setJarvis(false)} />
    {onboard && <Onboarding done={() => { localStorage.setItem('nq_onboarded', '1'); setOnboard(false) }} />}
  </div>
}
