"""Bind palette-specific UE materials to named OBJ sections after reimport."""
from pathlib import Path
import unreal

def apply_palette(asset, obj_file, palette):
    colors={}; name=None
    for line in Path(obj_file).with_suffix('.mtl').read_text(encoding='utf-8').splitlines():
        if line.startswith('newmtl '): name=line.split()[1]
        elif line.startswith('Kd ') and name: colors[name]=tuple(float(c) for c in line.split()[1:4])
    folder='/Game/landscape/Houdini/MedievalMaterials'
    unreal.EditorAssetLibrary.make_directory(folder)
    tools=unreal.AssetToolsHelpers.get_asset_tools()
    library=unreal.MaterialEditingLibrary
    assigned=[]
    for index,slot in enumerate(asset.get_editor_property('static_materials')):
        key=str(slot.get_editor_property('imported_material_slot_name'))
        if key not in colors: key=str(slot.get_editor_property('material_slot_name'))
        if key not in colors:
            raise RuntimeError('未识别的材质分组：'+key)
        path=folder+'/M_'+palette+'_'+key
        material=unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
        if material is None:
            material=tools.create_asset('M_'+palette+'_'+key,folder,unreal.Material,unreal.MaterialFactoryNew())
            color=library.create_material_expression(material,unreal.MaterialExpressionConstant3Vector,-350,0)
            color.set_editor_property('constant',unreal.LinearColor(*colors[key],1.0))
            library.connect_material_property(color,'',unreal.MaterialProperty.MP_BASE_COLOR)
            rough=library.create_material_expression(material,unreal.MaterialExpressionConstant,-350,160)
            rough.set_editor_property('r',.82 if key!='iron' else .55)
            library.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
            library.recompile_material(material)
            if not unreal.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False):
                raise RuntimeError('无法保存材质：'+path)
        asset.set_material(index,material)
        assigned.append(key)
    return assigned
