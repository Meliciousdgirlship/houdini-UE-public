"""Executed by hython, exports a validated V006 design into a staging directory."""
import json
import sys
from pathlib import Path
import hou
from medieval_design import OPTIONS, validate_spec
from medieval_geometry import export_obj

payload=json.loads(sys.argv[1]); spec=payload['spec']
validate_spec(spec)
hou.hipFile.load(payload['hip'],suppress_save_prompt=True,ignore_load_warnings=True)
hou.setUpdateMode(hou.updateMode.Manual)
root=hou.node('/obj/medieval_inn')
if root is None: raise RuntimeError('需要 V006 中世纪模板；未找到 /obj/medieval_inn')
values={'md_'+k: choices.index(spec[k]) for k,choices in OPTIONS.items()}
values.update(md_seed=spec['seed'],md_overrides=json.dumps(spec['overrides']))
root.setParms(values)
hou.setUpdateMode(hou.updateMode.AutoUpdate)
out=root.node('OUT_BUILDING'); out.cook(force=True)
for n in root.allSubChildren():
    if n.errors(): raise RuntimeError(n.path()+': '+str(n.errors()))
geo=out.geometry()
if not geo.prims(): raise RuntimeError('Empty geometry')
target=Path(payload['obj']); export_obj(geo,target,spec,coordinate_space='unreal')
target.with_suffix('.spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
print('BUILD_SUCCESS',flush=True)
