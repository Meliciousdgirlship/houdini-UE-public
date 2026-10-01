"""Create the native v006 editor utility widget, preserving the original asset."""
import sys
from pathlib import Path
import unreal
root=Path(unreal.Paths.project_dir()).resolve()/'Tools/HoudiniBuildingDemo'
sys.path.insert(0,str(root))
import medieval_design as design
destination='/Game/landscape/Houdini/EUW_MedievalBuildingTool_V006'
if unreal.EditorAssetLibrary.does_asset_exist(destination):raise RuntimeError('New panel already exists; preserve edits')
bp=unreal.EditorAssetLibrary.duplicate_asset('/Game/landscape/Houdini/EUW_BuildingTool',destination)
tree=unreal.find_object(bp,'WidgetTree')
existing={obj.get_name():obj for obj in unreal.ObjectIterator(unreal.Widget) if obj.get_outer()==tree}
roots=[obj for obj in existing.values() if obj.get_parent() is None and isinstance(obj,unreal.PanelWidget)]
if len(roots)!=1:raise RuntimeError('Unexpected roots '+str([x.get_name() for x in roots]))
host=roots[0];host.clear_children()
def make(cls,name):return existing[name] if name in existing else unreal.new_object(cls,outer=tree,name=name)
def add(parent,child):
    child.remove_from_parent()
    return parent.add_child(child)
def text(parent,name,value,size=12):
    obj=make(unreal.TextBlock,name);obj.set_text(value);obj.set_auto_wrap_text(True)
    font=obj.get_editor_property('font');font.size=size;obj.set_font(font)
    add(parent,obj);return obj
def row(parent,name):
    obj=make(unreal.HorizontalBox,name);add(parent,obj);return obj
def button(parent,name,label):
    obj=make(unreal.Button,name);obj.clear_children();add(parent,obj);text(obj,name+'_Label',label,12);return obj
scroll=make(unreal.ScrollBox,'V006Scroll');slot=add(host,scroll)
if isinstance(slot,unreal.CanvasPanelSlot):
    slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(0,0),maximum=unreal.Vector2D(1,1)))
    slot.set_offsets(unreal.Margin(12,12,12,12))
body=make(unreal.VerticalBox,'V006Body');add(scroll,body)
text(body,'Title006','中世纪建筑工具  ·  V006',22)
text(body,'Intro006','读取建筑 → 调整设计 → 手动生成 / AI 修改 → 保存资产。尺寸单位：米；UE 导出：厘米、Z 轴朝上。')
text(body,'TargetText','当前目标：尚未读取建筑')
button(body,'ReadSelection','读取选中建筑 / 切换目标')
text(body,'TargetHelp','可选场景中的建筑或内容浏览器中的网格。目标读取后固定；同一网格的所有场景实例都会更新。')
params=make(unreal.VerticalBox,'ParameterPanel');add(body,params)
text(params,'DesignTitle','01  设计参数',17)
for key,choices in design.OPTIONS.items():
    line=row(params,'Row_'+key)
    text(line,'Label_'+key,design.LABELS[key]+'  ')
    combo=make(unreal.ComboBoxString,'Design_'+key)
    for label in design.MENU_LABELS[key]:combo.add_option(label)
    combo.set_selected_index(choices.index(design.DEFAULT_SPEC[key]));add(line,combo)
    lock=make(unreal.CheckBox,'Lock_'+key);add(line,lock);text(lock,'LockLabel_'+key,'AI 锁定')
    combo.set_tool_tip_text('用途决定专属形状与装饰；锁定只限制 AI 修改该设计字段。')
text(params,'LockHelp','AI 锁定仅锁定对应选项，不保证所有派生尺寸不变。想固定尺寸，请启用下面的尺寸覆盖。')
text(params,'AdvancedTitle','02  高级尺寸与变化',17)
text(params,'OverrideHelp','不勾选“覆盖”时按用途、规模自动推导。勾选后使用输入数值；长度 4–12 米，楼层 1–3。连桥至少两层。')
names={'width':'WidthInput','depth':'DepthInput','floors':'FloorsInput'}
labels={'width':'宽度（米）','depth':'长度（米）','floors':'楼层','floor_height':'层高（米）','roof_height':'屋顶高度（米）','roof_overhang':'屋檐伸出（米）'}
values=design.resolve_spec(design.DEFAULT_SPEC)
for key,(lo,hi) in design.RANGES.items():
    line=row(params,'SizeRow_'+key)
    check=make(unreal.CheckBox,'Override_'+key);add(line,check);text(check,'OverrideLabel_'+key,'覆盖')
    text(line,'SizeLabel_'+key,labels[key]+'  ['+str(lo)+'–'+str(hi)+']  ')
    number=make(unreal.SpinBox,names.get(key,'Size_'+key));number.set_min_value(lo);number.set_max_value(hi);number.set_min_slider_value(lo);number.set_max_slider_value(hi);number.set_value(values[key]);number.set_editor_property('delta',1 if key=='floors' else .1);add(line,number)
seedrow=row(params,'SeedRow');text(seedrow,'SeedLabel','变化种子  [0–99999]  ')
seed=make(unreal.SpinBox,'SeedInput');seed.set_min_value(0);seed.set_max_value(99999);seed.set_editor_property('delta',1);seed.set_value(17);add(seedrow,seed)
flat=make(unreal.CheckBox,'FlatRoofInput');flat.set_is_checked(False);add(params,flat);flat.set_visibility(unreal.SlateVisibility.COLLAPSED)
text(params,'SeedHelp','同一种子保持装饰变化稳定。当前支持双坡屋顶；不提供平屋顶。')
button(body,'Btn_Generate','生成建筑 · 应用上面的完整参数')
text(body,'AITitle','03  AI 修改',17)
prompt=make(unreal.MultiLineEditableTextBox,'PromptInput');prompt.set_hint_text('例如：保持用途、尺寸和布局，只把配色改成灰蓝象牙。');add(body,prompt)
text(body,'AIHelp','AI 以面板当前参数为基础，返回 JSON 后由本机校验，再生成并直接应用。只支持上面列出的参数；每次点击可能消耗平台额度。')
button(body,'Btn_AIGenerate','AI 生成 · 调用接口并应用')
text(body,'StatusText','就绪：请先读取建筑',14)
api=make(unreal.VerticalBox,'ApiPanel');add(body,api)
text(api,'ApiTitle','04  API 接口配置与说明',17)
text(api,'BaseHelp','Base URL：平台接口前缀（例如 https://claudex.org/v1），不要填写密钥。自动补 /chat/completions。')
base=make(unreal.EditableTextBox,'ApiBase');base.set_text('https://claudex.org/v1');add(api,base)
text(api,'ModelHelp','Model：平台的精确模型 ID，沿用旧配置；可用性取决于账户权限。')
model=make(unreal.EditableTextBox,'ApiModel');model.set_text('deepseek-v4.1-flash');add(api,model)
button(api,'SaveAPI','保存接口配置（不发请求）')
text(api,'ApiStatus','密钥状态：打开工具时读取')
line=row(api,'KeyRow');button(line,'ConfigureKey','配置密钥（打开隐藏输入窗口）');button(line,'RefreshAPI','刷新密钥状态')
text(api,'APIComment','接口：POST /chat/completions；Bearer 密钥认证；非流式。发送内容：建筑设计 JSON + 描述文字，不上传模型文件。密钥存在本机用户环境变量，不写入工程。401：密钥；403：权限；404：地址或模型；429：额度或频率。')
text(api,'APIOverrides','若设置 BUILDING_API_BASE_URL / BUILDING_API_MODEL 环境变量，它们优先于此处的配置。')
for graph in unreal.BlueprintEditorLibrary.list_graphs(bp):
    for node in unreal.BlueprintGraphEditor.get_graph_editor(graph).list_all_nodes():
        if not isinstance(node,unreal.K2Node):continue
        for pin in unreal.BlueprintEditorLibrary.list_input_pins(node):
            script=unreal.BlueprintGraphPinLibrary.get_pin_value(pin)
            if 'ue_building_tool.py' in script:
                unreal.BlueprintGraphPinLibrary.set_pin_value(pin,'import building_tool_v006\nbuilding_tool_v006.manual()')
            elif 'building_async.start' in script:
                unreal.BlueprintGraphPinLibrary.set_pin_value(pin,'import building_tool_v006\nbuilding_tool_v006.ai(tool_ui)')
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
if not unreal.EditorAssetLibrary.save_loaded_asset(bp,only_if_is_dirty=False):raise RuntimeError('Could not save v006 widget')
unreal.log('V006_WIDGET_CREATED '+destination)
