"""Rebuild the V006 six-building collection from its included source modules."""
import copy,json,sys,datetime,shutil,base64
from pathlib import Path
import hou
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
import medieval_design as design
import medieval_geometry as geometry
target=root/'building_generator_v006_medieval_town.hipnc'
if target.exists():
    backup=root/'backup'
    backup.mkdir(parents=True,exist_ok=True)
    shutil.copy2(target,backup/(datetime.datetime.now().strftime('%Y%m%d_%H%M%S_')+target.name))
hou.hipFile.clear(suppress_save_prompt=True)
hou.setUpdateMode(hou.updateMode.Manual)
for obj in hou.node('/obj').children(): obj.setDisplayFlag(False)
source=(root/'medieval_design.py').read_text(encoding='utf-8')+'\nLEGACY_PARTS_SOURCE='+repr((root/'medieval_legacy_parts.py').read_text(encoding='utf-8'))+'\nSTYLE_SOURCE='+"__import__('base64').b64decode('"+base64.b64encode((root/'medieval_identities.py').read_bytes()).decode('ascii')+"').decode('utf-8')"+'\n'+(root/'medieval_geometry.py').read_text(encoding='utf-8')+'\nbuild_geometry(hou.pwd().geometry(),spec_from_parms(hou.pwd().parent()))\n'
presets=[('inn','旅馆','medium','right_wing','oxblood','balanced'),('home','住宅','small','compact','moss','rich'),('shop','商店','medium','left_wing','oxblood','rich'),('smithy','铁匠铺','small','right_wing','slate','balanced'),('guildhall','公会馆 · 塔楼连桥','large','tower_bridge','slate','rich'),('watchhouse','守卫所 · 贴合塔楼','medium','tower','moss','restrained')]
manifest=[]
for i,(purpose,label,scale,layout,palette,detail) in enumerate(presets):
    spec=copy.deepcopy(design.DEFAULT_SPEC)
    spec.update(purpose=purpose,scale=scale,layout=layout,palette=palette,detail=detail)
    name='medieval_'+purpose
    obj=hou.node('/obj/'+name)
    if obj is not None: obj.destroy()
    obj=hou.node('/obj').createNode('geo',name)
    for child in obj.children(): child.destroy()
    group=obj.parmTemplateGroup()
    for folder in ('medieval_design','medieval_advanced'):
        if group.find(folder): group.remove(folder)
    controls=hou.FolderParmTemplate('medieval_design','中世纪建筑 · 七项设计')
    for key,choices in design.OPTIONS.items():
        controls.addParmTemplate(hou.MenuParmTemplate('md_'+key,design.LABELS[key],choices,design.MENU_LABELS[key],default_value=choices.index(spec[key])))
    advanced=hou.FolderParmTemplate('medieval_advanced','高级尺寸与变化')
    advanced.addParmTemplate(hou.IntParmTemplate('md_seed','变化种子',1,default_value=(17,),min=0,max=99999,min_is_strict=True,max_is_strict=True))
    advanced.addParmTemplate(hou.StringParmTemplate('md_overrides','尺寸覆盖 JSON',1,default_value=('{}',)))
    group.append(controls);group.append(advanced);obj.setParmTemplateGroup(group)
    obj.setParms({'md_'+k:v.index(spec[k]) for k,v in design.OPTIONS.items()})
    obj.setParms({'tx':(i%3)*28,'tz':(i//3)*26})
    obj.setPosition(hou.Vector2((i%3)*4,-(i//3)*3))
    obj.setComment(label);obj.setGenericFlag(hou.nodeFlag.DisplayComment,True)
    sop=obj.createNode('python','medieval_kit');sop.parm('python').set(source)
    out=obj.createNode('null','OUT_BUILDING');out.setInput(0,sop);out.setDisplayFlag(True);out.setRenderFlag(True)
    obj.setDisplayFlag(True);obj.layoutChildren()
    hou.setUpdateMode(hou.updateMode.AutoUpdate)
    try:
        out.cook(force=True)
    except hou.OperationFailed:
        raise RuntimeError(name+str(sop.errors()))
    if sop.errors(): raise RuntimeError(name+str(sop.errors()))
    export=root/'exports'/('medieval_'+purpose+'_v006.obj')
    geometry.export_obj(out.geometry(),export,spec,coordinate_space='unreal')
    export.with_suffix('.spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest.append(dict(purpose=purpose,label=label,node=obj.path(),obj=export.relative_to(root).as_posix(),asset='SM_Medieval'+purpose.title(),position_m=[(i%3)*28,0,(i//3)*26]))
    hou.setUpdateMode(hou.updateMode.Manual)
hou.setUpdateMode(hou.updateMode.AutoUpdate)
hou.hipFile.save(str(target))
(root/'medieval_collection_v006.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('SAVED',target)
