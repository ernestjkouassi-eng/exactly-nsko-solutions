const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const b = await chromium.launch({ args: ['--disable-gpu'] });
  const url = f => 'file://' + path.resolve(__dirname, 'poster.html') + '?fmt=' + f;
  const jobs = [['ig', 1080, 1350, 1, 'out/nsko-quant-poster-instagram-1080x1350.png'], ['story', 1080, 1920, 1, 'out/nsko-quant-poster-story-1080x1920.png'],
                ['a3', 1123, 1587, 3508 / 1123, 'out/nsko-quant-poster-A3-300dpi.png']];
  for (const [f, w, h, dpr, out] of jobs) {
    const pg = await (await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: dpr })).newPage();
    await pg.goto(url(f)); await pg.evaluate(() => document.fonts.ready); await pg.waitForLoadState('networkidle'); await pg.waitForTimeout(500);
    await pg.screenshot({ path: out, clip: { x: 0, y: 0, width: w, height: h } }); console.log(out);

  }
  await b.close();
})();
