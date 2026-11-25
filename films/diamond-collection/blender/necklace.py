# NSKO Diamond Collection: piece 2, lady's yellow pear diamond pendant on a white-gold marquise-leaf chain (V front).
# Same conventions as cuban.py: modelled in cm under a root empty scaled 0.01. Every stone sits on an open gallery rim.
import math, bpy, bmesh
from mathutils import Vector, Matrix
import jlib as J
import cuban as C

PITCH = .8            # cm between leaf units
LEAF = .72             # marquise length, cm
LIFT = LEAF * .43 + .06

def _frame(o, x, n):
    n = n.normalized(); x = (x - n * x.dot(n)).normalized(); y = n.cross(x); M = Matrix.Identity(4)
    for r in range(3): M[r][0], M[r][1], M[r][2], M[r][3] = x[r], y[r], n[r], o[r]
    return M

def rim_mesh(name, pts, r=.03, depth=.0, seg=6):
    """Metal rim following a closed 2D outline (girdle seat), with an optional open wall hanging down `depth` (no floor)."""
    if name in bpy.data.meshes: return bpy.data.meshes[name]
    bm = bmesh.new(); N = len(pts); rings = []
    for i in range(N):
        p = Vector((*pts[i], 0)); q = Vector((*pts[(i + 1) % N], 0)) - Vector((*pts[i - 1], 0)); t = q.normalized()
        out = Vector((t.y, -t.x, 0))
        if out.dot(p - Vector((sum(a for a, _ in pts) / N, sum(b for _, b in pts) / N, 0))) < 0: out = -out
        rings.append([bm.verts.new(p + out * r * math.cos(2 * math.pi * j / seg) + Vector((0, 0, r * math.sin(2 * math.pi * j / seg)))) for j in range(seg)])
    for i in range(N):
        A, B = rings[i], rings[(i + 1) % N]
        for j in range(seg): bm.faces.new((A[j], B[j], B[(j + 1) % seg], A[(j + 1) % seg]))
    if depth > 0:
        top = [bm.verts.new((x * .98, y * .98, -r)) for x, y in pts]; bot = [bm.verts.new((x * .7, y * .7, -depth)) for x, y in pts]
        for i in range(N):
            j = (i + 1) % N; bm.faces.new((top[i], top[j], bot[j], bot[i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    return me

def outline(shape, size, n=48, grow=0.):
    pts = J._outline(shape, n)
    if shape == 'round': return [(x * size * (1 + grow), y * size * (1 + grow)) for x, y in pts]
    return [(x * size * (1 + grow), y * size * (1 + grow)) for x, y in pts]

def set_stone(name, cut, mat, size, M, root, shape, rim_r=.022, wall=None):
    """Stone with girdle at M's origin (its long axis = M's local y), a rim at the girdle and V-claws at the tips."""
    pl = J.M_platinum(.1)
    s = bpy.data.objects.new(name, cut); J.sc.collection.objects.link(s); s.parent = root; s.matrix_basis = M @ Matrix.Diagonal((size, size, size, 1))
    if not cut.materials: cut.materials.append(mat)
    C._inst(name + '_rim', rim_mesh('rim_%s_%g' % (shape, size), outline(shape, size, 64, .015), rim_r, wall if wall is not None else size * .45), pl, M, root)
    if shape in ('marquise', 'pear'):
        tips = [(0, .5 * size)] + ([(0, -.5 * size)] if shape == 'marquise' else [])
        for k, (x, y) in enumerate(tips):
            C._inst('%s_claw%d' % (name, k), C._ellipsoid('vclaw', .045, .07, .05, 12, 8), pl, M @ Matrix.Translation((x, y * 1.02, .015)), root)
    return s

# ---------------------------------------------------------------- path: V down the chest, chain round the back of the neck
def path_frames(z_back=2.4, z_front=-10.2, p=.55):
    def z_of(phi): return z_front + (z_back - z_front) * (abs(phi) / math.pi) ** p
    N = 3000; P = []
    for i in range(N + 1):
        phi = -math.pi + 2 * math.pi * i / N; th = -math.pi / 2 + phi; z = z_of(phi)
        P.append((phi, th, z, C.bust_point(th, z) + C.bust_normal(th, z) * LIFT))
    L = [0]
    for a, b in zip(P, P[1:]): L.append(L[-1] + (b[3] - a[3]).length)
    half = L[-1] / 2; n = int(half / PITCH)
    out = []
    for side in (-1, 1):
        for j in range(0, n):
            s = half + side * (j * PITCH + .95)
            k = max(1, min(N - 1, next(i for i in range(N) if L[i + 1] >= s)))
            phi, th, z, p_ = P[k]
            x = (P[k][3] - P[k + side if 0 <= k + side <= N else k][3]); x = -x if side > 0 else x
            x = (P[min(k + 3, N)][3] - P[max(k - 3, 0)][3]) * (-side)      # points toward the front
            out.append(_frame(p_, x, C.bust_normal(th, z)))
    th0 = -math.pi / 2; front = C.bust_point(th0, z_front) + C.bust_normal(th0, z_front) * LIFT
    return out, _frame(front, Vector((0, 0, -1)), C.bust_normal(th0, z_front))

# ---------------------------------------------------------------- leaf unit: two marquises in a V with a round at the vertex
def leaf_unit(F, root, S, k, scale=1.):
    md = J.M_diamond(); mq = J.brilliant('cut_marquise', 'marquise', 48); rd = J.brilliant('cut_round', 'round', 32)
    L = LEAF * scale
    for i, a in enumerate((math.radians(148), math.radians(-148))):
        d = Vector((math.cos(a), math.sin(a), 0)); c = Vector((.16, 0, 0)) * scale + d * (L * .52)
        M = F @ Matrix.Translation(c) @ Matrix.Rotation(a - math.pi / 2, 4, 'Z') @ Matrix.Rotation(.12 * (1 if i else -1), 4, 'Y')
        set_stone('leaf%03d_%d' % (k, i), mq, md, L, M, root, 'marquise')
    S.add(.17 * scale, F @ Vector((.2 * scale, 0, .02)), F.to_3x3() @ Vector((0, 0, 1)))
    S.bead(F @ Vector((.2 * scale, .1 * scale, -.02)), F.to_3x3() @ Vector((0, 0, 1))); S.bead(F @ Vector((.2 * scale, -.1 * scale, -.02)), F.to_3x3() @ Vector((0, 0, 1)))

def front_and_drop(Ff, root, S):
    """Ff: frame at the V point, x = down the chest. A 5-leaf spray, a short leaf drop, a bail and the canary pear in a white halo."""
    md = J.M_diamond(); mq = J.brilliant('cut_marquise', 'marquise', 48)
    L = LEAF * 1.15
    for i, deg in enumerate((-125, -60, 0, 60, 125)):          # spray: angle from 'down'
        a = math.radians(deg); d = Vector((math.cos(a), math.sin(a), 0)); c = d * (L * .55)
        M = Ff @ Matrix.Translation(c + Vector((0, 0, .02 if deg == 0 else 0))) @ Matrix.Rotation(a - math.pi / 2, 4, 'Z')
        set_stone('spray%d' % i, mq, md, L * (.85 if deg in (-125, 125) else 1), M, root, 'marquise')
    S.add(.26, Ff @ Vector((0, 0, .05)), Ff.to_3x3() @ Vector((0, 0, 1)))
    # drop: two small leaf units pointing down
    for j in range(2):
        Fj = Ff @ Matrix.Translation((L * 1.05 + j * PITCH * .8, 0, -.03)) @ Matrix.Rotation(math.pi, 4, 'Z')
        leaf_unit(Fj, root, S, 900 + j, .8)
    # bail + pear (point down)
    yb = L * 1.05 + 2 * PITCH * .8 + .05
    C._inst('bail', C._torus('bail', 1, .18), J.M_platinum(.1), Ff @ Matrix.Translation((yb, 0, -.05)) @ Matrix.Rotation(math.pi / 2, 4, 'X') @ Matrix.Diagonal((.13, .13, .13, 1)), root)
    P = 1.6; lift = P * .43 * .6
    Mp = Ff @ Matrix.Translation((yb + .15 + P * .5 + .14, 0, lift - LIFT + .1)) @ Matrix.Rotation(-math.pi / 2, 4, 'Z')   # local +y (pear point) = down the chest
    set_stone('yellow_pear', J.brilliant('cut_pear_y', 'pear', 64), J.principled('yellow_diamond_cm', '#FFF3A6', 0, 0, 1, 2.417, .045, absorb='#FFE04A', absorb_d=14), P, Mp, root, 'pear', .028, lift + .05)
    # white diamond halo: micro rounds round the pear girdle, on their own rim
    po = outline('pear', P, 400, 0)
    per = sum(math.dist(po[i], po[i - 1]) for i in range(len(po))); nh = int(per / .135)
    acc, idx, Lc = 0, [], [0]
    for i in range(1, len(po)): Lc.append(Lc[-1] + math.dist(po[i], po[i - 1]))
    cx = sum(x for x, _ in po) / len(po); cy = sum(y for _, y in po) / len(po)
    hp = []
    for h in range(nh):
        s = per * h / nh; i = next(i for i in range(len(Lc)) if Lc[i] >= s) if s <= Lc[-1] else len(po) - 1
        x, y = po[i]; v = Vector((x - cx, y - cy)); v = v.normalized() if v.length else Vector((0, 1))
        hp.append((x + v.x * .1, y + v.y * .1))
        S.add(.11, Mp @ Vector((x + v.x * .1, y + v.y * .1, -.04)), Mp.to_3x3() @ Vector((v.x * .2, v.y * .2, 1)).normalized())
    out = [(x * 1.0 + (x - cx) * .0, y) for x, y in outline('pear', P, 96, .16)]
    C._inst('halo_rim', rim_mesh('pear_halo_rim', out, .022, lift), J.M_platinum(.1), Mp @ Matrix.Translation((0, 0, -.06)), root)

def build(root):
    frames, Ff = path_frames()
    S = C.Stones(); S.metal = J.M_platinum(.1); S.bead_r = .028
    for k, F in enumerate(frames): leaf_unit(F, root, S, k)
    front_and_drop(Ff, root, S)
    S.emit(root, 'npave')
    return frames, Ff
