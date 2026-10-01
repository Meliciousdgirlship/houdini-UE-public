import json
import os
import runpy
import urllib.request
import urllib.error
from pathlib import Path

import unreal


PROJECT = Path(__file__).resolve().parent

from medieval_design import PLANNER_PROMPT as SYSTEM_PROMPT, normalize_spec, enforce_locks



def load_base_spec(tool, new_building):
    asset, manager = tool['selected_target']()
    STATE_FILE = tool['source_for_asset'](asset,manager).with_suffix('.spec.json')
    if new_building or not STATE_FILE.exists():
        spec = dict(tool["SPEC"])
        tool["validate_spec"](spec)
        return spec, "默认参数"

    try:
        spec = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(
            "无法读取当前建筑状态，请检查配置的 OBJ 对应的 spec.json："
            + str(error)
        ) from None

    if not isinstance(spec, dict):
        raise ValueError("当前建筑状态不是 JSON 对象")

    spec = normalize_spec(spec)
    tool["validate_spec"](spec)
    return spec, "最近导出的建筑参数"


def plan_building(description):
    if not isinstance(description, str) or not description.strip():
        raise ValueError("建筑描述不能为空")

    description = description.strip()

    tool = runpy.run_path(
        str(PROJECT / "ue_building_tool.py"),
        run_name="building_tool",
    )

    # 明确的新建指令才重置基础参数
    new_building = description.startswith(("新建", "重新生成"))

    base_spec, source = load_base_spec(tool, new_building)

    from building_api import request_spec
    spec = request_spec(description,base_spec,SYSTEM_PROMPT)

    tool["validate_spec"](spec)
    enforce_locks(base_spec, spec)

    changes = {
        key: {"before": base_spec[key], "after": spec[key]}
        for key in base_spec
        if base_spec[key] != spec[key]
    }

    unreal.log(
        "[Planner] 参数变化：\n"
        + json.dumps(changes, ensure_ascii=False, indent=2)
    )

    unreal.log(
        "[Planner] 校验通过：\n"
        + json.dumps(spec, ensure_ascii=False, indent=2)
    )

    # 此处只返回方案，不提前覆盖状态文件。
    # 现有生成脚本在 OBJ 导出后保存新的参数。
    return spec
