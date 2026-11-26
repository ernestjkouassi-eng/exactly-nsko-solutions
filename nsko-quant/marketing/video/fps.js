const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ args: ['--use-angle=swiftshader','--enable-unsafe-swiftshader'] });
  for (const p of process.argv.slice(2)) {
  const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 } });
  const pg = await ctx.newPage();
  await pg.addInitScript(() => { try { localStorage.setItem('nq_onboarded','1') } catch(e){} });
  await pg.goto('http://localhost:4190/?page='+p); await pg.waitForTimeout(4000);
  const fps = await pg.evaluate(() => new Promise(r => { let n=0; const t0=performance.now(); const f=()=>{n++; if(performance.now()-t0<3000) requestAnimationFrame(f); else r(n/3)}; requestAnimationFrame(f) }));
  console.log(p, 'rAF fps', fps.toFixed(1)); await ctx.close() }
  await b.close();
})();
