// node render.js anim <card> <w> <h> <seconds> <out.mp4>   (deterministic: render(t) per frame at 30 fps)
// node render.js png  <card> <w> <h> <out.png> [extra query]  (transparent overlay)
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path'), cp = require('child_process');
(async () => {
  const [mode, card, w, h, a5, a6] = process.argv.slice(2);
  const b = await chromium.launch({ args: ['--disable-gpu'] });
  const pg = await (await b.newContext({ viewport: { width: +w, height: +h } })).newPage();
  const url = 'file://' + path.resolve(__dirname, 'cards.html') + `?card=${card}` + (mode === 'png' && a6 ? '&' + a6 : '') + (process.env.Q ? '&' + process.env.Q : '');
  await pg.goto(url); await pg.evaluate(() => document.fonts.ready); await pg.waitForTimeout(300);
  if (mode === 'png') { await pg.evaluate(() => window.render(0)); await pg.screenshot({ path: a5, omitBackground: true }); await b.close(); return }
  const N = Math.round(+a5 * 30), dir = `/tmp/claude-0/-home-user/d33af76a-f98e-5d59-8081-b5bd0277881c/scratchpad/fr_${card}_${w}x${h}`;
  fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true });
  for (let i = 0; i < N; i++) { await pg.evaluate(t => window.render(t), i / 30); await pg.screenshot({ path: `${dir}/f${String(i).padStart(5, '0')}.png` }) }
  await b.close();
  cp.execSync(`ffmpeg -y -v error -framerate 30 -i ${dir}/f%05d.png -c:v libx264 -preset veryfast -crf 14 -pix_fmt yuv420p ${a6}`);
  console.log('ok', a6, N);
})();
