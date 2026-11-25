# NSKO Diamond Collection: shared jewellery library (Blender 5, Cycles).
# Real faceted cuts (round brilliant, pear, marquise, baguette), physically based metals and stones, vertex instancing for pavé.
import bpy, bmesh, math, os
from mathutils import Vector, Matrix
sc = bpy.context.scene

def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c)

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    global sc; sc = bpy.context.scene; return sc

# ------------------------------------------------------------------ materials
_M = {}
def principled(name, col='#ffffff', metal=0., rough=.1, trans=0., ior=1.45, disp=0., coat=0., emit=0., sheen=0., absorb=None, absorb_d=1.0):
    if name in _M: return _M[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*lin(col), 1); b.inputs['Metallic'].default_value = metal; b.inputs['Roughness'].default_value = rough
    if trans:
        b.inputs['Transmission Weight'].default_value = trans; b.inputs['IOR'].default_value = ior
    if disp and 'Dispersion' in b.inputs: b.inputs['Dispersion'].default_value = disp
    if coat: b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = .03
    if sheen: b.inputs['Sheen Weight'].default_value = sheen; b.inputs['Sheen Roughness'].default_value = .35; b.inputs['Sheen Tint'].default_value = (*lin(col), 1) if 'Sheen Tint' in b.inputs else None
    if emit: b.inputs['Emission Color'].default_value = (*lin(col), 1); b.inputs['Emission Strength'].default_value = emit
    if absorb:  # coloured stones: tint by volume absorption, not by a painted surface
        out = nt.nodes['Material Output']; v = nt.nodes.new('ShaderNodeVolumeAbsorption')
        v.inputs['Color'].default_value = (*lin(absorb), 1); v.inputs['Density'].default_value = absorb_d; nt.links.new(v.outputs[0], out.inputs['Volume'])
    _M[name] = m; return m

def M_diamond(): return principled('diamond', '#ffffff', 0, 0, 1, 2.417, .045)          # Abbe ~55: dispersion from R/G/B 2.407/2.417/2.451
def M_yellow(): return principled('yellow_diamond', '#ffffff', 0, 0, 1, 2.417, .045, absorb='#F2C230', absorb_d=6)
def M_sapphire(): return principled('blue_sapphire', '#ffffff', 0, 0, 1, 1.77, .02, absorb='#2F63E0', absorb_d=7)
def M_gem(name, col, ior, dens=7): return principled(name, '#ffffff', 0, 0, 1, ior, .02, absorb=col, absorb_d=dens)
def M_rosegold(r=.11): return principled('rose_gold_%d' % int(r * 100), '#F2B8A0', 1, r)
def M_platinum(r=.1): return principled('platinum_%d' % int(r * 100), '#E3E5E8', 1, r)
def M_black(r=.35): return principled('black_metal_%d' % int(r * 100), '#141417', 1, r)
def M_velvet(col='#0E0E10', sheen=.6): return principled('velvet_' + col, col, 0, .95, sheen=sheen)

# ------------------------------------------------------------------ cuts
def _outline(shape, n):
    """Girdle outline, unit size (length along +y = 1 for fancy shapes, radius .5 for round)."""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        if shape == 'round': pts.append((.5 * math.cos(t), .5 * math.sin(t)))
        elif shape == 'marquise':    # vesica: two circular arcs meeting in sharp points; width/length 0.45
            R = .668; y = .5 * math.cos(t); x = math.sqrt(max(0, R * R - y * y)) - math.sqrt(R * R - .25)
            pts.append((math.copysign(x, math.sin(t)) if abs(math.sin(t)) > 1e-9 else 0, y))
        elif shape == 'pear':        # teardrop: point at +y, round at -y; width/length 0.62
            y = .5 * math.cos(t); x = (.31 / .7698) * math.sin(t) * math.sin(t / 2)
            pts.append((x, y))
    return pts

def brilliant(name, shape='round', n=32, table=.56, crown=.15, pav=.43, girdle=.02):
    """Faceted brilliant: table polygon, star+kite crown ring, thin girdle band, pavilion to a culet. Size 1 across the long axis."""
    if name in bpy.data.meshes: return bpy.data.meshes[name]
    bm = bmesh.new(); O = _outline(shape, n)
    g_top = [bm.verts.new((x, y, girdle / 2)) for x, y in O]
    g_bot = [bm.verts.new((x, y, -girdle / 2)) for x, y in O]
    mid = [bm.verts.new((x * (.5 + table / 2), y * (.5 + table / 2), girdle / 2 + crown * .55)) for x, y in O[::2]]   # crown break (kites)
    tab = [bm.verts.new((x * table, y * table, girdle / 2 + crown)) for x, y in O[::2]]
    m = len(tab)
    bm.faces.new(tab)                                                                    # table
    for i in range(m):
        a, b = i, (i + 1) % m
        bm.faces.new((tab[a], mid[a], mid[b], tab[b]))                                   # star/bezel band
        g0, g1, g2 = g_top[2 * a], g_top[2 * a + 1], g_top[(2 * a + 2) % n]
        bm.faces.new((mid[a], g0, g1)); bm.faces.new((mid[a], g1, mid[b])); bm.faces.new((mid[b], g1, g2))  # upper girdle facets
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((g_top[i], g_bot[i], g_bot[j], g_top[j]))        # girdle
    pm = [bm.verts.new((x * .45, y * .45, -girdle / 2 - pav * .55)) for x, y in O[::2]]  # pavilion mains break
    cul = bm.verts.new((0, 0, -girdle / 2 - pav))
    for i in range(m):
        a, b = i, (i + 1) % m
        g0, g1, g2 = g_bot[2 * a], g_bot[2 * a + 1], g_bot[(2 * a + 2) % n]
        bm.faces.new((g1, g0, pm[a])); bm.faces.new((g2, g1, pm[b])); bm.faces.new((pm[a], g1, pm[b]))     # lower girdle facets
        bm.faces.new((pm[b], cul, pm[a]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = False
    return me

def baguette(name, taper=0., steps=3):
    """Step-cut baguette, 1 long x .35 wide, optional taper (tapered baguette)."""
    if name in bpy.data.meshes: return bpy.data.meshes[name]
    bm = bmesh.new(); L, W = .5, .175
    def ring(s, z, tp):
        return [bm.verts.new(v) for v in ((-W * s * (1 - tp), -L * s, z), (W * s * (1 - tp), -L * s, z), (W * s, L * s, z), (-W * s, L * s, z))]
    rings = [ring(1, .015, taper), ring(1, -.015, taper)]
    top = [ring(1 - .12 * k, .015 + .05 * k, taper) for k in range(1, steps + 1)]
    bot = [ring(1 - .26 * k, -.015 - .1 * k, taper) for k in range(1, steps + 1)]
    seq_up = [rings[0]] + top; seq_dn = [rings[1]] + bot
    def bridge(A, B):
        for i in range(4): bm.faces.new((A[i], A[(i + 1) % 4], B[(i + 1) % 4], B[i]))
    bridge(rings[1], rings[0])
    for a, b in zip(seq_up, seq_up[1:]): bridge(a, b)
    for a, b in zip(seq_dn, seq_dn[1:]): bridge(b, a)
    bm.faces.new(seq_up[-1]); bm.faces.new(list(reversed(seq_dn[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); return me

def stone(name, mesh, mat, size, loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, mesh); o.scale = (size, size, size); o.location = loc; o.rotation_euler = rot
    if not mesh.materials: mesh.materials.append(mat)
    sc.collection.objects.link(o)
    if parent: o.parent = parent
    return o

# ------------------------------------------------------------------ pavé by vertex instancing
def pave(name, pts, normals, gem_mesh, mat, size, parent=None, seat=True, seat_mat=None):
    """One emitter mesh whose vertices carry the stone positions; the gem is instanced on every vertex, aligned to the vertex normal.
    seat=True adds a tiny prong bead ring per stone so pavé reads as set metal, not floating glass."""
    me = bpy.data.meshes.new(name + '_pts')
    emitter = bpy.data.objects.new(name, me); sc.collection.objects.link(emitter)
    if parent: emitter.parent = parent
    # store normals as a face-less mesh: Blender uses vertex normals for instance rotation; build tiny tris so normals are defined
    bm = bmesh.new()
    for p, n in zip(pts, normals):
        n = Vector(n).normalized(); t = n.orthogonal().normalized() * 1e-5; u = n.cross(t).normalized() * 1e-5; P = Vector(p)
        a, b, c = bm.verts.new(P), bm.verts.new(P + t), bm.verts.new(P + u)
        f = bm.faces.new((a, b, c))
        if f.normal.dot(n) < 0: f.normal_flip()
    bm.to_mesh(me); bm.free()
    emitter.instance_type = 'FACES'; emitter.use_instance_faces_scale = False
    child = bpy.data.objects.new(name + '_gem', gem_mesh); child.scale = (size, size, size); sc.collection.objects.link(child); child.parent = emitter
    if not gem_mesh.materials: gem_mesh.materials.append(mat)
    emitter.hide_render = False; child.hide_render = False
    return emitter

# ------------------------------------------------------------------ studio
def camera(loc, target, lens=100, fstop=4.0, sensor=36):
    t = bpy.data.objects.new('target', None); sc.collection.objects.link(t); t.location = target
    c = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(c); sc.camera = c
    c.location = loc; c.data.lens = lens; c.data.sensor_width = sensor
    k = c.constraints.new('TRACK_TO'); k.target = t; k.track_axis = 'TRACK_NEGATIVE_Z'; k.up_axis = 'UP_Y'
    c.data.dof.use_dof = True; c.data.dof.focus_object = t; c.data.dof.aperture_fstop = fstop
    return c, t

def area(name, loc, target, size, energy, col=(1, 1, 1), spread=180, shape='RECTANGLE', sx=None):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.color = col; l.shape = shape; l.size = size
    if sx: l.size_y = sx
    l.spread = math.radians(spread)
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
    tr = o.constraints.new('TRACK_TO'); tr.target = target; tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
    return o

def spark(name, loc, energy, radius=.002):
    """Tiny hard point lights: these are what make diamonds throw crisp fire."""
    l = bpy.data.lights.new(name, 'POINT'); l.energy = energy; l.shadow_soft_size = radius
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc; return o

def world(col='#050506', strength=1.0):
    w = sc.world = bpy.data.worlds.new('w'); w.use_nodes = True; bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = (*lin(col), 1); bg.inputs[1].default_value = strength; return w

def cycles(res=(1620, 2880), spp=256, threads=4, bounces=16):
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = spp; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = .01
    sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.max_bounces = bounces; sc.cycles.transmission_bounces = bounces; sc.cycles.glossy_bounces = 8; sc.cycles.diffuse_bounces = 2
    sc.cycles.caustics_reflective = True; sc.cycles.caustics_refractive = True; sc.cycles.blur_glossy = .3
    sc.cycles.sample_clamp_indirect = 20
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.render.threads_mode = 'FIXED'; sc.render.threads = threads
    sc.view_settings.view_transform = 'AgX'
    try: sc.view_settings.look = 'AgX - Base Contrast'
    except Exception: pass
    sc.render.film_transparent = False

def softboxes(target, dist=1.6, strength=6, n=5, height=.9, size=.9, warm=False, visible_camera=False):
    """Jewellery studio: big white cards around the piece, seen only in reflections. They give metal its shine and diamonds their white flashes."""
    import random; random.seed(7); out = []
    for i in range(n):
        a = 2 * math.pi * (i + .5) / n + .3
        bpy.ops.mesh.primitive_plane_add(size=size, location=(target.location.x + math.cos(a) * dist, target.location.y + math.sin(a) * dist, target.location.z + height * (.6 + .5 * (i % 2))))
        o = bpy.context.active_object; o.name = 'softbox%d' % i
        tr = o.constraints.new('TRACK_TO'); tr.target = target; tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
        col = '#FFF1E6' if warm and i % 2 else '#FFFFFF'
        o.data.materials.append(principled('softbox_' + col + str(strength), col, 0, 1, emit=strength))
        o.visible_camera = visible_camera; o.visible_shadow = False; out.append(o)
    return out

def overhead(target, h=1.3, size=1.4, strength=5, hole=.45):
    """Overhead ring light with a dark centre (the camera's hole): gives brilliants their black-and-white arrow pattern."""
    bm = bmesh.new(); n = 48; R, r = size / 2, size * hole / 2
    outer = [bm.verts.new((R * math.cos(2 * math.pi * i / n), R * math.sin(2 * math.pi * i / n), 0)) for i in range(n)]
    inner = [bm.verts.new((r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n), 0)) for i in range(n)]
    for i in range(n): j = (i + 1) % n; bm.faces.new((outer[i], outer[j], inner[j], inner[i]))
    me = bpy.data.meshes.new('overhead'); bm.to_mesh(me); bm.free(); o = bpy.data.objects.new('overhead', me); sc.collection.objects.link(o)
    o.location = (target.location.x, target.location.y, target.location.z + h); o.rotation_euler = (math.pi, 0, 0)
    o.data.materials.append(principled('overhead%d' % strength, '#FFFFFF', 0, 1, emit=strength)); o.visible_camera = False; o.visible_shadow = False; return o
