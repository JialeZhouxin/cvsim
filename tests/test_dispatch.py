"""Lab dispatch: run/sample 单点分派 (ADR-0010) — 行为 + 结构守卫。

行为测试打在 dispatch 公开 interface 上（双动词，rng=None 由 circuit.seed
派生）；结构守卫是 ADR-0010 #8 的换防合同（AST 级，不 import cvsim）。
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.lab import LabResult, load_circuit

# ---------------------------------------------------------------------------
# fixtures — 三后端同一物理场景（squeeze 0.1）
# ---------------------------------------------------------------------------

def _v1_body(backend: str, **extra) -> dict:
    body = {
        "schema": "circuit_v1",
        "nmode": 1,
        "backend": backend,
        "seed": 7,
        "ops": [{"id": "s", "op": "squeeze", "modes": [0], "params": {"r": 0.1}}],
        "view": {"wigner_mode": 0, "lim": 4.0, "n": 16},
    }
    body.update(extra)
    return body


def _gaussian_body() -> dict:
    return {
        "schema": "circuit_v1",
        "nmode": 1,
        "seed": 7,
        "ops": [{"id": "s", "op": "squeeze", "modes": [0], "params": {"r": 0.1, "phi": 0.0}}],
        "view": {"wigner_mode": 0, "lim": 4.0, "n": 16},
    }


# ---------------------------------------------------------------------------
# 1. dispatch 双动词：三后端全部走同一 interface
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("backend", ["gaussian", "fock", "bosonic"])
def test_run_circuit_all_backends_via_dispatch(backend: str) -> None:
    """run_circuit 是三后端的唯一入口：返回 LabResult 且自报家门。"""
    from cvsim.lab import dispatch

    body = _v1_body(backend)
    if backend == "gaussian":
        body = _gaussian_body()
    result = dispatch.run_circuit(load_circuit(body))
    assert isinstance(result, LabResult)
    assert result.backend == backend
    assert result.nmode == 1


@pytest.mark.parametrize("backend", ["gaussian", "fock", "bosonic"])
def test_sample_circuit_all_backends_via_dispatch(backend: str) -> None:
    """sample_circuit 带 sampled 契约键（seed/sampled 入 LabResult）。"""
    from cvsim.lab import dispatch

    body = _v1_body(backend)
    if backend == "gaussian":
        body = _gaussian_body()
    result = dispatch.sample_circuit(load_circuit(body))
    assert isinstance(result, LabResult)
    assert result.sampled is True
    assert result.seed == 7


def test_dispatch_rng_none_derives_from_seed() -> None:
    """rng=None → dispatch 用 circuit.seed 派生：同 seed 两次运行 measured
    一致（fock 有真采样路径，最能暴露 rng 是否真的接上了）。"""
    from cvsim.lab import dispatch

    body = _v1_body("fock", ops=[
        {"id": "s", "op": "squeeze", "modes": [0], "params": {"r": 0.1}},
        {"id": "m", "op": "measure_homodyne", "modes": [0], "params": {"name": "hd"}},
    ])
    r1 = dispatch.sample_circuit(load_circuit(body))
    r2 = dispatch.sample_circuit(load_circuit(body))
    assert r1.measured == r2.measured


def test_dispatch_rng_injection_still_works() -> None:
    """显式 rng 仍被尊重（测试注入通道，ADR-0010 双动词签名）。"""
    from cvsim.lab import dispatch

    body = _v1_body("fock", ops=[
        {"id": "m", "op": "measure_homodyne", "modes": [0], "params": {"name": "hd"}},
    ])
    rng_a = np.random.default_rng(3)
    rng_b = np.random.default_rng(3)
    a = dispatch.sample_circuit(load_circuit(body), rng=rng_a)
    b = dispatch.sample_circuit(load_circuit(body), rng=rng_b)
    assert a.measured == b.measured  # 同 seed 的两个 Generator → 同结果


def test_dispatch_unknown_backend_raises() -> None:
    """注册表外的 backend：显式 KeyError，不静默落 gaussian。"""
    from cvsim.lab import dispatch

    circuit = load_circuit(_v1_body("fock"))
    circuit.backend = "quantum_dots"  # type: ignore[assignment]
    with pytest.raises(KeyError):
        dispatch.run_circuit(circuit)


# ---------------------------------------------------------------------------
# 1b. detail=steps 升格为 LabCircuit 扩展字段（ADR-0010 #4）
# ---------------------------------------------------------------------------

def test_detail_steps_loads_into_labcircuit() -> None:
    """detail 是 load 层解析的扩展字段：bosonic circuit.detail == 'steps'。"""
    circuit = load_circuit(_v1_body("bosonic", detail="steps"))
    assert circuit.detail == "steps"


def test_detail_absent_is_none() -> None:
    circuit = load_circuit(_v1_body("bosonic"))
    assert circuit.detail is None


@pytest.mark.parametrize("bad", ["snapshot", True, 3, "step"])
def test_detail_invalid_value_rejected(bad: object) -> None:
    """detail 只接受 None|'steps'：其余值 422（422 契约，不静默忽略）。"""
    from cvsim.lab import CircuitV0Error

    with pytest.raises(CircuitV0Error, match="detail"):
        load_circuit(_v1_body("bosonic", detail=bad))


def test_detail_steps_reaches_bosonic_runner_via_server() -> None:
    """端到端：/run + detail=steps 仍返回分步快照（steps 线程不因搬家断）。"""
    from fastapi.testclient import TestClient

    from cvsim.lab.server import app

    body = _v1_body("bosonic", detail="steps", initial=["gkp0"], ops=[
        {"id": "l", "op": "loss", "modes": [0], "params": {"T": 0.9}},
        {"id": "m", "op": "measure_homodyne", "modes": [0], "params": {"name": "hd"}},
    ])
    tc = TestClient(app)
    r = tc.post("/run", json=body)
    assert r.status_code == 200, r.json()
    assert "steps" in r.json() and len(r.json()["steps"]) >= 1


def test_run_without_detail_has_no_steps_key() -> None:
    """无 detail → 无 steps 键（序列化省略 falsy extensions，字节不变）。"""
    from fastapi.testclient import TestClient

    from cvsim.lab.server import app

    tc = TestClient(app)
    r = tc.post("/run", json=_v1_body("bosonic", initial=["gkp0"]))
    assert r.status_code == 200
    assert "steps" not in r.json()


# ---------------------------------------------------------------------------
# 2. 顶层 re-export 不变（test_lab_ir 等调用面零改动存活）
# ---------------------------------------------------------------------------

def test_top_level_verbs_reexport() -> None:
    """cvsim.lab 顶层动词继续可用（re-export 源换到 dispatch，调用方无感）。"""
    import cvsim.lab as lab

    assert lab.run_circuit is not None
    assert lab.sample_circuit is not None
    assert "run_circuit" in lab.__all__ and "sample_circuit" in lab.__all__


# ---------------------------------------------------------------------------
# 3. ADR-0010 #8 结构守卫（AST，学 test_architecture.py）
# ---------------------------------------------------------------------------

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER_MODULES = ("gaussian_backend", "fock_backend", "bosonic_backend")


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.extend(node.module if node.level == 0 else ".".join(["cvsim.lab"] + [node.module]))
    return out


def test_server_does_not_import_runners() -> None:
    """server.py 只经 dispatch 拿执行：不得 import 任何 runner 模块。"""
    mods = _imports(ROOT / "cvsim" / "lab" / "server.py")
    for runner in RUNNER_MODULES:
        assert not any(m == f"cvsim.lab.{runner}" for m in mods), (
            f"server.py imports {runner} directly — must go through dispatch (ADR-0010 #8)"
        )


def test_server_run_body_has_no_backend_branch() -> None:
    """/run /sample 路由体零 backend 特判（AST：函数体内无 backend 比较）。"""
    tree = ast.parse((ROOT / "cvsim" / "lab" / "server.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in ("run", "sample"):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Compare):
                    names = set()
                    for cmp_node in ast.walk(sub):
                        if isinstance(cmp_node, ast.Attribute) and cmp_node.attr == "backend":
                            names.add("backend")
                        if isinstance(cmp_node, ast.Constant) and cmp_node.value in ("fock", "bosonic", "gaussian"):
                            names.add("lit")
                    assert not {"backend", "lit"} <= names, (
                        f"server.{node.name} branches on circuit.backend — dispatch owns routing (ADR-0010)"
                    )


def test_ir_has_no_gaussian_execution_knowledge() -> None:
    """ir.py 无 gaussian 执行知识（ADR-0010 #3：_execute 搬去
    gaussian_backend 后 ir.py 只管 load/translate/schema）。"""
    src = (ROOT / "cvsim" / "lab" / "ir.py").read_text(encoding="utf-8")
    assert "GaussianState" not in src, "ir.py must not reference GaussianState (execution knowledge)"
    assert "_apply_measure" not in src, "ir.py must not own _apply_measure"
    assert "homodyne_mean" not in src, "ir.py must not import gaussian measurement ops"


# ---------------------------------------------------------------------------
# 4. check_wigner_mode 模板单点（ADR-0010 #5）：三个 runner 的越界消息字节一致
# ---------------------------------------------------------------------------

_WIGNER_OUT = "view.wigner_mode {mode} out of range (nmode={nmode})"


def test_wigner_mode_guard_template_matches_all_backends() -> None:
    """同一越界输入 → 三 runner 同一消息（模板单点，422 文本可测）。"""
    from cvsim.lab import CircuitV0Error, dispatch

    views = {"wigner_mode": 3, "lim": 4.0, "n": 8}
    two_ops = [
        {"id": "s0", "op": "squeeze", "modes": [0], "params": {"r": 0.1}},
        {"id": "s1", "op": "squeeze", "modes": [1], "params": {"r": 0.1}},
    ]
    for backend, body in (
        ("gaussian", {**_gaussian_body(), "nmode": 2, "ops": two_ops, "view": views}),
        ("fock", _v1_body("fock", nmode=2, ops=two_ops, view=views, cutoff=4)),
        ("bosonic", _v1_body("bosonic", nmode=2, ops=two_ops, view=views, initial=[None, None])),
    ):
        circuit = load_circuit(body)
        with pytest.raises(CircuitV0Error) as ei:
            dispatch.run_circuit(circuit)
        assert str(ei.value) == _WIGNER_OUT.format(mode=3, nmode=2), f"{backend} drift"