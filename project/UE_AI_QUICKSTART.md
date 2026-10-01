# V006 AI 与 UE 演示

1. 用本机环境变量 BUILDING_API_KEY 配置密钥，API 地址与模型可通过 SetupBuildingAI.cmd 设置。
2. 在原 Te08 项目中选中 V006 建筑，运行 EUW_MedievalBuildingTool_V006。
3. 读取选中建筑，输入修改要求，点击 AI 生成；流程为在线请求、参数校验、Houdini 生成、UE 重导入。
4. 完成后保存 UE 资产。工具接口和在线调用已完成，界面说明见 TOOL_V006.md。

此公开包只包含 V006 工程和源码；工具蓝图及 UE 资产保留在原项目。Houdini 工程使用 Y-up/米，OBJ 导出转换为 UE Z-up/厘米。
