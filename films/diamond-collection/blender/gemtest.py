import sys, os, math; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import jlib as J
from mathutils import Vector
J.reset(); J.world('#050506')
fl = J.bpy.data.objects.new('floor', J.bpy.data.meshes.new('f')); 
import bpy
bpy.ops.mesh.primitive_plane_add(size=2); bpy.context.active_object.data.materials.append(J.M_velvet())
for i, (shape, x) in enumerate([('round', -.3), ('pear', 0), ('marquise', .3)]):
    J.stone(shape, J.brilliant('cut_' + shape, shape, 48 if shape != 'round' else 32), J.M_yellow() if shape == 'pear' else J.M_diamond(), .2, (x, 0, .06), (0, 0, 0))
J.stone('bag', J.baguette('bag'), J.M_sapphire(), .2, (0, .35, .05), (0, 0, math.radians(90)))
pts = [(-.4 + (i % 24) * .035, -.35 - (i // 24) * .035, .005) for i in range(72)]; J.pave('pv', pts, [(0, 0, 1)] * 72, J.brilliant('cut_round', 'round', 32), J.M_diamond(), .03)
bpy.ops.mesh.primitive_plane_add(size=.9, location=(0, -.38, .003)); bpy.context.active_object.scale = (1, .14, 1); bpy.context.active_object.data.materials.append(J.M_rosegold())
c, t = J.camera((0, -.35, 1.7), (0, 0, 0), 50, 11); J.softboxes(t, 1.4, 5, 6); J.overhead(t, 1.1, 1.2, 4)
J.area('key', (-1, -1, 1.5), t, .6, 60); J.area('rim', (1, 1, 1), t, .5, 40, (1, .95, .9))
for k, p in enumerate([(-.6, -1.2, .9), (.7, -1.1, 1.2), (.2, -1.4, .4), (-.3, .8, 1.2), (.9, .3, .6)]): J.spark('s%d' % k, p, 25)
J.cycles((900, 900), int(os.environ.get('SPP', 128)))
J.sc.render.filepath = sys.argv[-1]; bpy.ops.render.render(write_still=True)
