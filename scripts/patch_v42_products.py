#!/usr/bin/env python3
"""One-off patch: scroll fix for iOS, guard for the old Lab cards, product 3D sections and the hero 3D slider."""
import pathlib
p = pathlib.Path(__file__).resolve().parent.parent / 'public/js/v42.js'
s = p.read_text()
s = s.replace("const go = i => scenes[Math.max(0, Math.min(scenes.length - 1, i))]?.scrollIntoView({behavior: RM ? 'auto' : 'smooth'});",
"""// Scroll to a section. iOS Safari fights smooth scrolling while scroll-snap is on, so snap is paused during the move.
let goT = 0;
const go = i => { const el = scenes[Math.max(0, Math.min(scenes.length - 1, i))]; if (!el) return;
  const root = document.documentElement; root.style.scrollSnapType = 'none'; clearTimeout(goT);
  window.scrollTo({top: el.getBoundingClientRect().top + scrollY, behavior: RM ? 'auto' : 'smooth'});
  goT = setTimeout(() => { root.style.scrollSnapType = ''; }, 1100); };""")
s = s.replace("$('#labcards').innerHTML =", "if ($('#labcards')) $('#labcards').innerHTML =")
s += r"""
/* ---------- products: live 3D, explode, 360, zoom to part ---------- */
const P3D = {robot: 'NSKO R1 robot arm', quad: 'NSKO Sentinel inspection robot', surgical: 'NSKO Surgical Assist concept', arch: 'NSKO Tower scale model', watch: 'NSKO Tourbillon watch'};
const live = new Map(); let lib = null;
const lib3d = () => lib || (lib = import('/js/product3d.js'));
$$('.p3d').forEach(h => { h.style.backgroundImage = `url(/media/v42/poster/${h.dataset.poster}-tall.webp)`; });
function mount3d(h) {
  if (live.has(h)) return; live.set(h, null);
  const sec = h.closest('.scene'), btn = x => sec.querySelector(`[data-x="${x}"]`);
  lib3d().then(m => { if (!live.has(h)) return;
    const v = m.mount(h, {src: `/media/v42/glb3/${h.dataset.glb}.glb`, label: P3D[h.dataset.glb], intro: !h.dataset.hero, hero: !!h.dataset.hero,
      onExplode: on => { const b = btn('explode'); if (b) { b.setAttribute('aria-pressed', on); b.textContent = on ? 'Assemble' : 'Explode'; } },
      onSpin: on => btn('spin')?.setAttribute('aria-pressed', on)});
    if (!v) { live.delete(h); return; } live.set(h, v); }).catch(() => live.delete(h));
}
function unmount3d(h) { const v = live.get(h); v?.dispose?.(); live.delete(h); }
const pio = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) mount3d(e.target); else unmount3d(e.target); }), {threshold: .25});
$$('.prod .p3d').forEach(h => pio.observe(h));
$$('.prod').forEach(sec => {
  const h = $('.p3d', sec), v = () => live.get(h);
  sec.querySelector('[data-x="explode"]').addEventListener('click', () => { const x = v(); if (x) x.explode(!x.exploded); });
  sec.querySelector('[data-x="spin"]').addEventListener('click', e => { const b = e.currentTarget, on = b.getAttribute('aria-pressed') !== 'true'; b.setAttribute('aria-pressed', on); v()?.spin(on); });
  sec.querySelector('[data-x="reset"]').addEventListener('click', () => { v()?.reset(); $$('[data-part]', sec).forEach(o => o.setAttribute('aria-pressed', false)); });
  $$('[data-part]', sec).forEach(b => b.addEventListener('click', () => { const x = v(); if (!x) return; if (!x.exploded) x.explode(true);
    $$('[data-part]', sec).forEach(o => o.setAttribute('aria-pressed', o === b)); setTimeout(() => x.focus(b.dataset.at.split(',').map(Number)), 450); }));
});
/* ---------- hero 3D slider: the N, then the robot arm ---------- */
{ const slides = $$('.slide'), caps = ['The NSKO mark', 'NSKO R1 robot arm · drag to turn']; let cur = 0, idle = 0;
  const show = i => { cur = (i + slides.length) % slides.length; slides.forEach((s, j) => { s.classList.toggle('on', j === cur); s.setAttribute('aria-hidden', j !== cur); });
    $('#slcap').textContent = caps[cur]; const h = $('.hero3d'); if (cur === 1) mount3d(h); else unmount3d(h); };
  $$('[data-sl]').forEach(b => b.addEventListener('click', () => { clearInterval(idle); show(cur + +b.dataset.sl); }));
  let sx = null; $('#slides').addEventListener('touchstart', e => { sx = e.touches[0].clientX; }, {passive: true});
  $('#slides').addEventListener('touchend', e => { if (sx == null) return; const dx = e.changedTouches[0].clientX - sx; if (Math.abs(dx) > 60 && cur === 0) { clearInterval(idle); show(cur + (dx < 0 ? 1 : -1)); } sx = null; }, {passive: true});
  if (!RM) { idle = setInterval(() => { if (scrollY < innerHeight * .5 && !document.hidden && cur === 0) show(1); }, 8000); $('#slides').addEventListener('pointerdown', () => clearInterval(idle), {once: true}); }
}
"""
p.write_text(s)
print('patched')
