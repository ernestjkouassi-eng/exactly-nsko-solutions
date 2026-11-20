/* Creative layer: neural-code field behind the manifesto, and the cursor. */
export function initFx() {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  // ---- cursor ----
  const cur = document.getElementById('cur'), lab = cur && cur.firstElementChild;
  if (cur && matchMedia('(hover:hover) and (pointer:fine)').matches) {
    let x = innerWidth / 2, y = innerHeight / 2, sx = x, sy = y;
    addEventListener('pointermove', e => { x = e.clientX; y = e.clientY; const t = e.target, hit = t.closest && (t.closest('#gl') ? 'DRAG' : t.closest('.tile') ? 'OPEN' : t.closest('a,button,.cap,[role=slider]') ? '' : null); cur.classList.toggle('big', hit !== null); lab.textContent = hit || ''; }, {passive:true});
    const loop = () => { sx += (x - sx) * .22; sy += (y - sy) * .22; cur.style.transform = `translate(${sx}px,${sy}px)`; requestAnimationFrame(loop); }; loop();
  }
  // ---- sound design (off until the visitor switches it on) ----
  const btn = document.getElementById('snd'); let AC = null, master = null, padF = null, on = false;
  const mk = () => { AC = new (window.AudioContext || window.webkitAudioContext)(); master = AC.createGain(); master.gain.value = 0; master.connect(AC.destination);
    padF = AC.createBiquadFilter(); padF.type = 'lowpass'; padF.frequency.value = 420; padF.Q.value = 6; padF.connect(master);
    [[55, 'sawtooth', .10], [55.4, 'sawtooth', .10], [82.4, 'triangle', .08], [110, 'sine', .10], [164.8, 'sine', .03]].forEach(([fr, ty, g]) => { const o = AC.createOscillator(), gn = AC.createGain(); o.type = ty; o.frequency.value = fr; gn.gain.value = g; o.connect(gn); gn.connect(padF); o.start(); });
    const lfo = AC.createOscillator(), lg = AC.createGain(); lfo.frequency.value = .08; lg.gain.value = 160; lfo.connect(lg); lg.connect(padF.frequency); lfo.start(); };
  const noise = (dur, f0, f1, vol, type = 'bandpass') => { if (!on) return; const n = AC.sampleRate * dur, b = AC.createBuffer(1, n, AC.sampleRate), d = b.getChannelData(0); for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1; const s = AC.createBufferSource(); s.buffer = b; const fl = AC.createBiquadFilter(); fl.type = type; fl.Q.value = 1.2; fl.frequency.setValueAtTime(f0, AC.currentTime); fl.frequency.exponentialRampToValueAtTime(f1, AC.currentTime + dur); const g = AC.createGain(); g.gain.setValueAtTime(0, AC.currentTime); g.gain.linearRampToValueAtTime(vol, AC.currentTime + dur * .35); g.gain.exponentialRampToValueAtTime(.0001, AC.currentTime + dur); s.connect(fl); fl.connect(g); g.connect(master); s.start(); };
  const tone = (f, dur, vol, type = 'sine', slide = 1) => { if (!on) return; const o = AC.createOscillator(), g = AC.createGain(); o.type = type; o.frequency.setValueAtTime(f, AC.currentTime); o.frequency.exponentialRampToValueAtTime(f * slide, AC.currentTime + dur); g.gain.setValueAtTime(vol, AC.currentTime); g.gain.exponentialRampToValueAtTime(.0001, AC.currentTime + dur); o.connect(g); g.connect(master); o.start(); o.stop(AC.currentTime + dur); };
  if (btn) { btn.onclick = () => { if (!AC) mk(); on = !on; AC.resume(); master.gain.cancelScheduledValues(AC.currentTime); master.gain.linearRampToValueAtTime(on ? .5 : 0, AC.currentTime + .6); btn.textContent = on ? 'SOUND ON' : 'SOUND OFF'; btn.classList.toggle('on', on); if (on) { tone(880, .12, .12); tone(1320, .2, .08); } };
    addEventListener('nsko:scene', () => { noise(.9, 300, 3200, .22); tone(48, 1.1, .5, 'sine', .6); });
    addEventListener('nsko:vel', e => { if (on && padF) padF.frequency.setTargetAtTime(420 + Math.min(2600, Math.abs(e.detail) * 220), AC.currentTime, .15); });
    document.addEventListener('pointerover', e => { if (on && e.target.closest && e.target.closest('a,button,.cap,.tile')) tone(1900, .04, .03, 'square'); });
    document.addEventListener('pointerdown', e => { if (!on) return; if (e.target.closest && e.target.closest('.cine')) { noise(.5, 2400, 500, .14, 'highpass'); tone(220, .5, .1, 'sawtooth', 2); } else tone(660, .07, .06); }); }
  // ---- chapter card: a brief full-screen title as each scene takes over ----
  const flash = document.getElementById('flash');
  if (flash && !reduced) { const fn = flash.querySelector('b'), fl = flash.querySelector('span'); const G = 'ABCDEFGHKLMNOPRSTUVXYZ0123456789/<>'; let fid = 0;
    addEventListener('nsko:scene', e => { const id = ++fid, txt = e.detail.l.toUpperCase(); fn.textContent = String(e.detail.n).padStart(2, '0'); flash.classList.remove('go'); void flash.offsetWidth; flash.classList.add('go'); const t0 = performance.now();
      const tick = now => { if (id !== fid) return; const k = Math.min(1, (now - t0) / 520); fl.textContent = [...txt].map((c, i) => c === ' ' || i / txt.length < k ? c : G[(Math.random() * G.length) | 0]).join(''); if (k < 1) requestAnimationFrame(tick); }; requestAnimationFrame(tick); }); }
  // ---- manifesto words push away from the cursor and spring back ----
  const words = [...document.querySelectorAll('#mf .w')].map(el => ({el, x:0, y:0, vx:0, vy:0})); let wx = -999, wy = -999;
  const mfSec = document.getElementById('manifesto');
  if (words.length && !reduced) { addEventListener('pointermove', e => { wx = e.clientX; wy = e.clientY; }, {passive:true});
    const wl = () => { requestAnimationFrame(wl); if (!mfSec || mfSec.dataset.on !== '1') return; for (const w of words) { const r = w.el.getBoundingClientRect(), cx = r.left + r.width / 2 - w.x, cy = r.top + r.height / 2 - w.y, dx = cx - wx, dy = cy - wy, d = Math.hypot(dx, dy), f = d < 200 ? (1 - d / 200) * 46 : 0; const tx = d ? dx / d * f : 0, ty = d ? dy / d * f : 0; w.vx = (w.vx + (tx - w.x) * .12) * .78; w.vy = (w.vy + (ty - w.y) * .12) * .78; w.x += w.vx; w.y += w.vy; w.el.style.transform = `translate(${w.x.toFixed(1)}px,${w.y.toFixed(1)}px) rotate(${(w.x * .12).toFixed(2)}deg)`; } }; wl(); }
  // ---- manifesto: a field of nodes that links up into a "mind" and streams code glyphs ----
  const sec = document.getElementById('manifesto'), c = document.getElementById('mf-cv'); if (!sec || !c) return;
  const g = c.getContext('2d'); let W = 0, H = 0, nodes = [], mx = -9999, my = -9999;
  const rnd = (() => { let s = 5; return () => (s = (s * 16807) % 2147483647) / 2147483647; })();
  const GLY = '01{}<>=/+*;:()[]fnletifmind';
  const size = () => { const d = Math.min(devicePixelRatio, 1.5); W = c.clientWidth; H = c.clientHeight; c.width = W * d; c.height = H * d; g.setTransform(d, 0, 0, d, 0, 0); const n = Math.round(Math.min(110, W * H / 13000)); nodes = Array.from({length:n}, () => ({x:rnd() * W, y:rnd() * H, vx:(rnd() - .5) * .25, vy:(rnd() - .5) * .25, ph:rnd() * 6.28, ch:GLY[(rnd() * GLY.length) | 0]})); };
  new ResizeObserver(size).observe(c); size();
  sec.addEventListener('pointermove', e => { const r = c.getBoundingClientRect(); mx = e.clientX - r.left; my = e.clientY - r.top; });
  const draw = t => {
    g.clearRect(0, 0, W, H); const R = Math.min(190, W * .22);
    for (const n of nodes) { if (!reduced) { n.x += n.vx; n.y += n.vy; const dx = n.x - mx, dy = n.y - my, d2 = dx * dx + dy * dy; if (d2 < 26000) { n.x += dx / Math.sqrt(d2 + 1) * .9; n.y += dy / Math.sqrt(d2 + 1) * .9; } if (n.x < 0 || n.x > W) n.vx *= -1; if (n.y < 0 || n.y > H) n.vy *= -1; } }
    g.lineWidth = 1;
    for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) { const a = nodes[i], b = nodes[j], dx = a.x - b.x, dy = a.y - b.y, d = Math.sqrt(dx * dx + dy * dy); if (d < R) { const k = 1 - d / R, pulse = .5 + .5 * Math.sin(t * .002 + a.ph + b.ph); g.strokeStyle = `rgba(127,212,255,${(k * .28 * (.4 + pulse * .6)).toFixed(3)})`; g.beginPath(); g.moveTo(a.x, a.y); g.lineTo(b.x, b.y); g.stroke();
      if (k > .55 && !reduced) { const f = (t * .0006 + a.ph) % 1; g.fillStyle = 'rgba(255,90,60,.8)'; g.fillRect(a.x + (b.x - a.x) * f - 1, a.y + (b.y - a.y) * f - 1, 2, 2); } } }
    g.font = '11px "Geist Mono", monospace';
    for (const n of nodes) { const tw = .5 + .5 * Math.sin(t * .003 + n.ph); g.fillStyle = `rgba(207,224,245,${(.25 + tw * .5).toFixed(3)})`; g.fillText(n.ch, n.x + 5, n.y - 5); g.fillStyle = `rgba(127,212,255,${(.5 + tw * .5).toFixed(3)})`; g.beginPath(); g.arc(n.x, n.y, 1.6 + tw, 0, 6.3); g.fill(); if (!reduced && Math.random() < .004) n.ch = GLY[(Math.random() * GLY.length) | 0]; }
  };
  const loop = t => { requestAnimationFrame(loop); if (sec.dataset.on === '1') draw(t); };
  draw(0); requestAnimationFrame(loop);
}
