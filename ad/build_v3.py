import subprocess
from PIL import Image, ImageDraw
A='/home/user/nsko-solutions/assets-src'; D='.'
SANS=f'{D}/InterBlack.ttf'; MONO=f'{D}/Mono.ttf'; FPS=24
def run(c): subprocess.run(c,shell=True,check=True)
def tf(n,t): open(n,'w').write(t); return n
def dt(file,font,size,x,y,t0,t1,color='0xF5F5F2',fade=.35):
    al=f"if(lt(t,{t0}),0,if(lt(t,{t0+fade}),(t-{t0})/{fade},if(lt(t,{t1-fade}),1,if(lt(t,{t1}),({t1}-t)/{fade},0))))"
    return f"drawtext=fontfile={font}:textfile={file}:fontsize={size}:fontcolor={color}:x={x}:y={y}:alpha='{al}':line_spacing=-{int(size*.18)}"
def build(W,H,tag):
    V=H>W; s=H/1080 if not V else W/1080
    ENC=f"-r {FPS} -c:v libx264 -crf 16 -preset medium -pix_fmt yuv420p -an"
    WM=f"drawtext=fontfile={MONO}:text='NSKO SOLUTIONS':fontsize={int(20*s)}:fontcolor=white@0.55:x=w-tw-{int(40*s)}:y=h-th-{int(36*s)}"
    g=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(g)
    for y in range(H):
        a=int(max(0,(y-H*.42)/(H*.58))**1.3*225); d.line([(0,y),(W,y)],fill=(10,10,11,a))
    g.save(f'grad_{tag}.png'); Image.new('RGB',(W,H),(10,10,11)).save(f'obs_{tag}.png')
    X=int(90*s) if not V else int(70*s)
    BIG=int((96 if not V else 92)*s); KS=int(20*s)
    def clip(src,out,ss,dur,lines,kick):
        crop=f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
        txt=[dt(tf(f'k_{out}.txt',kick),MONO,KS,X,f"h-{int((330 if not V else 520)*s)}",.25,dur,'0xE8541A')]
        y0=(H-int((290 if not V else 480)*s))
        for i,(t,a,b) in enumerate(lines): txt.append(dt(tf(f'l_{out}{i}.txt',t),SANS,BIG,X,y0,a,b))
        vf=f"[0:v]{crop},fps={FPS}[v0];[v0][1:v]overlay[v1];[v1]"+",".join(txt+[WM,f"fade=t=in:st=0:d=0.3,fade=t=out:st={dur-.3}:d=0.3"])+"[v]"
        run(f"ffmpeg -v error -y -ss {ss} -t {dur} -i {A}/{src} -loop 1 -t {dur} -i grad_{tag}.png -filter_complex \"{vf}\" -map \"[v]\" -t {dur} {ENC} {out}_{tag}.mp4")
    # 1 logo build: symbol, fragment pops (scale-in), then lockup
    lk=Image.open('lockup.png'); lw=int(W*(.62 if not V else .82)); lk=lk.resize((lw,int(lk.height*lw/lk.width))); bg=Image.open(f'obs_{tag}.png').copy(); bg.paste(lk,((W-lw)//2,(H-lk.height)//2),lk); bg.save(f'logo_{tag}.png')
    run(f"ffmpeg -v error -y -loop 1 -t 3 -i logo_{tag}.png -vf \"fps={FPS},zoompan=z='1.08-0.08*on/72':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=72:s={W}x{H}:fps={FPS},fade=t=in:st=0:d=0.6,fade=t=out:st=2.6:d=0.4\" -t 3 {ENC} s1_{tag}.mp4")
    clip('hero_src.mp4','s2',0,5,[('WE BUILD THE BODY',.4,2.6),('AND GIVE IT A MIND.',2.6,5)],'NSKO SOLUTIONS')
    clip('drone_src.mp4','s3',0,5,[('WE BUILD THE BRAIN.',.5,5)],'MACHINE INTELLIGENCE')
    clip('sweeps_src.mp4','s4',.5,4.5,[('FIND WHAT SHOULD\nNOT BE THERE.',.4,4.5)] if V else [('FIND WHAT SHOULD NOT BE THERE.',.4,4.5)],'NSKO SECURE')
    # site montage inside a frame
    shots=['s_services','s_lab','s_industries','s_projects','s_medusa']
    for i,sh in enumerate(shots):
        im=Image.open(f'{sh}.png').convert('RGB'); fw=int(W*(.8 if not V else .9)); fh=int(fw*1080/1920); im=im.resize((fw,fh))
        fr=Image.open(f'obs_{tag}.png').copy(); dd=ImageDraw.Draw(fr); x=(W-fw)//2; y=(H-fh)//2-(int(40*s) if not V else 0)
        dd.rounded_rectangle([x-2,y-2,x+fw+2,y+fh+2],radius=int(14*s),fill=(40,41,46)); m=Image.new('L',(fw,fh),0); ImageDraw.Draw(m).rounded_rectangle([0,0,fw,fh],radius=int(12*s),fill=255); fr.paste(im,(x,y),m); fr.save(f'fr{i}_{tag}.png')
        lab=tf(f'm_{i}.txt','NSKOSOLUTIONS.CO.UK  /  LIVE')
        vf=f"scale={int(W*1.08)}:{int(H*1.08)},zoompan=z='1+0.03*on/36':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d=36:s={W}x{H}:fps={FPS},"+",".join([dt(lab,MONO,KS,'(w-tw)/2',f"h-{int(110*s)}",0,9,'0xE8541A',.01),WM,"fade=t=in:st=0:d=0.15,fade=t=out:st=1.35:d=0.15"])
        run(f"ffmpeg -v error -y -loop 1 -t 1.5 -i fr{i}_{tag}.png -vf \"{vf}\" -t 1.5 {ENC} s5_{i}_{tag}.mp4")
    # end card
    lk2=Image.open('lockup.png'); lw2=int(W*(.34 if not V else .6)); lk2=lk2.resize((lw2,int(lk2.height*lw2/lk2.width))); e=Image.open(f'obs_{tag}.png').copy(); e.paste(lk2,((W-lw2)//2,int(H*.62)),lk2); e.save(f'end_{tag}.png')
    t1=tf('e1.txt',"COMPLEX\nMADE REAL."); t2=tf('e2.txt','Bring us the hard problem.  nskosolutions.co.uk'); t3=tf('e3.txt','BUILT BY NSKO.')
    vf=",".join([f"fps={FPS}",dt(t1,SANS,int((130 if not V else 120)*s),'(w-tw)/2',f"h*{.22 if not V else .26}",.3,6),dt(t2,MONO,int(22*s),'(w-tw)/2',f"h*{.52 if not V else .5}",1,6,'0xE8541A'),dt(t3,MONO,int(16*s),'(w-tw)/2',f"h-{int(90*s)}",1.4,6,'0x8A8F98'),"fade=t=in:st=0:d=0.4,fade=t=out:st=5.5:d=0.5"])
    run(f"ffmpeg -v error -y -loop 1 -t 6 -i end_{tag}.png -vf \"{vf}\" -t 6 {ENC} s6_{tag}.mp4")
    segs=[f's1_{tag}.mp4',f's2_{tag}.mp4',f's3_{tag}.mp4',f's4_{tag}.mp4']+[f's5_{i}_{tag}.mp4' for i in range(5)]+[f's6_{tag}.mp4']
    open(f'list_{tag}.txt','w').write(''.join(f"file '{x}'\n" for x in segs))
    run(f"ffmpeg -v error -y -f concat -safe 0 -i list_{tag}.txt -c copy silent_{tag}.mp4")
build(1920,1080,'h'); build(1080,1920,'v')
