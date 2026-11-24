# Shared GLB export hook: call export_glb(root, path) after a scene is built (before the studio).
import bpy, os, sys
def export_glb(root, path):
    sc = bpy.context.scene
    bpy.ops.object.select_all(action='DESELECT')
    objs = [o for o in root.children_recursive]
    for o in objs:
        if o.type in ('FONT', 'CURVE'):
            bpy.context.view_layer.objects.active = o; o.select_set(True)
    if bpy.context.selected_objects: bpy.ops.object.convert(target='MESH')
    bpy.ops.object.select_all(action='DESELECT')
    for o in root.children_recursive: o.select_set(True)
    root.select_set(True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, use_selection=True, export_apply=True, export_yup=True, export_materials='EXPORT', export_draco_mesh_compression_enable=False)
    print('glb ok', path); sys.exit(0)
