# NSKO v4.2 hero objects, procedural (Blender Cycles, CPU).
# python3 objects.py <name> <frames> <size> <spp> <outdir> [glb]
# Style: matte obsidian/graphite, brushed metal, frost rim light, one tiny orange detail, shallow DOF, soft floor reflection.
import bpy, bmesh, math, os, sys
from mathutils import Vector
NAME, N, SZ, SPP, OUT = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
GLB = len(sys.argv) > 6 and sys.argv[6] == 'glb'
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
def lin(h): h = h.lstrip('#'); c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]; return tuple(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c)
def mat(name, col, metal=0., rough=.5, emit=0., aniso=0., coat=0., ecol=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*lin(col), 1); b.inputs['Metallic'].default_value = metal; b.inputs['Roughness'].default_value = rough
    if aniso: b.inputs['Anisotropic'].default_value = aniso
    if coat: b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = .08
    if emit: b.inputs['Emission Color'].default_value = (*lin(ecol or col), 1); b.inputs['Emission Strength'].default_value = emit
    return m
OBS = mat('obsidian', '#141518', .2, .55); GRA = mat('graphite', '#2A2D33', .5, .42); MET = mat('brushed', '#B9BEC6', 1., .28, aniso=.6)
DARKMET = mat('darkmetal', '#3A3E45', 1., .35, aniso=.4); SIG = mat('signal', '#E8541A', 0, .4, 3.5); FROST = mat('frost', '#CFE0EC', 0, .45)
WHITE = mat('white', '#E9EAEC', 0, .6); GLASS = mat('glass', '#FFFFFF', 0, .02); GLASS.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 1
root = bpy.data.objects.new('root', None); sc.collection.objects.link(root)
def P(o, m=None, smooth=True, bevel=0.):
    if m: o.data.materials.append(m)
    o.parent = root
    if bevel: b = o.modifiers.new('b', 'BEVEL'); b.width = bevel; b.segments = 3; b.limit_method = 'ANGLE'
    if smooth and o.type == 'MESH':
        for p in o.data.polygons: p.use_smooth = True
        try: o.data.set_sharp_from_angle(angle=math.radians(35))
        except Exception: pass
    return o
def cube(loc, size, m, bevel=.01, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot); o = bpy.context.active_object; o.scale = (size[0] / 2, size[1] / 2, size[2] / 2); bpy.ops.object.transform_apply(scale=True); return P(o, m, bevel=bevel)
def cyl(loc, r, d, m, rot=(0, 0, 0), v=64, bevel=.004):
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=d, location=loc, rotation=rot); return P(bpy.context.active_object, m, bevel=bevel)
def sph(loc, r, m, sc_=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=r, location=loc); o = bpy.context.active_object; o.scale = sc_; return P(o, m)
def tor(loc, R, r, m, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=rot, major_segments=96, minor_segments=18); return P(bpy.context.active_object, m)
def prism(pts, z0, z1, m, bevel=.006):
    me = bpy.data.meshes.new('p'); bm = bmesh.new(); vs = [bm.verts.new((x, y, z0)) for x, y in pts]; f = bm.faces.new(vs)
    ex = bmesh.ops.extrude_face_region(bm, geom=[f]); bmesh.ops.translate(bm, verts=[e for e in ex['geom'] if isinstance(e, bmesh.types.BMVert)], vec=(0, 0, z1 - z0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); o = bpy.data.objects.new('p', me); sc.collection.objects.link(o); return P(o, m, smooth=False, bevel=bevel)
H = 1.0  # framing height target
# ---------------- objects ----------------
if NAME == 'n':  # the exploded N mark: four slabs, orange fragment floating forward
    s = .02; parts = [([(0, 0), (22, 0), (22, 100), (0, 100)], GRA, 0), ([(26, 0), (56, 0), (58.88, 16), (28.88, 16)], SIG, .35), ([(29.96, 22), (59.96, 22), (74, 100), (44, 100)], GRA, .12), ([(78, 0), (100, 0), (100, 100), (78, 100)], GRA, 0)]
    for pts, m, dz in parts:
        o = prism([((x - 50) * s, (50 - y) * s) for x, y in pts], -.12 + dz, .12 + dz, m if m is not SIG else mat('sigN', '#E8541A', .1, .35, 1.2))
    root.rotation_euler = (math.radians(90), 0, 0); H = 2.0
elif NAME == 'drone':
    cube((0, 0, 0), (.42, .3, .1), OBS, .03); cube((0, 0, .07), (.26, .18, .05), GRA, .02)
    for i, (x, y) in enumerate([(1, 1), (1, -1), (-1, 1), (-1, -1)]):
        a = math.atan2(y, x); L = .42; cx, cy = math.cos(a) * L, math.sin(a) * L
        cube((cx / 2, cy / 2, 0), (L, .04, .03), GRA, .01, rot=(0, 0, a)); cyl((cx, cy, .03), .045, .07, DARKMET); cyl((cx, cy, .075), .012, .03, MET)
        for k in range(2): cube((cx, cy, .095), (.36, .022, .004), OBS, .002, rot=(0, 0, a + k * math.pi / 2 + .4))
        cyl((cx, cy, -.03), .006, .06, GRA)
    sph((0, -.02, -.1), .06, DARKMET); cyl((0, -.075, -.1), .028, .02, GLASS, rot=(math.radians(90), 0, 0)); cyl((0, -.083, -.1), .02, .006, mat('lens', '#0E1A24', 1, .05), rot=(math.radians(90), 0, 0))
    cyl((.12, .155, .02), .008, .005, SIG, rot=(math.radians(90), 0, 0))
    for x in (-.14, .14): cube((x, 0, -.16), (.015, .28, .015), GRA, .006); cube((x, 0, -.1), (.012, .012, .12), GRA, .004)
    H = 1.1
elif NAME == 'arm':
    cyl((0, 0, .03), .22, .06, GRA); cyl((0, 0, .1), .14, .1, OBS); cyl((0, 0, .17), .1, .06, MET)
    j1 = Vector((0, 0, .26)); cyl(j1, .08, .2, DARKMET, rot=(0, math.radians(90), 0))
    a1 = math.radians(-25); L1 = .62; e = j1 + Vector((math.sin(a1) * L1, 0, math.cos(a1) * L1))
    mid = (j1 + e) / 2; cube(mid, (.1, .12, L1), OBS, .035, rot=(0, a1, 0)); cyl(e, .065, .17, DARKMET, rot=(0, math.radians(90), 0))
    a2 = math.radians(70); L2 = .5; w = e + Vector((math.sin(a2) * L2, 0, math.cos(a2) * L2)); cube((e + w) / 2, (.08, .1, L2), OBS, .03, rot=(0, a2, 0))
    cyl(w, .05, .12, MET, rot=(0, math.radians(90), 0)); cyl(w + Vector((.06, 0, -.04)), .035, .08, GRA, rot=(0, math.radians(30), 0))
    g = w + Vector((.1, 0, -.1)); cube(g + Vector((0, .035, 0)), (.025, .018, .09), MET, .005); cube(g + Vector((0, -.035, 0)), (.025, .018, .09), MET, .005)
    cyl(j1 + Vector((0, .101, 0)), .02, .004, SIG, rot=(math.radians(90), 0, 0)); root.location = (.1, 0, -.4); H = 1.2
elif NAME == 'chip':
    cube((0, 0, 0), (.9, .9, .06), GRA, .01); cube((0, 0, .05), (.6, .6, .04), MET, .02)
    for i in range(14):
        t = -.39 + i * .06
        for sx, sy, rx in [(t, .5, 0), (t, -.5, 0), (.5, t, 1), (-.5, t, 1)]: cube((sx, sy, -.02), (.025, .12, .01) if not rx else (.12, .025, .01), MET, .002)
    pts = [(0, 0), (22, 0), (22, 100), (0, 100)]
    s = .0035
    for pts, m in [([(0, 0), (22, 0), (22, 100), (0, 100)], OBS), ([(26, 0), (56, 0), (58.88, 16), (28.88, 16)], SIG), ([(29.96, 22), (59.96, 22), (74, 100), (44, 100)], OBS), ([(78, 0), (100, 0), (100, 100), (78, 100)], OBS)]:
        prism([((x - 50) * s, (50 - y) * s) for x, y in pts], .07, .075, m, .0005)
    root.rotation_euler = (math.radians(28), 0, math.radians(20)); H = .9
elif NAME == 'blade':  # secure server module
    cube((0, 0, 0), (1.1, .5, .09), OBS, .012); cube((-.53, 0, 0), (.04, .52, .1), DARKMET, .008)
    for i in range(10): cube((-.548, -.2 + i * .045, 0), (.006, .03, .05), GRA, .002)
    cube((.15, 0, .05), (.7, .42, .01), GRA, .003)
    for i in range(18): cube((.15 - .33 + i * .039, 0, .065), (.012, .38, .02), MET, .002)
    cyl((-.555, .21, .02), .008, .004, SIG, rot=(0, math.radians(90), 0)); cyl((-.555, .21, -.02), .008, .004, mat('frostled', '#CFE0EC', 0, .3, 2), rot=(0, math.radians(90), 0))
    root.rotation_euler = (math.radians(12), 0, math.radians(25)); H = .9
elif NAME == 'key':  # hardware security key
    cube((0, 0, 0), (.62, .22, .06), OBS, .03); cube((.38, 0, 0), (.16, .12, .035), MET, .004)
    for i in range(4): cube((.4, -.03 + i * .02, .02), (.08, .01, .002), mat('gold', '#C9A45A', 1, .3), .001)
    cyl((-.22, 0, 0), .05, .08, mat('hole', '#0B0B0D', 0, .9), v=48); tor((-.22, 0, 0), .05, .012, MET)
    cyl((-.02, 0, .032), .07, .006, mat('touch', '#1E2126', .3, .25)); tor((-.02, 0, .034), .07, .004, SIG)
    root.rotation_euler = (math.radians(22), 0, math.radians(-25)); H = .75
elif NAME == 'arch':  # architectural scale model, frost white on a dark plinth
    cube((0, 0, -.04), (1.2, .9, .06), OBS, .01)
    import random; random.seed(3)
    for x, y, w, d, h in [(-.35, -.18, .26, .3, .55), (-.05, .12, .3, .22, .38), (.3, -.1, .22, .36, .72), (.12, -.28, .18, .14, .22), (-.38, .25, .2, .18, .25)]:
        cube((x, y, h / 2), (w, d, h), WHITE, .004)
        for k in range(int(h / .06)): cube((x, y - d / 2 - .001, .03 + k * .06), (w * .9, .004, .012), FROST, .001)
    cube((.3, -.1, .74), (.36, .2, .025), WHITE, .003)  # cantilever roof
    cyl((-.1, -.3, .01), .006, .02, SIG); H = 1.05
elif NAME == 'watch':
    cyl((0, 0, 0), .2, .07, MET, v=96, bevel=.01); tor((0, 0, .036), .19, .012, DARKMET); cyl((0, 0, .03), .175, .01, mat('dial', '#121317', .2, .45), v=96)
    for i in range(12):
        a = i / 12 * 2 * math.pi; r = .15; cube((math.cos(a) * r, math.sin(a) * r, .037), (.028 if i % 3 == 0 else .016, .006, .004), FROST if i % 3 else MET, .001, rot=(0, 0, a))
    cube((.04, .02, .04), (.1, .008, .003), MET, .001, rot=(0, 0, math.radians(30))); cube((.0, .055, .042), (.006, .13, .003), MET, .001, rot=(0, 0, math.radians(-15)))
    cube((.045, -.06, .044), (.004, .13, .002), SIG, .0005, rot=(0, 0, math.radians(35))); cyl((0, 0, .046), .01, .006, MET)
    cyl((.215, 0, 0), .018, .04, MET, rot=(0, math.radians(90), 0)); cyl((0, 0, .041), .176, .004, GLASS, v=96)
    for sgn in (1, -1):
        for k in range(5): cube((0, sgn * (.24 + k * .075), -.005 - k * .012), (.2, .07, .03), mat('strap', '#1A1C20', .1, .7), .01, rot=(math.radians(-sgn * k * 9), 0, 0))
    root.rotation_euler = (math.radians(55), 0, math.radians(15)); H = .8
elif NAME == 'pendant':
    s = .006
    for pts, m in [([(0, 0), (22, 0), (22, 100), (0, 100)], MET), ([(26, 0), (56, 0), (58.88, 16), (28.88, 16)], SIG), ([(29.96, 22), (59.96, 22), (74, 100), (44, 100)], MET), ([(78, 0), (100, 0), (100, 100), (78, 100)], MET)]:
        prism([((x - 50) * s, (50 - y) * s) for x, y in pts], -.015, .015, m if m is not SIG else mat('sigP', '#E8541A', .6, .3, .8), .003)
    tor((0, .36, 0), .035, .008, MET, rot=(0, math.radians(90), 0))
    cu = bpy.data.curves.new('chain', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = .006; cu.bevel_resolution = 4
    sp = cu.splines.new('NURBS'); pts_ = [(t * .42, .39 + abs(t) ** 1.5 * .6, 0) for t in [i / 8 - 1 for i in range(17)]]
    sp.points.add(len(pts_) - 1)
    for p_, (x, y, z) in zip(sp.points, pts_): p_.co = (x, y, z, 1)
    sp.use_endpoint_u = True; sp.order_u = 4
    co = bpy.data.objects.new('chain', cu); sc.collection.objects.link(co); co.data.materials.append(MET); co.parent = root
    root.rotation_euler = (math.radians(90), 0, 0); H = 1.6
# ---------------- studio ----------------
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in root.children_recursive if o.type == 'MESH' for c in o.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))); hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
ctr = (lo + hi) / 2; size = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z)
piv = bpy.data.objects.new('piv', None); sc.collection.objects.link(piv); piv.location = (ctr.x, ctr.y, 0); root.parent = piv; root.location = (root.location.x - ctr.x, root.location.y - ctr.y, root.location.z - lo.z + .002) if NAME != 'n' else (root.location.x - ctr.x, root.location.y - ctr.y, -lo.z + .25)
bpy.context.view_layer.update()
top = max((o.matrix_world @ Vector(c)).z for o in root.children_recursive if o.type == 'MESH' for c in o.bound_box)
OBSID = lin('#0B0B0D')
w = sc.world = bpy.data.worlds.new('w'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (*OBSID, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 1
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0)); fl = bpy.context.active_object; fm = mat('floor', '#0B0B0D', .0, .32); fm.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = .35; fl.data.materials.append(fm)
tgt = bpy.data.objects.new('tgt', None); sc.collection.objects.link(tgt); tgt.location = (0, 0, top * .48)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam; cam.data.lens = 70
dist = size * (4.2 if NAME == 'n' else 3.1); cam.location = (0, -dist, top * .5 + dist * .22)
c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
cam.data.dof.use_dof = True; cam.data.dof.focus_object = tgt; cam.data.dof.aperture_fstop = 2.2 if NAME != 'n' else 3.2
def area(nm, loc, sz, en, col):
    l = bpy.data.lights.new(nm, 'AREA'); l.size = sz; l.energy = en; l.color = col; o = bpy.data.objects.new(nm, l); sc.collection.objects.link(o); o.location = loc
    t = o.constraints.new('TRACK_TO'); t.target = tgt; t.track_axis = 'TRACK_NEGATIVE_Z'; t.up_axis = 'UP_Y'; return o
k = size
area('key', (-2.2 * k, -2.4 * k, 2.6 * k), 2.5 * k, 260 * k * k, (1, .97, .94))
area('rim', (2.4 * k, 2.2 * k, 1.6 * k), 1.6 * k, 520 * k * k, lin('#CFE0EC'))
area('rim2', (-2.6 * k, 2.4 * k, 1.2 * k), 1.6 * k, 300 * k * k, lin('#CFE0EC'))
area('top', (0, 0, 4 * k), 3 * k, 120 * k * k, (1, 1, 1))
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SPP; sc.cycles.use_denoising = True; sc.cycles.max_bounces = 6
sc.render.resolution_x = SZ; sc.render.resolution_y = int(SZ * (0.625 if NAME == 'n' else 1)); sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'; sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Base Contrast' if False else 'None'
try: sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass
sc.render.threads_mode = 'FIXED'; sc.render.threads = int(os.environ.get('TH', '4'))
if GLB:
    for o in [fl]: o.hide_set(True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in root.children_recursive: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=f'{OUT}/{NAME}.glb', use_selection=True, export_apply=True, export_yup=True); print('glb ok'); sys.exit(0)
FSTEP = int(os.environ.get('FSTEP', '1'))
for f in range(0, N, FSTEP):
    if os.path.exists(f'{OUT}/f{f:03d}.png') and os.environ.get('SKIP'): continue
    ARC = float(os.environ.get('ARC', '360')); A0 = float(os.environ.get('A0', '-30'))
    piv.rotation_euler = (0, 0, math.radians(A0 + ARC * f / N))
    sc.render.filepath = f'{OUT}/f{f:03d}.png'; bpy.ops.render.render(write_still=True)
print('done', N)
