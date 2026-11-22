/* Photoreal scene: an image sequence scrubbed by scroll or by the cursor, drawn to canvas (no <video>, so it
   works on phones in Low Power Mode and without range requests), under a live interface layer.
   init(root, opts) -> { setProgress(p), dispose() }.  root.dataset.on === '1' gates the loop. */
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const smooth = t => { t = clamp(t); return t * t * (3 - 2 * t); };
const seg = (p, a, b) => smooth((p - a) / (b - a));

export function init(root, o = {}) {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const small = innerWidth < 800;
  const host = root.querySelector('.scene') || root;
  const wrap = document.createElement('div'); wrap.className = 'cine' + (o.cls ? ' ' + o.cls : '');
  wrap.innerHTML = `
    <div class="cine-stage"><div class="cine-plate" style="background-image:url(${o.seq}/f${String(o.first ?? 0).padStart(2, '0')}.webp)"><canvas class="cine-c"></canvas></div></div>
    <canvas class="cine-lens"></canvas><div class="cine-light"></div><div class="cine-vig"></div>
    <div class="cine-hud" aria-hidden="true"><i class="c tl"></i><i class="c tr"></i><i class="c bl"></i><i class="c br"></i><span class="cine-scan"></span>
      <span class="cine-read rl"></span><span class="cine-read rr"></span><span class="cine-hint">HOLD TO SEE THE CODE</span></div>
    ${o.headline ? `<div class="cine-panel"><p class="cine-k">${o.kicker || ''}</p><h2 class="cine-h">${o.headline}</h2>
      <ol class="cine-items">${(o.items || []).map((it, i) => `<li><b>${String(i + 1).padStart(2, '0')}</b><div><strong>${it.t}</strong><span>${it.d}</span></div></li>`).join('')}</ol>
      ${o.closing ? `<p class="cine-close">${o.closing}</p>` : ''}${o.note ? `<p class="cine-note">${o.note}</p>` : ''}</div>` : ''}
    ${o.steps ? `<div class="cine-code"><div class="cine-tab"><i></i><span class="cine-file"></span><em>nsko / autonomy / src</em></div><pre class="cine-pre"></pre></div>
      <div class="cine-step"><p class="cine-k"><span class="cine-n"></span></p><div class="cine-bar">${o.steps.map(() => '<i></i>').join('')}</div><h2 class="cine-h"></h2><p class="cine-d"></p></div>
      <div class="cine-intro"><p class="cine-k">${o.kicker || ''}</p><h2 class="cine-h">${o.intro || ''}</h2></div>
      <div class="cine-outro"><h2 class="cine-h">${o.closing || ''}</h2></div>` : ''}`;
  host.append(wrap);
  const cv = wrap.querySelector('.cine-c'), cx2 = cv.getContext('2d'), plate = wrap.querySelector('.cine-plate'), light = wrap.querySelector('.cine-light');
  const items = [...wrap.querySelectorAll('.cine-items li')], closeEl = wrap.querySelector('.cine-close');
  const rl = wrap.querySelector('.rl'), rr = wrap.querySelector('.rr');
  let p = 0, cur = o.mode === 'pointer' ? .5 : 0, raf = 0, dead = false, px = .5, py = .5, spx = .5, spy = .5, hasPointer = false, lastStep = -2, lastLen = -1;

  // ---- frames: first frame at once, then coarse-to-fine so scrubbing has coverage early ----
  const N = o.frames || 40, imgs = new Array(N), ok = new Uint8Array(N); let ready = false, drawnKey = '';
  const order = []; { const seen = new Set(), add = i => { i = clamp(Math.round(i), 0, N - 1); if (!seen.has(i)) { seen.add(i); order.push(i); } }; add(o.first ?? 0); for (let step = N; step >= 1; step = Math.floor(step / 2)) { for (let i = 0; i < N; i += step) add(i); if (step === 1) break; } add(N - 1); }
  let qi = 0, active = 0;
  const pump = () => { while (!dead && active < (small ? 3 : 5) && qi < order.length) { const i = order[qi++], im = new Image(); active++; im.decoding = 'async'; im.onload = () => { imgs[i] = im; ok[i] = 1; ready = true; drawnKey = ''; active--; pump(); }; im.onerror = () => { active--; pump(); }; im.src = `${o.seq}/f${String(i).padStart(2, '0')}.webp`; } };
  pump();
  const nearest = i => { if (ok[i]) return i; for (let d = 1; d < N; d++) { if (i - d >= 0 && ok[i - d]) return i - d; if (i + d < N && ok[i + d]) return i + d; } return -1; };
  let W = 0, H = 0, dpr = 1;
  const portraitFit = () => o.portraitZoom && W / H < .8;
  const cover = (ctx, im, tw, th) => { const iw = im.naturalWidth, ih = im.naturalHeight; if (portraitFit()) { const s = tw / iw * o.portraitZoom, dw = iw * s, dh = ih * s; ctx.drawImage(im, (tw - dw) / 2, th * (o.portraitY ?? .4) - dh / 2, dw, dh); return; } const s = Math.max(tw / iw, th / ih), dw = iw * s, dh = ih * s; ctx.drawImage(im, (tw - dw) * (o.posX ?? .5), (th - dh) * (o.posY ?? .5), dw, dh); };

  // ---- code vision lens ----
  const lc = wrap.querySelector('.cine-lens'), lx = lc.getContext('2d'), off = document.createElement('canvas'), ox = off.getContext('2d', {willReadFrequently:true});
  const RAMP = ' .:;=+{}<>/01#%@', CELL = small ? 9 : 11, ROW = CELL * 1.45;
  let held = false, lensR = 0, lensOK = true, hintGone = false, curImg = null;
  const size = () => { dpr = Math.min(devicePixelRatio || 1, 2); W = wrap.clientWidth; H = wrap.clientHeight; if (!W || !H) return; cv.width = Math.round(plate.clientWidth * dpr); cv.height = Math.round(plate.clientHeight * dpr); const d = Math.min(dpr, 1.5); lc.width = W * d; lc.height = H * d; lx.setTransform(d, 0, 0, d, 0, 0); off.width = Math.ceil(W / CELL); off.height = Math.ceil(H / ROW); drawnKey = ''; };
  const ro = new ResizeObserver(size); ro.observe(wrap); size();
  const onMove = e => { const r = root.getBoundingClientRect(); px = clamp((e.clientX - r.left) / r.width); py = clamp((e.clientY - r.top) / r.height); hasPointer = e.pointerType !== 'touch'; };
  const down = e => { if (e.target.closest && e.target.closest('a,button,input,textarea,select')) return; onMove(e); held = true; if (!hintGone) { hintGone = true; const h = wrap.querySelector('.cine-hint'); h && h.classList.add('gone'); } };
  const up = () => { held = false; };
  addEventListener('pointermove', onMove, {passive:true}); root.addEventListener('pointerdown', down); addEventListener('pointerup', up); addEventListener('pointercancel', up);
  function drawLens(t) {
    const base = hasPointer ? 92 : 0, target = held ? Math.hypot(W, H) : base;
    lensR += (target - lensR) * (held ? .09 : .16);
    lx.clearRect(0, 0, W, H); if (lensR < 6 || !lensOK || !curImg) return;
    const cx = px * W, cy = py * H, R = lensR;
    try {
      ox.fillStyle = '#03070f'; ox.fillRect(0, 0, off.width, off.height); cover(ox, curImg, off.width, off.height);
      const x0 = Math.max(0, Math.floor((cx - R) / CELL)), x1 = Math.min(off.width - 1, Math.ceil((cx + R) / CELL)), y0 = Math.max(0, Math.floor((cy - R) / ROW)), y1 = Math.min(off.height - 1, Math.ceil((cy + R) / ROW));
      const img = ox.getImageData(x0, y0, x1 - x0 + 1, y1 - y0 + 1).data, w = x1 - x0 + 1;
      lx.save(); lx.beginPath(); lx.arc(cx, cy, R, 0, 6.2832); lx.clip();
      lx.fillStyle = 'rgba(2,6,14,.94)'; lx.fillRect(cx - R, cy - R, R * 2, R * 2);
      lx.font = `500 ${CELL + 2}px "Geist Mono", monospace`; lx.textBaseline = 'top';
      const R2 = R * R, flick = Math.floor(t * 9);
      for (let gy = y0; gy <= y1; gy++) for (let gx = x0; gx <= x1; gx++) {
        const X = gx * CELL, Y = gy * ROW, dx = X - cx, dy = Y - cy; if (dx * dx + dy * dy > R2) continue;
        const k = ((gy - y0) * w + (gx - x0)) * 4, lum = (img[k] * .3 + img[k + 1] * .59 + img[k + 2] * .11) / 255; if (lum < .07) continue;
        const hot = img[k] > img[k + 2] + 40, ch = RAMP[Math.min(RAMP.length - 1, (lum * RAMP.length + ((gx * 7 + gy * 13 + flick) % 5 === 0 ? 1 : 0)) | 0)];
        lx.fillStyle = hot ? `rgba(255,120,90,${Math.min(1, .35 + lum).toFixed(2)})` : `rgba(${190 + lum * 65 | 0},${190 + lum * 65 | 0},${195 + lum * 60 | 0},${Math.min(1, .25 + lum * 1.1).toFixed(2)})`;
        lx.fillText(ch, X, Y);
      }
      lx.restore();
      if (R < Math.max(W, H)) { lx.strokeStyle = 'rgba(232,84,26,.95)'; lx.lineWidth = 1; lx.beginPath(); lx.arc(cx, cy, R, 0, 6.2832); lx.stroke(); lx.fillStyle = 'rgba(232,84,26,.95)'; lx.font = '500 9px "Geist Mono", monospace'; lx.fillText('CODE VIEW', cx - 26, cy + R + 8); }
    } catch (e) { lensOK = false; try { lx.restore(); } catch (_) {} }
  }

  const stepEls = o.steps ? {code:wrap.querySelector('.cine-code'), pre:wrap.querySelector('.cine-pre'), file:wrap.querySelector('.cine-file'), box:wrap.querySelector('.cine-step'), n:wrap.querySelector('.cine-n'), h:wrap.querySelector('.cine-step .cine-h'), d:wrap.querySelector('.cine-d'), bars:[...wrap.querySelectorAll('.cine-bar i')], intro:wrap.querySelector('.cine-intro'), outro:wrap.querySelector('.cine-outro')} : null;
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
  const paint = code => esc(code).replace(/(\/\/[^\n]*|#[^\n]*)/g, '<i>$1</i>').replace(/\b(fn|let|mut|const|for|in|if|return|while|def|async|await|export|function|import|from|loop|match|else)\b/g, '<b>$1</b>').replace(/\b(\d+(\.\d+)?)\b/g, '<u>$1</u>');

  function frame(now) {
    raf = requestAnimationFrame(frame);
    if (dead || root.dataset.on === '0') return;
    if (!W || !H) size();
    const t = now / 1000;
    if (!hasPointer && !held && !reduced) { px = .5 + .34 * Math.sin(t * .45); py = .46 + .08 * Math.sin(t * .37); }
    spx += (px - spx) * .07; spy += (py - spy) * .07;
    let want = o.mode === 'pointer' ? spx : o.timeMap ? o.timeMap(p) : p;
    cur += (clamp(want) - cur) * (reduced ? 1 : .16);
    // picture: nearest loaded frame, cross-faded toward the next for smooth motion
    if (ready && W) { const f = clamp(cur, 0, 1) * (N - 1), i0 = Math.floor(f), a = f - i0, A = nearest(i0), B = i0 + 1 < N && ok[i0 + 1] && ok[i0] ? i0 + 1 : -1, al = B >= 0 ? Math.round(a * 12) / 12 : 0, key = A + ':' + B + ':' + al;
      if (A >= 0 && key !== drawnKey) { drawnKey = key; curImg = imgs[A]; cx2.globalAlpha = 1; cx2.fillStyle = '#03070f'; cx2.fillRect(0, 0, cv.width, cv.height); cover(cx2, imgs[A], cv.width, cv.height); if (B >= 0 && al > 0) { cx2.globalAlpha = al; cover(cx2, imgs[B], cv.width, cv.height); cx2.globalAlpha = 1; } } }
    const z = o.mode === 'pointer' ? 1.03 + p * .5 : 1.03 + (o.push || 0) * p;
    const rx = (spy - .5) * -(o.tilt ?? 3.2), ry = (spx - .5) * (o.tilt ?? 3.2) * 1.4;
    plate.style.transform = `translate3d(${(.5 - spx) * 14}px,${(.5 - spy) * 9}px,0) rotateX(${rx.toFixed(2)}deg) rotateY(${ry.toFixed(2)}deg) scale(${z.toFixed(4)})`;
    light.style.background = `radial-gradient(${small ? 60 : 38}vmax circle at ${(px * 100).toFixed(1)}% ${(py * 100).toFixed(1)}%, rgba(255,255,255,.14), rgba(232,84,26,.05) 40%, transparent 70%)`;
    if (o.mode === 'pointer') wrap.style.opacity = (1 - seg(p, .45, 1) * .85).toFixed(3);
    if (rl) { rl.textContent = `${o.tag || 'NSKO'} · T+${(cur * 5).toFixed(2)}S`; rr.textContent = `X ${(spx * 100 | 0).toString().padStart(2, '0')} · Y ${(spy * 100 | 0).toString().padStart(2, '0')} · ${Math.round(p * 100)}%`; }
    drawLens(t);
    if (items.length) { const n = items.length, act = Math.min(n - 1, Math.floor(clamp((p - .1) / .76) * n)); items.forEach((li, i) => { li.classList.toggle('on', i === act && (p < .9 || small)); li.classList.toggle('past', i < act || p >= .9); li.style.opacity = small ? 1 : seg(p, .02 + i * .02, .08 + i * .02); }); if (closeEl) closeEl.style.opacity = seg(p, .88, .95); }
    if (stepEls) {
      const S = o.steps, n = S.length, a0 = .1, a1 = .84, local = (p - a0) / (a1 - a0) * n, si = p < a0 ? -1 : p >= a1 ? n : Math.min(n - 1, Math.floor(local)), lp = local - si;
      stepEls.intro.style.opacity = 1 - seg(p, .05, .1); stepEls.outro.style.opacity = seg(p, .9, .96);
      const show = si >= 0 && si < n; stepEls.code.style.opacity = show ? 1 : 0; stepEls.box.style.opacity = show ? 1 : 0;
      if (show) { const s = S[si]; if (si !== lastStep) { lastStep = si; lastLen = -1; stepEls.file.textContent = s.file; stepEls.n.textContent = `${String(si + 1).padStart(2, '0')} / ${String(n).padStart(2, '0')}  ${s.tag}`; stepEls.h.innerHTML = s.h; stepEls.d.textContent = s.d; stepEls.bars.forEach((b, i) => b.classList.toggle('on', i <= si)); }
        const len = reduced ? s.code.length : Math.round(clamp(lp / .8) * s.code.length); if (len !== lastLen) { lastLen = len; stepEls.pre.innerHTML = paint(s.code.slice(0, len)) + '<span class="cine-caret"></span>'; } }
      else lastStep = -2;
    }
  }
  raf = requestAnimationFrame(frame);
  return {
    setProgress(x) { p = clamp(x); },
    dispose() { dead = true; cancelAnimationFrame(raf); removeEventListener('pointermove', onMove); removeEventListener('pointerup', up); removeEventListener('pointercancel', up); root.removeEventListener('pointerdown', down); ro.disconnect(); imgs.length = 0; wrap.remove(); },
  };
}

/* hero keeps the older entry point: initHero(root, api) with api.start() */
export function initHero(root, api = {}, o = {}) {
  const h = init(root, {mode:'pointer', tilt:2.2, tag:'OPERATOR', ...o});
  const w = root.querySelector('.cine'); if (w) w.classList.add('pre');
  api.start = () => { const el = root.querySelector('.cine'); el && el.classList.remove('pre'); };
  return h;
}
