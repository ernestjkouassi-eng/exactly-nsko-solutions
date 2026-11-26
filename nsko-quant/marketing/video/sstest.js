const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ args: ['--use-angle=swiftshader','--enable-unsafe-swiftshader'] });
  const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 } });
  const pg = await ctx.newPage();
  await pg.addInitScript(() => { try { localStorage.setItem('nq_onboarded','1') } catch(e){} });
  await pg.clock.install();
  await pg.goto('http://localhost:4190/?page=overview');
  await pg.clock.runFor(3000);
  let t0=Date.now();
  for (let i=0;i<10;i++){ await pg.clock.runFor(33.333); await pg.screenshot({path:`rec/ss${i}.jpg`, type:'jpeg', quality:92}); }
  console.log('jpeg ms/frame', (Date.now()-t0)/10);
  t0=Date.now();
  for (let i=0;i<10;i++){ await pg.clock.runFor(33.333); await pg.screenshot({path:`rec/ss${i}.png`}); }
  console.log('png ms/frame', (Date.now()-t0)/10);
  const cdp = await ctx.newCDPSession(pg);
  t0=Date.now();
  for (let i=0;i<10;i++){ await pg.clock.runFor(33.333); const r = await cdp.send('Page.captureScreenshot',{format:'jpeg',quality:92}); }
  console.log('cdp jpeg ms/frame', (Date.now()-t0)/10);
  await b.close();
})();
