import { useEffect, useRef, useState } from 'react'
import { useS, notify } from '../store'
import { Head, Wordmark, fmt, ask } from '../shell/Shell'
import { RiskWarning } from './Money'
import { selectDemo, selectEngine, afterLogin } from '../source'
import {
  brokers as getBrokers, connectBroker, keychainSet, isTauri, DEMO_BROKERS, getSettings, saveSettings, exportDesk, restoreDesk, health as getHealth,
  createAccount, licenceCheck, totpBegin, totpConfirm, pauseTrading, vaultNames, saveSecret, telegramPairBegin, notifyTest, type Broker, type Settings as SettingsT, type Created, type Licence,
} from '../api'

const STATUS: Record<Broker['status'], [string, string]> = { connected: ['CONNECTED', 'g'], demo: ['DEMO', 'a'], not_connected: ['NOT CONNECTED', 'lo'], error: ['ERROR', 'r'], coming_soon: ['COMING SOON', 'lo'], unsupported: ['NOT SUPPORTED', 'r'] }

// ---------------- Brokers
export function Brokers() {
  const [list, setList] = useState<Broker[]>(DEMO_BROKERS); const [demo, setDemo] = useState(true); const [open, setOpen] = useState<Broker | null>(null)
  const load = () => getBrokers().then(r => { if (r.ok && Array.isArray(r.data)) { setList(r.data); setDemo(r.demo) } })
  useEffect(() => { load() }, [])
  return <div className="page"><div className="row" style={{ alignItems: 'flex-start' }}><div><div className="ptitle">Brokers</div><div className="psub">Your money stays in your own broker account. NSKO QUANT only holds a key that can trade: switch withdrawals OFF on the key wherever the broker allows it. Keys are kept in this computer's keychain, never in a file.</div></div>
    {demo && <span className="chip a" style={{ borderColor: '#5A4020', marginLeft: 'auto' }}>DEMO LIST</span>}</div>
    <div className="grid" data-testid="brokers" style={{ gridTemplateColumns: 'repeat(4,1fr)' }}>{list.filter(b => b.id !== 'cmc').map(b => { const [t, c] = STATUS[b.status] || STATUS.not_connected; return <div key={b.id} className="panel" style={{ padding: 14 }}>
      <div className="row" style={{ justifyContent: 'space-between' }}><span style={{ fontSize: 15, fontWeight: 600 }}>{b.name}</span><span className={`chip ${c}`} style={{ borderColor: 'var(--line)' }}>{t}</span></div>
      <div className="lo" style={{ fontSize: 11.5, margin: '6px 0 10px', minHeight: 30 }}>{b.markets}</div>
      {b.status === 'demo' || b.status === 'connected' ? <div className="mono" style={{ fontSize: 10.5, lineHeight: 1.7 }}><span className="g">Trading ✓</span> · <span className={b.withdrawals_off ? 'g' : 'a'}>{b.withdrawals_off ? 'Withdrawals OFF ✓' : 'Withdrawals: check the key'}</span><br /><span className="lo">{b.id === 'paper' ? 'simulator on this computer · no key needed' : <>{b.latency_ms ? `latency ${b.latency_ms} ms · ` : ''}<span style={{ cursor: 'pointer', textDecoration: 'underline' }} onClick={() => setOpen(b)}>replace key</span></>}</span></div>
        : b.status === 'coming_soon' || b.status === 'unsupported' ? <div className="lo" style={{ fontSize: 10.5, lineHeight: 1.5 }} title={b.reason}>{(b.reason || '').slice(0, 120)}{(b.reason || '').length > 120 ? '…' : ''}</div>
        : <button onClick={() => setOpen(b)}>Connect{b.key_stored ? ' · key saved' : ''}</button>}</div> })}</div>
    <div className="panel" style={{ marginTop: 12, padding: 14 }}><span className="r mono">CMC Markets is not supported</span><span className="lo"> · it offers no API access for automated trading.</span></div>
    {open && <ConnectModal b={open} close={() => setOpen(null)} done={load} />}</div>
}
function ConnectModal({ b, close, done }: { b: Broker; close: () => void; done: () => void }) {
  const [env, setEnv] = useState<'demo' | 'live'>('demo'); const [key, setKey] = useState(''); const [secret, setSecret] = useState(''); const [acct, setAcct] = useState(''); const [busy, setBusy] = useState(false); const [res, setRes] = useState('')
  const go = async () => {
    setBusy(true); setRes('')
    try {
      const account = `broker:${b.id}:${env}`
      let body: Parameters<typeof connectBroker>[1] = { environment: env, account_id: acct || undefined }
      if (isTauri) { await keychainSet(`${account}:key`, key); if (secret) await keychainSet(`${account}:secret`, secret); body = { ...body, keychain_service: 'uk.co.nsko.quant', keychain_account: account } }
      else body = { ...body, api_key: key, api_secret: secret || undefined }   // browser dev only: sent to the localhost engine, never stored by the UI
      const r = await connectBroker(b.id, body)
      if (r.ok && r.data.ok !== false) { setRes(r.data.message || `Connected · trading ${r.data.trading ? 'ON' : 'OFF'} · withdrawals ${r.data.withdrawals_off ? 'OFF ✓' : 'not confirmed OFF'}`); done() }
      else setRes(`Not connected: ${r.error || r.data.message || 'unknown error'}`)
    } catch (e) { setRes(`Keychain error: ${String(e)}`) } finally { setBusy(false); setKey(''); setSecret('') }
  }
  return <div style={{ position: 'fixed', inset: 0, zIndex: 150, background: 'rgba(4,4,8,.72)', display: 'grid', placeItems: 'center' }} onClick={close}>
    <div className="panel" style={{ width: 480, padding: 20 }} onClick={e => e.stopPropagation()}>
      <div className="lbl" style={{ color: 'var(--hi)' }}>CONNECT · {b.name.toUpperCase()}</div><div className="lo" style={{ fontSize: 11.5, margin: '6px 0 14px' }}>Create an API key at {b.name} with trading ON and withdrawals OFF. Start with a demo account.</div>
      <div className="row" style={{ marginBottom: 10 }}>{(['demo', 'live'] as const).map(e => <button key={e} onClick={() => setEnv(e)} style={{ borderColor: env === e ? 'var(--orange)' : undefined }}>{e === 'demo' ? 'Demo account' : 'Live account'}</button>)}</div>
      <div className="grid" style={{ gap: 8 }}><input placeholder="API key" value={key} onChange={e => setKey(e.target.value)} autoComplete="off" /><input type="password" placeholder="API secret / password (if the broker uses one)" value={secret} onChange={e => setSecret(e.target.value)} autoComplete="off" /><input placeholder="Account ID (optional)" value={acct} onChange={e => setAcct(e.target.value)} /></div>
      <div className="lo" style={{ fontSize: 10.5, margin: '10px 0' }}>{isTauri ? 'Stored in your OS keychain (uk.co.nsko.quant). The engine reads it from there; this window can never read it back.' : 'Browser preview: the key goes only to the engine on 127.0.0.1. The desktop app stores it in the OS keychain instead.'}</div>
      {res && <div className="mono" style={{ fontSize: 11, margin: '6px 0', color: res.startsWith('Not') || res.startsWith('Keychain') ? 'var(--red)' : 'var(--green)' }}>{res}</div>}
      <div className="row" style={{ justifyContent: 'flex-end' }}><button onClick={close}>Close</button><button className="primary" disabled={!key || busy} onClick={go}>{busy ? 'Connecting…' : 'Save key and connect'}</button></div></div></div>
}

// ---------------- Engine
export function Engine() {
  const h = useS(s => s.health); const round = useS(s => s.round); const source = useS(s => s.source), conn = useS(s => s.conn), fallback = useS(s => s.fallback)
  const [checked, setChecked] = useState('')
  const check = async () => { const r = await getHealth(); setChecked(r.demo ? 'demo values' : r.ok ? `answered ${new Date().toLocaleTimeString('en-GB', { hour12: false })}` : r.error || 'error'); if (r.ok && !r.demo) useS.setState({ health: { ...useS.getState().health, ...r.data } }) }
  const live = source === 'engine' && !fallback
  const status = source === 'demo' ? ['DEMO SIM', 'a'] : conn === 'online' ? ['RUNNING', 'g'] : conn === 'offline' ? ['NOT ANSWERING', 'r'] : [conn.toUpperCase(), 'a']
  const up = h.uptime ?? round
  return <div className="page"><div className="ptitle">Engine</div><div className="psub">The background service that trades 24/7 on this computer, even with the window closed, as long as the computer is on and online.</div>
    <div className="panel" style={{ display: 'flex', marginBottom: 12 }}>{[['STATUS', status[0], status[1]], ['UPTIME', `${Math.floor(up / 3600)}h ${Math.floor(up / 60) % 60}m`, ''], ['KEEP-AWAKE', h.keepAwake === false ? 'OFF' : 'ON', h.keepAwake === false ? 'a' : 'g'], ['CPU', `${(h.cpu ?? 20).toFixed(0)}%`, ''], ['RAM', `${(h.ram ?? 2.2).toFixed(1)} GB`, ''], ['LAST HEARTBEAT', h.heartbeat ? new Date(h.heartbeat).toLocaleTimeString('en-GB', { hour12: false }) : '—', '']].map(([l, v, c]) =>
      <div key={l} style={{ flex: 1, padding: 14, borderRight: '1px solid var(--line)' }}><div className="lbl">{l}</div><div className={`big ${c}`} style={{ fontSize: 18 }}>{v}</div></div>)}</div>
    <div className="row" style={{ marginBottom: 12 }}><button onClick={check}>Check now</button><UpdateButton />{checked && <span className="lo mono" style={{ fontSize: 11 }}>{checked}</span>}
      {!live && <span className="chip a" style={{ borderColor: '#5A4020' }}>{source === 'demo' ? 'DEMO DATA · switch to Live engine in Settings' : 'ENGINE OFFLINE · showing demo data'}</span>}</div>
    <div className="panel"><Head t="LOGS" s="keys are always redacted" /><div className="pb mono" style={{ fontSize: 11, lineHeight: 1.8 }}>{useS.getState().log.slice(-12).map((l, i) => <div key={i}><span className="lo">{new Date(l.ts).toISOString()}</span> INFO {l.verb.toLowerCase()} {l.msg}</div>)}</div></div></div>
}
function UpdateButton() {
  const [t, setT] = useState('Check for updates')
  const go = async () => {
    if (!isTauri) { setT('Updates: desktop app only'); return }
    setT('Checking…')
    try { const { check } = await import('@tauri-apps/plugin-updater'); const u = await check(); setT(u ? `Update ${u.version} available` : 'Up to date') ; if (u && await ask('Install update', `Version ${u.version} is ready. The window restarts; the engine keeps trading.`, 'Install')) { await u.downloadAndInstall(); const { relaunch } = await import('@tauri-apps/plugin-process'); await relaunch() } }
    catch { setT('Update feed not set up yet') }
  }
  return <button onClick={go}>{t}</button>
}

export function Costs() {

  const b = useS(s => s.budget)
  return <div className="page"><div className="ptitle">Costs</div><div className="psub">NSKO QUANT runs on free, local tools. The think budget is compute and time on your own computer (the local AI model), not money, unless you bring your own Claude or OpenAI key.</div>
    <div className="grid" style={{ gridTemplateColumns: 'repeat(3,1fr)' }}>{[['THINK BUDGET', `${b.used.toFixed(1)} of ${b.of} units`, `${b.days} days left`], ['LOCAL AI', 'Ollama · small model', '0 £ · runs on this computer'], ['DATA', 'Broker + public feeds', 'free tiers · licences logged']].map(([l, v, s]) => <div key={l} className="panel" style={{ padding: 14 }}><div className="lbl">{l}</div><div style={{ fontSize: 18, margin: '6px 0' }}>{v}</div><div className="lo">{s}</div></div>)}</div></div>
}
export function Help() {
  return <div className="page"><div className="ptitle">Help</div><div className="psub">The full User Guide (PDF) opens here once it is written in Stage 5.</div>
    <div className="panel" style={{ maxWidth: 780 }}>{[['Does NSKO hold my money?', 'No. Your money stays in your own broker account. NSKO QUANT holds a trade-only key and has no withdrawal code at all.'], ['Does it trade when the window is closed?', 'Yes. The engine is a background service with a tray icon. It trades as long as the computer is on and online.'], ['Can I stop everything at once?', 'Yes. Hold the KILL SWITCH for 1.5 s, or send /kill from your paired Telegram account. It cancels orders, closes positions and locks trading.'], ['Is the data on screen real?', 'In Demo data mode, no: it comes from the seeded simulator and every screen says DEMO DATA. Switch to Live engine in Settings to see your real engine. If the engine stops answering, the desk falls back to demo data and tells you.']].map(([q, a]) =>
      <div key={q} style={{ padding: 14, borderBottom: '1px solid var(--line)' }}><div style={{ fontWeight: 600, marginBottom: 4 }}>{q}</div><div className="lo" style={{ lineHeight: 1.6 }}>{a}</div></div>)}<div style={{ padding: '0 14px' }}><RiskWarning /></div></div></div>
}


// ---------------- Settings
const RISK: [string, string, string][] = [['risk_per_trade_pct', 'Risk per trade', '%'], ['daily_loss_limit_pct', 'Daily loss limit · then stop for the day', '%'], ['weekly_loss_limit_pct', 'Weekly loss limit', '%'], ['max_trades_per_day', 'Max trades per day', ''], ['max_open_positions', 'Max open positions', ''],
  ['news_blackout_min', 'News blackout', '± min'], ['paper_days', 'Paper period before live', 'days'], ['paper_trades', 'Paper trades before live', 'trades'], ['live_start_size_pct', 'Live start size (2 weeks)', '%'], ['bar_sharpe_oos', 'The bar (Lab): OOS Sharpe after costs', '≥']]
export function Settings() {
  const auto = useS(s => s.auto), set = useS(s => s.set), source = useS(s => s.source), conn = useS(s => s.conn), fallback = useS(s => s.fallback)
  const [cfg, setCfg] = useState<SettingsT | null>(null); const [demo, setDemo] = useState(true); const [dirty, setDirty] = useState(false); const [saving, setSaving] = useState(false)
  useEffect(() => { getSettings().then(r => { if (r.ok) { setCfg(r.data); setDemo(r.demo); if (r.data.trading_mode) set({ auto: r.data.trading_mode !== 'manual' }) } }) }, [source, fallback])
  const upd = (k: string, v: any) => { setCfg(c => ({ ...c, [k]: v })); setDirty(true) }
  const save = async () => { if (!cfg) return; setSaving(true); const r = await saveSettings(cfg); setSaving(false); if (r.ok) { setDirty(false); notify(r.demo ? 'Saved for this demo session only' : 'Settings saved to the engine', r.demo ? 'info' : 'good') } else notify(`Not saved: ${r.error}`, 'bad') }
  const toEngine = () => selectEngine(), toDemo = async () => { if (source === 'engine' && !fallback && !await ask('Switch to demo data?', 'The engine keeps trading in the background. The desk will show the seeded simulator until you switch back.', 'Show demo data')) return; selectDemo() }
  const mode = (m: 'Auto' | 'Manual') => { set({ auto: m === 'Auto' }); upd('trading_mode', m.toLowerCase()) }
  const paused = useS(s => s.paused)
  const togglePause = async () => { const r = await pauseTrading(!paused); if (r.ok) { set({ paused: r.data.trading_paused }); notify(r.data.trading_paused ? 'New trades paused' : 'New trades resumed', 'good') } else notify(`Not changed: ${r.error}`, 'bad') }
  return <div className="page"><div className="row" style={{ alignItems: 'flex-start' }}><div className="ptitle">Settings</div>
    <div className="row" style={{ marginLeft: 'auto' }}>{demo && <span className="chip a" style={{ borderColor: '#5A4020' }}>DEMO SETTINGS</span>}<button className="primary" disabled={!dirty || saving} style={{ opacity: dirty ? 1 : .4 }} onClick={save}>{saving ? 'Saving…' : 'Save settings'}</button></div></div>
    <div className="panel" style={{ marginBottom: 12, marginTop: 10 }}><Head t="DATA SOURCE" s="what the desk shows" />
      <div className="pb row" style={{ gap: 0, alignItems: 'stretch' }}>
        {([['demo', 'Demo data', 'Seeded simulator. Same demo every time: for sales demos and the video ad. Nothing trades.', toDemo], ['engine', 'Live engine', 'Your engine on this computer (127.0.0.1:8787). Real research, real paper and live trading. Needs your login.', toEngine]] as const).map(([k, t, d, fn], i) =>
          <div key={k} onClick={fn} data-testid={`src-${k}`} style={{ flex: 1, cursor: 'pointer', padding: 14, border: `1px solid ${source === k ? 'var(--orange)' : 'var(--line)'}`, borderRadius: i ? '0 3px 3px 0' : '3px 0 0 3px', background: source === k ? 'rgba(232,84,26,.06)' : 'transparent', marginLeft: i ? -1 : 0 }}>
            <div className="row" style={{ gap: 8 }}><span style={{ width: 12, height: 12, borderRadius: '50%', border: `1px solid ${source === k ? 'var(--orange)' : '#3A3E4E'}`, display: 'grid', placeItems: 'center' }}>{source === k && <i style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--orange)' }} />}</span>
              <span className="lbl" style={{ color: 'var(--hi)', fontSize: 10.5 }}>{t}</span>
              {k === 'engine' && source === 'engine' && <span className={`chip ${conn === 'online' ? 'g' : conn === 'offline' ? 'r' : 'a'}`} style={{ borderColor: 'var(--line)', marginLeft: 'auto' }}>ENGINE · {conn.toUpperCase()}</span>}
              {k === 'demo' && source === 'demo' && <span className="chip a" style={{ borderColor: '#5A4020', marginLeft: 'auto' }}>DEMO DATA</span>}</div>
            <div className="lo" style={{ fontSize: 11.5, marginTop: 8, lineHeight: 1.5 }}>{d}</div></div>)}
      </div>
      {fallback && <div className="pb" style={{ paddingTop: 0 }}><div className="empty" style={{ borderColor: '#5A4020', color: 'var(--amber)' }}>The engine is not answering on 127.0.0.1:8787, so the desk is showing DEMO DATA. It keeps retrying in the background. <span style={{ textDecoration: 'underline', cursor: 'pointer' }} onClick={toEngine}>Retry now</span></div></div>}
    </div>
    <div className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
      <div className="panel"><Head t="RISK LIMITS" s="hard limits: the gate cannot be switched off in live" /><div className="pb">{RISK.map(([k, l, u]) => <div key={k} className="row" style={{ justifyContent: 'space-between', padding: '7px 0', borderBottom: '1px solid #12131B' }}><span>{l}</span>
        <span className="row" style={{ gap: 6 }}><input type="number" step="any" value={cfg?.[k] ?? ''} onChange={e => upd(k, e.target.value === '' ? '' : +e.target.value)} style={{ width: 110, textAlign: 'right' }} /><span className="lo mono" style={{ fontSize: 10, width: 44 }}>{u}</span></span></div>)}</div></div>
      <div className="grid" style={{ alignContent: 'start' }}>
        <div className="panel"><Head t="TRADING" /><div className="pb row">{(['Auto', 'Manual'] as const).map(m => <button key={m} onClick={() => mode(m)} style={{ borderColor: (m === 'Auto') === auto ? 'var(--orange)' : undefined }}>{m}</button>)}<span className="lo" style={{ fontSize: 11 }}>Manual waits for Approve at the order ticket</span></div>
          <div className="pb row" style={{ paddingTop: 0 }}><button data-testid="pause-toggle" onClick={togglePause}>{paused ? 'Resume new trades' : 'Pause new trades'}</button><span className="lo" style={{ fontSize: 11 }}>{paused ? 'PAUSED: open trades keep their stops and targets; nothing new opens.' : 'Pausing stops new trades only. The kill switch closes everything.'}</span></div></div>
        <div className="panel"><Head t="STRATEGY UPDATES" /><div className="pb">{([['manual', 'Manual'], ['auto_paper', 'Automatic → paper, then ask me'], ['ask', 'Ask me']] as const).map(([k, m]) => <label key={k} className="row" style={{ padding: '4px 0', cursor: 'pointer' }}><input type="radio" checked={(cfg?.strategy_updates ?? 'ask') === k} onChange={() => upd('strategy_updates', k)} />{m}</label>)}<div className="lo" style={{ fontSize: 11, marginTop: 6 }}>NSKO strategy packs always go to the Lab first, never straight to live. Every change can be rolled back in one click.</div></div></div>
        <AlertsPanel cfg={cfg} upd={upd} />
        <div className="panel"><Head t="GOD'S EYE · RISK ACTIONS" s="it never opens a trade" /><div className="pb">{([['suggest', 'Suggest only: show "cut size" / "pause new" on the alert card'], ['apply', 'Apply: the risk gate halves the size or pauses new entries on the flagged market (it can only reduce risk)']] as const).map(([k, l]) => <label key={k} className="row" style={{ padding: '4px 0', cursor: 'pointer' }}><input type="radio" checked={(cfg?.godseye_risk_actions ?? 'suggest') === k} onChange={() => upd('godseye_risk_actions', k)} />{l}</label>)}</div></div>
        <DesktopPanel />
        <DeskPanel />
      </div></div></div>
}
// Phone alerts: ntfy (server + topic, saved with the other settings) and the Telegram bot (token into the vault, then pairing).
function AlertsPanel({ cfg, upd }: { cfg: SettingsT | null; upd: (k: string, v: any) => void }) {
  const [token, setToken] = useState(''); const [hasToken, setHasToken] = useState(false); const [pair, setPair] = useState(''); const [test, setTest] = useState(''); const [busy, setBusy] = useState('')
  const source = useS(s => s.source)
  useEffect(() => { vaultNames().then(r => { if (r.ok && !r.demo) setHasToken(r.data.names.includes('telegram.bot_token')) }) }, [source])
  const saveToken = async () => { setBusy('token'); const r = await saveSecret('telegram.bot_token', token.trim()); setBusy(''); setToken('')
    if (r.ok) { setHasToken(true); notify(r.demo ? 'Demo: the token was not stored' : `Bot token saved (${r.data.stored_in}). It is never shown again.`, r.demo ? 'info' : 'good') } else notify(`Not saved: ${r.error}`, 'bad') }
  const startPair = async () => { setBusy('pair'); const r = await telegramPairBegin(); setBusy(''); if (r.ok) setPair(r.data.how); else notify(r.error || 'Pairing failed', 'bad') }
  const sendTest = async () => { setBusy('test'); const r = await notifyTest(); setBusy(''); setTest(r.ok ? `Sent · ${r.data.delivered}` : `Not sent: ${r.error}`) }
  return <div className="panel" data-testid="alerts-panel"><Head t="ALERTS" s="phone alarms for trades, errors and the kill switch" /><div className="pb">
    {([['alerts_ntfy', 'Phone: ntfy (high priority alarm)'], ['alerts_telegram', 'Telegram bot · /kill and /status from your paired chat'], ['alerts_desktop', 'Desktop notifications']] as const).map(([k, a]) => <label key={k} className="row" style={{ padding: '4px 0' }}><input type="checkbox" checked={cfg?.[k] ?? true} onChange={e => upd(k, e.target.checked)} />{a}</label>)}
    <div className="lbl" style={{ margin: '10px 0 6px' }}>NTFY</div>
    <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 8 }}><input placeholder="Server · https://ntfy.sh" value={cfg?.ntfy_url ?? ''} onChange={e => upd('ntfy_url', e.target.value)} />
      <input data-testid="ntfy-topic" placeholder="Topic (long and random, e.g. nsko-7f3k9q…)" value={cfg?.ntfy_topic ?? ''} onChange={e => upd('ntfy_topic', e.target.value.trim())} /></div>
    <div className="lo" style={{ fontSize: 10.5, marginTop: 4 }}>Install the ntfy app on your phone and subscribe to the same topic. Anyone who knows the topic can read it, so make it hard to guess (or use your own ntfy server).</div>
    <div className="lbl" style={{ margin: '12px 0 6px' }}>TELEGRAM {hasToken && <span className="g">· TOKEN SAVED ✓</span>} {cfg?.telegram_chat_id ? <span className="g">· PAIRED ✓</span> : <span className="a">· NOT PAIRED</span>}</div>
    <div className="row" style={{ gap: 8 }}><input type="password" autoComplete="off" placeholder={hasToken ? 'Replace the bot token' : 'Bot token from @BotFather'} value={token} onChange={e => setToken(e.target.value)} style={{ flex: 1 }} />
      <button disabled={!token.trim() || !!busy} onClick={saveToken}>{busy === 'token' ? 'Saving…' : 'Save token'}</button><button disabled={!!busy} onClick={startPair}>Pair my chat</button></div>
    {pair && <div className="mono a" data-testid="pair-code" style={{ fontSize: 11, marginTop: 6 }}>{pair}</div>}
    <div className="lo" style={{ fontSize: 10.5, marginTop: 4 }}>The token goes into this computer's keychain (or the engine's encrypted vault) and is never shown again. Only the paired chat can use /kill.</div>
    <div className="row" style={{ marginTop: 10 }}><button disabled={!!busy} onClick={sendTest}>{busy === 'test' ? 'Sending…' : 'Send a test alert'}</button>{test && <span className="lo mono" style={{ fontSize: 10.5 }}>{test}</span>}</div>
    <div className="lo" style={{ fontSize: 10.5, marginTop: 4 }}>Save settings first if you changed the ntfy topic.</div>
  </div></div>
}
function DesktopPanel() {
  const [boot, setBoot] = useState<boolean | null>(null)
  useEffect(() => { if (isTauri) import('@tauri-apps/plugin-autostart').then(a => a.isEnabled()).then(setBoot).catch(() => setBoot(null)) }, [])
  const toggle = async () => { try { const a = await import('@tauri-apps/plugin-autostart'); if (boot) await a.disable(); else await a.enable(); setBoot(await a.isEnabled()) } catch (e) { notify(`Start on boot: ${String(e)}`, 'bad') } }
  return <div className="panel"><Head t="DESKTOP" s="the app around the engine" /><div className="pb">
    <label className="row" style={{ padding: '4px 0', opacity: isTauri ? 1 : .5 }}><input type="checkbox" disabled={!isTauri} checked={!!boot} onChange={toggle} />Start NSKO QUANT when the computer turns on (window hidden, tray icon only)</label>
    <div className="row" style={{ marginTop: 8 }}><UpdateButton /><span className="lo" style={{ fontSize: 11 }}>{isTauri ? 'Closing the window hides it to the tray. The engine keeps running.' : 'Desktop features are off in the browser preview.'}</span></div></div></div>
}
function DeskPanel() {
  const [pass, setPass] = useState(''); const [busy, setBusy] = useState(''); const file = useRef<HTMLInputElement>(null)
  const doExport = async () => { if (pass.length < 8) return notify('Use a passphrase of at least 8 characters', 'warn'); setBusy('export'); const r = await exportDesk(pass); setBusy('')
    if (!r.ok) return notify(`Export failed: ${r.error}`, 'bad')
    const a = document.createElement('a'); a.href = 'data:application/octet-stream;base64,' + r.data.data_b64; a.download = r.data.filename; a.click(); notify(r.demo ? 'Demo export downloaded (no real data)' : `Desk exported: ${r.data.filename}`, r.demo ? 'info' : 'good') }
  const doRestore = async (f: File) => { if (!await ask('Restore this desk?', `Settings, strategies and journal from ${f.name} replace the ones on this computer. Broker keys are never in a backup: reconnect them after.`, 'Restore')) return
    setBusy('restore'); const b64 = await new Promise<string>(res => { const rd = new FileReader(); rd.onload = () => res(String(rd.result).split(',')[1] || ''); rd.readAsDataURL(f) })
    const r = await restoreDesk(b64, pass); setBusy(''); if (r.ok) notify(`Restored: ${(r.data.restored || []).join(', ') || 'desk'}${r.demo ? ' (demo)' : ''}`, 'good'); else notify(`Restore failed: ${r.error}`, 'bad') }
  return <div className="panel"><Head t="DESK" s="backup" /><div className="pb">
    <input type="password" placeholder="Backup passphrase" value={pass} onChange={e => setPass(e.target.value)} style={{ width: '100%', marginBottom: 8 }} />
    <div className="row"><button disabled={!!busy} onClick={doExport}>{busy === 'export' ? 'Exporting…' : 'Export my desk'}</button><button disabled={!!busy || pass.length < 8} onClick={() => file.current?.click()}>{busy === 'restore' ? 'Restoring…' : 'Restore'}</button>
      <input ref={file} type="file" accept=".nsqdesk" style={{ display: 'none' }} onChange={e => { const f = e.target.files?.[0]; if (f) doRestore(f); e.target.value = '' }} />
      <span className="lo" style={{ fontSize: 11 }}>encrypted with your passphrase · never includes broker keys</span></div></div></div>
}

// ---------------- first-run onboarding (7 steps). Step 2 creates the real account on the engine.
export function Onboarding({ done }: { done: () => void }) {
  const [s, setS] = useState(0); const [acct, setAcct] = useState({ name: '', email: '', pw: '', pw2: '', lic: '', pin: '' })
  const [usePin, setUsePin] = useState(false); const [use2fa, setUse2fa] = useState(false)
  const [lic, setLic] = useState<Licence | null>(null); const [created, setCreated] = useState<Created | null>(null); const [ack, setAck] = useState(false); const [busy, setBusy] = useState(false); const [err, setErr] = useState('')
  const [token, setToken] = useState<string | undefined>(); const [tcode, setTcode] = useState(''); const [tok2fa, setTok2fa] = useState('')
  const confirm2fa = async () => { const r = await totpConfirm(tcode); if (r.ok && r.data.ok !== false) { setTok2fa('ok'); setCreated(c => c && { ...c, totp_pending: false }) } else setTok2fa(r.error || 'That code is not right') }
  const steps = ['Welcome', 'Your account', '24/7 setup', 'Connect broker', 'Risk limits', 'Markets & mode', 'Start on paper']
  const formOk = acct.name.trim() && /.+@.+\..+/.test(acct.email) && acct.pw.length >= 10 && acct.pw === acct.pw2 && lic?.valid && (!usePin || /^\d{6}$/.test(acct.pin))
  const checkLic = async () => { setLic(null); const r = await licenceCheck(acct.lic); setLic(r.ok ? r.data : { valid: false, message: r.error }) }
  const create = async () => {
    setBusy(true); setErr('')
    const r = await createAccount({ name: acct.name.trim(), email: acct.email.trim(), password: acct.pw, licence_key: acct.lic.trim(), pin: usePin ? acct.pin : undefined, totp: use2fa })
    setBusy(false)
    if (!r.ok) { setErr(r.error || 'Could not create the account'); return }
    let c = r.data
    if (use2fa && !c.totp_secret && c.token) {   // engine sets 2FA up in two steps: begin (secret), then confirm with a code
      if (!r.demo) useS.setState({ session: { token: c.token, email: acct.email } })
      const t = await totpBegin(); if (t.ok) c = { ...c, totp_secret: t.data.secret, totp_uri: t.data.uri, totp_pending: !t.demo }
    }
    setCreated(c); setToken(c.token); setAcct(a => ({ ...a, pw: '', pw2: '', pin: '' }))
  }
  const finish = () => { if (token) afterLogin({ token, name: acct.name, email: acct.email }); done() }
  const next = async () => { if (s === 2 && isTauri) { try { const a = await import('@tauri-apps/plugin-autostart'); await a.enable() } catch { /* optional */ } } setS(s + 1) }
  const F = (k: keyof typeof acct, l: string, type = 'text') => <input key={k} type={type} placeholder={l} value={acct[k]} onChange={e => setAcct({ ...acct, [k]: e.target.value })} autoComplete={type === 'password' ? 'new-password' : 'off'} />
  const accountStep = created ? <div data-testid="recovery">
      <div className="lbl g">ACCOUNT CREATED ✓</div>
      <div style={{ margin: '10px 0 6px' }}>Your recovery code. It is shown <b>once</b>. Write it on paper and keep it somewhere safe: it is the only way back in if you forget your password.</div>
      <div className="num" style={{ fontSize: 22, letterSpacing: '.12em', padding: '14px 16px', border: '1px dashed var(--orange)', background: '#06060B', textAlign: 'center', userSelect: 'all' }}>{created.recovery_code}</div>
      {created.totp_secret && <div style={{ marginTop: 12 }}><div className="lbl">AUTHENTICATOR APP (2FA)</div><div className="lo" style={{ fontSize: 11.5, margin: '4px 0' }}>Add this key in your authenticator app (Google Authenticator, 1Password, Authy):</div><div className="num" style={{ fontSize: 14, letterSpacing: '.14em', userSelect: 'all' }}>{created.totp_secret.replace(/(.{4})/g, '$1 ').trim()}</div>
        {created.totp_pending && <div className="row" style={{ marginTop: 8, gap: 8 }}><input inputMode="numeric" maxLength={6} placeholder="6-digit code" value={tcode} onChange={e => setTcode(e.target.value.replace(/\D/g, ''))} style={{ width: 140 }} /><button onClick={confirm2fa} disabled={tcode.length !== 6}>Turn on 2FA</button></div>}
        {tok2fa && <div className={`mono ${tok2fa === 'ok' ? 'g' : 'r'}`} style={{ fontSize: 11, marginTop: 4 }}>{tok2fa === 'ok' ? '✓ 2FA is on' : tok2fa}</div>}</div>}
      <label className="row" style={{ marginTop: 14 }}><input type="checkbox" checked={ack} onChange={e => setAck(e.target.checked)} />I have written down my recovery code</label>
      {token === 'demo' && <div className="a mono" style={{ fontSize: 10.5, marginTop: 8 }}>DEMO: this account was not saved anywhere.</div>}</div>
    : <div className="grid" style={{ gap: 9 }}>
      <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 9 }}>{F('name', 'Name')}{F('email', 'Email')}{F('pw', 'Password (10+ characters)', 'password')}{F('pw2', 'Password again', 'password')}</div>
      <div className="row" style={{ gap: 8 }}><input data-testid="licence" placeholder="Licence key · NSQ1.… (demo: NSQ-XXXX-XXXX-XXXX)" value={acct.lic} onChange={e => { setAcct({ ...acct, lic: e.target.value.trim() }); setLic(null) }} style={{ flex: 1 }} /><button onClick={checkLic} disabled={!acct.lic.trim()}>Check</button></div>
      {lic && <div className={`mono ${lic.valid ? 'g' : 'r'}`} style={{ fontSize: 11 }}>{lic.valid ? `✓ Licence valid · ${lic.plan || ''}${lic.expires ? ` · until ${lic.expires}` : ''}` : `✗ ${lic.status === 'expired' ? 'Expired: ' : ''}${lic.message || 'Licence not valid'}`}</div>}
      <div className="row" style={{ gap: 18 }}><label className="row" style={{ gap: 8 }}><input type="checkbox" checked={usePin} onChange={e => setUsePin(e.target.checked)} />Add a 6-digit PIN</label>{usePin && <input type="password" inputMode="numeric" maxLength={6} placeholder="PIN" value={acct.pin} onChange={e => setAcct({ ...acct, pin: e.target.value.replace(/\D/g, '') })} style={{ width: 110, letterSpacing: '.3em' }} />}
        <label className="row" style={{ gap: 8 }}><input type="checkbox" checked={use2fa} onChange={e => setUse2fa(e.target.checked)} />Authenticator app (2FA)</label></div>
      {err && <div className="r mono" style={{ fontSize: 11 }}>{err}</div>}
      <div className="row"><button className="primary" disabled={!formOk || busy} style={{ opacity: formOk ? 1 : .45, whiteSpace: 'nowrap' }} onClick={create}>{busy ? 'Creating…' : 'Create account'}</button><span className="lo" style={{ fontSize: 11 }}>Your account lives on this computer only, encrypted by the engine. There is no NSKO login server.</span></div></div>
  const body = [
    <div key={0} style={{ textAlign: 'center', padding: '50px 0' }}><div style={{ animation: 'sting 2.4s var(--ease) both' }}><Wordmark size={34} /></div><div className="lo" style={{ marginTop: 14 }}>by NSKO Solutions</div><div style={{ marginTop: 26, fontSize: 18 }}>Trade the markets. Automatically.</div><RiskWarning /></div>,
    <div key={1}>{accountStep}</div>,
    <div key={2}>{['Start NSKO QUANT when the computer turns on', 'Keep the computer awake while the engine is active', 'Plugged in · laptop lid closed = do nothing', 'Phone alerts paired and tested (ntfy / Telegram)'].map(c => <div key={c} className="row" style={{ padding: '7px 0' }}><span className="g">✓</span>{c}</div>)}<div className="lo" style={{ fontSize: 11, marginTop: 8 }}>It trades 24/7 as long as this computer is on and online.</div></div>,
    <div key={3} className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>{DEMO_BROKERS.slice(0, 4).map(b => <button key={b.id} style={{ padding: 14, textAlign: 'left' }}>{b.name}<div className="lo" style={{ fontSize: 11 }}>{b.id === 'paper' ? 'start here · no real money' : b.id === 'alpaca' ? 'free paper account' : 'demo / paper first'}</div></button>)}<div className="lo" style={{ fontSize: 11, gridColumn: '1/-1' }}>Key permissions: trading ON, withdrawals OFF. You connect the key on the Brokers page; it goes into this computer's keychain.</div></div>,
    <div key={4}>{[['Risk per trade', '1%'], ['Daily loss limit', '3%'], ['Weekly loss limit', '6%'], ['Max trades per day', '5'], ['Max open positions', '2']].map(([l, v]) => <div key={l} className="row" style={{ justifyContent: 'space-between', padding: '6px 0' }}><span>{l}</span><input defaultValue={v} style={{ width: 90, textAlign: 'right' }} /></div>)}</div>,
    <div key={5}><div className="row" style={{ flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>{['XAU/USD', 'BTC/USD', 'ETH/USD', 'US stocks'].map((m, i) => <label key={m} className="pill"><input type="checkbox" defaultChecked={i < 2} />{m}</label>)}</div><div className="row"><button style={{ borderColor: 'var(--orange)' }}>Auto</button><button>Manual</button></div></div>,
    <div key={6} style={{ textAlign: 'center', padding: '30px 0' }}><div className="big o" style={{ fontSize: 30 }}>PAPER</div><div className="lo" style={{ margin: '8px 0 20px' }}>Live stays locked until the paper checklist is met (21 days and 30 trades).</div><button className="primary" onClick={finish}>Open my desk</button></div>,
  ]
  const canNext = s !== 1 || (!!created && ack && !created.totp_pending)
  return <div style={{ position: 'fixed', inset: 0, background: 'radial-gradient(circle at 50% 30%, #14141E, #08080F 60%)', zIndex: 100, display: 'grid', placeItems: 'center' }}>
    <style>{`@keyframes sting{0%{opacity:0;letter-spacing:.5em;filter:blur(8px)}60%{opacity:1;filter:blur(0)}100%{letter-spacing:.14em}}`}</style>
    <div className="panel" style={{ width: 640, padding: 26 }}>
      <div className="row" style={{ gap: 4, marginBottom: 18 }}>{steps.map((x, i) => <i key={x} style={{ flex: 1, height: 2, background: i <= s ? 'var(--orange)' : 'var(--line)' }} />)}</div>
      <div className="row"><div className="lbl">STEP {s + 1} OF 7 · {steps[s].toUpperCase()}</div>{useS.getState().demo && <span className="chip a" style={{ borderColor: '#5A4020', marginLeft: 'auto' }}>DEMO DATA</span>}</div>
      <div style={{ minHeight: 300, marginTop: 14 }}>{body[s]}</div>
      <div className="row" style={{ justifyContent: 'space-between' }}><button onClick={() => s ? setS(s - 1) : done()} disabled={s === 2 && !!created}>{s ? 'Back' : 'Skip (demo)'}</button>{s < 6 && <button className="primary" disabled={!canNext} style={{ opacity: canNext ? 1 : .4 }} onClick={next}>Continue</button>}</div>
    </div></div>
}
export { fmt }
