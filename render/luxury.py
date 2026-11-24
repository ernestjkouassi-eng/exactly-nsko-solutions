# NSKO luxury objects: original skeleton tourbillon watch and medallion pendant, black and gold, engraved "NSKO SOLUTIONS".
# Original designs (style direction only from mood references). python3 luxury.py watch|pendant SIZE SPP OUT.png
import bpy, bmesh, math, os, sys, random
from mathutils import Vector
NAME, SZ, SPP, OUT = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
FONT = '/tmp/ddin-src/D-DIN-Bold.otf'
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene; random.seed(4)
def lin(h): h = h.lstrip('#'); c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]; return tuple(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c)
def mat(n, col, metal=0., rough=.5, emit=0., coat=0., trans=0.):
    m = bpy.data.materials.new(n); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*lin(col), 1); b.inputs['Metallic'].default_value = metal; b.inputs['Roughness'].default_value = rough
    if coat: b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = .05
    if emit: b.inputs['Emission Color'].default_value = (*lin(col), 1); b.inputs['Emission Strength'].default_value = emit
    if trans: b.inputs['Transmission Weight'].default_value = trans
    return m
GOLD = mat('gold', '#E9B65A', 1, .16); GOLDB = mat('goldbrushed', '#D9A548', 1, .3); BLK = mat('black', '#0C0C0E', .6, .28, coat=.6)
RUBY = mat('ruby', '#B0123A', 0, .05, trans=.6); STEEL = mat('steel', '#C7CCD3', 1, .2); GLASS = mat('glass', '#FFFFFF', 0, 0, trans=1)
LEATH = mat('leather', '#050507', 0, .8); DIAL = mat('dial', '#040405', 0, .6); SIG = mat('signal', '#E8541A', .2, .3, .6)
root = bpy.data.objects.new('root', None); sc.collection.objects.link(root)
def P(o, m, smooth=True):
    o.data.materials.append(m); o.parent = root
    if smooth and o.type == 'MESH':
        for p in o.data.polygons: p.use_smooth = True
    return o
def cyl(loc, r, d, m, rot=(0, 0, 0), v=96):
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=d, location=loc, rotation=rot); o = bpy.context.active_object
    b = o.modifiers.new('b', 'BEVEL'); b.width = min(d, r) * .2; b.segments = 2; return P(o, m)
def tor(loc, R, r, m, rot=(0, 0, 0), seg=128):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=rot, major_segments=seg, minor_segments=16); return P(bpy.context.active_object, m)
def box(loc, s, m, rot=(0, 0, 0), bev=.002):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot); o = bpy.context.active_object; o.scale = (s[0] / 2, s[1] / 2, s[2] / 2); bpy.ops.object.transform_apply(scale=True)
    if bev: b = o.modifiers.new('b', 'BEVEL'); b.width = bev; b.segments = 2
    return P(o, m, False)
def sph(loc, r, m): bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=r, location=loc); return P(bpy.context.active_object, m)
def text(s, size, loc, m, rot=(0, 0, 0), depth=.0004, curve=None, align='CENTER', spacing=1.0):
    cu = bpy.data.curves.new('t', 'FONT'); cu.body = s; cu.font = bpy.data.fonts.load(FONT); cu.size = size; cu.extrude = depth; cu.align_x = align; cu.space_character = spacing
    o = bpy.data.objects.new('t', cu); sc.collection.objects.link(o); o.location = loc; o.rotation_euler = rot; o.data.materials.append(m); o.parent = root
    if curve: cu.follow_curve = curve
    return o
def gear(loc, r, th, teeth, m, spokes=5, rot=0):
    g = cyl(loc, r * .86, th, m, v=64)
    for k in range(teeth):
        a = rot + 2 * math.pi * k / teeth; box((loc[0] + math.cos(a) * r * .93, loc[1] + math.sin(a) * r * .93, loc[2]), (r * .16, r * 2 * math.pi / teeth * .5, th), m, rot=(0, 0, a), bev=0)
    # skeleton: cut-outs suggested with dark discs between spokes
    for k in range(spokes):
        a = rot + 2 * math.pi * (k + .5) / spokes; cyl((loc[0] + math.cos(a) * r * .5, loc[1] + math.sin(a) * r * .5, loc[2] + th * .51), r * .24, th * .05, BLK, v=32)
    cyl((loc[0], loc[1], loc[2] + th * .6), r * .12, th * .4, GOLD, v=32); sph((loc[0], loc[1], loc[2] + th * .9), r * .07, RUBY)
    return g
# --------------------------------------------------------------- WATCH
if NAME == 'watch':
    R = .2; Z = .045
    cyl((0, 0, -.01), R * 1.02, .06, GOLD)                                 # case (top sits below the dial)
    tor((0, 0, .036), R * .97, .016, GOLD)                                 # bezel roll
    for k in range(180):                                                   # fluted bezel
        a = 2 * math.pi * k / 180; box((math.cos(a) * R * 1.035, math.sin(a) * R * 1.035, .02), (.006, .0035, .05), GOLDB, rot=(0, 0, a), bev=0)
    cyl((0, 0, .03), R * .9, .006, DIAL)                                    # dark base plate
    tor((0, 0, .037), R * .84, .006, BLK)                                  # chapter ring
    for i in range(12):                                                    # gold indices
        a = math.pi / 2 - i * math.pi / 6; box((math.cos(a) * R * .8, math.sin(a) * R * .8, .04), (.022 if i % 3 == 0 else .014, .0045, .004), GOLD, rot=(0, 0, a))
    # skeleton bridges: arches from rim to centre
    for k in range(6):
        a = k * math.pi / 3 + .3; mid = Vector((math.cos(a) * R * .45, math.sin(a) * R * .45, .037))
        box(mid, (R * .78, .007, .004), GOLDB, rot=(0, 0, a))
        tor((math.cos(a + .5) * R * .55, math.sin(a + .5) * R * .55, .036), R * .17, .0035, BLK)
    # visible movement: gold gears with ruby jewels
    for (x, y, r, n) in [(-.07, .06, .045, 24), (.065, .07, .038, 20), (.08, -.02, .03, 16), (-.085, -.02, .028, 16), (0, .1, .025, 14)]:
        gear((x, y, .033), r, .004, n, GOLDB, rot=random.random())
    for (x, y) in [(-.05, .12), (.12, .04), (-.13, .05), (.03, .02), (-.02, -.05), (.11, -.08)]: sph((x, y, .038), .0045, RUBY)
    # tourbillon at six o'clock: open cage
    tx, ty = 0, -.095
    tor((tx, ty, .038), .05, .004, GOLD); tor((tx, ty, .036), .042, .002, STEEL)
    for k in range(3): a = k * 2 * math.pi / 3; box((tx + math.cos(a) * .024, ty + math.sin(a) * .024, .042), (.05, .004, .003), GOLD, rot=(0, 0, a))
    gear((tx, ty, .034), .022, .003, 18, GOLD); sph((tx, ty, .046), .006, RUBY)
    # hands
    box((-.035, .04, .05), (.11, .006, .002), GOLD, rot=(0, 0, math.radians(130))); box((.05, .045, .052), (.15, .004, .002), GOLD, rot=(0, 0, math.radians(42)))
    cyl((0, 0, .053), .008, .006, GOLD, v=32)
    # engraving: small luxury wordmark on the chapter ring and caseback-style line
    text('NSKO', .016, (0, .132, .041), GOLD, spacing=1.25)
    text('SOLUTIONS', .0085, (0, .116, .041), GOLD, spacing=1.6)
    text('TOURBILLON', .0065, (0, -.165, .041), GOLDB, spacing=1.8)
    cyl((R * 1.06, 0, 0), .022, .035, GOLD, rot=(0, math.radians(90), 0), v=48)   # crown
    for k in range(24): a = 2 * math.pi * k / 24; box((R * 1.08, math.cos(a) * .02, math.sin(a) * .02), (.03, .004, .004), GOLDB, rot=(a, 0, 0), bev=0)
    for sgn in (1, -1):                                                    # lugs + leather strap
        for sx in (-1, 1): box((sx * .11, sgn * .21, 0), (.03, .07, .03), GOLD, bev=.006)
        for k in range(6):
            y = sgn * (.25 + k * .07); z = -.004 - k * k * .004
            s = box((0, y, z), (.2, .075, .022), LEATH, rot=(math.radians(-sgn * k * 7), 0, 0), bev=.008)
            for sx in (-1, 1): box((sx * .088, y, z + .012), (.002, .06, .002), GOLDB, rot=(math.radians(-sgn * k * 7), 0, 0), bev=0)  # stitching
    root.rotation_euler = (math.radians(58), 0, math.radians(8)); root.location = (0, 0, .2)
# --------------------------------------------------------------- PENDANT
else:
    R = .16
    cyl((0, 0, 0), R, .03, GOLD)                                           # medallion
    tor((0, 0, 0), R, .012, GOLDB, seg=180)                                # rope edge
    for k in range(48): a = 2 * math.pi * k / 48; tor((math.cos(a) * R, math.sin(a) * R, 0), .011, .004, GOLD, rot=(0, math.radians(90), a + math.pi / 2), seg=24)
    cyl((0, 0, .016), R * .78, .004, BLK)                                  # black enamel field
    for k in range(60): a = 2 * math.pi * k / 60; box((math.cos(a) * R * .83, math.sin(a) * R * .83, .017), (.008 if k % 5 else .016, .002, .003), GOLD, rot=(0, 0, a), bev=0)
    s = .0014                                                              # raised N mark in gold, orange fragment in enamel
    def prism(pts, z0, z1, m):
        me = bpy.data.meshes.new('p'); bm = bmesh.new(); vs = [bm.verts.new((x, y, z0)) for x, y in pts]; f = bm.faces.new(vs)
        ex = bmesh.ops.extrude_face_region(bm, geom=[f]); bmesh.ops.translate(bm, verts=[e for e in ex['geom'] if isinstance(e, bmesh.types.BMVert)], vec=(0, 0, z1 - z0))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); o = bpy.data.objects.new('p', me); sc.collection.objects.link(o)
        b = o.modifiers.new('b', 'BEVEL'); b.width = .0012; b.segments = 2; o.data.materials.append(m); o.parent = root; return o
    for pts, m in [([(0, 0), (22, 0), (22, 100), (0, 100)], GOLD), ([(26, 0), (56, 0), (58.88, 16), (28.88, 16)], SIG), ([(29.96, 22), (59.96, 22), (74, 100), (44, 100)], GOLD), ([(78, 0), (100, 0), (100, 100), (78, 100)], GOLD)]:
        prism([((x - 50) * s, (50 - y) * s) for x, y in pts], .016, .026, m)
    # engraving around the rim: N S K O  S O L U T I O N S
    word = 'NSKO SOLUTIONS'; n = len(word)
    for i, ch in enumerate(word):
        a = math.radians(-90 + (i - (n - 1) / 2) * 10.2)
        if ch != ' ': text(ch, .0115, (math.cos(a) * .106, math.sin(a) * .106, .0182), GOLD, rot=(0, 0, a + math.pi / 2), depth=.0008)
    # bail and box chain
    box((0, R + .03, 0), (.04, .05, .022), GOLD, bev=.006); tor((0, R + .062, 0), .016, .005, GOLD, rot=(0, math.radians(90), 0))
    for sgn in (1, -1):
        for k in range(26):
            t = k / 25; x = sgn * (.012 + t * .2); y = R + .08 + t * t * .55 + t * .25
            ang = math.atan2(.25 + 2 * t * .55, sgn * .2)
            box((x, y, 0), (.026, .02, .02), GOLD, rot=(0, 0, ang + math.pi / 2), bev=.004)
            box((x, y, 0), (.016, .021, .012), BLK, rot=(0, 0, ang + math.pi / 2), bev=0)
    root.rotation_euler = (math.radians(90), 0, math.radians(-8)); root.location = (0, 0, .23)
# --------------------------------------------------------------- set: black marble with gold veins, warm bokeh
bpy.ops.mesh.primitive_plane_add(size=8); fl = bpy.context.active_object
m = bpy.data.materials.new('marble'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
b.inputs['Roughness'].default_value = .12; b.inputs['Coat Weight'].default_value = .8; b.inputs['Coat Roughness'].default_value = .03
tc = nt.nodes.new('ShaderNodeTexCoord'); wv = nt.nodes.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = .7; wv.inputs['Distortion'].default_value = 14; wv.inputs['Detail'].default_value = 8
nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3; cr = nt.nodes.new('ShaderNodeValToRGB')
cr.color_ramp.elements[0].position = .0; cr.color_ramp.elements[0].color = (*lin('#050506'), 1); cr.color_ramp.elements[1].position = .025; cr.color_ramp.elements[1].color = (*lin('#0A0A0C'), 1)
e = cr.color_ramp.elements.new(.012); e.color = (*lin('#4A3B22'), 1)
nt.links.new(tc.outputs['Object'], nz.inputs['Vector']); nt.links.new(nz.outputs['Color'], wv.inputs['Vector']); nt.links.new(wv.outputs['Fac'], cr.inputs['Fac']); nt.links.new(cr.outputs['Color'], b.inputs['Base Color'])
fl.data.materials.append(m)
if False:  # (plinth removed) a raised marble block under the watch, like a plinth
    bpy.ops.mesh.primitive_cube_add(location=(0, .05, .05)); blk = bpy.context.active_object; blk.scale = (.5, .32, .05); blk.rotation_euler = (0, 0, math.radians(-12)); pm = m.copy(); pb = pm.node_tree.nodes['Principled BSDF']; pb.inputs['Coat Weight'].default_value = .15; pb.inputs['Roughness'].default_value = .38; blk.data.materials.append(pm)
    bv = blk.modifiers.new('b', 'BEVEL'); bv.width = .02; bv.segments = 3
w = sc.world = bpy.data.worlds.new('w'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (*lin('#070707'), 1); w.node_tree.nodes['Background'].inputs[1].default_value = 1
for i in range(9):  # warm out-of-focus lights in the background
    o = sph((random.uniform(-2.4, 2.4), random.uniform(2.2, 4.5), random.uniform(.3, 1.6)), random.uniform(.05, .14), mat('bk%d' % i, '#FFB35C', 0, 1, random.uniform(6, 16)))
    o.parent = None
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam; cam.data.lens = 85
tgt = bpy.data.objects.new('tgt', None); sc.collection.objects.link(tgt); tgt.location = (0, 0, .18 if NAME == 'watch' else .23)
cam.location = (.45, -2.6, 1.05) if NAME == 'watch' else (.1, -2.5, .5)
c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
cam.data.dof.use_dof = True; cam.data.dof.focus_object = tgt; cam.data.dof.aperture_fstop = 2.4
def area(loc, sz, en, col):
    l = bpy.data.lights.new('a', 'AREA'); l.size = sz; l.energy = en; l.color = col; o = bpy.data.objects.new('a', l); sc.collection.objects.link(o); o.location = loc
    t = o.constraints.new('TRACK_TO'); t.target = tgt; t.track_axis = 'TRACK_NEGATIVE_Z'; t.up_axis = 'UP_Y'
area((-1.6, -.4, 1.1), 1.0, 70, (1, .9, .78)); area((1.3, .8, .8), .8, 220, (1, .78, .5)); area((0, -1.6, .9), 1.6, 18, (1, .95, .9)); area((-.9, 1.2, .9), .6, 160, (1, .85, .6))
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SPP; sc.cycles.use_denoising = True; sc.cycles.max_bounces = 8
sc.render.resolution_x = SZ; sc.render.resolution_y = int(SZ * 1.25); sc.view_settings.view_transform = 'AgX'
try: sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass
sc.render.threads_mode = 'FIXED'; sc.render.threads = int(os.environ.get('TH', '4'))
sc.render.filepath = OUT; bpy.ops.render.render(write_still=True); print('done', OUT)
