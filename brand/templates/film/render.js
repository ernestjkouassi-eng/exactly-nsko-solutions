// node render.js probe <film> <h|v> outdir t1 t2...   |   node render.js chunk <film> <h|v> f0 f1 out.mp4 dpr
const { chromium } = require('/opt/node22/lib/node_modules/playwright'); const { spawn } = require('child_process'); const fs = require('fs');
const [mode, film, fmt] = process.argv.slice(2, 5); const V = fmt === 'v'; const W = V ? 1080 : 1920, H = V ? 1920 : 1080;
(async () => {
  const dpr = mode === 'chunk' ? +process.argv[8] : 1;
  const b = await chromium.launch({ args: ['--force-color-profile=srgb', '--font-render-hinting=none', '--disable-lcd-text', '--hide-scrollbars', '--disable-threaded-animation', '--disable-checker-imaging'] });
  const p = await b.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: dpr }); const errs = [];
  p.on('pageerror', e => errs.push(e.message)); p.on('console', m => m.type() === 'error' && errs.push(m.text()));
  await p.goto(`http://localhost:8830/brand/templates/film/${film}.html?v=${V ? 1 : 0}&dpr=${dpr}#render`); await p.waitForFunction(() => window.ready === true, null, { timeout: 120000 }); await p.waitForTimeout(500);
  if (mode === 'probe') { const out = process.argv[5]; fs.mkdirSync(out, { recursive: true });
    for (const t of process.argv.slice(6).map(Number)) { await p.evaluate(t => window.seek(t), t); await p.screenshot({ path: `${out}/t${t.toFixed(2).padStart(6, '0')}.png` }); } }
  else { const f0 = +process.argv[5], f1 = +process.argv[6], out = process.argv[7];
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', '24', '-c:v', 'mjpeg', '-i', '-', '-vf', 'scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p', '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const t0 = Date.now(); for (let f = f0; f < f1; f++) { await p.evaluate(t => window.seek(t), f / 24); const buf = await p.screenshot({ type: 'jpeg', quality: 95 }); if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r)); }
    ff.stdin.end(); await new Promise(r => ff.on('close', r)); console.log(out, f1 - f0, 'frames', ((Date.now() - t0) / (f1 - f0) / 1000).toFixed(2), 's/frame'); }
  console.log('errors:', errs.length ? [...new Set(errs)].slice(0, 6) : 0); await b.close();
})();
