# NSKO Diamond Collection: piece 4, the NSKO Celestial Tourbillon. An ORIGINAL NSKO design (style cues only from the reference:
# open rose-gold case, gem planets, blue sapphire ring). No maker names, no zodiac, no dial text. One tiny "NSKO" on the caseband at 9.
# cm units, face in the xy plane, 12 o'clock = +y, angles measured clockwise from 12.
import math, bpy, bmesh
from mathutils import Vector, Matrix
import jlib as J
import cuban as C

RC = 2.2          # case radius (44 mm)
GEIST = '/home/user/nsko-solutions/node_modules/geist/dist/fonts/geist-sans/Geist-Medium.ttf'

def at(a_deg, r, z=0.):
    a = math.radians(a_deg); return Vector((r * math.sin(a), r * math.cos(a), z))

def revolve(name, prof, seg=192, window=None):
    """Surface of revolution from an (r, z) profile. window=(a0, a1, keep): between those clock angles only the first `keep` profile points survive
    (the asymmetric arc window cut through the bezel at 2 o'clock)."""
    bm = bmesh.new(); rings = []
    for i in range(seg + 1):
        a = 360 * i / seg; P = prof
        if window and window[0] <= a <= window[1]:
            t = (a - window[0]) / (window[1] - window[0]); s = math.sin(math.pi * t) ** .6          # smooth scoop
            P = [(r, z - s * max(0, z - window[2])) for r, z in prof]
        rings.append([bm.verts.new(at(a, r, z)) for r, z in P])
    n = len(prof)
    for i in range(seg):
        A, B = rings[i], rings[i + 1]
        for j in range(n): bm.faces.new((A[j], A[(j + 1) % n], B[(j + 1) % n], B[j]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    return me

def gear(name, R, teeth, h, hole=.25, spokes=5):
    if name in bpy.data.meshes: return bpy.data.meshes[name]
    bm = bmesh.new(); pts = []
    for i in range(teeth * 4):
        a = 2 * math.pi * i / (teeth * 4); r = R if (i % 4) in (1, 2) else R * .9; pts.append((r * math.cos(a), r * math.sin(a)))
    vb = [bm.verts.new((x, y, 0)) for x, y in pts]; f = bm.faces.new(vb)
    ex = bmesh.ops.extrude_face_region(bm, geom=[f]); bmesh.ops.translate(bm, verts=[v for v in ex['geom'] if isinstance(v, bmesh.types.BMVert)], vec=(0, 0, h))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('tmp', me)
    for p in me.polygons: p.use_smooth = False
    return me

def bar(name, p0, p1, w, h, mat, root, z0=0):
    """Rectangular bridge bar from p0 to p1 (2D, cm)."""
    p0, p1 = Vector((*p0, 0)), Vector((*p1, 0)); d = p1 - p0; L = d.length
    me = C._ellipsoid('bar_unit', 1, 1, 1, 8, 4) if False else None
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1); me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = C._inst(name, me, mat, Matrix.Translation((p0 + p1) / 2 + Vector((0, 0, z0 + h / 2))) @ Matrix.Rotation(math.atan2(d.y, d.x), 4, 'Z') @ Matrix.Diagonal((L, w, h, 1)), root)
    bv = o.modifiers.new('bv', 'BEVEL'); bv.width = min(w, h) * .25; bv.segments = 2
    return o

def gem_ball(name, r, mat, M, root, facets=2):
    if ('ball%d' % facets) not in bpy.data.meshes:
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=facets, radius=1); me = bpy.data.meshes.new('ball%d' % facets); bm.to_mesh(me); bm.free()
        for p in me.polygons: p.use_smooth = False
    o = bpy.data.objects.new(name, bpy.data.meshes['ball%d' % facets]); J.sc.collection.objects.link(o); o.parent = root
    o.matrix_basis = M @ Matrix.Diagonal((r, r, r, 1))
    me = o.data
    if not me.materials: me.materials.append(None)
    o.material_slots[0].link = 'OBJECT'; o.material_slots[0].material = mat      # per-object: the balls share one mesh
    return o

def M_tint(name, col, ior, absorb=None, d=60):
    return J.principled(name, col, 0, 0, 1, ior, .02, absorb=absorb, absorb_d=d)

def M_earth():
    if 'earth' in bpy.data.materials: return bpy.data.materials['earth']
    m = bpy.data.materials.new('earth'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tx = nt.nodes.new('ShaderNodeTexNoise'); tx.inputs['Scale'].default_value = 3.0; tx.inputs['Detail'].default_value = 8
    cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].position = .6; cr.color_ramp.elements[1].position = .62
    nt.links.new(tx.outputs['Fac'], cr.inputs['Fac']); nt.links.new(cr.outputs['Color'], b.inputs['Metallic'])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.inputs['A'].default_value = (*J.lin('#1B4FC9'), 1); mix.inputs['B'].default_value = (*J.lin('#F2B8A0'), 1)
    nt.links.new(cr.outputs['Color'], mix.inputs['Factor']); nt.links.new(mix.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .12; b.inputs['Coat Weight'].default_value = 1; b.inputs['Coat Roughness'].default_value = .02
    return m

def M_agate():
    if 'agate' in bpy.data.materials: return bpy.data.materials['agate']
    m = bpy.data.materials.new('agate'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    w = nt.nodes.new('ShaderNodeTexWave'); w.wave_type = 'RINGS'; w.inputs['Scale'].default_value = 2.2; w.inputs['Distortion'].default_value = 6
    cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = (*J.lin('#3A1C10'), 1); cr.color_ramp.elements[1].color = (*J.lin('#E8C9A0'), 1)
    nt.links.new(w.outputs['Fac'], cr.inputs['Fac']); nt.links.new(cr.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .08; b.inputs['Coat Weight'].default_value = 1; b.inputs['Coat Roughness'].default_value = .02
    return m

def M_aventurine():
    """Dial floor: deep midnight-blue aventurine with tiny metallic specks (a 'night sky', no printed stars)."""
    if 'aventurine' in bpy.data.materials: return bpy.data.materials['aventurine']
    m = bpy.data.materials.new('aventurine'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    v = nt.nodes.new('ShaderNodeTexVoronoi'); v.inputs['Scale'].default_value = 260
    cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].position = .0; cr.color_ramp.elements[1].position = .06
    cr.color_ramp.elements[0].color = (1, 1, 1, 1); cr.color_ramp.elements[1].color = (0, 0, 0, 1)
    nt.links.new(v.outputs['Distance'], cr.inputs['Fac']); nt.links.new(cr.outputs['Color'], b.inputs['Metallic'])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.inputs['A'].default_value = (*J.lin('#0A1442'), 1); mix.inputs['B'].default_value = (*J.lin('#D9E4FF'), 1)
    nt.links.new(cr.outputs['Color'], mix.inputs['Factor']); nt.links.new(mix.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .3; b.inputs['Coat Weight'].default_value = 1; b.inputs['Coat Roughness'].default_value = .03
    return m

def M_leather():
    if 'leather' in bpy.data.materials: return bpy.data.materials['leather']
    m = bpy.data.materials.new('leather'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*J.lin('#0B1A52'), 1); b.inputs['Roughness'].default_value = .5; b.inputs['Coat Weight'].default_value = .25
    v = nt.nodes.new('ShaderNodeTexVoronoi'); v.feature = 'DISTANCE_TO_EDGE'; v.inputs['Scale'].default_value = 16
    bu = nt.nodes.new('ShaderNodeBump'); bu.inputs['Strength'].default_value = .35; bu.inputs['Distance'].default_value = .02
    nt.links.new(v.outputs['Distance'], bu.inputs['Height']); nt.links.new(bu.outputs['Normal'], b.inputs['Normal'])
    return m

# ---------------------------------------------------------------- the watch
def build(root, strap=True):
    rg, rgm = J.M_rosegold(.08), J.M_rosegold(.22); blk = J.M_black(.3); md = J.M_diamond()
    sap = M_tint('sapphire_cm', '#2F5FE0', 1.77, '#1D3E8C', 350)
    parts = {}
    # case: polished rose-gold middle and bezel, arc window scooped through the bezel at 2 o'clock
    prof = [(1.92, .02), (2.12, 0), (2.22, .12), (2.27, .48), (2.22, .84), (2.12, .98), (2.0, 1.04), (1.92, .98)]
    parts['case'] = C._inst('case', revolve('case', prof, 240, (38, 82, .42)), rg, Matrix.Identity(4), root)
    parts['back'] = C._inst('caseback', revolve('caseback', [(0, -.04), (1.95, -.04), (1.95, .05), (0, .05)], 96), rgm, Matrix.Identity(4), root)
    # dial: aventurine floor + two stepped tiers for the tapered sapphire baguette ring
    C._inst('dial', revolve('dial', [(0, .3), (1.93, .3), (1.93, .36), (0, .36)], 128), M_aventurine(), Matrix.Identity(4), root)
    C._inst('tier1', revolve('tier1', [(1.38, .36), (1.93, .36), (1.93, .48), (1.4, .48)], 192), rgm, Matrix.Identity(4), root)
    C._inst('tier2', revolve('tier2', [(1.66, .48), (1.93, .48), (1.93, .6), (1.68, .6)], 192), rgm, Matrix.Identity(4), root)
    bag = J.baguette('bag_t', taper=.18); sb = []
    for tier, (r0, r1, z, n) in enumerate(((1.42, 1.65, .52, 64), (1.69, 1.9, .64, 72))):
        for i in range(n):
            a = 360 * i / n; L = (r1 - r0) * (1 - .35 * (1 - math.cos(math.radians(a))) / 2)    # taper toward 6 o'clock
            r = r0 + L / 2 + .005
            M = Matrix.Translation(at(a, r, z + .1)) @ Matrix.Rotation(-math.radians(a), 4, 'Z')
            o = bpy.data.objects.new('sap%d_%d' % (tier, i), bag); J.sc.collection.objects.link(o); o.parent = root
            wx = (2 * math.pi * r / n) * .93 / .35; o.matrix_basis = M @ Matrix.Diagonal((wx, L, min(L, .3), 1))
            sb.append(o)
    if not bag.materials: bag.materials.append(sap)
    # black skeleton bridges + rose-gold gear train glimpsed beneath
    hub = Vector((0, 0))
    for a in (95, 250, 330):
        bar('bridge%d' % a, (0, 0), tuple(at(a, 1.38).xy), .24, .07, J.principled('bridge_dark', '#2B2C33', 1, .18), root, .66)
    for k, (a, r, R, t) in enumerate(((60, .55, .32, 28), (130, .42, .26, 22), (290, .6, .3, 26), (200, .35, .2, 18), (10, .3, .18, 16))):
        g = C._inst('gear%d' % k, gear('gear_%d' % t, R, t, .04), rg, Matrix.Translation(at(a, r, .5)), root)
    C._inst('hub', C._ellipsoid('hub', .16, .16, .09, 24, 12), rg, Matrix.Translation((0, 0, .8)), root)
    # flying tourbillon at 7 o'clock: 3-arm cage, balance wheel, upper bridge with the NSKO 'N' cut out
    T = at(210, .9, .42)
    C._inst('tb_ring_lo', C._torus('tbring', 1, .06), rg, Matrix.Translation(T) @ Matrix.Diagonal((.42, .42, .42, 1)), root)
    for i in range(3):
        a = i * 120; p = T + at(a, .38); bar('tb_pillar%d' % i, tuple(p.xy), tuple((p + at(a, .06)).xy), .05, .3, rg, root, T.z)
    bal = C._inst('balance', C._torus('balwheel', 1, .05), rg, Matrix.Translation(T + Vector((0, 0, .17))) @ Matrix.Diagonal((.3, .3, .3, 1)), root)
    for i in range(4): bar('bal_spoke%d' % i, tuple((T + at(45 + 90 * i, .03)).xy), tuple((T + at(45 + 90 * i, .29)).xy), .025, .02, rg, root, T.z + .16)
    tz = T.z + .32
    C._inst('tb_ring_up', C._torus('tbring', 1, .06), rg, Matrix.Translation(T + Vector((0, 0, .32))) @ Matrix.Diagonal((.42, .42, .42, 1)), root)
    s = .27; N = [(-s, -s), (-s, s), (s, -s), (s, s)]
    for i, (p, q) in enumerate(zip(N, N[1:])):                      # the N: left stem, diagonal, right stem
        bar('tbN%d' % i, tuple((T.xy + Vector(p))), tuple((T.xy + Vector(q))), .075, .05, rg, root, tz - .02)
    C._inst('tb_jewel', C._ellipsoid('jewel', .05, .05, .03, 16, 8), M_tint('ruby', '#E0103A', 1.76), Matrix.Translation(T + Vector((0, 0, .36))), root)
    # sub-dial at 1 o'clock: deep blue, rose-gold rim, dot indices, rose-gold hands. No numerals, no text.
    D = at(30, .86, .78)
    C._inst('sub', revolve('subdisc', [(0, -.02), (.5, -.02), (.5, .02), (0, .02)], 96), J.principled('subblue', '#0E2A8A', .3, .25, coat=1), Matrix.Translation(D), root)
    C._inst('sub_rim', C._torus('subrim', 1, .05), rg, Matrix.Translation(D + Vector((0, 0, .02))) @ Matrix.Diagonal((.5, .5, .5, 1)), root)
    for i in range(12): C._inst('idx%d' % i, C._ellipsoid('idx', .025, .025, .012, 10, 6), rg, Matrix.Translation(D + at(i * 30, .42, .03)), root)
    bar('hand_h', tuple(D.xy), tuple((D + at(300, .26)).xy), .045, .015, rg, root, D.z + .03)
    bar('hand_m', tuple(D.xy), tuple((D + at(60, .4)).xy), .03, .015, rg, root, D.z + .05)
    C._inst('sub_pin', C._ellipsoid('pin', .04, .04, .03, 12, 6), rg, Matrix.Translation(D + Vector((0, 0, .07))), root)
    # gem planets on thin rose-gold arms from the centre hub
    planets = [('amethyst', 315, 1.05, .17, M_tint('amethyst', '#9A55F0', 1.54, '#6A2BC9', 300)),
               ('citrine', 100, .95, .18, M_tint('citrine', '#FF9A2E', 1.54, '#E86A0A', 300)),
               ('peridot', 75, 1.25, .14, M_tint('peridot', '#B5E83A', 1.65, '#6FB01A', 300)),
               ('topaz', 150, 1.15, .16, M_tint('bluetopaz', '#5CC4FF', 1.62, '#1E8BE0', 250)),
               ('earth', 125, .66, .2, M_earth()),
               ('agate', 260, 1.2, .15, M_agate())]
    for name, a, r, pr, m in planets:
        P = at(a, r, .9)
        gem_ball('planet_' + name, pr * 1.35, m, Matrix.Translation(P), root, 3 if name in ('earth', 'agate') else 2)
        bar('arm_' + name, (0, 0), tuple(at(a, r - pr * .8).xy), .028, .02, rg, root, .86)
        if name in ('earth', 'agate'):
            for p in bpy.data.objects['planet_' + name].data.polygons: pass
    # domed sapphire crystal
    cr = J.principled('crystal', '#ffffff', 0, 0, 1, 1.15)   # sapphire with anti-reflective coating
    C._inst('crystal', revolve('crystal', [(1.97, 1.0), (1.4, 1.16), (.7, 1.24), (0, 1.26), (0, 1.22), (.7, 1.2), (1.4, 1.12), (1.95, .97)], 128), cr, Matrix.Identity(4), root)
    # lugs: sculpted, three stepped rows of white diamond baguettes each
    bagw = J.baguette('bag_w')
    for sx in (1, -1):
        for sy in (1, -1):
            x0 = sx * 1.42; Ls = 1.55
            M = Matrix.Translation((x0, sy * (1.6 + Ls / 2), .42)) @ Matrix.Diagonal((.6, Ls, .7, 1))
            lug = C._inst('lug%d%d' % (sx, sy), C._ellipsoid('lugbody', .5, .5, .5, 24, 12), rg, M, root)
            for step in range(3):
                xs = x0 + sx * (-.17 + step * .17); zs = .78 - step * .1
                for j in range(4):
                    y = sy * (1.98 + j * .3)
                    o = bpy.data.objects.new('lugbag', bagw); J.sc.collection.objects.link(o); o.parent = root
                    o.matrix_basis = Matrix.Translation((xs, y, zs)) @ Matrix.Diagonal((.29, .29, .29, 1))
                bar('lugrail%d%d%d' % (sx, sy, step), (xs - .085, sy * 1.84), (xs - .085, sy * 2.95), .02, .06, rg, root, zs - .07)
    if not bagw.materials: bagw.materials.append(md)
    # NSKO engraving on the caseband at 9 o'clock
    cu = bpy.data.curves.new('nsko', 'FONT'); cu.body = 'NSKO'; cu.size = .13; cu.extrude = .006; cu.space_character = 1.35; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    try: cu.font = bpy.data.fonts.load(GEIST)
    except Exception: pass
    tx = bpy.data.objects.new('nsko_engraving', cu); J.sc.collection.objects.link(tx); tx.parent = root
    tx.matrix_basis = Matrix.Translation((-2.265, 0, .48)) @ Matrix.Rotation(-math.pi / 2, 4, 'Z') @ Matrix.Rotation(math.pi / 2, 4, 'X')
    cu.materials.append(J.M_rosegold(.35))
    # strap: deep blue alligator-style leather leaving both pairs of lugs and curving down round the wrist
    if strap:
        for sy in (1, -1):
            bm = bmesh.new(); prev = None; w = 2.2
            for i in range(41):
                t = i / 40; y = sy * (2.3 + t * 5.0); z = .3 - 2.6 * t * t; ww = w * (1 - .18 * t)
                ring = [bm.verts.new((x * ww / 2, y, z + dz)) for x, dz in ((-1, -.18), (1, -.18), (1, .18), (-1, .18))]
                if prev:
                    for j in range(4): bm.faces.new((prev[j], prev[(j + 1) % 4], ring[(j + 1) % 4], ring[j]))
                prev = ring
            me = bpy.data.meshes.new('strap%d' % sy); bm.to_mesh(me); bm.free()
            so = C._inst('strap%d' % sy, me, M_leather(), Matrix.Identity(4), root)
            sm = so.modifiers.new('sub', 'SUBSURF'); sm.levels = 2; sm.render_levels = 2
            for p in me.polygons: p.use_smooth = True
    return parts
