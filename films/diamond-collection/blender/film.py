# NSKO Diamond Collection film: renders one shot as a PNG sequence (every 2nd frame at 30 fps, resumable) + callout anchors.
# Usage: SHOT=cuban python3 film.py            (all shots: see SHOTS)
# Only real camera motion and real object motion (parts lifting off and settling back). No overlays here; labels are added in comp.
import sys, os, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jlib as J, bpy
from mathutils import Vector, Matrix

FPS = 30; STEP = int(os.environ.get('STEP', 2)); RES = tuple(int(v) for v in os.environ.get('RES', '720,1280').split(','))
SPP = int(os.environ.get('SPP', 24))
SHOTS = {  # name: (first global frame, last global frame)
    'title_open': (0, 89), 'cuban': (90, 329), 'neck': (330, 479), 'ring': (480, 629), 'watch': (630, 794),
    'hero_cuban': (795, 854), 'hero_neck': (855, 869), 'hero_ring': (870, 884), 'hero_watch': (885, 899), 'title_end': (900, 959)}
OUT = os.environ.get('OUT') or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'render')

def ease(x):
    x = max(0., min(1., x)); return x * x * x * (x * (x * 6 - 15) + 10)           # smootherstep: slow in, slow out

def keys(t, K):
    """K: [(time, value)], eased between keys. value: float or tuple."""
    if t <= K[0][0]: return K[0][1]
    for (t0, a), (t1, b) in zip(K, K[1:]):
        if t <= t1:
            u = ease((t - t0) / (t1 - t0))
            return tuple(x + (y - x) * u for x, y in zip(a, b)) if isinstance(a, tuple) else a + (b - a) * u
    return K[-1][1]

def link_lights(root, extra=()):
    jewel = bpy.data.collections.new('jewel')
    def under(o):
        p = o.parent
        while p:
            if p == root: return True
            p = p.parent
        return False
    for o in bpy.data.objects:
        if under(o) and o.name not in ('bust',) and not o.name.startswith('strap'): jewel.objects.link(o)
    for o in bpy.data.objects:
        if (o.type == 'LIGHT' and o.name not in ('top', 'back', 'strapkey')) or o.name.startswith(('softbox', 'overhead')):
            o.light_linking.receiver_collection = jewel

def new_root(scale=.01, loc=(0, 0, 0)):
    r = bpy.data.objects.new('root', None); J.sc.collection.objects.link(r); r.scale = (scale,) * 3; r.location = loc; return r

def cam_rig(lens=100, fstop=5.6):
    c, t = J.camera((0, -1, 0), (0, 0, 0), lens, fstop)
    fo = bpy.data.objects.new('focus', None); J.sc.collection.objects.link(fo); c.data.dof.focus_object = fo
    return c, t, fo

# ================================================================ scenes
def scene_cuban(hero=False):
    import cuban as C
    J.reset(); J.world('#2C2C30', 1); root = new_root()
    bust = C.build_bust(root); frames, clasp, n = C.build(root, clasp_at=.82)
    bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 1.2, 0), rotation=(math.pi / 2, 0, 0)); bpy.context.active_object.data.materials.append(J.principled('wall', '#55555B', 0, .8))
    c, t, fo = cam_rig(100, 5.6)
    J.softboxes(t, 1.1, 6, 8, .6, .7, warm=True); J.overhead(t, .9, 1.0, 3.5, .35); J.area('top', (0, -.1, 1.0), t, .9, 32)
    J.area('rim', (.7, .6, .5), t, .4, 25, (1, .93, .88))
    for k, p in enumerate([(-.5, -.9, .6), (.4, -1.0, .7), (.1, -1.1, .3), (-.8, -.4, .9), (.7, -.5, .3), (0, -.7, 1.1)]): J.spark('s%d' % k, p, 30)
    fill = J.area('fill', (0, -1, 0), t, .35, 0)
    link_lights(root)
    Fc = C.build.clasp_frame; cn = Fc.col[2].xyz.normalized()
    top, lock = bpy.data.objects['clasp_top'], bpy.data.objects['clasp_lock']
    tw = Matrix.Rotation(math.radians(-18), 4, 'Z') @ Matrix.Rotation(math.radians(24), 4, 'Y')
    G = frames[1] @ tw; zc, _ = C._link_z(.05, .55)
    A = {'18K ROSE GOLD CUBAN LINK': frames[3] @ tw @ Vector((-.1, -1.0, .15)),
         'HALO-SET ROUND BRILLIANTS': G @ Vector((.05, .55, zc + .56 * .43 + .1)),
         'HAND-SET PAVÉ': frames[-2] @ tw @ Vector((.45, 0, C._link_z(.45, 0)[0] + .08)),
         'PEAR-CUT CENTRE CLASP': Fc @ Vector((-.18, 0, .55 + .44 + .1)),
         'HIDDEN BOX LOCK': Fc @ Vector((.2, 0, -.32))}
    clasp_p = Fc.translation * .01
    wide0, wide1 = Vector((.15, -.66, .085)), Vector((.07, -.5, .06))
    cview = clasp_p + (cn * .9 + Vector((0, -.45, 0))).normalized() * .24
    cview2 = clasp_p + (cn * .9 + Vector((0, -.45, 0))).normalized() * .15
    def state(t):
        if hero:            # 2 s full turn on the turntable
            root.rotation_euler = (0, 0, 2 * math.pi * ease(t / 2.0)); campos, tgt, foc = Vector((.12, -.62, .075)), Vector((0, 0, .003)), Vector((0, -.04, -.01)); fill.data.energy = 0
            lab = {}
        else:
            lift = keys(t, [(4.6, 0.), (5.8, .9), (6.6, .9), (7.6, 0.)])          # clasp top lifts off along its normal (cm)
            drop = keys(t, [(5.0, 0.), (6.0, -.45), (6.6, -.45), (7.5, 0.)])      # box lock drops out the other way
            top.location = tuple(cn * lift); lock.location = tuple(cn * drop)
            if t < 3.2:
                u = t / 3.2; campos = wide0.lerp(wide1, ease(u)); tgt = Vector((0, -.02 * ease(u), .003 - .008 * ease(u))); foc = Vector(frames[0].translation * .01)
                fill.data.energy = 0
            else:
                u = ease((t - 3.2) / 1.4); v = ease((t - 4.6) / 3.4)
                campos = wide1.lerp(cview, u).lerp(cview2, v) if t > 4.6 else wide1.lerp(cview, u)
                tgt = Vector((0, -.02, -.005)).lerp(clasp_p + cn * .006, u); foc = Vector(frames[0].translation * .01).lerp(clasp_p + cn * (.009 + lift * .01 * .5), u)
                fill.data.energy = 6 * u
            lab = {k: (A[k], keys(t, [(.8, 0.), (1.3, 1.), (2.7, 1.), (3.1, 0.)])) for k in ('18K ROSE GOLD CUBAN LINK', 'HALO-SET ROUND BRILLIANTS', 'HAND-SET PAVÉ')}
            lab['PEAR-CUT CENTRE CLASP'] = (A['PEAR-CUT CENTRE CLASP'] + Vector((0, 0, 0)) + cn * lift, keys(t, [(5.0, 0.), (5.5, 1.), (7.0, 1.), (7.4, 0.)]))
            lab['HIDDEN BOX LOCK'] = (A['HIDDEN BOX LOCK'] + cn * drop, keys(t, [(5.6, 0.), (6.0, 1.), (7.0, 1.), (7.4, 0.)]))
        return campos, tgt, foc, {k: (root.matrix_world @ (Matrix.Translation(Vector()) @ p.to_4d()).to_3d() if False else root.matrix_world @ p, a) for k, (p, a) in lab.items()}
    return c, t, fo, state

def scene_neck(hero=False):
    import cuban as C, necklace as NK
    J.reset(); J.world('#2C2C30', 1); root = new_root()
    C.set_bust_scale(.74); C.build_bust(root); frames, Ff = NK.build(root)
    bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 1.2, 0), rotation=(math.pi / 2, 0, 0)); bpy.context.active_object.data.materials.append(J.principled('wall', '#55555B', 0, .8))
    c, t, fo = cam_rig(100, 5.6)
    J.softboxes(t, 1.1, 6, 8, .6, .7); J.overhead(t, .9, 1.0, 3.5, .35); J.area('top', (0, -.1, 1.0), t, .9, 32)
    for k, p in enumerate([(-.5, -.9, .6), (.4, -1.0, .7), (.1, -1.1, .3), (-.8, -.4, .9), (.7, -.5, .3), (0, -.7, 1.1)]): J.spark('s%d' % k, p, 30)
    link_lights(root)
    pear = bpy.data.objects['yellow_pear']; pb = pear.matrix_basis.copy(); pn = pb.col[2].xyz.normalized()
    claws = [o for o in bpy.data.objects if o.name.startswith('yellow_pear_claw')]; cb = [o.matrix_basis.copy() for o in claws]
    leaf = bpy.data.objects['leaf004_0'].matrix_basis.translation; rim = bpy.data.objects['leaf006_1'].matrix_basis.translation
    F = Ff.translation; P = pb.translation
    A = {'MARQUISE LEAF LINKS': leaf + Vector((0, -.1, 0)), 'WHITE GOLD SETTING': rim + Vector((.1, -.15, -.1)),
         'YELLOW PEAR DIAMOND': P, 'WHITE DIAMOND HALO': P + pb.col[0].xyz.normalized() * .55}
    def state(t):
        if hero:
            root.rotation_euler = (0, 0, math.radians(-20 + 40 * ease(t / .5))); campos, tgt, foc = Vector((.1, -.55, -.03)), Vector((0, -.07, -.085)), F * .01
            return campos, tgt, foc, {}
        lift = keys(t, [(2.0, 0.), (3.0, .55), (3.6, .55), (4.6, 0.)])
        pear.matrix_basis = Matrix.Translation(pn * lift) @ pb
        for o, b in zip(claws, cb): o.matrix_basis = Matrix.Translation(pn * lift) @ b
        u = ease(t / 5.0)
        tgt = (F * .01).lerp(P * .01, u); campos = tgt + Vector((.07, -.34, .1)).lerp(Vector((.03, -.2, .02)), u)
        foc = tgt
        lab = {'MARQUISE LEAF LINKS': (A['MARQUISE LEAF LINKS'], keys(t, [(.3, 0.), (.7, 1.), (1.8, 1.), (2.2, 0.)])),
               'WHITE GOLD SETTING': (A['WHITE GOLD SETTING'], keys(t, [(.5, 0.), (.9, 1.), (1.8, 1.), (2.2, 0.)])),
               'YELLOW PEAR DIAMOND': (A['YELLOW PEAR DIAMOND'] + pn * lift, keys(t, [(2.7, 0.), (3.1, 1.), (4.3, 1.), (4.7, 0.)])),
               'WHITE DIAMOND HALO': (A['WHITE DIAMOND HALO'], keys(t, [(2.9, 0.), (3.3, 1.), (4.3, 1.), (4.7, 0.)]))}
        return campos, tgt, foc, {k: (root.matrix_world @ p, a) for k, (p, a) in lab.items()}
    return c, t, fo, state

def scene_ring(hero=False):
    import ring as R
    J.reset(); J.world('#040405', 1); root = new_root(loc=(0, 0, .011))
    stone, band = R.build(root)
    bpy.ops.mesh.primitive_plane_add(size=3); bpy.context.active_object.data.materials.append(J.M_velvet('#0C0C0E', .5))
    c, t, fo = cam_rig(100, 5.6)
    J.softboxes(t, .9, 7, 8, .5, .5); J.overhead(t, .6, .7, 5, .35); J.area('top', (0, .05, .6), t, .5, 3)
    for k, p in enumerate([(-.4, -.5, .5), (.35, -.55, .45), (.1, -.6, .2), (-.6, .1, .6), (.5, .2, .3), (0, -.4, .7), (.2, .5, .6)]): J.spark('s%d' % k, p, 12)
    link_lights(root)
    s0 = stone.location.copy(); a = math.radians(-62); n = Vector((math.sin(a), 0, math.cos(a)))
    A = {'MARQUISE CENTRE STONE': Vector((0, .35, R.ZG + .2)), 'PAVÉ BAND': n * (R.RI + .2),
         'MILGRAIN EDGE': n * (R.RI + .232) + Vector((0, -(.27 + .1 * max(0, n.z) ** 1.5) / 2 + .04, 0))}
    claw = bpy.data.objects['claw2_tip']
    def state(t):
        if hero:
            root.rotation_euler = (0, 0, math.radians(40 + 90 * ease(t / .5)))
            return Vector((-.07, -.12, .14)), Vector((0, 0, .02)), Vector((0, 0, .033)), {}
        root.rotation_euler = (0, 0, math.radians(18 + 34 * ease(t / 5.0)))
        lift = keys(t, [(1.4, 0.), (2.6, 1.5), (3.4, 1.5), (4.5, 0.)])     # the centre stone lifts clear of its six claws: the cut-away
        stone.location = s0 + Vector((0, 0, lift))
        u = ease(t / 5.0); campos = Vector((-.08, -.15, .12)).lerp(Vector((-.055, -.105, .105)), u)
        tgt = Vector((0, 0, .02 + .006 * keys(t, [(1.4, 0.), (2.6, 1.), (3.4, 1.), (4.5, 0.)])))
        lab = {'MARQUISE CENTRE STONE': (A['MARQUISE CENTRE STONE'] + Vector((0, 0, lift)), keys(t, [(2.4, 0.), (2.8, 1.), (3.6, 1.), (4.0, 0.)])),
               '6-CLAW PLATINUM SETTING': (claw.matrix_basis.translation, keys(t, [(2.5, 0.), (2.9, 1.), (3.6, 1.), (4.0, 0.)])),
               'PAVÉ BAND': (A['PAVÉ BAND'], keys(t, [(.4, 0.), (.8, 1.), (1.8, 1.), (2.2, 0.)])),
               'MILGRAIN EDGE': (A['MILGRAIN EDGE'], keys(t, [(.6, 0.), (1.0, 1.), (1.8, 1.), (2.2, 0.)]))}
        return campos, tgt, Vector((0, 0, .011 + .0222 + lift * .01)) if 2 < t < 4 else Vector((0, 0, .033)), {k: (root.matrix_world @ p, a) for k, (p, a) in lab.items()}
    return c, t, fo, state

def scene_watch(hero=False):
    import watch as W
    J.reset(); J.world('#050506', 1); root = new_root(); root.rotation_euler = (math.radians(62), 0, math.radians(-18))
    W.build(root)
    bpy.ops.mesh.primitive_plane_add(size=4, location=(0, .25, 0), rotation=(math.pi / 2, 0, 0)); bpy.context.active_object.data.materials.append(J.M_velvet('#111114', .4))
    c, t, fo = cam_rig(100, 8)
    J.softboxes(t, .9, 4.5, 8, .4, .5, warm=True); J.overhead(t, .6, .7, 2.5, .35); J.area('back', (0, .6, .3), t, 1.2, 4); J.area('strapkey', (-.3, -.3, .5), t, .6, 6)
    for k, p in enumerate([(-.4, -.5, .5), (.35, -.55, .45), (.1, -.6, .2), (-.6, -.1, .4), (.5, -.2, .3), (0, -.4, .6), (.2, -.3, -.4)]): J.spark('s%d' % k, p, 12)
    link_lights(root)
    # tourbillon cage turns on its own axis (real motion)
    T = W.at(210, .9, .42); E = bpy.data.objects.new('tb_axis', None); J.sc.collection.objects.link(E); E.parent = root; E.location = T
    for o in list(bpy.data.objects):
        if o.parent == root and o.name.startswith(('tb_', 'balance', 'bal_spoke', 'tbN')) and o is not E:
            mb = o.matrix_basis.copy(); o.parent = E; o.matrix_basis = Matrix.Translation(-T) @ mb
    groups = [(('crystal',), 3.2), (('planet_', 'arm_'), 2.3), (('sub', 'idx', 'hand_'), 1.8), (('tb_axis',), 1.5), (('bridge', 'hub', 'gear'), 1.1), (('sap', 'tier'), .6)]
    G = []
    for pref, dz in groups:
        obs = [o for o in bpy.data.objects if o.parent == root and o.name.startswith(pref)]
        G.append((obs, [o.matrix_basis.copy() for o in obs], dz))
    D = W.at(30, .86, .78)
    A = {'SAPPHIRE CRYSTAL': (W.at(330, 1.2, 1.18), 0), 'SKELETON TOURBILLON': (T + Vector((0, 0, .35)), 3), 'GEMSTONE PLANETS': (W.at(100, .95, .9), 1),
         'BLUE BAGUETTE DIAL': (W.at(160, 1.55, .62), 5), 'DIAMOND BAGUETTE LUGS': (Vector((1.42, -2.3, .8)), None), 'ROSE GOLD CASE': (W.at(250, 2.26, .5), None)}
    def state(t):
        E.rotation_euler = (0, 0, -2 * math.pi * (t + (17 if hero else 0)) / 10.0)
        if hero:
            root.rotation_euler = (math.radians(62), 0, math.radians(-18 + 60 * ease(t / .5)))
            return Vector((0, -.3, 0)), Vector((0, 0, 0)), Vector((0, 0, 0)), {}
        k = 0; off = []
        for i, (obs, mbs, dz) in enumerate(G):
            e = keys(t, [(.9 + i * .1, 0.), (2.2 + i * .1, 1.), (3.6, 1.), (4.8 - i * .08, 0.)]); off.append(dz * e)
            for o, mb in zip(obs, mbs): o.matrix_basis = Matrix.Translation((0, 0, dz * e)) @ mb
        u = ease(t / 5.5); campos = Vector((-.06, -.36, .06)).lerp(Vector((.03, -.26, -.01)), u)
        lab = {}
        for i, (name, (p, gi)) in enumerate(A.items()):
            dz = off[gi] if gi is not None else 0.
            win = [(1.5, 0.), (1.9, 1.), (3.0, 1.), (3.4, 0.)] if i < 3 else [(3.3, 0.), (3.7, 1.), (5.0, 1.), (5.4, 0.)]
            lab[name] = (p + Vector((0, 0, dz)), keys(t, win))
        return campos, Vector((0, 0, .004 * keys(t, [(1, 0.), (2.2, 1.), (3.6, 1.), (4.8, 0.)]))), Vector((0, 0, 0)), {k: (root.matrix_world @ p, a) for k, (p, a) in lab.items()}
    return c, t, fo, state

def scene_title(end=False):
    """The website's own NSKO SOLUTIONS lockup (brand/logo SVG: same shapes, same font, white + the orange fragment),
    extruded as brushed white metal with an orange enamel fragment, revealed by a real light sweeping across it."""
    J.reset(); J.world('#000000', 0)
    bpy.ops.import_curve.svg(filepath='/home/user/nsko-solutions/brand/logo/nsko-solutions-lockup-white.svg')
    cur = [o for o in bpy.data.objects if o.type == 'CURVE']
    white = J.principled('logo_white', '#F4F5F7', 1, .2)
    bw = white.node_tree.nodes['Principled BSDF']
    if 'Anisotropic' in bw.inputs: bw.inputs['Anisotropic'].default_value = .8
    orange = J.principled('logo_orange', '#E8541A', 0, .28, coat=1)
    lo = Vector((1e9, 1e9, 0)); hi = Vector((-1e9, -1e9, 0))
    for o in cur:
        col = o.data.materials[0].diffuse_color if o.data.materials else (1, 1, 1, 1)
        o.data.materials.clear(); o.data.materials.append(orange if (col[0] > .5 and col[2] < .3) else white)
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c); lo = Vector((min(lo.x, w.x), min(lo.y, w.y), 0)); hi = Vector((max(hi.x, w.x), max(hi.y, w.y), 0))
    k = .25 / (hi.x - lo.x); ctr = (lo + hi) / 2
    grp = bpy.data.objects.new('logo', None); J.sc.collection.objects.link(grp)
    for o in cur:
        o.data.extrude = .0016 / k; o.data.bevel_depth = .0003 / k; o.data.bevel_resolution = 3
        o.parent = grp; o.location = o.location - ctr
    grp.scale = (k, k, k); grp.rotation_euler = (math.pi / 2, 0, 0)
    bpy.context.view_layer.update(); xs, zs = [], []
    for o in cur:
        for cb in o.bound_box: w = o.matrix_world @ Vector(cb); xs.append(w.x); zs.append(w.z)
    grp.location = (-(min(xs) + max(xs)) / 2, 0, -(min(zs) + max(zs)) / 2)
    bpy.ops.mesh.primitive_plane_add(size=4, location=(0, .2, 0), rotation=(math.pi / 2, 0, 0)); bpy.context.active_object.data.materials.append(J.principled('black_set', '#010101', 0, .9)); _bs = bpy.data.materials['black_set'].node_tree.nodes['Principled BSDF']; _bs.inputs['Specular IOR Level'].default_value = 0
    c, t, fo = cam_rig(85, 5.6)
    bar = J.area('sweep', (0, -.35, .25), t, .06, 60, (1, .97, .94), shape='RECTANGLE', sx=1.2)
    bar.data.size = .06; bar.data.size_y = 1.2
    fill = J.area('fill', (0, -1.2, .3), t, 1.0, 0)
    for L_ in (bar, fill): L_.visible_camera = False
    def state(tt):
        dur = 3.0 if not end else 2.0
        x = keys(tt, [(0, -.6), (dur * .85, .6)]) if not end else keys(tt, [(0, .6), (dur * .8, -.25)])
        bar.location = (x, -.35, .2); bar.data.energy = 60 * keys(tt, [(0, 0.), (.4, 1.)])
        fill.data.energy = 6 * keys(tt, [(dur * .5, 0.), (dur, 1.)]) if not end else 6.
        campos = Vector((0, -1.5, .0)).lerp(Vector((0, -1.36, .0)), ease(tt / dur))
        return campos, Vector((0, 0, 0)), Vector((0, -.004, 0)), {}
    return c, t, fo, state

def main():
    shot = os.environ['SHOT']; f0, f1 = SHOTS[shot]
    base = shot.replace('hero_', '')
    hero = shot.startswith('hero_')
    if base == 'title_open': c, t, fo, st = scene_title(False)
    elif base == 'title_end': c, t, fo, st = scene_title(True)
    else: c, t, fo, st = {'cuban': scene_cuban, 'neck': scene_neck, 'ring': scene_ring, 'watch': scene_watch}[base](hero)
    J.cycles(RES, SPP); J.sc.render.image_settings.file_format = 'PNG'
    J.sc.render.use_motion_blur = False
    od = os.path.join(OUT, shot); os.makedirs(od, exist_ok=True)
    from bpy_extras.object_utils import world_to_camera_view
    anc = {}
    ap = os.path.join(od, 'anchors.json')
    if os.path.exists(ap): anc = json.load(open(ap))
    for f in range(f0, f1 + 1):
        if os.environ.get('ONLY') and str(f) not in os.environ['ONLY'].split(','): continue
        if (f - f0) % STEP and f != f1: continue
        tt = (f - f0) / FPS
        campos, tgt, foc, labs = st(tt)
        c.location = campos; t.location = tgt; fo.location = foc
        bpy.context.view_layer.update()
        a = {}
        for k, (p, alpha) in labs.items():
            if alpha <= 0: continue
            v = world_to_camera_view(J.sc, c, p); a[k] = [v.x, 1 - v.y, alpha]
        anc[str(f)] = a
        fn = os.path.join(od, 'f%04d.png' % f)
        if not os.path.exists(fn):
            J.sc.render.filepath = fn; bpy.ops.render.render(write_still=True)
        json.dump(anc, open(ap, 'w'))
        print('frame', f, flush=True)

main()
