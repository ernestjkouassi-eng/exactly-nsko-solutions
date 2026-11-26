const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ args: ['--use-angle=swiftshader','--enable-unsafe-swiftshader'] });
  const pages = process.argv.slice(2);
  for (const p of pages) {
    const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 } });
    const pg = await ctx.newPage();
    await pg.addInitScript(() => { try { localStorage.setItem('nq_onboarded','1') } catch(e){} });
    const url = p === 'onboard' ? 'http://localhost:4190/?onboard=1' : `http://localhost:4190/?page=${p}`;
    await pg.goto(url); await pg.waitForTimeout(p==='godseye'?15000:5000);
    await pg.screenshot({ path: `stills/${p}.png` }); console.log('ok', p);
    await ctx.close();
  }
  await b.close();
})();
