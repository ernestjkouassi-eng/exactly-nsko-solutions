# NSKO Diamond Collection: piece 1, rose-gold iced Cuban link chain with pear-motif box clasp, on a grey velvet bust.
# Modelled in centimetres, then everything hangs off a root empty scaled 0.01 so the scene is in real metres (correct DOF and light falloff).
import math, bpy, bmesh
from mathutils import Vector, Matrix
import jlib as J

LINK_PITCH = 1.22     # cm between link centres (≈37 links on a 45 cm neck)
W = 2.2               # chain width, cm (photo reads 20 to 22 mm)

# ---------------------------------------------------------------- bust (display form, not a person)
_BP = [(-30, 16.0), (-16, 16.6), (-10, 15.6), (-6, 13.6), (-3, 11.4), (0, 8.9), (2.5, 7.3), (5, 6.4), (8, 6.0), (14, 5.9), (20.5, 5.9), (22, 5.6), (22.6, 4.8)]
def _pchip_slopes(P):
    h = [P[i + 1][0] - P[i][0] for i in range(len(P) - 1)]; d = [(P[i + 1][1] - P[i][1]) / h[i] for i in range(len(h))]
    m = [d[0]] + [0 if d[i - 1] * d[i] <= 0 else 3 * (h[i - 1] + h[i]) / ((2 * h[i] + h[i - 1]) / d[i - 1] + (h[i] + 2 * h[i - 1]) / d[i]) for i in range(1, len(d))] + [d[-1]]
    return m
_BP = [(z * .74, r * .74) for z, r in _BP]
_BM = _pchip_slopes(_BP)
def _bust_r(z):
    """Profile radius of the bust at height z (cm): smooth monotone curve (no ripples), neck above 5, flaring to the shoulders."""
    P = _BP; z = max(P[0][0], min(P[-1][0], z))
    for i in range(len(P) - 1):
        (z0, r0), (z1, r1) = P[i], P[i + 1]
        if z0 <= z <= z1:
            h = z1 - z0; t = (z - z0) / h
            return (2*t**3 - 3*t**2 + 1) * r0 + (t**3 - 2*t**2 + t) * h * _BM[i] + (-2*t**3 + 3*t**2) * r1 + (t**3 - t**2) * h * _BM[i + 1]

def _bust_sy(z):
    """Front-to-back squash: round neck, flatter chest."""
    t = min(1, max(0, (4.4 - z) / 10.4)); return 1 - .38 * t

def bust_point(theta, z):
    r = _bust_r(z); return Vector((r * math.cos(theta), r * _bust_sy(z) * math.sin(theta), z))

def bust_normal(theta, z):
    e = 1e-3
    a = bust_point(theta + e, z) - bust_point(theta - e, z); b = bust_point(theta, z + e) - bust_point(theta, z - e)
    n = a.cross(b).normalized()
    p = bust_point(theta, z)
    if n.dot(Vector((p.x, p.y, 0))) < 0: n = -n
    return n

def build_bust(root, col='#8F8B88'):
    bm = bmesh.new(); NT = 96; zs = [_BP[0][0] + i * .2 for i in range(int((_BP[-1][0] - _BP[0][0]) / .2) + 1)]
    rings = [[bm.verts.new(bust_point(2 * math.pi * i / NT, z)) for i in range(NT)] for z in zs]
    for A, B in zip(rings, rings[1:]):
        for i in range(NT):
            j = (i + 1) % NT; bm.faces.new((A[i], A[j], B[j], B[i]))
    bm.faces.new(list(reversed(rings[0]))); top = bm.faces.new(rings[-1])
    me = bpy.data.meshes.new('bust'); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new('bust', me); J.sc.collection.objects.link(o); o.parent = root
    m = J.principled('bust_velvet', col, 0, .95, sheen=.8); o.data.materials.append(m)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']                        # velvet nap: fine noise bump
    tx = nt.nodes.new('ShaderNodeTexNoise'); tx.inputs['Scale'].default_value = 2600; tx.inputs['Detail'].default_value = 6
    bu = nt.nodes.new('ShaderNodeBump'); bu.inputs['Strength'].default_value = .12; bu.inputs['Distance'].default_value = .02
    nt.links.new(tx.outputs['Fac'], bu.inputs['Height']); nt.links.new(bu.outputs['Normal'], b.inputs['Normal'])
    sub = o.modifiers.new('sub', 'SUBSURF'); sub.levels = 1; sub.render_levels = 2
    return o

# ---------------------------------------------------------------- chain path on the bust
def chain_frames(n_links=None, z_back=2.5, z_front=-1.3, lift=.26):
    """Link frames (4x4, cm) sitting on the bust: x = along the chain, z = out of the bust surface."""
    def z_of(th): return (z_back + z_front) / 2 + (z_back - z_front) / 2 * math.sin(th)    # th=-90° is the front (camera side)
    N = 2000; P = []
    for i in range(N + 1):
        th = -math.pi / 2 + 2 * math.pi * i / N; z = z_of(th); P.append((th, z, bust_point(th, z) + bust_normal(th, z) * lift))
    L = [0]
    for a, b in zip(P, P[1:]): L.append(L[-1] + (b[2] - a[2]).length)
    total = L[-1]; n = n_links or int(round(total / LINK_PITCH)); n -= n % 2
    out = []; k = 0
    for j in range(n):
        s = total * j / n
        while L[k + 1] < s: k += 1
        th, z, p = P[k]; nxt = P[min(k + 4, N)][2]; prv = P[max(k - 4, 0)][2]
        x = (nxt - prv).normalized(); nz = bust_normal(th, z); nz = (nz - x * nz.dot(x)).normalized(); y = nz.cross(x)
        M = Matrix.Identity(4)
        for r in range(3): M[r][0], M[r][1], M[r][2], M[r][3] = x[r], y[r], nz[r], p[r]
        out.append(M)
    return out, total

# ---------------------------------------------------------------- shared meshes
def _ellipsoid(name, a, b, c, seg=40, ring=20):
    if name in bpy.data.meshes: return bpy.data.meshes[name]
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=1)
    for v in bm.verts: v.co = Vector((v.co.x * a, v.co.y * b, v.co.z * c))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    return me

def _disc(name, r, h, seg=48):
    """Raised bezel cup for a halo cluster: a short cylinder with a rounded rim."""
    if name in bpy.data.meshes: return bpy.data.meshes[name]
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r * .92, radius2=r, depth=h)
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges if e.verts[0].co.z > 0 and e.verts[1].co.z > 0], offset=h * .35, segments=3, affect='EDGES')
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    return me

def _torus(name, R, r, seg=48):
    if name in bpy.data.meshes: return bpy.data.meshes[name]
    bm = bmesh.new(); vs = []
    for i in range(seg):
        a = 2 * math.pi * i / seg; ring = []
        for j in range(10):
            b = 2 * math.pi * j / 10; ring.append(bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b))))
        vs.append(ring)
    for i in range(seg):
        for j in range(10): bm.faces.new((vs[i][j], vs[(i + 1) % seg][j], vs[(i + 1) % seg][(j + 1) % 10], vs[i][(j + 1) % 10]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    return me

def _inst(name, mesh, mat, M, root):
    o = bpy.data.objects.new(name, mesh); J.sc.collection.objects.link(o); o.parent = root; o.matrix_basis = M
    if not mesh.materials: mesh.materials.append(mat)
    return o

class Stones:
    """Collects stone positions per size, then emits one instanced pavé object per size (thousands of stones, low memory)."""
    def __init__(self): self.b = {}; self.beads = ([], [])
    def bead(self, p, n): self.beads[0].append(tuple(p)); self.beads[1].append(tuple(n))
    def add(self, size, p, n): self.b.setdefault(round(size, 3), ([], []))[0].append(tuple(p)); self.b[round(size, 3)][1].append(tuple(n))
    def emit(self, root, tag):
        cut = J.brilliant('cut_round', 'round', 32); out = []
        for k, (ps, ns) in self.b.items(): out.append(J.pave('%s_%g' % (tag, k), ps, ns, cut, J.M_diamond(), k, parent=root))
        if self.beads[0]: out.append(J.pave(tag + '_beads', *self.beads, _ellipsoid('bead', 1, 1, 1, 10, 6), getattr(self, 'metal', None) or J.M_rosegold(.1), getattr(self, 'bead_r', .03), parent=root))
        return out

# ---------------------------------------------------------------- one link
def _basket(name, r_top, r_bot, h, seg=48):
    """Open cone (no caps) under a cluster: the gallery. Its walls never touch a pavilion."""
    if name in bpy.data.meshes: return bpy.data.meshes[name]
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=False, segments=seg, radius1=r_bot, radius2=r_top, depth=h)
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=.012)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    return me

def halo_cluster(F, S, cx, cy, cz, root, tag, centre=.5, halo=.12, nh=16, mats=None):
    """Raised halo cluster. cz = centre-stone girdle height above the frame origin.
    Round brilliant centre held by a thin bezel and 4 claws; a halo of micro brilliants sits on a gallery ring;
    an open basket carries it down to the link. Nothing solid touches a pavilion."""
    rg = J.M_rosegold(.1)
    R = centre / 2 + halo * .62 + .02
    C = F @ Matrix.Translation((cx, cy, cz))
    hz = -.06                                                   # halo girdle, relative to the centre girdle
    ring_z = hz - halo * .45 - .03
    _inst(tag + '_gal', _torus('gallery', 1, .1), rg, C @ Matrix.Translation((0, 0, ring_z)) @ Matrix.Diagonal((R, R, R * .9, 1)), root)
    _inst(tag + '_rim', _torus('halo_rim', 1, .03), rg, C @ Matrix.Translation((0, 0, hz - .015)) @ Matrix.Diagonal((R + halo * .55, R + halo * .55, R + halo * .55, 1)), root)
    _inst(tag + '_bas', _basket('basket', 1, .35, .5), rg, C @ Matrix.Translation((0, 0, ring_z - .5 * (R * .9) / 2 - .005)) @ Matrix.Diagonal((R * .96, R * .96, R * .9 * .5 / .5 * 1, 1)), root)
    bz = centre / 2 + .006
    _inst(tag + '_bezel', _torus('bezel', 1, .05), rg, C @ Matrix.Diagonal((bz, bz, bz, 1)), root)
    for i in range(4):
        a = math.pi / 4 + i * math.pi / 2
        _inst('%s_claw%d' % (tag, i), _ellipsoid('claw', .035, .035, .05, 12, 8), rg, C @ Matrix.Translation((bz * math.cos(a), bz * math.sin(a), .03)), root)
    rot = F.to_3x3()
    S.add(centre, F @ Vector((cx, cy, cz)), rot @ Vector((0, 0, 1)))
    for i in range(nh):
        a = 2 * math.pi * (i + .5) / nh; p = Vector((cx + R * math.cos(a), cy + R * math.sin(a), cz + hz))
        tilt = Vector((math.cos(a) * .22, math.sin(a) * .22, 1)).normalized()
        S.add(halo, F @ p, rot @ tilt)

LB = (.7, 1.1, .3)            # link body half-sizes (cm): along chain, across, dome height

def _link_z(x, y):
    a, b, c = LB; q = 1 - (x / a) ** 2 - (y / b) ** 2; z = c * math.sqrt(max(q, 0))
    return z, Vector((x / a ** 2, y / b ** 2, z / c ** 2 + 1e-4)).normalized()

def cuban_link(F, S, root, k, centre=.56, halo=.14, nh=15):
    """F: link frame. Body: domed rose-gold curb link, twisted so its two halo clusters run on a diagonal (the Cuban 'scale' look).
    Every bit of the top not under a cluster is pavé, as in the source photos."""
    rg = J.M_rosegold(.1)
    tw = Matrix.Rotation(math.radians(-20), 4, 'Z') @ Matrix.Rotation(math.radians(10), 4, 'Y')
    G = F @ tw
    _inst('link%02d' % k, _ellipsoid('link_body', *LB), rg, G, root)
    R = centre / 2 + halo * .62 + .02; rc = R + halo * .6
    cl = [(.05, .55), (-.05, -.55)]
    for i, (cx, cy) in enumerate(cl):
        z, _ = _link_z(cx, cy)
        halo_cluster(G, S, cx, cy, z + centre * .43 + .07, root, 'l%02d%s' % (k, 'ab'[i]), centre, halo, nh)
    rot = G.to_3x3(); d = .118; sz = .1
    for j in range(-12, 13):
        for i in range(-8, 9):
            x = (i + .5 * (j % 2)) * d; y = j * d * .866
            if (x / LB[0]) ** 2 + (y / LB[1]) ** 2 > .9: continue
            if any((x - cx) ** 2 + (y - cy) ** 2 < (rc + .05) ** 2 for cx, cy in cl): continue
            z, n = _link_z(x, y); S.add(sz, G @ Vector((x, y, z)) + (rot @ n) * (sz * .43 + .012), rot @ n)
            S.bead(G @ Vector((x, y, z)) + (rot @ n) * .02 + (rot @ Vector((d / 2, 0, 0))), rot @ n)
    for side in (1, -1):                       # one row down each chain edge, so it reads iced from the side
        for i in range(7):
            x = -.54 + i * .18; yy = LB[1] * math.sqrt(max(0, 1 - (x / LB[0]) ** 2))
            n = Vector((x / LB[0] ** 2 * .3, side / LB[1], .25)).normalized()
            S.add(.095, G @ Vector((x, side * yy * .97, .06)) + (rot @ n) * .05, rot @ n)

# ---------------------------------------------------------------- pear-motif box clasp
def box_clasp(F, S, root, tag='clasp'):
    """Domed pear clasp ≈1.8 links long: one large pear centre, 10 pears fanning round it, micro-pavé pear outline,
    six halo clusters around it and a pavé dome shoulder. Hidden box lock (tongue + box + latch) underneath."""
    rg = J.M_rosegold(.1)
    L, Wd, H = 1.55, 1.3, .55        # half-length, half-width, dome height (cm)
    G = F
    body = _inst(tag + '_body', _ellipsoid('clasp_body', L, Wd, H, 64, 32), rg, G, root)
    # hidden box lock, visible only in the exploded view
    lock = _inst(tag + '_box', _ellipsoid('clasp_box', L * .8, Wd * .78, .22, 32, 12), J.M_rosegold(.14), G @ Matrix.Translation((0, 0, -.32)), root)
    tongue = _inst(tag + '_tongue', _ellipsoid('clasp_tongue', .9, .5, .08, 24, 8), J.M_rosegold(.14), G @ Matrix.Translation((L * .9, 0, -.32)), root)
    rot = G.to_3x3()
    def dome(x, y):
        q = 1 - (x / L) ** 2 - (y / Wd) ** 2; z = H * math.sqrt(max(q, 0)); n = Vector((x / L ** 2, y / Wd ** 2, z / H ** 2 + 1e-4)).normalized(); return z, n
    pear = J.brilliant('cut_pear', 'pear', 48)
    # raised pear motif: stones on a pear-shaped open gallery above the dome, so every pavilion sees air
    ML = .44                                          # motif lift above the dome (cm)
    def pear_xy(t, k):
        py = .5 * math.cos(t); px = (.31 / .7698) * math.sin(t) * math.sin(t / 2); return -.1 - py * k, px * k
    bm = bmesh.new(); top, bot = [], []
    for i in range(96):
        t = 2 * math.pi * i / 96; x, y = pear_xy(t, 2.25); z, n = dome(x, y)
        top.append(bm.verts.new((x, y, z + ML - .05))); bot.append(bm.verts.new((x * .97, y * .97, z - .05)))
    for i in range(96):
        j = (i + 1) % 96; bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=.03)
    me = bpy.data.meshes.new(tag + '_wall'); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    _inst(tag + '_wall', me, rg, G, root)
    pz, pn = dome(-.15, 0)
    big = J.stone(tag + '_pear', pear, J.M_diamond(), 1.0, (0, 0, 0)); big.parent = root
    big.matrix_basis = G @ Matrix.Translation((-.12, 0, pz + ML + .1)) @ Matrix.Rotation(-math.pi / 2, 4, 'Z')
    for i in range(10):
        a = math.radians(-150 + i * 300 / 9); r = .7
        x, y = -.12 + r * math.cos(a) * 1.02, r * math.sin(a) * .74; z, n = dome(x, y)
        s = J.stone('%s_p%d' % (tag, i), pear, J.M_diamond(), .36, (0, 0, 0)); s.parent = root
        s.matrix_basis = G @ Matrix.Translation((x, y, z + ML)) @ Matrix.Rotation(a - math.pi / 2, 4, 'Z') @ Matrix.Rotation(-.22, 4, 'X')
    # micro pavé pear outline on the gallery rim
    for i in range(78):
        x, y = pear_xy(2 * math.pi * i / 78, 2.25); z, n = dome(x, y)
        S.add(.07, G @ Vector((x, y, z + ML + .02)), rot @ Vector((0, 0, 1)))
    # six halo clusters on the shoulder
    for i in range(6):
        a = math.radians(40 + i * 56); x, y = L * .72 * math.cos(a), Wd * .74 * math.sin(a)
        if abs(math.cos(a)) > .9 and math.cos(a) > 0: x *= .9
        z, n = dome(x, y)
        T = Matrix.Translation((x, y, z + .14)); Rn = n.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        halo_cluster(G @ T @ Rn, S, 0, 0, 0, root, '%s_h%d' % (tag, i), centre=.34, halo=.08, nh=13)
    # pavé dome on what is left
    import random; rnd = random.Random(3)
    placed = []
    for j in range(2600):
        x, y = rnd.uniform(-L, L), rnd.uniform(-Wd, Wd)
        if (x / L) ** 2 + (y / Wd) ** 2 > .97: continue
        xr, yr = -(x + .1) / 2.25, y / 2.25           # inside the pear outline? skip
        if abs(xr) < .5:
            t = math.acos(max(-1, min(1, xr / .5))); hw = abs((.31 / .7698) * math.sin(t) * math.sin(t / 2))
            if abs(yr) < hw + .03: continue
        ok = all((x - a) ** 2 + (y - b) ** 2 > .105 ** 2 for a, b in placed)
        if ok:
            for i in range(6):
                a = math.radians(40 + i * 56); hx, hy = L * .72 * math.cos(a), Wd * .74 * math.sin(a)
                if (x - hx) ** 2 + (y - hy) ** 2 < .42 ** 2: ok = False; break
        if not ok: continue
        placed.append((x, y)); z, n = dome(x, y); S.add(.095, G @ Vector((x, y, z)) + (rot @ n) * .045, rot @ n)
    return body

# ---------------------------------------------------------------- assemble
def build(root, clasp_at=.62, skip=()):
    """Whole necklace on the bust. clasp_at: position round the neck (0 = front centre, .5 = back)."""
    frames, total = chain_frames()
    S = Stones(); n = len(frames); ci = int(round(clasp_at * n)) % n
    for k, F in enumerate(frames):
        if k in skip: continue
        if k in (ci, (ci + 1) % n): continue
        cuban_link(F, S, root, k)
    Fc = frames[ci].lerp(frames[(ci + 1) % n], .5) if hasattr(frames[ci], 'lerp') else frames[ci]
    clasp = box_clasp(frames[ci] @ Matrix.Translation((LINK_PITCH / 2, 0, .1)), S, root)
    S.emit(root, 'pave')
    return frames, clasp, sum(len(v[0]) for v in S.b.values())
