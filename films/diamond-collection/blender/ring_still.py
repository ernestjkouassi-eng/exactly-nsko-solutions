# Checkpoint-2 lighting still: marquise ring standing on black velvet.
import sys, os, math; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jlib as J, bpy
J.reset(); J.world('#040405', 1)
root = bpy.data.objects.new('root', None); J.sc.collection.objects.link(root); root.scale = (.01, .01, .01); root.location = (0, 0, .011)
root.rotation_euler = (0, 0, math.radians(float(os.environ.get('RZ', 28))))
import ring as R
stone, band = R.build(root)
bpy.ops.mesh.primitive_plane_add(size=3, location=(0, 0, 0)); floor = bpy.context.active_object; floor.data.materials.append(J.M_velvet('#0C0C0E', .5))
tgt = tuple(float(v) for v in os.environ.get('TGT', '0,0,.016').split(','))
c, t = J.camera(tuple(float(v) for v in os.environ.get('CAM', '-.05,-.17,.09').split(',')), tgt, float(os.environ.get('LENS', 100)), float(os.environ.get('F', 5.6)))
fo = bpy.data.objects.new('focus', None); J.sc.collection.objects.link(fo); fo.location = (0, 0, .011 + .0222); c.data.dof.focus_object = fo
J.softboxes(t, .9, 7, 8, .5, .5); J.overhead(t, .6, .7, 5, .35)
J.area('top', (0, .05, .6), t, .5, 3)
for k, p in enumerate([(-.4, -.5, .5), (.35, -.55, .45), (.1, -.6, .2), (-.6, .1, .6), (.5, .2, .3), (0, -.4, .7), (.2, .5, .6)]): J.spark('s%d' % k, p, 12)
jewel = bpy.data.collections.new('jewel')
for o in bpy.data.objects:
    if o.parent == root or (o.parent and o.parent.parent == root): jewel.objects.link(o)
for o in bpy.data.objects:
    if o.name.startswith(('softbox', 'overhead')) or (o.type == 'LIGHT' and o.name != 'top'): o.light_linking.receiver_collection = jewel
J.cycles(tuple(int(v) for v in os.environ.get('RES', '540,960').split(',')), int(os.environ.get('SPP', 64)))
J.sc.render.filepath = sys.argv[-1]; bpy.ops.render.render(write_still=True)
