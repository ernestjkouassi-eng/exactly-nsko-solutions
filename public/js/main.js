const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const store = {get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }};

/* theme: dark by default (Command Deck), light switch */
const root = document.documentElement, tbtn = $('#theme');
const applyTheme = t => { root.dataset.theme = t; tbtn.setAttribute('aria-label', t === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'); };
applyTheme(store.get('nsko-theme') === 'light' ? 'light' : 'dark');
tbtn.onclick = () => { const t = root.dataset.theme === 'dark' ? 'light' : 'dark'; applyTheme(t); store.set('nsko-theme', t); };

/* loader */
let pct = 0, shown = 0, skipped = false, booted = false, logN = 0;
const LOG = ['> linking perception', '> calibrating state estimate', '> loading planner', '> arming control loop', '> verifying trust chain', '> systems online'], ldlog = $('#ldlog');
const assets = ['/js/cine.js', '/media/seq/hero/f20.webp', '/media/seq/drone/f00.webp', '/fonts/Inter.woff2'];
(async () => { const sizes = await Promise.all(assets.map(u => fetch(u, {method:'HEAD'}).then(r => +r.headers.get('content-length') || 60000).catch(() => 60000))); const total = sizes.reduce((a, b) => a + b, 0); let got = 0;
  await Promise.all(assets.map(async u => { try { const r = await fetch(u); const rd = r.body.getReader(); for (;;) { const {done, value} = await rd.read(); if (done) break; got += value.length; pct = Math.min(99, got / total * 100); } } catch (e) {} })); pct = 100; })();
const tick = () => { shown += (pct - shown) * .14; if (pct >= 100 && shown > 99.5) shown = 100; $('#ldc').textContent = String(Math.round(shown)).padStart(3, '0');
  const want = Math.min(LOG.length, Math.floor(shown / 100 * LOG.length) + 1); while (logN < want) { const d = document.createElement('div'); d.textContent = LOG[logN++] + (logN < LOG.length ? ' … ok' : ''); ldlog.append(d); }
  if (shown < 100 && !skipped) requestAnimationFrame(tick); else finish(); };
const finish = () => { if (booted) return; booted = true; $('#loader').classList.add('out'); setTimeout(() => $('#loader').remove(), 700); boot(); };
$('#ldskip').onclick = () => { skipped = true; pct = 100; }; requestAnimationFrame(tick); setTimeout(() => { pct = 100; }, 7000);

/* scenes */
const CINE = {
  hero: {seq:'/media/seq/hero', first:20, posY:.28, cls:'is-hero', tag:'OPERATOR', tilt:1.6},
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
};
CINE.lab.timeMap = p => p < .1 ? 0 : p < .84 ? (p - .1) / .74 : 1;
const webgl = (() => { try { return !!document.createElement('canvas').getContext('webgl2'); } catch (e) { return false; } })();
let cine = null; const getCine = () => cine || (cine = import('/js/cine.js'));
const hero = $('#hero'); hero.dataset.on = '0';
const io = (el, fn, m = '25% 0px') => new IntersectionObserver(es => es.forEach(e => fn(e.isIntersecting)), {rootMargin:m}).observe(el);
let heroH = null; io(hero, v => { hero.dataset.on = v ? '1' : '0'; if (v && !heroH) getCine().then(m => { const api = {}; heroH = m.initHero(hero, api, CINE.hero); api.start && api.start(); }); });

/* Machine Lab tabs */
const tabs = $$('.tabs [role=tab]'), panels = {drone:$('#tp-drone'), field:$('#tp-field'), desk:$('#tp-desk')};
let labVisible = false, active = 'drone', droneH = null, medusaOn = false, novaOn = false;
const onTarget = k => k === 'field' ? $('#medusa') : panels[k];
const syncOn = () => Object.keys(panels).forEach(k => { onTarget(k).dataset.on = (labVisible && active === k) ? '1' : '0'; });
async function initTab(k) {
  if (k === 'drone' && !droneH) { const m = await getCine(); droneH = m.init(panels.drone, CINE.lab); droneH.setProgress(dp.p); }
  if (k === 'field' && !medusaOn && webgl) { medusaOn = true; (await import('/js/medusa.js')).initMedusa($('#medusa')); }
  if (k === 'desk' && !novaOn && webgl) { novaOn = true; panels.desk.__p = .75; (await import('/js/nova.js')).initNova(panels.desk, {}); }
  syncOn();
}
function selectTab(k) { active = k; tabs.forEach(t => { const on = t.id === 't-' + k; t.setAttribute('aria-selected', on); t.tabIndex = on ? 0 : -1; }); Object.entries(panels).forEach(([n, el]) => el.hidden = n !== k); initTab(k); syncOn(); }
tabs.forEach((t, i) => { t.onclick = () => selectTab(t.id.slice(2)); t.onkeydown = e => { const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0; if (d) { const n = tabs[(i + d + tabs.length) % tabs.length]; n.focus(); n.click(); } }; });
Object.keys(panels).forEach(k => onTarget(k).dataset.on = '0');
io($('#lab'), v => { labVisible = v; if (v) initTab(active); syncOn(); }, '10% 0px');
// drone steps: click a step, or let it play
const dp = {p:0}, stepsEl = $('#steps'), S = CINE.lab.steps, a0 = .1, a1 = .84, w = (a1 - a0) / S.length;
let userTouched = false, playT = null, cur = -1;
const stepBtns = S.map((s, i) => { const b = document.createElement('button'); b.textContent = String(i + 1).padStart(2, '0') + ' ' + s.tag; b.onclick = () => { userTouched = true; goStep(i); }; stepsEl.append(b); return b; });
const rb = document.createElement('button'); rb.textContent = '↺ Reassemble'; rb.onclick = () => { userTouched = true; goStep(S.length); }; stepsEl.append(rb);
function goStep(i) { cur = i; stepBtns.forEach((b, j) => b.classList.toggle('on', j === i)); const from = i >= S.length ? .9 : a0 + i * w + .002, to = i >= S.length ? 1 : a0 + (i + .97) * w;
  if (!window.gsap || reduced) { dp.p = to; droneH && droneH.setProgress(to); return; }
  gsap.killTweensOf(dp); dp.p = from; gsap.to(dp, {p:to, duration:i >= S.length ? 1.6 : 3.2, ease:'power1.inOut', onUpdate:() => droneH && droneH.setProgress(dp.p)}); }
setInterval(() => { if (!labVisible || active !== 'drone' || userTouched || !droneH) return; goStep((cur + 1) % (S.length + 1)); }, 6000);

/* panels (service detail) */
$$('[data-open]').forEach(b => b.addEventListener('click', () => { const d = document.getElementById(b.dataset.open); d.showModal(); }));
const film = $('#d-film'); if (film) { const fv = film.querySelector('video'); film.querySelector('.x').onclick = () => film.close(); film.addEventListener('click', e => { if (e.target === film) film.close(); }); film.addEventListener('close', () => fv.pause()); film.addEventListener('toggle', () => { if (film.open) fv.play().catch(() => {}); }); }
$$('dialog.panel').forEach(d => { d.querySelector('.x').onclick = () => d.close(); d.addEventListener('click', e => { if (e.target === d) d.close(); }); });
$$('[data-close]').forEach(a => a.addEventListener('click', () => a.closest('dialog').close()));

/* menu drawer */
const burger = $('#burger'), drawer = $('#drawer');
const setDrawer = o => { drawer.hidden = !o; burger.setAttribute('aria-expanded', o); burger.setAttribute('aria-label', o ? 'Close menu' : 'Open menu'); document.body.style.overflow = o ? 'hidden' : ''; o ? lenis && lenis.stop() : lenis && lenis.start(); };
burger.onclick = () => setDrawer(drawer.hidden); addEventListener('keydown', e => { if (e.key === 'Escape' && !drawer.hidden) setDrawer(false); });

/* navigation */
let lenis = null;
function goTo(id) { setDrawer(false); const t = id === 'top' ? 0 : document.getElementById(id); if (t === null) return; lenis ? lenis.scrollTo(t, {duration:1.4, offset:id === 'top' ? 0 : -70}) : (t === 0 ? scrollTo({top:0, behavior:'smooth'}) : t.scrollIntoView({behavior:reduced ? 'auto' : 'smooth'})); }
$$('[data-go]').forEach(a => a.addEventListener('click', e => { e.preventDefault(); goTo(a.dataset.go); const ind = a.dataset.ind; if (ind) { const c = $('#ind-' + ind); setTimeout(() => { c.classList.add('hl'); c.focus({preventScroll:true}); setTimeout(() => c.classList.remove('hl'), 2200); }, 900); } }));
const totop = $('#totop'); totop.onclick = () => goTo('top');
const navLinks = $$('.nav nav a');
const onScroll = () => { const y = scrollY; totop.classList.toggle('show', y > innerHeight * .6);
  const ids = ['top', 'lab', 'industries', 'projects', 'contact']; let curId = 'top'; ids.forEach(id => { const el = document.getElementById(id); if (el && el.getBoundingClientRect().top < innerHeight * .4) curId = id; });
  navLinks.forEach(a => a.classList.toggle('on', a.dataset.go === curId && curId !== 'top')); };
addEventListener('scroll', onScroll, {passive:true});

/* reveals */
$$('.ind,.proj,.how li,.sh').forEach(el => el.classList.add('rv'));
const rio = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); rio.unobserve(e.target); } }), {rootMargin:'0px 0px -8% 0px'});
$$('.rv').forEach(el => { const sib = [...el.parentElement.children]; el.style.transitionDelay = (sib.indexOf(el) % 6) * .07 + 's'; rio.observe(el); });

/* project loop */
const pv = $('.proj video'); if (pv) io(pv, v => { if (reduced) return; v ? pv.play().catch(() => {}) : pv.pause(); }, '0px');

function boot() {
  if (!reduced && window.Lenis) { lenis = new Lenis({lerp:.11}); const raf = t => { lenis.raf(t); requestAnimationFrame(raf); }; requestAnimationFrame(raf); lenis.on('scroll', onScroll); }
  onScroll();
}

/* cursor */
const curEl = $('#cur'); if (curEl && matchMedia('(hover:hover) and (pointer:fine)').matches) { const lab = curEl.firstElementChild; let x = -99, y = -99, sx = x, sy = y;
  addEventListener('pointermove', e => { x = e.clientX; y = e.clientY; const t = e.target, hit = t.closest && (t.closest('#gl') ? 'DRAG' : t.closest('.cine') ? 'HOLD' : t.closest('.svc') ? 'OPEN' : t.closest('a,button,.ind') ? '' : null); curEl.classList.toggle('big', hit !== null); lab.textContent = hit || ''; }, {passive:true});
  const loop = () => { sx += (x - sx) * .22; sy += (y - sy) * .22; curEl.style.transform = `translate(${sx}px,${sy}px)`; requestAnimationFrame(loop); }; loop(); }

/* contact form */
const cf = $('#cf'), cfm = $('#cfm'); const siteKey = document.querySelector('meta[name="turnstile-sitekey"]')?.content;
if (siteKey) { const s = document.createElement('script'); s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js'; s.async = true; s.onload = () => turnstile.render('#ts', {sitekey:siteKey}); document.head.append(s); }
cf.addEventListener('submit', async e => { e.preventDefault(); cfm.className = 'cf-msg'; const d = Object.fromEntries(new FormData(cf)); d.nda = cf.nda.checked;
  if (!d.name || !/^\S+@\S+\.\S+$/.test(d.email || '') || !d.message) { cfm.textContent = 'Please add your name, a valid email and a short message.'; cfm.classList.add('err'); return; }
  cfm.textContent = 'Sending…'; try { const r = await fetch('/api/contact', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify(d)}); const j = await r.json(); if (!r.ok || !j.ok) throw new Error(j.error || 'failed'); cf.reset(); cfm.textContent = 'Received. Ernest will reply personally within one working day.'; } catch (err) { cfm.textContent = 'That did not send. Please try again in a moment.'; cfm.classList.add('err'); } });

/* Kickstarter backer list: saved to HQ like a brief */
const ksf = $('#ksf'), ksm = $('#ksm');
if (ksf) ksf.addEventListener('submit', async e => { e.preventDefault(); ksm.className = 'ks-m mono'; const email = ksf.email.value.trim();
  if (!/^\S+@\S+\.\S+$/.test(email)) { ksm.textContent = 'Please enter a valid email.'; ksm.classList.add('err'); return; }
  ksm.textContent = 'Adding you…'; try { const r = await fetch('/api/contact', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({name:'Kickstarter backer list', email, project:'Kickstarter', message:'Wants an email when the first NSKO Kickstarter campaign opens.', website:ksf.website.value})}); const j = await r.json(); if (!r.ok || !j.ok) throw 0; ksf.reset(); ksm.textContent = 'You’re on the list. One email when the campaign opens, nothing else.'; } catch (err) { ksm.textContent = 'That didn’t go through. Please try again in a moment.'; ksm.classList.add('err'); } });
