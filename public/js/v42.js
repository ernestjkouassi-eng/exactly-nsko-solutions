// NSKO Solutions v4.2 — scenes, panels, Lab, forms. No sound, no loaders, no scroll-jacking.
const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
document.documentElement.style.setProperty('--dpr', Math.min(devicePixelRatio || 1, 3));

/* ---------- content ---------- */
const CAP = {
  'intelligent-systems': {t: 'Intelligent systems', obj: 'chip', line: 'The brain inside the machine.', b: ['Perception, planning and control software for robots and drones.', 'Platforms that run fleets of machines, with people in charge.', 'Models tested on your own data before anything goes live.'], aud: ['healthcare', 'industry', 'defence']},
  'robotics': {t: 'Robotics and prototypes', obj: 'arm', line: 'Built in house, tested by hand.', b: ['Small robots and robot arms, designed and built in house.', '3D-printed working prototypes you can hold and test.', 'Test, improve, hand over, with drawings and source files.'], aud: ['industry', 'healthcare', 'partner']},
  'secure-platforms': {t: 'Secure platforms', obj: 'blade', line: 'Software for regulated work.', b: ['Web, mobile and data platforms for regulated work.', 'Role-based access, audit trails and UK hosting options.', 'Built to pass review by your own security team.'], aud: ['government', 'healthcare']},
  'cyber-security': {t: 'Cyber security', obj: 'key', line: 'Find it before they do.', b: ['Penetration testing of apps, networks and devices.', 'Technical bug sweeps for rooms and vehicles.', 'Plain-English reports with fixes ranked by risk.'], aud: ['government', 'defence']},
};
const LAB = {
  drone: {t: 'Drone', obj: 'drone', s: 'Concept', d: 'A compact quadcopter frame with a stabilised camera pod. Printed carbon-nylon arms, swappable payload bay.', spec: [['Status', 'Concept'], ['Frame', 'Quad, 420 mm diagonal'], ['Build', 'Printed arms, machined motor mounts']]},
  architecture: {t: 'Architectural scale model', obj: 'arch', s: 'Concept', d: 'A presentation model for a small mixed-use scheme. Printed in white resin on a dark plinth, with a cantilevered roof.', spec: [['Status', 'Concept'], ['Scale', '1:200'], ['Build', 'Resin print, hand finished']]},
  watch: {t: 'Watch', obj: 'watch', s: 'Concept', d: 'A minimal three-hand watch with a brushed steel case and a single signal-orange seconds hand.', spec: [['Status', 'Concept'], ['Case', '40 mm, brushed steel'], ['Build', 'Machined case, printed strap links']]},
  pendant: {t: 'Pendant', obj: 'pendant', s: 'Concept', d: 'The NSKO mark as a pendant in polished steel, with the orange fragment in enamel.', spec: [['Status', 'Concept'], ['Size', '32 mm'], ['Build', 'Cast steel, enamel fill']]},
};
const PROJ = {
  nsko: {t: 'NSKO', tag: 'Live', live: true, d: 'Our own fitness, health and coaching membership, with wellness in VR. Members, coaches and an admin portal, on the web and in the app.', kv: [['Status', 'Live'], ['Built', 'Web, iOS and Android app, member portal'], ['Stack', 'Secure sign-in, row-level security, payments']]},
  wellspring: {t: 'NSKO 1.1 Wellspring', tag: 'Demo built', d: 'A working demo built to show the idea end to end. Every number in it is simulated data.', kv: [['Status', 'Demo built'], ['Data', 'Simulated data only'], ['Next', 'Partner pilot']], demo: true},
  pure: {t: 'NSKO 1.2 Pure', tag: 'Concept', d: 'An early concept. No product exists yet and we make no safety or health claims about it.', kv: [['Status', 'Concept'], ['Next', 'Research and partners']]},
};
const IMPACT = {
  water: {t: 'Clean water', d: 'Low-cost sensor kits that check water quality at the tap and report it to the people who run the supply.', g: [['Phase 1', 'Feasibility and lab tests, 3 to 6 months'], ['Phase 2', 'Field pilot with a delivery partner'], ['Phase 3', 'Scale with the partner and local makers'], ['We need', 'A water charity or utility partner, letters of support, match funding'], ['Status', 'Programme concept. Not yet funded.']]},
  health: {t: 'Health diagnostics concept', d: 'A simple screening device and app for clinics with little equipment. A concept only, with no medical claims until it is tested and approved.', g: [['Phase 1', 'Needs research with clinicians'], ['Phase 2', 'Prototype and lab validation'], ['Phase 3', 'Regulated trials with an NHS or university partner'], ['We need', 'A clinical partner, ethics approval route, research funding'], ['Status', 'Programme concept. Not yet funded.']]},
  climate: {t: 'Climate and food resilience', d: 'Drones and ground sensors that help small farms see crop stress, water use and soil health early.', g: [['Phase 1', 'Sensor and drone feasibility'], ['Phase 2', 'Season-long pilot with growers'], ['Phase 3', 'Open data tools for co-ops'], ['We need', 'Grower groups, a research partner, grant funding'], ['Status', 'Programme concept. Not yet funded.']]},
};
const AUD = {healthcare: 'Healthcare first: intelligent systems and secure platforms for clinical and care teams.', government: 'Government first: secure platforms and cyber security built for public sector review.', defence: 'Defence first: cyber security, sweeps and intelligent systems for controlled settings.', industry: 'Industry first: robotics, prototypes and machine software you can test on site.', partner: 'Funders and partners first: our Impact programmes and how grants would run them.'};

/* ---------- scenes: index, dots, reveal, keys ---------- */
const scenes = $$('.scene');
const setCur = id => { $$('.index a,.dots a').forEach(a => a.toggleAttribute('aria-current', a.getAttribute('href') === '#' + id)); };
const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); setCur(e.target.id); if (e.target.id === 's2') playCap(); } }), {threshold: .55});
scenes.forEach(s => io.observe(s));
if (RM) scenes.forEach(s => s.classList.add('in'));
const go = i => scenes[Math.max(0, Math.min(scenes.length - 1, i))]?.scrollIntoView({behavior: RM ? 'auto' : 'smooth'});
const curIdx = () => { const y = innerHeight / 2; return Math.max(0, scenes.findIndex(s => { const r = s.getBoundingClientRect(); return r.top <= y && r.bottom > y; })); };
$$('[data-next]').forEach(a => a.addEventListener('click', e => { e.preventDefault(); go(scenes.indexOf(a.closest('.scene')) + 1); }));
$$('.index a,.dots a').forEach(a => a.addEventListener('click', e => { e.preventDefault(); go(+a.getAttribute('href').slice(2) - 1); }));
addEventListener('keydown', e => {
  if ($('dialog[open]') || /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName)) return;
  if (e.key === 'ArrowDown' || e.key === 'PageDown') { e.preventDefault(); go(curIdx() + 1); }
  if (e.key === 'ArrowUp' || e.key === 'PageUp') { e.preventDefault(); go(curIdx() - 1); }
});

/* ---------- hero: 120-frame turntable on canvas, scroll + drag ---------- */
const hero = $('#hero'), hx = hero.getContext('2d');
const NF = 120, step = 2;
const frames = new Array(NF);
let shown = -1, dragOff = 0, autoT = 0;
const draw = i => {
  i = ((Math.round(i) % NF) + NF) % NF; i -= i % step;
  let f = frames[i], k = i;
  while (!f && k > 0) f = frames[k -= step];
  if (!f || k === shown) return; shown = k;
  hx.clearRect(0, 0, 1600, 1000); hx.drawImage(f, 0, 0, 1600, 1000);
};
const load = i => new Promise(r => { const im = new Image(); im.decoding = 'async'; im.onload = () => { frames[i] = im; r(); }; im.onerror = r; im.src = `/media/v42/hero/f${String(i).padStart(3, '0')}.webp`; });
load(0).then(() => { draw(0); if (RM) return;
  const rest = []; for (let i = step; i < NF; i += step) rest.push(i);
  const idle = window.requestIdleCallback || (f => setTimeout(f, 200));
  idle(async () => { for (let j = 0; j < rest.length; j += 8) await Promise.all(rest.slice(j, j + 8).map(load)); });
});
const heroIdx = () => { const p = Math.min(1, Math.max(0, scrollY / innerHeight)); return (NF - 1) * 0.5 + p * 50 + dragOff + autoT; };
if (!RM) {
  addEventListener('scroll', () => requestAnimationFrame(() => draw(heroIdx())), {passive: true});
  let down = null;
  hero.addEventListener('pointerdown', e => { down = {x: e.clientX, o: dragOff}; hero.setPointerCapture(e.pointerId); });
  hero.addEventListener('pointermove', e => { if (!down) return; dragOff = down.o + (e.clientX - down.x) / 6; dragOff = Math.max(-59, Math.min(59, dragOff)); draw(heroIdx()); });
  hero.addEventListener('pointerup', () => down = null); hero.addEventListener('pointercancel', () => down = null);
  // a slow breath back and forth while idle on scene 1
  let t0 = performance.now();
  const tick = now => { if (!down && scrollY < innerHeight * .5 && !document.hidden) { autoT = Math.sin((now - t0) / 4200) * 10; draw(heroIdx()); } requestAnimationFrame(tick); };
  requestAnimationFrame(tick);
} else load(60).then(() => draw(60));

/* parallax on stages (8–24px) */
if (!RM && matchMedia('(pointer:fine)').matches) addEventListener('pointermove', e => {
  const x = e.clientX / innerWidth - .5, y = e.clientY / innerHeight - .5;
  $$('.stage').forEach((s, i) => { s.style.transform = `translate3d(${(-x * (12 + i * 3)).toFixed(1)}px,${(-y * (8 + i * 2)).toFixed(1)}px,0)`; });
}, {passive: true});

/* ---------- capabilities tabs ---------- */
const capd = $('#capd'), capvid = $('#capvid'), capmore = $('#capmore');
let cap = 'intelligent-systems';
const capHTML = k => `<p class="k">${esc(CAP[k].t)}</p><p class="lede" style="margin-top:8px">${esc(CAP[k].line)}</p><ul>${CAP[k].b.map(x => `<li>${esc(x)}</li>`).join('')}</ul>`;
function setCap(k, focus) {
  cap = k; $$('[data-cap]').forEach(b => { const on = b.dataset.cap === k; b.setAttribute('aria-selected', on); b.tabIndex = on ? 0 : -1; if (on && focus) b.focus(); });
  capd.setAttribute('aria-labelledby', 't-' + k); capd.innerHTML = capHTML(k); capmore.href = '/capabilities/' + k;
  capvid.style.opacity = 0;
  setTimeout(() => { capvid.poster = `/media/v42/poster/${CAP[k].obj}-900.webp`; capvid.src = RM ? '' : `/media/v42/loop/${CAP[k].obj}.mp4`; capvid.style.opacity = 1; playCap(); }, RM ? 0 : 250);
}
function playCap() { if (!RM && capvid.src && scenes[1].classList.contains('in')) capvid.play().catch(() => {}); }
$$('[data-cap]').forEach(b => b.addEventListener('click', () => setCap(b.dataset.cap)));
$('.tabs').addEventListener('keydown', e => { const ks = $$('[data-cap]').map(b => b.dataset.cap), i = ks.indexOf(cap);
  if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { e.preventDefault(); e.stopPropagation(); setCap(ks[(i + (e.key === 'ArrowRight' ? 1 : ks.length - 1)) % ks.length], true); } });
capmore.addEventListener('click', e => { e.preventDefault(); openRoute('capabilities/' + cap); });

/* ---------- lab cards with tilt (max 6°) ---------- */
$('#labcards').innerHTML = Object.entries(LAB).map(([k, v]) => `<a class="card" href="/lab/${k}" data-lab="${k}"><img src="/media/v42/poster/${v.obj}-600.webp" width="600" height="600" alt="${esc(v.t)}, studio render" loading="lazy" decoding="async"><div class="meta"><h3>${esc(v.t)}</h3><span class="tag">${esc(v.s)}</span></div></a>`).join('');
if (!RM && matchMedia('(pointer:fine)').matches) $$('.card').forEach(c => {
  c.addEventListener('pointermove', e => { const r = c.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5; c.style.transform = `perspective(900px) rotateY(${x * 12}deg) rotateX(${-y * 12}deg)`; });
  c.addEventListener('pointerleave', () => c.style.transform = '');
});
$('#tiles').innerHTML = Object.entries(IMPACT).map(([k, v]) => `<a class="tile" href="/impact/#${k}" data-impact="${k}"><h3>${esc(v.t)}</h3><p>${esc(v.d)}</p><span class="k">Concept · Grant structure</span></a>`).join('');

/* ---------- dialogs and routes ---------- */
const panel = $('#panel'), pbody = $('#pbody');
let viewer = null, lastFocus = null;
const kv = rows => `<dl class="kv">${rows.map(([a, b]) => `<dt>${esc(a)}</dt><dd>${esc(b)}</dd>`).join('')}</dl>`;
function openDlg(d) { lastFocus = document.activeElement; if (!d.open) d.showModal(); }
function routeHTML(r) {
  const [sec, k] = r.split('/');
  if (sec === 'capabilities' && CAP[k]) { const v = CAP[k]; return `<p class="k" style="margin-top:12px">Capabilities</p><h2 id="ph">${esc(v.t)}</h2><div class="media"><img src="/media/v42/poster/${v.obj}-900.webp" alt="${esc(v.t)}, studio render" width="900" height="900"></div><p class="lede">${esc(v.line)}</p><div class="detail" style="margin-top:0;border:0;padding:0"><ul>${v.b.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div><div class="row" style="margin-top:26px"><a class="btn p" href="/start" data-start>Start a project</a></div>`; }
  if (sec === 'lab' && LAB[k]) { const v = LAB[k]; return `<p class="k" style="margin-top:12px">Prototype Lab</p><h2 id="ph">${esc(v.t)}</h2><div class="media" data-glb="${v.obj}"><img src="/media/v42/poster/${v.obj}-900.webp" alt="${esc(v.t)}, studio render" width="900" height="900"><span class="k hint">Drag to turn</span></div><span class="tag">${esc(v.s)}</span><p class="lede" style="margin-top:16px">${esc(v.d)}</p>${kv(v.spec)}<div class="row" style="margin-top:22px"><a class="btn p" href="/lab/portfolio" data-pack>Request the portfolio pack</a></div>`; }
  if (sec === 'projects' && PROJ[k]) { const v = PROJ[k]; return `<p class="k" style="margin-top:12px">Projects</p><h2 id="ph">${esc(v.t)}</h2><span class="tag">${v.live ? '<span class="dot live" aria-hidden="true"></span> ' : ''}${esc(v.tag)}</span>${v.demo ? `<div class="media" data-demo style="margin-top:18px;aspect-ratio:9/16;max-height:62svh;display:none"></div>` : ''}<p class="lede" style="margin-top:16px">${esc(v.d)}</p>${kv(v.kv)}<div class="row" style="margin-top:22px"><a class="btn p" href="/start" data-start>Start a project</a></div>`; }
  return null;
}
function openRoute(r, push = true) {
  if (r === 'start') return openStart(push);
  if (r === 'lab/portfolio') return openPack(push);
  const h = routeHTML(r); if (!h) return;
  pbody.innerHTML = h; openDlg(panel); panel.scrollTop = 0;
  if (push && location.pathname !== '/' + r) history.pushState({r}, '', '/' + r);
  const dm = $('[data-demo]', pbody); if (dm) fetch('/demo/wellspring/', {method: 'HEAD'}).then(r => { if (!r.ok) return; dm.style.display = ''; dm.innerHTML = '<iframe src="/demo/wellspring/" title="Wellspring demo, simulated data" loading="lazy" sandbox="allow-scripts allow-same-origin"></iframe><span class="k hint" style="background:#0B0B0D;padding:6px 10px;border-radius:999px">Simulated data</span>'; }).catch(() => {});
  const m = $('[data-glb]', pbody); if (m) import('/js/lab3d.js').then(x => { viewer = x.mount(m, m.dataset.glb); }).catch(() => {});
}
function openStart(push = true) { openDlg($('#start')); if (push && location.pathname !== '/start') history.pushState({r: 'start'}, '', '/start'); }
function openPack(push = true) { openDlg($('#pack')); if (push && location.pathname !== '/lab/portfolio') history.pushState({r: 'lab/portfolio'}, '', '/lab/portfolio'); }
$$('dialog').forEach(d => {
  d.addEventListener('close', () => { if (d === panel) { viewer?.dispose?.(); viewer = null; } if (!$('dialog[open]') && location.pathname !== '/') history.pushState({}, '', '/' + location.hash); lastFocus?.focus?.(); });
  d.addEventListener('click', e => { if (e.target === d && d !== $('#menu')) d.close(); if (e.target.closest('[data-close]')) d.close(); });
});
document.addEventListener('click', e => {
  const a = e.target.closest('a'); if (!a || e.defaultPrevented || e.metaKey || e.ctrlKey) return;
  if (a.hasAttribute('data-start')) { e.preventDefault(); $$('dialog[open]').forEach(d => d !== $('#start') && d.close()); openStart(); return; }
  if (a.hasAttribute('data-pack')) { e.preventDefault(); $$('dialog[open]').forEach(d => d !== $('#pack') && d.close()); openPack(); return; }
  const u = new URL(a.href, location.href); if (u.origin !== location.origin) return;
  const r = u.pathname.replace(/^\/|\/$/g, '');
  if (/^(capabilities|lab|projects)\/[\w-]+$/.test(r)) { e.preventDefault(); $$('dialog[open]').forEach(d => d.close()); openRoute(r); }
});
$('[data-open-menu]').addEventListener('click', () => openDlg($('#menu')));
addEventListener('popstate', () => { const r = location.pathname.replace(/^\/|\/$/g, ''); $$('dialog[open]').forEach(d => d.close()); if (r) openRoute(r, false); });
// deep link: /capabilities/robotics etc. are static copies of this page with a route meta
{ const r = $('meta[name=nsko-route]')?.content; if (r) { const sec = {capabilities: 1, lab: 2, projects: 3}[r.split('/')[0]];
  if (sec) scenes[sec].scrollIntoView(); if (r.startsWith('capabilities/')) setCap(r.split('/')[1]); openRoute(r, false); } }

/* ---------- audience selector ---------- */
const saved = (() => { try { return localStorage.getItem('nsko-aud'); } catch { return null; } })();
function setAud(a, save = true) {
  $$('[data-aud]').forEach(b => b.setAttribute('aria-pressed', b.dataset.aud === a));
  $('#audnote').textContent = AUD[a] || 'Pick one and we show the work that fits you first.';
  if (!a) return; if (save) try { localStorage.setItem('nsko-aud', a); } catch {}
  const tabs = $('.tabs'), order = Object.keys(CAP).sort((x, y) => (CAP[y].aud.indexOf(a) > -1 ? 3 - CAP[y].aud.indexOf(a) : 0) - (CAP[x].aud.indexOf(a) > -1 ? 3 - CAP[x].aud.indexOf(a) : 0));
  order.forEach(k => tabs.appendChild($(`[data-cap="${k}"]`)));
  if (!$('meta[name=nsko-route]')?.content?.startsWith('capabilities/')) setCap(order[0]);
  const sec = {healthcare: 'Healthcare', government: 'Government', defence: 'Defence', industry: 'Industry', partner: 'Charity or funder'}[a]; $('#f-sector').value = sec;
}
$$('[data-aud]').forEach(b => b.addEventListener('click', () => setAud(b.dataset.aud)));
setCap(cap); if (saved && AUD[saved]) setAud(saved, false);

/* ---------- forms ---------- */
const tsKey = $('meta[name=nsko-ts]')?.content;
if (tsKey) { const s = document.createElement('script'); s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'; s.async = true;
  s.onload = () => $$('[data-ts]').forEach(el => window.turnstile.render(el, {sitekey: tsKey, theme: 'dark', size: 'flexible'})); document.head.appendChild(s); }
$$('[data-multi] .chip').forEach(c => c.addEventListener('click', () => c.setAttribute('aria-pressed', c.getAttribute('aria-pressed') !== 'true')));
async function send(url, form, extra) {
  const fd = new FormData(form); for (const [k, v] of Object.entries(extra || {})) fd.set(k, v);
  const ts = $('[name="cf-turnstile-response"]', form); if (ts) fd.set('cf-turnstile-response', ts.value);
  const r = await fetch(url, {method: 'POST', body: fd}); let j = {}; try { j = await r.json(); } catch {}
  if (!r.ok || !j.ok) throw new Error(j.error || 'failed'); return j;
}
const errText = e => ({'slow down': 'Too many tries. Please wait an hour and try again.', captcha: 'Please complete the check and try again.', 'file too large': 'That file is over 10 MB.', 'file type': 'Please attach a PDF, image or document.'}[e.message] || 'That did not send. Please email hello@nskosolutions.co.uk.');
{ // Start a project: 3 steps
  const f = $('#sform'), steps = $$('.step', f), bars = $$('#start .steps i'), back = $('[data-back]', f), sub = $('[type=submit]', f), msg = $('.msg', f);
  let n = 0;
  const show = i => { n = i; steps.forEach((s, j) => s.classList.toggle('on', j === i)); bars.forEach((b, j) => b.classList.toggle('on', j <= i)); back.hidden = i === 0; sub.textContent = i === 2 ? 'Send' : 'Next'; msg.textContent = ''; $('input,select,textarea', steps[i])?.focus(); };
  const valid = i => { for (const el of $$('[required]', steps[i])) { if (el.type === 'checkbox' ? !el.checked : !el.value.trim() || (el.type === 'email' && !/^\S+@\S+\.\S+$/.test(el.value))) { el.focus(); msg.textContent = el.type === 'checkbox' ? 'Please tick the box to continue.' : 'Please fill in ' + ($(`label[for="${el.id}"]`)?.textContent || 'this field').toLowerCase() + '.'; return false; } }
    const fl = $('#f-file').files[0]; if (i === 1 && fl && fl.size > 10 * 1024 * 1024) { msg.textContent = 'That file is over 10 MB.'; return false; } return true; };
  back.addEventListener('click', () => show(n - 1));
  f.addEventListener('submit', async e => { e.preventDefault(); if (!valid(n)) return; if (n < 2) return show(n + 1);
    sub.disabled = true; msg.textContent = 'Sending.';
    try { await send('/api/brief', f, {type: $$('[data-multi=type] [aria-pressed=true]').map(b => b.textContent).join(', '), source: location.pathname}); f.innerHTML = '<p class="lede" style="margin-top:10px">Thank you. We will reply.</p>'; }
    catch (er) { msg.textContent = errText(er); sub.disabled = false; } });
}
{ const f = $('#pform'), msg = $('.msg', f), sub = $('[type=submit]', f);
  f.addEventListener('submit', async e => { e.preventDefault();
    for (const el of $$('[required]', f)) if (el.type === 'checkbox' ? !el.checked : !el.value.trim()) { el.focus(); msg.textContent = 'Please complete every field marked and tick the box.'; return; }
    sub.disabled = true; msg.textContent = 'Sending.';
    try { await send('/api/portfolio', f); f.innerHTML = '<p class="lede" style="margin-top:10px">Thank you. We check each request by hand and will reply.</p>'; }
    catch (er) { msg.textContent = errText(er); sub.disabled = false; } });
}
