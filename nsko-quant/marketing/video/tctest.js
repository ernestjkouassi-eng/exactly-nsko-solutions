const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ args: ['--disable-gpu','--enable-unsafe-swiftshader'] });
  for (const ts of [1, 2.4]) {
  const pg = await (await b.newContext({ viewport: { width: 1920, height: 1080 } })).newPage();
  await pg.addInitScript((ts) => { const si = window.setInterval.bind(window), st = window.setTimeout.bind(window);
      if (ts!==1) { window.setInterval = (f, d, ...a) => si(f, d === 50 ? 50 / ts : d, ...a);  } }, ts);
  await pg.goto('http://localhost:4190/?page=tradecard'); await pg.waitForTimeout(13000/ts);
  const info = await pg.evaluate(() => [...document.querySelectorAll('canvas')].map(c => [c.width, c.height, c.getBoundingClientRect().height]));
  console.log(ts, JSON.stringify(info));
  await pg.screenshot({ path: `rec/tct_${ts}.png`, clip:{x:1330,y:190,width:600,height:450} }); }
  await b.close();
})();
