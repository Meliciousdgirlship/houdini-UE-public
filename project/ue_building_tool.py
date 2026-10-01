"""UE entry point for the V006 medieval kit; retains existing widget callbacks."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import shutil
import unreal

PROJECT = Path(__file__).resolve().parent
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))
from medieval_design import DEFAULT_SPEC, validate_spec, normalize_spec, manual_edit, resolve_spec, enforce_locks
import bundle_transaction as bundle

_config_path = PROJECT / 'config.local.json'
_local_config = json.loads(_config_path.read_text(encoding='utf-8')) if _config_path.exists() else {}
HYTHON = Path(os.environ.get('BUILDING_HYTHON') or _local_config.get('hython', 'C:/Program Files/Side Effects Software/Houdini 22.0.429/bin/hython.exe'))
HIP_FILE = PROJECT / _local_config.get('hip', 'building_generator_v006_medieval_town.hipnc')
OBJ_FILE = PROJECT / _local_config.get('export_obj', 'exports/medieval_inn_v006.obj')
SPEC = copy.deepcopy(DEFAULT_SPEC)

HOUDINI_CODE = r'''
import json, sys, runpy
from pathlib import Path
payload=json.loads(sys.argv[1])
folder=Path(payload['hip']).parent
sys.path.insert(0,str(folder))
runpy.run_path(str(folder/'houdini_design_worker.py'),run_name='__main__')
'''

def source_for_asset(asset, manager):
    sources=manager.can_reimport(asset)
    allowed={OBJ_FILE.resolve()}
    newer=PROJECT/'medieval_collection_v006.json'
    if newer.exists():
        allowed.update((PROJECT/item['obj']).resolve() for item in json.loads(newer.read_text(encoding='utf-8')))
    if not sources or len(sources)!=1 or Path(str(sources[0])).resolve() not in allowed:
        raise RuntimeError('请选择本项目中世纪建筑集合的静态网格资产')
    return Path(str(sources[0])).resolve()

def selected_target():
    manager = unreal.InterchangeManager.get_interchange_manager_scripted()
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_selected_level_actors()
    scene_meshes=[]
    for actor in actors:
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh=component.get_editor_property('static_mesh')
            if mesh is not None:
                try: source_for_asset(mesh,manager)
                except RuntimeError: continue
                if mesh not in scene_meshes: scene_meshes.append(mesh)
    if len(scene_meshes)>1:
        raise RuntimeError('场景中选中了多种建筑，请只选中要修改的一栋')
    if len(scene_meshes)==1: return scene_meshes[0],manager
    selected = unreal.EditorUtilityLibrary.get_selected_assets()
    if len(selected) != 1 or not isinstance(selected[0], unreal.StaticMesh):
        raise RuntimeError('请在场景中选中一栋中世纪建筑，或在内容浏览器中选中一个建筑静态网格资产')
    asset = selected[0]
    manager = unreal.InterchangeManager.get_interchange_manager_scripted()
    source_for_asset(asset,manager)
    return asset, manager

def generate_staged(spec, target=None):
    target=Path(target or OBJ_FILE)
    validate_spec(spec)
    for path in (HYTHON, HIP_FILE):
        if not path.is_file(): raise RuntimeError('文件不存在：' + str(path))
    OBJ_FILE.parent.mkdir(parents=True, exist_ok=True)
    folder=Path(tempfile.mkdtemp(prefix='building_job_',dir=str(OBJ_FILE.parent)))
    staged=folder/target.name
    payload=json.dumps({'spec':spec,'hip':str(HIP_FILE),'obj':str(staged)})
    result=subprocess.run([str(HYTHON),'-',payload],input=HOUDINI_CODE,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode or 'BUILD_SUCCESS' not in result.stdout:
        raise RuntimeError('Houdini 生成失败，检查文件保留于 '+str(folder)+'\n'+result.stdout+'\n'+result.stderr)
    return staged

def _main_impl(spec_override=None):
    asset,manager=selected_target()
    OBJ_FILE=source_for_asset(asset,manager)
    state=OBJ_FILE.with_suffix('.spec.json')
    if spec_override and 'schema_version' in spec_override:
        spec=normalize_spec(spec_override)
    else:
        base=normalize_spec(json.loads(state.read_text(encoding='utf-8'))) if state.exists() else copy.deepcopy(SPEC)
        spec=manual_edit(base,spec_override or {})
    staged=generate_staged(spec,OBJ_FILE)
    backup=staged.parent/'previous'
    existed=bundle.capture(OBJ_FILE,backup)
    try:
        bundle.publish_geometry(staged,OBJ_FILE)
        parameters=unreal.ImportAssetParameters()
        parameters.set_editor_property('is_automated',True)
        imported=manager.reimport_asset(asset,parameters)
        if not imported: raise RuntimeError('UE 重新导入未返回成功结果')
        from ue_medieval_materials import apply_palette
        apply_palette(asset,OBJ_FILE,spec['palette'])
        staged.with_suffix('.spec.json').replace(state)
    except Exception:
        bundle.restore(OBJ_FILE,backup,existed)
        unreal.log_error('源 OBJ/MTL/状态已恢复；如 UE 内存网格部分改变，请重新导入恢复后的源文件。备份：'+str(backup))
        raise
    recovery=PROJECT/'exports/previous_success'
    recovery.mkdir(exist_ok=True)
    for file in backup.iterdir(): shutil.copy2(file,recovery/file.name)
    shutil.rmtree(staged.parent)
    unreal.log('[Medieval Kit] 生成与重新导入完成，请检查并保存建筑资产。')

def main(spec_override=None):
    try:
        return _main_impl(spec_override)
    except Exception as error:
        unreal.log_error('[建筑生成] '+str(error))
        unreal.EditorDialog.show_message('建筑未生成',str(error),unreal.AppMsgType.OK)
        raise

if __name__ == '__main__':
    main()
