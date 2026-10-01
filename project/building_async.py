import json
import os
import queue
import runpy
import shutil
import subprocess
import tempfile
import threading
import urllib.request
import urllib.error
from pathlib import Path

import unreal


PROJECT = Path(__file__).resolve().parent
from medieval_design import normalize_spec, resolve_spec, enforce_locks
import bundle_transaction as bundle

# 使用普通 import 加载本模块，保持任务状态，阻止重复点击
_job = None


def _request_spec(description, base_spec, system_prompt, config):
    from building_api import request_spec
    return request_spec(description,base_spec,system_prompt,config)


def _worker(events, config):
    """工作线程：只操作网络、文件和子进程，不调用 UE API。"""
    key = config["key"]

    try:
        spec = _request_spec(
            config["description"],
            config["base_spec"],
            config["system_prompt"],
            config["api"],
        )

        config["validate"](spec)
        enforce_locks(config["base_spec"], spec)

        changes = {
            name: {
                "before": config["base_spec"][name],
                "after": spec[name],
            }
            for name in spec
            if config["base_spec"][name] != spec[name]
        }

        events.put((
            "log",
            "参数变化：\n"
            + json.dumps(changes, ensure_ascii=False, indent=2),
        ))
        events.put(("status", "正在生成建筑……"))

        # 先生成到独立目录，不覆盖当前成功版本
        staged_obj = Path(config["staged_obj"])

        payload = json.dumps({
            "spec": spec,
            "hip": config["hip"],
            "obj": str(staged_obj),
        })

        result = subprocess.run(
            [config["hython"], "-", payload],
            input=config["houdini_code"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Houdini 生成失败：\n"
                + result.stderr
                + "\n"
                + result.stdout
            )

        if "BUILD_SUCCESS" not in result.stdout:
            raise RuntimeError("未收到 Houdini 成功标记")

        if not staged_obj.is_file() or staged_obj.stat().st_size == 0:
            raise RuntimeError("Houdini 没有生成有效 OBJ 文件")

        if result.stderr.strip():
            events.put(("log", result.stderr.strip()))

        events.put(("ready", spec))

    except Exception as error:
        events.put((
            "error",
            str(error).replace(key, "[REDACTED]"),
        ))


def _status(job, message):
    """只在 UE 主线程调用。"""
    unreal.log("[Building Async] " + message)

    try:
        job["status_widget"].set_text(message)
    except Exception:
        # 面板关闭后，日志仍然保留
        pass


def _finish(job, success, message):
    global _job

    try:
        _status(job, message)

        if not success:
            unreal.log_error("[Building Async] " + message)

        for widget, enabled in job["restore_enabled"]:
            try:
                widget.set_is_enabled(enabled)
            except Exception:
                pass

    finally:
        handle = job.get("tick_handle")
        if handle is not None:
            unreal.unregister_slate_post_tick_callback(handle)

        _job = None

        if success:
            shutil.rmtree(job["work_dir"], ignore_errors=True)
        else:
            unreal.log_warning(
                "[Building Async] 本次临时文件保留于："
                + str(job["work_dir"])
            )


def _import_result(job):
    """主线程：发布 OBJ、重新导入、提交状态、回填界面。"""
    target = job["target"]
    staged = job["staged_obj"]
    backup = job["work_dir"] / "previous"
    existed = bundle.capture(target, backup)

    try:
        bundle.publish_geometry(staged, target)
        parameters = unreal.ImportAssetParameters()
        parameters.set_editor_property("is_automated", True)

        imported = job["manager"].reimport_asset(
            job["asset"],
            parameters,
        )

        if not imported:
            raise RuntimeError("UE 重新导入未返回成功结果")
        from ue_medieval_materials import apply_palette
        apply_palette(job['asset'],target,job['ready_spec']['palette'])
        spec = job['ready_spec']
        pending_state = job['work_dir'] / 'state_pending.json'
        pending_state.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding='utf-8')
        pending_state.replace(target.with_suffix('.spec.json'))

    except Exception:
        bundle.restore(target, backup, existed)

        raise RuntimeError(
            "UE 重新导入失败，源 OBJ 已恢复，连续修改状态未更新。"
            "请检查日志并手动重新导入恢复后的 OBJ。"
        ) from None

    spec = job["ready_spec"]

    try:
        widgets = job["widgets"]
        spec = resolve_spec(spec)
        widgets["WidthInput"].set_value(float(spec["width"]))
        widgets["DepthInput"].set_value(float(spec["depth"]))
        widgets["FloorsInput"].set_value(float(spec["floors"]))
        widgets["FlatRoofInput"].set_is_checked(
            spec["roof_type"] == "flat"
        )
    except Exception as error:
        unreal.log_warning(
            "[Building Async] 建筑已更新，但面板回填失败："
            + str(error)
        )

    recovery = PROJECT / "exports" / "previous_success"
    recovery.mkdir(exist_ok=True)
    for file in backup.iterdir():
        shutil.copy2(file, recovery / file.name)
    if job.get('on_complete'): job['on_complete'](job['ready_spec'])
    _finish(job, True, "生成完成，请保存建筑资产。")


def _tick(delta_time):
    """UE 每帧回调：读取队列，不等待工作线程。"""
    job = _job
    if job is None:
        return

    try:
        # 留出一帧刷新“正在导入”提示
        if job["ready_spec"] is not None:
            _import_result(job)
            return

        while True:
            try:
                event, data = job["events"].get_nowait()
            except queue.Empty:
                break

            if event == "status":
                _status(job, data)

            elif event == "log":
                unreal.log("[Building Async] " + data)

            elif event == "error":
                _finish(job, False, "失败：" + data)
                return

            elif event == "ready":
                job["ready_spec"] = data
                _status(job, "正在重新导入 UE……")
                return

    except Exception as error:
        _finish(job, False, "失败：" + str(error))


def _start_impl(description, tool_ui, base_override=None, target_override=None, on_complete=None):
    """蓝图调用入口，必须从 UE 主线程执行。"""
    global _job

    if _job is not None:
        unreal.log_warning("[Building Async] 已有任务正在执行")
        return

    description = str(description).strip()
    if not description:
        raise ValueError("请输入建筑描述")

    from building_api import configuration
    api = configuration()
    key = api["key"]

    tool = runpy.run_path(
        str(PROJECT / "ue_building_tool.py"),
        run_name="building_tool",
    )
    planner = runpy.run_path(
        str(PROJECT / "building_planner.py"),
        run_name="building_planner",
    )

    for path in (tool["HYTHON"], tool["HIP_FILE"]):
        if not Path(path).is_file():
            raise RuntimeError("文件不存在：" + str(path))

    asset, manager = target_override or tool['selected_target']()
    sources = manager.can_reimport(asset)
    target = tool['source_for_asset'](asset,manager)

    if (
        not sources
        or len(sources) != 1
        or Path(str(sources[0])).resolve() != target
    ):
        raise ValueError("选中资产的来源不是当前配置的中世纪旅馆 OBJ")

    names = [
        "Btn_Generate",
        "Btn_AIGenerate",
        "PromptInput",
        "WidthInput",
        "DepthInput",
        "FloorsInput",
        "FlatRoofInput",
        "StatusText",
    ]

    widgets = {}
    for name in names:
        widget = tool_ui.find_child_widget_by_name(name)
        if widget is None:
            raise ValueError("面板中找不到控件：" + name)
        widgets[name] = widget

    state_file = target.with_suffix(".spec.json")
    for name in ('ParameterPanel','CompactAdvanced','ApiPanel','ReadSelection'):
        extra=tool_ui.find_child_widget_by_name(name)
        if extra is not None:
            widgets[name]=extra
            names.append(name)
    new_building = description.startswith(("新建", "重新生成"))

    if base_override is not None:
        base_spec = base_override
    elif not new_building and state_file.exists():
        base_spec = json.loads(state_file.read_text(encoding="utf-8"))
    else:
        base_spec = dict(tool["SPEC"])

    if not isinstance(base_spec, dict):
        raise ValueError("建筑状态文件格式错误")

    base_spec = normalize_spec(base_spec)
    tool["validate_spec"](base_spec)

    # 与目标 OBJ 同盘，便于替换文件
    target.parent.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(
        prefix="building_job_",
        dir=str(target.parent),
    ))
    staged_obj = work_dir / target.name

    job = {
        "events": queue.Queue(),
        "asset": asset,
        "manager": manager,
        "target": target,
        "staged_obj": staged_obj,
        "work_dir": work_dir,
        "widgets": widgets,
        "status_widget": widgets["StatusText"],
        "restore_enabled": [],
        "ready_spec": None,
        "tick_handle": None,
        "on_complete": on_complete,
    }

    config = {
        "key": key,
        "api": api,
        "description": description,
        "base_spec": base_spec,
        "system_prompt": planner["SYSTEM_PROMPT"],
        "validate": tool["validate_spec"],
        "hython": str(tool["HYTHON"]),
        "hip": str(tool["HIP_FILE"]),
        "houdini_code": tool["HOUDINI_CODE"],
        "staged_obj": str(staged_obj),
    }

    _job = job

    try:
        # 暂时锁定输入，避免计算过程中改动面板
        for name in names:
            if name == "StatusText":
                continue
            widget = widgets[name]
            job["restore_enabled"].append(
                (widget, widget.get_is_enabled())
            )
            widget.set_is_enabled(False)

        _status(job, "正在解析建筑描述……")

        job["tick_handle"] = unreal.register_slate_post_tick_callback(
            _tick
        )

        thread = threading.Thread(
            target=_worker,
            args=(job["events"], config),
            daemon=True,
        )
        thread.start()

    except Exception as error:
        _finish(job, False, "启动失败：" + str(error))


def start(description, tool_ui, **kwargs):
    try:
        return _start_impl(description, tool_ui, **kwargs)
    except Exception as error:
        message='启动失败：'+str(error)
        try: tool_ui.find_child_widget_by_name('StatusText').set_text(message)
        except Exception: pass
        unreal.log_error(message)
        unreal.EditorDialog.show_message('AI 建筑未生成',message,unreal.AppMsgType.OK)
