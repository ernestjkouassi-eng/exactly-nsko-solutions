// Records the live NSKO Solutions site as exact 24 fps frame sequences.
// The page clock is frozen and stepped 1/24 s per frame, so every scene
// (canvas, three.js, gsap, Lenis) moves exactly as a viewer would see it.
// usage: node capture.js <shot> [maxFrames]
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const SITE = process.env.SITE || 'http://localhost:8811/';
const OUT = process.env.OUT || '/home/user/film/rec';
const STEP = 1000 / 24;
const ARGS = process.env.NOGL ? ['--disable-gpu', '--hide-scrollbars', '--force-color-profile=srgb'] : ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--hide-scrollbars', '--force-color-profile=srgb'];

const SHOTS = {
  // hero tile: pointer sweeps so the operator's head turns
  hero: { vw: 1920, vh: 1080, dsf: 1.5, frames: 84, async prep(p) {}, async frame(p, i, n) {
      const x = 960 + Math.sin(i / n * Math.PI * 2) * 700, y = 420 + Math.sin(i / n * Math.PI) * 60;
      await p.mouse.move(x, y); } },
  // Machine Lab: drone explodes, code types
  drone: { vw: 1920, vh: 1080, dsf: 1.25, frames: 144, async prep(p) {
      await p.evaluate(() => document.getElementById('lab').scrollIntoView());
      await p.clock.runFor(300); await p.click('#t-drone'); await p.evaluate(() => scrollBy(0, document.querySelector('#tp-drone').getBoundingClientRect().top - 150)); await p.clock.runFor(800);
      await p.evaluate(() => document.querySelector('#steps button').click()); },
    async frame(p, i) { if (i === 72) await p.evaluate(() => document.querySelectorAll('#steps button')[1].click()); } },
  // Field kit: Medusa opens
  medusa: { vw: 1920, vh: 1080, dsf: 1, frames: 66, every: 2, async prep(p) {
      await p.evaluate(() => document.getElementById('lab').scrollIntoView());
      await p.clock.runFor(300); await p.click('#t-field'); await p.evaluate(() => scrollBy(0, document.querySelector('#tp-field').getBoundingClientRect().top - 70)); await p.clock.runFor(1500); }, async frame() {} },
  // Desk unit: Nova turns to camera
  nova: { vw: 1920, vh: 1080, dsf: 1, frames: 120, async prep(p) {
      await p.evaluate(() => document.getElementById('lab').scrollIntoView());
      await p.clock.runFor(300); await p.click('#t-desk'); await p.evaluate(() => scrollBy(0, document.querySelector('#tp-desk').getBoundingClientRect().top - 110)); await p.clock.runFor(1500); await p.mouse.move(200, 300); },
    async frame(p, i, n) { const k = Math.min(1, i / (n * .7)); const e = k * k * (3 - 2 * k); await p.mouse.move(200 + e * 760, 300 + e * 160, { steps: 1 }); } },
  // page glide: services -> industries -> projects
  glide: { vw: 1920, vh: 1080, dsf: 1.5, frames: 120, async prep(p) { await p.evaluate(() => scrollTo(0, 0)); },
    async frame(p, i, n) { const k = i / (n - 1), e = k * k * (3 - 2 * k);
      await p.evaluate(e => { const a = document.getElementById('industries').offsetTop - 70, b = document.getElementById('projects').offsetTop - 70; scrollTo(0, a + (b - a) * e); }, e); } },
  // industries row
  sectors: { vw: 1920, vh: 1080, dsf: 1.5, frames: 72, async prep(p) { await p.evaluate(() => scrollTo(0, document.getElementById('industries').offsetTop - 70)); },
    async frame(p, i, n) { await p.mouse.move(300 + i / n * 1300, 600); } },
  // phone: the site on a 390 wide screen, scrolled through the deck
  phone: { vw: 390, vh: 844, dsf: 3, mobile: true, frames: 120, async prep(p) { await p.evaluate(() => scrollTo(0, 0)); },
    async frame(p, i, n) { const k = Math.max(0, (i - 30) / (n - 30)), e = k * k * (3 - 2 * k);
      await p.evaluate(e => scrollTo(0, e * 1400), e); } },
};

(async () => {
  const name = process.argv[2], S = SHOTS[name], max = +(process.argv[3] || S.frames);
  const dir = `${OUT}/${name}`; fs.mkdirSync(dir, { recursive: true });
  const b = await chromium.launch({ args: ARGS });
  const ctx = await b.newContext({ viewport: { width: S.vw, height: S.vh }, deviceScaleFactor: S.dsf, isMobile: !!S.mobile, hasTouch: !!S.mobile, colorScheme: 'dark' });
  const p = await ctx.newPage(); const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  await p.clock.install({ time: new Date('2026-11-22T10:00:00Z') });
  await p.goto(SITE, { waitUntil: 'load' });
  await p.clock.runFor(1500);
  await p.evaluate(() => { const s = document.getElementById('ldskip'); s && s.click(); });
  await p.clock.runFor(2500);
  await p.addStyleTag({ content: '#cursor,.cursor,#totop{display:none!important}' });
  await S.prep(p);
  const t0 = Date.now();
  for (let i = 0; i < max; i++) {
    await S.frame(p, i, S.frames);
    await p.clock.runFor(STEP * (S.every || 1));
    await p.screenshot({ path: `${dir}/f${String(i).padStart(4, '0')}.jpg`, type: 'jpeg', quality: 94, timeout: 0 });
  }
  console.log(name, max, 'frames', ((Date.now() - t0) / max / 1000).toFixed(2) + 's/frame', 'errors:', errs.length ? errs : 0);
  await b.close();
})();
