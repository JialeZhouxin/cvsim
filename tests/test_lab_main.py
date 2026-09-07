"""Lab 启动入口测试：``python -m cvsim.lab`` 必须正确接线 uvicorn。

cover 的是 `cvsim/lab/__main__.py` 全部 6 语句：main() 的 app 字符串 /
host / port / log_level 参数，以及 ``__main__`` guard 直接执行时的单次调用。
之前该文件 0% 覆盖 —— 启动参数改错（如端口）不会在任何门里暴露。
"""

from __future__ import annotations

import runpy
import sys
from typing import Any

import cvsim.lab.__main__ as lab_main


def test_main_runs_uvicorn_with_lab_server(monkeypatch: Any) -> None:
    calls: list[tuple[tuple, dict]] = []

    def fake_run(*args: Any, **kwargs: Any) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr(lab_main.uvicorn, "run", fake_run)
    lab_main.main()

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[0] == "cvsim.lab.server:app"
    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["port"] == 8000
    assert kwargs["log_level"] == "info"


def test_module_guard_calls_main_once_on_direct_run(monkeypatch: Any) -> None:
    """``python -m cvsim.lab`` 路径：guard 必须触发 main() 恰好一次。

    用 runpy.run_module(run_name="__main__") 重执行模块源码，覆盖
    ``if __name__ == "__main__": main()`` 分支（pytest 导入路径下不执行）。
    """
    calls: list[tuple[tuple, dict]] = []

    def fake_run(*args: Any, **kwargs: Any) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr(lab_main.uvicorn, "run", fake_run)
    # runpy 对已导入模块的 re-exec 会告警（unpredictable behaviour），
    # 先弹出 sys.modules 条目让 run_module 走干净加载；执行完恢复。
    saved = sys.modules.pop("cvsim.lab.__main__", None)
    try:
        runpy.run_module("cvsim.lab.__main__", run_name="__main__")
    finally:
        if saved is not None:
            sys.modules["cvsim.lab.__main__"] = saved

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[0] == "cvsim.lab.server:app"
    assert kwargs["port"] == 8000
