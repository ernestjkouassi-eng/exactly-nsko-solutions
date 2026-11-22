mkdir -p /home/user/nsko-solutions/marketing/instagram && cd /home/user/nsko-solutions/marketing/instagram && python3 - <<'PY'
import base64,os
A='/home/user/nsko-solutions/assets-src/'; P='/home/user/nsko-solutions/public/'
def img(path):
    ext=path.rsplit('.',1)[1]; mt={'png':'image/png','jpg':'image/jpeg','webp':'image/webp'}[ext]
    return f'data:{mt};base64,'+base64.b64encode(open(path,'rb').read()).decode()
def font(path): return 'data:font/woff2;base64,'+base64.b64encode(open(path,'rb').read()).decode()
lock=open('/home/user/nsko-solutions/brand/logo/nsko-solutions-lockup-white.svg').read()
lockuri='data:image/svg+xml;base64,'+base64.b64encode(lock.encode()).decode()
CSS=f'''@font-face{{font-family:I;src:url({font(P+'fonts/Inter.woff2')});font-weight:100 900}}@font-face{{font-family:M;src:url({font(P+'fonts/JetBrainsMono-500.woff2')})}}
*{{margin:0;padding:0;box-sizing:border-box}}body{{width:1080px;height:1350px;background:#0A0A0B;color:#F5F5F2;font-family:I;overflow:hidden;position:relative}}
.bg{{position:absolute;inset:0;background-size:cover;background-position:center}}.sh{{position:absolute;inset:0;background:linear-gradient(0deg,rgba(10,10,11,.96) 0%,rgba(10,10,11,.55) 42%,rgba(10,10,11,.05) 70%)}}
.k{{font:500 22px M;letter-spacing:.2em;text-transform:uppercase;color:#E8541A}}h1 em{{font-style:normal;color:#E8541A}}.b p.k{{color:#E8541A;font-size:22px;margin:0 0 18px}}h1{{font-weight:900;text-transform:uppercase;letter-spacing:-.045em;line-height:.9;font-size:118px}}
.b{{position:absolute;left:72px;right:72px;bottom:150px}}.b p{{font-size:34px;line-height:1.35;color:#d6d9de;margin-top:26px;max-width:880px}}
.top{{position:absolute;left:72px;right:72px;top:64px;display:flex;justify-content:space-between;align-items:center}}.top img{{height:54px}}.top span{{font:500 20px M;letter-spacing:.2em;color:#8A8F98}}
.foot{{position:absolute;left:72px;right:72px;bottom:64px;display:flex;justify-content:space-between;font:500 20px M;letter-spacing:.18em;color:#8A8F98;text-transform:uppercase}}.foot b{{color:#F5F5F2;font-weight:500}}
.cv{{position:absolute;right:72px;top:140px;font:500 16px M;letter-spacing:.16em;border:1px solid rgba(245,245,242,.4);padding:8px 12px;border-radius:4px;color:#d6d9de}}
.corner{{position:absolute;width:44px;height:44px;border:2px solid rgba(245,245,242,.6)}}.c1{{left:40px;top:40px;border-right:0;border-bottom:0}}.c2{{right:40px;bottom:40px;border-left:0;border-top:0}}
.offers{{display:flex;gap:16px;margin-top:30px}}.offers div{{flex:1;border:1px solid rgba(245,245,242,.22);border-radius:10px;padding:18px 20px;background:rgba(10,10,11,.55)}}.offers b{{display:block;font-size:30px;font-weight:800}}.offers span{{font:500 18px M;color:#E8541A;letter-spacing:.14em}}
pre{{font:500 25px/1.55 M;color:#dbe7f7;background:rgba(10,10,11,.82);border:1px solid rgba(245,245,242,.18);border-radius:14px;padding:28px 30px;margin-top:28px;white-space:pre-wrap}}pre i{{color:#8A8F98;font-style:normal}}pre em{{color:#E8541A;font-style:normal}}
'''
def page(n,body,bg=None,concept=False,tag=''):
    bgh=f'<div class="bg" style="background-image:url({bg})"></div><div class="sh"></div>' if bg else ''
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{bgh}<i class="corner c1"></i><i class="corner c2"></i><div class="top"><img src="{lockuri}"><span>{n:02d} / 10</span></div>{"<span class=cv>CONCEPT VISUAL</span>" if concept else ""}{body}<div class="foot"><span>{tag}</span><b>nskosolutions.co.uk</b></div></body></html>'
posts=[
 (A+'hero.png',False,'<div class="b"><p class="k">NSKO Solutions</p><h1 style="font-size:150px">Complex<br>made <em>real.</em></h1><p>Intelligent systems, from the brain inside the machine to the platform that runs it.</p></div>','Engineered in Britain'),
 (A+'heroL.png',False,'<div class="b"><p class="k">Who we are</p><h1>We build<br>the body<br>and give it<br>a <em>mind.</em></h1></div>','Built by NSKO'),
 (A+'drone.png',False,'<div class="b"><p class="k">01 · Machine Intelligence</p><h1>We build<br>the <em>brain.</em></h1><p>You bring the robot, drone or machine. We build and install its AI, autonomy and control software.</p><div class="offers"><div><b>Brain Audit</b><span>2 weeks</span></div><div><b>Pilot Brain</b><span>6–8 weeks</span></div></div></div>','Service 01'),
 (A+'droneX.png',False,'<div class="b"><p class="k">02 · Prototype Lab</p><h1>Show it<br>before you<br><em>build it.</em></h1><p>A 3D digital prototype and working demo for investors and buyers, before anything is manufactured.</p><div class="offers"><div><b>Prototype Sprint</b><span>3 weeks</span></div><div><b>Investor Demo</b><span>6 weeks</span></div></div></div>','Service 02'),
 (A+'sweeps.png',True,'<div class="b"><p class="k">03 · NSKO Secure</p><h1>Find what<br>should not<br>be <em>there.</em></h1><p>Cyber security and TSCM bug sweeps, for spaces you own or control.</p><div class="offers"><div><b>Security Assessment</b><span>2 weeks</span></div><div><b>TSCM Sweep</b><span>1 day on site</span></div></div></div>','Service 03'),
 (A+'drone.png',False,'<div class="b" style="bottom:130px"><p class="k">Machine Lab · planner.rs</p><h1 style="font-size:84px">How a drone<br>chooses its <em>route.</em></h1><pre><i>// shortest safe route</i>\n<em>fn</em> plan(map: &amp;Grid, a: Node, b: Node) -&gt; Route {\n  <em>while let</em> Some(s) = open.pop() {\n    <em>if</em> s.node == b { <em>return</em> s.route(); }\n    <em>for</em> n <em>in</em> map.neighbours(s.node) {\n      <em>if</em> map.no_fly(n) { <em>continue</em>; }\n      open.push(next(n, b));\n} } }</pre></div>','We code the mind'),
 (A+'surgery.png',True,'<div class="b"><p class="k">Industries · Healthcare</p><h1>Intelligence<br>for the<br>operating <em>room.</em></h1><p>Software for hospital delivery robots, and AI that flags patients at risk.</p></div>','Software, data, simulation'),
 (A+'defence.png',True,'<div class="b"><p class="k">Industries · Government &amp; Defence</p><h1>The mind<br>behind the<br><em>mission.</em></h1><p>Secure mission and drone software, security assessments and TSCM sweeps.</p></div>','No weapons systems'),
 (None,False,'<div class="b" style="bottom:170px"><p class="k">Fund the build · Planned</p><h1 style="font-size:132px">Back our<br>first <em>robot.</em></h1><p>We plan to fund new in-house robots and prototypes through Kickstarter. Join the backer list on our site and we&rsquo;ll email you once, when the first campaign opens.</p></div>','Kickstarter · Planned'),
 (A+'heroR.png',False,'<div class="b"><p class="k">Contact</p><h1 style="font-size:132px">Bring us<br>the hard<br><em>problem.</em></h1><p>Healthcare, pharma, agriculture, government, defence, corporates and founders. Ernest replies personally.</p></div>','Complex made real.'),
]
for i,(bg,cv,body,tag) in enumerate(posts,1):
    html=page(i,body,img(bg) if bg else None,cv,tag)
    if bg is None: html=html.replace('<body>','<body style="background:radial-gradient(80% 60% at 70% 30%,#2a1a12,#0A0A0B 70%)">')
    open(f'_p{i:02d}.html','w').write(html)
print('ok')
PY
cat > /tmp/render_posts.js <<'E'
const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1080,height:1350}});const D='/home/user/nsko-solutions/marketing/instagram/';
for(let i=1;i<=10;i++){const n=String(i).padStart(2,'0');await p.goto('file://'+D+'_p'+n+'.html');await p.waitForTimeout(400);await p.screenshot({path:D+'post-'+n+'.jpg',type:'jpeg',quality:92});}await b.close()})();
E
cd /tmp && node /tmp/render_posts.js && cd /home/user/nsko-solutions/marketing/instagram && rm -f _p*.html && ls && python3 -c "
from PIL import Image
s=Image.new('RGB',(5*216,2*270))
for i in range(10): s.paste(Image.open('post-%02d.jpg'%(i+1)).resize((216,270)),((i%5)*216,(i//5)*270))
s.save('/home/user/film/posts_sheet.jpg',quality=88)"