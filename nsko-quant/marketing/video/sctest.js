const { chromium } = require('playwright');
const variants = {
  swgl: ['--use-angle=swiftshader','--enable-unsafe-swiftshader'],
  nogpu: ['--disable-gpu','--enable-unsafe-swiftshader'],
  swgl_nothrottle: ['--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-gpu-vsync','--disable-frame-rate-limit'],
};
(async () => {
  const [v, page, q] = process.argv.slice(2);
  const b = await chromium.launch({ args: variants[v] });
  const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 } });
  const pg = await ctx.newPage();
  await pg.addInitScript(() => { try { localStorage.setItem('nq_onboarded','1') } catch(e){} });
  await pg.goto('http://localhost:4190/?page='+page); await pg.waitForTimeout(4000);
  const cdp = await ctx.newCDPSession(pg); let n=0;
  cdp.on('Page.screencastFrame', f => { n++; cdp.send('Page.screencastFrameAck',{sessionId:f.sessionId}).catch(()=>{}) });
  await cdp.send('Page.startScreencast',{format:'jpeg',quality:+q,maxWidth:1920,maxHeight:1080});
  await pg.waitForTimeout(4000); console.log(v, page, 'q'+q, 'fps', n/4);
  await b.close();
})();
