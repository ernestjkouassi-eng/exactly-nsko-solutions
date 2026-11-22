const { chromium } = require('/opt/node22/lib/node_modules/playwright'); const fs = require('fs');
(async () => { const D = __dirname + '/'; const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1350 } });
  for (const f of fs.readdirSync(D).filter(f => /^_s.*\.html$/.test(f)).sort()) { await p.goto('file://' + D + f); await p.waitForTimeout(350);
    await p.screenshot({ path: D + 'series2/post-' + f.slice(2, -5) + '.jpg', type: 'jpeg', quality: 92 }); }
  await b.close(); })();
