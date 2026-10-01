"""Compact runtime layout for the existing native tool; no asset reload needed."""
import json
import unreal
import medieval_design as design
_refs=[]
_ui=None

@unreal.uclass()
class MedievalCompactActions(unreal.EditorUtilityObject):
    @unreal.ufunction()
    def toggle_advanced(self):
        panel=_ui.find_child_widget_by_name('CompactAdvanced')
        panel.set_visibility(unreal.SlateVisibility.VISIBLE if panel.get_visibility()==unreal.SlateVisibility.COLLAPSED else unreal.SlateVisibility.COLLAPSED)
    @unreal.ufunction()
    def toggle_api(self):
        panel=_ui.find_child_widget_by_name('ApiPanel')
        panel.set_visibility(unreal.SlateVisibility.VISIBLE if panel.get_visibility()==unreal.SlateVisibility.COLLAPSED else unreal.SlateVisibility.COLLAPSED)

def apply(ui):
    global _ui
    _ui=ui
    if ui.find_child_widget_by_name('CompactAdvanced') is not None:return
    tree=unreal.find_object(ui,'WidgetTree')
    if tree is None:tree=ui
    names=['V006Body','Title006','TargetText','ReadSelection','ParameterPanel','Btn_Generate','PromptInput','Btn_AIGenerate','StatusText','ApiPanel','SeedRow','FlatRoofInput']
    names+=['Row_'+k for k in design.OPTIONS]+['SizeRow_'+k for k in design.RANGES]
    items={n:ui.find_child_widget_by_name(n) for n in names}
    # AddOption updates runtime option storage only; populate every widget instance.
    for key,choices in design.OPTIONS.items():
        combo=ui.find_child_widget_by_name('Design_'+key)
        selected=combo.get_selected_index()
        combo.clear_options()
        for label in design.MENU_LABELS[key]:combo.add_option(label)
        combo.set_selected_index(selected if 0<=selected<len(choices) else choices.index(design.DEFAULT_SPEC[key]))
        combo.set_is_enabled(True)
    allwidgets=[]
    def walk(w):
        allwidgets.append(w)
        if isinstance(w,unreal.PanelWidget):
            for child in w.get_all_children():walk(child)
    walk(items['V006Body'])
    for w in allwidgets:
        if isinstance(w,unreal.TextBlock):
            font=w.get_editor_property('font');font.size=10;w.set_font(font)
        elif isinstance(w,(unreal.SpinBox,unreal.ComboBoxString)):
            font=w.get_editor_property('font');font.size=11;w.set_editor_property('font',font)
    def new(cls,name):
        obj=unreal.new_object(cls,outer=tree,name=name);_refs.append(obj);return obj
    def add(parent,child):
        child.remove_from_parent();slot=parent.add_child(child)
        if isinstance(slot,unreal.VerticalBoxSlot):slot.set_padding(unreal.Margin(0,1,0,1))
        return slot
    def sized(parent,child,name,width=None,height=None):
        box=new(unreal.SizeBox,name)
        if width is not None:box.set_width_override(width)
        if height is not None:box.set_height_override(height)
        add(box,child);add(parent,box)
        return box
    def label(parent,name,value):
        text=new(unreal.TextBlock,name);text.set_text(value)
        font=text.get_editor_property('font');font.size=11;text.set_font(font);add(parent,text);return text
    body=items['V006Body'];body.clear_children()
    title=items['Title006'];title.set_text('中世纪建筑工具')
    font=title.get_editor_property('font');font.size=14;title.set_font(font);add(body,title)
    add(body,items['TargetText'])
    items['TargetText'].set_tool_tip_text('修改会应用到同一网格的所有实例。切换目标后点击读取。')
    sized(body,items['ReadSelection'],'CompactReadSize',height=24)
    params=items['ParameterPanel'];params.clear_children();add(body,params)
    for key in design.OPTIONS:
        row=items['Row_'+key]
        labelw=ui.find_child_widget_by_name('Label_'+key) or next(w for w in allwidgets if w.get_name()=='Label_'+key)
        combo=next(w for w in allwidgets if w.get_name()=='Design_'+key)
        lock=next(w for w in allwidgets if w.get_name()=='Lock_'+key)
        row.clear_children()
        sized(row,labelw,'CompactLabel_'+key,width=90)
        sized(row,combo,'CompactChoice_'+key,width=220,height=22)
        add(row,lock);add(params,row)
    sized(body,items['Btn_Generate'],'CompactGenerateSize',height=28)
    next(w for w in allwidgets if w.get_name()=='Btn_Generate_Label').set_text('生成建筑')
    label(body,'CompactPromptLabel','AI 描述')
    prompt=items['PromptInput'];prompt.set_visibility(unreal.SlateVisibility.VISIBLE);prompt.set_is_enabled(True)
    prompt.set_hint_text('例如：保持尺寸和布局，把屋顶改成灰蓝色。')
    sized(body,prompt,'CompactPromptSize',height=90)
    sized(body,items['Btn_AIGenerate'],'CompactAISize',height=30)
    next(w for w in allwidgets if w.get_name()=='Btn_AIGenerate_Label').set_text('AI 生成')
    add(body,items['StatusText'])
    actions=unreal.new_object(MedievalCompactActions);_refs.append(actions)
    def fold_button(name,title,callback):
        b=new(unreal.Button,name);label(b,name+'_Text',title);sized(body,b,name+'_Size',height=26)
        b.on_clicked.add_function(actions,callback)
    fold_button('CompactAdvancedToggle','高级尺寸与种子  ·  展开 / 收起','toggle_advanced')
    advanced=new(unreal.VerticalBox,'CompactAdvanced');add(body,advanced)
    label(advanced,'CompactOverrideHelp','勾选覆盖才使用输入值；未勾选时自动推导。')
    for key in design.RANGES:add(advanced,items['SizeRow_'+key])
    add(advanced,items['SeedRow']);add(advanced,items['FlatRoofInput'])
    advanced.set_visibility(unreal.SlateVisibility.COLLAPSED)
    fold_button('CompactApiToggle','API 设置与说明  ·  展开 / 收起','toggle_api')
    add(body,items['ApiPanel']);items['ApiPanel'].set_visibility(unreal.SlateVisibility.COLLAPSED)
    _refs.extend(items.values())

def refresh():
    import building_tool_v006 as controller
    ui=unreal.get_editor_subsystem(unreal.EditorUtilitySubsystem).find_utility_widget_from_blueprint(unreal.load_asset(controller.ASSET))
    if ui is None:ui=controller.open_tool()
    apply(ui)
    controller.ensure(ui)
    if controller._target:
        controller.fill(design.normalize_spec(json.loads(controller._target[2].with_suffix('.spec.json').read_text(encoding='utf-8'))))
        controller.widget('TargetText').set_text('当前建筑：'+controller._target[0].get_name())
    controller.message('布局已更新。可调整参数，或输入描述后点击 AI 生成。')
