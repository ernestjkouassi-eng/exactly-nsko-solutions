// Tiny app core for the Rastamonk concept demos: screens, state, gestures, 3D frame viewer.
(() => {
  const R = window.R = {};
  R.$ = (s, r = document) => r.querySelector(s); R.$$ = (s, r = document) => [...r.querySelectorAll(s)];
  R.esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  // ---------- persisted demo state ----------
  R.store = (key, defaults) => {
    let s; try { s = JSON.parse(localStorage.getItem(key)) || null; } catch (e) { s = null; }
    const st = Object.assign(structuredClone(defaults), s || {});
    st.save = () => { try { const c = { ...st }; delete c.save; delete c.reset; localStorage.setItem(key, JSON.stringify(c)); } catch (e) {} };
    st.reset = () => { try { localStorage.removeItem(key); } catch (e) {} location.reload(); };
    return st;
  };
  // ---------- screens ----------
  R.screens = {}; R.stack = [];
  const app = () => R.$('#app');
  R.go = (name, params = {}, opts = {}) => {
    const fn = R.screens[name]; if (!fn) return;
    if (!opts.replace && R.cur) R.stack.push(R.cur); if (opts.root) R.stack = [];
    R.cur = { name, params };
    const v = document.createElement('div'); v.className = 'view ' + name + (opts.back ? ' back' : ''); v.innerHTML = fn(params);
    const old = R.$$('.view', app()); app().append(v); requestAnimationFrame(() => v.classList.add('in'));
    old.forEach(o => { o.classList.add('out'); setTimeout(() => o.remove(), 380); });
    R.after && R.after(name, v, params); (R.mount[name] || (() => {}))(v, params);
  };
  R.mount = {};
  R.back = () => { const p = R.stack.pop(); if (p) R.go(p.name, p.params, { replace: true, back: true }); };
  document.addEventListener('click', e => {
    const g = e.target.closest('[data-go]'); if (g) { e.preventDefault(); R.vib(); R.go(g.dataset.go, g.dataset.p ? JSON.parse(g.dataset.p) : {}, { root: g.hasAttribute('data-root') }); return; }
    const b = e.target.closest('[data-back]'); if (b) { e.preventDefault(); R.vib(); R.back(); return; }
    const a = e.target.closest('[data-act]'); if (a && R.act[a.dataset.act]) { e.preventDefault(); R.vib(); R.act[a.dataset.act](a, e); }
  });
  R.act = {};
  R.vib = (ms = 8) => { try { navigator.vibrate && navigator.vibrate(ms); } catch (e) {} };
  R.toast = (msg, ms = 2200) => { const t = document.createElement('div'); t.className = 'toast'; t.innerHTML = msg; R.$('#device').append(t); requestAnimationFrame(() => t.classList.add('in')); setTimeout(() => { t.classList.remove('in'); setTimeout(() => t.remove(), 400); }, ms); };
  R.sheet = (html) => { const s = document.createElement('div'); s.className = 'sheet-wrap'; s.innerHTML = `<div class="sheet">${html}</div>`; R.$('#device').append(s); requestAnimationFrame(() => s.classList.add('in'));
    s.addEventListener('click', e => { if (e.target === s || e.target.closest('[data-close]')) { s.classList.remove('in'); setTimeout(() => s.remove(), 350); } }); return s; };
  // ---------- 3D frame viewer: drag to scrub, or play ----------
  R.seq = (el, dir, n, o = {}) => {
    const img = document.createElement('img'); img.className = 'seqimg'; img.draggable = false; el.append(img);
    const srcs = Array.from({ length: n }, (_, i) => `${dir}/f${String(i).padStart(2, '0')}.webp`);
    srcs.forEach(s => { const i = new Image(); i.src = s; });
    let k = o.start || 0, raf = 0, dead = false;
    const set = x => { k = Math.max(0, Math.min(1, x)); img.src = srcs[Math.round(k * (n - 1))]; o.onFrame && o.onFrame(k, Math.round(k * (n - 1))); };
    set(k);
    const play = (to = 1, dur = 1600, done) => { cancelAnimationFrame(raf); const a = k, t0 = performance.now();
      const step = t => { if (dead) return; const p = Math.min(1, (t - t0) / dur), e = p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; set(a + (to - a) * e); if (p < 1) raf = requestAnimationFrame(step); else done && done(); };
      raf = requestAnimationFrame(step); };
    if (o.drag !== false) { let x0 = null, k0 = 0;
      el.addEventListener('pointerdown', e => { x0 = e.clientX; k0 = k; cancelAnimationFrame(raf); el.setPointerCapture(e.pointerId); });
      el.addEventListener('pointermove', e => { if (x0 === null) return; set(k0 + (e.clientX - x0) / (o.dragPx || 220)); });
      const up = () => { x0 = null; }; el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up); }
    if (o.loop) { let dir2 = 1; const swing = () => { if (dead || !el.isConnected) return; play(dir2 > 0 ? 1 : 0, o.loop, () => { dir2 *= -1; setTimeout(swing, 200); }); }; swing(); }
    return { set, play, get: () => k, stop: () => { dead = true; cancelAnimationFrame(raf); } };
  };
  // count-up numbers
  R.count = (el, to, ms = 900, fmt = v => Math.round(v)) => { const t0 = performance.now(), a = 0; const step = t => { const p = Math.min(1, (t - t0) / ms), e = 1 - Math.pow(1 - p, 3); el.textContent = fmt(a + (to - a) * e); if (p < 1 && el.isConnected) requestAnimationFrame(step); }; requestAnimationFrame(step); };
  // confetti
  R.confetti = (host, colors) => { for (let i = 0; i < 46; i++) { const c = document.createElement('i'); c.className = 'conf'; c.style.left = Math.random() * 100 + '%'; c.style.background = colors[i % colors.length]; c.style.animationDelay = Math.random() * .5 + 's'; c.style.setProperty('--r', (Math.random() * 720 - 360) + 'deg'); c.style.setProperty('--x', (Math.random() * 80 - 40) + 'px'); host.append(c); setTimeout(() => c.remove(), 3200); } };
  // hold-to-record (simulated voice note: no audio is captured)
  R.hold = (btn, onStart, onEnd) => { let t0 = 0; btn.addEventListener('pointerdown', e => { t0 = performance.now(); btn.classList.add('rec'); onStart && onStart(); });
    const end = () => { if (!t0) return; const d = (performance.now() - t0) / 1000; t0 = 0; btn.classList.remove('rec'); onEnd && onEnd(d); }; btn.addEventListener('pointerup', end); btn.addEventListener('pointerleave', end); };
  R.clock = () => { const d = new Date(); return d.getHours().toString().padStart(2, '0') + ':' + d.getMinutes().toString().padStart(2, '0'); };
  setInterval(() => R.$$('.sbt').forEach(e => e.textContent = R.clock()), 15000);
})();
