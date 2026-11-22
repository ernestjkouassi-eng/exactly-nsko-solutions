# 3D silver NSKO lockup (exploded-N symbol + NSKO wordmark) rendered in Blender Cycles.
# usage: python3 mark3d.py <frames> <width> <samples> [outdir]
import bpy, math, sys, os
from mathutils import Vector
N = int(sys.argv[1]); W = int(sys.argv[2]); SPP = int(sys.argv[3]); OUT = sys.argv[4] if len(sys.argv) > 4 else '/home/user/film/mark'
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def mat(name, col, metal, rough, emit=0, ecol=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Metallic'].default_value = metal; b.inputs['Roughness'].default_value = rough
    if 'Coat Weight' in b.inputs: b.inputs['Coat Weight'].default_value = .6; b.inputs['Coat Roughness'].default_value = .04
    if emit: b.inputs['Emission Color'].default_value = (*(ecol or col), 1); b.inputs['Emission Strength'].default_value = emit
    return m
SILVER = mat('silver', (.93, .94, .96), 1, .11)
ORANGE = mat('orange', (0.80, 0.10, 0.012), .2, .16, .35, (0.9, 0.16, 0.02))

def prism(name, pts, depth, m, bev=.6):
    # pts in the SVG's 0..100 space (y down) -> blender units (y up), scale .02
    s = .02; v = [(x * s, -y * s, 0) for x, y in pts]
    me = bpy.data.meshes.new(name); me.from_pydata(v, [], [list(range(len(v)))]); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); o.data.materials.append(m)
    so = o.modifiers.new('solid', 'SOLIDIFY'); so.thickness = depth; so.offset = 0
    bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = bev * s; bv.segments = 4; bv.limit_method = 'ANGLE'
    return o
root = bpy.data.objects.new('root', None); bpy.context.collection.objects.link(root)
parts = [prism('L', [(0, 0), (22, 0), (22, 100), (0, 100)], .5, SILVER),
         prism('F', [(26, 0), (56, 0), (58.88, 16), (28.88, 16)], .5, ORANGE),
         prism('D', [(29.96, 22), (59.96, 22), (74, 100), (44, 100)], .5, SILVER),
         prism('R', [(78, 0), (100, 0), (100, 100), (78, 100)], .5, SILVER)]
# orange fragment floats forward a little: the "exploded" N
parts[1].location.z = .14
fc = bpy.data.curves.new('word', 'FONT'); fc.body = 'NSKO'
fc.font = bpy.data.fonts.load('/home/user/film/InterBlack.ttf'); fc.size = 2.62; fc.extrude = .25; fc.bevel_depth = .014; fc.bevel_resolution = 3; fc.space_character = .96
word = bpy.data.objects.new('word', fc); bpy.context.collection.objects.link(word); word.data.materials.append(SILVER)
word.location = (2.62, -2.0, -.25)
for o in parts + [word]: o.parent = root
# centre the group
bpy.context.view_layer.update()
xs = [ (o.matrix_world @ Vector(c)).x for o in parts + [word] for c in o.bound_box ]
ys = [ (o.matrix_world @ Vector(c)).y for o in parts + [word] for c in o.bound_box ]
cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
piv = bpy.data.objects.new('piv', None); bpy.context.collection.objects.link(piv)
root.parent = piv; root.location = (-cx, -cy, 0)
span = max(xs) - min(xs)

cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); bpy.context.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 85; cam.location = (0, 0, 27); cam.rotation_euler = (0, 0, 0)
cam.data.sensor_width = 36

def area(name, loc, size, energy, col):
    l = bpy.data.lights.new(name, 'AREA'); l.size = size; l.energy = energy; l.color = col
    o = bpy.data.objects.new(name, l); bpy.context.collection.objects.link(o); o.location = loc
    t = o.constraints.new('TRACK_TO'); t.target = piv; t.track_axis = 'TRACK_NEGATIVE_Z'; t.up_axis = 'UP_Y'; return o
area('key', (-6, 7, 10), 6, 1500, (1, .97, .94))
area('rim', (8, -2, -3), 3, 900, (1, .55, .3))
area('fill', (4, -6, 9), 8, 260, (.8, .88, 1))
# the moving light sweep: a long thin bright strip that crosses the letters
sw = bpy.data.lights.new('sweep', 'AREA'); sw.shape = 'RECTANGLE'; sw.size = .35; sw.size_y = 14; sw.energy = 2600
swo = bpy.data.objects.new('sweep', sw); bpy.context.collection.objects.link(swo); swo.rotation_euler = (0, math.radians(0), math.radians(-18))
w = sc.world = bpy.data.worlds.new('w'); w.use_nodes = True
bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (.05, .055, .065, 1); bg.inputs[1].default_value = 1
# simple studio "environment": big soft panels the chrome can reflect
for i, (x, y) in enumerate([(-9, 5), (9, 4), (0, -8)]):
    pm = bpy.data.meshes.new(f'p{i}'); pm.from_pydata([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], [], [[0, 1, 2, 3]])
    po = bpy.data.objects.new(f'p{i}', pm); bpy.context.collection.objects.link(po); po.location = (x, y, 14)
    em = bpy.data.materials.new(f'pe{i}'); em.use_nodes = True; nt = em.node_tree; nt.nodes.clear()
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs[1].default_value = 3.5; o_ = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(e.outputs[0], o_.inputs[0]); po.data.materials.append(em)
    po.visible_camera = False
def emitter(name, verts, loc, strength, col=(1,1,1)):
    pm = bpy.data.meshes.new(name); pm.from_pydata(verts, [], [[0, 1, 2, 3]])
    po = bpy.data.objects.new(name, pm); bpy.context.collection.objects.link(po); po.location = loc
    em = bpy.data.materials.new(name); em.use_nodes = True; nt = em.node_tree; nt.nodes.clear()
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs[0].default_value = (*col, 1); e.inputs[1].default_value = strength
    o_ = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(e.outputs[0], o_.inputs[0]); po.data.materials.append(em)
    po.visible_camera = False; return po
# soft front reflector so flat metal faces read silver, with a gradient falloff by placing it high
emitter('front', [(-14, 2, 0), (14, 2, 0), (14, 12, 0), (-14, 12, 0)], (0, 0, 40), 1.1, (.85, .9, 1))
emitter('floor', [(-14, -12, 0), (14, -12, 0), (14, -6, 0), (-14, -6, 0)], (0, 0, 40), .25, (1, .7, .5))
# the light sweep: a bright thin strip the metal reflects; it crosses left to right
SW = emitter('sweepstrip', [(-.5, -30, 0), (.5, -30, 0), (.5, 30, 0), (-.5, 30, 0)], (0, 0, 38), 14)
SW.rotation_euler = (0, 0, math.radians(-20))
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SPP; sc.cycles.use_denoising = True
sc.render.film_transparent = True; sc.render.resolution_x = W; sc.render.resolution_y = int(W * .42); sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy' if 'AgX - Punchy' in [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties['look'].enum_items] else 'None'
sc.render.threads_mode = 'FIXED'; sc.render.threads = 2
cam.data.lens = 85 * (36 / (span * 1.28)) * (27 / 85) * 85 / 85 if False else cam.data.lens
# fit: horizontal FOV must cover span*1.25
fov = 2 * math.atan((span * 1.25 / 2) / 27); cam.data.lens = 36 / (2 * math.tan(fov / 2))
for f in range(N):
    k = f / max(1, N - 1)
    piv.rotation_euler = (math.radians(-6 + 10 * k), math.radians(-24 + 38 * k), 0)
    swo.location = (-span * .9 + span * 1.8 * k, 0, 6)
    SW.location.x = (-span * 1.2 + span * 2.4 * k) * 1.4
    sc.render.filepath = f'{OUT}/m{f:02d}.png'
    bpy.ops.render.render(write_still=True)
print('done', N)
