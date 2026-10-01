"""Run inside UE's Python commandlet; import the separate collection folder."""
import json,sys
from pathlib import Path
import unreal
project=Path(unreal.Paths.project_dir()).resolve()
root=project/'Tools/HoudiniBuildingDemo'
sys.path.insert(0,str(root))
from ue_medieval_materials import apply_palette
items=json.loads((root/'medieval_collection_v006.json').read_text(encoding='utf-8'))
report=[]
for item in items:
    filename=root/item['obj']
    destination='/Game/landscape/Houdini/MedievalTownV006'
    asset_path=destination+'/'+item['asset']
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        raise RuntimeError('Asset already exists; preserve edits: '+asset_path)
    task=unreal.AssetImportTask()
    for key,value in dict(filename=str(filename),destination_path=destination,destination_name=item['asset'],automated=True,save=True,replace_existing=False).items(): task.set_editor_property(key,value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    meshes=[a for a in task.get_objects() if isinstance(a,unreal.StaticMesh)]
    if len(meshes)!=1: raise RuntimeError('Expected one mesh for '+item['purpose'])
    asset=meshes[0]
    spec=json.loads(filename.with_suffix('.spec.json').read_text(encoding='utf-8'))
    slots=apply_palette(asset,filename,spec['palette'])
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset,only_if_is_dirty=False): raise RuntimeError('Save failed: '+asset_path)
    report.append(dict(asset=asset.get_path_name(),slots=len(slots),source=str(filename)))
(project/'Saved/MedievalIntegration/v006_import.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('MEDIEVAL_V006_IMPORT_COMPLETE '+str(len(report)))
