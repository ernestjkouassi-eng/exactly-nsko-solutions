const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const store = {get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }};

/* ---------- theme: light by default, dark switch ---------- */
const root = document.documentElement, tbtn = $('#theme');
const applyTheme = t => { root.dataset.theme = t; tbtn.setAttribute('aria-label', t === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'); };
applyTheme(store.get('nsko-theme') === 'dark' ? 'dark' : 'light');
tbtn.onclick = () => { const t = root.dataset.theme === 'dark' ? 'light' : 'dark'; applyTheme(t); store.set('nsko-theme', t); };

/* ---------- loader: counter driven by real bytes, boot log ---------- */
let pct = 0, shown = 0, skipped = false, booted = false;
const LOG = ['> linking perception', '> calibrating state estimate', '> loading planner', '> arming control loop', '> verifying trust chain', '> systems online'];
let logN = 0; const ldlog = $('#ldlog');
const assets = ['/vendor/three/three.module.js', '/js/cine.js', '/media/seq/hero/f20.webp', '/fonts/Inter.woff2'];
(async () => { let total = 0, got = 0; const sizes = await Promise.all(assets.map(u => fetch(u, {method:'HEAD'}).then(r => +r.headers.get('content-length') || 60000).catch(() => 60000))); total = sizes.reduce((a, b) => a + b, 0);
  await Promise.all(assets.map(async u => { try { const r = await fetch(u); const rd = r.body.getReader(); for (;;) { const {done, value} = await rd.read(); if (done) break; got += value.length; pct = Math.min(99, got / total * 100); } } catch (e) {} })); pct = 100; })();
const tick = () => { shown += (pct - shown) * .12; if (pct >= 100 && shown > 99.5) shown = 100; $('#ldc').textContent = String(Math.round(shown)).padStart(3, '0');
  const want = Math.min(LOG.length, Math.floor(shown / 100 * LOG.length) + 1); while (logN < want) { const d = document.createElement('div'); d.textContent = LOG[logN++] + (logN < LOG.length ? ' … ok' : ''); ldlog.append(d); }
  if (shown < 100 && !skipped) requestAnimationFrame(tick); else finish(); };
const finish = () => { if (booted) return; booted = true; $('#loader').classList.add('out'); setTimeout(() => $('#loader').remove(), 700); boot(); };
$('#ldskip').onclick = () => { skipped = true; pct = 100; };
requestAnimationFrame(tick); setTimeout(() => { pct = 100; }, 9000);

/* ---------- scenes ---------- */
const NOTE = 'Concept visualisation.';
const CINE = {
  hero: {seq:'/media/seq/hero', first:20, posY:.3, cls:'is-hero', tag:'OPERATOR'},
  lab: {seq:'/media/seq/drone', portraitZoom:1.85, portraitY:.42, cls:'is-drone', tag:'MACHINE LAB', kicker:'MACHINE LAB', intro:'We build the brain.', closing:'We code the mind and the system. Partners build the airframe.', tilt:2.4,
    timeMap:p => p < .1 ? 0 : p < .8 ? (p - .1) / .7 : p < .9 ? 1 : 1 - (p - .9) / .08,
        steps:[
      {tag:'PERCEPTION', file:'perception.ts', h:'It learns to <em>see.</em>', d:'A detection loop reads every frame from the gimbal, finds what matters and scores its own confidence, in milliseconds.',
       code:"// perception.ts · what is in front of me?\nexport async function perceive(frame: Frame) {\n  const tensor = normalise(frame, 640);\n  const boxes = await detector.run(tensor);\n  return boxes\n    .filter(b => b.score > 0.62)\n    .map(b => track.update(b));\n}"},
      {tag:'STATE', file:'fusion.py', h:'It knows where it <em>is.</em>', d:'Satellite fixes and motion sensors disagree. Sensor fusion blends them into one position it can trust.',
       code:"# fusion.py · predict, then correct\ndef step(x, P, imu, gnss, dt):\n    x, P = predict(x, P, imu, dt)\n    if gnss.fresh:\n        K = gain(P, gnss.R)\n        x = x + K @ (gnss.pos - H @ x)\n        P = (I - K @ H) @ P\n    return x, P"},
      {tag:'PLANNING', file:'planner.rs', h:'It chooses the <em>route.</em>', d:'The flight computer searches for the shortest safe path and routes around no-fly zones before it commits.',
       code:"// planner.rs · shortest safe route\nfn plan(map: &Grid, a: Node, b: Node) -> Route {\n  let mut open = BinaryHeap::new();\n  open.push(State::new(a, 0.0));\n  while let Some(s) = open.pop() {\n    if s.node == b { return s.route(); }\n    for n in map.neighbours(s.node) {\n      if map.no_fly(n) { continue; }\n      open.push(State::new(n, s.cost + h(n, b)));\n    }\n  }\n  Route::hold()\n}"},
      {tag:'CONTROL', file:'control.ts', h:'It holds the <em>line.</em>', d:'A control loop turns the plan into motor commands hundreds of times a second, keeping the airframe level in gusts.',
       code:"// control.ts · 400 Hz attitude loop\nfunction tick(target: Attitude, now: Attitude, dt: number) {\n  const err = sub(target, now);\n  integral = clampVec(add(integral, scale(err, dt)), 0.4);\n  const out = add(scale(err, Kp), scale(integral, Ki), scale(rate(err, dt), Kd));\n  motors.mix(out);\n}"},
      {tag:'TRUST', file:'trust.ts', h:'It refuses bad <em>orders.</em>', d:'Every command is signed and checked against the geofence. If the link drops, it comes home on its own.',
       code:"// trust.ts · signed commands, safe defaults\nexport function accept(cmd: Command) {\n  if (!verify(cmd.sig, cmd.body, fleetKey)) return reject('signature');\n  if (cmd.seq <= lastSeq) return reject('replay');\n  if (!fence.contains(cmd.target)) return reject('geofence');\n  return execute(cmd);\n}\nlink.onLost(() => mission.returnHome());"},
    ]},
  secure: {seq:'/media/seq/sweeps', posX:.3, cls:'is-def', tag:'NSKO SECURE', push:.14, kicker:'NSKO SECURE', headline:'Find what should not be there.', closing:'Protecting what we build, and our clients’ businesses.', note:'Sweeps are for spaces you own or control. ' + NOTE,
    items:[{t:'Security Assessment', d:'We test your systems and code and report what an attacker could do, in order of risk.'},
      {t:'TSCM bug sweeps', d:'Offices, boardrooms, vehicles, homes and hotels, swept discreetly, with a written report.'},
      {t:'Secure by design', d:'Signed commands, encrypted links and least-privilege access in everything we build.'},
      {t:'Phones and networks', d:'Rogue access points, odd traffic and compromised devices, found and documented.'}]},
};
const handles = {}, state = {};
const MODS = {
  top:    {load:() => import('/js/cine.js'), make:(m, el) => { const api = {}; const h = m.initHero(el, api, CINE.hero); api.start && api.start(); return h; }},
  lab:    {load:() => import('/js/cine.js'), make:(m, el) => m.init(el, CINE.lab)},
  secure: {load:() => import('/js/cine.js'), make:(m, el) => m.init(el, CINE.secure)},
  field:  {load:() => import('/js/medusa.js'), make:(m, el) => { m.initMedusa($('#medusa')); }, on:'#medusa'},
  desk:   {load:() => import('/js/nova.js'), make:(m, el) => { m.initNova(el, {}); }},
};
const webgl = (() => { try { return !!document.createElement('canvas').getContext('webgl2'); } catch (e) { return false; } })();
async function ensure(id) { if (state[id]) return; const M = MODS[id], el = document.getElementById(id); if (!M || !el) return; if (!webgl && (id === 'field' || id === 'desk')) return; state[id] = 1;
  try { const mod = await M.load(); handles[id] = M.make(mod, el) || null; } catch (e) { console.warn('scene', id, e); } }
// on-screen gating + lazy init
const onIO = new IntersectionObserver(es => es.forEach(e => { const id = e.target.id, M = MODS[id], t = M && M.on ? $(M.on) : e.target; if (e.isIntersecting) ensure(id); t.dataset.on = e.isIntersecting ? '1' : '0'; if (t !== e.target) e.target.dataset.on = t.dataset.on; }), {rootMargin:'40% 0px'});
Object.keys(MODS).forEach(id => { const el = document.getElementById(id); if (el) { el.dataset.on = '0'; if (MODS[id].on) $(MODS[id].on).dataset.on = '0'; onIO.observe(el); } });

/* ---------- reveal on scroll ---------- */
const rvIO = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); rvIO.unobserve(e.target); } }), {rootMargin:'0px 0px -12% 0px'});
$$('.rv').forEach(el => { const sib = [...el.parentElement.children].filter(c => c.classList.contains('rv')); el.style.transitionDelay = (sib.indexOf(el) * .08) + 's'; rvIO.observe(el); });

/* ---------- boot: smooth scroll, pins, choreography ---------- */
let lenis = null;
function goTo(id) { const t = id === 'top' ? 0 : document.getElementById(id); if (t === null) return; lenis ? lenis.scrollTo(t, {duration:1.6, offset:id === 'top' ? 0 : -8}) : (t === 0 ? scrollTo({top:0}) : t.scrollIntoView({behavior:reduced ? 'auto' : 'smooth'})); }
$$('[data-go]').forEach(a => a.addEventListener('click', e => { e.preventDefault(); goTo(a.dataset.go); }));
function boot() {
  if (!window.gsap) return;
  gsap.registerPlugin(ScrollTrigger);
  if (!reduced && window.Lenis) { lenis = new Lenis({lerp:.1}); lenis.on('scroll', ScrollTrigger.update); gsap.ticker.add(t => lenis.raf(t * 1000)); gsap.ticker.lagSmoothing(0); }
  $$('[data-pin]').forEach(sec => { const id = sec.id, len = +sec.dataset.pin;
    ScrollTrigger.create({trigger:sec, start:'top top', end:() => '+=' + Math.round(len * innerHeight), pin:$('.pin', sec), pinSpacing:true, anticipatePin:1, invalidateOnRefresh:true,
      onUpdate:s => { const p = s.progress; if (id === 'desk') sec.__p = p * 1.2; else handles[id] && handles[id].setProgress && handles[id].setProgress(p); if (id === 'top') { const o = 1 - Math.min(1, p * 2.2); $('.hero-copy').style.opacity = o; $('.hero-copy').style.transform = `translateY(${-p * 80}px)`; $('.scrollhint').style.opacity = o; } }}); });
  // statement words light up as you scroll
  const mf = $('#mf'); mf.innerHTML = mf.innerHTML.split('<br>').map(l => l.trim().split(/\s+/).map(w => `<span class="w">${w}</span>`).join(' ')).join('<br>');
  const ws = $$('#mf .w'); ScrollTrigger.create({trigger:mf, start:'top 85%', end:'bottom 40%', scrub:true, onUpdate:s => ws.forEach((w, i) => { w.style.opacity = s.progress * ws.length > i ? 1 : .14; })});
  if (reduced) ws.forEach(w => w.style.opacity = 1);
  ScrollTrigger.batch('.rv', {start:'top 94%', onEnter:els => els.forEach(e => e.classList.add('in'))});
  gsap.fromTo('.marq-in', {xPercent:0}, {xPercent:-50, duration:40, ease:'none', repeat:-1});
  // nav: dark style over dark sections, out of the way over the simulator
  const nav = $('#nav'); const navSync = () => { const el = document.elementsFromPoint(innerWidth / 2, 36).find(n => !nav.contains(n) && n.closest('section')), sec = el && el.closest('section'); nav.classList.toggle('on-dark', !!(sec && sec.classList.contains('dark'))); const f = $('#medusa').getBoundingClientRect(); nav.classList.toggle('away', f.top < 60 && f.bottom > 120); };
  (lenis ? lenis.on('scroll', navSync) : addEventListener('scroll', navSync, {passive:true})); navSync();
  addEventListener('resize', () => ScrollTrigger.refresh());
}

/* ---------- projects: play loops when visible ---------- */
const vIO = new IntersectionObserver(es => es.forEach(e => { const v = $('video', e.target); if (!v || reduced) return; e.isIntersecting ? v.play().catch(() => {}) : v.pause(); }), {threshold:.35});
$$('.proj').forEach(p => vIO.observe(p));

/* ---------- cursor ---------- */
const cur = $('#cur'); if (cur && matchMedia('(hover:hover) and (pointer:fine)').matches) { const lab = cur.firstElementChild; let x = -99, y = -99, sx = x, sy = y;
  addEventListener('pointermove', e => { x = e.clientX; y = e.clientY; const t = e.target, hit = t.closest && (t.closest('#gl') ? 'DRAG' : t.closest('.cine') ? 'HOLD' : t.closest('a,button,.svc,.ind,.proj') ? '' : null); cur.classList.toggle('big', hit !== null); lab.textContent = hit || ''; }, {passive:true});
  const loop = () => { sx += (x - sx) * .22; sy += (y - sy) * .22; cur.style.transform = `translate(${sx}px,${sy}px)`; requestAnimationFrame(loop); }; loop(); }

/* ---------- contact form ---------- */
const cf = $('#cf'), cfm = $('#cfm'); const siteKey = document.querySelector('meta[name="turnstile-sitekey"]')?.content;
if (siteKey) { const s = document.createElement('script'); s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js'; s.async = true; s.onload = () => turnstile.render('#ts', {sitekey:siteKey}); document.head.append(s); }
cf.addEventListener('submit', async e => { e.preventDefault(); cfm.className = 'cf-msg'; const d = Object.fromEntries(new FormData(cf)); d.nda = cf.nda.checked;
  if (!d.name || !/^\S+@\S+\.\S+$/.test(d.email || '') || !d.message) { cfm.textContent = 'Please add your name, a valid email and a short message.'; cfm.classList.add('err'); return; }
  cfm.textContent = 'Sending…'; try { const r = await fetch('/api/contact', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify(d)}); const j = await r.json(); if (!r.ok || !j.ok) throw new Error(j.error || 'failed'); cf.reset(); cfm.textContent = 'Received. Ernest will reply personally within one working day.'; } catch (err) { cfm.textContent = 'That did not send. Please try again in a moment.'; cfm.classList.add('err'); } });
