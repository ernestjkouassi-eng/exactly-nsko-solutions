const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const heroApi = {};
let booted = false, lenis = null, st = null;

/* ---------------- loader: 96-dot ring, counter driven by real bytes ---------------- */
const ring = $('#ring'), rx = ring.getContext('2d');
let pct = 0, shown = 0, skipped = false;
const drawRing = fly => { const w = ring.width = innerWidth, h = ring.height = innerHeight, cx = w / 2, cy = h / 2, R = Math.min(w, h) * .24; rx.clearRect(0, 0, w, h);
  for (let i = 0; i < 96; i++) { const a = i / 96 * Math.PI * 2 - Math.PI / 2, on = i / 96 <= shown / 100, f = fly || 0, r = R * (1 + f * 3), x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r * (1 - f * .3); rx.globalAlpha = (on ? 1 : .25) * (1 - f); rx.fillStyle = on ? '#7FD4FF' : '#CFE0F5'; rx.beginPath(); rx.arc(x, y, 3, 0, 7); rx.fill(); } };
const assets = ['/vendor/three/three.module.js', '/js/cine.js', '/js/medusa.js', '/media/seq/hero/f20.webp', '/fonts/Geist.woff2', '/fonts/InstrumentSerif-Italic.woff2', '/fonts/GeistMono.woff2'];
async function preload() { const sizes = await Promise.all(assets.map(u => fetch(u, {method:'HEAD'}).then(r => +r.headers.get('content-length') || 60000).catch(() => 60000))); const total = sizes.reduce((a, b) => a + b, 0); let got = 0;
  await Promise.all(assets.map(async u => { try { const r = await fetch(u); const rd = r.body.getReader(); for (;;) { const {done, value} = await rd.read(); if (done) break; got += value.length; pct = Math.min(99, got / total * 100); } } catch (e) {} })); pct = 100; }
const LOG = ['> linking perception', '> calibrating state estimate', '> loading planner', '> arming control loop', '> verifying trust chain', '> systems online'], ldlog = $('#ldlog'); let logN = 0;
function tickLoader() { const want = Math.min(LOG.length, Math.floor(shown / 100 * LOG.length) + 1); while (ldlog && logN < want) { const d = document.createElement('div'); d.textContent = LOG[logN++] + (logN < LOG.length ? ' \u2026 ok' : ''); ldlog.append(d); } shown += (pct - shown) * .12; if (pct >= 100 && shown > 99.5) shown = 100; $('#ldc').textContent = String(Math.round(shown)).padStart(3, '0'); drawRing(0); if (shown < 100 && !skipped) requestAnimationFrame(tickLoader); else finishLoader(); }
function finishLoader() { if (booted) return; booted = true; const t0 = performance.now(); const fly = now => { const f = Math.min(1, (now - t0) / (reduced || skipped ? 1 : 700)); drawRing(f * f); if (f < 1) requestAnimationFrame(fly); else { $('#loader').classList.add('out'); setTimeout(() => $('#loader').remove(), 700); } }; requestAnimationFrame(fly); boot(); }
$('#ldskip').onclick = () => { skipped = true; pct = 100; };
tickLoader(); preload().then(() => { pct = 100; });

/* ---------------- scene table: length in viewport-heights of scroll ---------------- */
const SC = [
  {id:'hero', len:1.0, l:'Start'}, {id:'manifesto', len:1.2, l:'Our aim'}, {id:'field', len:1.9, l:'The machine'},
  {id:'drone', len:5.2, l:'The system'}, {id:'healthcare', len:3.8, l:'Healthcare'}, {id:'defence', len:3.8, l:'Defence'},
  {id:'sweeps', len:2.8, l:'Bug sweeps'}, {id:'capabilities', len:2.4, l:'Capabilities'}, {id:'nova', len:2.8, l:'Ask NSKO'},
  {id:'work', len:1.5, l:'Work'}, {id:'process', len:1.5, l:'Process'},
];
const OV = .38; let acc = 0;
SC.forEach((s, i) => { s.a = i ? acc - OV : 0; s.b = s.a + s.len; acc = s.b; s.el = $('#' + s.id); });
const TOTAL = acc;
const smooth = t => { t = Math.min(1, Math.max(0, t)); return t * t * (3 - 2 * t); };
const seg = (p, a, b) => smooth((p - a) / (b - a));
const rv = (el, t, y = 34) => { el.style.opacity = t; el.style.transform = `translateY(${(1 - t) * y}px)`; };

/* ---------------- lazy 3D modules (dispose when far, re-init when near) ---------------- */

const NOTE_H = 'Concept visualisation. NSKO writes software, data and simulation; partners build the hardware. Not a medical device.';
const NOTE_D = 'Concept visualisation. NSKO writes software and simulation; partners build the hardware. No weapons systems.';
const CINE = {
  hero: {seq:'/media/seq/hero', first:20, posY:.3, cls:'is-hero'},
  drone: {seq:'/media/seq/drone', portraitZoom:1.85, portraitY:.42, cls:'is-drone', tag:'SURVEY UNIT', kicker:'TEN YEARS IN THE BUILD', intro:'We see the whole <em>system.</em>', closing:'We code the <em>mind</em> and the system. Partners build the airframe.', tilt:2.4,
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
  healthcare: {seq:'/media/seq/surgery', posX:.3, cls:'is-health', tag:'THEATRE 2', push:.16, kicker:'HEALTHCARE', headline:'Intelligence for the <em>operating room.</em>', closing:'We don’t build the robot. We code the mind and the system.', note:NOTE_H,
    items:[{t:'Surgical-robot control and simulation software', d:'Kinematics, motion planning and a digital twin to rehearse against, written as software your hardware partner can run.'},
      {t:'Computer vision for imaging and live scene understanding', d:'Models that read the field of view and flag what a team needs to see, with confidence shown.'},
      {t:'Clinical and wearable data platforms', d:'Secure pipelines that bring device, wearable and record data into one clinical view.'},
      {t:'Lab, trial and supply-chain data systems', d:'Clean audit trails from sample to result to shipment.'},
      {t:'AI agents for clinical workflow', d:'Assistants that draft, schedule and summarise, with a person always in charge.'}]},
  sweeps: {seq:'/media/seq/sweeps', posX:.3, cls:'is-def', tag:'TSCM', push:.14, kicker:'BUG SWEEPS', headline:'Find what should <em>not</em> be there.', closing:'Discreet teams. A written report.', note:'Sweeps are for spaces you own or control.',
    items:[{t:'Offices and boardrooms', d:'Before the meeting that matters: rooms, fittings, cabling and conferencing kit.'},
      {t:'Vehicles', d:'Trackers and listening devices, found and documented.'},
      {t:'Homes and hotels', d:'Private spaces checked quietly, at short notice.'},
      {t:'Phones and networks', d:'Rogue access points, odd traffic and compromised devices.'}]},
  defence: {seq:'/media/seq/defence', cls:'is-def', tag:'OPS FLOOR', push:.16, kicker:'DEFENCE', headline:'The mind behind the <em>mission.</em>', closing:'We don’t build the machine. We code the mind and the system.', note:NOTE_D,
    items:[{t:'Autonomy and mission-planning software', d:'Route planning, task allocation and re-planning for survey swarms, written so a person can audit every decision.'},
      {t:'Sensor fusion and telemetry dashboards', d:'Many feeds, one picture: tracks, health and link quality on a single screen.'},
      {t:'Secure communications and zero-trust architecture', d:'Signed commands, encrypted links and least-privilege access by design.'},
      {t:'Digital twins and field simulators', d:'Rehearse the plan in software before anything leaves the ground.'},
      {t:'Counter-surveillance and RF sweep reporting', d:'Sweeps of spaces you own or control, with a written report.'}]},
};
const NOVA_PROMPTS = ['Write flight software for a survey drone.', 'Audit this codebase for security holes.', 'Sweep our boardroom before Monday’s board meeting.', 'Build a clinical data dashboard for our trial.'];
const MODS = {
  hero:       {load:() => import('/js/cine.js'), make:(m, el) => m.initHero(el, heroApi, CINE.hero), dispose:true},
  field:      {load:() => import('/js/medusa.js'),   make:(m, el) => { m.initMedusa(el); }, on:'#medusa'},
  drone:      {load:() => import('/js/cine.js'), make:(m, el) => m.init(el, CINE.drone), dispose:true},
  healthcare: {load:() => import('/js/cine.js'), make:(m, el) => m.init(el, CINE.healthcare), dispose:true},
  defence:    {load:() => import('/js/cine.js'), make:(m, el) => m.init(el, CINE.defence), dispose:true},
  sweeps:     {load:() => import('/js/cine.js'), make:(m, el) => m.init(el, CINE.sweeps), dispose:true},
  nova:       {load:() => import('/js/nova.js'),     make:(m, el) => { m.initNova(el, {prompts:NOVA_PROMPTS}); }},
};
const state = {}, handles = {};
async function ensure(s) {
  const M = MODS[s.id]; if (!M || state[s.id]) return; state[s.id] = 'loading';
  try { const mod = await M.load(); const host = M.on ? $(M.on) : s.el; const h = M.make(mod, host); handles[s.id] = h || null; state[s.id] = 'on'; if (s.id === 'hero') heroApi.start && heroApi.start(); }
  catch (e) { state[s.id] = 'failed'; console.warn('scene failed', s.id, e); }
}
function release(s) { const M = MODS[s.id]; if (!M || !M.dispose || state[s.id] !== 'on') return; try { handles[s.id] && handles[s.id].dispose && handles[s.id].dispose(); } catch (e) {} handles[s.id] = null; state[s.id] = null; }
function webgl2() { try { return !!document.createElement('canvas').getContext('webgl2'); } catch (e) { return false; } }
const GL = webgl2();

/* ---------------- per-scene choreography (p in 0..1) ---------------- */
const fit = (el, p) => { const H = el.parentElement.clientHeight || innerHeight, over = el.scrollHeight - H; el.style.justifyContent = over > 4 ? 'flex-start' : 'center'; el.style.transform = over > 4 ? `translateY(${-over * seg(p, .12, .9)}px)` : ''; };
const mfWords = $$('#mf .ln').map(l => { const words = l.innerHTML.split(/(<em>.*?<\/em>)|\s+/).filter(Boolean); l.innerHTML = words.map(w => `<span class="w">${w}</span>`).join(' '); return $$('.w', l); }).flat();
const counted = new Set();
const ACT = {
  hero(p) { const o = 1 - seg(p, .05, .5); $('.hero-copy').style.opacity = o; $('.pill').style.opacity = o; $('.hero-hint').style.opacity = o; $('.scrollind').style.opacity = o; handles.hero && handles.hero.setProgress && handles.hero.setProgress(p); },
  manifesto(p) { const n = mfWords.length; mfWords.forEach((w, i) => { w.style.opacity = .12 + .88 * seg(p, .08 + i / n * .5, .18 + i / n * .5); }); rv($('.mf-sub'), seg(p, .55, .75), 20); $('.mf-in').style.opacity = 1 - seg(p, .88, 1); },
  field(p) { $('#fcap').style.opacity = 1 - seg(p, .1, .3); const c = $('#fcta'); c.style.opacity = seg(p, .8, .95); c.style.pointerEvents = p > .85 ? 'auto' : 'none'; },
  capabilities(p) { const a = $('.cap-a'), b = $('.cap-b'); const outA = 1 - seg(p, .5, .6), inB = seg(p, .58, .7);
    a.style.opacity = outA; a.style.pointerEvents = outA > .5 ? 'auto' : 'none'; $$('.cap', a).forEach((c, i) => { const t = seg(p, .04 + i * .035, .16 + i * .035); c.style.opacity = t; if (!c.matches(':hover')) c.style.transform = `translateY(${(1 - t) * 40}px) rotateX(${(1 - t) * 14}deg)`; });
    b.style.opacity = inB; b.style.pointerEvents = inB > .5 ? 'auto' : 'none'; $$('li', b).forEach((li, i) => { const t = seg(p, .62 + i * .018, .74 + i * .018); li.style.opacity = t; li.style.transform = `translateY(${(1 - t) * 20}px)`; });
    fit(a, p); fit(b, Math.max(0, (p - .6) / .4)); },
  nova(p) { $('#nova').__p = p * 2; },
  work(p) { $$('.tile').forEach((t, i) => { const k = seg(p, .06 + i * .12, .4 + i * .12); t.style.opacity = k; if (!t.matches(':hover')) t.style.transform = `translateY(${(1 - k) * 60}px) rotateX(${(1 - k) * 10}deg)`; });
    $$('.tile video').forEach(v => { if (p > .15 && p < .95) v.play().catch(() => {}); else v.pause(); }); fit($('.work-in'), p); },
  process(p) { $$('.nums b').forEach(b => { if (p > .12 && !counted.has(b)) { counted.add(b); const n = +b.dataset.n; gsap.to({v:0}, {v:n, duration:1.5, ease:'power2.out', onUpdate() { b.textContent = Math.round(this.targets()[0].v); }}); } });
    $$('.steps > div').forEach((d, i) => { const k = seg(p, .22 + i * .1, .5 + i * .1); d.style.opacity = k; d.style.transform = `translateY(${(1 - k) * 50}px) rotateX(${(1 - k) * 30}deg)`; }); fit($('.proc-in'), p); },
};

/* ---------------- master render ---------------- */
const railEl = $('#rail');
SC.forEach(s => { const b = document.createElement('button'); b.dataset.l = s.l; b.setAttribute('aria-label', s.l); b.onclick = () => goTo(s.id); railEl.append(b); });
const railBtns = $$('button', railEl);
let lastActive = -1;
const PHONE = matchMedia('(max-width:860px), (pointer:coarse)').matches;
const TR = PHONE ? {manifesto:'zoom', field:'fade', drone:'zoom', healthcare:'fade', defence:'zoom', sweeps:'fade', capabilities:'zoom', nova:'fade', work:'zoom', process:'fade'} : {manifesto:'zoom', field:'iris', drone:'wipe', healthcare:'iris', defence:'wipe', sweeps:'fade', capabilities:'wipe', nova:'fade', work:'iris', process:'wipe'};
let ptx = innerWidth / 2, pty = innerHeight / 2; addEventListener('pointermove', e => { ptx = e.clientX; pty = e.clientY; }, {passive:true});
const wipeline = $('#wipeline'), hudL = $('#hud-l'), hudN = $('#hud-n'), hudBar = $('#hud-bar');
const GLY = 'ABCDEFGHIKLMNOPRSTUVXYZ01<>/{}[]=+*#';
let scr = 0; function scramble(el, txt) { const id = ++scr, t0 = performance.now(); const f = now => { if (id !== scr) return; const k = Math.min(1, (now - t0) / 600); el.textContent = [...txt].map((c, i) => c === ' ' || i / txt.length < k ? c : GLY[(Math.random() * GLY.length) | 0]).join(''); if (k < 1) requestAnimationFrame(f); }; requestAnimationFrame(f); }
let vel = 0, velS = 0, lastU = 0;
function render(u) {
  velS += (Math.max(-1.6, Math.min(1.6, vel * .035)) - velS) * .2; lastU = u;
  let best = 0, wipeY = -1;
  SC.forEach((s, i) => {
    const tr = TR[s.id] || 'fade', nx = SC[i + 1], ntr = nx ? (TR[nx.id] || 'fade') : null;
    const tin = i ? Math.min(1, Math.max(0, (u - s.a) / OV)) : 1, tout = nx ? Math.min(1, Math.max(0, (u - nx.a) / OV)) : 0;
    let op = 1, clip = 'none', sc = 1;
    if (i && tin < 1) {
      if (tin <= 0) op = 0;
      else if (tr === 'fade') { op = smooth((tin - .3) / .7); sc = 1 - (1 - op) * .05; }
      else if (tr === 'zoom') { op = smooth((tin - .15) / .85); sc = 1.4 - .4 * smooth(tin); }
      else if (tr === 'iris') clip = `circle(${(smooth(tin) * 130).toFixed(2)}vmax at ${ptx | 0}px ${pty | 0}px)`;
      else if (tr === 'wipe') { const k = (1 - smooth(tin)) * 100; clip = `inset(${k.toFixed(2)}% 0 0 0)`; wipeY = k; }
    }
    if (nx && tout > 0) { if (ntr === 'fade' || ntr === 'zoom') { op = Math.min(op, 1 - smooth(tout / .7)); sc = 1 + smooth(tout) * .1; } else { sc = 1 + smooth(tout) * .06; if (tout >= 1) op = 0; } }
    const p = Math.min(1, Math.max(0, (u - s.a) / (s.b - s.a))), on = op > .003, el = s.el, M = MODS[s.id], dEl = M && M.on ? $(M.on) : el;
    if (i && tin > .5) best = i;
    el.style.opacity = op; el.style.visibility = on ? 'visible' : 'hidden'; el.style.zIndex = i + 1; el.style.clipPath = clip; el.style.transform = (sc === 1 && Math.abs(velS) < .02) ? '' : `scale(${sc.toFixed(4)}) skewY(${velS.toFixed(3)}deg)`;
    dEl.dataset.on = on ? '1' : '0'; if (el !== dEl) el.dataset.on = on ? '1' : '0';
    const near = u > s.a - 1.3 && u < s.b + 1.3, far = u < s.a - 3.2 || u > s.b + 3.2;
    if (GL && near) ensure(s); else if (far) release(s);
    if (on) { ACT[s.id] && ACT[s.id](p); if (handles[s.id] && handles[s.id].setProgress && s.id !== 'hero') handles[s.id].setProgress(p); }
  });
  SC.forEach((s, i) => { s.el.style.pointerEvents = i === best ? 'auto' : 'none'; });
  if (wipeline) { wipeline.style.opacity = wipeY > 0 && wipeY < 100 ? 1 : 0; wipeline.style.top = wipeY + '%'; }
  document.body.classList.toggle('past', u >= TOTAL - .02);
  if (hudBar) hudBar.style.transform = `scaleX(${(u / TOTAL).toFixed(4)})`;
  if (best !== lastActive) { if (lastActive >= 0) dispatchEvent(new CustomEvent('nsko:scene', {detail:{id:SC[best].id, l:SC[best].l, n:best + 1}})); lastActive = best; railBtns.forEach((b, i) => b.classList.toggle('on', i === best)); $('#nav').classList.toggle('away', SC[best].id === 'field');
    if (hudL) { scramble(hudL, SC[best].l.toUpperCase()); hudN.textContent = String(best + 1).padStart(2, '0') + ' / ' + String(SC.length).padStart(2, '0'); document.body.dataset.tone = ['field', 'capabilities', 'nova', 'process'].includes(SC[best].id) ? 'light' : 'dark'; } }
}
addEventListener('keydown', e => { if (!st || /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) return; const d = (e.key === 'ArrowDown' || e.key === 'PageDown' || e.key === 'j') ? 1 : (e.key === 'ArrowUp' || e.key === 'PageUp' || e.key === 'k') ? -1 : 0; if (!d) return; e.preventDefault(); const n = lastActive + d; if (n >= SC.length) goTo('contact'); else goTo(SC[Math.max(0, n)].id); });

/* ---------------- boot ---------------- */
function goTo(id) {
  let y;
  if (id === 'contact') y = st ? st.end : $('#contact').offsetTop;
  else { const s = SC.find(x => x.id === id); y = st ? st.start + (s.a + (id === 'hero' ? 0 : Math.min(.2, s.len * .06) + .05)) * innerHeight : s.el.offsetTop; }
  lenis ? lenis.scrollTo(y, {duration:1.8}) : scrollTo({top:y, behavior:reduced ? 'auto' : 'smooth'});
}
$$('[data-go]').forEach(a => a.addEventListener('click', e => { e.preventDefault(); goTo(a.dataset.go); }));
function boot() {
  if (window.gsap) gsap.registerPlugin(ScrollTrigger);
  if (reduced || !window.gsap) {
    document.body.classList.add('flat'); SC.forEach(s => { s.el.style.visibility = 'visible'; s.el.style.opacity = 1; const M = MODS[s.id]; const d = M && M.on ? $(M.on) : s.el; d.dataset.on = '1'; ACT[s.id] && ACT[s.id](.5); if (GL) ensure(s).then(() => handles[s.id] && handles[s.id].setProgress && handles[s.id].setProgress(.5)); });
    $$('.nums b').forEach(b => b.textContent = b.dataset.n); $('#nova').__p = .5; return;
  }
  lenis = window.Lenis ? new Lenis({lerp:.09}) : null; if (lenis) { lenis.on('scroll', e => { vel = e.velocity || 0; dispatchEvent(new CustomEvent('nsko:vel', {detail:vel})); }); lenis.on('scroll', ScrollTrigger.update); gsap.ticker.add(() => { if (Math.abs(velS) > .01 && Math.abs(vel) < .05) { vel = 0; render(lastU); } }); gsap.ticker.add(t => lenis.raf(t * 1000)); gsap.ticker.lagSmoothing(0); }
  st = ScrollTrigger.create({trigger:'#film', start:'top top', end:() => '+=' + Math.round(TOTAL * innerHeight), pin:true, anticipatePin:1, invalidateOnRefresh:true, onUpdate:self => render(self.progress * TOTAL)});
  let snapT = 0, snapping = false; const settle = () => { if (snapping || !st) return; const u = st.progress * TOTAL; for (let i = 1; i < SC.length; i++) { const s = SC[i], t = (u - s.a) / OV; if (t > .02 && t < .98) { const tu = t > .4 ? s.a + OV + .02 : s.a - .02, y = st.start + tu / TOTAL * (st.end - st.start); snapping = true; setTimeout(() => snapping = false, 900); lenis ? lenis.scrollTo(y, {duration:.7}) : scrollTo({top:y, behavior:'smooth'}); return; } } };
  addEventListener('scroll', () => { clearTimeout(snapT); snapT = setTimeout(settle, 170); }, {passive:true});
  render(0); railEl.classList.add('show'); $('#hud').classList.add('show'); import('/js/fx.js').then(f => f.initFx()).catch(() => {});
  gsap.fromTo('.marq-in', {xPercent:0}, {xPercent:-50, duration:40, ease:'none', repeat:-1});
  addEventListener('resize', () => ScrollTrigger.refresh());
}

/* ---------------- capability tilt + glow, work, lightbox ---------------- */
$$('.cap').forEach(c => { c.addEventListener('pointermove', e => { const r = c.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height; c.style.setProperty('--mx', x * 100 + '%'); c.style.setProperty('--my', y * 100 + '%'); if (!reduced) c.style.transform = `rotateX(${(.5 - y) * 8}deg) rotateY(${(x - .5) * 10}deg)`; }); c.addEventListener('pointerleave', () => c.style.transform = ''); });
$$('.tile').forEach(t => { t.addEventListener('pointermove', e => { if (reduced) return; const r = t.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5; t.style.transform = `rotateY(${x * 8}deg) rotateX(${-y * 8}deg)`; }); t.addEventListener('pointerleave', () => t.style.transform = '');
  t.onclick = () => { const lb = $('#lb'), v = $('#lbv'); v.innerHTML = `<source src="/media/${t.dataset.v}.mp4" type="video/mp4">`; v.load(); $('#lbt').textContent = t.dataset.t; $('#lbm').textContent = [t.dataset.s, t.dataset.y, t.dataset.l, t.dataset.r].join(' · '); lb.showModal(); v.play().catch(() => {}); }; });
$('#lb').addEventListener('close', () => $('#lbv').pause()); $('.lb-x').onclick = () => $('#lb').close(); $('#lb').addEventListener('click', e => { if (e.target.id === 'lb') $('#lb').close(); });
const pr = ['Secure by design.', 'One accountable team.', 'Built to be audited.']; let pi = 0; const q = $('#nv-quote');
const swap = d => { q.classList.add('sw'); setTimeout(() => { pi = (pi + d + pr.length) % pr.length; q.textContent = pr[pi]; q.classList.remove('sw'); }, 450); };
$('#pr-next').onclick = () => swap(1); $('#pr-prev').onclick = () => swap(-1);

/* ---------------- contact form ---------------- */
const cf = $('#cf'), cfm = $('#cfm'); const siteKey = document.querySelector('meta[name="turnstile-sitekey"]')?.content;
if (siteKey) { const s = document.createElement('script'); s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js'; s.async = true; s.onload = () => turnstile.render('#ts', {sitekey:siteKey}); document.head.append(s); }
cf.addEventListener('submit', async e => { e.preventDefault(); cfm.className = 'cf-msg'; const d = Object.fromEntries(new FormData(cf)); d.nda = cf.nda.checked;
  if (!d.name || !/^\S+@\S+\.\S+$/.test(d.email || '') || !d.message) { cfm.textContent = 'Please add your name, a valid email and a short message.'; cfm.classList.add('err'); return; }
  cfm.textContent = 'Sending…'; try { const r = await fetch('/api/contact', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify(d)}); const j = await r.json(); if (!r.ok || !j.ok) throw new Error(j.error || 'failed'); cf.reset(); cfm.textContent = 'Received. Ernest will reply personally within one working day.'; } catch (err) { cfm.textContent = 'That did not send. Please try again, or email hello@nskosolutions.co.uk.'; cfm.classList.add('err'); } });
