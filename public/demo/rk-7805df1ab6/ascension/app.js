// Rastamonk Ascension · clickable DEMO in the client's original brand. Demo logins are checked in the browser only; sample data only.
const S3 = '../shared/3d', BR = '../shared/brand';
const DEMO = { beta: 'ASCEND2026', member: ['member@ascension.demo', 'Discipline1'], coach: ['coach@ascension.demo', 'Coach2026'] };
const st = R.store('rm-ascension-demo-v2', {
  user: null, role: null, onboarded: false, goals: ['Build Strength', 'Sharpen Focus'], level: 1, gate: 2, progress: 38, sessions: 3, faceid: false, gateOpen: false,
  rem: { on: true, time: '19:00', loud: true }, pendingUnlock: false, trend: [22, 30, 26, 44, 40, 58, 66], assessRequested: false,
  notes: [{ dur: 24, text: 'Strong stances tonight. Keep your hips lower in horse stance and breathe out on every strike. Gate 3 assessment next week.' }],
});
const GOALS = ['Build Strength', 'Develop Martial Arts Skills', 'Improve Mobility', 'Master Movement', 'Sharpen Focus', 'Track Real Progress'];
const GN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII'];
const GATE_REQ = ['Hold horse stance 60 s', '20 clean front-stance strikes each side', 'Hip mobility flow, 5 min', 'Breathing focus drill, 3 rounds', 'Coach assessment'];
const SESSIONS = [{ n: '04', t: 'Stance & Strike', m: 32, tags: 'strength · martial arts · mobility', ex: ['Joint warm-up · 4 min', 'Horse stance holds · 3 × 45 s', 'Front-stance strikes · 3 × 20', 'Hip mobility flow · 5 min', 'Box breathing · 3 rounds'] },
  { n: '05', t: 'Flow & Focus', m: 26, tags: 'mobility · focus', ex: ['Spine waves · 3 min', 'Crawl patterns · 4 × 30 s', 'Balance holds · 3 × 40 s', 'Candle gaze focus · 4 min'] },
  { n: '06', t: 'Power Base', m: 40, tags: 'strength', ex: ['Goblet squat · 4 × 10', 'Push-up ladder · 1-5', 'Single-leg RDL · 3 × 8', 'Plank to pike · 3 × 10'] }];
const MEMBERS = [{ id: 'you', n: 'Demo member', g: 2, r: 38, last: 'Today' }, { id: 'a', n: 'Member A · sample', g: 4, r: 81, last: 'Yesterday' }, { id: 'b', n: 'Member B · sample', g: 1, r: 64, last: '2 days ago' },
  { id: 'c', n: 'Member C · sample', g: 3, r: 92, last: 'Today' }, { id: 'd', n: 'Member D · sample', g: 6, r: 22, last: '4 days ago' }];
const sb = () => `<div class="sb"><span class="sbt">${R.clock()}</span><span>●●● ▮</span></div>`;
const tabs = on => `<nav class="tabs">${[['home', 'Home'], ['gates', 'Gates'], ['train', 'Train'], ['progress', 'Progress']].map(([k, n]) => `<a data-go="${k}" data-root class="${k === on ? 'on' : ''}"><i></i>${n}</a>`).join('')}</nav>`;
const hdr = (title, k) => `<div class="top"><button class="bk" data-back>←</button><div><div class="k">${k || ''}</div><div class="h2">${title}</div></div></div>`;
const wave = n => `<div class="wave">${Array.from({ length: n }, (_, i) => `<i style="height:${8 + Math.abs(Math.sin(i * 1.7)) * 30}px"></i>`).join('')}</div>`;
const pct = () => Math.min(100, st.progress);
const embers = n => Array.from({ length: n }, () => `<i class="ember" style="left:${Math.random() * 100}%;top:${60 + Math.random() * 40}%;animation-duration:${3 + Math.random() * 4}s;animation-delay:${Math.random() * 4}s"></i>`).join('');
// ================= SPLASH: the original logo, lit by fire =================
R.screens.splash = () => `${embers(26)}<div style="text-align:center;margin-top:170px"><span class="shine" id="lg" style="opacity:0;transform:scale(.8);transition:all 1.2s cubic-bezier(.2,.8,.2,1)"><img class="logo" src="${BR}/asc-logo.webp" style="width:220px"></span></div>
<p class="k" style="text-align:center;margin-top:34px;opacity:0;transition:opacity 1s 1s" id="tp">Discipline breeds freedom</p>`;
R.mount.splash = v => { requestAnimationFrame(() => { R.$('#lg', v).style.opacity = 1; R.$('#lg', v).style.transform = 'none'; R.$('#tp', v).style.opacity = 1; });
  const go = () => R.cur.name === 'splash' && R.go(st.gateOpen ? 'landing' : 'gate', {}, { root: true }); setTimeout(go, 2600); v.addEventListener('click', go, { once: true }); };
// ================= ENTER THE GATE (original layout) =================
R.screens.gate = () => `${sb()}<div class="gatecard"><img class="logo" src="${BR}/asc-logo.webp" style="width:170px">
<p class="k" style="margin-top:22px;color:var(--muted)">Private beta</p><div class="h gold" style="font-size:32px;margin-top:10px">Enter the Gate</div>
<p class="p" style="margin-top:10px">Invited testers only. Enter the beta password you were given.</p>
<label class="lbl" style="text-align:left;margin-top:18px">Beta password</label><input class="field" id="beta" type="password" autocomplete="off">
<button class="btn yel" data-act="enterGate">Enter Ascension</button>
<div class="fid" data-act="faceid"><svg width="34" height="34" viewBox="0 0 38 38" fill="none" stroke="#E9C24F" stroke-width="2.4" stroke-linecap="round"><path d="M2 11V6a4 4 0 0 1 4-4h5M27 2h5a4 4 0 0 1 4 4v5M36 27v5a4 4 0 0 1-4 4h-5M11 36H6a4 4 0 0 1-4-4v-5M13 13v3M25 13v3M19 13v9h-2M13 27c3.5 3 8.5 3 12 0"/></svg></div>
<p class="k" style="margin-top:8px;font-size:9px;color:var(--muted)">Face ID</p>
<p class="k" style="margin-top:18px;color:var(--muted)">Discipline breeds freedom</p></div><button class="link" data-act="creds" style="font-size:13px">Demo logins</button><div class="doors open"><i></i><i></i></div>`;
const openDoors = then => { const d = R.$('.view.in .doors') || R.$('.doors'); if (!d) return then(); d.classList.remove('open'); R.vib(30); setTimeout(() => { d.classList.add('open'); then(); }, 750); };
R.act.enterGate = () => { const v = R.$('#beta').value.trim().toUpperCase(); if (v !== DEMO.beta) { R.toast('That beta password isn&rsquo;t right. Tap <b>Demo logins</b>.'); R.$('#beta').animate([{ transform: 'translateX(-8px)' }, { transform: 'translateX(8px)' }, { transform: 'none' }], 300); return; }
  st.gateOpen = true; st.save(); openDoors(() => R.go('landing', {}, { root: true })); };
R.act.faceid = el => { if (!st.faceid || !st.user) { R.toast('Face ID turns on after your first sign-in.'); return; } el.classList.add('scan'); setTimeout(() => { el.classList.remove('scan'); st.gateOpen = true; st.save(); openDoors(() => routeHome()); }, 1300); };
R.act.creds = () => R.sheet(`<div class="k">Demo logins · sample only</div><div class="h2" style="margin-top:6px">Try it as a member or a coach</div>
<div class="creds">Beta password: <b>${DEMO.beta}</b><br><br>Member: <b>${DEMO.member[0]}</b><br>Password: <b>${DEMO.member[1]}</b><br><br>Coach: <b>${DEMO.coach[0]}</b><br>Password: <b>${DEMO.coach[1]}</b></div>
<p class="p" style="margin-top:12px">Sample data only. Everything stays in this browser.</p><button class="btn ghost" data-act="resetDemo">Reset demo</button><button class="btn ghost" data-close>Close</button>`);
R.act.resetDemo = () => st.reset();
// ================= LANDING (original) =================
R.screens.landing = () => `<div class="hero" style="background-image:url(${BR}/asc-hero.webp)"></div>
<p class="k" style="margin-top:-30px;position:relative">Adult human performance</p><div class="h" style="font-size:40px;margin-top:10px;position:relative">Rastamonk<br>Ascension</div>
<div class="h2" style="color:var(--gold2);margin-top:12px">Don&rsquo;t just work out. Ascend.</div>
<p style="margin-top:12px;font-size:16px;line-height:1.55">Build strength, develop martial arts skills, improve mobility and sharpen focus. Track the progress you earn.</p>
<button class="btn" data-go="signin" data-p='{"mode":"create"}'>Begin your Ascension</button><button class="link" data-go="signin" data-p='{"mode":"signin"}'>Already a member? Sign in</button>
<p class="p" style="text-align:center;font-size:13px;margin-top:10px">Free DEMO starting experience · Adults 18+</p>
<p class="k" style="margin-top:36px">You are the character</p><div class="h2" style="margin-top:8px;font-size:26px">Your next capability. Your own pace.</div>
<div class="feat">${GOALS.map(g => `<div>${g}</div>`).join('')}</div><p class="h2" style="color:var(--gold2);margin-top:28px;font-size:18px">Discipline breeds freedom.</p>`;
// ================= SIGN IN / CREATE ACCOUNT (original style) =================
R.screens.signin = ({ mode }) => `${sb()}<button class="bk" data-back style="width:40px;height:40px;border-radius:12px;border:1px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer">←</button>
<img class="logo" src="${BR}/asc-logo.webp" style="width:150px;margin-top:4px"><div class="h gold" style="text-align:center;font-size:28px;margin-top:22px">${mode === 'create' ? 'Create your account' : 'Welcome back'}</div>
<p class="p" style="text-align:center;margin-top:6px;font-size:14px">${mode === 'create' ? 'Start with a free personalised DEMO. Adults aged 18 or over.' : 'Sign in as a member or a coach.'}</p>
<button class="btn ghost" data-act="google">Continue with Google</button><div class="or">or with email</div>
<label class="lbl">Email</label><input class="field" id="em" type="email" autocomplete="username"><label class="lbl">Password</label><input class="field" id="pw" type="password" autocomplete="current-password">
<button class="btn" data-act="signin" data-mode="${mode}">${mode === 'create' ? 'Create account' : 'Sign in'}</button>
<button class="link" data-go="signin" data-p='{"mode":"${mode === 'create' ? 'signin' : 'create'}"}'>${mode === 'create' ? 'Back to sign in' : 'New here? Create an account'}</button>
<div class="row" style="gap:10px;margin-top:6px"><button class="btn ghost" style="height:44px;font-size:13px" data-act="fill" data-w="member">Fill demo member</button><button class="btn ghost" style="height:44px;font-size:13px" data-act="fill" data-w="coach">Fill demo coach</button></div>`;
R.act.fill = el => { const c = DEMO[el.dataset.w]; R.$('#em').value = c[0]; R.$('#pw').value = c[1]; };
R.act.google = () => R.sheet(`<div class="k">Sign in with Google · demo</div><div class="h2" style="margin-top:6px">Choose an account</div>
<div class="gacct" data-act="gpick" data-w="member" data-close><div class="av">M</div><div><b>Demo member</b><div class="p" style="font-size:13px">${DEMO.member[0]}</div></div></div>
<div class="gacct" data-act="gpick" data-w="coach" data-close><div class="av">C</div><div><b>Demo coach</b><div class="p" style="font-size:13px">${DEMO.coach[0]}</div></div></div><p class="p" style="font-size:12px;margin-top:10px">In the real app this opens Google&rsquo;s own sign-in.</p>`);
R.act.gpick = el => login(el.dataset.w, DEMO[el.dataset.w][0]);
R.act.signin = el => { const e = R.$('#em').value.trim().toLowerCase(), p = R.$('#pw').value;
  let role = e === DEMO.member[0] && p === DEMO.member[1] ? 'member' : e === DEMO.coach[0] && p === DEMO.coach[1] ? 'coach' : null;
  if (!role && el.dataset.mode === 'create' && /.+@.+\..+/.test(e) && p.length >= 6) { role = 'member'; st.onboarded = false; }
  if (!role) { R.toast(el.dataset.mode === 'create' ? 'Use a valid email and a 6+ character password, or tap <b>Fill demo member</b>.' : 'Email or password not recognised. Tap <b>Fill demo member</b>.'); return; }
  login(role, e); };
const login = (role, e) => { st.user = e; st.role = role; st.save(); R.toast(role === 'coach' ? 'Welcome, Coach.' : 'Welcome, Warrior.');
  if (!st.faceid) setTimeout(() => R.sheet(`<div class="h2">Turn on Face ID?</div><p class="p" style="margin-top:8px">Next time, open the Gate with a glance.</p><button class="btn" data-act="faceOn" data-close>Turn on</button><button class="btn ghost" data-close>Not now</button>`), 900);
  routeHome(); };
R.act.faceOn = () => { st.faceid = true; st.save(); R.toast('Face ID is on.'); };
const routeHome = () => st.role === 'coach' ? R.go('coach', {}, { root: true }) : st.onboarded ? R.go('home', {}, { root: true }) : R.go('onboard', {}, { root: true });
// ================= ONBOARDING =================
R.screens.onboard = () => `${sb()}<div style="height:4px;border-radius:2px;background:rgba(255,255,255,.1)"><i style="display:block;width:50%;height:100%;background:var(--gold);border-radius:2px"></i></div>
<p class="k" style="margin-top:18px">Your starting point</p><div class="h" style="margin-top:8px">Find your starting <em>point.</em></div>
<p class="p" style="margin-top:8px">Pick what you want to build. We set your first session.</p>
<div class="chips">${GOALS.map(g => `<div class="chip ${st.goals.includes(g) ? 'on' : ''}" data-act="goal" data-g="${g}">${g}</div>`).join('')}</div>
<label class="lbl">Experience</label><div class="seg">${['New', 'Some', 'Advanced'].map((n, i) => `<div class="${st.level === i ? 'on' : ''}" data-act="lvl" data-i="${i}">${n}</div>`).join('')}</div>
<label class="lbl">Train most days at</label><div class="seg">${['07:00', '12:30', '19:00'].map(n => `<div class="${st.rem.time === n ? 'on' : ''}" data-act="rtime" data-t="${n}">${n}</div>`).join('')}</div>
<button class="btn" data-act="obDone">Build my plan</button>`;
R.act.goal = el => { const g = el.dataset.g; st.goals = st.goals.includes(g) ? st.goals.filter(x => x !== g) : [...st.goals, g]; el.classList.toggle('on'); };
R.act.lvl = el => { st.level = +el.dataset.i; R.$$('[data-act=lvl]').forEach(x => x.classList.toggle('on', x === el)); };
R.act.rtime = el => { st.rem.time = el.dataset.t; R.$$('[data-act=rtime]').forEach(x => x.classList.toggle('on', x === el)); };
R.act.obDone = () => { if (!st.goals.length) { R.toast('Pick at least one goal.'); return; } st.onboarded = true; st.save(); R.toast('Plan ready. Session 04 is set for you.'); R.go('home', {}, { root: true }); };
// ================= HOME =================
R.screens.home = () => `${sb()}<p class="k">Gate ${st.gate} of 8 · demo data</p><div class="h" style="font-size:30px;margin-top:6px">Tonight&rsquo;s <em>session.</em></div>
${st.pendingUnlock ? `<button class="btn" data-go="unlock">Your coach passed Gate ${GN[st.gate - 2]} · open it</button>` : ''}
<div class="ring" id="ring" style="--p:0"><div><b id="rn">0%</b><span class="k" style="font-size:9px">to Gate ${GN[st.gate]}</span></div></div>
<div class="card" data-go="session" data-p='{"i":0}' style="cursor:pointer"><div class="k" style="font-size:10px">Session ${SESSIONS[0].n} · beginner demo</div><div class="h2" style="margin-top:6px">${SESSIONS[0].t}</div><div class="p" style="font-size:13px;margin-top:4px">${SESSIONS[0].m} min · ${SESSIONS[0].tags}</div><div class="play"></div></div>
<div class="card"><div class="k" style="font-size:10px">This week · sample trend</div><svg width="300" height="96" style="margin-top:8px"><defs><linearGradient id="tg" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#E9C24F" stop-opacity=".4"/><stop offset="1" stop-color="#E9C24F" stop-opacity="0"/></linearGradient></defs><path id="ta" fill="url(#tg)"/><path id="tl" fill="none" stroke="#E9C24F" stroke-width="3" stroke-linecap="round"/></svg></div>
${st.rem.on ? `<div class="notif"><img src="${BR}/asc-icon-192.png"><div><div class="k" style="font-size:9px">Reminder · ${st.rem.time}</div><div style="font-weight:700;margin-top:3px">Session ${SESSIONS[0].n} is set for ${st.rem.time}.</div><div class="p" style="font-size:13px">The Gate won&rsquo;t open itself.</div></div></div>` : ''}${tabs('home')}`;
R.mount.home = v => { const r = R.$('#ring', v); let p = 0; const to = pct(); const step = () => { p += (to - p) * .08; r.style.setProperty('--p', p); R.$('#rn', v).textContent = Math.round(p) + '%'; if (Math.abs(to - p) > .3 && r.isConnected) requestAnimationFrame(step); else { r.style.setProperty('--p', to); R.$('#rn', v).textContent = to + '%'; } }; requestAnimationFrame(step);
  const pts = st.trend.map((y, i) => [i * 48 + 6, 90 - y]); let n = 1; const grow = () => { n = Math.min(pts.length, n + 1); const d = pts.slice(0, n).map((q, i) => (i ? 'L' : 'M') + q[0] + ',' + q[1]).join(' '); R.$('#tl', v).setAttribute('d', d); R.$('#ta', v).setAttribute('d', d + ` L${pts[n - 1][0]},94 L6,94 Z`); if (n < pts.length) setTimeout(grow, 90); }; setTimeout(grow, 400); };
R.after = (name, v) => { R.$$('.tabs a', v).forEach(a => a.addEventListener('pointerdown', () => { const r = document.createElement('span'); r.className = 'ripple'; r.style.left = '50%'; r.style.top = '40%'; a.append(r); setTimeout(() => r.remove(), 600); })); };
// ================= GATES + AVATAR + BADGE =================
R.screens.gates = () => `${sb()}<div class="row"><div class="grow"><p class="k">Your path</p><div class="h" style="margin-top:6px">Eight <em>Gates.</em></div></div><button class="btn ghost" style="width:auto;padding:0 14px;height:44px;margin:0;font-size:13px" data-go="avatar">My character</button></div>
${GN.map((g, i) => { const s = i + 1 < st.gate ? 'done' : i + 1 === st.gate ? 'cur' : ''; return `<div class="gl ${s}" data-go="gateDetail" data-p='{"g":${i + 1}}'><b>${g}</b><span>Gate ${i + 1}</span><em>${s === 'done' ? 'PASSED' : s === 'cur' ? pct() + '%' : 'LOCKED'}</em></div>`; }).join('')}${tabs('gates')}`;
R.screens.gateDetail = ({ g }) => { const s = g < st.gate ? 'done' : g === st.gate ? 'cur' : 'lock';
  return `${sb()}${hdr('Gate ' + GN[g - 1], s === 'done' ? 'Passed' : s === 'cur' ? 'In progress · ' + pct() + '%' : 'Locked')}
${s === 'done' ? `<div class="card" style="text-align:center"><img src="${S3}/badge/f00.webp" style="width:230px"><button class="btn" data-go="badge" data-p='{"g":${g}}'>View badge in 3D</button></div>` : ''}
<div class="card"><div class="k">What it takes</div>${GATE_REQ.map((r, i) => { const d = s === 'done' || (s === 'cur' && i < 2); return `<div class="ex ${d ? 'done' : ''}"><div class="n">${d ? '✓' : i + 1}</div><div>${r}</div></div>`; }).join('')}</div>
${s === 'cur' ? `<button class="btn" data-act="requestAssess">Request Gate assessment</button><button class="btn ghost" data-go="session" data-p='{"i":0}'>Train for this Gate</button>` : s === 'lock' ? `<div class="card"><p class="p">Pass Gate ${GN[g - 2]} to open this Gate. Here&rsquo;s the badge you&rsquo;ll forge.</p><button class="btn ghost" data-go="badge" data-p='{"g":${g}}'>Preview the badge</button></div>` : ''}`; };
R.act.requestAssess = () => { st.assessRequested = true; st.save(); R.toast('Request sent. Your coach will book your assessment.'); };
R.screens.badge = ({ g }) => `${sb()}${hdr('Gate ' + GN[(g || 4) - 1] + ' badge', 'Pull it apart')}<p class="p">Drag the slider (or the badge) to break it into its six layers.</p>
<div class="seq" id="bseq" style="width:350px;height:350px;margin:6px auto 0"></div>
<input type="range" id="bx" min="0" max="100" value="0" style="width:100%;accent-color:#E9C24F;margin-top:6px"><div class="row" style="gap:10px"><button class="btn ghost" data-act="bAuto" style="margin-top:8px">Pull apart</button><button class="btn" data-act="bRebuild" style="margin-top:8px">Rebuild</button></div>`;
let BADGE = null, BLAB = null;
R.mount.badge = v => { const host = R.$('#bseq', v), names = ['Iron base plate', 'Gold rim', 'Black enamel', 'Gate seal', 'Rastamonk crest', 'Glass lens'];
  fetch(`${S3}/badge/labels.json`).then(r => r.json()).then(j => BLAB = j).catch(() => {});
  const els = names.map((n, i) => { const e = document.createElement('div'); e.className = 'lab'; e.textContent = i + 1; e.style.opacity = 0; host.append(e); return e; });
  const leg = document.createElement('div'); leg.className = 'card'; leg.style.display = 'none'; leg.innerHTML = names.map((n, i) => `<div class="ex" style="padding:8px 0"><div class="n" style="width:28px;height:28px;font-size:13px">${i + 1}</div><div>${n}</div></div>`).join(''); v.append(leg);
  BADGE = R.seq(host, `${S3}/badge`, 30, { dragPx: 260, onFrame: (k, fi) => { R.$('#bx', v).value = k * 100; leg.style.display = k > .85 ? 'block' : 'none'; if (!BLAB) return; BLAB[fi].forEach(([, x, y], i) => { els[i].style.left = (x * 350 - 12) + 'px'; els[i].style.top = (y * 350 - 12) + 'px'; els[i].style.opacity = k > .85 ? 1 : 0; }); } });
  R.$('#bx', v).addEventListener('input', e => BADGE.set(e.target.value / 100)); };
R.act.bAuto = () => BADGE && BADGE.play(1, 1600); R.act.bRebuild = () => BADGE && BADGE.play(0, 1400);
// character: the original artwork, unchanged, in a 3D frame; the Gate shows as rings of light around it
R.screens.avatar = () => `${sb()}${hdr('My character', 'You are the character')}<p class="p">Drag to tilt. Each Gate you pass adds a ring of light.</p>
<div class="avstage" id="avs"><div class="avcard" id="avc"><img src="${BR}/asc-avatar.webp" alt="Rastamonk character"><div class="glare"></div></div></div><div id="auras" style="position:relative;height:0"></div>
<div class="lvt">${[['I', 1], ['IV', 4], ['VIII', 8]].map(([n, l]) => `<div class="${l === Math.min(st.gate, 1) || (l === 1) ? '' : ''} ${l > st.gate ? 'lock' : ''}" data-act="avl" data-l="${l}">${n}</div>`).join('')}</div><p class="p" style="text-align:center;margin-top:10px;font-size:13px" id="avn"></p>`;
const showLevel = (v, l) => { R.$$('[data-act=avl]', v).forEach(x => x.classList.toggle('on', +x.dataset.l === l)); const a = R.$('#avc', v); const n = l >= 8 ? 3 : l >= 4 ? 2 : 1;
  a.querySelectorAll('.aura').forEach(x => x.remove()); for (let i = 0; i < n; i++) { const r = document.createElement('div'); r.className = 'aura'; r.style.width = r.style.height = (150 + i * 46) + 'px'; r.style.top = (78 + i * 4) + '%'; r.style.opacity = .9 - i * .2; a.append(r); }
  a.style.boxShadow = `0 40px 80px rgba(0,0,0,.6),0 0 ${20 + n * 25}px rgba(233,194,79,${.15 + n * .12})`;
  R.$('#avn', v).textContent = l <= st.gate ? `Gate ${GN[l - 1]} look · unlocked` : `Gate ${GN[l - 1]} look · preview, unlocks when you pass Gate ${GN[l - 1]}`; };
R.mount.avatar = v => { showLevel(v, 1); const s = R.$('#avs', v), c = R.$('#avc', v); let t = 0;
  s.addEventListener('pointermove', e => { const r = s.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5; c.style.transform = `rotateY(${x * 26}deg) rotateX(${-y * 20}deg)`; });
  s.addEventListener('pointerleave', () => c.style.transform = ''); const idle = () => { if (!c.isConnected) return; t += .02; if (!s.matches(':hover')) c.style.transform = `rotateY(${Math.sin(t) * 10}deg) rotateX(${Math.cos(t * .7) * 4}deg)`; requestAnimationFrame(idle); }; idle(); };
R.act.avl = el => showLevel(R.$('.view.in'), +el.dataset.l);
// ================= TRAIN + FORM CHECK =================
R.screens.train = () => `${sb()}<p class="k">Your plan · demo sessions</p><div class="h" style="margin-top:6px">Train<em>.</em></div>
${SESSIONS.map((s, i) => `<div class="card" data-go="session" data-p='{"i":${i}}' style="cursor:pointer"><div class="k" style="font-size:10px">Session ${s.n}</div><div class="h2" style="margin-top:6px">${s.t}</div><div class="p" style="font-size:13px;margin-top:4px">${s.m} min · ${s.tags}</div><div class="play"></div></div>`).join('')}
<div class="card" data-go="form" style="cursor:pointer"><div class="k">AI form check</div><div class="h2" style="margin-top:6px">Check my horse stance</div><div class="p" style="font-size:13px">Simulated in this demo · scores are estimates</div></div>${tabs('train')}`;
R.screens.session = ({ i }) => { const s = SESSIONS[i]; return `${sb()}${hdr(s.t, 'Session ' + s.n + ' · ' + s.m + ' min')}
<div class="card"><div class="k">Steps · tap when done</div>${s.ex.map((e, j) => `<div class="ex" data-act="exTick" data-j="${j + 1}"><div class="n">${j + 1}</div><div class="grow">${e}</div></div>`).join('')}</div>
<button class="btn ghost" data-go="form">AI form check</button><button class="btn" data-act="finish">Finish session</button>`; };
R.act.exTick = el => { el.classList.toggle('done'); R.$('.n', el).textContent = el.classList.contains('done') ? '✓' : el.dataset.j; };
R.act.finish = () => { st.sessions++; st.progress = Math.min(100, st.progress + 12); st.trend = [...st.trend.slice(1), Math.min(86, st.trend[st.trend.length - 1] + 6)]; st.save();
  R.toast(`Session logged · Gate ${GN[st.gate - 1]} progress ${pct()}%`); R.go('home', {}, { root: true }); };
R.screens.form = () => `${sb()}${hdr('Form check', 'AI · estimate')}<div class="cam"><svg id="sk" width="350" height="470" style="position:absolute;inset:0"></svg>
<div class="cue" id="c1" style="left:190px;top:330px;opacity:0">Knees out</div><div class="cue" id="c2" style="left:20px;top:150px;opacity:0">Guard up</div>
<div class="k" style="position:absolute;left:16px;top:14px;color:#fff;font-size:10px"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--gold);margin-right:6px"></span>Tracking · simulated</div></div>
<div class="card"><div class="k" style="font-size:10px">Technique · horse stance</div><div class="row"><div class="score" id="sc">0</div><div class="h2" style="color:var(--muted)">/ 100</div></div>
<div class="k" style="font-size:9px;margin-top:6px;letter-spacing:.14em">Estimate from your camera · not a medical or coaching judgement</div></div><button class="btn ghost" data-act="retake">Check again</button>`;
const formRun = v => { R.$('#c1', v).style.opacity = 0; R.$('#c2', v).style.opacity = 0; R.$('#sc', v).textContent = 0; setTimeout(() => R.count(R.$('#sc', v), 80 + Math.round(Math.random() * 10), 1800), 600); setTimeout(() => R.$('#c1', v).style.opacity = 1, 1500); setTimeout(() => R.$('#c2', v).style.opacity = 1, 2300); };
R.mount.form = v => { const SK = { h: [175, 90], n: [175, 140], ls: [130, 160], rs: [220, 160], le: [98, 230], re: [252, 230], lw: [130, 280], rw: [220, 280], hp: [175, 310], lh: [140, 320], rh: [210, 320], lk: [90, 400], rk: [260, 400], la: [100, 455], ra: [250, 455] };
  const B = [['h', 'n'], ['n', 'ls'], ['n', 'rs'], ['ls', 'le'], ['le', 'lw'], ['rs', 're'], ['re', 'rw'], ['n', 'hp'], ['hp', 'lh'], ['hp', 'rh'], ['lh', 'lk'], ['lk', 'la'], ['rh', 'rk'], ['rk', 'ra']];
  const svg = R.$('#sk', v), t0 = performance.now(); const tick = t => { if (!svg.isConnected) return; const s = Math.sin((t - t0) / 450) * .5 + .5, P = {};
    for (const k in SK) P[k] = [SK[k][0] + (k.includes('k') ? (k[0] === 'l' ? -1 : 1) * s * 14 : 0), SK[k][1] + (['h', 'n', 'ls', 'rs', 'le', 're', 'lw', 'rw', 'hp', 'lh', 'rh'].includes(k) ? s * 24 : 0)];
    svg.innerHTML = `<rect x="50" y="50" width="250" height="420" rx="18" fill="none" stroke="rgba(233,194,79,.5)" stroke-dasharray="10 10"/>` + B.map(([a, b]) => `<line x1="${P[a][0]}" y1="${P[a][1]}" x2="${P[b][0]}" y2="${P[b][1]}" stroke="#E9C24F" stroke-width="5" stroke-linecap="round"/>`).join('') + Object.entries(P).map(([k, p]) => `<circle cx="${p[0]}" cy="${p[1]}" r="${k === 'h' ? 24 : 7}" fill="${k === 'h' ? 'none' : '#EEEAE3'}" stroke="#FFD815" stroke-width="3"/>`).join('');
    requestAnimationFrame(tick); }; requestAnimationFrame(tick); formRun(v); };
R.act.retake = () => formRun(R.$('.view.in'));
// ================= UNLOCK CEREMONY =================
R.screens.unlock = () => `<div class="unlock"><div class="flash"></div>${embers(18)}<div class="seq" id="useq" style="width:320px;height:320px;margin:0 auto"></div>
<p class="k">Gate ${GN[st.gate - 2] || 'II'}</p><div class="h gold" style="font-size:44px;margin-top:6px">Unlocked.</div><p class="p" style="margin-top:6px">Forged, not given.</p>
<button class="btn" data-go="home" data-root style="margin-top:28px">Continue</button><button class="btn ghost" data-go="badge" data-p='{"g":4}'>Pull the badge apart</button></div>`;
R.mount.unlock = v => { R.vib(60); const u = R.seq(R.$('#useq', v), `${S3}/badge`, 30, { start: 1, drag: false }); setTimeout(() => u.play(0, 1700), 300); st.pendingUnlock = false; st.save(); };
// ================= PROGRESS / COACH REVIEW / REMINDERS =================
R.screens.progress = () => `${sb()}<p class="k">Coach review · demo data</p><div class="h" style="margin-top:6px">Your <em>progress.</em></div>
<div class="card"><div class="row"><div class="av">C</div><div class="grow"><div class="k" style="font-size:9px">Coach voice note</div><div class="p" style="font-size:13px">0:${String(st.notes[0].dur).padStart(2, '0')} · after Session 04</div></div><button class="btn" style="width:56px;height:44px;margin:0;font-size:14px" data-act="playNote">▶</button></div>${wave(40)}
<p class="p" style="font-size:13px;margin-top:10px;display:none" id="tr">&ldquo;${R.esc(st.notes[0].text)}&rdquo;</p></div>
<div class="card bars">${[['Strength', 62], ['Martial arts', 48], ['Mobility', 55], ['Focus', 70]].map(([n, v]) => `<div class="k" style="font-size:10px;color:var(--fg)">${n}</div><div class="b"><i style="width:0" data-w="${v}"></i></div>`).join('')}
<p class="p" style="font-size:12px">Sessions logged: ${st.sessions} · sample</p></div>
<div class="card"><div class="k">Reminders</div><div class="row" style="margin-top:12px"><div class="grow">Session reminders</div><div class="sw ${st.rem.on ? 'on' : ''}" data-act="remOn"></div></div>
<div class="row" style="margin-top:12px"><div class="grow">Loud mode (lock screen + sound)</div><div class="sw ${st.rem.loud ? 'on' : ''}" data-act="remLoud"></div></div>
<button class="btn ghost" data-act="testRem">Send me a test reminder</button></div>
<button class="btn ghost" data-act="logout">Sign out</button>${tabs('progress')}`;
R.mount.progress = v => setTimeout(() => R.$$('.bars i', v).forEach(i => i.style.width = i.dataset.w + '%'), 200);
R.act.playNote = () => { const w = R.$$('.view.in .wave i'); let i = 0; const tr = R.$('#tr'); if (tr) tr.style.display = 'block'; w.forEach(x => x.classList.remove('on')); const t = setInterval(() => { if (i >= w.length) { clearInterval(t); return; } w[i++].classList.add('on'); }, 70); };
R.act.remOn = el => { st.rem.on = !st.rem.on; el.classList.toggle('on'); st.save(); };
R.act.remLoud = el => { st.rem.loud = !st.rem.loud; el.classList.toggle('on'); st.save(); };
R.act.testRem = () => { R.vib([80, 60, 80]); R.toast(`<div style="display:flex;gap:10px"><img src="${BR}/asc-icon-192.png" style="width:36px;height:36px;border-radius:9px"><div><div class="k" style="font-size:9px">Rastamonk Ascension · now</div>Session ${SESSIONS[0].n} starts in 10 minutes. The Gate won&rsquo;t open itself.</div></div>`, 3600); };
R.act.logout = () => { st.user = null; st.role = null; st.save(); R.go('gate', {}, { root: true }); };
// ================= COACH =================
R.screens.coach = () => `${sb()}<p class="k">Coach · demo data</p><div class="h" style="margin-top:6px">Your <em>members.</em></div>
${st.assessRequested ? `<div class="notif"><img src="${BR}/asc-icon-192.png"><div><div class="k" style="font-size:9px">Assessment request</div><div style="font-weight:700">Demo member asked for a Gate ${GN[st.gate - 1]} assessment.</div></div></div>` : ''}
<div class="card" style="padding:4px 18px">${MEMBERS.map(m => { const g = m.id === 'you' ? st.gate : m.g, r = m.id === 'you' ? pct() : m.r; return `<div class="mem" data-go="member" data-p='{"id":"${m.id}"}'><div class="av">${m.n[0]}</div><div class="grow"><div style="font-weight:700">${m.n}</div><div class="p" style="font-size:12px">Gate ${GN[g - 1]} · last session ${m.last}</div></div><span class="pill ${r >= 80 ? 'hot' : ''}">${r >= 80 ? 'Ready' : r + '%'}</span></div>`; }).join('')}</div>
<button class="btn ghost" data-act="logout">Sign out</button>`;
R.screens.member = ({ id }) => { const m = MEMBERS.find(x => x.id === id), you = id === 'you', g = you ? st.gate : m.g, r = you ? pct() : m.r;
  return `${sb()}${hdr(m.n, 'Gate ' + GN[g - 1] + ' · ' + r + '% ready')}
<div class="card bars">${[['Strength', 62], ['Martial arts', 48], ['Mobility', 55], ['Focus', 70]].map(([n, v]) => `<div class="k" style="font-size:10px;color:var(--fg)">${n}</div><div class="b"><i style="width:${v}%"></i></div>`).join('')}</div>
<div class="card" style="text-align:center"><div class="k">Voice note</div><p class="p" style="font-size:13px;margin-top:6px">Hold to record (simulated in the demo)</p><div class="recbtn" id="rec"><i></i></div>${wave(36)}<p class="k" id="rs" style="margin-top:8px;font-size:9px">&nbsp;</p></div>
<button class="btn" data-act="pass" data-id="${id}">Pass Gate ${GN[g - 1]}</button><button class="btn ghost" data-act="nudge">Send a reminder</button>`; };
R.mount.member = (v, { id }) => { const w = R.$$('.wave i', v); let t = null, i = 0; R.hold(R.$('#rec', v), () => { i = 0; w.forEach(x => x.classList.remove('on')); R.$('#rs', v).textContent = '● Recording…'; t = setInterval(() => { if (i < w.length) w[i++].classList.add('on'); }, 90); },
  d => { clearInterval(t); R.$('#rs', v).textContent = d < .4 ? 'Hold the button to record' : `Voice note saved · 0:${String(Math.max(1, Math.round(d))).padStart(2, '0')} · sent`; if (d >= .4 && id === 'you') { st.notes = [{ dur: Math.max(1, Math.round(d)), text: 'New note from your coach (recorded in the demo).' }, ...st.notes]; st.save(); } }); };
R.act.pass = el => { if (el.dataset.id === 'you') { if (st.gate >= 8) { R.toast('All Gates passed.'); return; } st.gate++; st.progress = 10; st.pendingUnlock = true; st.assessRequested = false; st.save(); R.toast(`Gate ${GN[st.gate - 2]} passed. The member sees the unlock ceremony next time they open the app.`); } else R.toast('Sample member updated (demo).'); R.back(); };
R.act.nudge = () => R.toast('Reminder sent (demo).');
// ================= BOOT =================
R.go('splash', {}, { root: true });
