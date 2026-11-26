// Stage 2 screenshots (headless Chromium, software WebGL). Needs `npx vite preview` on :4173.
// Engine screens use a throwaway mock engine passed with ?engine=http://127.0.0.1:8799 (set MOCK=...); without it they show the offline fallback.
const { chromium } = require('playwright')
const B = 'http://localhost:4173', OUT = 'docs/screenshots/stage-2', MOCK = process.env.MOCK || 'http://127.0.0.1:8799'
;(async () => {
  const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] })
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } })
  p.on('pageerror', e => console.log('PAGEERROR', e.message)); p.on('console', m => { if (m.type() === 'error') console.log('CONSOLE', m.text().slice(0, 200)) })
  const shot = async (n) => { await p.screenshot({ path: `${OUT}/${n}.png`, timeout: 90000 }); console.log('shot', n) }
  const nav = async (id) => { await p.locator(`[data-nav=${id}]`).click(); await p.waitForTimeout(1500) }

  // 1 · onboarding, account step (demo mode)
  await p.goto(`${B}/?onboard=1&source=demo`); await p.waitForTimeout(1200)
  await p.getByRole('button', { name: 'Continue' }).click(); await p.waitForTimeout(400)
  await p.getByPlaceholder('Name').fill('Ernest K.'); await p.getByPlaceholder('Email').fill('desk@example.com')
  await p.getByPlaceholder('Password (10+ characters)').fill('correct horse 1'); await p.getByPlaceholder('Password again').fill('correct horse 1')
  await p.getByPlaceholder(/Licence key/).fill('NSQ-7K2P-QX9D-4HMA'); await p.getByRole('button', { name: 'Check' }).click(); await p.waitForTimeout(300)
  await p.getByText('Add a 6-digit PIN').click(); await p.getByPlaceholder('PIN').fill('482913'); await p.getByText('Authenticator app (2FA)').click()
  await shot('01-onboarding-account')
  await p.getByRole('button', { name: 'Create account' }).click(); await p.waitForTimeout(500); await shot('02-onboarding-recovery-code')

  // 2 · lock screen against the mock engine: password, then authenticator code
  await p.goto(`${B}/?page=overview&source=engine&engine=${encodeURIComponent(MOCK)}`); await p.waitForTimeout(2500)
  await p.getByPlaceholder('Email').fill('desk@example.com'); await p.getByPlaceholder('Password').fill('correct horse 1'); await shot('03-lock-password')
  await p.getByRole('button', { name: 'Continue' }).click(); await p.waitForTimeout(800); await shot('04-lock-authenticator')
  await p.locator('input[inputmode=numeric]').fill('123456'); await p.getByRole('button', { name: 'Unlock' }).click(); await p.waitForTimeout(4000)
  await shot('05-engine-online-overview')
  await nav('settings'); await p.waitForTimeout(1200); await shot('06-settings-source-engine')
  await nav('withdraw'); await p.waitForTimeout(1000); await shot('07-withdraw-engine')

  // 3 · settings in demo mode, and the engine-offline fallback
  await p.goto(`${B}/?page=settings&source=demo`); await p.waitForTimeout(1500); await shot('08-settings-source-demo')
  await p.goto(`${B}/?page=settings&source=engine&engine=${encodeURIComponent('http://127.0.0.1:8798')}`); await p.waitForTimeout(3500); await shot('09-engine-offline-fallback')

  // 4 · withdraw in demo mode
  await p.goto(`${B}/?page=withdraw&source=demo`); await p.waitForTimeout(1500); await shot('10-withdraw-demo')

  // 5 · God's Eye on CesiumJS (demo layers): satellite, night-vision, thermal, OSM map
  await p.goto(`${B}/?page=godseye&source=demo`); await p.waitForTimeout(14000); await shot('11-godseye-cesium-satellite')
  await p.getByRole('button', { name: 'Night-vision' }).click(); await p.waitForTimeout(2500); await shot('12-godseye-night-vision')
  await p.getByRole('button', { name: 'Thermal' }).click(); await p.waitForTimeout(2500); await shot('13-godseye-thermal')
  await p.getByRole('button', { name: 'Normal' }).click(); await p.getByRole('button', { name: 'Map', exact: true }).click(); await p.waitForTimeout(8000); await shot('14-godseye-osm-map')
  const fps = await p.evaluate(() => new Promise(r => { let n = 0; const t0 = performance.now(); const f = () => { n++; performance.now() - t0 < 2000 ? requestAnimationFrame(f) : r(Math.round(n / 2)) }; requestAnimationFrame(f) }))
  console.log('godseye fps (software WebGL)', fps)

  // 6 · Strategy Book version history
  await p.goto(`${B}/?page=strategies&source=demo&history=1`); await p.waitForTimeout(1500)
  await p.getByText('Trend-follower XAU').first().click(); await p.waitForTimeout(800); await shot('15-strategy-version-history')
  await b.close()
})()
