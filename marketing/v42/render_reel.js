// node render_reel.js robot out.mp4  -> 12 s, 30 fps, 1080x1920 reel captured from the live 3D page with a fake clock (deterministic).
const {chromium} = require('/opt/node22/lib/node_modules/playwright'); const {spawn} = require('child_process');
const [p, out] = process.argv.slice(2), FPS = 30, SECS = +(process.env.SECS || 12.5);
(async () => {
  const b = await chromium.launch({args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']});
  const pg = await b.newPage({viewport: {width: 1080, height: 1920}, deviceScaleFactor: 1});
  await pg.goto(`http://localhost:8642/reel/?p=${p}`);
  await pg.waitForFunction(() => window.ready === true, null, {timeout: 120000});
  const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-', '-vf', 'format=yuv420p', '-c:v', 'libx264', '-crf', '19', '-preset', 'medium', '-movflags', '+faststart', out], {stdio: ['pipe', 'inherit', 'inherit']});
  const t0 = Date.now();
  for (let f = 0; f < FPS * SECS; f++) {
    await pg.evaluate(dt => window.frame(dt), 1 / FPS);
    const buf = await pg.screenshot({type: 'jpeg', quality: 92, timeout: 0});
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r)); console.log(out, ((Date.now() - t0) / 1000).toFixed(0) + 's'); await b.close();
})();
