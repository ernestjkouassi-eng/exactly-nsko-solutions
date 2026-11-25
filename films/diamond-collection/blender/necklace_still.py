# Checkpoint-2 lighting still: Cuban link on the grey velvet bust, 3/4 view like the source photo.
import sys, os, math; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jlib as J, bpy
from mathutils import Vector
J.reset(); J.world('#08080A', 1)
root = bpy.data.objects.new('root', None); J.sc.collection.objects.link(root); root.scale = (.01, .01, .01)
import cuban as C, necklace as NK
bust = C.build_bust(root)
frames, Ff = NK.build(root); print('front', Ff.translation)
print('units', len(frames))
# backdrop: dark showroom wall, softly lit
bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 1.2, 0), rotation=(math.pi / 2, 0, 0)); bpy.context.active_object.data.materials.append(J.principled('wall', '#16161A', 0, .8))
tgt = (float(os.environ.get('TX', 0)), float(os.environ.get('TY', -.06)), float(os.environ.get('TZ', -.01)))
c, t = J.camera(tuple(float(v) for v in os.environ.get('CAM', '-.36,-1.02,.16').split(',')), tgt, float(os.environ.get('LENS', 100)), float(os.environ.get('F', 5.6)))
if os.environ.get('FOCUS'):
    fo = bpy.data.objects.new('focus', None); J.sc.collection.objects.link(fo); fo.location = tuple(float(v) for v in os.environ['FOCUS'].split(',')); c.data.dof.focus_object = fo
elif True:   # default: focus on the front-centre link of the chain
    fo = bpy.data.objects.new('focus', None); J.sc.collection.objects.link(fo); fo.location = (Ff.translation * .01); c.data.dof.focus_object = fo
J.softboxes(t, 1.1, 6, 8, .6, .7, warm=False); J.overhead(t, .9, 1.0, 3.5, .35)
J.area('top', (0, -.1, 1.0), t, .9, 32)
J.area('rim', (.7, .6, .5), t, .4, 25, (.95, .97, 1))
for k, p in enumerate([(-.5, -.9, .6), (.4, -1.0, .7), (.1, -1.1, .3), (-.8, -.4, .9), (.7, -.5, .3), (0, -.7, 1.1)]): J.spark('s%d' % k, p, 30)
# light linking: the white cards and sparks light only the jewellery, so the velvet stays moody and the stones keep black/white contrast
jewel = bpy.data.collections.new('jewel')
for o in bpy.data.objects:
    if o.parent == root and o is not bust: jewel.objects.link(o)
    elif o.parent and o.parent.parent == root: jewel.objects.link(o)
for o in bpy.data.objects:
    if o.name.startswith(('softbox', 'overhead', 's', 'rim')) and o.name not in ('bust',) and (o.type == 'LIGHT' or o.name.startswith(('softbox', 'overhead'))):
        o.light_linking.receiver_collection = jewel                      # big soft top light on the velvet
J.cycles(tuple(int(v) for v in os.environ.get('RES', '540,960').split(',')), int(os.environ.get('SPP', 64)))
if os.environ.get('BORDER'):
    b = [float(v) for v in os.environ['BORDER'].split(',')]; J.sc.render.use_border = True; J.sc.render.use_crop_to_border = True
    J.sc.render.border_min_x, J.sc.render.border_max_x, J.sc.render.border_min_y, J.sc.render.border_max_y = b
J.sc.render.filepath = sys.argv[-1]; bpy.ops.render.render(write_still=True)
