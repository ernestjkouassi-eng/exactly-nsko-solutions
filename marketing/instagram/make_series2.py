# NSKO Solutions Instagram, series 2: 12 posts in new formats (games, carousels, myths, diary, polls,
# word of the week, code explained, fail-safe map, humour, guess-the-machine). 1080x1350.
# python3 make_series2.py  -> writes _s*.html, then render with render_series2.js
import base64, os
D = os.path.dirname(os.path.abspath(__file__)) + '/'
A = '/home/user/nsko-solutions/assets-src/'; P = '/home/user/nsko-solutions/public/'
def b64(path, mt): return f'data:{mt};base64,' + base64.b64encode(open(path, 'rb').read()).decode()
IMG = {k: b64(A + k + '.png', 'image/png') for k in ['hero', 'heroL', 'heroR', 'droneX', 'surgery', 'sweeps']}
LOCK = b64('/home/user/nsko-solutions/brand/logo/nsko-solutions-lockup-white.svg', 'image/svg+xml')
CSS = f'''@font-face{{font-family:I;src:url({b64(P+'fonts/Inter.woff2','font/woff2')});font-weight:100 900}}
@font-face{{font-family:M;src:url({b64(P+'fonts/JetBrainsMono-500.woff2','font/woff2')})}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1080px;height:1350px;background:#0A0A0B;color:#F5F5F2;font-family:I;overflow:hidden;position:relative}}
em{{font-style:normal;color:#E8541A}}
.k{{font:500 22px M;letter-spacing:.2em;text-transform:uppercase;color:#E8541A}}
h1{{font-weight:900;text-transform:uppercase;letter-spacing:-.045em;line-height:.9;font-size:112px}}
h2{{font-weight:900;text-transform:uppercase;letter-spacing:-.04em;line-height:.92;font-size:64px}}
p.t{{font-size:33px;line-height:1.38;color:#d6d9de}}
.top{{position:absolute;left:72px;right:72px;top:60px;display:flex;justify-content:space-between;align-items:center;z-index:5}}
.top img{{height:50px}}.top span{{font:500 20px M;letter-spacing:.2em;color:#8A8F98}}
.foot{{position:absolute;left:72px;right:72px;bottom:58px;display:flex;justify-content:space-between;font:500 19px M;letter-spacing:.18em;color:#8A8F98;text-transform:uppercase;z-index:5}}
.foot b{{color:#F5F5F2;font-weight:500}}
.corner{{position:absolute;width:44px;height:44px;border:2px solid rgba(245,245,242,.55);z-index:5}}.c1{{left:40px;top:40px;border-right:0;border-bottom:0}}.c2{{right:40px;bottom:40px;border-left:0;border-top:0}}
.tag{{display:inline-block;font:500 16px M;letter-spacing:.16em;border:1px solid rgba(245,245,242,.4);padding:8px 12px;border-radius:4px;color:#d6d9de;text-transform:uppercase}}
.swipe{{font:500 20px M;letter-spacing:.2em;color:#E8541A;text-transform:uppercase}}
.abs{{position:absolute}}
.grid{{position:absolute;inset:0;background-image:linear-gradient(rgba(245,245,242,.045) 1px,transparent 1px),linear-gradient(90deg,rgba(245,245,242,.045) 1px,transparent 1px);background-size:54px 54px}}
.glow{{position:absolute;inset:0;background:radial-gradient(70% 50% at 80% 10%,rgba(232,84,26,.16),transparent 70%)}}
.ring{{position:absolute;width:96px;height:96px;margin:-48px 0 0 -48px;border:4px solid #E8541A;border-radius:50%;box-shadow:0 0 0 8px rgba(232,84,26,.18),0 0 30px rgba(232,84,26,.5)}}
.ring b{{position:absolute;left:62px;top:-30px;width:46px;height:46px;border-radius:50%;background:#E8541A;color:#0A0A0B;font:800 26px/46px I;text-align:center}}
.box{{position:absolute;border:3px solid #E8541A}}.box span{{position:absolute;left:-3px;top:-36px;background:#E8541A;color:#0A0A0B;font:500 18px/34px M;padding:0 10px;letter-spacing:.06em;white-space:nowrap}}
pre{{font:500 27px/1.6 M;color:#dbe7f7;background:rgba(20,21,24,.9);border:1px solid rgba(245,245,242,.16);border-radius:14px;padding:30px 32px;white-space:pre-wrap}}
pre i{{color:#8A8F98;font-style:normal}}pre em{{color:#E8541A}}pre u{{text-decoration:none;background:rgba(232,84,26,.22);border-radius:4px;padding:0 4px}}
.card{{border:1px solid rgba(245,245,242,.18);border-radius:16px;background:rgba(255,255,255,.035);padding:34px 36px}}
'''
def page(n, total, body, slide=None, foot=''):
    num = f'{n:02d} / 22' + (f' · {slide}' if slide else '')
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{body}'
            f'<i class="corner c1"></i><i class="corner c2"></i><div class="top"><img src="{LOCK}"><span>{num}</span></div>'
            f'<div class="foot"><span>{foot}</span><b>nskosolutions.co.uk</b></div></body></html>')
def photo(key, x, y, w, h, iw, ih, ox, oy, extra=''):
    # draw image (natural 2688x1520 scaled to iw x ih) inside a box, offset ox,oy
    return f'<div class="abs" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;overflow:hidden;{extra}"><img src="{IMG[key]}" style="position:absolute;left:{-ox}px;top:{-oy}px;width:{iw}px;height:{ih}px"></div>'
S = {}  # name -> html
# ---------- 11 · Spot the bug (3 slides) ----------
iw, ih = 1521, 860; ox = int(.6 * iw - 540)
def bugimg(rings=False):
    r = ''
    if rings:
        for i, (fx, fy) in enumerate([(.593, .055), (.55, .47), (.905, .13), (.74, .66)], 1):
            r += f'<i class="ring" style="left:{fx*iw-ox:.0f}px;top:{fy*ih+140:.0f}px"><b>{i}</b></i>'
    return photo('sweeps', 0, 140, 1080, 860, iw, ih, ox, 0) + '<div class="abs" style="left:0;top:140px;width:1080px;height:860px;background:linear-gradient(0deg,#0A0A0B 0%,rgba(10,10,11,0) 30%)"></div>' + r
S['11-1'] = page(11, 3, bugimg() + '''<div class="abs" style="left:72px;right:72px;top:880px"><p class="k">Game · NSKO Secure</p><h1 style="margin-top:16px">Spot the <em>bug.</em></h1>
<p class="t" style="margin-top:22px">There are four places in this room where a listening device could hide. Guess, then swipe.</p></div>''', '1/3', 'Concept visual')
S['11-2'] = page(11, 3, bugimg(True) + '''<div class="abs" style="left:72px;right:72px;top:900px"><p class="k">The answer</p>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px 40px;margin-top:22px;font:700 36px I;letter-spacing:-.01em">
<div><em>1</em>&nbsp; Smoke alarm</div><div><em>2</em>&nbsp; Plant pot</div><div><em>3</em>&nbsp; Ceiling light</div><div><em>4</em>&nbsp; Under the table</div></div>
<p class="t" style="margin-top:24px;font-size:28px">Common hiding places, not a real find. Chargers and power strips are high on the list too.</p></div>''', '2/3', 'Concept visual')
S['11-3'] = page(11, 3, '''<div class="grid"></div><div class="glow"></div><div class="abs" style="left:72px;right:72px;top:300px">
<p class="k">NSKO Secure · TSCM sweeps</p><h1 style="margin-top:20px;font-size:120px">We check<br>every one<br>of <em>them.</em></h1>
<p class="t" style="margin-top:40px">A sweep covers the room, the network, the phones and the power. Ceiling to carpet.</p>
<p class="t" style="margin-top:24px;color:#8A8F98;font-size:28px">Sweeps are only for spaces you own or control.</p>
<p class="swipe" style="margin-top:56px">Book a sweep → link in bio</p></div>''', '3/3', 'NSKO Secure')
# ---------- 12 · What the machine sees ----------
iw2, ih2 = 1080, 611; oy2 = 25
def surg(y, boxes):
    h = photo('surgery', 0, y, 1080, 560, iw2, ih2, 0, oy2, 'filter:' + ('none' if not boxes else 'grayscale(1) brightness(.6) contrast(1.2)'))
    if boxes:
        h += f'<div class="abs" style="left:0;top:{y}px;width:1080px;height:560px;background:repeating-linear-gradient(0deg,rgba(232,84,26,.06) 0 2px,transparent 2px 6px)"></div>'
        for (X0, Y0, X1, Y1, lab) in [(415, 128, 648, 262, 'MONITOR 0.96'), (728, 118, 978, 262, 'DISPLAY 0.93'), (62, 70, 560, 505, 'ROBOT ARM 0.98'), (288, 180, 482, 470, 'PERSON 0.99')]:
            h += f'<div class="box" style="left:{X0}px;top:{Y0 + y}px;width:{X1 - X0}px;height:{Y1 - Y0}px"><span>{lab}</span></div>'
    return h
S['12'] = page(12, 1, surg(130, False) + surg(700, True) + '''
<div class="abs" style="left:72px;top:150px"><span class="tag" style="background:rgba(10,10,11,.7)">What you see</span></div>
<div class="abs" style="left:72px;top:1210px"><span class="tag" style="background:#E8541A;color:#0A0A0B;border-color:#E8541A">What the machine sees</span></div>
<div class="abs" style="right:72px;top:150px;text-align:right"><span class="tag" style="background:rgba(10,10,11,.7)">Concept · simulated overlay</span></div>
<div class="abs" style="left:0;right:0;top:690px;height:3px;background:#E8541A;box-shadow:0 0 24px #E8541A"></div>''', None, 'Perception, explained')
# ---------- 13 · 3 myths about AI (4 slides) ----------
S['13-1'] = page(13, 4, '''<div class="grid"></div><div class="glow"></div><div class="abs" style="left:72px;right:72px;top:330px">
<p class="k">Myth vs fact</p><h1 style="margin-top:20px;font-size:150px">3 myths<br>about <em>AI.</em></h1>
<p class="t" style="margin-top:40px">Number two is the one we hear most.</p><p class="swipe" style="margin-top:60px">Swipe →</p></div>''', '1/4', 'Myth vs fact')
for i, (m, f) in enumerate([('AI means chatbots.', 'The AI that matters most is invisible. It sits inside machines, deciding what to do next, many times a second.'),
                            ('Robots replace people.', 'Good robots take the dull, dirty and dangerous jobs. People still make the calls.'),
                            ('Build the hardware first.', 'Start with the brain. Simulate it, test it, break it safely. Then choose the body.')], 2):
    S[f'13-{i}'] = page(13, 4, f'''<div class="grid"></div><div class="abs" style="left:72px;right:72px;top:250px">
<p class="k" style="color:#8A8F98">Myth 0{i-1}</p><h2 style="margin-top:18px;font-size:76px;color:#8A8F98;text-decoration:line-through;text-decoration-color:#E8541A;text-decoration-thickness:8px">{m}</h2>
<div style="height:3px;background:#E8541A;width:120px;margin:70px 0 50px"></div>
<p class="k">Fact</p><p style="margin-top:22px;font:800 56px/1.12 I;letter-spacing:-.02em">{f}</p></div>''', f'{i}/4', 'Myth vs fact')
# ---------- 14 · A delivery robot's diary ----------
diary = [('06:00', 'Woke up. Battery full. Ready.'), ('06:02', 'A trolley is parked in my corridor. Planned a new route.'), ('06:03', 'Said &ldquo;excuse me&rdquo; to Dave.<br>Dave did not move.'),
         ('06:04', 'Went around Dave.'), ('07:30', 'Every delivery done. Nobody said thank you.'), ('07:31', 'That&rsquo;s fine. I&rsquo;m a robot.')]
rows = ''.join(f'<div style="display:flex;gap:34px;padding:20px 0;border-bottom:1px solid rgba(245,245,242,.12)"><span style="font:500 26px M;color:#E8541A;padding-top:6px">{t}</span><span style="font:500 34px/1.35 I;color:#E7E8EA">{x}</span></div>' for t, x in diary)
S['14'] = page(14, 1, f'''<div class="glow"></div><div class="abs" style="left:72px;right:72px;top:190px"><p class="k">A short story · fiction</p>
<h2 style="margin-top:16px;font-size:80px">A delivery robot&rsquo;s <em>diary.</em></h2><div style="margin-top:34px">{rows}</div>
<p class="t" style="margin-top:30px;font-size:27px;color:#8A8F98">The &ldquo;go around Dave&rdquo; part is route planning. We write that.</p></div>''', None, 'Robot diaries · 01')
# ---------- 15 · This or that (poll) ----------
S['15'] = page(15, 1, '''<div class="abs" style="left:0;top:0;width:1080px;height:675px;background:linear-gradient(160deg,#1C1D21,#0A0A0B)"></div>
<div class="abs" style="left:0;top:675px;width:1080px;height:675px;background:#E8541A"></div>
<div class="abs" style="left:72px;right:72px;top:190px"><p class="k">This or that · vote in the comments</p><p style="font:900 46px I;letter-spacing:-.03em;text-transform:uppercase;margin-top:18px;color:#8A8F98">Which robot do you want first?</p>
<p style="font:900 30px M;margin-top:70px;color:#E8541A">A</p><h1 style="font-size:104px;margin-top:4px">One that does<br>the dishes.</h1></div>
<div class="abs" style="left:540px;top:640px;width:72px;height:72px;margin-left:-36px;border-radius:50%;background:#0A0A0B;border:3px solid #F5F5F2;font:800 26px/66px I;text-align:center;z-index:3">OR</div>
<div class="abs" style="left:72px;right:72px;top:770px;color:#0A0A0B"><p style="font:900 30px M">B</p><h1 style="font-size:104px;margin-top:4px">One that does<br>the paperwork.</h1>
<p style="font:600 30px I;margin-top:34px">Comment A or B. We&rsquo;ll share what you picked.</p></div>''', None, 'This or that')
# ---------- 16 · Word of the week ----------
S['16'] = page(16, 1, '''<div class="grid"></div><div class="abs" style="left:72px;right:72px;top:230px"><p class="k">Word of the week · 01</p>
<h1 style="margin-top:26px;font-size:128px;text-transform:none;letter-spacing:-.05em">sensor<br>fusion<em>.</em></h1>
<p style="font:500 28px M;color:#8A8F98;margin-top:28px">/ˈsen.sər ˈfjuː.ʒən/ &nbsp;·&nbsp; noun</p>
<p style="font:800 46px/1.2 I;letter-spacing:-.02em;margin-top:50px">Blending readings from several sensors that each lie a little, to get one answer you can <em>trust.</em></p>
<div class="card" style="margin-top:56px"><p class="k" style="font-size:18px">In a sentence</p><p class="t" style="margin-top:14px;font-size:30px">GPS says you&rsquo;re here. The motion sensor says you&rsquo;re there. Sensor fusion says: you&rsquo;re probably right about here.</p></div></div>''', None, 'Word of the week')
# ---------- 17 · Code that says no (4 slides) ----------
code = '''<i>// trust.ts · every order is checked</i>
<em>if</em> (!verify(cmd.sig, fleetKey))
  <em>return</em> reject(<u>'signature'</u>);
<em>if</em> (cmd.seq &lt;= lastSeq)
  <em>return</em> reject(<u>'replay'</u>);
<em>if</em> (!fence.contains(cmd.target))
  <em>return</em> reject(<u>'geofence'</u>);
link.onLost(() =&gt; mission.<u>returnHome</u>());'''
S['17-1'] = page(17, 4, f'''<div class="glow"></div><div class="abs" style="left:72px;right:72px;top:190px"><p class="k">Line by line · Machine Lab</p>
<h1 style="margin-top:16px;font-size:132px">Code that<br>says <em>no.</em></h1><pre style="margin-top:46px">{code}</pre>
<p class="swipe" style="margin-top:36px">Swipe: what each line means →</p></div>''', '1/4', 'Concept code')
for i, (snip, head, txt) in enumerate([
        ("<em>if</em> (!verify(cmd.sig, fleetKey))\n  <em>return</em> reject(<u>'signature'</u>);", 'Is this order <em>really</em> from us?', 'Every order carries a digital signature. If it doesn&rsquo;t check out, the drone ignores it.'),
        ("<em>if</em> (cmd.seq &lt;= lastSeq)\n  <em>return</em> reject(<u>'replay'</u>);", 'Have we seen this order <em>before?</em>', 'Someone could record a real order and play it back later. Old orders are refused.'),
        ("<em>if</em> (!fence.contains(cmd.target))\n  <em>return</em> reject(<u>'geofence'</u>);\nlink.onLost(() =&gt; mission.<u>returnHome</u>());", 'Is it <em>safe?</em> And if we lose contact?', 'Targets outside the safe zone are refused. If the link drops, it flies home on its own.')], 2):
    S[f'17-{i}'] = page(17, 4, f'''<div class="grid"></div><div class="abs" style="left:72px;right:72px;top:230px"><p class="k">Line by line · 0{i-1} / 03</p>
<pre style="margin-top:26px;font-size:30px">{snip}</pre><h2 style="margin-top:64px;font-size:74px">{head}</h2><p class="t" style="margin-top:30px;font-size:36px">{txt}</p></div>''', f'{i}/4', 'Concept code')
# ---------- 18 · Designed for the worst day ----------
fs = [('Link drops', 'Fly home on its own'), ('GPS fails', 'Hold position using camera and motion sensors'), ('Battery runs low', 'Land at the nearest safe point'), ('Order looks fake', 'Refuse it and report it')]
rows = ''.join(f'''<div style="display:grid;grid-template-columns:380px 60px 1fr;align-items:center;padding:26px 0;border-bottom:1px solid rgba(245,245,242,.12)">
<span style="font:500 22px M;letter-spacing:.1em;text-transform:uppercase;color:#8A8F98;white-space:nowrap">If · <b style="color:#F5F5F2;font-weight:500">{a}</b></span><span style="font:700 40px I;color:#E8541A">→</span><span style="font:800 36px/1.2 I;letter-spacing:-.015em">{b}</span></div>''' for a, b in fs)
S['18'] = page(18, 1, f'''<div class="grid"></div><div class="glow"></div><div class="abs" style="left:72px;right:72px;top:210px"><p class="k">How we design · fail-safes</p>
<h1 style="margin-top:18px;font-size:112px">We design<br>for the<br><em>worst day.</em></h1><div style="margin-top:50px;border-top:1px solid rgba(245,245,242,.12)">{rows}</div>
<p class="t" style="margin-top:30px;font-size:26px;color:#8A8F98">Concept: how we&rsquo;d plan a drone&rsquo;s fail-safes before it ever flies.</p></div>''', None, 'Some systems cannot fail')
# ---------- 19 · Hard Problem Friday ----------
S['19'] = page(19, 1, '''<div class="abs" style="inset:0;background:#E8541A"></div><div class="grid" style="opacity:.6"></div>
<div class="abs" style="left:72px;right:72px;top:250px;color:#0A0A0B"><p style="font:500 22px M;letter-spacing:.2em;text-transform:uppercase">Every Friday · your turn</p>
<h1 style="margin-top:20px;font-size:168px">Hard<br>problem<br>Friday.</h1>
<p style="font:700 44px/1.25 I;letter-spacing:-.015em;margin-top:50px">Comment the hardest problem in your industry.</p>
<p style="font:500 34px/1.4 I;margin-top:22px">We&rsquo;ll pick one and sketch, in public, how we&rsquo;d solve it. No pitch. Just the thinking.</p></div>''', None, 'Bring us the hard problem')
# ---------- 20 · "Just put it over there" ----------
S['20'] = page(20, 1, photo('heroR', 380, 0, 700, 1350, 2387, 1350, 1150, 0, 'opacity:.55') + '''<div class="abs" style="left:0;top:0;width:1080px;height:1350px;background:linear-gradient(90deg,#0A0A0B 38%,rgba(10,10,11,.2) 100%)"></div>
<div class="abs" style="left:72px;right:72px;top:250px"><p class="k">The hardest instruction to teach a robot</p>
<h1 style="margin-top:30px;font-size:124px">&ldquo;Just put it<br><em>over there.</em>&rdquo;</h1>
<p class="t" style="margin-top:50px;max-width:640px">Which &ldquo;there&rdquo;? How far? On top, or next to it? People fill the gaps without thinking.</p>
<p style="font:800 40px/1.25 I;margin-top:34px;max-width:640px;letter-spacing:-.015em">Machines need every gap filled. That&rsquo;s our job.</p></div>''', None, 'Complex made real')
# ---------- 21 · Guess the machine (2 slides) ----------
S['21-1'] = page(21, 2, photo('droneX', 0, 0, 1080, 1350, 6400, 3619, int(.47 * 6400 - 540), int(.72 * 3619 - 640), 'filter:contrast(1.1)') + '''
<div class="abs" style="left:0;top:0;width:1080px;height:1350px;background:linear-gradient(0deg,rgba(10,10,11,.95) 0%,rgba(10,10,11,0) 45%)"></div>
<div class="abs" style="left:72px;right:72px;top:880px"><p class="k">Game · zoom 400%</p><h1 style="margin-top:14px;font-size:128px">Guess the<br><em>machine.</em></h1><p class="swipe" style="margin-top:28px">Answer: swipe →</p></div>''', '1/2', 'Concept visual')
S['21-2'] = page(21, 2, photo('droneX', 0, 140, 1080, 760, 1344, 760, 132, 0) + '''<div class="abs" style="left:0;top:140px;width:1080px;height:760px;background:linear-gradient(0deg,#0A0A0B 0%,rgba(10,10,11,0) 30%)"></div>
<i class="ring" style="left:500px;top:690px;width:150px;height:150px;margin:-75px 0 0 -75px"></i>
<div class="abs" style="left:72px;right:72px;top:930px"><p class="k">The answer</p><h1 style="margin-top:14px;font-size:104px">A survey <em>drone.</em></h1>
<p class="t" style="margin-top:22px">That was its camera. It feeds code that finds, tracks and scores what it sees, many times a second.</p></div>''', '2/2', 'Concept visual')
# ---------- 22 · You bring the body ----------
lines = '\\n'.join(['perceive(frame)', 'fuse(imu, gnss)', 'plan(map, a, b)', 'control(target)', 'accept(cmd)', 'returnHome()'] * 6)
S['22'] = page(22, 1, photo('hero', 0, 0, 1080, 1350, 2387, 1350, 654, 0) + '''<div class="abs" style="left:540px;top:0;width:540px;height:1350px;background:rgba(10,10,11,.72);backdrop-filter:blur(2px)"></div>
<pre class="abs" style="left:560px;top:120px;width:500px;background:none;border:0;padding:0;font-size:24px;line-height:1.9;color:rgba(232,84,26,.55)">''' + '<br>'.join(['perceive(frame)', 'fuse(imu, gnss)', 'plan(map, a, b)', 'control(target)', 'accept(cmd)', 'returnHome()'] * 5) + '''</pre>
<div class="abs" style="left:539px;top:0;width:3px;height:1350px;background:#E8541A;box-shadow:0 0 24px #E8541A"></div>
<div class="abs" style="left:72px;top:150px"><span class="tag" style="background:rgba(10,10,11,.6)">The body</span></div><div class="abs" style="left:612px;top:150px"><span class="tag" style="background:#E8541A;color:#0A0A0B;border-color:#E8541A">The brain</span></div>
<div class="abs" style="left:0;top:880px;width:1080px;height:470px;background:linear-gradient(0deg,#0A0A0B 55%,rgba(10,10,11,0))"></div>
<div class="abs" style="left:72px;right:72px;top:930px"><h1 style="font-size:84px">You bring<br>the body. We build<br>the <em>brain.</em></h1></div>''', None, 'Machine Intelligence')
for k, html in S.items(): open(D + f'_s{k}.html', 'w').write(html)
print(len(S), 'slides')
