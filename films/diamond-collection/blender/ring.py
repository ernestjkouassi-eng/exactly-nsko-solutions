# NSKO Diamond Collection: piece 3, marquise diamond ring. Platinum, 6 claws (V-claw at each point + two side pairs),
# open basket, channel-set pavé shoulders between milgrain rails. Modelled in cm (ring centre at origin, finger along y).
import math, bpy, bmesh
from mathutils import Vector, Matrix
import jlib as J
import cuban as C

RI = .875             # inner radius (UK size ~N)
MQ = 2.5              # marquise length (cm); width ≈ .45 of that
ZG = 2.22             # girdle height above ring centre

def band_mesh(name='band', seg=240):
    """Swept U-channel: inner comfort curve, a channel floor, two raised rails on the edges. Width grows toward the head."""
    if name in bpy.data.meshes: return bpy.data.meshes[name]
    def prof(w):
        h = w / 2
        return [(RI, -h * .92), (RI + .02, -h), (RI + .2, -h), (RI + .225, -h + .02), (RI + .225, -h + .055), (RI + .2, -h + .07),
                (RI + .13, -h + .075), (RI + .13, h - .075), (RI + .2, h - .07), (RI + .225, h - .055), (RI + .225, h - .02), (RI + .2, h), (RI + .02, h), (RI, h * .92)]
    bm = bmesh.new(); rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg; c = math.cos(a)               # a=0: top of the ring (under the head)
        w = .27 + .1 * max(0, c) ** 1.5
        rings.append([bm.verts.new((r * math.sin(a), y, r * math.cos(a))) for r, y in prof(w)])
    n = len(rings[0])
    for i in range(seg):
        A, B = rings[i], rings[(i + 1) % seg]
        for j in range(n): bm.faces.new((A[j], A[(j + 1) % n], B[(j + 1) % n], B[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    return me

def claw(name, pts, r, root, mat):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 4; cu.use_fill_caps = True
    sp = cu.splines.new('NURBS'); sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts): p.co = (*q, 1)
    sp.use_endpoint_u = True; sp.order_u = 3
    o = bpy.data.objects.new(name, cu); J.sc.collection.objects.link(o); o.parent = root; cu.materials.append(mat)
    # rounded claw tip
    t = bpy.data.objects.new(name + '_tip', C._ellipsoid('clawtip', 1, 1, 1, 16, 8)); J.sc.collection.objects.link(t); t.parent = root
    t.location = pts[-1]; t.scale = (r * 1.15, r * 1.15, r * 1.15)
    if not t.data.materials: t.data.materials.append(mat)
    return o

def build(root):
    pl = J.M_platinum(.09); md = J.M_diamond()
    band = C._inst('band', band_mesh(), pl, Matrix.Identity(4), root)
    # centre stone: marquise, long axis along the finger (y)
    mq = J.brilliant('cut_marquise_hi', 'marquise', 64)
    stone = bpy.data.objects.new('marquise', mq); J.sc.collection.objects.link(stone); stone.parent = root
    stone.location = (0, 0, ZG); stone.scale = (MQ, MQ, MQ)
    if not mq.materials: mq.materials.append(md)
    # open basket: girdle rail + lower rail, both following the marquise outline
    import necklace as NK
    C._inst('rail_top', NK.rim_mesh('ring_rail_top', NK.outline('marquise', MQ, 96, .01), .035, 0), pl, Matrix.Translation((0, 0, ZG - .05)), root)
    C._inst('rail_low', NK.rim_mesh('ring_rail_low', NK.outline('marquise', MQ * .5, 64, 0), .04, 0), pl, Matrix.Translation((0, 0, ZG - .78)), root)
    # 6 claws: V-claws at both points, two pairs on the sides
    O = J._outline('marquise', 400)
    def edge_at(yf):        # girdle x at a fraction of the half-length
        y = yf * .5; xs = [abs(x) for x, yy in O if abs(yy - y) < .004]; return max(xs) if xs else 0
    pos = [(0, .5), (0, -.5)] + [(s * edge_at(f), f * .5) for s in (1, -1) for f in (.5, -.5)]
    for k, (x, y) in enumerate(pos):
        X, Y = x * MQ, y * MQ; tip = (X * .93, Y * .965, ZG + .09); g = (X * 1.03, Y * 1.01, ZG - .02)
        low = (X * .5, Y * .5, ZG - .78); base = (X * .18, Y * .25, RI + .2)
        claw('claw%d' % k, [base, low, g, tip], .07 if k < 2 else .06, root, pl)
    # pavé in the channel + milgrain beads on both rails
    S = C.Stones(); S.metal = pl; S.bead_r = .017
    d = .135; amax = math.radians(128)
    a = -amax
    while a <= amax:
        c = math.cos(a); n = Vector((math.sin(a), 0, c)); w = .27 + .1 * max(0, c) ** 1.5
        sz = min(.13, w - .16)
        if abs(a) > math.radians(16): S.add(sz, n * (RI + .13 + sz * .43 + .012), n)
        a += (sz + .01) / (RI + .2)
    a = 0.
    while a < 2 * math.pi:
        c = math.cos(a); n = Vector((math.sin(a), 0, c)); w = .27 + .1 * max(0, c) ** 1.5
        for s in (1, -1): S.bead(n * (RI + .232) + Vector((0, s * (w / 2 - .038), 0)), n)
        a += .04 / (RI + .23)
    S.emit(root, 'rpave')
    return stone, band
