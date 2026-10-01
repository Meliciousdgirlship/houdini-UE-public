"""Native v006 editor widget controller. UI state is the common manual/AI input."""
import copy,json,subprocess
from pathlib import Path
import unreal
import medieval_design as design
import ue_building_tool as tool
import building_api
import building_async
ROOT=Path(__file__).resolve().parent
ASSET='/Game/landscape/Houdini/EUW_MedievalBuildingTool_V006'
_ui=None
_target=None
_actions=None
_tick_handle=None

def widget(name): return _ui.find_child_widget_by_name(name)
def message(text):
    if _ui: widget('StatusText').set_text(text)
    unreal.log('[Medieval Tool] '+text)

def read_form():
    spec=copy.deepcopy(design.DEFAULT_SPEC)
    for key,choices in design.OPTIONS.items():
        index=widget('Design_'+key).get_selected_index()
        if index<0 or index>=len(choices):raise ValueError('请选择'+design.LABELS[key])
        spec[key]=choices[index]
    seed=float(widget('SeedInput').get_value())
    if not seed.is_integer():raise ValueError('变化种子必须为整数')
    spec['seed']=int(seed)
    spec['locks']=[key for key in design.OPTIONS if widget('Lock_'+key).is_checked()]
    names={'width':'WidthInput','depth':'DepthInput','floors':'FloorsInput'}
    for key in design.RANGES:
        if widget('Override_'+key).is_checked():
            value=widget(names.get(key,'Size_'+key)).get_value()
            if key=='floors' and not float(value).is_integer():raise ValueError('楼层必须是整数')
            spec['overrides'][key]=int(value) if key=='floors' else float(value)
    design.validate_spec(spec)
    return spec

def fill(spec):
    values=design.resolve_spec(spec)
    for key,choices in design.OPTIONS.items():
        widget('Design_'+key).set_selected_index(choices.index(spec[key]))
        widget('Lock_'+key).set_is_checked(key in spec['locks'])
    widget('SeedInput').set_value(spec['seed'])
    names={'width':'WidthInput','depth':'DepthInput','floors':'FloorsInput'}
    for key in design.RANGES:
        widget('Override_'+key).set_is_checked(key in spec['overrides'])
        widget(names.get(key,'Size_'+key)).set_value(values[key])
    widget('FlatRoofInput').set_is_checked(False)

def read_selected():
    global _target
    if building_async._job is not None: raise RuntimeError('请等待当前任务完成')
    asset,manager=tool.selected_target()
    path=tool.source_for_asset(asset,manager)
    spec=design.normalize_spec(json.loads(path.with_suffix('.spec.json').read_text(encoding='utf-8')))
    _target=(asset,manager,path)
    fill(spec)
    widget('TargetText').set_text('当前建筑：'+asset.get_name())
    widget('TargetText').set_tool_tip_text(asset.get_path_name())
    message('已读取建筑。修改后点击生成；切换建筑请点击“读取选中建筑”。')

def refresh_api():
    path=ROOT/'api.local.json'
    data=json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}
    widget('ApiBase').set_text(data.get('base_url','https://claudex.org/v1'))
    widget('ApiModel').set_text(data.get('model','deepseek-v4.1-flash'))
    try:
        state=building_api.status()
        widget('ApiStatus').set_text('密钥：'+('已配置（不显示）' if state['key_configured'] else '未配置，请点击“配置密钥”'))
    except Exception as e: widget('ApiStatus').set_text(str(e))

def save_api():
    base=str(widget('ApiBase').get_text()).strip().rstrip('/')
    model=str(widget('ApiModel').get_text()).strip()
    from urllib.parse import urlsplit
    parsed=urlsplit(base)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or not model:
        raise ValueError('请填写有效 HTTPS Base URL 和模型名称；不要在地址里填密钥')
    (ROOT/'api.local.json').write_text(json.dumps(dict(base_url=base,model=model),indent=2),encoding='utf-8')
    refresh_api();message('接口配置已保存，没有发送 API 请求。')

def ensure(ui=None):
    global _ui,_actions,_target
    if ui is None:
        ui=unreal.get_editor_subsystem(unreal.EditorUtilitySubsystem).find_utility_widget_from_blueprint(unreal.load_asset(ASSET))
    if ui is None: raise RuntimeError('请先打开新版中世纪工具面板')
    if _ui==ui:return
    _ui=ui
    _target=None
    import building_tool_layout
    building_tool_layout.apply(ui)
    _actions=unreal.new_object(MedievalV006Actions)
    for name,method in [('ReadSelection','read_selection'),('SaveAPI','save_api_action'),('ConfigureKey','configure_key'),('RefreshAPI','refresh_api_action')]:
        widget(name).on_clicked.add_function(_actions,method)
    refresh_api()
    try:read_selected()
    except Exception as e: fill(design.DEFAULT_SPEC);message(str(e))

def manual():
    try:
        ensure()
        if building_async._job is not None:raise RuntimeError('AI 正在生成，请等待完成')
        if _target is None:raise RuntimeError('请先选中建筑并点击“读取选中建筑”')
        spec=read_form();asset,manager,path=_target
        message('正在生成并重导入，请稍候……')
        old=tool.selected_target
        try:
            tool.selected_target=lambda:(asset,manager)
            tool._main_impl(spec)
        finally:tool.selected_target=old
        fill(spec);message('生成完成。场景中同一网格的实例都会更新，请保存资产。')
    except Exception as e:message('未生成：'+str(e))

def ai(ui):
    try:
        ensure(ui)
        if _target is None:raise RuntimeError('请先读取选中建筑')
        save_api()
        building_async.start(str(widget('PromptInput').get_text()),ui,base_override=read_form(),target_override=_target[:2],on_complete=fill)
    except Exception as e:message('AI 未启动：'+str(e))

@unreal.uclass()
class MedievalV006Actions(unreal.EditorUtilityObject):
    @unreal.ufunction()
    def read_selection(self):
        try:read_selected()
        except Exception as e:message(str(e))
    @unreal.ufunction()
    def save_api_action(self):
        try:save_api()
        except Exception as e:message(str(e))
    @unreal.ufunction()
    def refresh_api_action(self):
        refresh_api()
    @unreal.ufunction()
    def configure_key(self):
        subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'setup_api.ps1')],creationflags=subprocess.CREATE_NEW_CONSOLE)
        message('请在配置窗口输入密钥，完成后点击“刷新密钥状态”。')

def open_tool():
    if building_async._job is not None:raise RuntimeError('请等待当前 AI 任务完成后再打开新版工具')
    import importlib
    importlib.reload(building_async)
    ui=unreal.get_editor_subsystem(unreal.EditorUtilitySubsystem).spawn_and_register_tab(unreal.load_asset(ASSET))
    ensure(ui)
    return ui

def install():
    global _tick_handle
    if _tick_handle is not None:return
    elapsed=[0.0]
    def tick(delta):
        elapsed[0]+=delta
        if elapsed[0]<.5:return
        elapsed[0]=0.0
        bp=unreal.load_asset(ASSET) if unreal.EditorAssetLibrary.does_asset_exist(ASSET) else None
        if bp is None:return
        ui=unreal.get_editor_subsystem(unreal.EditorUtilitySubsystem).find_utility_widget_from_blueprint(bp)
        if ui is not None and ui!=_ui:
            try:ensure(ui)
            except Exception as e:unreal.log_warning('新版面板初始化失败：'+str(e))
    _tick_handle=unreal.register_slate_post_tick_callback(tick)
