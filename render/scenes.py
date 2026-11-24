# NSKO original hero scenes (Blender Cycles). Original designs, NSKO-branded, no third-party marks.
# python3 scenes.py arch|robot|wire|quad|surgical|chip|iced SIZE SPP OUT.png
import bpy, bmesh, math, os, sys, random
from mathutils import Vector
NAME, SZ, SPP, OUT = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
FONT = '/tmp/ddin-src/D-DIN-Bold.otf'
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene; random.seed(11)
def lin(h): h = h.lstrip('#'); c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]; return tuple(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c)
def mat(n, col, metal=0., rough=.5, emit=0., coat=0., trans=0., ior=1.45, disp=0.):
    m = bpy.data.materials.new(n); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*lin(col), 1); b.inputs['Metallic'].default_value = metal; b.inputs['Roughness'].default_value = rough
    if coat: b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = .04
    if emit: b.inputs['Emission Color'].default_value = (*lin(col), 1); b.inputs['Emission Strength'].default_value = emit
    if trans: b.inputs['Transmission Weight'].default_value = trans; b.inputs['IOR'].default_value = ior
    if disp and 'Dispersion' in b.inputs: b.inputs['Dispersion'].default_value = disp
    return m
SIG = mat('signal', '#E8541A', 0, .3, 6); FROSTE = mat('frostE', '#CFE0EC', 0, .3, 8); WARM = mat('warm', '#FFC27A', 0, .5, 5)
WHITE = mat('white', '#EDEDEA', 0, .35, coat=.3); BLKM = mat('blackmatte', '#101114', 0, .55); BLKG = mat('blackgloss', '#0B0B0D', .2, .2, coat=.7)
CHROME = mat('chrome', '#D6DAE0', 1, .08); GRAPH = mat('graphite', '#24272C', .5, .38); GLASSD = mat('glassdark', '#1C2A33', 0, .05, trans=.85)
LENS = mat('lens', '#05070A', .8, .04, coat=1); GOLD = mat('gold', '#E9B65A', 1, .18)
root = bpy.data.objects.new('root', None); sc.collection.objects.link(root)
def P(o, m, smooth=True, bev=0.):
    if m: o.data.materials.append(m)
    o.parent = root
    if bev: b = o.modifiers.new('b', 'BEVEL'); b.width = bev; b.segments = 3; b.limit_method = 'ANGLE'
    if smooth and o.type == 'MESH':
        for p in o.data.polygons: p.use_smooth = True
    return o
def box(loc, s, m, rot=(0, 0, 0), bev=.003):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot); o = bpy.context.active_object; o.scale = (s[0] / 2, s[1] / 2, s[2] / 2); bpy.ops.object.transform_apply(scale=True); return P(o, m, False, bev)
def cyl(loc, r, d, m, rot=(0, 0, 0), v=64, bev=.003):
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=d, location=loc, rotation=rot); return P(bpy.context.active_object, m, True, bev)
def sph(loc, r, m, s=(1, 1, 1), seg=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=r, location=loc); o = bpy.context.active_object; o.scale = s; return P(o, m)
def tor(loc, R, r, m, rot=(0, 0, 0), seg=96):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=rot, major_segments=seg, minor_segments=16); return P(bpy.context.active_object, m)
def text(s, size, loc, m, rot=(0, 0, 0), depth=.0005, spacing=1.0, align='CENTER'):
    cu = bpy.data.curves.new('t', 'FONT'); cu.body = s; cu.font = bpy.data.fonts.load(FONT); cu.size = size; cu.extrude = depth; cu.align_x = align; cu.space_character = spacing
    o = bpy.data.objects.new('t', cu); sc.collection.objects.link(o); o.location = loc; o.rotation_euler = rot; o.data.materials.append(m); o.parent = root; return o
def seg(a, b, r, m, v=48):  # cylinder between two points
    a, b = Vector(a), Vector(b); d = b - a; o = cyl((a + b) / 2, r, d.length, m, v=v)
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('Z', 'Y'); return o
def prism(pts, z0, z1, m, s=1.):
    me = bpy.data.meshes.new('p'); bm = bmesh.new(); vs = [bm.verts.new((x * s, y * s, z0)) for x, y in pts]; f = bm.faces.new(vs)
    ex = bmesh.ops.extrude_face_region(bm, geom=[f]); bmesh.ops.translate(bm, verts=[e for e in ex['geom'] if isinstance(e, bmesh.types.BMVert)], vec=(0, 0, z1 - z0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); o = bpy.data.objects.new('p', me); sc.collection.objects.link(o)
    b = o.modifiers.new('b', 'BEVEL'); b.width = .0015; b.segments = 2; o.data.materials.append(m); o.parent = root; return o
NMARK = [[(0, 0), (22, 0), (22, 100), (0, 100)], [(26, 0), (56, 0), (58.88, 16), (28.88, 16)], [(29.96, 22), (59.96, 22), (74, 100), (44, 100)], [(78, 0), (100, 0), (100, 100), (78, 100)]]
def nmark(cx, cy, z0, z1, s, m, mo):
    return [prism([((x - 50) * s + cx, (50 - y) * s + cy) for x, y in pts], z0, z1, mo if i == 1 else m) for i, pts in enumerate(NMARK)]
LOOK = 'dark'; TGT = Vector((0, 0, .3)); CAM = Vector((1.4, -2.6, 1.2)); LENSMM = 70; FST = 2.8; ASP = 1.25
# ======================================================================= scenes
def arm(white, dark, accent, wire=False):
    """Original 6-axis arm. Returns nothing; builds under root."""
    for i, (r, h, m) in enumerate([(.24, .05, dark), (.21, .04, CHROME), (.19, .09, white)]):
        cyl((0, 0, .025 + sum(x[1] for x in [(0, .05), (0, .04), (0, .09)][:i]) + h / 2 - .025), r, h, m, v=96)
    if accent: tor((0, 0, .06), .212, .006, accent)
    cyl((0, 0, .26), .15, .16, white, v=96); cyl((0, 0, .36), .16, .05, dark, v=96)
    j1 = Vector((0, .0, .46)); cyl(j1, .13, .26, white, rot=(math.radians(90), 0, 0), v=96)
    for s in (1, -1):
        cyl(j1 + Vector((0, s * .135, 0)), .1, .012, dark, rot=(math.radians(90), 0, 0));
        if accent: tor(j1 + Vector((0, s * .142, 0)), .085, .005, accent, rot=(math.radians(90), 0, 0))
    j2 = j1 + Vector((.34, 0, .62)); seg(j1, j2, .085, white, v=64); seg(j1 + Vector((0, -.05, 0)), j2 + Vector((0, -.05, 0)), .05, dark, v=32)
    cyl(j2, .1, .22, white, rot=(math.radians(90), 0, 0), v=96)
    for s in (1, -1):
        cyl(j2 + Vector((0, s * .112, 0)), .075, .01, dark, rot=(math.radians(90), 0, 0))
        if accent: tor(j2 + Vector((0, s * .118, 0)), .064, .004, accent, rot=(math.radians(90), 0, 0))
    j3 = j2 + Vector((-.52, 0, -.1)); seg(j2, j3, .065, white, v=64); seg(j2 + Vector((-.12, 0, -.025)), j2 + Vector((-.3, 0, -.06)), .07, dark, v=48)
    cyl(j3, .065, .15, dark, rot=(math.radians(90), 0, 0), v=64); w = j3 + Vector((-.05, 0, -.18)); seg(j3, w, .05, white)
    cyl(w, .05, .07, CHROME); cyl(w + Vector((0, 0, -.05)), .06, .03, dark)
    for s in (1, -1):  # gripper fingers
        box(w + Vector((s * .03, 0, -.12)), (.018, .05, .12), dark, bev=.004); box(w + Vector((s * .036, 0, -.19)), (.012, .04, .05), dark, rot=(0, s * .25, 0), bev=.003)
    text('NSKO R1', .045, (.17, -.087, .77), dark if not wire else accent, rot=(math.radians(90), math.radians(-61), 0), spacing=1.15)
    text('NSKO SOLUTIONS', .022, (0, -.152, .27), dark if not wire else accent, rot=(math.radians(90), 0, 0), spacing=1.5)
    # cables
    pts = [j1 + Vector((-.12, .06, -.05)), j1 + Vector((-.2, .08, .25)), j2 + Vector((-.1, .1, .12)), j2 + Vector((.02, .09, .02))]
    cu = bpy.data.curves.new('c', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = .009; sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts): bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    co = bpy.data.objects.new('c', cu); sc.collection.objects.link(co); co.data.materials.append(dark); co.parent = root
if NAME in ('robot', 'wire'):
    if NAME == 'robot': arm(WHITE, BLKG, SIG)
    else:
        FW = mat('frostW', '#CFE0EC', 0, .3, 1.1); arm(FW, FW, FW, wire=True)
        for o in root.children:
            if o.type == 'MESH':
                wm = o.modifiers.new('w', 'WIREFRAME'); wm.thickness = .0016; wm.use_replace = True
        LOOK = 'void'
    TGT = Vector((-.05, 0, .52)); CAM = Vector((1.5, -2.9, 1.15)); LENSMM = 60
elif NAME == 'quad':  # unarmed quadruped inspection robot
    body = box((0, 0, .52), (.78, .32, .16), GRAPH, bev=.035); box((0, 0, .61), (.6, .24, .03), BLKG, bev=.01)
    for x in (-.3, -.1, .1, .3): box((x, -.162, .52), (.12, .004, .06), BLKM, bev=.002)  # side vents
    head = box((.46, 0, .56), (.18, .26, .12), GRAPH, rot=(0, math.radians(-8), 0), bev=.03)
    for y in (-.07, .07): cyl((.555, y, .565), .03, .02, LENS, rot=(0, math.radians(82), 0)); tor((.563, y, .566), .031, .004, CHROME, rot=(0, math.radians(82), 0))
    cyl((.556, 0, .53), .012, .02, FROSTE, rot=(0, math.radians(82), 0)); box((.5, 0, .63), (.08, .16, .015), FROSTE, bev=.004)
    cyl((-.32, .09, .74), .006, .22, BLKM); sph((-.32, .09, .85), .012, BLKM)
    text('NSKO SOLUTIONS', .032, (0, -.166, .55), mat('stencil', '#C9CED6', 0, .5), rot=(math.radians(90), 0, 0), spacing=1.35); box((-.22, -.163, .5), (.05, .002, .012), SIG, bev=0)
    for sx in (1, -1):
        for sy in (1, -1):
            hip = Vector((sx * .3, sy * .2, .5)); cyl(hip, .075, .1, BLKG, rot=(math.radians(90), 0, 0)); tor(hip + Vector((0, sy * .05, 0)), .06, .004, FROSTE, rot=(math.radians(90), 0, 0))
            knee = hip + Vector((-sx * .1, sy * .02, -.22)); foot = knee + Vector((sx * .07, 0, -.25))
            seg(hip, knee, .06, GRAPH); cyl(knee, .048, .08, BLKG, rot=(math.radians(90), 0, 0)); seg(knee, foot, .04, GRAPH); sph(foot, .045, BLKM)
    root.location = (0, 0, .0); root.rotation_euler = (0, 0, math.radians(-28)); LOOK = 'wet'; TGT = Vector((0, 0, .42)); CAM = Vector((1.3, -2.4, .7)); LENSMM = 60
elif NAME == 'surgical':  # surgical arm over a hologram brain, no people
    base = Vector((.75, .2, 1.45)); j = Vector((.35, 0, 1.05)); seg(base + Vector((.4, 0, .3)), base, .07, WHITE); cyl(base, .09, .16, WHITE, rot=(math.radians(90), 0, 0)); seg(base, j, .06, WHITE)
    cyl(j, .075, .14, CHROME, rot=(math.radians(90), 0, 0)); tor(j + Vector((0, .072, 0)), .06, .004, FROSTE, rot=(math.radians(90), 0, 0))
    h = Vector((.1, 0, .85)); seg(j, h, .045, WHITE); cyl(h, .05, .1, CHROME); cyl(h + Vector((0, 0, -.07)), .03, .06, BLKM)
    for a in (0, 2.09, 4.19):
        p1 = h + Vector((math.cos(a) * .09, math.sin(a) * .09, -.05)); p2 = h + Vector((math.cos(a) * .05, math.sin(a) * .05, -.25)); seg(h, p1, .012, CHROME); seg(p1, p2, .006, CHROME); sph(p2, .009, BLKM)
    seg(h + Vector((0, 0, -.1)), h + Vector((0, 0, -.33)), .004, CHROME)
    text('NSKO SOLUTIONS', .022, (.53, -.072, 1.27), BLKM, rot=(math.radians(90), math.radians(42), 0), spacing=1.2)
    HOLO = mat('holo', '#7FC4FF', 0, .3, 1.4)
    # hologram brain (wireframe, frost)
    for s in (1, -1):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=.13, location=(0.06, s * .07, .46)); b = bpy.context.active_object; b.scale = (1.3, .95, .9)
        t = bpy.data.textures.new('n', 'CLOUDS'); t.noise_scale = .05; d = b.modifiers.new('d', 'DISPLACE'); d.texture = t; d.strength = .03
        wm = b.modifiers.new('w', 'WIREFRAME'); wm.thickness = .0007; P(b, HOLO)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=.06, location=(-.05, 0, .37)); cb = bpy.context.active_object; cb.scale = (1.2, 1.4, .8); wm = cb.modifiers.new('w', 'WIREFRAME'); wm.thickness = .0006; P(cb, HOLO)
    for i in range(40): sph((random.uniform(-.12, .24), random.uniform(-.17, .17), random.uniform(.33, .58)), .004, SIG if i % 9 == 0 else HOLO)
    # table and drape
    box((0, 0, .2), (1.6, .8, .06), mat('drape', '#1B3A4E', 0, .85), bev=.03); box((0, 0, .1), (.3, .3, .2), WHITE)
    LOOK = 'clinic'; TGT = Vector((.1, 0, .55)); CAM = Vector((.9, -2.3, .95)); LENSMM = 55
elif NAME == 'chip':
    board = box((0, 0, 0), (1.6, 1.2, .02), mat('pcb', '#120E10', .1, .45, coat=.5), bev=.002)
    TR = mat('trace', '#B9823F', 1, .3)
    for k in range(140):  # traces in L-paths
        x, y = random.uniform(-.75, .75), random.uniform(-.55, .55)
        if abs(x) < .24 and abs(y) < .24: continue
        L = random.uniform(.05, .3); horiz = random.random() < .5
        box((x + (L / 2 if horiz else 0), y + (0 if horiz else L / 2), .0105), (L if horiz else .006, .006 if horiz else L, .001), TR, bev=0)
    for k in range(60):
        x, y = random.uniform(-.75, .75), random.uniform(-.55, .55)
        if abs(x) < .3 and abs(y) < .3: continue
        w = random.choice([(.03, .015, .012), (.06, .04, .02), (.02, .02, .01)]); box((x, y, .01 + w[2] / 2), w, BLKM if random.random() < .7 else CHROME, bev=.002)
    for k in range(20): x, y = random.uniform(-.75, .75), random.uniform(-.55, .55); cyl((x, y, .011), .008, .002, mat('via%d' % k, '#D9A548', 1, .25), v=24)
    box((0, 0, .03), (.4, .4, .04), BLKG, bev=.006)                       # package
    for side in range(4):
        for i in range(24):
            t = -.19 + i * .0165; a = side * math.pi / 2; c, s_ = math.cos(a), math.sin(a)
            px, py = c * .215 - s_ * t, s_ * .215 + c * t
            box((px, py, .015), (.035 if c else .006, .006 if c else .035, .004), SIG if side == 3 else CHROME, rot=(0, 0, 0), bev=0)
    box((0, 0, .051), (.2, .2, .004), GRAPH, bev=.002)
    text('NSKO', .04, (0, .035, .054), CHROME, spacing=1.2); text('N1 · SECURE', .018, (0, -.02, .054), CHROME, spacing=1.4); text('NSKO SOLUTIONS', .0125, (0, -.06, .054), CHROME, spacing=1.4)
    nmark(-.15, .15, .051, .053, .0006, CHROME, SIG)
    root.rotation_euler = (0, 0, math.radians(32)); LOOK = 'pcb'; TGT = Vector((0, 0, .03)); CAM = Vector((.55, -.95, .55)); LENSMM = 80; FST = 2.0
elif NAME == 'arch':  # stacked tower scale model
    stone = mat('stone', '#D8D3C9', 0, .7); wood = mat('wood', '#8A5A33', 0, .55); glassw = mat('gw', '#3A2A1C', 0, .15, coat=.6); glow = mat('glow', '#FFB866', 0, .5, 1.6)
    box((0, 0, .03), (1.3, 1.0, .06), BLKM, bev=.004); box((0, 0, .063), (1.24, .94, .006), stone, bev=.002)
    random.seed(5); z = .066; levels = [(.0, .0, .42, .34), (.06, -.05, .36, .3), (-.06, .04, .4, .28), (.08, .02, .3, .3), (-.04, -.06, .34, .26), (.03, .05, .28, .24)]
    for i, (dx, dy, w, d) in enumerate(levels):
        h = .11
        box((dx, dy, z + .004), (w * .94, d * .94, .008), WHITE, bev=.002)
        box((dx, dy, z + h / 2), (w * .86, d * .86, h - .01), glassw, bev=0)                       # glass
        for q in range(int(w / .05)):
            if random.random() < .7: box((dx - w * .4 + q * .05 + .02, dy - d * .431, z + h * .55), (.03, .002, h * .5), glow, bev=0)   # lit rooms
        for k in range(int(w / .03)): box((dx - w * .43 + k * .03, dy - d * .43 - .002, z + h / 2), (.004, .004, h - .012), BLKM, bev=0)   # mullions
        if i % 2 == 0: box((dx + w * .25, dy - d * .47, z + h / 2), (w * .45, .012, h * .95), wood, bev=.002)    # timber screen
        else: box((dx - w * .28, dy - d * .46, z + h / 2), (w * .38, d * .05, h * .95), WHITE, bev=.002)
        box((dx, dy, z + h - .004), (w, d, .012), WHITE, bev=.002)
        for t in range(3):  # roof planting
            tx, ty = dx + random.uniform(-w * .4, w * .4), dy + random.uniform(-d * .4, d * .4)
            sph((tx, ty, z + h + .02), .022, mat('leaf%d%d' % (i, t), '#3F5E33', 0, .8), s=(1, 1, .8), seg=12)
        z += h
    for k in range(10):  # street lamps and trees
        a = k / 10 * 2 * math.pi; x, y = math.cos(a) * .5, math.sin(a) * .36
        cyl((x, y, .09), .003, .05, BLKM); sph((x, y, .118), .006, WARM)
        if k % 2: cyl((x * .85, y * .85, .085), .004, .04, wood); sph((x * .85, y * .85, .12), .03, mat('tree%d' % k, '#4A6B3A', 0, .8), seg=12)
    box((.42, -.47, .035), (.22, .004, .04), BLKG, bev=.001); text('NSKO SOLUTIONS · 1:200', .011, (.42, -.4735, .036), GOLD, rot=(math.radians(90), 0, 0), spacing=1.3)
    root.rotation_euler = (0, 0, math.radians(-22)); LOOK = 'studio'; TGT = Vector((0, 0, .32)); CAM = Vector((1.4, -2.3, 1.25)); LENSMM = 65; FST = 4
elif NAME == 'iced':  # iced-out medallion, diamond pavé, Cuban chain
    DIA = mat('diamond', '#FFFFFF', 0, 0, trans=1, ior=2.42, disp=.06); SILV = mat('silver', '#C9CCD2', 1, .14)
    R = .16; cyl((0, 0, 0), R, .03, SILV, v=128); tor((0, 0, 0), R, .012, SILV, seg=160)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=.0064); gem = bpy.context.active_object; gem.data.materials.append(DIA); gem.parent = root; gem.location = (0, 0, -5)
    step = .0128; n = 0
    for iy in range(-13, 14):
        for ix in range(-13, 14):
            x = (ix + (iy % 2) * .5) * step; y = iy * step * .866
            if x * x + y * y < (R * .84) ** 2:
                g = gem.copy(); g.location = (x, y, .0175); sc.collection.objects.link(g); g.parent = root; n += 1
    for k in range(44):  # marquise ring
        a = 2 * math.pi * k / 44
        if abs(math.degrees(a) - 270) < 38: continue
        g = gem.copy(); g.scale = (2.4, 1.2, 1.1); g.rotation_euler = (0, 0, a + math.pi / 2); g.location = (math.cos(a) * R * .92, math.sin(a) * R * .92, .02); sc.collection.objects.link(g); g.parent = root
    nmark(0, 0, .02, .036, .0017, SILV, mat('sigP', '#E8541A', .3, .2, .4))
    bail = box((0, R + .035, 0), (.05, .06, .03), SILV, bev=.008)
    for k in range(5): g = gem.copy(); g.location = (0, R + .015 + k * .011, .016); sc.collection.objects.link(g); g.parent = root
    text('NSKO SOLUTIONS', .0042, (0, R + .045, .0156), mat('engr', '#2A2C30', .8, .3), spacing=1.2)
    text('NSKO SOLUTIONS', .0115, (0, -R * .925, .03), mat('engr2', '#26282C', .8, .35), spacing=1.4)
    for sgn in (1, -1):  # Cuban links
        for k in range(18):
            t = k / 17; x = sgn * (.02 + t * .23); y = R + .075 + t * t * .5 + t * .22
            ang = math.atan2(.22 + 2 * t * .5, sgn * .23)
            l = tor((x, y, 0), .022, .009, SILV, rot=(math.radians(55 if k % 2 else -55), 0, ang), seg=40); l.scale = (1.35, 1, .8)
    root.rotation_euler = (math.radians(90), 0, math.radians(-6)); root.location = (0, 0, .25); LOOK = 'jewel'; TGT = Vector((0, 0, .3)); CAM = Vector((.05, -2.2, .38)); LENSMM = 85; FST = 3.5
# ======================================================================= studio
w = sc.world = bpy.data.worlds.new('w'); w.use_nodes = True; bg = w.node_tree.nodes['Background']
bg.inputs[0].default_value = (*lin({'clinic': '#0E1820', 'studio': '#0D0D0E', 'jewel': '#020202', 'pcb': '#060506', 'void': '#05070A', 'wet': '#060A0E'}.get(LOOK, '#0B0B0D')), 1)
if LOOK != 'pcb':
    bpy.ops.mesh.primitive_plane_add(size=12); fl = bpy.context.active_object
    fm = mat('floor', {'wet': '#07090B', 'clinic': '#0F161C', 'jewel': '#030303', 'void': '#05070A'}.get(LOOK, '#0B0B0D'), 0, {'wet': .04, 'jewel': .6, 'void': .9}.get(LOOK, .3))
    fl.data.materials.append(fm)
tgt = bpy.data.objects.new('tgt', None); sc.collection.objects.link(tgt); tgt.location = TGT
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam; cam.data.lens = LENSMM; cam.location = CAM
c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
cam.data.dof.use_dof = True; cam.data.dof.focus_object = tgt; cam.data.dof.aperture_fstop = FST
def area(loc, sz, en, col):
    l = bpy.data.lights.new('a', 'AREA'); l.size = sz; l.energy = en; l.color = col; o = bpy.data.objects.new('a', l); sc.collection.objects.link(o); o.location = loc
    t = o.constraints.new('TRACK_TO'); t.target = tgt; t.track_axis = 'TRACK_NEGATIVE_Z'; t.up_axis = 'UP_Y'
F = lin('#CFE0EC'); Wm = (1, .82, .6)
if LOOK == 'void': area((2.2, 1.8, 1.6), 1.4, 60, F)
elif LOOK == 'dark': area((-2, -1.6, 2.2), 2, 260, (1, .97, .94)); area((2.2, 1.8, 1.6), 1.4, 520, F); area((-2.2, 2, 1.2), 1.4, 300, F)
elif LOOK == 'wet': area((-1.6, -1.4, 1.6), 1.6, 120, (1, .97, .94)); area((1.8, 1.6, 1.2), 1.2, 600, F); area((-1.8, 1.8, .9), 1.2, 400, F); area((0, 3, .5), 3, 40, F)
elif LOOK == 'clinic': area((0, 0, 3), 1.6, 220, (.92, .97, 1)); area((2, 1.5, 1.4), 1.2, 420, F); area((-2, -1.2, 1.2), 1.6, 140, (1, .97, .94))
elif LOOK == 'studio': area((-1.6, -1.2, 2.2), 1.8, 160, Wm); area((1.8, 1.6, 1.4), 1.2, 260, F); area((0, 2.5, 2), 3, 120, Wm)
elif LOOK == 'pcb': area((-.6, -.4, 1.2), .8, 60, (1, .97, .94)); area((.8, .8, .5), .6, 180, F)
elif LOOK == 'jewel':
    area((-1.2, -1.2, 1.4), .4, 120, (1, 1, 1)); area((1.2, -1, 1.2), .3, 120, (1, 1, 1)); area((0, -1.6, .2), 1.2, 40, (1, 1, 1))
    for i in range(10):  # small hard lights make the stones sparkle
        l = bpy.data.lights.new('p', 'POINT'); l.energy = 40; l.shadow_soft_size = .005; o = bpy.data.objects.new('p', l); sc.collection.objects.link(o)
        o.location = (random.uniform(-1.5, 1.5), random.uniform(-2.2, -.8), random.uniform(.2, 1.6))
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SPP; sc.cycles.use_denoising = True; sc.cycles.max_bounces = 10 if LOOK == 'jewel' else 6
sc.render.resolution_x = SZ; sc.render.resolution_y = int(SZ * ASP); sc.view_settings.view_transform = 'AgX'
try: sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass
sc.render.threads_mode = 'FIXED'; sc.render.threads = int(os.environ.get('TH', '4'))
sc.render.filepath = OUT; bpy.ops.render.render(write_still=True); print('done', OUT)
