// Stage 4 end-to-end: the REAL engine + the built desk in headless Chromium, in engine mode (?source=engine).
//   cd nsko-quant && node tools/e2e-stage4.cjs
// Starts `engine/.venv/bin/python -m nsq` with NSQ_DEV=1 on a fresh temp NSQ_DATA, and `vite preview` on :4173
// (build first: cd app && npx vite build). Licence keys for the test come from env LICENCE / LICENCE_EXPIRED
// (make them with tools/make-licence). Screenshots go to docs/screenshots/stage-4/. Exit code 1 if a check fails.
const { chromium } = require('playwright')
const { spawn } = require('child_process')
const fs = require('fs'), os = require('os'), path = require('path')

const ROOT = path.resolve(__dirname, '..'), OUT = path.join(ROOT, 'docs/screenshots/stage-4')
const ENGINE = 'http://127.0.0.1:8787', UI = 'http://localhost:4173'
const EMAIL = 'desk@example.com', PW = 'correct horse battery 1'
const LIC = (process.env.LICENCE || '').trim(), LIC_OLD = (process.env.LICENCE_EXPIRED || '').trim()
const results = []
const check = (name, ok, detail = '') => { results.push({ name, ok: !!ok, detail }); console.log(`${ok ? 'PASS' : 'FAIL'} · ${name}${detail ? ' · ' + detail : ''}`) }
const sleep = ms => new Promise(r => setTimeout(r, ms))
const H = { 'Content-Type': 'application/json', 'X-NSQ-Client': 'e2e' }
async function api(method, p, body, token) {
  const r = await fetch(ENGINE + p, { method, headers: { ...H, ...(token ? { Authorization: `Bearer ${token}` } : {}) }, body: body ? JSON.stringify(body) : undefined })
  return { status: r.status, json: await r.json().catch(() => ({})) }
}
async function waitFor(fn, ms = 20000, every = 250) { const t0 = Date.now(); while (Date.now() - t0 < ms) { try { const v = await fn(); if (v) return v } catch { /* retry */ } await sleep(every) } return null }

;(async () => {
  fs.mkdirSync(OUT, { recursive: true })
  const data = fs.mkdtempSync(path.join(os.tmpdir(), 'nsq-e2e-'))
  const eng = spawn(path.join(ROOT, 'engine/.venv/bin/python'), ['-m', 'nsq', '--port', '8787'], { cwd: path.join(ROOT, 'engine'),
    env: { ...process.env, NSQ_DATA: data, NSQ_DEV: '1', NSQ_VAULT_BACKEND: 'file' }, stdio: ['ignore', 'pipe', 'pipe'] })
  const elog = fs.createWriteStream(path.join(data, 'e2e-engine-stdout.log')); eng.stdout.pipe(elog); eng.stderr.pipe(elog)
  const ui = spawn('npx', ['vite', 'preview', '--port', '4173', '--strictPort'], { cwd: path.join(ROOT, 'app'), stdio: 'ignore' })
  let browser
  const stop = () => { try { eng.kill('SIGINT') } catch { } try { ui.kill('SIGTERM') } catch { } }
  process.on('exit', stop)
  try {
    check('engine starts and answers /health', await waitFor(async () => (await fetch(ENGINE + '/health')).ok, 40000))
    check('desk preview server starts', await waitFor(async () => (await fetch(UI)).ok, 30000))
    const tokFile = path.join(data, 'shell.token')
    check('engine wrote the tray shared secret (owner-only file)', fs.existsSync(tokFile) && (fs.statSync(tokFile).mode & 0o077) === 0, `${data}/shell.token`)

    browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] })
    const p = await browser.newPage({ viewport: { width: 1920, height: 1080 } })
    const errors = []
    p.on('pageerror', e => { errors.push(e.message); console.log('PAGEERROR', e.message) })
    p.on('console', m => { if (m.type() === 'error' && !/WebSocket|ERR_CONNECTION|Failed to load resource/.test(m.text())) console.log('CONSOLE', m.text().slice(0, 200)) })
    const shot = async (n) => { await p.screenshot({ path: `${OUT}/${n}.png`, timeout: 90000 }); console.log('  shot', n) }
    const nav = async (id, ms = 1500) => { await p.locator(`[data-nav=${id}]`).click(); await p.waitForTimeout(ms) }
    const confirmDialog = async (label) => { await p.getByRole('button', { name: label, exact: true }).last().click(); await p.waitForTimeout(600) }

    // ---------------------------------------------------------------- 1 · create account -> recovery code
    await p.goto(`${UI}/?source=engine`); await p.waitForTimeout(2500)
    check('first run on a new engine shows onboarding', await p.getByText('STEP 1 OF 7').isVisible())
    await p.getByRole('button', { name: 'Continue' }).click(); await p.waitForTimeout(400)
    await p.getByPlaceholder('Name').fill('Ernest K.'); await p.getByPlaceholder('Email').fill(EMAIL)
    await p.getByPlaceholder('Password (10+ characters)').fill(PW); await p.getByPlaceholder('Password again').fill(PW)
    if (LIC_OLD) {
      await p.getByTestId('licence').fill(LIC_OLD); await p.getByRole('button', { name: 'Check' }).click(); await p.waitForTimeout(800)
      check('expired licence is refused by the engine', await p.getByText(/Expired: This licence ended on/).isVisible()); await shot('01-licence-expired')
    }
    await p.getByTestId('licence').fill('NSQ1.not-a-real.key'); await p.getByRole('button', { name: 'Check' }).click(); await p.waitForTimeout(800)
    check('invalid licence is refused by the engine', await p.getByText(/damaged or incomplete|not genuine/).isVisible())
    await p.getByTestId('licence').fill(LIC); await p.getByRole('button', { name: 'Check' }).click(); await p.waitForTimeout(800)
    check('valid licence accepted (Ed25519, offline)', await p.getByText(/Licence valid · Pro/).isVisible()); await shot('02-onboarding-account-valid-licence')
    await p.getByRole('button', { name: 'Create account' }).click(); await p.waitForTimeout(2500)
    const code = (await p.getByTestId('recovery').locator('.num').first().innerText()).trim()
    check('account created on the engine, recovery code shown once', /^[A-Z0-9]{4}(-[A-Z0-9]{4}){5}$/.test(code), code.replace(/[A-Z0-9]/g, '•'))
    await shot('03-recovery-code')
    await p.getByText('I have written down my recovery code').click()
    for (let i = 0; i < 5; i++) { await p.getByRole('button', { name: 'Continue' }).click(); await p.waitForTimeout(300) }
    await p.getByRole('button', { name: 'Open my desk' }).click(); await p.waitForTimeout(3500)
    check('desk opens on the engine (ENGINE · ONLINE)', await p.getByText('ENGINE · ONLINE').first().isVisible()); await shot('04-overview-engine-online')

    // ---------------------------------------------------------------- 2 · lock screen + login (wrong, then right)
    await p.goto(`${UI}/?source=engine`); await p.waitForTimeout(2500)
    check('reload asks for login (token kept in memory only)', await p.getByText('UNLOCK THE DESK').isVisible())
    await p.getByPlaceholder('Email').fill(EMAIL); await p.getByPlaceholder('Password').fill('wrong password here'); await p.getByRole('button', { name: 'Continue' }).click(); await p.waitForTimeout(1200)
    check('wrong password is refused', await p.getByText('Email or password is not right.').isVisible()); await shot('05-lock-wrong-password')
    await p.getByPlaceholder('Password').fill(PW); await p.getByRole('button', { name: 'Continue' }).click(); await p.waitForTimeout(3000)
    check('right password unlocks the desk and the WebSocket connects', await p.getByText('ENGINE · ONLINE').first().isVisible())
    const login = await api('POST', '/account/login', { email: EMAIL, password: PW }); const T = login.json.token
    check('API login for the test driver', !!T)

    // ---------------------------------------------------------------- 3 · settings load / save
    await nav('settings', 2000)
    const perTrade = p.locator('input[type=number]').first()
    check('settings load from the engine (not the DEMO SETTINGS chip)', !(await p.getByText('DEMO SETTINGS').isVisible()) && (await perTrade.inputValue()) === '1')
    await perTrade.fill('0.8'); await p.getByRole('button', { name: 'Save settings' }).click(); await p.waitForTimeout(1200)
    const st = (await api('GET', '/settings')).json
    check('settings saved to the engine (risk.per_trade_pct = 0.8)', st['risk.per_trade_pct'] === 0.8, `engine value ${st['risk.per_trade_pct']}`)
    await shot('06-settings-saved')
    await perTrade.fill('1'); await p.getByRole('button', { name: 'Save settings' }).click(); await p.waitForTimeout(800)

    // ---------------------------------------------------------------- 4 · brokers
    await nav('brokers', 2000)
    check('brokers list from the engine (paper connected, OANDA coming soon)', (await p.getByTestId('brokers').getByText('CONNECTED').count()) >= 1 && await p.getByText('COMING SOON').first().isVisible())
    await shot('07-brokers')

    // ---------------------------------------------------------------- 5 · a full paper trade (Auto) through the trade flow
    await nav('tradecard', 1200)
    let r = await api('POST', '/dev/run-demo-trade', { step_s: 4 }, T)
    check('dev demo trade started (NSQ_DEV=1, session needed)', r.json.state === 'running', JSON.stringify(r.json))
    check('Trade Card fills from engine events up to the order', await waitFor(async () => (await p.getByTestId('tc-7').innerText()).includes('Filled') && !(await p.getByTestId('tc-7').innerText()).includes('waiting…'), 60000))
    await shot('08-tradecard-auto-filled')
    check('Trade Card shows the exit (scale-out, target, journal)', await waitFor(async () => (await p.getByTestId('tc-8').innerText()).includes('journal written'), 40000))
    await shot('09-tradecard-auto-exit')
    const j1 = (await api('GET', '/journal')).json.trades
    check('journal has the closed paper trade', j1.length === 1 && j1[0].mode === 'paper', `${j1.length} row(s), ${j1[0] ? j1[0].r_multiple.toFixed(2) + 'R' : ''}`)
    const aud = (await api('GET', '/audit?n=200')).json.entries.map(e => e.action)
    check('audit has an entry per step (trade.open, position.scale_out, trade.exit)', ['trade.open', 'position.scale_out', 'trade.exit'].every(a => aud.includes(a)))
    check('audit hash chain verifies', (await api('GET', '/audit/verify')).json.ok === true)

    // ---------------------------------------------------------------- 6 · Manual: the card waits for Approve
    await p.getByTestId('mode-manual').click(); await p.waitForTimeout(800)
    check('Manual mode saved to the engine', (await api('GET', '/settings')).json.trade_mode === 'manual')
    r = await api('POST', '/dev/run-demo-trade', { step_s: 8 }, T)
    check('Manual: Approve appears at the order ticket', await waitFor(() => p.getByTestId('tc-approve').isVisible(), 60000))
    await shot('10-tradecard-manual-waiting')
    await p.getByTestId('tc-approve').click()
    check('Manual: approved trade is filled', await waitFor(async () => (await p.getByTestId('tc-7').innerText()).includes('Filled') && !(await p.getByTestId('tc-7').innerText()).includes('waiting…'), 30000))
    await shot('11-tradecard-manual-approved')

    // ---------------------------------------------------------------- 7 · kill switch (hold 1.5 s), then release
    const ks = p.getByTestId('kill-switch'); const box = await ks.boundingBox()
    await p.mouse.move(box.x + box.width / 2, box.y + box.height / 2); await p.mouse.down(); await p.waitForTimeout(1900); await p.mouse.up(); await p.waitForTimeout(1500)
    const h1 = (await api('GET', '/health')).json
    check('kill switch: engine locked', h1.killed === true)
    const acct = (await api('GET', '/account/summary')).json
    check('kill switch: no open positions or orders left', acct.positions.length === 0 && acct.orders.length === 0, `${acct.positions.length} positions, ${acct.orders.length} orders`)
    check('desk shows TRADING LOCKED', await p.getByTestId('kill-release').isVisible()); await shot('12-kill-switch-on')
    await p.getByTestId('kill-release').click(); await p.waitForTimeout(400); await confirmDialog('Re-enable')
    await p.waitForTimeout(1200)
    check('release: trading re-enabled (needs the login)', (await api('GET', '/health')).json.killed === false && await p.getByTestId('kill-switch').isVisible())
    await shot('13-kill-switch-released')
    await api('POST', '/settings', { values: { trade_mode: 'auto' } }, T)

    // tray path: pause with the shared secret (no session), as the Rust shell does
    const tok = fs.readFileSync(tokFile, 'utf8').trim()
    const tp = await fetch(ENGINE + '/trading/pause', { method: 'POST', headers: { ...H, 'X-NSQ-Shell': tok }, body: JSON.stringify({ paused: true }) })
    check('tray pause works with the shared secret, no login', tp.ok && (await api('GET', '/health')).json.paused === true)
    await fetch(ENGINE + '/trading/pause', { method: 'POST', headers: { ...H, 'X-NSQ-Shell': tok }, body: JSON.stringify({ paused: false }) })
    const tk = await fetch(ENGINE + '/kill', { method: 'POST', headers: H, body: JSON.stringify({ reason: 'tray test', source: 'tray' }) })
    check('tray kill works without any login', tk.ok && (await api('GET', '/health')).json.killed === true)
    await api('POST', '/trading/enable', {}, T); await p.waitForTimeout(1500)

    // ---------------------------------------------------------------- 8 · withdraw helper
    await nav('withdraw', 2000)
    check('withdraw helper loads from the engine', await p.getByTestId('withdraw-note').isVisible() && await p.getByText('Paper simulator').first().isVisible())
    await p.getByRole('button', { name: 'Pause new trades' }).click(); await p.waitForTimeout(1200)
    check('withdraw step 1 pauses new trades on the engine', (await api('GET', '/health')).json.paused === true)
    await p.getByRole('button', { name: /Paper money: nothing to withdraw/ }).click(); await p.waitForTimeout(300)
    await p.getByRole('button', { name: /I have withdrawn/ }).click(); await p.waitForTimeout(2000)
    check('withdraw step 4 rescales and resumes', (await api('GET', '/health')).json.paused === false && await p.getByText(/Every new trade is sized from the new balance/).isVisible())
    await shot('14-withdraw-helper')

    // ---------------------------------------------------------------- 9 · strategy promote / rollback
    await nav('strategies', 2500)
    await p.getByText('Dev demo XAU').first().click(); await p.waitForTimeout(500)
    await p.getByRole('button', { name: /Version history/ }).click(); await p.waitForTimeout(500)
    await shot('15-strategy-versions')
    await p.getByRole('button', { name: 'Roll back to v1' }).click(); await p.waitForTimeout(300); await confirmDialog('Roll back to v1'); await p.waitForTimeout(1500)
    const sv = (await api('GET', '/strategies?include=versions')).json.strategies.find(s => s.id === 'dev-demo-xau')
    check('rollback to v1 on the engine', sv && sv.active_version === 1, `active v${sv && sv.active_version}`)
    await shot('16-strategy-rolled-back')
    await p.getByRole('button', { name: 'To live' }).click(); await p.waitForTimeout(300); await confirmDialog('To live'); await p.waitForTimeout(1200)
    check('promote to live is refused while live is locked', await p.getByText(/Live is locked/).first().isVisible())
    await p.getByText('Trend-XAU').first().click(); await p.waitForTimeout(500)
    await p.getByRole('button', { name: 'To paper' }).click(); await p.waitForTimeout(300); await confirmDialog('To paper'); await p.waitForTimeout(1500)
    const tx = (await api('GET', '/strategies')).json.strategies.find(s => s.id === 'trend-xau')
    check('promote Trend-XAU to paper on the engine', tx && tx.status === 'paper', tx && tx.status)
    await shot('17-strategy-promoted')
    await api('POST', '/strategies/trend-xau/promote', { to: 'lab' }, T)   // keep the scanner quiet for the rest of the run

    // ---------------------------------------------------------------- 10 · paper & live checklist
    await nav('paperlive', 2000)
    check('paper & live checklist from the engine', await p.getByText('from the engine').isVisible() && await p.getByText(/\d+ trades ·/).first().isVisible())
    await p.getByPlaceholder(/Type "I understand/).fill('I understand I can lose money'); await p.waitForTimeout(300)
    check('Go live stays disabled until every box is ticked', await p.getByRole('button', { name: 'Go live' }).isDisabled())
    await shot('18-paper-live-checklist')

    // ---------------------------------------------------------------- 11 · engine-fed pages: Live Desk, Lab, Research, Agents, JARVIS
    await nav('desk', 5000); check('Live Desk: candles from the engine, flagged synthetic for gold', await p.getByTestId('desk-source').innerText().then(t => t.includes('SYNTHETIC')))
    await shot('19-live-desk-xau-engine')
    await p.getByRole('button', { name: 'BTC/USD' }).click(); await p.waitForTimeout(6000)
    const src = await p.getByTestId('desk-source').innerText(); check('Live Desk: BTC candles', src.length > 0, src)
    await shot('20-live-desk-btc-engine')
    r = await api('POST', '/lab/run', { recipe_id: 'vwap-rev-btc', variants: 10, start: '2025-06-01' }, T); check('Lab run started (session needed)', r.json.state === 'running')
    await waitFor(async () => { const j = (await api('GET', '/lab/jobs')).json['vwap-rev-btc']; return j && j.state !== 'running' }, 240000, 2000)
    const job = (await api('GET', '/lab/jobs')).json['vwap-rev-btc']; check('Lab run finished', job && job.state === 'done', job && (job.error || `${job.summary.clear} clear · ${job.summary.sieve} sieve · ${job.summary.failed} failed · synthetic=${job.summary.synthetic}`))
    await nav('lab', 3000); check('Lab fan draws the real variants', (await p.locator('table tbody tr').count()) >= 10)
    await shot('21-lab-fan-engine')
    r = await api('POST', '/research/round', { max_sources: 3 }, T); check('research round started', r.json.state === 'running', JSON.stringify(r.json))
    await waitFor(async () => (await api('GET', '/research/status')).json.running === false, 180000, 2000)
    await nav('research', 2500); check('Research: sources and terms from the engine', await p.getByTestId('now-reading').isVisible())
    await shot('22-research-engine')
    await nav('agents', 4000); check('Agent Room: handoffs from the engine', (await p.getByTestId('handoffs').locator('tr').count()) >= 1)
    await shot('23-agent-room-engine')
    await p.keyboard.press('Control+j'); await p.waitForTimeout(600)
    await p.getByTestId('jarvis-input').fill('How is my desk doing?'); await p.keyboard.press('Enter')
    check('JARVIS answers through the engine (honest without Ollama)', await waitFor(async () => (await p.getByTestId('jarvis-reply').last().innerText()).includes('not installed') || (await p.getByTestId('jarvis-reply').last().innerText()).includes('LOCAL MODEL'), 100000))
    await shot('24-jarvis-engine')
    check('no uncaught page errors', errors.length === 0, errors.slice(0, 3).join(' | '))
  } catch (e) { check('e2e script ran to the end', false, String(e && e.stack || e).slice(0, 400)) }
  finally {
    if (browser) await browser.close()
    stop(); await sleep(1500)
    fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify({ when: new Date().toISOString(), data_dir: data, results }, null, 1))
    const bad = results.filter(r => !r.ok); console.log(`\n${results.length - bad.length}/${results.length} checks passed`)
    process.exit(bad.length ? 1 : 0)
  }
})()
