// NSKO Office (admin). Owner only: magic link + mandatory TOTP (aal2), 30-minute session, RLS on every table.
// Only the publishable key is here. All data rules live in the database (is_owner() requires aal2).
// Sign-in never creates accounts (shouldCreateUser: false), so only the one owner account can get a link.
const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const SESSION_MIN = 30;
const sb = window.supabase.createClient('https://rluiyojdvkahfjuugqzt.supabase.co', 'sb_publishable_NJWZ-zPaMkhomhYT5ZCWFA_j09PJ0bC', {auth: {flowType: 'pkce', detectSessionInUrl: true, persistSession: true}});
const DEMO = new URLSearchParams(location.search).has('preview') && location.hostname === 'localhost';
const gmsg = t => $('#gmsg').textContent = t || '';
const show = id => ['#f-email', '#f-enrol', '#f-code'].forEach(f => $(f).hidden = f !== id);

/* ---------- sign-in ---------- */
async function boot() {
  if (DEMO) return openOffice(demoData());
  const {data: {session}} = await sb.auth.getSession();
  if (!session) { $('#gate').hidden = false; show('#f-email'); return; }
  const {data: aal} = await sb.auth.mfa.getAuthenticatorAssuranceLevel();
  if (aal.currentLevel === 'aal2') return startSession();
  $('#gate').hidden = false;
  const {data: f} = await sb.auth.mfa.listFactors(); const totp = f?.totp?.find(x => x.status === 'verified');
  if (totp) { show('#f-code'); $('#f-code').dataset.fid = totp.id; $('#c2').focus(); return; }
  const {data: en, error} = await sb.auth.mfa.enroll({factorType: 'totp', friendlyName: 'NSKO Office ' + new Date().toISOString().slice(0, 10)});
  if (error) return gmsg('Could not start two-step sign-in. ' + error.message);
  $('#qr').src = en.totp.qr_code; $('#secret').textContent = en.totp.secret; $('#f-enrol').dataset.fid = en.id; show('#f-enrol');
}
$('#f-email').addEventListener('submit', async e => { e.preventDefault(); const em = $('#em').value.trim().toLowerCase();
  const {error} = await sb.auth.signInWithOtp({email: em, options: {shouldCreateUser: false, emailRedirectTo: location.origin + '/admin'}});
  gmsg(error ? 'If this is the owner address, a link is on its way. If nothing arrives, wait a minute and try again.' : 'Check your inbox for the sign-in link. It opens this page.'); });
async function verify(fid, code) {
  const {data: ch, error: e1} = await sb.auth.mfa.challenge({factorId: fid}); if (e1) return gmsg(e1.message);
  const {error} = await sb.auth.mfa.verify({factorId: fid, challengeId: ch.id, code}); if (error) return gmsg('That code did not match. Try the newest one.');
  sessionStorage.setItem('nsko-aal2-at', Date.now()); startSession(true);
}
$('#f-enrol').addEventListener('submit', async e => { e.preventDefault(); await verify(e.target.dataset.fid, $('#c1').value.trim()); sb.rpc('log_event', {p_action: 'mfa_enrolled'}); });
$('#f-code').addEventListener('submit', e => { e.preventDefault(); verify(e.target.dataset.fid, $('#c2').value.trim()); });
$('#out').addEventListener('click', signOut);
async function signOut() { try { await sb.rpc('log_event', {p_action: 'sign_out'}); } catch {} await sb.auth.signOut(); sessionStorage.clear(); location.replace('/admin'); }

/* ---------- 30-minute session ---------- */
let deadline = 0;
async function startSession(fresh) {
  const at = +sessionStorage.getItem('nsko-aal2-at') || Date.now(); sessionStorage.setItem('nsko-aal2-at', at);
  deadline = at + SESSION_MIN * 60e3; if (Date.now() > deadline) return signOut();
  if (fresh) sb.rpc('log_event', {p_action: 'sign_in', p_detail: {ua: navigator.userAgent.slice(0, 120)}});
  $('#gate').hidden = true; $('#out').hidden = false;
  setInterval(() => { const left = deadline - Date.now(); if (left <= 0) return signOut(); $('#sess').textContent = `Session ends in ${Math.ceil(left / 60e3)} min`; }, 15e3);
  $('#sess').textContent = `Session ends in ${SESSION_MIN} min`;
  openOffice(await loadAll());
}
async function loadAll() {
  const q = (t, o = 'created_at') => sb.from(t).select('*').order(o, {ascending: false}).limit(200).then(r => r.data || []);
  const [briefs, packs, lab, projects, grants, social, todos, audit] = await Promise.all([q('briefs'), q('portfolio_requests'), q('lab_items', 'key'), q('projects', 'key'), q('grants'), q('social_drafts', 'day'), q('todos'), q('audit_log', 'at')]);
  return {briefs, packs, lab, projects, grants, social: social.reverse(), todos, audit};
}

/* ---------- the office: isometric floor plan ---------- */
const ROOMS = [
  {k: 'inbox', t: 'Reception', x: 0, y: 0, w: 4, d: 3, n: D => D.briefs.filter(b => b.state === 'new').length},
  {k: 'portfolio', t: 'Portfolio desk', x: 4, y: 0, w: 3, d: 3, n: D => D.packs.filter(p => p.state === 'new').length},
  {k: 'projects', t: 'Projects room', x: 7, y: 0, w: 3, d: 3, n: D => D.projects.length},
  {k: 'lab', t: 'Lab', x: 0, y: 3, w: 3, d: 4, n: D => D.lab.length},
  {k: 'grants', t: 'Grants office', x: 3, y: 3, w: 4, d: 2, n: D => D.grants.length + D.todos.filter(t => t.room === 'grants' && !t.done).length},
  {k: 'studio', t: 'Content studio', x: 3, y: 5, w: 4, d: 2, n: D => D.social.filter(s => s.state === 'draft').length},
  {k: 'settings', t: 'Settings', x: 7, y: 3, w: 3, d: 4, n: D => D.todos.filter(t => t.room !== 'grants' && !t.done).length},
];
const U = 46, H = 26, OX = 500, OY = 70;
const iso = (x, y, z = 0) => [OX + (x - y) * U * .866, OY + (x + y) * U * .5 - z];
const pts = a => a.map(p => p.join(',')).join(' ');
let D = null;
function openOffice(data) {
  D = data; $('#office').hidden = false; $('#gate').hidden = true;
  let h = '';
  for (const r of ROOMS) {
    const g = .12, x0 = r.x + g, y0 = r.y + g, x1 = r.x + r.w - g, y1 = r.y + r.d - g;
    const c = iso(r.x + r.w / 2, r.y + r.d / 2), n = r.n(D);
    h += `<g class="room" tabindex="0" role="button" data-room="${r.k}" aria-label="${esc(r.t)}${n ? ', ' + n + ' waiting' : ''}">
      <polygon class="wr" points="${pts([iso(x1, y0), iso(x1, y1), iso(x1, y1, -H), iso(x1, y0, -H)])}"/>
      <polygon class="wl" points="${pts([iso(x0, y1), iso(x1, y1), iso(x1, y1, -H), iso(x0, y1, -H)])}"/>
      <polygon class="fl" points="${pts([iso(x0, y0), iso(x1, y0), iso(x1, y1), iso(x0, y1)])}"/>
      <text x="${c[0]}" y="${c[1] - 4}" text-anchor="middle">${esc(r.t)}</text>
      <text class="cnt" x="${c[0]}" y="${c[1] + 14}" text-anchor="middle">${n ? n + ' waiting' : 'All clear'}</text>
      ${n && (r.k === 'inbox' || r.k === 'portfolio') ? `<circle class="live" cx="${c[0] + 72}" cy="${c[1] - 9}" r="4"/>` : ''}</g>`;
  }
  $('#plan').innerHTML = h;
  $('#rooms').innerHTML = ROOMS.map(r => `<button class="chip" data-room="${r.k}">${esc(r.t)} · ${r.n(D)}</button>`).join('');
  $$('[data-room]').forEach(el => { el.addEventListener('click', () => room(el.dataset.room)); el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); room(el.dataset.room); } }); });
}
const dlg = $('#room'); dlg.addEventListener('click', e => { if (e.target === dlg || e.target.closest('[data-close]')) dlg.close(); });
const when = t => new Date(t).toLocaleString('en-GB', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'});
const sel = (name, val, opts, id) => `<select data-${name}="${esc(id)}" aria-label="${name}">${opts.map(o => `<option ${o === val ? 'selected' : ''}>${esc(o)}</option>`).join('')}</select>`;
async function upd(t, keyCol, id, patch) { if (DEMO) return true; const {error} = await sb.from(t).update(patch).eq(keyCol, id); if (error) alert('Not saved: ' + error.message); return !error; }
const TITLES = {inbox: 'Inbox', portfolio: 'Portfolio requests', projects: 'Project labels', lab: 'Lab status', grants: 'Grants', studio: 'Social drafts', settings: 'Settings'};
function room(k) {
  const r = ROOMS.find(x => x.k === k); let h = `<p class="k" style="margin-top:12px">${esc(r.t)}</p><h2 id="rh">${esc(TITLES[k])}</h2>`;
  if (k === 'inbox') h += D.briefs.length ? `<div class="list">${D.briefs.map(b => `<div class="item"><h3>${esc(b.company || b.name)}</h3><p class="m">${esc(b.name)} · <a href="mailto:${esc(b.email)}">${esc(b.email)}</a>${b.phone ? ' · ' + esc(b.phone) : ''} · ${when(b.created_at)}</p><p class="m">${esc([b.sector, b.need, b.budget, b.timeline, b.nda ? 'NDA requested' : ''].filter(Boolean).join(' · '))}</p><p class="b">${esc(b.message)}</p><div class="row">${sel('state', b.state, ['new', 'replied', 'in_progress', 'won', 'closed'], b.id)}${b.file_path ? `<button class="btn s sm" data-file="${esc(b.file_path)}">Open attachment</button>` : ''}</div></div>`).join('')}</div>` : '<p class="empty">No briefs yet.</p>';
  if (k === 'portfolio') h += `<p class="note">Send pack marks the request approved and opens an email to the requester with the pack link, ready for you to send from your own inbox.</p>` + (D.packs.length ? `<div class="list">${D.packs.map(p => `<div class="item"><h3>${esc(p.company || p.name)}</h3><p class="m">${esc(p.name)} · ${esc(p.email)} · ${esc(p.interest || '')} · ${when(p.created_at)}</p><div class="row"><span class="tag">${esc(p.state)}</span>${p.state === 'new' ? `<button class="btn p sm" data-pack="${esc(p.id)}">Send pack</button><button class="btn s sm" data-decline="${esc(p.id)}">Decline</button>` : ''}</div></div>`).join('')}</div>` : '<p class="empty">No requests yet.</p>');
  if (k === 'projects') h += `<div class="list">${D.projects.map(p => `<div class="item"><h3>${esc(p.title)}</h3><div class="row">${sel('plabel', p.label, ['Live', 'Demo built', 'In build', 'Concept'], p.key)}<span class="m">${esc(p.note || '')}</span></div></div>`).join('')}</div>`;
  if (k === 'lab') h += `<div class="list">${D.lab.map(l => `<div class="item"><h3>${esc(l.title)}</h3><div class="row">${sel('lstatus', l.status, ['Concept', 'In build', 'Prototype built'], l.key)}</div></div>`).join('')}</div><p class="note">The website shows these labels after the next publish.</p>`;
  if (k === 'grants') h += todoList('grants') + (D.grants.length ? `<div class="list">${D.grants.map(g => `<div class="item"><h3>${esc(g.funder || '')} · ${esc(g.call_name || g.programme)}</h3><p class="m">${esc(g.programme)} · ${esc(g.amount || '')} · deadline ${esc(g.deadline || 'open')}</p>${/^https?:\/\//.test(g.url || '') ? `<p class="m"><a href="${esc(g.url)}" target="_blank" rel="noopener">Source</a></p>` : ''}<p class="b">${esc(g.notes || '')}</p><div class="row">${sel('gstatus', g.status, ['researching', 'drafting', 'approved_to_submit', 'submitted', 'won', 'lost'], g.id)}</div></div>`).join('')}</div>` : '<p class="empty">No grant calls saved yet.</p>');
  if (k === 'studio') h += `<p class="note">Drafts only. Nothing is posted from here. Approve marks a post ready for you to publish yourself.</p>` + (D.social.length ? `<div class="list">${D.social.map(s => `<div class="item"><h3>Day ${esc(s.day)} · ${esc(s.channel)}</h3><p class="b">${esc(s.caption)}</p>${s.media_path ? `<p class="m">Media: ${esc(s.media_path)}</p>` : ''}<div class="row"><span class="tag">${esc(s.state)}</span>${s.state === 'draft' ? `<button class="btn p sm" data-approve="${esc(s.id)}">Approve</button>` : ''}</div></div>`).join('')}</div>` : '<p class="empty">No drafts yet.</p>');
  if (k === 'settings') h += todoList('settings') + todoList('lab') + `<p class="k" style="margin-top:26px">Security</p><p class="note">Owner-only sign-in, two-step codes required, 30-minute sessions, every change logged.</p><p class="k" style="margin-top:20px">Recent activity</p><div class="list">${D.audit.slice(0, 15).map(a => `<div class="item"><p class="m">${when(a.at)} · ${esc(a.action)} ${esc(a.tbl || '')}</p></div>`).join('') || '<p class="empty">Nothing yet.</p>'}</div>`;
  $('#rbody').innerHTML = h; if (!dlg.open) dlg.showModal(); dlg.scrollTop = 0; wire();
}
const todoList = rm => { const t = D.todos.filter(x => x.room === rm); return t.length ? `<p class="k" style="margin-top:18px">To do</p><div class="list">${t.map(x => `<label class="check item" style="margin:0"><input type="checkbox" data-todo="${esc(x.id)}" ${x.done ? 'checked' : ''}> ${esc(x.title)}</label>`).join('')}</div>` : ''; };
function wire() {
  const b = $('#rbody'), set = (arr, key, id, patch) => Object.assign(arr.find(x => x[key] === id) || {}, patch);
  $$('[data-state]', b).forEach(s => s.onchange = async () => { if (await upd('briefs', 'id', s.dataset.state, {state: s.value})) set(D.briefs, 'id', s.dataset.state, {state: s.value}); openOffice(D); });
  $$('[data-plabel]', b).forEach(s => s.onchange = () => upd('projects', 'key', s.dataset.plabel, {label: s.value, updated_at: new Date().toISOString()}).then(ok => ok && set(D.projects, 'key', s.dataset.plabel, {label: s.value})));
  $$('[data-lstatus]', b).forEach(s => s.onchange = () => upd('lab_items', 'key', s.dataset.lstatus, {status: s.value, updated_at: new Date().toISOString()}).then(ok => ok && set(D.lab, 'key', s.dataset.lstatus, {status: s.value})));
  $$('[data-gstatus]', b).forEach(s => s.onchange = () => upd('grants', 'id', s.dataset.gstatus, {status: s.value}).then(ok => ok && set(D.grants, 'id', s.dataset.gstatus, {status: s.value})));
  $$('[data-todo]', b).forEach(c => c.onchange = () => upd('todos', 'id', c.dataset.todo, {done: c.checked}).then(ok => { if (ok) set(D.todos, 'id', c.dataset.todo, {done: c.checked}); openOffice(D); }));
  $$('[data-approve]', b).forEach(x => x.onclick = async () => { if (await upd('social_drafts', 'id', x.dataset.approve, {state: 'approved', decided_at: new Date().toISOString()})) { set(D.social, 'id', x.dataset.approve, {state: 'approved'}); room('studio'); openOffice(D); } });
  $$('[data-decline]', b).forEach(x => x.onclick = async () => { if (await upd('portfolio_requests', 'id', x.dataset.decline, {state: 'declined', decided_at: new Date().toISOString()})) { set(D.packs, 'id', x.dataset.decline, {state: 'declined'}); room('portfolio'); openOffice(D); } });
  $$('[data-pack]', b).forEach(x => x.onclick = async () => { const p = D.packs.find(q => q.id === x.dataset.pack);
    if (!(await upd('portfolio_requests', 'id', p.id, {state: 'approved', decided_at: new Date().toISOString()}))) return;
    if (!DEMO) sb.rpc('log_event', {p_action: 'send_pack_approved', p_detail: {id: p.id}});
    p.state = 'approved'; room('portfolio'); openOffice(D);
    location.href = `mailto:${encodeURIComponent(p.email)}?subject=${encodeURIComponent('NSKO Prototype Lab portfolio pack')}&body=${encodeURIComponent(`Hello ${p.name},\n\nThank you for asking about the NSKO Prototype Lab. Here is the portfolio pack:\nhttps://nskosolutions.co.uk/media/v42/nsko-portfolio-pack.pdf\n\nBuilt by NSKO.`)}`; });
  $$('[data-file]', b).forEach(x => x.onclick = async () => { const {data, error} = await sb.storage.from('briefs').createSignedUrl(x.dataset.file, 300); if (error) return alert(error.message); window.open(data.signedUrl, '_blank', 'noopener'); });
}
function demoData() { // local layout preview only (localhost + ?preview). Placeholder rows, never shipped as real data.
  const now = new Date().toISOString();
  return {briefs: [{id: '1', created_at: now, company: 'Sample Trust', name: 'Sample Person', email: 'sample@example.com', sector: 'Healthcare', need: 'Secure platform', budget: '£50k to £150k', timeline: '3 to 6 months', message: 'Sample brief text for the layout preview.', state: 'new'}],
    packs: [{id: 'p1', created_at: now, name: 'Sample Person', company: 'Sample Studio', email: 'sample@example.com', interest: 'Drones', state: 'new'}],
    lab: [{key: 'drone', title: 'Drone', status: 'Concept'}, {key: 'watch', title: 'Watch', status: 'Concept'}], projects: [{key: 'nsko', title: 'NSKO', label: 'Live', note: 'Wellness in VR'}],
    grants: [], social: [{id: 's1', day: 1, channel: 'Instagram', caption: 'Sample draft caption.', state: 'draft'}], todos: [{id: 't1', room: 'settings', title: 'Confirm company number', done: false}, {id: 't2', room: 'grants', title: 'Decide: CIC or charity', done: false}], audit: []};
}
setInterval(() => { $('#clock').textContent = new Date().toLocaleTimeString('en-GB', {hour: '2-digit', minute: '2-digit'}); }, 1000);
boot();
