bl_info = {
    "name": "BABFT Export (june 20) v1.0.9",
    "author": "mishvel",
    "version": (1, 0, 9),
    "blender": (4, 0, 0),
    "location": "File > Export",
    "category": "Import-Export"
}

import bpy, bmesh, os, json, random
from mathutils import Vector, Matrix
from bpy_extras.io_utils import ExportHelper

B_TYPES = [
    ("PlasticBlock", "Plastic", ""), ("GlassBlock", "Glass", ""), ("MetalBlock", "Metal", ""),
    ("NeonBlock", "Neon", ""), ("ConcreteBlock", "Concrete", ""), ("WoodBlock", "Wood", ""),
    ("SmoothWoodBlock", "Smooth Wood", ""), ("LightBulb", "Light Bulb", ""), ("Delay", "Delay", ""),
    ("Note", "Note", ""), ("Seat", "Seat", ""), ("CoalBlock", "Coal", ""), ("GoldBlock", "Gold", ""),
    ("MarbleBlock", "Marble", ""), ("IceBlock", "Ice", ""), ("FabricBlock", "Fabric", ""),
    ("GrassBlock", "Grass", ""), ("Piston", "Piston", ""), ("Lamp", "Lamp", ""),
    ("ObsidianBlock", "Obsidian", ""), ("TitaniumBlock", "Titanium", ""), ("Sign", "Sign", ""),
    ("Switch", "Switch", ""), ("Portal", "Portal", ""), ("Candle", "Candle", ""),
    ("Throne", "Throne", ""), ("Motor", "Motor", ""), ("Hinge", "Hinge", ""), ("Wedge", "Wedge", "")
]

class EXPORT_OT_babft_ultimate(bpy.types.Operator, ExportHelper):
    bl_idname, bl_label, filename_ext = "export_scene.babft_ultimate", "BABFT – Export", ".build"
    filter_glob: bpy.props.StringProperty(default="*.build", options={'HIDDEN'})
    
    block_limit: bpy.props.IntProperty(
        name="1.1 Лимит Блоков", 
        description="Максимальное количество блоков, которое экспортер запишет в файл. Защищает игру от лагов",
        default=250000, min=1, max=500000
    )
    round_precision: bpy.props.IntProperty(
        name="1.2 Точность округления", 
        description="Количество знаков после запятой для CFrame и размеров. 3 знака убирают микро-щели в игре",
        default=3, min=0, max=6
    )
    min_block_size: bpy.props.FloatProperty(
        name="1.3 Мин. размер блока", 
        description="Игнорировать блоки, которые меньше этого размера (в studs). Полезно для очистки меша от мусора",
        default=0.01, min=0.0
    )
    invert_y_axis: bpy.props.BoolProperty(
        name="1.4 Инверсия оси Y (Вверх ногами)", 
        description="Зеркально разворачивает всю модель по оси Y движка игры при экспорте",
        default=False
    )
    color_mode: bpy.props.EnumProperty(
        name="2.1 Режим цвета", 
        description="LOCAL — берет цвета оригинальной модели (если он есть). GLOBAL — принудительно красит всю модель в цвет из палитры",
        items=[('LOCAL', "Локальный цвет фейсов", ""), ('GLOBAL', "Мировой цвет", "")], default='LOCAL'
    )
    global_color: bpy.props.FloatVectorProperty(
        name="Цвет палитры", subtype='COLOR', 
        description="Выберите цвет, в который будет принудительно перекрашена вся модель (работает в режиме Мировой цвет)",
        default=(1.0, 1.0, 1.0), min=0.0, max=1.0
    )
    mat_mode: bpy.props.EnumProperty(
        name="2.2 Режим материала", 
        description="LOCAL — сохраняет материалы из модели(если были сохранены). GLOBAL — принудительно превращает всю модель в один материал",
        items=[('LOCAL', "Локальные материалы островков", ""), ('GLOBAL', "Мировой материал", "")], default='LOCAL'
    )
    global_material: bpy.props.EnumProperty(
        name="Материал", items=B_TYPES, 
        description="Выберите игровой материал, в который превратится вся модель (работает в режиме Мировой материал)",
        default="PlasticBlock"
    )
    change_material: bpy.props.BoolProperty(
        name="2.3 Включить замену материалов", 
        description="Активирует функцию умной подмены. Позволяет автоматически заменить один тип блоков на другой",
        default=False
    )
    find_material: bpy.props.EnumProperty(
        name="Искать", items=B_TYPES, 
        description="Выберите тип блока, который экспортер должен найти в модели для последующей замены",
        default="WoodBlock"
    )
    replace_material: bpy.props.EnumProperty(
        name="Заменить на", items=B_TYPES, 
        description="Выберите материал, в который превратятся все найденные блоки из поля 'Искать'",
        default="MetalBlock"
    )
    collision_mode: bpy.props.EnumProperty(
        name="3.1 Коллизия", 
        description="LOCAL — берет коллизию из памяти. TRUE/FALSE — принудительно включает или отключает физику всей моделе",
        items=[('LOCAL', "Локальная (Из метаданных)", ""), ('TRUE', "Мировая (Включена всегда)", ""), ('FALSE', "Мировая (Отключена)", "")], default='LOCAL'
    )
    transparency_limit: bpy.props.FloatProperty(
        name="3.2 Лимит прозрачности", 
        description="Блоки с прозрачностью выше этого значения будут полностью вырезаны из файла. 1.0 — экспортировать всё",
        default=1.00, min=0.0, max=1.0
    )
    shadow_mode: bpy.props.EnumProperty(
        name="3.3 Отбрасывание теней", 
        description="LOCAL — тени записанные в мето данных. TRUE/FALSE — принудительно включает или выключает тени у всей модели",
        items=[('LOCAL', "Локальные тени", ""), ('TRUE', "Включить тени всем", ""), ('FALSE', "Отключить тени всем", "")], default='LOCAL'
    )
    export_logic: bpy.props.BoolProperty(
        name="3.4 Логика механизмов (Binds/MValues)", 
        description="Включено — экспортирует скорость поршней и привязки кнопок. Выключено — стирает провода для экономии веса файла",
        default=True
    )
    file_format: bpy.props.EnumProperty(
        name="4.1 Формат файла", 
        description="V1_FORMAT — полный файл с логикой и маркером Version V1 (script Butter). SIMPLE — легкая версия без ID и настроек",
        items=[('V1_FORMAT', "Modern Data Format (V1)", ""), ('SIMPLE', "Simple Version (No Meta)", "")], default='V1_FORMAT'
    )

    def draw(self, context):
        layout = self.layout
        b1 = layout.box(); b1.label(text="1. Геометрия постройки", icon='MESH_CUBE'); b1.prop(self, "block_limit"); b1.prop(self, "round_precision"); b1.prop(self, "min_block_size"); b1.prop(self, "invert_y_axis")
        b2 = layout.box(); b2.label(text="2. Цвет и материалы", icon='MATERIAL'); b2.prop(self, "color_mode")
        if self.color_mode == 'GLOBAL': b2.prop(self, "global_color")
        b2.prop(self, "mat_mode")
        if self.mat_mode == 'GLOBAL': b2.prop(self, "global_material")
        b2.prop(self, "change_material")
        if self.change_material: b2.prop(self, "find_material"); b2.prop(self, "replace_material")
        b3 = layout.box(); b3.label(text="3. Данные блоков (Meta Data)", icon='TRACKING'); b3.prop(self, "collision_mode"); b3.prop(self, "transparency_limit"); b3.prop(self, "shadow_mode"); b3.prop(self, "export_logic")
        b4 = layout.box(); b4.label(text="4. Выбор типа файла", icon='FILE_TEXT'); b4.prop(self, "file_format")
    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH': return {'CANCELLED'}
        mesh = obj.data; bm = bmesh.new(); bm.from_mesh(mesh); bm.faces.ensure_lookup_table(); bm.verts.ensure_lookup_table()
        meta_layer = mesh.attributes.get("BABFT_IslandMeta"); color_layer = mesh.color_attributes.get("BABFT_Color")
        vert_to_faces = {}; output_data = {}; unvisited = set(f.index for f in bm.faces)
        for face in bm.faces:
            for v in face.verts: vert_to_faces.setdefault(v.index, []).append(face.index)
        P_pos = Matrix(((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0))); blocks_counter, prec = 0, self.round_precision
        col_r, col_g, col_b = 0, 1, 2
        g_hex = f"{int(self.global_color[col_r]*255):02x}{int(self.global_color[col_g]*255):02x}{int(self.global_color[col_b]*255):02x}".upper()
        
        while unvisited and blocks_counter < self.block_limit:
            start_idx = unvisited.pop(); queue, island_indices = [start_idx], [start_idx]
            while queue:
                curr_idx = queue.pop(0)
                for v in bm.faces[curr_idx].verts:
                    for linked_idx in vert_to_faces[v.index]:
                        if linked_idx in unvisited: unvisited.remove(linked_idx); island_indices.append(linked_idx); queue.append(linked_idx)
            
            base_face_idx = island_indices[0]
            meta = {}
            if meta_layer and meta_layer.data[base_face_idx].value:
                try: meta = json.loads(meta_layer.data[base_face_idx].value.decode('utf-8').strip())
                except: pass
            transparency_val = float(meta.get("T", 0.0))
            if transparency_val > self.transparency_limit: continue
            mat = meta.get("N", "PlasticBlock")
            if self.mat_mode == 'GLOBAL': mat = self.global_material
            if self.change_material and mat == self.find_material: mat = self.replace_material
            all_verts = set(v for idx in island_indices for v in bm.faces[idx].verts)
            pts = [Vector(obj.matrix_world @ v.co) for v in all_verts]; center_mass = sum(pts, Vector((0,0,0))) / len(pts); dynamic_pos = P_pos @ center_mass
            if self.invert_y_axis: dynamic_pos.y = -dynamic_pos.y
            cf_arr = []
            if "O" in meta:
                try: cf_arr = [float(x) for x in meta["O"].split(":")]
                except: pass
            
            if len(cf_arr) == 12:
                i3, i4, i5, i6, i7, i8, i9, i10, i11 = 3, 4, 5, 6, 7, 8, 9, 10, 11
                r00, r01, r02 = cf_arr[i3], cf_arr[i4], cf_arr[i5]
                r10, r11, r12 = cf_arr[i6], cf_arr[i7], cf_arr[i8]
                r20, r21, r22 = cf_arr[i9], cf_arr[i10], cf_arr[i11]
                v_x_blender = P_pos.inverted() @ Vector((r00, r10, r20)); v_y_blender = P_pos.inverted() @ Vector((r01, r11, r21)); v_z_blender = P_pos.inverted() @ Vector((r02, r12, r22))
            else:
                unique_normals = []
                for idx in island_indices:
                    w_normal = (obj.matrix_world.to_3x3() @ bm.faces[idx].normal).normalized()
                    if not any(n.dot(w_normal) > 0.99 for n in unique_normals):
                        unique_normals.append(w_normal)
                        if len(unique_normals) == 3: break
                if len(unique_normals) >= 2:
                    idx0, idx1 = 0, 1
                    v_x_blender = unique_normals[idx0].normalized(); v_y_blender = unique_normals[idx1].normalized()
                    v_z_blender = v_x_blender.cross(v_y_blender).normalized(); v_y_blender = v_z_blender.cross(v_x_blender).normalized()
                else: v_x_blender, v_y_blender, v_z_blender = Vector((1,0,0)), Vector((0,1,0)), Vector((0,0,1))
                m_rot = P_pos @ Matrix((v_x_blender, v_y_blender, v_z_blender)).transposed()
                m0, m1, m2 = 0, 1, 2
                r00, r01, r02 = m_rot[m0][m0], m_rot[m0][m1], m_rot[m0][m2]
                r10, r11, r12 = m_rot[m1][m0], m_rot[m1][m1], m_rot[m1][m2]
                r20, r21, r22 = m_rot[m2][m0], m_rot[m2][m1], m_rot[m2][m2]
                
            proj_x = [p.dot(v_x_blender) for p in pts]; proj_y = [p.dot(v_y_blender) for p in pts]; proj_z = [p.dot(v_z_blender) for p in pts]
            sx, sy, sz = round(max(proj_x)-min(proj_x), prec), round(max(proj_y)-min(proj_y), prec), round(max(proj_z)-min(proj_z), prec)
            if sx < self.min_block_size or sy < self.min_block_size or sz < self.min_block_size: continue
            cf_arr = [round(dynamic_pos.x, prec), round(dynamic_pos.y, prec), round(dynamic_pos.z, prec), round(r00, prec), round(r01, prec), round(r02, prec), round(r10, prec), round(r11, prec), round(r12, prec), round(r20, prec), round(r21, prec), round(r22, prec)]
            hex_c = g_hex if self.color_mode == 'GLOBAL' else "FFFFFF"
           
            if self.color_mode == 'LOCAL' and color_layer and mesh.polygons[base_face_idx].loop_indices:
                loop_idx = mesh.polygons[base_face_idx].loop_indices[0]
                col_rgba = color_layer.data[loop_idx].color
                hex_c = f"{int(col_rgba[col_r]*255):02x}{int(col_rgba[col_g]*255):02x}{int(col_rgba[col_b]*255):02x}".upper()
                
            blk = {"ID": meta.get("I", random.randint(10000, 99999)), "Transparency": transparency_val, "Anchored": meta.get("A", True), "CanCollide": meta.get("C", True) if self.collision_mode=='LOCAL' else (self.collision_mode=='TRUE'), "Color": hex_c, "CFrame": cf_arr, "CastShadow": meta.get("S", True) if self.shadow_mode=='LOCAL' else (self.shadow_mode=='TRUE'), "Size": [sx, sy, sz]}
            if self.export_logic and "M" in meta: blk["MValues"] = meta["M"]
            if self.export_logic and "B" in meta: blk["Binds"] = meta["B"]
            output_data.setdefault(mat, []).append(blk); blocks_counter += 1
            
        bm.free()
        try:
            final_json = {"Data": output_data}
            if self.file_format == 'V1_FORMAT':
                final_json["AutoBuild_Version"] = "v1"
            
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(final_json, f, separators=(',', ':'))
            self.report({'INFO'}, f"Экспорт v1 завершен! Записано блоков: {blocks_counter}")
        except Exception as e:
            self.report({'ERROR'}, f"Ошибка: {str(e)}"); return {'CANCELLED'}
        return {'FINISHED'}


def menu_layout_core_func(self, context): self.layout.operator(EXPORT_OT_babft_ultimate.bl_idname, text="BABFT Exporter beta 1.0.9 (.build)")
def register(): bpy.utils.register_class(EXPORT_OT_babft_ultimate); bpy.types.TOPBAR_MT_file_export.append(menu_layout_core_func)
def unregister(): bpy.utils.unregister_class(EXPORT_OT_babft_ultimate); bpy.types.TOPBAR_MT_file_export.remove(menu_layout_core_func)
if __name__ == "__main__": register()
