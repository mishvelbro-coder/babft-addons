bl_info = {
    "name": "BABFT Modern Importer v1.0.6",
    "author": "mishvel",
    "version": (1, 0, 6),
    "blender": (4, 0, 0),
    "location": "File > Import > BABFT importer beta 1.0.6 (.build)",
    "description": "Импортер с автоматическим фоновым запеканием CFrame метаданных.",
    "category": "Import-Export",
}

import bpy, os, json, random
from mathutils import Vector, Matrix
from bpy_extras.io_utils import ImportHelper

def hex_to_rgb(hex_str):
    if not hex_str: return (0.6, 0.6, 0.6, 1.0)
    hex_str = hex_str.strip('#"')
    if len(hex_str) != 6: return (0.6, 0.6, 0.6, 1.0)
    try:
        r = int(hex_str[0:2], 16) / 255.0
        g = int(hex_str[2:4], 16) / 255.0
        b = int(hex_str[4:6], 16) / 255.0
        return (r, g, b, 1.0)
    except ValueError: return (0.6, 0.6, 0.6, 1.0)

def build_mesh_obj_modern(filepath, mesh_vertices, mesh_faces, block_colors_store, use_color, block_meta_store, suffix=""):
    if not mesh_vertices: return
    file_base_name = str(os.path.splitext(os.path.basename(filepath))) + suffix
    mesh_data = bpy.data.meshes.new(name=file_base_name + "_Mesh")
    mesh_data.from_pydata(mesh_vertices, [], mesh_faces)
    mesh_data.update()

    if use_color and block_colors_store:
        color_layer = mesh_data.color_attributes.new(name="BABFT_Color", type='BYTE_COLOR', domain='CORNER')
        corner_colors = []
        for f_idx, poly in enumerate(mesh_data.polygons):
            poly.use_smooth = False
            color = block_colors_store[f_idx]
            for _ in range(len(poly.loop_indices)): corner_colors.extend(color)
        color_layer.data.foreach_set("color", corner_colors)
        mesh_data.update()
    else:
        for poly in mesh_data.polygons: poly.use_smooth = True
        mesh_data.update()
        
    if block_meta_store:
        meta_layer = mesh_data.attributes.new(name="BABFT_IslandMeta", type='STRING', domain='FACE')
        for f_idx, poly in enumerate(mesh_data.polygons):
            meta_layer.data[f_idx].value = block_meta_store[f_idx].encode('utf-8')
        mesh_data.update()
        
    root_obj = bpy.data.objects.new(file_base_name, mesh_data)
    bpy.context.collection.objects.link(root_obj)

def execute_import_modern(filepath, block_limit, import_invisible, use_color, filter_precision, only_mechanisms):
    bpy.ops.ed.undo_push(message="Before BABFT Import")
    with open(filepath, "r", encoding="utf-8-sig", errors="ignore") as f:
        raw_content = f.read().strip()
    if not raw_content: return

    try:
        parsed_json = json.loads(raw_content)
        data_dict = parsed_json.get("Data", parsed_json)
    except Exception: return

    mesh_vertices, mesh_faces, block_colors_store, block_meta_store = [], [], [], []
    inv_vertices, inv_faces, inv_colors_store, inv_meta_store = [], [], [], []
    seen_blocks = set(); actual_blocks, actual_inv = 0, 0

    P = Matrix(((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, -1.0, 0.0), (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))
    P_inv = P.inverted()

    cube_verts = [(-1,-1,-1), (1,-1,-1), (1,1,-1), (-1,1,-1), (-1,-1,1), (1,-1,1), (1,1,1), (-1,1,1)]
    cube_faces = [(0,1,2,3), (4,5,6,7), (0,1,5,4), (2,3,7,6), (1,2,6,5), (0,3,7,4)]
    wedge_verts = [(-1,-1,-1), (1,-1,-1), (1,1,-1), (-1,1,-1), (-1,-1,1), (1,-1,1)]
    wedge_faces = [(0,1,2,3), (0,1,5,4), (2,3,4,5), (0,3,4), (1,2,5)]
    building_keywords = ["Block", "Plate", "Truss", "Brick", "Pole", "Beam", "Wall"]
    for block_name, instances in data_dict.items():
        if not isinstance(instances, list): continue
        is_mechanism = not any(keyword in block_name for keyword in building_keywords)
        if only_mechanisms and not is_mechanism: continue

        for inst in instances:
            if not isinstance(inst, dict) or (actual_blocks + actual_inv) >= block_limit: break
            transparency_val = float(inst.get("Transparency", 0.0))
            is_invisible_block = transparency_val >= 0.95
            if is_invisible_block and not import_invisible and not only_mechanisms: continue

            cf = inst.get("CFrame", []); size_arr = inst.get("Size", [1.0, 1.0, 1.0])
            if len(cf) < 12 or len(size_arr) < 3: continue

            idx_sx, idx_sy, idx_sz = 0, 1, 2
            size_x, size_y, size_z = float(size_arr[idx_sx]), float(size_arr[idx_sy]), float(size_arr[idx_sz])
            if size_x <= 0.001 or size_y <= 0.001 or size_z <= 0.001: continue

            block_id = inst.get("ID", 0)
            if filter_precision != 6 and block_id != 0:
                if block_id in seen_blocks: continue
                seen_blocks.add(block_id)

            i0, i1, i2, i3, i4, i5, i6, i7, i8, i9, i10, i11 = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
            pos_vec = Vector((float(cf[i0]), float(cf[i1]), float(cf[i2])))
            r00, r01, r02 = float(cf[i3]), float(cf[i4]), float(cf[i5])
            r10, r11, r12 = float(cf[i6]), float(cf[i7]), float(cf[i8])
            r20, r21, r22 = float(cf[i9]), float(cf[i10]), float(cf[i11])

            mat_roblox_rot = Matrix(((r00, r01, r02, 0.0), (r10, r11, r12, 0.0), (r20, r21, r22, 0.0), (0.0, 0.0, 0.0, 1.0)))
            gap = 0.0005
            mat_scale = Matrix.Diagonal((max(0.001, size_x/2.0 - gap), max(0.001, size_y/2.0 - gap), max(0.001, size_z/2.0 - gap), 1.0))
            final_matrix = P @ (Matrix.Translation(pos_vec) @ mat_roblox_rot @ mat_scale) @ P_inv
            color_rgba = hex_to_rgb(inst.get("Color", "999999")) if use_color else (0.6, 0.6, 0.6, 1.0)

            is_wedge = "Wedge" in block_name
            base_verts, base_faces = (wedge_verts, wedge_faces) if is_wedge else (cube_verts, cube_faces)
            cf_string = ":".join(f"{float(num):.4f}".rstrip('0').rstrip('.') for num in cf)

            block_pure_meta = {
                "N": block_name, "I": block_id, "C": inst.get("CanCollide", True), "A": inst.get("Anchored", True),
                "T": transparency_val, "S": inst.get("CastShadow", True), "O": cf_string
            }
            if inst.get("MValues"): block_pure_meta["M"] = inst["MValues"]
            if inst.get("Binds"): block_pure_meta["B"] = inst["Binds"]
            meta_string = json.dumps(block_pure_meta, separators=(',', ':'))

            if is_invisible_block:
                v_offset = len(inv_vertices)
                for v in base_verts: inv_vertices.append(final_matrix @ Vector(v))
                for f in base_faces: 
                    inv_faces.append([v_idx + v_offset for v_idx in f]), inv_colors_store.append(color_rgba), inv_meta_store.append(meta_string)
                actual_inv += 1
            else:
                v_offset = len(mesh_vertices)
                for v in base_verts: mesh_vertices.append(final_matrix @ Vector(v))
                for f in base_faces: 
                    mesh_faces.append([v_idx + v_offset for v_idx in f]), block_colors_store.append(color_rgba), block_meta_store.append(meta_string)
                actual_blocks += 1

    build_mesh_obj_modern(filepath, mesh_vertices, mesh_faces, block_colors_store, use_color, block_meta_store, suffix="")
    build_mesh_obj_modern(filepath, inv_vertices, inv_faces, inv_colors_store, use_color, inv_meta_store, suffix="_InvisibleParts")
    
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D': space.shading.color_type = 'VERTEX'
    bpy.ops.ed.undo_push(message="After BABFT Import")

class IMPORT_OT_babft_modern(bpy.types.Operator, ImportHelper):
    bl_idname, bl_label, filename_ext = "import_scene.babft_modern", "BABFT IMPORT", ".build"
    filter_glob: bpy.props.StringProperty(default="*.build", options={'HIDDEN'})
    
    block_limit: bpy.props.IntProperty(name="Лимит блоков", default=90000, min=1, max=250000)
    filter_precision: bpy.props.IntProperty(name="Фильтр ID", default=6, min=1, max=6)
    import_invisible: bpy.props.BoolProperty(name="Импорт невидимых", default=True)
    use_color: bpy.props.BoolProperty(name="Использовать цвета", default=True)
    only_mechanisms: bpy.props.BoolProperty(name="Только механизмы", default=False)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "block_limit")
        layout.prop(self, "filter_precision")
        layout.prop(self, "import_invisible")
        layout.prop(self, "use_color")
        layout.prop(self, "only_mechanisms")

    def execute(self, context):
        execute_import_modern(self.filepath, self.block_limit, self.import_invisible, self.use_color, self.filter_precision, self.only_mechanisms)
        return {'FINISHED'}

def menu_layout_import_func(self, context): self.layout.operator(IMPORT_OT_babft_modern.bl_idname, text="BABFT importer beta 1.0.6 (.build)")
def register(): bpy.utils.register_class(IMPORT_OT_babft_modern); bpy.types.TOPBAR_MT_file_import.append(menu_layout_import_func)
def unregister(): bpy.utils.unregister_class(IMPORT_OT_babft_modern); bpy.types.TOPBAR_MT_file_import.remove(menu_layout_import_func)
if __name__ == "__main__": register()
