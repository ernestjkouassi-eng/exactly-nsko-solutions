const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ args: ['--disable-gpu','--enable-unsafe-swiftshader'] });
  const jobs = [ ['godseye','?page=godseye',20000,'2026-11-26T03:03:10Z'], ['overview','?page=overview',6000,'2026-11-26T03:01:10Z'], ['tradecard','?page=tradecard',24600,'2026-11-26T03:04:10Z'], ['desk','?page=desk',6000,'2026-11-26T03:05:10Z'] ];
  for (const [n,q,w,tg] of jobs) {
    const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 });
    const pg = await ctx.newPage();
    await pg.addInitScript((tg) => { try { localStorage.setItem('nq_onboarded','1') } catch(e){}
      const off = tg - Date.now(), OD = Date; class D extends OD { constructor(...a){ if(a.length===0) super(OD.now()+off); else super(...a) } static now(){ return OD.now()+off } }; window.Date = D; }, Date.parse(tg));
    await pg.goto('http://localhost:4190/'+q); await pg.waitForTimeout(w);
    const t0=Date.now(); await pg.screenshot({ path: `stills/${n}@2x.png` }); console.log(n, 'shot ms', Date.now()-t0);
    await ctx.close();
  }
  await b.close();
})();
