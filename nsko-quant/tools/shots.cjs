// Stage 1 screenshots + a frame-rate sample per page (headless Chromium, software WebGL).
const { chromium } = require('playwright')
const pages = ['overview','lab','research','strategies','knowledge','agents','godseye','desk','tradecard','decisions','paperlive','brokers','engine','costs','settings','help']
;(async () => {
  const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] })
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } }); const out = []
  for (const [i, pg] of pages.entries()) {
    await p.goto(`http://localhost:4173/?page=${pg}`); await p.waitForTimeout(pg === 'tradecard' ? 9000 : 5000)
    const fps = await p.evaluate(() => new Promise(r => { let n = 0; const t0 = performance.now(); const f = () => { n++; performance.now() - t0 < 2000 ? requestAnimationFrame(f) : r(Math.round(n / 2)) }; requestAnimationFrame(f) }))
    await p.screenshot({ timeout: 90000, path: `docs/screenshots/stage-1/${String(i + 1).padStart(2, '0')}-${pg}.png` }); out.push(`${pg}: ${fps} fps`); console.log(pg, fps, 'fps')
  }
  await p.goto('http://localhost:4173/?onboard=1'); await p.waitForTimeout(2600); await p.screenshot({ path: 'docs/screenshots/stage-1/17-onboarding.png' })
  await p.goto('http://localhost:4173/?page=overview'); await p.waitForTimeout(2500); await p.keyboard.press('Control+j'); await p.waitForTimeout(800); await p.screenshot({ path: 'docs/screenshots/stage-1/18-jarvis.png' })
  console.log(out.join('\n')); await b.close()
})()
