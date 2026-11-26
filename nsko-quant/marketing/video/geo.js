const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ args: ['--disable-gpu','--enable-unsafe-swiftshader'] });
  for (const mode of ['Offline','Map']) {
  const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 });
  const pg = await ctx.newPage();
  await pg.addInitScript((tg) => { try { localStorage.setItem('nq_onboarded','1') } catch(e){}
    const off = tg - Date.now(), OD = Date; class D extends OD { constructor(...a){ if(a.length===0) super(OD.now()+off); else super(...a) } static now(){ return OD.now()+off } }; window.Date = D; }, Date.parse('2026-11-26T03:03:10Z'));
  await pg.goto('http://localhost:4190/?page=godseye'); await pg.waitForTimeout(8000);
  await pg.getByRole('button', { name: mode, exact: true }).click(); await pg.waitForTimeout(14000);
  await pg.screenshot({ path: `stills/godseye_${mode}@2x.png` }); console.log(mode);
  await ctx.close() }
  await b.close();
})();
