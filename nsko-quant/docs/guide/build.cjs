// Build the NSKO QUANT guides: HTML/CSS -> PDF (Playwright Chromium, A4, backgrounds on).
// Run from anywhere:  NODE_PATH=$(npm root -g) node docs/guide/build.cjs
const path = require('path');
const fs = require('fs');
const { chromium } = require('playwright');

const here = __dirname;
const out = path.join(here, '..', 'pdf');
const docs = [
  ['user-guide.html', 'NSKO-QUANT-User-Guide.pdf'],
  ['how-it-works.html', 'How-NSKO-QUANT-Works.pdf'],
];

(async () => {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (const [src, dst] of docs) {
    await page.goto('file://' + path.join(here, src), { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    await page.pdf({ path: path.join(out, dst), format: 'A4', printBackground: true, preferCSSPageSize: true });
    console.log('wrote', path.join(out, dst));
  }
  await browser.close();
})();
