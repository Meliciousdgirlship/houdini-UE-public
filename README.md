# AI 辅助的 Houdini 中世纪小镇建筑工具 V006

本仓库只发布 V006：六栋建筑的 Houdini 工程、必要脚本、OBJ/MTL/spec 导出、预览图和两页 Word 项目说明。

## 打开工程

使用 Houdini 22.0.429 打开 `project/building_generator_v006_medieval_town.hipnc`，进入 `/obj`，选择 `medieval_inn` 等建筑节点，按 P 调整设计参数。工程为 Apprentice 非商业格式 `.hipnc`。

## 文件说明

- `project/building_generator_v006_medieval_town.hipnc`：V006 六栋建筑工程。
- `project/exports/medieval_*_v006.*`：旅馆、住宅、商店、铁匠铺、公会馆和守卫所的导出及预览。
- `project/medieval_design.py`：七项设计控制与参数校验。
- `project/medieval_geometry.py`、`medieval_identities.py`、`medieval_legacy_parts.py`：V006 使用的建模规则、专属装饰、塔楼与连桥模块。塔楼与连桥代码已包含在模块中，不需要旧版工程或节点源码。
- `project/maintenance/build_medieval_v006.py`：从当前脚本重建 V006 工程，无需旧版模板。
- `report/Houdini_AI_建筑生产流程项目总结.docx`：两页项目演示说明。
- `manifest.json`：当前 project 文件的大小和 SHA-256。

## AI 与 UE

AI 在线调用和 UE 工具接口已完成，可将文字需求转换为设计参数并更新 UE 中的建筑。`building_api.py` 使用兼容 Chat Completions 的接口，密钥放在本机 `BUILDING_API_KEY` 环境变量。

本仓库提供接口源码，UE 工具蓝图和资产保留在原 Te08 项目。Houdini 工程可独立打开；UE 面板演示在原项目中进行。

本机路径在 `config.local.json` 中配置，可参考 `project/config.example.json`；密钥、本机配置和运行备份均不提交。
