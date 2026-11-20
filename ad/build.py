import subprocess, os
from PIL import Image, ImageDraw
A='/home/user/nsko-solutions/assets-src'; F='/home/user/nsko-solutions/node_modules/geist/dist/fonts'
SANS=f'{F}/geist-sans/Geist-Medium.ttf'; MONO=f'{F}/geist-mono/GeistMono-Medium.ttf'
W,H,FPS=1920,1080,24
# bottom gradient for legibility
g=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(g)
for y in range(H):
    a=int(max(0,(y-H*0.45)/(H*0.55))**1.4*215); d.line([(0,y),(W,y)],fill=(3,7,15,a))
g.save('grad.png')
bg=Image.new('RGB',(W,H),(5,11,22)); d=ImageDraw.Draw(bg)
for r in range(700,0,-4):
    k=1-r/700; d.ellipse([W/2-r*1.5,H/2-r,W/2+r*1.5,H/2+r],fill=(int(5+16*k*k),int(11+30*k*k),int(22+70*k*k)))
bg.save('bg.png')
def tf(name,text): open(name,'w').write(text); return name
def dt(file,font,size,x,y,t0,t1,color='white',fade=0.5):
    al=f"if(lt(t,{t0}),0,if(lt(t,{t0+fade}),(t-{t0})/{fade},if(lt(t,{t1-fade}),1,if(lt(t,{t1}),({t1}-t)/{fade},0))))"
    return f"drawtext=fontfile={font}:textfile={file}:fontsize={size}:fontcolor={color}:x={x}:y={y}:alpha='{al}':shadowcolor=black@0.5:shadowx=0:shadowy=2"
WM=f"drawtext=fontfile={MONO}:text='NSKO SOLUTIONS':fontsize=22:fontcolor=white@0.6:x=w-tw-48:y=h-th-40"
def run(cmd): subprocess.run(cmd,shell=True,check=True)
ENC=f"-r {FPS} -c:v libx264 -crf 15 -preset medium -pix_fmt yuv420p -an"
def clip(src,out,dur,texts):
    vf=f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}[v0];[v0][1:v]overlay=0:0[v1];[v1]"+",".join(texts+[WM,f"fade=t=in:st=0:d=0.35,fade=t=out:st={dur-0.35}:d=0.35"])+"[v]"
    run(f"ffmpeg -v error -y -t {dur} -i {src} -loop 1 -t {dur} -i grad.png -filter_complex \"{vf}\" -map \"[v]\" -t {dur} {ENC} {out}")
def card(out,dur,texts,img='bg.png'):
    vf=",".join([f"fps={FPS}"]+texts+[f"fade=t=in:st=0:d=0.4,fade=t=out:st={dur-0.4}:d=0.4"])
    run(f"ffmpeg -v error -y -loop 1 -t {dur} -i {img} -vf \"{vf}\" -t {dur} {ENC} {out}")
# 1 cold open
card('s1.mp4',3,[dt(tf('t1a.txt','NSKO SOLUTIONS'),MONO,34,'(w-tw)/2','h/2-60',0.3,3),dt(tf('t1b.txt','PRESENTS'),MONO,20,'(w-tw)/2','h/2+10',0.9,3,'0x7FD4FF')])
# 2 hero
clip(f'{A}/hero_src.mp4','s2.mp4',5,[dt(tf('t2a.txt','INTELLIGENT SYSTEMS'),MONO,22,120,'h-250',0.4,5,'0x7FD4FF'),dt(tf('t2b.txt','Some systems cannot fail.'),SANS,84,116,'h-205',0.7,5)])
# 3 drone
clip(f'{A}/drone_src.mp4','s3.mp4',5,[dt(tf('t3a.txt','OUR AIM'),MONO,22,120,'h-250',0.3,5,'0x7FD4FF'),dt(tf('t3b.txt','We don’t build the machine.'),SANS,78,116,'h-205',0.4,2.6),dt(tf('t3c.txt','We code the mind and the system.'),SANS,78,116,'h-205',2.7,5)])
# 4 surgery
clip(f'{A}/surgery_src.mp4','s4.mp4',5,[dt(tf('t4a.txt','HEALTHCARE'),MONO,22,120,'h-250',0.3,5,'0x7FD4FF'),dt(tf('t4b.txt','Intelligence for the operating room.'),SANS,74,116,'h-205',0.6,5),dt(tf('t4c.txt','CONCEPT VISUALISATION'),MONO,16,120,'h-88',0.9,5,'white@0.7')])
# 5 defence
clip(f'{A}/defence_src.mp4','s5.mp4',5,[dt(tf('t5a.txt','DEFENCE'),MONO,22,120,'h-250',0.3,5,'0x7FD4FF'),dt(tf('t5b.txt','The mind behind the mission.'),SANS,74,116,'h-205',0.6,5),dt(tf('t5c.txt','CONCEPT VISUALISATION'),MONO,16,120,'h-88',0.9,5,'white@0.7')])
# 6 site montage: four frames with a slow push, inside a floating browser frame
shots=['site_drone.png','site_medusa.png','site_health.png','site_nova.png']
for i,s in enumerate(shots):
    im=Image.open(s).convert('RGB').resize((1536,864)); fr=Image.open('bg.png').copy(); d=ImageDraw.Draw(fr)
    x,y=192,96; d.rounded_rectangle([x-3,y-3,x+1536+3,y+864+3],radius=22,fill=(40,70,120))
    m=Image.new('L',(1536,864),0); ImageDraw.Draw(m).rounded_rectangle([0,0,1536,864],radius=20,fill=255); fr.paste(im,(x,y),m); fr.save(f'fr{i}.png')
    vf=f"scale=2112:1188,zoompan=z='1+0.035*on/{int(1.5*FPS)}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d={int(1.5*FPS)}:s={W}x{H}:fps={FPS},"+",".join([dt(tf('t6a.txt','THE SITE · LIVE AND INTERACTIVE'),MONO,20,'(w-tw)/2','h-62',0,9,'0x7FD4FF',0.01),WM,"fade=t=in:st=0:d=0.2,fade=t=out:st=1.3:d=0.2"])
    run(f"ffmpeg -v error -y -loop 1 -t 1.5 -i fr{i}.png -vf \"{vf}\" -t 1.5 {ENC} s6_{i}.mp4")
# 7 end card
card('s7.mp4',5.5,[dt(tf('t7a.txt','Intelligent systems for a world that cannot fail.'),SANS,58,'(w-tw)/2','h/2-110',0.4,5.5),dt(tf('t7b.txt','NSKO SOLUTIONS'),MONO,34,'(w-tw)/2','h/2+10',1.0,5.5,'0x7FD4FF'),dt(tf('t7c.txt','nskosolutions.co.uk'),SANS,34,'(w-tw)/2','h/2+80',1.4,5.5),dt(tf('t7d.txt','BRING US THE HARD PROBLEM'),MONO,18,'(w-tw)/2','h-120',1.8,5.5,'white@0.7')])
segs=['s1.mp4','s2.mp4','s3.mp4','s4.mp4','s5.mp4']+[f's6_{i}.mp4' for i in range(4)]+['s7.mp4']
open('list.txt','w').write(''.join(f"file '{s}'\n" for s in segs))
run("ffmpeg -v error -y -f concat -safe 0 -i list.txt -c copy silent.mp4")
