# Checkpoint-2 lighting still + design sheet views: NSKO Celestial Tourbillon on a charcoal set.
import sys, os, math; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jlib as J, bpy
J.reset(); J.world('#050506', 1)
root = bpy.data.objects.new('root', None); J.sc.collection.objects.link(root); root.scale = (.01, .01, .01)
root.rotation_euler = tuple(math.radians(float(v)) for v in os.environ.get('ROT', '62,0,-18').split(','))
import watch as W
W.build(root)
bpy.ops.mesh.primitive_plane_add(size=4, location=(0, .25, 0), rotation=(math.pi / 2, 0, 0)); bpy.context.active_object.data.materials.append(J.M_velvet('#111114', .4))
c, t = J.camera(tuple(float(v) for v in os.environ.get('CAM', '0,-.34,.02').split(',')), tuple(float(v) for v in os.environ.get('TGT', '0,0,0').split(',')), float(os.environ.get('LENS', 100)), float(os.environ.get('F', 8)))
J.softboxes(t, .9, 4.5, 8, .4, .5, warm=True); J.overhead(t, .6, .7, 2.5, .35)
J.area('back', (0, .6, .3), t, 1.2, 4); J.area('strapkey', (-.3, -.3, .5), t, .6, 6)
for k, p in enumerate([(-.4, -.5, .5), (.35, -.55, .45), (.1, -.6, .2), (-.6, -.1, .4), (.5, -.2, .3), (0, -.4, .6), (.2, -.3, -.4)]): J.spark('s%d' % k, p, 12)
jewel = bpy.data.collections.new('jewel')
for o in bpy.data.objects:
    if o.parent == root and not o.name.startswith('strap'): jewel.objects.link(o)
for o in bpy.data.objects:
    if o.name.startswith(('softbox', 'overhead')) or (o.type == 'LIGHT' and o.name != 'back'): o.light_linking.receiver_collection = jewel
if os.environ.get('NOCRYSTAL'): bpy.data.objects['crystal'].hide_render = True
J.cycles(tuple(int(v) for v in os.environ.get('RES', '540,960').split(',')), int(os.environ.get('SPP', 64)))
J.sc.render.filepath = sys.argv[-1]; bpy.ops.render.render(write_still=True)
