// Rastamonk Warriors Academy · clickable concept demo. Demo logins are checked in the browser only; sample data only.
const S3 = '../shared/3d', LG = '../shared/logos';
const DEMO = { parent: ['parent@warriors.demo', 'Warrior2026'], coach: ['coach@warriors.demo', 'Sensei2026'] };
const GATES = ['Awakening', 'Wind', 'Shadow', 'Dragon', 'Storm', 'Master', 'Legend', 'Ascension'];
const BELTS = [['White', '#F4F1E8'], ['Yellow', '#FFD23F'], ['Orange', '#FF9F1C'], ['Green', '#3DDC84'], ['Blue', '#2E7DFF'], ['Red', '#E5243B'], ['Brown', '#8B5A2B'], ['Black', '#141414']];
const RANKS = [['Street Initiate', 0], ['Foundation Fighter', 500], ['Wind Walker', 1200], ['Shadow Guard', 2000], ['Dragon Disciple', 3000], ['Storm Warrior', 4200], ['Master Blade', 5600], ['Legend', 7200]];
const WEAPONS = [['Training Staff', 'Balance, grip and safe spacing.'], ['Short Staff', 'Fast hands and twirls close to the body.'], ['Tonfa', 'Blocks and turns from the forearm.'], ['Jian', 'The straight sword: precise, light footwork.'],
  ['Dao', 'One-handed broadsword. Wrapping cuts, body turns, power through the waist.'], ['Twin Serpent Blades', 'Two blades moving as one: ambidextrous patterns.'], ['Titan Sword', 'A heavy two-handed discipline.'], ['Dragon Crescent', 'The final gate: a crescent polearm for the master.']];
const SKILLS = [['Front Stance', 'stance'], ['Horse Stance', 'stance'], ['Cross Stance', 'stance'], ['Back Stance', 'stance'], ['Cartwheel', 'acro'], ['Forward Roll', 'acro'], ['Backward Roll', 'acro'], ['Kip Up', 'acro'],
  ['25 Press Ups', 'conditioning'], ['25 Lunges', 'conditioning'], ['25 Straddle Leg Lifts', 'conditioning'], ['1 min Split Hold', 'conditioning']];
const st = R.store('rm-warriors-demo', {
  role: null, kid: 'ayo', present: { zara: true },
  kids: { ayo: { n: 'Ayo', c: '#FFC52E', lv: 1, xp: 120, signed: [0, 1, 2], gi: 0, certs: [], notes: [] }, mia: { n: 'Mia', c: '#2EE6FF', lv: 5, xp: 3180, signed: [0, 1, 2, 3, 4], gi: 1, certs: [1, 2, 3, 4], notes: [] }, leo: { n: 'Leo', c: '#B8FF2C', lv: 1, xp: 40, signed: [0], gi: 0, certs: [], notes: [] } },
  pendingCert: null,
});
const ROSTER = [['ayo', 'Ayo'], ['mia', 'Mia'], ['leo', 'Leo'], ['zara', 'Zara'], ['kofi', 'Kofi']];
const K = () => st.kids[st.kid];
const sb = () => `<div class="sb"><span class="sbt">${R.clock()}</span><span>●●● ▮</span></div>`;
const hdr = (t, k) => `<div class="top"><button class="bk" data-back>←</button><div><div class="k">${k || ''}</div><div class="h2">${t}</div></div></div>`;
const tabs = on => `<nav class="tabs">${[['gates', 'My Gates'], ['training', 'My Training'], ['rewards', 'My Rewards'], ['warrior', 'My Warrior']].map(([k, n]) => `<a data-go="${k}" data-root class="${k === on ? 'on' : ''}"><i></i>${n}</a>`).join('')}</nav>`;
const rankOf = xp => { let r = 0; RANKS.forEach(([, v], i) => { if (xp >= v) r = i; }); return r; };
const avDir = lv => `${S3}/av_war${lv >= 8 ? 'black' : lv >= 5 ? 'blue' : 'white'}`;
const wave = n => `<div class="wave">${Array.from({ length: n }, (_, i) => `<i style="height:${8 + Math.abs(Math.sin(i * 1.3)) * 32}px"></i>`).join('')}</div>`;
const xpFly = (txt = '+50 XP') => { const e = document.createElement('div'); e.className = 'xpfly'; e.textContent = txt; R.$('#device').append(e); setTimeout(() => e.remove(), 1500); R.vib(30); };
// ================= ENTRY =================
R.screens.splash = () => `<div class="seq" id="forge" style="width:330px;margin:140px auto 0"></div><img src="${LG}/warriors-wordmark.svg" id="wm" style="width:280px;display:block;margin:0 auto;opacity:0;transition:opacity .6s">`;
R.mount.splash = v => { const f = R.seq(R.$('#forge', v), `${S3}/war_forge`, 22, { drag: false }); f.play(1, 2600, () => { R.$('#wm', v).style.opacity = 1; setTimeout(() => R.cur.name === 'splash' && R.go('landing', {}, { root: true }), 1200); }); v.addEventListener('click', () => R.go('landing', {}, { root: true }), { once: true }); };
R.screens.landing = () => `${sb()}<img src="${LG}/warriors-lockup.svg" style="width:230px;display:block;margin:10px auto 0">
<div class="h" style="text-align:center;margin-top:10px">Gates. Weapons. <em>Glory.</em></div>
<button class="btn" data-go="profiles">I&rsquo;m a Warrior</button><button class="btn gold" data-go="signin" data-p='{"who":"parent"}'>Parent sign in</button>
<button class="btn ghost" data-go="signin" data-p='{"who":"coach"}'>Coach · Academy HQ</button><button class="link" data-act="creds">Demo logins</button>`;
R.act.creds = () => R.sheet(`<div class="k">Demo logins · concept only</div><div class="h2" style="margin-top:6px">Parent (user) and Coach (admin)</div>
<div class="creds">Parent: <b>${DEMO.parent[0]}</b><br>Password: <b>${DEMO.parent[1]}</b><br><br>Coach (admin): <b>${DEMO.coach[0]}</b><br>Password: <b>${DEMO.coach[1]}</b><br><br>Kids: tap &ldquo;I&rsquo;m a Warrior&rdquo;, no password.</div>
<p class="p" style="margin-top:12px">Sample data only, saved in this browser. Coach actions show up in the Warrior and Parent views. <a href="#" data-act="resetDemo" style="color:var(--gold)">Reset demo</a></p><button class="btn ghost" data-close>Close</button>`);
R.act.resetDemo = () => st.reset();
R.screens.signin = ({ who }) => `${sb()}${hdr(who === 'coach' ? 'Academy HQ' : 'Parent portal', who === 'coach' ? 'Owner and coach sign-in' : 'One account for the whole family')}
<label class="lbl">Email</label><input class="field" id="em" type="email" autocomplete="username"><label class="lbl">Password</label><input class="field" id="pw" type="password" autocomplete="current-password">
<button class="btn ${who === 'coach' ? 'cyan' : ''}" data-act="signin" data-who="${who}">Sign in</button><button class="btn ghost" data-act="fill" data-who="${who}">Fill demo ${who}</button>`;
R.act.fill = el => { const c = DEMO[el.dataset.who]; R.$('#em').value = c[0]; R.$('#pw').value = c[1]; };
R.act.signin = el => { const who = el.dataset.who, c = DEMO[who]; if (R.$('#em').value.trim().toLowerCase() !== c[0] || R.$('#pw').value !== c[1]) { R.toast('Not recognised. Tap <b>Fill demo ' + who + '</b>.'); return; }
  st.role = who; st.save(); R.toast(who === 'coach' ? 'Welcome to Academy HQ.' : 'Welcome back.'); R.go(who === 'coach' ? 'hq' : 'parent', {}, { root: true }); };
R.screens.profiles = () => `${sb()}<img src="${LG}/warriors-mark.svg" style="width:120px;display:block;margin:20px auto 0"><div class="h" style="text-align:center;margin-top:10px">Who&rsquo;s training<br><em>today?</em></div>
<div class="row" style="justify-content:space-around;margin-top:30px">${Object.entries(st.kids).map(([id, k]) => `<div class="prof" data-act="pick" data-id="${id}"><div class="av" style="background:${k.c}">${k.n[0]}</div><div class="h2" style="margin-top:8px;font-size:20px">${k.n}</div><div class="k" style="font-size:9px;color:var(--muted)">${BELTS[k.lv - 1][0]} belt</div></div>`).join('')}</div>
<p class="k" style="text-align:center;margin-top:24px;color:var(--muted)">Sample family · demo</p><button class="btn ghost" data-go="landing" data-root style="margin-top:30px">Back</button>`;
R.act.pick = el => { st.kid = el.dataset.id; st.save(); R.go('gates', {}, { root: true }); if (st.pendingCert && st.pendingCert.kid === st.kid) setTimeout(() => R.go('cert', { lv: st.pendingCert.lv, fresh: 1 }), 700); };
// ================= MY GATES =================
R.screens.gates = () => { const k = K(), r = rankOf(k.xp), nx = RANKS[r + 1], need = nx ? nx[1] : k.xp, base = RANKS[r][1];
  return `${sb()}<div class="row"><div class="mini" style="background:${k.c}">${k.n[0]}</div><div class="grow"><div class="k">${RANKS[r][0]} · sample</div><div class="h2">Gate ${k.lv} · The <em>${GATES[k.lv - 1]}</em></div></div></div>
<div class="card"><div class="row k" style="color:var(--fg)"><span class="grow">XP</span><span style="color:var(--accent)">${k.xp} / ${need}</span></div><div class="xp" style="margin-top:8px"><i style="width:${nx ? Math.round((k.xp - base) / (need - base) * 100) : 100}%"></i></div>
<div class="k" style="color:var(--muted);margin-top:8px;font-size:10px">${nx ? 'Next rank: ' + nx[0] : 'Top rank'}</div></div>
<div class="row" style="margin-top:16px"><div class="h2 grow">Gate ${k.lv} skills <em>${k.signed.length}/${SKILLS.length}</em></div><button class="btn gold" style="width:auto;height:40px;padding:0 14px;margin:0;font-size:15px" data-go="weapons">Weapons</button></div>
${SKILLS.map((s, i) => `<div class="sk ${k.signed.includes(i) ? 'on' : ''}"><div class="tk">${k.signed.includes(i) ? '✓' : ''}</div>${s[0]}<span class="tg ${s[1] === 'conditioning' ? 'c' : ''}">${s[1]}</span></div>`).join('')}
<p class="k" style="text-align:center;margin-top:12px;color:var(--muted);font-size:10px">🔒 Only your coach can sign off skills</p>
<div class="h2" style="margin-top:18px">Warrior <em>path</em></div><div class="path">${GATES.map((g, i) => `<div class="${i + 1 < k.lv ? 'done' : i + 1 === k.lv ? 'on' : ''}" data-act="gateInfo" data-i="${i}">${i + 1}</div>`).join('')}</div>${tabs('gates')}`; };
R.act.gateInfo = el => { const i = +el.dataset.i, k = K(); R.sheet(`<div class="k">Gate ${i + 1} · ${BELTS[i][0]} belt</div><div class="h">The <em>${GATES[i]}</em></div><p class="p" style="margin-top:8px">${i + 1 < k.lv ? 'Passed. Your certificate is in My Rewards.' : i + 1 === k.lv ? 'Your gate now. Train, then your coach grades you in class.' : 'Locked. Pass Gate ' + i + ' to open it.'}</p><p class="p" style="margin-top:8px">Unlocks: <b style="color:var(--fg)">${WEAPONS[i][0]}</b></p><button class="btn ghost" data-close>Close</button>`); };
// ================= WEAPONS =================
R.screens.weapons = () => { const k = K(); return `${sb()}${hdr('Weapons <em>' + k.lv + '/8</em>', 'Unlock by belt level')}<div class="wgrid">${WEAPONS.map(([n], i) => { const open = i < k.lv, [bn, bc] = BELTS[i];
  return `<div class="wc ${open ? 'open' : ''}" data-act="weapon" data-i="${i}"><span class="bl" style="background:${bc};color:${i === 0 || i === 1 ? '#120B33' : '#fff'}">LV${i + 1} · ${bn}</span>${i === 4 && open ? `<img src="${S3}/dao/f00.webp">` : `<div class="lk">${open ? '⚔️' : '🔒'}</div>`}<div class="nm">${n}</div></div>`; }).join('')}</div>`; };
R.act.weapon = el => { const i = +el.dataset.i, k = K(); if (i >= k.lv) { R.toast(`Complete Level ${i + 1} · ${BELTS[i][0]} belt to unlock ${WEAPONS[i][0]}.`); return; } R.go('weapon', { i }); };
R.screens.weapon = ({ i }) => `${sb()}${hdr(WEAPONS[i][0], 'LV' + (i + 1) + ' · ' + BELTS[i][0] + ' belt · unlocked')}<p class="p">${WEAPONS[i][1]}</p>
${i === 4 ? `<div class="seq" id="dseq" style="width:350px;height:350px;margin:4px auto 0"></div><input type="range" id="dx" min="0" max="100" value="0" style="width:100%;accent-color:#B8FF2C"><div class="row"><button class="btn ghost" data-act="dOpen">Pull apart</button><button class="btn" data-act="dShut">Rebuild</button></div><div class="card" id="leg" style="display:none"></div>`
  : `<div class="card" style="text-align:center;padding:40px 18px"><div style="font-size:70px">⚔️</div><p class="p">3D model for ${WEAPONS[i][0]} is made in the full build. The Dao shows how every weapon will forge and pull apart.</p></div>`}`;
let DAO = null, DLAB = null;
R.mount.weapon = (v, { i }) => { if (i !== 4) return; const host = R.$('#dseq', v), names = ['Blade · curved single edge', 'Guard · brass disc', 'Grip wrap', 'Pommel ring', 'Tassel · LV5 unlock'];
  fetch(`${S3}/dao/labels.json`).then(r => r.json()).then(j => DLAB = j).catch(() => {});
  const els = names.map((n, j) => { const e = document.createElement('div'); e.className = 'lab'; e.textContent = j + 1; e.style.opacity = 0; host.append(e); return e; });
  const leg = R.$('#leg', v); leg.innerHTML = names.map((n, j) => `<div class="ex"><div class="n">${j + 1}</div><div>${n}</div></div>`).join('');
  DAO = R.seq(host, `${S3}/dao`, 30, { dragPx: 240, onFrame: (k, fi) => { R.$('#dx', v).value = k * 100; leg.style.display = k > .85 ? 'block' : 'none'; if (!DLAB) return; DLAB[fi].forEach(([, x, y], j) => { els[j].style.left = (x * 350 - 12) + 'px'; els[j].style.top = (y * 350 - 12) + 'px'; els[j].style.opacity = k > .85 ? 1 : 0; }); } });
  R.$('#dx', v).addEventListener('input', e => DAO.set(e.target.value / 100)); setTimeout(() => DAO.play(1, 1800), 500); };
R.act.dOpen = () => DAO && DAO.play(1, 1600); R.act.dShut = () => DAO && DAO.play(0, 1400);
// ================= MY TRAINING =================
const DRILLS = ['Front stance hold · 3 × 30 s', 'Horse stance hold · 3 × 30 s', 'Forward rolls · 5', '10 press ups', 'Stretch: split hold · 1 min'];
R.screens.training = () => { const k = K(); k.drills = k.drills || []; return `${sb()}<div class="k">My training · sample</div><div class="h">Train like a <em>warrior.</em></div>
<div class="card"><div class="k">Next class</div><div class="h2" style="margin-top:4px">Kids 6&ndash;9 · Wed 17:00</div><p class="p">Main hall · bring water</p></div>
<div class="card"><div class="row"><div class="grow"><div class="k">Home drills</div><div class="h2" style="margin-top:4px">Practice <em>stars</em></div></div><div class="h2" style="color:var(--gold)">★ ${k.drills.length}</div></div>
${DRILLS.map((d, i) => `<div class="sk ${k.drills.includes(i) ? 'on' : ''}" data-act="drill" data-i="${i}" style="cursor:pointer"><div class="tk">${k.drills.includes(i) ? '★' : ''}</div>${d}</div>`).join('')}
<p class="p" style="font-size:12px;margin-top:10px">Practice stars show effort at home. Skills and XP are still signed off by your coach in class.</p></div>${tabs('training')}`; };
R.act.drill = el => { const k = K(), i = +el.dataset.i; k.drills = k.drills || []; k.drills = k.drills.includes(i) ? k.drills.filter(x => x !== i) : [...k.drills, i]; st.save(); if (k.drills.includes(i)) xpFly('★ Practice star'); R.go('training', {}, { replace: true }); };
// ================= MY REWARDS =================
R.screens.rewards = () => { const k = K(), r = rankOf(k.xp); return `${sb()}<div class="card" style="text-align:center;margin-top:0"><div class="k">Warrior rank</div><div class="h" style="color:var(--gold)">${RANKS[r][0]}</div><p class="p">${k.xp} XP · ${RANKS[r + 1] ? (RANKS[r + 1][1] - k.xp) + ' XP to ' + RANKS[r + 1][0] : 'top rank'}</p></div>
<div class="h2" style="margin-top:18px">Certificates &amp; <em>badges</em></div><div class="badges">${GATES.map((g, i) => `<div class="${i + 1 < k.lv || k.certs.includes(i + 1) ? 'on' : ''}" ${i + 1 < k.lv || k.certs.includes(i + 1) ? `data-go="cert" data-p='{"lv":${i + 1}}'` : ''}>${i + 1}<small>${g}</small></div>`).join('')}</div>
<p class="p" style="font-size:12px;margin-top:8px">Tap a lit badge to see its certificate.</p>
<div class="h2" style="margin-top:18px">Monthly <em>Champions</em></div><p class="k" style="font-size:10px;color:var(--muted)">November · sample board · ranked on effort and attendance</p>
<div class="pod"><div style="height:150px;background:linear-gradient(#C9D3E8,#8F9AB8);animation-delay:.2s"><span class="b" style="background:#2EE6FF">M</span>2</div><div style="height:210px;background:linear-gradient(#FFE07A,#FFC52E)"><span class="b" style="background:#FFC52E">A</span>1</div><div style="height:115px;background:linear-gradient(#FFB27A,#E07A3A);animation-delay:.35s"><span class="b" style="background:#B8FF2C">L</span>3</div></div>${tabs('rewards')}`; };
R.screens.cert = ({ lv, fresh }) => { const k = K(), [bn, bc] = BELTS[Math.min(7, lv)] || BELTS[0];
  return `${sb()}${hdr('Belt <em>day</em>', 'Certificate · Gate ' + lv)}<div class="cert"><img src="${LG}/warriors-mark.svg" style="width:100px"><div class="k" style="color:#6a5cc4">Certificate of grading</div>
<div class="h" style="color:#120B33;margin-top:6px">${R.esc(k.n)}</div><div class="k" style="color:#8a7f60;font-size:10px">Sample name</div><p style="font:600 16px Baloo;margin-top:10px">has passed <b>Gate ${lv} · The ${GATES[lv - 1]}</b><br>and earned the</p>
<div class="h" style="color:${bc === '#F4F1E8' ? '#8a7f60' : bc};font-size:34px;margin-top:4px">${bn} belt</div><div class="belt" style="background:${bc}"></div><div class="k" style="color:#8a7f60;margin-top:24px;font-size:10px">Signed by your coach · demo</div></div>
<button class="btn" data-act="shareCert">Share with family</button>`; };
R.mount.cert = (v, { fresh }) => { R.confetti(R.$('#device'), ['#B8FF2C', '#FFC52E', '#2EE6FF', '#7B5CFF']); R.vib(40); if (fresh) { st.pendingCert = null; st.save(); } };
R.act.shareCert = () => R.toast('Sent to the Parent portal (demo).');
// ================= MY WARRIOR =================
const GIS = ['#F7F3EA', '#2EE6FF', '#FFC52E', '#B8FF2C', '#7B5CFF'];
R.screens.warrior = () => { const k = K(), r = rankOf(k.xp); return `${sb()}<div class="k">My warrior</div><div class="h">${R.esc(k.n)} the <em>${RANKS[r][0].split(' ')[1] || 'Warrior'}</em></div>
<div class="card" style="padding:6px;overflow:hidden"><div id="aura" style="position:absolute;inset:0;background:radial-gradient(50% 45% at 50% 55%,${GIS[k.gi]}55,transparent 70%)"></div><div class="seq" id="aseq" style="width:300px;height:400px;margin:0 auto"></div></div>
<p class="p" style="text-align:center;font-size:13px">Drag to turn your warrior</p>
<label class="lbl">Gi glow</label><div class="row" style="gap:10px;margin-top:8px">${GIS.map((c, i) => `<div class="swatch ${k.gi === i ? 'on' : ''}" style="background:${c}" data-act="gi" data-i="${i}"></div>`).join('')}</div>
<label class="lbl">Belt · set by your rank</label><div class="card" style="margin-top:8px;font:400 22px Lilita">${BELTS[k.lv - 1][0]} belt · Gate ${k.lv}</div>${tabs('warrior')}`; };
R.mount.warrior = v => R.seq(R.$('#aseq', v), avDir(K().lv), 10, { start: .5, dragPx: 160 });
R.act.gi = el => { const k = K(); k.gi = +el.dataset.i; st.save(); R.$$('.swatch').forEach(s => s.classList.toggle('on', s === el)); R.$('#aura').style.background = `radial-gradient(50% 45% at 50% 55%,${GIS[k.gi]}55,transparent 70%)`; };
// ================= PARENT PORTAL =================
R.screens.parent = () => `${sb()}<div class="k">Parent portal · sample family</div><div class="h">Your <em>warriors</em></div>
${['ayo', 'mia'].map(id => { const k = st.kids[id], inClass = st.present[id]; return `<div class="card" data-go="parentKid" data-p='{"id":"${id}"}' style="cursor:pointer"><div class="row"><div class="mini" style="background:${k.c}">${k.n[0]}</div><div class="grow"><div class="h2">${k.n}</div><div class="k" style="color:var(--muted);font-size:10px">Gate ${k.lv} · The ${GATES[k.lv - 1]}</div></div>${inClass ? '<span class="live">● In class now</span>' : ''}</div>
<div class="xp" style="margin-top:12px"><i style="width:${Math.min(100, Math.round(k.signed.length / SKILLS.length * 100))}%"></i></div><div class="k" style="color:var(--muted);font-size:10px;margin-top:6px">${k.signed.length} of ${SKILLS.length} skills signed · ${k.xp} XP</div></div>`; }).join('')}
<button class="btn ghost" data-go="profiles">Open the Warrior app</button><button class="btn ghost" data-act="logout">Sign out</button>`;
R.screens.parentKid = ({ id }) => { const k = st.kids[id]; return `${sb()}${hdr(k.n, 'Gate ' + k.lv + ' · ' + BELTS[k.lv - 1][0] + ' belt')}
<div class="card"><div class="k">Attendance · sample</div><div class="row" style="gap:6px;margin-top:10px">${['M', 'W', 'F', 'M', 'W', 'F', 'M', 'W'].map((d, i) => `<div style="flex:1;height:34px;border-radius:9px;background:${i % 4 === 3 ? 'rgba(255,255,255,.08)' : 'rgba(184,255,44,.35)'};display:flex;align-items:center;justify-content:center;font:800 11px Baloo">${d}</div>`).join('')}</div></div>
<div class="card"><div class="k">Latest from the coach</div>${k.notes.length ? `<div class="row" style="margin-top:8px"><div class="grow p">Voice note · ${k.notes[0].skill} · 0:${String(k.notes[0].d).padStart(2, '0')}</div><button class="btn cyan" style="width:52px;height:42px;margin:0" data-act="playNote">▶</button></div>${wave(36)}` : `<p class="p" style="margin-top:6px">No voice notes yet. Coaches add them when they grade a skill.</p>`}</div>
<div class="card"><div class="k">Skills signed</div>${SKILLS.filter((s, i) => k.signed.includes(i)).map(s => `<div class="ex"><div class="n">✓</div><div>${s[0]}</div></div>`).join('') || '<p class="p">None yet.</p>'}</div>`; };
R.act.playNote = () => { const w = R.$$('.wave i'); let i = 0; const t = setInterval(() => { if (i >= w.length) { clearInterval(t); return; } w[i++].classList.add('on'); }, 70); };
R.act.logout = () => { st.role = null; st.save(); R.go('landing', {}, { root: true }); };
// ================= ACADEMY HQ (COACH / ADMIN) =================
R.screens.hq = () => `${sb()}<div class="k" style="color:var(--cyan)">Academy HQ · coach</div><div class="h">Tonight · Kids 6&ndash;9</div><p class="p">Tap to take the register.</p>
${ROSTER.map(([id, n]) => `<div class="reg ${st.present[id] ? 'on' : ''}" data-act="mark" data-id="${id}">${n}<span class="k" style="color:var(--muted);font-size:9px">sample</span><div class="tk">${st.present[id] ? '✓' : ''}</div></div>`).join('')}
<button class="btn cyan" data-go="grade">Grade a skill</button><button class="btn ghost" data-go="belt">Belt grading</button><button class="btn ghost" data-act="logout">Sign out</button>`;
R.mount.hq = v => v.classList.add('hq');
R.act.mark = el => { const id = el.dataset.id; st.present[id] = !st.present[id]; st.save(); el.classList.toggle('on'); R.$('.tk', el).textContent = st.present[id] ? '✓' : ''; if (st.present[id] && st.kids[id]) R.toast(`${st.kids[id].n} checked in. Parent sees &ldquo;In class now&rdquo;.`); };
R.screens.grade = () => `${sb()}${hdr('Grade a skill', 'Academy HQ')}<label class="lbl">Warrior</label><div class="row" style="gap:10px;margin-top:8px">${['ayo', 'mia', 'leo'].map((id, i) => `<div class="prof" data-act="gkid" data-id="${id}" style="flex:1"><div class="av" style="width:70px;height:70px;font-size:30px;background:${st.kids[id].c};${i === 0 ? 'border-color:var(--cyan)' : ''}">${st.kids[id].n[0]}</div><div class="k" style="margin-top:6px">${st.kids[id].n}</div></div>`).join('')}</div>
<label class="lbl">Skill</label><select class="field" id="gsk">${SKILLS.map((s, i) => `<option value="${i}">${s[0]}</option>`).join('')}</select>
<div class="card" style="text-align:center"><div class="k" style="color:var(--cyan)">Voice note</div><p class="p" style="font-size:13px">Hold to record (simulated in the demo)</p><div class="recbtn" id="rec"><i></i></div>${wave(34)}<p class="k" id="rs" style="color:var(--muted);font-size:10px;margin-top:6px">&nbsp;</p></div>
<button class="btn" data-act="signoff">Sign off · award 50 XP</button>`;
let GK = 'ayo', GNOTE = 0;
R.mount.grade = v => { v.classList.add('hq'); GK = 'ayo'; GNOTE = 0; const w = R.$$('.wave i', v); let t = null, i = 0;
  R.hold(R.$('#rec', v), () => { i = 0; w.forEach(x => x.classList.remove('on')); R.$('#rs', v).textContent = '● Recording…'; t = setInterval(() => { if (i < w.length) w[i++].classList.add('on'); }, 90); }, d => { clearInterval(t); GNOTE = d >= .4 ? Math.max(1, Math.round(d)) : 0; R.$('#rs', v).textContent = GNOTE ? `Voice note saved · 0:${String(GNOTE).padStart(2, '0')}` : 'Hold the button to record'; });
  const next = st.kids[GK].signed.length < SKILLS.length ? SKILLS.findIndex((s, i) => !st.kids[GK].signed.includes(i)) : 0; R.$('#gsk', v).value = next; };
R.act.gkid = el => { GK = el.dataset.id; R.$$('[data-act=gkid] .av').forEach(a => a.style.borderColor = ''); R.$('.av', el).style.borderColor = 'var(--cyan)'; const k = st.kids[GK]; R.$('#gsk').value = Math.max(0, SKILLS.findIndex((s, i) => !k.signed.includes(i))); };
R.act.signoff = () => { const k = st.kids[GK], s = +R.$('#gsk').value; if (k.signed.includes(s)) { R.toast(`${k.n} already has ${SKILLS[s][0]} signed off.`); return; }
  k.signed.push(s); k.xp += 50; if (GNOTE) k.notes.unshift({ skill: SKILLS[s][0], d: GNOTE }); st.save(); xpFly('+50 XP'); R.toast(`${SKILLS[s][0]} signed off for ${k.n}. Parent and Warrior app updated.`); };
R.screens.belt = () => `${sb()}${hdr('Belt grading', 'Academy HQ')}<p class="p">Pass a warrior to their next Gate. They get a certificate and belt ceremony in their app.</p>
${['ayo', 'mia', 'leo'].map(id => { const k = st.kids[id]; return `<div class="card"><div class="row"><div class="mini" style="background:${k.c}">${k.n[0]}</div><div class="grow"><div class="h2">${k.n}</div><div class="k" style="color:var(--muted);font-size:10px">Gate ${k.lv} · ${BELTS[k.lv - 1][0]} belt · ${k.signed.length}/${SKILLS.length} skills</div></div>
<button class="btn gold" style="width:auto;height:44px;padding:0 14px;margin:0;font-size:15px" data-act="passGate" data-id="${id}">Pass</button></div></div>`; }).join('')}`;
R.mount.belt = v => v.classList.add('hq');
R.act.passGate = el => { const k = st.kids[el.dataset.id]; if (k.lv >= 8) { R.toast('Already at the final Gate.'); return; } k.certs.push(k.lv); k.lv++; k.xp += 200; st.pendingCert = { kid: el.dataset.id, lv: k.lv - 1 }; st.save(); xpFly('+200 XP');
  R.toast(`${k.n} passed Gate ${k.lv - 1}. Their certificate waits in the Warrior app.`); R.go('belt', {}, { replace: true }); };
// ================= BOOT =================
R.go('splash', {}, { root: true });
