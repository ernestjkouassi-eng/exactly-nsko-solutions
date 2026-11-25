# Builds stills/watch_design_sheet.png (1620x2880) from the two design renders + the hero still. Labels in Geist, uppercase, letterspaced.
import sys, os
from PIL import Image, ImageDraw, ImageFont
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'stills')
F = '/home/user/nsko-solutions/node_modules/geist/dist/fonts/geist-sans/Geist-%s.ttf'
def font(w, s): return ImageFont.truetype(F % w, s)
def spaced(d, xy, t, f, fill, sp=.18, anchor_center=False):
    w = sum(f.getlength(c) for c in t) + sp * f.size * (len(t) - 1); x, y = xy
    if anchor_center: x -= w / 2
    for c in t: d.text((x, y), c, font=f, fill=fill); x += f.getlength(c) + sp * f.size
W, H = 1620, 2880; im = Image.new('RGB', (W, H), (6, 8, 11)); d = ImageDraw.Draw(im)
spaced(d, (W / 2, 120), 'NSKO SOLUTIONS', font('Medium', 30), (242, 246, 250), .4, True)
spaced(d, (W / 2, 180), 'CELESTIAL TOURBILLON · ORIGINAL DESIGN', font('Regular', 26), (168, 216, 255), .3, True)
fr = Image.open(os.path.join(D, 'watch_design_front.png')).convert('RGB').resize((1300, 1300)); im.paste(fr, ((W - 1300) // 2, 260))
sd = Image.open(os.path.join(D, 'watch_design_side9.png')).convert('RGB').resize((760, 760)); im.paste(sd, (60, 1620))
notes = ['44 MM 18K ROSE GOLD OPEN CASE', 'ARC WINDOW AT 2 O’CLOCK', 'TAPERED BLUE SAPPHIRE BAGUETTES, 2 TIERS', 'AVENTURINE NIGHT-SKY FLOOR',
         'FLYING TOURBILLON AT 7, N BRIDGE', 'BLUE SUB-DIAL AT 1, NO TEXT', 'SIX GEMSTONE PLANETS', 'STEPPED DIAMOND BAGUETTE LUGS',
         'DOMED SAPPHIRE CRYSTAL', 'NSKO ENGRAVED AT 9 (LEFT)', 'BLUE LEATHER STRAP']
y = 1650
for n in notes:
    d.ellipse((880, y + 11, 888, y + 19), fill=(242, 246, 250)); spaced(d, (910, y), n, font('Regular', 25), (242, 246, 250), .12); y += 64
spaced(d, (W / 2, 2470), 'NOT A REPLICA: LAYOUT, CASE, BRIDGES AND PLANETS ARE NSKO’S OWN', font('Regular', 22), (150, 158, 168), .15, True)
spaced(d, (W / 2, 2520), 'NO MAKER NAMES, NO ZODIAC, NO DIAL TEXT', font('Regular', 22), (150, 158, 168), .15, True)
im.save(os.path.join(D, 'watch_design_sheet.png')); print('ok')
