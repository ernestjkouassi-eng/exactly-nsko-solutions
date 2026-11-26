// Crisp captures for the posters: the brain sphere drawn large, and the Trade Card at its final step.
const { chromium } = require('playwright');
const DATE = (tg) => { try { localStorage.setItem('nq_onboarded','1') } catch(e){}
  const off = tg - Date.now(), OD = Date; class D extends OD { constructor(...a){ if(a.length===0) super(OD.now()+off); else super(...a) } static now(){ return OD.now()+off } }; window.Date = D; };
(async () => {
  const b = await chromium.launch({ args: ['--disable-gpu','--enable-unsafe-swiftshader'] });
  // 1) sphere
  let ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 });
  let pg = await ctx.newPage(); await pg.addInitScript(DATE, Date.parse('2026-11-26T03:01:10Z'));
  await pg.goto('http://localhost:4190/?page=overview'); await pg.waitForTimeout(3000);
  const info = await pg.evaluate(() => { const cs=[...document.querySelectorAll('canvas')].map(c=>({c,r:c.getBoundingClientRect()})).sort((a,b)=>b.r.width*b.r.height-a.r.width*a.r.height); const c=cs[0].c;
    c.id='bigc'; c.style.position='fixed'; c.style.left='0'; c.style.top='0'; c.style.width='1920px'; c.style.height='1080px'; c.style.zIndex='9999'; c.style.background='#08080F';
    window.dispatchEvent(new Event('resize')); return [cs[0].r.width, cs[0].r.height] });
  console.log('brain canvas was', info);
  await pg.waitForTimeout(2500);
  for (let i = 0; i < 3; i++) { await pg.waitForTimeout(1300); await pg.screenshot({ path: `src/sphere_${i}.png` }); }
  await ctx.close();
  // 2) trade card, final step, 3x
  ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 3 });
  pg = await ctx.newPage(); await pg.addInitScript(DATE, Date.parse('2026-11-26T03:04:10Z'));
  await pg.addInitScript(() => { const si = window.setInterval.bind(window); window.setInterval = (f, d, ...a) => si((...x) => { if (!window.__pause) f(...x) }, d, ...a) });
  await pg.goto('http://localhost:4190/?page=tradecard'); await pg.getByText('CLOSED +1.7R', { exact: false }).waitFor({ timeout: 60000 }); await pg.evaluate(() => { window.__pause = true }); await pg.waitForTimeout(800);
  await pg.screenshot({ path: 'src/tradecard@3x.png' });
  await ctx.close(); await b.close();
})();
