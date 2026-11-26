// Real-time capture via CDP screencast (high-quality JPEG frames + timestamps) -> CFR 30 fps mp4.
// usage: node rec.js <name> <url-query> <settleSec> <recordSec> [timeScale]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), cp = require('child_process');
(async () => {
  const [name, query, settle, dur, scale] = process.argv.slice(2);
  const dir = path.join('rec', name + '_frames'); fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true });
  const b = await chromium.launch({ args: ['--disable-gpu', '--enable-unsafe-swiftshader', '--disable-renderer-backgrounding', '--disable-background-timer-throttling'] });
  const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const pg = await ctx.newPage();
  const ts = parseFloat(scale || '1');
  const target = process.env.DATE_TARGET ? Date.parse(process.env.DATE_TARGET) : 0;
  if (target) await pg.addInitScript((tg) => {
    const off = tg - Date.now(), OD = Date;
    class D extends OD { constructor(...a) { if (a.length === 0) super(OD.now() + off); else super(...a) } static now() { return OD.now() + off } }
    window.Date = D;
  }, target);
  await pg.addInitScript((ts) => {
    try { localStorage.setItem('nq_onboarded', '1') } catch (e) { }
    window.__startScaled = () => {
      const si = window.setInterval.bind(window), st = window.setTimeout.bind(window);
      window.setInterval = (f, d, ...a) => { if (d !== 50) return si(f, d, ...a); let acc = 0; return si(() => { acc += ts; while (acc >= 1) { f(); acc -= 1 } }, 50) };  // speed up the 50 ms step timer without rendering more often
      
    };
    if (ts !== 1) window.__startScaled();
  }, ts);
  await pg.goto('http://localhost:4190/' + query);
  await pg.waitForTimeout(parseFloat(settle) * 1000);
  const cdp = await ctx.newCDPSession(pg);
  const frames = [];
  cdp.on('Page.screencastFrame', async (f) => {
    const i = frames.length; const fn = path.join(dir, `f${String(i).padStart(5, '0')}.jpg`);
    fs.writeFileSync(fn, Buffer.from(f.data, 'base64')); frames.push({ fn: path.basename(fn), t: f.metadata.timestamp });
    cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }).catch(() => { });
  });
  await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: 1920, maxHeight: 1080, everyNthFrame: 1 });
  await pg.waitForTimeout(parseFloat(dur) * 1000);
  await cdp.send('Page.stopScreencast');
  if (process.env.RECTS) fs.writeFileSync(`rec/${name}_rects.json`, JSON.stringify(await pg.evaluate(() => [...document.querySelectorAll('canvas')].map(c => { const r = c.getBoundingClientRect(); return [r.x, r.y, r.width, r.height] }))));
  await b.close();
  // concat list with real durations
  let s = '';
  for (let i = 0; i < frames.length; i++) {
    const d = i < frames.length - 1 ? frames[i + 1].t - frames[i].t : 1 / 30;
    s += `file '${frames[i].fn}'\nduration ${d.toFixed(4)}\n`;
  }
  s += `file '${frames[frames.length - 1].fn}'\n`;
  fs.writeFileSync(path.join(dir, 'list.txt'), s);
  const span = frames[frames.length - 1].t - frames[0].t;
  console.log(name, 'frames', frames.length, 'span', span.toFixed(2), 'fps', (frames.length / span).toFixed(1));
  cp.execSync(`ffmpeg -y -v error -f concat -safe 0 -i ${dir}/list.txt -vf "scale=1920:1080:flags=lanczos,fps=30,format=yuv420p" -c:v libx264 -preset veryfast -crf 14 rec/${name}.mp4`);
})();
